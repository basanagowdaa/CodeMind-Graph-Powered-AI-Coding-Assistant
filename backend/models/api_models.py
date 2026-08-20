"""
backend/models/api_models.py
Pydantic request/response models for the CodeMind REST API.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ── Repository Analysis ─────────────────────────────────────────────────────

class AnalyzeRepositoryRequest(BaseModel):
    """Request to analyze a GitHub repository or local directory."""
    source: str = Field(
        ...,
        description="GitHub URL (https://github.com/owner/repo) or local directory path",
        examples=["https://github.com/tiangolo/fastapi"],
    )
    force_reanalysis: bool = Field(
        default=False,
        description="Re-analyze even if this repo was already analyzed",
    )


class AnalysisStatusResponse(BaseModel):
    """Current status of a repository analysis job."""
    repository_id: str
    repository_name: str
    repository_url: str
    status: str     # "analyzing" | "ingesting" | "ready" | "error"
    progress: int   # 0–100
    message: str
    statistics: dict[str, int] | None = None
    error: str | None = None


# ── Graph ────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the code graph for the frontend visualization."""
    id: str
    type: str
    name: str
    file: str
    line: int
    label: str
    connection_count: int = 0
    metadata: dict[str, Any] = {}


class GraphEdge(BaseModel):
    """A directed edge in the code graph."""
    source: str
    target: str
    relationship: str
    context: str = ""


class GraphResponse(BaseModel):
    """Full code graph for visualization."""
    repository_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    statistics: dict[str, int]


# ── Impact Analysis ──────────────────────────────────────────────────────────

class ImpactAnalysisRequest(BaseModel):
    """Request impact analysis for a specific code entity."""
    repository_id: str
    entity_id: str
    entity_name: str
    entity_type: str


class ImpactedEntity(BaseModel):
    """A code entity affected by the change."""
    id: str
    name: str
    type: str
    file: str
    line: int
    relationship: str    # How it's affected: CALLS, TESTS, IMPORTS, etc.
    impact_level: str    # "direct" | "transitive"
    confidence: float    # 0.0–1.0


class DependencyPathItem(BaseModel):
    """A single hop in a dependency path."""
    source: str
    predicate: str
    target: str
    context: str = ""


class ImpactAnalysisResponse(BaseModel):
    """Full impact analysis result for BEFORE YOU CHANGE IT."""
    repository_id: str
    entity_id: str
    entity_name: str
    entity_type: str

    # Categorized impact
    callers: list[ImpactedEntity]
    tests: list[ImpactedEntity]
    apis: list[ImpactedEntity]
    files: list[ImpactedEntity]
    classes: list[ImpactedEntity]

    # Graph-derived dependency paths (from HydraDB graph_context)
    dependency_paths: list[list[DependencyPathItem]]

    # Summary counts
    total_impacted: int
    blast_radius: str   # "low" | "medium" | "high" | "critical"

    # LLM-generated impact summary (if available)
    ai_summary: str | None = None

    # Source
    graph_source: str = "hydradb"   # Always "hydradb" — never "mock"
    hydradb_query_paths: int = 0    # Number of paths from HydraDB graph_context


# ── Natural Language Query ───────────────────────────────────────────────────

class AskRequest(BaseModel):
    """Natural language question about the codebase."""
    repository_id: str
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        examples=["What calls authenticate_user?", "Which tests cover the auth module?"],
    )


class EvidenceItem(BaseModel):
    """A piece of evidence from the code graph supporting an answer."""
    chunk_id: str | None = None
    text: str
    entity_name: str | None = None
    entity_type: str | None = None
    file: str | None = None
    relevance_score: float = 0.0
    relationship_path: str | None = None  # e.g. "login → CALLS → authenticate_user"


class AskResponse(BaseModel):
    """Response to a natural language code question."""
    question: str
    answer: str
    evidence: list[EvidenceItem]
    dependency_paths: list[list[DependencyPathItem]]
    hydradb_chunks: int
    hydradb_graph_paths: int


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    repository_id: str
    query: str
    entity_types: list[str] | None = None


class SearchResult(BaseModel):
    id: str
    name: str
    type: str
    file: str
    line: int
    relevance: float
    snippet: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ── Connection Status ─────────────────────────────────────────────────────────

class ConnectionStatus(BaseModel):
    """HydraDB connection status for the UI indicator."""
    connected: bool
    message: str
    databases_count: int | None = None


# ── Generic Error ─────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
