"""
analyzer/graph/graph_builder.py
Builds a normalized CodeGraph from parsed Python files.

Pipeline:
  1. Parse all .py files in the repository
  2. Extract entities (nodes) from each file
  3. Extract relationships between nodes
  4. Update statistics
  5. Return a complete CodeGraph ready for HydraDB ingestion
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ..parsers.python_parser import PythonParser, ParsedFile
from ..extractors.entity_extractor import EntityExtractor
from ..extractors.relationship_extractor import RelationshipExtractor
from backend.models.graph_models import CodeGraph, Node, NodeType

logger = logging.getLogger(__name__)

# Files / directories to ignore during analysis (security + relevance)
IGNORE_DIRS = frozenset({
    "__pycache__", ".git", ".hg", ".svn", "node_modules", ".venv", "venv",
    "env", ".env", "dist", "build", "*.egg-info", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "site-packages", ".tox", "coverage_html_report",
})

IGNORE_FILE_PATTERNS = frozenset({
    "setup.py", "setup.cfg", "pyproject.toml",  # keep these for context but skip parsing
})

# Maximum file size to parse (bytes)
MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB


class GraphBuilder:
    """
    Orchestrates the full parse → extract → graph pipeline for a repository.
    """

    def __init__(self) -> None:
        self._parser = PythonParser()
        self._entity_extractor = EntityExtractor()
        self._relationship_extractor = RelationshipExtractor()

    def build_from_directory(
        self,
        repo_root: str,
        repository_url: str = "",
        repository_name: str = "",
        max_files: int = 2000,
    ) -> CodeGraph:
        """
        Analyze all Python files in a directory and build a CodeGraph.

        Args:
            repo_root: Absolute path to the repository root.
            repository_url: Original GitHub URL (stored in graph metadata).
            repository_name: Human-readable name.
            max_files: Safety limit — stop after this many .py files.

        Returns:
            A fully populated CodeGraph.
        """
        if not repository_name:
            repository_name = os.path.basename(repo_root.rstrip("/\\"))

        graph = CodeGraph(
            repository_url=repository_url,
            repository_name=repository_name,
        )

        logger.info("Scanning repository: %s", repo_root)
        py_files = self._discover_python_files(repo_root, max_files=max_files)
        logger.info("Found %d Python files to analyze", len(py_files))

        # Phase 1: Parse all files
        parsed_files: list[ParsedFile] = []
        for file_path in py_files:
            parsed = self._parser.parse_file(file_path, repo_root)
            if parsed is not None:
                parsed_files.append(parsed)

        logger.info("Successfully parsed %d files", len(parsed_files))

        # Phase 2: Extract entities (nodes) from each file
        for parsed in parsed_files:
            nodes = self._entity_extractor.extract_from_file(parsed)
            for node in nodes:
                graph.add_node(node)

        logger.info("Extracted %d nodes", len(graph.nodes))

        # Phase 3: Extract relationships between nodes
        self._relationship_extractor.extract(graph, parsed_files)

        logger.info("Extracted %d relationships", len(graph.relationships))

        # Phase 4: Update statistics
        graph.update_statistics()

        logger.info(
            "Graph built: %d files, %d functions, %d classes, %d APIs, %d tests, %d relationships",
            graph.file_count, graph.function_count, graph.class_count,
            graph.api_count, graph.test_count, graph.relationship_count,
        )

        return graph

    # ── File discovery ─────────────────────────────────────────────────────

    def _discover_python_files(
        self, root: str, max_files: int = 2000
    ) -> list[str]:
        """
        Find all .py files in the repository, respecting ignore rules.
        Returns absolute paths sorted for deterministic ordering.
        """
        found: list[str] = []
        root_path = Path(root)

        try:
            for path in sorted(root_path.rglob("*.py")):
                if len(found) >= max_files:
                    logger.warning(
                        "Hit max_files limit (%d). Truncating file list.", max_files
                    )
                    break

                # Check against ignore list
                parts = set(path.parts)
                if any(ignore in parts for ignore in IGNORE_DIRS):
                    continue

                # Size limit
                try:
                    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                        logger.debug("Skipping large file: %s", path)
                        continue
                except OSError:
                    continue

                found.append(str(path))
        except PermissionError as exc:
            logger.error("Permission denied scanning repository: %s", exc)

        return found

    def get_most_connected_nodes(
        self, graph: CodeGraph, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """
        Return the top-N most-connected nodes by total relationship count.
        Used for the Overview dashboard.
        """
        degree: dict[str, int] = {}
        for rel in graph.relationships:
            degree[rel.source_id] = degree.get(rel.source_id, 0) + 1
            degree[rel.target_id] = degree.get(rel.target_id, 0) + 1

        ranked = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_n]
        result = []
        for node_id, count in ranked:
            node = graph.get_node(node_id)
            if node:
                result.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.type.value,
                    "file": node.file,
                    "connection_count": count,
                })
        return result

    def get_high_impact_functions(
        self, graph: CodeGraph, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """
        Return functions with the most callers (high blast radius if changed).
        Used for the Overview dashboard.
        """
        caller_count: dict[str, int] = {}
        from backend.models.graph_models import RelationshipType
        for rel in graph.relationships:
            if rel.relationship in (RelationshipType.CALLS, RelationshipType.TESTS):
                caller_count[rel.target_id] = caller_count.get(rel.target_id, 0) + 1

        ranked = sorted(caller_count.items(), key=lambda x: x[1], reverse=True)[:top_n]
        result = []
        for node_id, count in ranked:
            node = graph.get_node(node_id)
            if node and node.type in (NodeType.FUNCTION, NodeType.API):
                result.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.type.value,
                    "file": node.file,
                    "caller_count": count,
                })
        return result
