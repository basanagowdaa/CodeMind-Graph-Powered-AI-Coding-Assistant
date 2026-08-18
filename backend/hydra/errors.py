"""
backend/hydra/errors.py
Typed error hierarchy for HydraDB operations.
All errors carry a human-readable message suitable for the UI.
"""
from __future__ import annotations


class HydraError(Exception):
    """Base error for all HydraDB operations."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class HydraConnectionError(HydraError):
    """Raised when the HydraDB client cannot connect or authenticate."""


class HydraIngestionError(HydraError):
    """Raised when context ingestion fails."""


class HydraRetrievalError(HydraError):
    """Raised when a query or retrieval operation fails."""


class HydraTimeoutError(HydraError):
    """Raised when polling for ingestion status times out."""
