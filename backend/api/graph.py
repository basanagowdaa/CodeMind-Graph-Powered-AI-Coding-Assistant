"""
backend/api/graph.py
Code Graph endpoint — returns nodes and edges for visualization.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.models.api_models import GraphResponse, GraphNode, GraphEdge
from backend.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/graph", tags=["Graph"])
_service = AnalysisService()


@router.get("/{repository_id}", response_model=GraphResponse)
async def get_graph(repository_id: str) -> Any:
    """
    Get the complete code graph for a repository.
    Includes degrees (connection counts) for node size scaling in the UI.
    """
    graph = _service.get_graph(repository_id)
    if not graph:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repository_id}' has not been analyzed yet.",
        )

    # 1. Compute node degrees
    degree: dict[str, int] = {}
    for rel in graph.relationships:
        degree[rel.source_id] = degree.get(rel.source_id, 0) + 1
        degree[rel.target_id] = degree.get(rel.target_id, 0) + 1

    # 2. Map nodes
    nodes = [
        GraphNode(
            id=n.id,
            type=n.type.value,
            name=n.name,
            file=n.file,
            line=n.line,
            label=n.display_label(),
            connection_count=degree.get(n.id, 0),
            metadata={
                "docstring": n.docstring,
                "parameters": n.parameters,
                "return_type": n.return_type,
                "decorators": n.decorators,
                "is_async": n.is_async,
                "base_classes": n.base_classes,
                **n.metadata
            }
        )
        for n in graph.nodes.values()
    ]

    # 3. Map edges
    edges = [
        GraphEdge(
            source=r.source_id,
            target=r.target_id,
            relationship=r.relationship.value,
            context=r.context,
        )
        for r in graph.relationships
    ]

    return GraphResponse(
        repository_id=repository_id,
        nodes=nodes,
        edges=edges,
        statistics={
            "files": graph.file_count,
            "functions": graph.function_count,
            "classes": graph.class_count,
            "apis": graph.api_count,
            "tests": graph.test_count,
            "relationships": graph.relationship_count,
        }
    )
