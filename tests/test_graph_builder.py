"""
tests/test_graph_builder.py
Unit tests for the GraphBuilder, EntityExtractor, and RelationshipExtractor.
Verifies building a CodeGraph from the local demo-repository.
"""
from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.graph.graph_builder import GraphBuilder
from backend.models.graph_models import NodeType, RelationshipType


@pytest.fixture
def demo_repo_path() -> str:
    # Path to the demo repository in the workspace
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../demo-repository"))


def test_build_demo_repo_graph(demo_repo_path):
    """
    Verifies that GraphBuilder successfully parses the demo-repository,
    extracts all key nodes, and maps relationships correctly.
    """
    builder = GraphBuilder()
    graph = builder.build_from_directory(
        repo_root=demo_repo_path,
        repository_name="demo-repository",
    )

    # 1. Verify general statistics
    assert graph.file_count > 0
    assert graph.function_count > 0
    assert graph.class_count > 0
    assert graph.api_count > 0
    assert graph.test_count > 0
    assert graph.relationship_count > 0

    # 2. Verify specific nodes exist
    # Files
    auth_service_file = [n for n in graph.nodes.values() if n.type == NodeType.FILE and "auth_service" in n.name]
    assert len(auth_service_file) == 1

    # Classes
    auth_service_class = [n for n in graph.nodes.values() if n.type == NodeType.CLASS and n.name == "AuthService"]
    assert len(auth_service_class) == 1
    assert auth_service_class[0].file == "services/auth_service.py"

    # Functions
    auth_user_func = [n for n in graph.nodes.values() if n.type == NodeType.FUNCTION and n.name == "authenticate_user"]
    assert len(auth_user_func) == 1
    assert auth_user_func[0].file == "services/auth_service.py"

    # APIs
    login_api = [n for n in graph.nodes.values() if n.type == NodeType.API and n.endpoint_path == "/login"]
    assert len(login_api) == 1
    assert login_api[0].http_method == "POST"

    # Tests
    auth_tests = [n for n in graph.nodes.values() if n.type == NodeType.TEST and "test_authenticate_user" in n.name]
    assert len(auth_tests) >= 1

    # 3. Verify relationships
    # Check CONTAINS relationships
    contains_rels = [r for r in graph.relationships if r.relationship == RelationshipType.CONTAINS]
    assert len(contains_rels) > 0

    # Check DEFINED_IN relationships
    defined_in_rels = [r for r in graph.relationships if r.relationship == RelationshipType.DEFINED_IN]
    assert len(defined_in_rels) > 0

    # Check CALLS relationships (e.g. authenticate_user calls get_user_by_username)
    calls_rels = [r for r in graph.relationships if r.relationship == RelationshipType.CALLS]
    assert len(calls_rels) > 0

    # Check IMPORTS relationships
    imports_rels = [r for r in graph.relationships if r.relationship == RelationshipType.IMPORTS]
    assert len(imports_rels) > 0


def test_most_connected_nodes(demo_repo_path):
    """Verifies that degree calculation and dashboard metrics sorting works."""
    builder = GraphBuilder()
    graph = builder.build_from_directory(demo_repo_path)
    
    most_connected = builder.get_most_connected_nodes(graph, top_n=5)
    assert len(most_connected) > 0
    assert most_connected[0]["connection_count"] >= most_connected[-1]["connection_count"]


def test_high_impact_functions(demo_repo_path):
    """Verifies that high-impact caller metrics sorting works."""
    builder = GraphBuilder()
    graph = builder.build_from_directory(demo_repo_path)
    
    high_impact = builder.get_high_impact_functions(graph, top_n=5)
    assert len(high_impact) > 0
    assert "caller_count" in high_impact[0]
