"""
tests/test_impact_analysis.py
Unit tests for the ImpactService and CodeGraph BFS traversal.
Verifies structural "Before You Change It" calculations.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.graph.graph_builder import GraphBuilder
from backend.services.impact_service import ImpactService
from backend.hydra.retrieval import HydraRetrieval
from backend.models.graph_models import NodeType


@pytest.fixture
def demo_repo_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../demo-repository"))


@pytest.fixture
def demo_graph(demo_repo_path):
    builder = GraphBuilder()
    return builder.build_from_directory(demo_repo_path)


@pytest.fixture
def mock_hydra_retrieval() -> HydraRetrieval:
    mock = MagicMock(spec=HydraRetrieval)
    # Stub query_impact to return an empty RetrievalResult
    from backend.hydra.retrieval import RetrievalResult
    mock.query_impact.return_value = RetrievalResult(
        query="What could break?",
        chunks=[],
        dependency_paths=[],
        chunk_relations=[],
    )
    return mock


def test_impact_analysis_on_authenticate_user(demo_graph, mock_hydra_retrieval):
    """
    Verifies that calling impact analysis on authenticate_user finds
    all downstream callers, API endpoints, and pytest test functions.
    """
    service = ImpactService(mock_hydra_retrieval)

    # Find the authenticate_user node
    auth_user_nodes = [n for n in demo_graph.nodes.values() if n.name == "authenticate_user"]
    assert len(auth_user_nodes) == 1
    auth_user = auth_user_nodes[0]

    response = service.analyze_impact(
        graph=demo_graph,
        hydra_database="test-db",
        entity_id=auth_user.id,
        entity_name=auth_user.name,
        entity_type=auth_user.type.value,
    )

    assert response.entity_id == auth_user.id
    assert response.entity_name == "authenticate_user"

    # authenticate_user is called by:
    # 1. login api endpoint (api/routes.py)
    # 2. test_authenticate_user_* tests (tests/test_auth.py)
    
    # Assert that we found the callers, tests, or APIs
    assert len(response.apis) >= 1
    assert any(a.name == "login" for a in response.apis)

    assert len(response.tests) >= 1
    assert any("test_authenticate_user" in t.name for t in response.tests)

    assert response.total_impacted > 0
    assert response.blast_radius in ("medium", "high", "critical")


def test_dependency_chain_tracing(demo_graph, mock_hydra_retrieval):
    """Verifies that we can find dependency paths between two arbitrary functions."""
    service = ImpactService(mock_hydra_retrieval)

    # Path from login (API) to authenticate_user (Function)
    login_node = [n for n in demo_graph.nodes.values() if n.name == "login" and n.type == NodeType.API][0]
    auth_user_node = [n for n in demo_graph.nodes.values() if n.name == "authenticate_user"][0]


    paths = service.get_dependency_chain(
        graph=demo_graph,
        from_id=login_node.id,
        to_id=auth_user_node.id,
    )

    assert paths is not None
    assert len(paths) >= 1
    # Check that the path goes from login to authenticate_user
    assert paths[0][0] == login_node.id
    assert paths[0][-1] == auth_user_node.id
