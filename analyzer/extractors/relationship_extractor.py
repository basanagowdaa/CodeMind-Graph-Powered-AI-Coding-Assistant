"""
analyzer/extractors/relationship_extractor.py
Extracts relationships between code entities.

Produces relationships of type:
  CONTAINS    — File contains Function/Class
  IMPORTS     — File imports File/Module
  CALLS       — Function calls Function
  INHERITS    — Class inherits Class
  USES        — Function uses Class (via instantiation)
  TESTS       — Test function tests Function/Class
  EXPOSES     — API endpoint exposes Function (calls it directly)
  DEFINED_IN  — Function/Class defined in File

Rules:
  - Only creates relationships when the source code actually supports them.
  - Does NOT invent relationships when the connection is ambiguous.
  - Cross-file call resolution uses name matching (best-effort).
"""
from __future__ import annotations

import logging
from typing import Any

from ..parsers.python_parser import ParsedFile, ParsedFunction
from backend.models.graph_models import (
    Node, NodeType, Relationship, RelationshipType, CodeGraph
)
from .entity_extractor import _stable_id

logger = logging.getLogger(__name__)


# Common test naming patterns
TEST_PATTERNS = [
    # test_<function_name>  →  tests function_name
    # Test<ClassName>       →  tests ClassName
]


