"""
backend/hydra/__init__.py
Hydra sub-package — real HydraDB integration using hydradb-sdk v2.
"""
from .client import HydraClient, get_hydra_client
from .errors import HydraError, HydraConnectionError, HydraIngestionError, HydraRetrievalError

__all__ = [
    "HydraClient",
    "get_hydra_client",
    "HydraError",
    "HydraConnectionError",
    "HydraIngestionError",
    "HydraRetrievalError",
]
