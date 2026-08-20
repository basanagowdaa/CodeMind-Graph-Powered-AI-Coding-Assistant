"""
backend/api/benchmark.py
Benchmarking Endpoint — baseline vs CodeMind comparisons.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.services.analysis_service import AnalysisService
from backend.services.benchmark_service import BenchmarkService
from backend.hydra.client import get_hydra_client

router = APIRouter(prefix="/api/benchmark", tags=["Benchmark"])
_analysis_service = AnalysisService()
_hydra_client = get_hydra_client()
_benchmark_service = BenchmarkService(_hydra_client)


@router.get("/{repository_id}")
async def run_benchmark(repository_id: str) -> Any:
    """
    Run baseline (vector-only) vs CodeMind (HydraDB graph) retrieval benchmarks
    and return measurable performance differences.
    """
    graph = _analysis_service.get_graph(repository_id)
    if not graph:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repository_id}' has not been analyzed.",
        )

    hydra_db = _analysis_service.get_hydra_database(repository_id)
    if not hydra_db:
        hydra_db = repository_id

    try:
        results = _benchmark_service.run_benchmark(hydra_db, graph)
        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute benchmark run: {exc}",
        )
