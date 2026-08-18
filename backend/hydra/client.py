"""
backend/hydra/client.py
Real HydraDB client initialization and health-check.

Uses the official hydradb-sdk v2.
Auth: Bearer token via HYDRA_DB_API_KEY environment variable.
NEVER hard-codes secrets.
"""
from __future__ import annotations

import os
import time
import logging
from functools import lru_cache

from hydra_db import HydraDB  # hydradb-sdk >= 2, < 3

from .errors import HydraConnectionError

logger = logging.getLogger(__name__)


class HydraClient:
    """
    Thin wrapper around the official HydraDB client.
    Provides:
      - Lazy initialization from environment variable
      - Health check (real network call, not a mock)
      - Database provisioning with readiness polling
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None
        self._connected: bool = False
        if api_key:
            self._client = HydraDB(token=api_key, api_version="2")
        else:
            logger.warning("HYDRA_DB_API_KEY is not set. Copy .env.example → .env and add your key.")

    # ── Connection ────────────────────────────────────────────────────────

    def verify_connection(self) -> bool:
        """
        Perform a real network call to HydraDB to confirm connectivity.
        Returns True on success, raises HydraConnectionError on failure.
        """
        if not self._client:
            raise HydraConnectionError(
                "HYDRA_DB_API_KEY is not set. Copy .env.example → .env and add your key."
            )
        try:
            # List databases — lightweight call, no side effects
            self._client.databases.list()
            self._connected = True
            logger.info("HydraDB connection verified ✓")
            return True
        except Exception as exc:
            self._connected = False
            raise HydraConnectionError(
                "Could not connect to HydraDB. "
                "Check your HYDRA_DB_API_KEY and network connection.",
                cause=exc,
            ) from exc

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Database management ───────────────────────────────────────────────

    def _extract_database_names(self, response: Any) -> list[str]:
        if not response or not getattr(response, "data", None):
            return []
        data = response.data
        if hasattr(data, "databases") and data.databases is not None:
            return [str(d) for d in data.databases]
        if isinstance(data, list):
            return [getattr(d, "database", str(d)) for d in data]
        return []

    def ensure_database(self, database: str, *, timeout_seconds: int = 120) -> None:
        """
        Create the database if it doesn't exist, then poll until it's ready
        to accept ingestion. Idempotent — safe to call multiple times.
        """
        # Check if database already exists
        try:
            existing = self.raw.databases.list()
            existing_names = self._extract_database_names(existing)
            if database not in existing_names:
                logger.info("Creating HydraDB database: %s", database)
                self.raw.databases.create(database=database)
            else:
                logger.info("HydraDB database already exists: %s", database)
        except Exception as exc:
            raise HydraConnectionError(
                f"Failed to create/verify HydraDB database '{database}'",
                cause=exc,
            ) from exc

        # Poll until ready for ingestion
        logger.info("Waiting for database '%s' to be ready …", database)
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                status = self.raw.databases.status(database=database)
                if status.data and status.data.infra and status.data.infra.ready_for_ingestion:
                    logger.info("Database '%s' is ready ✓", database)
                    return
            except Exception:
                pass  # transient errors during provisioning are expected
            time.sleep(5)

        raise HydraConnectionError(
            f"Database '{database}' did not become ready within {timeout_seconds}s. "
            "It may still be provisioning — retry in a moment."
        )

    def delete_database(self, database: str) -> None:
        """Delete a database (used in tests, cleanup)."""
        try:
            self.raw.databases.delete(database=database)
            logger.info("Deleted HydraDB database: %s", database)
        except Exception as exc:
            raise HydraConnectionError(
                f"Failed to delete HydraDB database '{database}'",
                cause=exc,
            ) from exc

    def list_databases(self) -> list[str]:
        """Return the names of all HydraDB databases under this account."""
        try:
            result = self.raw.databases.list()
            return self._extract_database_names(result)
        except Exception as exc:
            raise HydraConnectionError("Failed to list HydraDB databases", cause=exc) from exc

    # ── Raw client access ─────────────────────────────────────────────────

    @property
    def raw(self) -> HydraDB:
        """
        Direct access to the underlying HydraDB SDK client for operations
        not wrapped by this class (ingestion, retrieval, etc.).
        """
        if not self._client:
            raise HydraConnectionError(
                "HYDRA_DB_API_KEY is not set. Copy .env.example → .env and add your key."
            )
        return self._client


@lru_cache(maxsize=1)
def get_hydra_client() -> HydraClient:
    """
    Singleton factory — reads HYDRA_DB_API_KEY from the environment.
    Called once at startup; connection is verified lazily on first use.
    """
    api_key = os.environ.get("HYDRA_DB_API_KEY", "")
    return HydraClient(api_key=api_key)
