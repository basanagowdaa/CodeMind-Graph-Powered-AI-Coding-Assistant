"""
backend/models/graph_models.py
Normalized internal graph model for CodeMind.

These models are the internal representation — independent of HydraDB's format.
The hydra_mapper.py module converts these to HydraDB's BYOG (graph_payload) format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    REPOSITORY = "Repository"
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    API = "API"
    TEST = "Test"
    MODULE = "Module"
    SERVICE = "Service"
    DATABASE = "Database"


class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"      # File contains Function/Class
    IMPORTS = "IMPORTS"        # File imports File/Module
    CALLS = "CALLS"            # Function calls Function
    INHERITS = "INHERITS"      # Class inherits Class
    USES = "USES"              # Function uses Class
    TESTS = "TESTS"            # Test tests Function/Class
    EXPOSES = "EXPOSES"        # API exposes Function
    DEPENDS_ON = "DEPENDS_ON"  # Service depends on Service
    DEFINED_IN = "DEFINED_IN"  # Function defined in File
    ACCESSES = "ACCESSES"      # Function accesses Database


@dataclass
class Node:
    """A code entity in the graph."""
    id: str                          # Stable unique ID (e.g. "func:auth:authenticate_user")
    type: NodeType
    name: str
    file: str = ""                   # Relative path within repository
    line: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Type-specific fields
    parameters: list[str] = field(default_factory=list)
    return_type: str = ""
    docstring: str = ""
    source_code: str = ""
    base_classes: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    http_method: str = ""            # For API nodes: GET, POST, etc.
    endpoint_path: str = ""          # For API nodes: /login, /users/{id}

    def __hash__(self) -> int:
        return hash(self.id)

    def display_label(self) -> str:
        """Short label for graph visualization."""
        if self.type == NodeType.API:
            return f"{self.http_method} {self.endpoint_path}"
        return self.name

    def to_app_knowledge_item(self, database: str) -> dict[str, Any]:
        """
        Convert to an app_knowledge item for HydraDB ingestion.
        The text body contains the source code + context for semantic search.
        """
        body_parts = [f"{self.type.value}: {self.name}"]
        if self.file:
            body_parts.append(f"File: {self.file}")
        if self.line:
            body_parts.append(f"Line: {self.line}")
        if self.docstring:
            body_parts.append(f"Docstring: {self.docstring}")
        if self.source_code:
            body_parts.append(f"Source:\n{self.source_code}")
        if self.parameters:
            body_parts.append(f"Parameters: {', '.join(self.parameters)}")
        if self.return_type:
            body_parts.append(f"Returns: {self.return_type}")
        if self.base_classes:
            body_parts.append(f"Inherits: {', '.join(self.base_classes)}")
        if self.http_method and self.endpoint_path:
            body_parts.append(f"Endpoint: {self.http_method} {self.endpoint_path}")

        body = "\n".join(body_parts)

        return {
            "id": self.id,
            "database": database,
            "collection": "default",
            "title": f"{self.type.value}: {self.name}",
            "type": "codemind",
            "kind": "knowledge_base",
            "provider": "codemind",
            "external_id": self.id,
            "fields": {
                "kind": "knowledge_base",
                "title": f"{self.type.value}: {self.name}",
                "body": body,
            },
            "metadata": {
                "entity_type": self.type.value,
                "file": self.file,
                "name": self.name,
            },
            "additional_metadata": {
                "line": self.line,
                "parameters": self.parameters,
                "return_type": self.return_type,
                "is_async": self.is_async,
                "http_method": self.http_method,
                "endpoint_path": self.endpoint_path,
                **{k: v for k, v in self.metadata.items()},
            },
        }


@dataclass
class Relationship:
    """
    A directed relationship between two nodes.
    Only created when the source code actually supports the relationship.
    """
    source_id: str
    relationship: RelationshipType
    target_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    file: str = ""
    line: int = 0
    context: str = ""   # Human-readable description of why this relationship exists

    def __hash__(self) -> int:
        return hash((self.source_id, self.relationship, self.target_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Relationship):
            return NotImplemented
        return (
            self.source_id == other.source_id
            and self.relationship == other.relationship
            and self.target_id == other.target_id
        )


@dataclass
class CodeGraph:
    """
    The complete normalized graph for a repository.
    Built by graph_builder.py, stored in HydraDB via hydra_mapper.py.
    """
    repository_url: str
    repository_name: str
    nodes: dict[str, Node] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)

    # Statistics — populated during build
    file_count: int = 0
    function_count: int = 0
    class_count: int = 0
    api_count: int = 0
    test_count: int = 0
    import_count: int = 0
    relationship_count: int = 0

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_relationship(self, rel: Relationship) -> None:
        if rel not in self.relationships:
            self.relationships.append(rel)

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_callers(self, node_id: str) -> list[Node]:
        """Return all nodes that CALL this node."""
        return [
            self.nodes[r.source_id]
            for r in self.relationships
            if r.relationship == RelationshipType.CALLS
            and r.target_id == node_id
            and r.source_id in self.nodes
        ]

    def get_callees(self, node_id: str) -> list[Node]:
        """Return all nodes this node CALLS."""
        return [
            self.nodes[r.target_id]
            for r in self.relationships
            if r.relationship == RelationshipType.CALLS
            and r.source_id == node_id
            and r.target_id in self.nodes
        ]

    def get_tests_for(self, node_id: str) -> list[Node]:
        """Return all test nodes that test this node."""
        return [
            self.nodes[r.source_id]
            for r in self.relationships
            if r.relationship == RelationshipType.TESTS
            and r.target_id == node_id
            and r.source_id in self.nodes
        ]

    def get_importers(self, node_id: str) -> list[Node]:
        """Return all files that import this node."""
        return [
            self.nodes[r.source_id]
            for r in self.relationships
            if r.relationship == RelationshipType.IMPORTS
            and r.target_id == node_id
            and r.source_id in self.nodes
        ]

    def get_downstream_impact(
        self, node_id: str, max_depth: int = 5
    ) -> dict[str, list[Node]]:
        """
        BFS/DFS to find all nodes that could be affected if node_id changes.
        Returns categorized impact: callers, test files, API endpoints, files.
        """
        visited: set[str] = set()
        impact: dict[str, list[Node]] = {
            "callers": [],
            "tests": [],
            "apis": [],
            "files": [],
            "classes": [],
        }

        def traverse(nid: str, depth: int) -> None:
            if depth > max_depth or nid in visited:
                return
            visited.add(nid)
            node = self.nodes.get(nid)
            if not node:
                return

            # Find everything that references this node
            for rel in self.relationships:
                if rel.target_id == nid and rel.source_id not in visited:
                    src = self.nodes.get(rel.source_id)
                    if src:
                        if src.type == NodeType.TEST:
                            if src not in impact["tests"]:
                                impact["tests"].append(src)
                        elif src.type == NodeType.API:
                            if src not in impact["apis"]:
                                impact["apis"].append(src)
                        elif src.type == NodeType.FUNCTION:
                            if src not in impact["callers"]:
                                impact["callers"].append(src)
                        elif src.type == NodeType.CLASS:
                            if src not in impact["classes"]:
                                impact["classes"].append(src)
                        elif src.type == NodeType.FILE:
                            if src not in impact["files"]:
                                impact["files"].append(src)
                        traverse(rel.source_id, depth + 1)

        traverse(node_id, 0)
        return impact

    def update_statistics(self) -> None:
        """Recount entities from the nodes dict."""
        type_counts = {t: 0 for t in NodeType}
        for node in self.nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1

        self.file_count = type_counts[NodeType.FILE]
        self.function_count = type_counts[NodeType.FUNCTION]
        self.class_count = type_counts[NodeType.CLASS]
        self.api_count = type_counts[NodeType.API]
        self.test_count = type_counts[NodeType.TEST]
        self.relationship_count = len(self.relationships)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses."""
        return {
            "repository_url": self.repository_url,
            "repository_name": self.repository_name,
            "statistics": {
                "files": self.file_count,
                "functions": self.function_count,
                "classes": self.class_count,
                "apis": self.api_count,
                "tests": self.test_count,
                "relationships": self.relationship_count,
            },
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "name": n.name,
                    "file": n.file,
                    "line": n.line,
                    "label": n.display_label(),
                    "metadata": n.metadata,
                }
                for n in self.nodes.values()
            ],
            "relationships": [
                {
                    "source": r.source_id,
                    "relationship": r.relationship.value,
                    "target": r.target_id,
                    "context": r.context,
                }
                for r in self.relationships
            ],
        }
