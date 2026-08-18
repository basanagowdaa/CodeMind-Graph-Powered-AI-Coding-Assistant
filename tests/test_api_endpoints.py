"""
tests/test_api_endpoints.py
Integration tests for all FastAPI endpoints.
Tests endpoints in isolation by mocking service layer dependencies.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.main import app
from backend.models.graph_models import CodeGraph

client = TestClient(app)


# ── Health check ────────────────────────────────────────────────────────────

def test_health_endpoint_connected():
    """Verify health endpoint returns connected when verify_connection succeeds."""
    with patch("backend.main.get_hydra_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.verify_connection.return_value = True
        mock_client.list_databases.return_value = ["db1", "db2"]
        mock_get_client.return_value = mock_client

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["databases_count"] == 2


def test_health_endpoint_disconnected():
    """Verify health endpoint returns disconnected when verify_connection fails."""
    with patch("backend.main.get_hydra_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.verify_connection.side_effect = Exception("Auth failed")
        mock_get_client.return_value = mock_client

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert "Auth failed" in data["message"]


# ── Repository Analysis ─────────────────────────────────────────────────────

@patch("backend.api.repository._service")
def test_analyze_repository_trigger(mock_service):
    """Verify trigger endpoint queues analysis and returns queued status."""
    mock_service.repository_id_from_url.return_value = "repo-id-123"
    mock_service.get_job.return_value = None

    response = client.post(
        "/api/repository/analyze",
        json={"source": "https://github.com/test/repo", "force_reanalysis": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == "repo-id-123"
    assert data["status"] == "cloning"
    assert "Queued" in data["message"]


@patch("backend.api.repository._service")
def test_get_analysis_status_success(mock_service):
    """Verify status endpoint returns job state."""
    from backend.services.analysis_service import AnalysisJob, AnalysisStatus
    job = AnalysisJob(
        repository_id="repo-123",
        repository_name="repo",
        repository_url="http://git",
        status=AnalysisStatus.READY,
        progress=100,
        message="Done",
        statistics={"files": 5},
    )
    mock_service.get_job.return_value = job

    response = client.get("/api/repository/repo-123/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["progress"] == 100
    assert data["statistics"]["files"] == 5


# ── Graph Endpoint ──────────────────────────────────────────────────────────

@patch("backend.api.graph._service")
def test_get_graph_success(mock_service):
    """Verify graph visualization data endpoint."""
    graph = CodeGraph(repository_url="", repository_name="test")
    # Add dummy file node
    from backend.models.graph_models import Node, NodeType
    graph.add_node(Node(id="file:1", type=NodeType.FILE, name="file.py"))
    mock_service.get_graph.return_value = graph

    response = client.get("/api/graph/repo-123")
    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == "repo-123"
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == "file:1"


# ── Ask Endpoint ────────────────────────────────────────────────────────────

@patch("backend.api.ask._analysis_service")
@patch("backend.api.ask._hydra_client")
@patch("backend.api.ask._ai_service")
def test_ask_codemind_success(mock_ai, mock_hydra, mock_analysis):
    """Verify Q&A endpoint correctly parses and returns grounded response."""
    mock_analysis.get_hydra_database.return_value = "db-name"
    mock_hydra.list_databases.return_value = ["db-name"]
    
    from backend.models.api_models import AskResponse
    mock_ai.answer_question.return_value = AskResponse(
        question="What is this?",
        answer="Grounded answer",
        evidence=[],
        dependency_paths=[],
        hydradb_chunks=2,
        hydradb_graph_paths=1,
    )

    response = client.post(
        "/api/ask",
        json={"repository_id": "repo-123", "question": "What calls main?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Grounded answer"
    assert data["hydradb_chunks"] == 2