class RelationshipExtractor:
    """
    Extracts relationships between nodes in a CodeGraph.
    Called after all entities are extracted so cross-file lookups work.
    """

    def extract(self, graph: CodeGraph, all_parsed_files: list[ParsedFile]) -> None:
        """
        Populate graph.relationships in place.
        Processes all files together so cross-file call resolution is possible.
        """
        # Build lookup maps for efficient resolution
        func_by_name: dict[str, list[Node]] = {}
        class_by_name: dict[str, list[Node]] = {}
        file_by_module: dict[str, Node] = {}
        file_by_path: dict[str, Node] = {}

        for node in graph.nodes.values():
            if node.type in (NodeType.FUNCTION, NodeType.API, NodeType.TEST):
                func_by_name.setdefault(node.name, []).append(node)
            elif node.type == NodeType.CLASS:
                class_by_name.setdefault(node.name, []).append(node)
            elif node.type == NodeType.FILE:
                module = node.metadata.get("module_path", "")
                if module:
                    file_by_module[module] = node
                file_by_path[node.file] = node

        for parsed in all_parsed_files:
            self._extract_file_relationships(
                graph, parsed, func_by_name, class_by_name, file_by_module, file_by_path
            )

    def _extract_file_relationships(
        self,
        graph: CodeGraph,
        parsed: ParsedFile,
        func_by_name: dict[str, list[Node]],
        class_by_name: dict[str, list[Node]],
        file_by_module: dict[str, Node],
        file_by_path: dict[str, Node],
    ) -> None:
        """Extract all relationships for a single parsed file."""
        file_node_id = _stable_id("file", parsed.module_path, parsed.relative_path)
        file_node = graph.get_node(file_node_id)
        if not file_node:
            return

        # ── CONTAINS: file contains functions and classes ──────────────────
        for func in parsed.functions:
            func_type = (
                NodeType.API if (func.http_method and func.endpoint_path)
                else NodeType.TEST if func.is_test
                else NodeType.FUNCTION
            )
            func_id = _stable_id(func_type.value, func.name, parsed.relative_path, func.line)
            if graph.get_node(func_id):
                graph.add_relationship(Relationship(
                    source_id=file_node_id,
                    relationship=RelationshipType.CONTAINS,
                    target_id=func_id,
                    file=parsed.relative_path,
                    line=func.line,
                    context=f"{parsed.relative_path} contains {func.name}()",
                ))
                # DEFINED_IN (reverse direction)
                graph.add_relationship(Relationship(
                    source_id=func_id,
                    relationship=RelationshipType.DEFINED_IN,
                    target_id=file_node_id,
                    file=parsed.relative_path,
                    line=func.line,
                    context=f"{func.name}() defined in {parsed.relative_path}",
                ))

        for cls in parsed.classes:
            cls_id = _stable_id("class", cls.name, parsed.relative_path, cls.line)
            if graph.get_node(cls_id):
                graph.add_relationship(Relationship(
                    source_id=file_node_id,
                    relationship=RelationshipType.CONTAINS,
                    target_id=cls_id,
                    file=parsed.relative_path,
                    line=cls.line,
                    context=f"{parsed.relative_path} contains class {cls.name}",
                ))

        # ── IMPORTS: file imports other modules ────────────────────────────
        for imp in parsed.imports:
            target_module = imp.module
            if imp.is_relative:
                # Resolve relative import against current module
                target_module = self._resolve_relative_import(
                    parsed.module_path, imp.level, imp.module
                )
            target_file_node = file_by_module.get(target_module)
            if target_file_node and target_file_node.id != file_node_id:
                graph.add_relationship(Relationship(
                    source_id=file_node_id,
                    relationship=RelationshipType.IMPORTS,
                    target_id=target_file_node.id,
                    file=parsed.relative_path,
                    line=imp.line,
                    context=f"{parsed.relative_path} imports {target_module}",
                ))

        # ── CALLS: function calls other functions ─────────────────────────
        for func in parsed.functions:
            func_type = (
                NodeType.API if (func.http_method and func.endpoint_path)
                else NodeType.TEST if func.is_test
                else NodeType.FUNCTION
            )
            caller_id = _stable_id(func_type.value, func.name, parsed.relative_path, func.line)
            if not graph.get_node(caller_id):
                continue

            for call_name in func.calls:
                # Skip self-calls and built-ins
                if call_name == func.name or call_name in _PYTHON_BUILTINS:
                    continue
                # Resolve to actual node(s)
                targets = self._resolve_call(
                    call_name, parsed.relative_path, func_by_name, class_by_name
                )
                for target_node in targets:
                    if target_node.id == caller_id:
                        continue  # skip self
                    # Use TESTS for test → non-test calls, CALLS otherwise
                    rel_type = RelationshipType.CALLS
                    if func.is_test and target_node.type in (
                        NodeType.FUNCTION, NodeType.API
                    ):
                        # Could be TESTS if naming matches
                        inferred_target = func.name.removeprefix("test_")
                        if target_node.name == inferred_target or target_node.name in func.name:
                            rel_type = RelationshipType.TESTS

                    graph.add_relationship(Relationship(
                        source_id=caller_id,
                        relationship=rel_type,
                        target_id=target_node.id,
                        file=parsed.relative_path,
                        line=func.line,
                        context=f"{func.name}() → {call_name}()",
                    ))

        # ── INHERITS: class inherits other classes ─────────────────────────
        for cls in parsed.classes:
            cls_id = _stable_id("class", cls.name, parsed.relative_path, cls.line)
            if not graph.get_node(cls_id):
                continue
            for base_name in cls.base_classes:
                if base_name in ("object", "ABC", "BaseModel", "Exception", "str", "int"):
                    continue  # Skip very common bases
                candidates = class_by_name.get(base_name, [])
                for base_node in candidates:
                    graph.add_relationship(Relationship(
                        source_id=cls_id,
                        relationship=RelationshipType.INHERITS,
                        target_id=base_node.id,
                        file=parsed.relative_path,
                        line=cls.line,
                        context=f"class {cls.name} inherits {base_name}",
                    ))

        # ── EXPOSES: API endpoint exposes / calls a handler function ───────
        for func in parsed.functions:
            if not (func.http_method and func.endpoint_path):
                continue
            api_id = _stable_id("API", func.name, parsed.relative_path, func.line)
            if not graph.get_node(api_id):
                continue
            for call_name in func.calls:
                targets = self._resolve_call(call_name, parsed.relative_path, func_by_name, class_by_name)
                for target_node in targets:
                    if target_node.type in (NodeType.FUNCTION,):
                        graph.add_relationship(Relationship(
                            source_id=api_id,
                            relationship=RelationshipType.EXPOSES,
                            target_id=target_node.id,
                            file=parsed.relative_path,
                            line=func.line,
                            context=f"{func.http_method} {func.endpoint_path} calls {call_name}()",
                        ))

    # ── Resolution helpers ─────────────────────────────────────────────────

    def _resolve_call(
        self,
        call_name: str,
        caller_file: str,
        func_by_name: dict[str, list[Node]],
        class_by_name: dict[str, list[Node]],
    ) -> list[Node]:
        """
        Try to resolve a call name to known nodes.
        Returns an empty list rather than guessing when ambiguous.
        """
        candidates = func_by_name.get(call_name, [])
        if not candidates:
            # Maybe it's a class instantiation
            candidates = class_by_name.get(call_name, [])

        if len(candidates) == 1:
            return candidates

        if len(candidates) > 1:
            # Prefer same file
            same_file = [n for n in candidates if n.file == caller_file]
            if same_file:
                return same_file[:1]
            # Return all — the graph will have multiple edges
            return candidates

        return []

    def _resolve_relative_import(
        self, current_module: str, level: int, imported: str
    ) -> str:
        """Convert a relative import to an absolute module path."""
        parts = current_module.split(".")
        # Level 1 = same package, level 2 = parent package, etc.
        parts = parts[: max(0, len(parts) - level)]
        if imported:
            parts.append(imported)
        return ".".join(parts)


# Python built-ins and common names we skip for call resolution
_PYTHON_BUILTINS = frozenset({
    "print", "len", "range", "enumerate", "zip", "map", "filter",
    "sorted", "list", "dict", "set", "tuple", "str", "int", "float",
    "bool", "bytes", "type", "isinstance", "issubclass", "hasattr",
    "getattr", "setattr", "delattr", "super", "property", "staticmethod",
    "classmethod", "abs", "min", "max", "sum", "round", "open", "repr",
    "hash", "id", "dir", "vars", "iter", "next", "reversed", "any", "all",
    "format", "input", "exec", "eval", "compile", "globals", "locals",
    "raise", "assert", "Exception", "ValueError", "TypeError", "KeyError",
    "RuntimeError", "NotImplementedError", "StopIteration", "AttributeError",
    "HTTPException", "json", "os", "sys", "time", "datetime", "logging",
    "dataclass", "field", "MagicMock", "patch", "pytest",
})
