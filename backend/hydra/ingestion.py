"""
backend/hydra/ingestion.py
HydraDB ingestion using the official "Bring Your Own Graph" (BYOG) API.

Strategy:
  - Each code entity (Function, Class, File, API, Test) becomes an app_knowledge
    item with its source code as text body.
  - The extracted static-analysis graph is passed as graph_payload (BYOG),
    giving HydraDB our deterministic code relationships instead of LLM-extracted ones.
  - Ingestion is idempotent: upsert=True replaces entities with the same id.
  - We poll for completion so callers know when the graph is queryable.

Reference: https://docs.hydradb.com/essentials/v2/bring-your-own-graph
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .client import HydraClient
from .errors import HydraIngestionError, HydraTimeoutError

logger = logging.getLogger(__name__)

# How long to wait for all items to finish indexing (seconds)
INGEST_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5
TERMINAL_STATUSES = {"completed", "errored", "success"}


@dataclass
class IngestionResult:
    """Summary of a completed ingestion batch."""

    database: str
    total: int
    succeeded: int
    failed: int
    ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class HydraIngestion:
    """
    Handles all context ingestion into HydraDB using the BYOG strategy.
    
    BYOG (Bring Your Own Graph): we supply our own entities and relations
    rather than relying on HydraDB's LLM extraction. This gives us:
      - Deterministic, reproducible code relationships
      - Faster ingestion (skips extraction LLM call)
      - Zero hallucinated relationships
    """

    def __init__(self, client: HydraClient) -> None:
        self._client = client

    # ── Main entry point ──────────────────────────────────────────────────

    def ingest_code_graph(
        self,
        database: str,
        entities: list[dict[str, Any]],
        graph_payload: dict[str, Any],
        *,
        wait_for_completion: bool = True,
        timeout_seconds: int = INGEST_TIMEOUT_SECONDS,
    ) -> IngestionResult:
        """
        Ingest a batch of code entities with their BYOG graph into HydraDB.

        Args:
            database: HydraDB database name for this repository.
            entities: List of app_knowledge items (one per code entity).
                      Each item must have an 'id' field matching a key in graph_payload.
            graph_payload: BYOG graph dict keyed by entity id.
                           { "entity_id": { "entities": {...}, "relations": [...] } }
            wait_for_completion: If True, poll until all items are indexed.
            timeout_seconds: Maximum wait time for polling.

        Returns:
            IngestionResult summary.
        """
        if not entities:
            logger.warning("ingest_code_graph called with empty entities list")
            return IngestionResult(database=database, total=0, succeeded=0, failed=0)

        logger.info(
            "Ingesting %d entities into HydraDB database '%s' (BYOG: %d graph entries)",
            len(entities),
            database,
            len(graph_payload),
        )

        # Batch in groups of 50 to avoid payload size limits
        batch_size = 50
        all_ids: list[str] = []
        all_errors: list[str] = []

        for batch_start in range(0, len(entities), batch_size):
            batch = entities[batch_start : batch_start + batch_size]
            # Only include graph_payload entries for items in this batch
            batch_ids = {e["id"] for e in batch if "id" in e}
            batch_graph = {k: v for k, v in graph_payload.items() if k in batch_ids}

            ids, errors = self._ingest_batch(database, batch, batch_graph)
            all_ids.extend(ids)
            all_errors.extend(errors)

        # Optionally wait for all items to be fully indexed
        if wait_for_completion and all_ids:
            self._poll_until_complete(database, all_ids, timeout_seconds=timeout_seconds)

        succeeded = len(all_ids)
        failed = len(all_errors)
        logger.info(
            "Ingestion complete: %d succeeded, %d failed", succeeded, failed
        )
        return IngestionResult(
            database=database,
            total=len(entities),
            succeeded=succeeded,
            failed=failed,
            ids=all_ids,
            errors=all_errors,
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _ingest_batch(
        self,
        database: str,
        app_knowledge_items: list[dict[str, Any]],
        graph_payload: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        """
        Send a single batch to HydraDB via POST /context/ingest with graph_payload.
        Returns (succeeded_ids, error_messages).
        """
        try:
            result = self._client.raw.context.ingest(
                type="knowledge",
                database=database,
                app_knowledge=json.dumps(app_knowledge_items),
                graph_payload=json.dumps(graph_payload) if graph_payload else None,
                upsert=True,  # idempotent: replace existing items with same id
            )
        except Exception as exc:
            raise HydraIngestionError(
                f"HydraDB ingest API call failed for database '{database}'",
                cause=exc,
            ) from exc

        # Parse the response
        ids: list[str] = []
        errors: list[str] = []

        if result.data and result.data.results:
            for item in result.data.results:
                if getattr(item, "error", None):
                    errors.append(f"{getattr(item, 'id', '?')}: {item.error}")
                else:
                    if hasattr(item, "id") and item.id:
                        ids.append(item.id)

        return ids, errors

    def _poll_until_complete(
        self,
        database: str,
        ids: list[str],
        *,
        timeout_seconds: int = INGEST_TIMEOUT_SECONDS,
    ) -> None:
        """
        Poll GET /context/status until all IDs reach a terminal state.
        Raises HydraTimeoutError if deadline is exceeded.
        """
        logger.info(
            "Polling status for %d items in database '%s' …", len(ids), database
        )
        deadline = time.time() + timeout_seconds
        pending = set(ids)

        while pending and time.time() < deadline:
            try:
                # Query in sub-batches of 100 (API limit)
                pending_list = list(pending)[:100]
                status_resp = self._client.raw.context.status(
                    database=database,
                    ids=pending_list,
                )
                if status_resp.data and status_resp.data.statuses:
                    for s in status_resp.data.statuses:
                        item_status = getattr(s, "indexing_status", None)
                        item_id = getattr(s, "id", None)
                        if item_status in TERMINAL_STATUSES and item_id in pending:
                            if item_status == "errored":
                                logger.warning(
                                    "Item '%s' errored during indexing: %s",
                                    item_id,
                                    getattr(s, "error_message", "unknown error"),
                                )
                            pending.discard(item_id)
            except Exception as exc:
                logger.warning("Status poll error (will retry): %s", exc)

            if pending:
                time.sleep(POLL_INTERVAL_SECONDS)

        if pending:
            raise HydraTimeoutError(
                f"{len(pending)} items did not finish indexing within {timeout_seconds}s. "
                f"Pending: {list(pending)[:5]} …"
            )

        logger.info("All items indexed ✓")

    # ── Utility ───────────────────────────────────────────────────────────

    def delete_entity(self, database: str, entity_id: str) -> None:
        """Remove a single entity from HydraDB (used during re-analysis cleanup)."""
        try:
            self._client.raw.context.delete(database=database, ids=[entity_id])
        except Exception as exc:
            raise HydraIngestionError(
                f"Failed to delete entity '{entity_id}' from '{database}'",
                cause=exc,
            ) from exc
