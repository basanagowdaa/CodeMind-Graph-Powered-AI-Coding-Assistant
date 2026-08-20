"""
analyzer/extractors/entity_extractor.py
Converts ParsedFile objects into CodeMind Node objects.

Produces nodes of type: File, Function, Class, API, Test
Each node gets a stable deterministic ID so ingestion is idempotent.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from ..parsers.python_parser import ParsedFile, ParsedFunction, ParsedClass
from backend.models.graph_models import Node, NodeType

logger = logging.getLogger(__name__)

# Maximum source code length stored per entity (characters)
MAX_SOURCE_LENGTH = 2000


def _stable_id(entity_type: str, name: str, file_path: str, line: int = 0) -> str:
    """
    Generate a stable, deterministic ID for a code entity.
    Format: type:name:file_hash[:line]
    Uses a short hash of the file path to keep IDs short but unique across files.
    """
    file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
    base = f"{entity_type.lower()}:{name}:{file_hash}"
    if line:
        base += f":{line}"
    return base


class EntityExtractor:
    """
    Converts parsed Python files into graph Node objects.
    One EntityExtractor instance is reused across all files in a repo.
    """

    def extract_from_file(self, parsed: ParsedFile) -> list[Node]:
        """
        Extract all entities (nodes) from a parsed Python file.
        Returns a list of Node objects ready for graph_builder.py.
        """
        nodes: list[Node] = []

        # ── File node ─────────────────────────────────────────────────────
        file_node = self._make_file_node(parsed)
        nodes.append(file_node)

        # ── Class nodes ────────────────────────────────────────────────────
        for cls in parsed.classes:
            class_node = self._make_class_node(cls, parsed.relative_path)
            nodes.append(class_node)

        # ── Function / method / API / test nodes ───────────────────────────
        for func in parsed.functions:
            func_node = self._make_function_node(func, parsed.relative_path)
            nodes.append(func_node)

        return nodes

    # ── Node factories ─────────────────────────────────────────────────────

    def _make_file_node(self, parsed: ParsedFile) -> Node:
        """Create a File node from a parsed file."""
        _, filename = parsed.relative_path.rsplit("/", 1) if "/" in parsed.relative_path else ("", parsed.relative_path)
        return Node(
            id=_stable_id("file", parsed.module_path, parsed.relative_path),
            type=NodeType.FILE,
            name=parsed.relative_path,
            file=parsed.relative_path,
            line=1,
            metadata={
                "module_path": parsed.module_path,
                "line_count": parsed.line_count,
                "has_parse_errors": parsed.has_errors,
                "function_count": len(parsed.functions),
                "class_count": len(parsed.classes),
            },
            source_code=parsed.source_code[:MAX_SOURCE_LENGTH],
        )

    def _make_class_node(self, cls: ParsedClass, file_path: str) -> Node:
        """Create a Class node from a parsed class definition."""
        return Node(
            id=_stable_id("class", cls.name, file_path, cls.line),
            type=NodeType.CLASS,
            name=cls.name,
            file=file_path,
            line=cls.line,
            metadata={
                "method_count": len(cls.methods),
            },
            base_classes=cls.base_classes,
            decorators=cls.decorators,
            docstring=cls.docstring,
            source_code=cls.source_code[:MAX_SOURCE_LENGTH],
        )

    def _make_function_node(self, func: ParsedFunction, file_path: str) -> Node:
        """
        Create a Function, API, or Test node from a parsed function definition.

        Priority:
          1. If it's a route decorator → API node
          2. If name starts with test_ → Test node
          3. Otherwise → Function node
        """
        if func.http_method and func.endpoint_path:
            node_type = NodeType.API
        elif func.is_test:
            node_type = NodeType.TEST
        else:
            node_type = NodeType.FUNCTION

        return Node(
            id=_stable_id(node_type.value, func.name, file_path, func.line),
            type=node_type,
            name=func.name,
            file=file_path,
            line=func.line,
            metadata={
                "is_method": func.is_method,
                "parent_class": func.parent_class or "",
                "call_count": len(func.calls),
            },
            parameters=func.parameters,
            return_type=func.return_annotation,
            docstring=func.docstring,
            source_code=func.source_code[:MAX_SOURCE_LENGTH],
            decorators=func.decorators,
            is_async=func.is_async,
            http_method=func.http_method,
            endpoint_path=func.endpoint_path,
        )
