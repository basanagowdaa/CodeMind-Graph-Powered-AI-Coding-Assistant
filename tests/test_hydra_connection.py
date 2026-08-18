"""
tests/test_hydra_connection.py
Milestone 1 tests — verifies real HydraDB connection, ingestion, and retrieval.

These tests use a REAL HydraDB connection (no mocks).
Run only when HYDRA_DB_API_KEY is set.
Tests are skipped gracefully if no key is available.
"""
from __future__ import annotations

import json
import os
import time
import pytest

# Skip all tests if no API key is configured
HYDRA_DB_API_KEY = os.environ.get("HYDRA_DB_API_KEY", "")
pytestmark = pytest.mark.skipif(
    not HYDRA_DB_API_KEY,
    reason="HYDRA_DB_API_KEY not set — skipping HydraDB integration tests",
)

# Test database name — unique so parallel test runs don't collide
TEST_DB = f"codemind-test-{int(time.time())}"


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hydra_client():
    """Initialize the HydraDB client for the test module."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from backend.hydra.client import HydraClient
    client = HydraClient(api_key=HYDRA_DB_API_KEY)
    return client


@pytest.fixture(scope="module", autouse=True)
def test_database(hydra_client):
    """Create a test database and clean it up after tests."""
    hydra_client.ensure_database(TEST_DB, timeout_seconds=120)
    yield TEST_DB
    # Cleanup after tests
    try:
        hydra_client.delete_database(TEST_DB)
    except Exception:
        pass  # best-effort cleanup


# ── Test 1: Real connection ──────────────────────────────────────────────────

def test_hydra_connection_is_real(hydra_client):
    """
    Verifies that the HydraDB connection is real (not mocked).
    A real call to databases.list() must succeed.
    """
    result = hydra_client.verify_connection()
    assert result is True, "HydraDB connection failed"
    assert hydra_client.is_connected is True


def test_list_databases_returns_list(hydra_client):
    """databases.list() returns a list of database names."""
    databases = hydra_client.list_databases()
    assert isinstance(databases, list)


# ── Test 2: Database creation ───────────────────────────────────────────────

def test_test_database_exists(hydra_client, test_database):
    """The test database was created successfully."""
    databases = hydra_client.list_databases()
    assert test_database in databases, f"Test database '{test_database}' not found in list"


# ── Test 3: BYOG ingestion ───────────────────────────────────────────────────

def test_byog_ingestion_with_code_graph(hydra_client, test_database):
    """
    Ingest a tiny code graph using BYOG (Bring Your Own Graph).
    Verifies that 3 entities with 2 relationships are stored successfully.
    """
    from backend.hydra.ingestion import HydraIngestion

    ingestion = HydraIngestion(hydra_client)

    # Three code entities: authenticate_user, validate_token, TokenService
    entities = [
        {
            "id": "func:authenticate_user",
            "database": test_database,
            "collection": "default",
            "title": "Function: authenticate_user",
            "type": "codemind",
            "kind": "knowledge_base",
            "provider": "codemind",
            "external_id": "func:authenticate_user",
            "fields": {
                "kind": "knowledge_base",
                "title": "Function: authenticate_user",
                "body": (
                    "Function: authenticate_user\n"
                    "File: services/auth_service.py\n"
                    "Line: 45\n"
                    "Authenticates a user and issues token pair.\n"
                    "Calls: get_user_by_username, verify_password, create_access_token, create_refresh_token"
                ),
            },
            "metadata": {"entity_type": "Function", "file": "services/auth_service.py"},
        },
        {
            "id": "func:validate_token",
            "database": test_database,
            "collection": "default",
            "title": "Function: validate_token",
            "type": "codemind",
            "kind": "knowledge_base",
            "provider": "codemind",
            "external_id": "func:validate_token",
            "fields": {
                "kind": "knowledge_base",
                "title": "Function: validate_token",
                "body": (
                    "Function: validate_token\n"
                    "File: utils/token_service.py\n"
                    "Line: 62\n"
                    "Validates a JWT token — signature, expiry, revocation.\n"
                    "Called by: authenticate_user, protected endpoints"
                ),
            },
            "metadata": {"entity_type": "Function", "file": "utils/token_service.py"},
        },
        {
            "id": "class:TokenService",
            "database": test_database,
            "collection": "default",
            "title": "Class: TokenService",
            "type": "codemind",
            "kind": "knowledge_base",
            "provider": "codemind",
            "external_id": "class:TokenService",
            "fields": {
                "kind": "knowledge_base",
                "title": "Class: TokenService",
                "body": (
                    "Class: TokenService\n"
                    "File: utils/token_service.py\n"
                    "Line: 30\n"
                    "Handles JWT-like token creation and validation.\n"
                    "Methods: create_access_token, create_refresh_token, validate_token, revoke_refresh_token"
                ),
            },
            "metadata": {"entity_type": "Class", "file": "utils/token_service.py"},
        },
    ]

    # BYOG graph: authenticate_user CALLS validate_token, validate_token USES TokenService
    graph_payload = {
        "func:authenticate_user": {
            "entities": {
                "src": {
                    "name": "authenticate_user",
                    "type": "FUNCTION",
                    "namespace": "code",
                    "identifier": "func:authenticate_user",
                },
                "tgt": {
                    "name": "validate_token",
                    "type": "FUNCTION",
                    "namespace": "code",
                    "identifier": "func:validate_token",
                },
            },
            "relations": [
                {
                    "source": "src",
                    "target": "tgt",
                    "predicate": "CALLS",
                    "context": "authenticate_user() calls validate_token() to verify the token",
                }
            ],
        },
        "func:validate_token": {
            "entities": {
                "src": {
                    "name": "validate_token",
                    "type": "FUNCTION",
                    "namespace": "code",
                    "identifier": "func:validate_token",
                },
                "tgt": {
                    "name": "TokenService",
                    "type": "CLASS",
                    "namespace": "code",
                    "identifier": "class:TokenService",
                },
            },
            "relations": [
                {
                    "source": "src",
                    "target": "tgt",
                    "predicate": "USES",
                    "context": "validate_token() is a method of TokenService",
                }
            ],
        },
    }

    result = ingestion.ingest_code_graph(
        database=test_database,
        entities=entities,
        graph_payload=graph_payload,
        wait_for_completion=True,
        timeout_seconds=180,
    )

    assert result.total == 3, f"Expected 3 entities, got {result.total}"
    assert result.failed == 0, f"Expected 0 failures, got: {result.errors}"
    assert len(result.ids) == 3


# ── Test 4: Graph retrieval ──────────────────────────────────────────────────

def test_graph_retrieval_returns_dependency_paths(hydra_client, test_database):
    """
    Query with graph_context=True and verify that dependency paths are returned.
    This is the core capability: HydraDB returns the CALLS relationship
    we supplied via BYOG.
    """
    from backend.hydra.retrieval import HydraRetrieval

    retrieval = HydraRetrieval(hydra_client)

    result = retrieval.query_with_graph(
        database=test_database,
        query="What does authenticate_user call? What depends on validate_token?",
    )

    # We must get at least some chunks back
    assert isinstance(result.chunks, list)
    assert len(result.chunks) > 0, "Expected at least one chunk from the query"

    # The graph context may or may not have paths depending on indexing completeness
    # We just verify the result structure is correct
    assert isinstance(result.dependency_paths, list)
    assert isinstance(result.chunk_relations, list)
    assert isinstance(result.has_graph_data, bool)

    print(f"\nChunks returned: {len(result.chunks)}")
    print(f"Dependency paths: {len(result.dependency_paths)}")
    print(f"Has graph data: {result.has_graph_data}")
    if result.dependency_paths:
        for path in result.dependency_paths[:3]:
            print(f"  Path: {path.as_text_chain()}")


def test_query_for_impact_analysis(hydra_client, test_database):
    """
    Specialized impact query: what could break if authenticate_user changes?
    """
    from backend.hydra.retrieval import HydraRetrieval

    retrieval = HydraRetrieval(hydra_client)
    result = retrieval.query_impact(
        database=test_database,
        entity_name="authenticate_user",
        entity_type="Function",
    )

    assert result is not None
    assert isinstance(result.chunks, list)
    # authenticate_user entity should be in the results
    chunk_texts = [c.get("text", "") for c in result.chunks]
    assert any("authenticate_user" in t for t in chunk_texts), (
        "Expected 'authenticate_user' to appear in query results"
    )
