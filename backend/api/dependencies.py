"""
backend/api/dependencies.py
Dependency and Test mapping routes for individual entities.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.services.analysis_service import AnalysisService
from backend.models.api_models import GraphNode, GraphEdge

router = APIRouter(prefix="/api/dependencies", tags=["Dependencies"])
_service = AnalysisService()


@router.get("/{repository_id}/{entity_id}/callers")
async def get_callers(repository_id: str, entity_id: str) -> list[dict[str, Any]]:
    """Get all functions/methods that directly call the given function."""
    graph = _service.get_graph(repository_id)
    if not graph:
        raise HTTPException(
            status_code=404, detail=f"Repository '{repository_id}' not analyzed."
        )

    node = graph.get_node(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    callers = graph.get_callers(entity_id)
    return [
        {
            "id": c.id,
            "name": c.name,
            "type": c.type.value,
            "file": c.file,
            "line": c.line,
        }
        for c in callers
    ]


@router.get("/{repository_id}/{entity_id}/callees")
async def get_callees(repository_id: str, entity_id: str) -> list[dict[str, Any]]:
    """Get all functions/methods that the given function calls."""
    graph = _service.get_graph(repository_id)
    if not graph:
        raise HTTPException(
            status_code=404, detail=f"Repository '{repository_id}' not analyzed."
        )

    node = graph.get_node(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    callees = graph.get_callees(entity_id)
    return [
        {
            "id": c.id,
            "name": c.name,
            "type": c.type.value,
            "file": c.file,
            "line": c.line,
        }
        for c in callees
    ]


@router.get("/{repository_id}/{entity_id}/tests")
async def get_tests(repository_id: str, entity_id: str) -> list[dict[str, Any]]:
    """Get all test functions/cases covering the given entity."""
    graph = _service.get_graph(repository_id)
    if not graph:
        raise HTTPException(
            status_code=404, detail=f"Repository '{repository_id}' not analyzed."
        )

    node = graph.get_node(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    tests = graph.get_tests_for(entity_id)
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type.value,
            "file": t.file,
            "line": t.line,
        }
        for t in tests
    ]
