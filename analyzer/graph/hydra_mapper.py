"""
analyzer/graph/hydra_mapper.py
Maps the internal CodeGraph model to HydraDB's BYOG (Bring Your Own Graph) format.

This is the bridge between our static analysis and HydraDB.

For each Node:
  → One app_knowledge item (with source code as text body)
  → One entry in graph_payload (with extracted relationships as triplets)

The BYOG format:
  {
    "entity_id": {
      "entities": {
        "local_key": { "name": "...", "type": "...", "namespace": "..." }
      },
      "relations": [
        {
          "source": "local_key",
          "target": "other_local_key",
          "predicate": "CALLS",
          "context": "..."
        }
      ]
    }
  }

Reference: https://docs.hydradb.com/essentials/v2/bring-your-own-graph
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.models.graph_models import CodeGraph, Node, Relationship, NodeType, RelationshipType

logger = logging.getLogger(__name__)

# HydraDB entity type mapping: our NodeType → HydraDB entity type string
NODE_TYPE_TO_HYDRA: dict[NodeType, str] = {
    NodeType.REPOSITORY: "REPOSITORY",
    NodeType.FILE: "FILE",
    NodeType.FUNCTION: "FUNCTION",
    NodeType.CLASS: "CLASS",
    NodeType.API: "API",
    NodeType.TEST: "TEST",
    NodeType.MODULE: "MODULE",
    NodeType.SERVICE: "SERVICE",
    NodeType.DATABASE: "DATABASE",
}

# HydraDB namespace for code entities
NAMESPACE = "code"


class HydraMapper:
    """
    Converts a CodeGraph into the two parallel data structures
    required for HydraDB BYOG ingestion:

    1. app_knowledge_items: List[dict]  — one per node (the text body)
    2. graph_payload: dict              — one entry per node (the graph relations)
    """

    def map_graph(
        self,
        graph: CodeGraph,
        database: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Convert the entire CodeGraph to HydraDB BYOG format.

        Returns:
            (app_knowledge_items, graph_payload)
        """
        app_knowledge_items: list[dict[str, Any]] = []
        graph_payload: dict[str, Any] = {}

        # Group relationships by source node for efficient lookup
        rels_by_source: dict[str, list[Relationship]] = {}
        for rel in graph.relationships:
            rels_by_source.setdefault(rel.source_id, []).append(rel)

        for node in graph.nodes.values():
            # App knowledge item
            item = node.to_app_knowledge_item(database)
            app_knowledge_items.append(item)

            # BYOG graph payload for this node
            node_graph = self._build_node_graph(
                node, graph, rels_by_source.get(node.id, [])
            )
            if node_graph:
                graph_payload[node.id] = node_graph

        logger.info(
            "Mapped %d nodes → %d app_knowledge items, %d graph entries",
            len(graph.nodes),
            len(app_knowledge_items),
            len(graph_payload),
        )
        return app_knowledge_items, graph_payload

    def _build_node_graph(
        self,
        node: Node,
        graph: CodeGraph,
        outgoing_rels: list[Relationship],
    ) -> dict[str, Any] | None:
        """
        Build the BYOG graph entry for a single node.
        The entry declares entities this node relates to and the relations.

        Returns None if the node has no relationships (graph entry not needed).
        """
        if not outgoing_rels:
            return None

        entities: dict[str, dict[str, str]] = {}
        relations: list[dict[str, Any]] = []

        # Source entity (this node itself)
        src_key = "src"
        entities[src_key] = {
            "name": node.name,
            "type": NODE_TYPE_TO_HYDRA.get(node.type, "ENTITY"),
            "namespace": NAMESPACE,
            "identifier": node.id,
        }

        # For each outgoing relationship, add a target entity + relation
        for i, rel in enumerate(outgoing_rels):
            target_node = graph.get_node(rel.target_id)
            if not target_node:
                continue

            tgt_key = f"tgt_{i}"
            entities[tgt_key] = {
                "name": target_node.name,
                "type": NODE_TYPE_TO_HYDRA.get(target_node.type, "ENTITY"),
                "namespace": NAMESPACE,
                "identifier": target_node.id,
            }

            relation: dict[str, Any] = {
                "source": src_key,
                "target": tgt_key,
                "predicate": rel.relationship.value,
                "context": rel.context or f"{node.name} {rel.relationship.value} {target_node.name}",
            }
            if rel.file:
                relation["temporal_details"] = f"{rel.file}:{rel.line}" if rel.line else rel.file

            relations.append(relation)

        if not relations:
            return None

        return {
            "entities": entities,
            "relations": relations,
        }

    def estimate_payload_size(
        self,
        graph_payload: dict[str, Any],
    ) -> dict[str, int]:
        """
        Check payload against HydraDB limits before sending.
        Returns stats dict.
        """
        total_entities = sum(len(v.get("entities", {})) for v in graph_payload.values())
        total_relations = sum(len(v.get("relations", [])) for v in graph_payload.values())
        json_size = len(json.dumps(graph_payload))

        return {
            "total_entities": total_entities,
            "total_relations": total_relations,
            "json_size_bytes": json_size,
            "graph_entries": len(graph_payload),
        }
