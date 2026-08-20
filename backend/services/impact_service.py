"""
backend/services/impact_service.py
Impact Analysis Engine — the "Before You Change It" feature.

Uses two sources of truth:
1. Local CodeGraph (BFS/DFS for exact structural paths)
2. HydraDB graph_context (semantic + dependency path retrieval)

Both are combined to produce evidence-based impact results.
NO confidence percentages are fabricated. Impact level is computed
from actual connection counts.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.models.api_models import (
    ImpactAnalysisResponse,
    ImpactedEntity,
    DependencyPathItem,
)
from backend.models.graph_models import CodeGraph, Node, NodeType, RelationshipType
from backend.hydra.retrieval import HydraRetrieval, DependencyPath

logger = logging.getLogger(__name__)


def _blast_radius(total: int) -> str:
    """Determine blast radius label from impact count. No arbitrary percentages."""
    if total == 0:
        return "none"
    if total <= 3:
        return "low"
    if total <= 10:
        return "medium"
    if total <= 25:
        return "high"
    return "critical"


def _node_to_impacted(
    node: Node,
    relationship: str,
    impact_level: str,
) -> ImpactedEntity:
    return ImpactedEntity(
        id=node.id,
        name=node.name,
        type=node.type.value,
        file=node.file,
        line=node.line,
        relationship=relationship,
        impact_level=impact_level,
        confidence=1.0,  # structural path = confirmed
    )


class ImpactService:
    """
    Computes the impact of changing a code entity.
    Combines local graph traversal with HydraDB semantic retrieval.
    """

    def __init__(self, hydra_retrieval: HydraRetrieval) -> None:
        self._hydra = hydra_retrieval

    def analyze_impact(
        self,
        graph: CodeGraph,
        hydra_database: str,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        *,
        max_depth: int = 5,
    ) -> ImpactAnalysisResponse:
        """
        Full impact analysis for a code entity.

        Local graph: BFS traversal for exact structural callers/tests/APIs
        HydraDB: semantic query for additional context and dependency paths
        """
        # ── 1. Local structural impact (from parsed graph) ────────────────
        local_impact = graph.get_downstream_impact(entity_id, max_depth=max_depth)

        callers = [
            _node_to_impacted(n, "CALLS", "direct") for n in local_impact["callers"]
        ]
        tests = [
            _node_to_impacted(n, "TESTS", "direct") for n in local_impact["tests"]
        ]
        apis = [
            _node_to_impacted(n, "EXPOSES", "direct") for n in local_impact["apis"]
        ]
        files = [
            _node_to_impacted(n, "IMPORTS", "transitive") for n in local_impact["files"]
        ]
        classes = [
            _node_to_impacted(n, "USES", "transitive") for n in local_impact["classes"]
        ]

        # ── 2. HydraDB graph-aware query ──────────────────────────────────
        hydra_result = None
        dependency_paths: list[list[DependencyPathItem]] = []
        hydradb_query_paths = 0

        try:
            hydra_result = self._hydra.query_impact(
                database=hydra_database,
                entity_name=entity_name,
                entity_type=entity_type,
            )
            hydradb_query_paths = len(hydra_result.dependency_paths)

            # Convert HydraDB dependency paths to API model
            for path in hydra_result.dependency_paths:
                path_items = [
                    DependencyPathItem(
                        source=t.source_name,
                        predicate=t.predicate,
                        target=t.target_name,
                        context=t.context,
                    )
                    for t in path.triplets
                ]
                if path_items:
                    dependency_paths.append(path_items)

        except Exception as exc:
            logger.warning(
                "HydraDB impact query failed (using local graph only): %s", exc
            )

        # ── 3. Compute summary ────────────────────────────────────────────
        total_impacted = len(callers) + len(tests) + len(apis) + len(files) + len(classes)

        logger.info(
            "Impact analysis for '%s': %d callers, %d tests, %d APIs, %d files, "
            "%d HydraDB paths",
            entity_name, len(callers), len(tests), len(apis), len(files), hydradb_query_paths,
        )

        return ImpactAnalysisResponse(
            repository_id="",   # filled by caller
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type,
            callers=callers,
            tests=tests,
            apis=apis,
            files=files,
            classes=classes,
            dependency_paths=dependency_paths,
            total_impacted=total_impacted,
            blast_radius=_blast_radius(total_impacted),
            graph_source="hydradb",
            hydradb_query_paths=hydradb_query_paths,
        )

    def get_dependency_chain(
        self,
        graph: CodeGraph,
        from_id: str,
        to_id: str,
        max_depth: int = 10,
    ) -> list[list[str]] | None:
        """
        Find all paths from from_id to to_id in the graph.
        Returns list of paths (each path is a list of node IDs).
        """
        paths: list[list[str]] = []
        visited: set[str] = set()

        def dfs(current: str, path: list[str]) -> None:
            if current == to_id:
                paths.append(list(path))
                return
            if current in visited or len(path) > max_depth:
                return
            visited.add(current)
            for rel in graph.relationships:
                if rel.source_id == current and rel.target_id not in visited:
                    path.append(rel.target_id)
                    dfs(rel.target_id, path)
                    path.pop()
            visited.discard(current)

        dfs(from_id, [from_id])
        return paths if paths else None
