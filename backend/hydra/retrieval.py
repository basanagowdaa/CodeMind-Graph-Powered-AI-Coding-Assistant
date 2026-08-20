"""
backend/hydra/retrieval.py
HydraDB graph-aware retrieval for CodeMind.

Uses graph_context=True to get dependency paths (query_paths + chunk_relations)
alongside semantic search results. This is the core of the impact analysis engine.

Reference: https://docs.hydradb.com/essentials/v2/context-graphs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .client import HydraClient
from .errors import HydraRetrievalError

logger = logging.getLogger(__name__)


@dataclass
class Triplet:
    """A single source → relation → target triple from HydraDB graph_context."""

    source_name: str
    source_type: str
    predicate: str
    target_name: str
    target_type: str
    context: str = ""
    origin: str = ""  # "byog" for our supplied graphs


@dataclass
class DependencyPath:
    """A multi-hop chain of triplets from a query_path."""

    triplets: list[Triplet]
    relevancy_score: float
    group_id: str
    source_chunk_ids: list[str] = field(default_factory=list)

    def as_text_chain(self) -> str:
        """
        Format the path as a human-readable chain:
        login → CALLS → authenticate_user → CALLS → validate_token
        """
        if not self.triplets:
            return ""
        parts = [self.triplets[0].source_name]
        for t in self.triplets:
            parts.append(f"→ {t.predicate} →")
            parts.append(t.target_name)
        return " ".join(parts)


@dataclass
class RetrievalResult:
    """Full result from a HydraDB graph-aware query."""

    query: str
    chunks: list[dict[str, Any]]
    dependency_paths: list[DependencyPath]
    chunk_relations: list[DependencyPath]
    raw_graph_context: dict[str, Any] | None = None

    @property
    def has_graph_data(self) -> bool:
        return bool(self.dependency_paths or self.chunk_relations)

    def all_entity_names(self) -> set[str]:
        """Collect every entity name mentioned across all dependency paths."""
        names: set[str] = set()
        for path in self.dependency_paths + self.chunk_relations:
            for t in path.triplets:
                names.add(t.source_name)
                names.add(t.target_name)
        return names


class HydraRetrieval:
    """
    Graph-aware retrieval from HydraDB.
    Always queries with graph_context=True and mode="thinking" for multi-hop traversal.
    """

    def __init__(self, client: HydraClient) -> None:
        self._client = client

    # ── Main retrieval ─────────────────────────────────────────────────────

    def query_with_graph(
        self,
        database: str,
        query: str,
        *,
        top_k: int = 15,
        metadata_filters: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """
        Run a hybrid search with graph context enabled.

        Returns chunks (semantically relevant code entities) AND
        graph_context (dependency paths as triplets) — the combination
        used by the impact analysis and LLM reasoning layers.

        Args:
            database: HydraDB database for this repository.
            query: Natural language question about the codebase.
            top_k: Maximum number of chunks to return.
            metadata_filters: Optional filters (e.g. {"entity_type": "Function"}).
        """
        try:
            kwargs: dict[str, Any] = {
                "database": database,
                "query": query,
                "type": "knowledge",
                "query_by": "hybrid",
                "mode": "thinking",  # required for forceful relations + multi-hop
                "graph_context": True,  # return dependency paths
                "query_forceful_relations": True,
                "max_results": top_k,
            }
            if metadata_filters:
                kwargs["metadata_filters"] = metadata_filters

            raw = self._client.raw.query(**kwargs)
        except Exception as exc:
            raise HydraRetrievalError(
                f"HydraDB query failed for database '{database}'",
                cause=exc,
            ) from exc

        return self._parse_result(query, raw)

    def query_impact(
        self,
        database: str,
        entity_name: str,
        entity_type: str | None = None,
    ) -> RetrievalResult:
        """
        Specialized query for impact analysis:
        "What could be affected if <entity_name> changes?"

        Adds entity_type filter when known for precision.
        """
        query = (
            f"What code depends on {entity_name}? "
            f"What calls {entity_name}? "
            f"What could break if {entity_name} changes?"
        )
        filters = {}
        # Don't filter entity type here — we want everything that DEPENDS ON the entity,
        # which may span multiple types
        return self.query_with_graph(database, query, metadata_filters=filters or None)

    def query_dependencies(
        self,
        database: str,
        entity_name: str,
    ) -> RetrievalResult:
        """What does this entity call/import/depend on?"""
        query = (
            f"What does {entity_name} call? "
            f"What does {entity_name} depend on? "
            f"What does {entity_name} import?"
        )
        return self.query_with_graph(database, query)

    def query_tests(
        self,
        database: str,
        entity_name: str,
    ) -> RetrievalResult:
        """Which test functions test this entity?"""
        query = (
            f"Which tests cover {entity_name}? What test functions test {entity_name}?"
        )
        return self.query_with_graph(database, query, metadata_filters=None)

    # ── Context relations ──────────────────────────────────────────────────

    def get_entity_relations(
        self,
        database: str,
        source_id: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve stored relations for a specific entity using GET /context/relations.
        Returns raw relation objects.
        """
        try:
            result = self._client.raw.context.relations(
                database=database,
                source_id=source_id,
            )
            return (
                result.data.relations if result.data and result.data.relations else []
            )
        except Exception as exc:
            raise HydraRetrievalError(
                f"Failed to retrieve relations for '{source_id}' in '{database}'",
                cause=exc,
            ) from exc

    # ── Response parsing ───────────────────────────────────────────────────

    def _parse_result(self, query: str, raw: Any) -> RetrievalResult:
        """
        Convert the raw HydraDB response into our typed RetrievalResult.
        Handles both the chunks and the graph_context (triplets).
        """
        chunks = self._parse_chunks(raw)
        dependency_paths, chunk_relations = self._parse_graph_context(raw)

        raw_graph = None
        if hasattr(raw, "data") and raw.data and hasattr(raw.data, "graph_context"):
            gc = raw.data.graph_context
            if gc:
                raw_graph = {
                    "query_paths_count": len(getattr(gc, "query_paths", []) or []),
                    "chunk_relations_count": len(
                        getattr(gc, "chunk_relations", []) or []
                    ),
                }

        return RetrievalResult(
            query=query,
            chunks=chunks,
            dependency_paths=dependency_paths,
            chunk_relations=chunk_relations,
            raw_graph_context=raw_graph,
        )

    def _parse_chunks(self, raw: Any) -> list[dict[str, Any]]:
        """Extract the ranked chunks from the response."""
        chunks = []
        if not (hasattr(raw, "data") and raw.data and hasattr(raw.data, "chunks")):
            return chunks
        for chunk in raw.data.chunks or []:
            # HydraDB v2 SDK uses chunk_content and relevancy_score
            text_val = getattr(chunk, "chunk_content", None) or getattr(
                chunk, "text", ""
            )
            score_val = getattr(chunk, "relevancy_score", None)
            if score_val is None:
                score_val = getattr(chunk, "score", 0.0)

            chunk_dict: dict[str, Any] = {
                "id": getattr(chunk, "id", None),
                "text": text_val,
                "score": score_val,
                "source_id": getattr(chunk, "source_id", None)
                or getattr(chunk, "id", None),
                "metadata": {},
            }
            # Pull metadata if available
            if hasattr(chunk, "metadata") and chunk.metadata:
                chunk_dict["metadata"] = dict(chunk.metadata)
            elif hasattr(chunk, "source") and chunk.source:
                src = chunk.source
                chunk_dict["metadata"] = {
                    "title": getattr(src, "title", ""),
                    "type": getattr(src, "type", ""),
                    "url": getattr(src, "url", ""),
                }
            chunks.append(chunk_dict)
        return chunks

    def _parse_graph_context(
        self, raw: Any
    ) -> tuple[list[DependencyPath], list[DependencyPath]]:
        """
        Parse graph_context from the HydraDB response into typed DependencyPath objects.

        graph_context contains:
          - query_paths: multi-hop chains from query → retrieved chunks
          - chunk_relations: paths between retrieved chunks
        """
        if not (
            hasattr(raw, "data") and raw.data and hasattr(raw.data, "graph_context")
        ):
            return [], []

        gc = raw.data.graph_context
        if not gc:
            return [], []

        query_paths = self._parse_paths(getattr(gc, "query_paths", None) or [])
        chunk_relations = self._parse_paths(getattr(gc, "chunk_relations", None) or [])
        return query_paths, chunk_relations

    def _parse_paths(self, raw_paths: list[Any]) -> list[DependencyPath]:
        """Parse a list of raw path objects into DependencyPath instances."""
        paths = []
        for rp in raw_paths or []:
            triplets = []
            for rt in getattr(rp, "triplets", None) or []:
                src = getattr(rt, "source", None)
                rel = getattr(rt, "relation", None)
                tgt = getattr(rt, "target", None)
                if src and rel and tgt:
                    triplets.append(
                        Triplet(
                            source_name=getattr(src, "name", "?"),
                            source_type=getattr(src, "type", "UNKNOWN"),
                            predicate=(
                                getattr(rel, "canonical_predicate", None)
                                or getattr(rel, "predicate", "?")
                            ),
                            target_name=getattr(tgt, "name", "?"),
                            target_type=getattr(tgt, "type", "UNKNOWN"),
                            context=getattr(rel, "context", ""),
                            origin=getattr(rel, "origin", ""),
                        )
                    )
            if triplets:
                paths.append(
                    DependencyPath(
                        triplets=triplets,
                        relevancy_score=getattr(rp, "relevancy_score", 0.0),
                        group_id=getattr(rp, "group_id", ""),
                        source_chunk_ids=list(
                            getattr(rp, "source_chunk_ids", None) or []
                        ),
                    )
                )
        return paths
