"""
backend/services/analysis_service.py
Orchestrates repository analysis and HydraDB ingestion.

Pipeline:
  1. Clone or load repository
  2. Parse Python files (static analysis only)
  3. Build code graph
  4. Map to HydraDB BYOG format
  5. Ensure HydraDB database exists
  6. Ingest entities + graph
  7. Store graph in memory for fast local queries
  8. Return analysis result

Thread safety: each analysis job gets its own instance.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AnalysisStatus(str, Enum):
    CLONING = "cloning"
    PARSING = "parsing"
    BUILDING_GRAPH = "building_graph"
    INGESTING = "ingesting"
    READY = "ready"
    ERROR = "error"


@dataclass
class AnalysisJob:
    """Tracks the state of a single repository analysis."""
    repository_id: str
    repository_name: str
    repository_url: str
    status: AnalysisStatus = AnalysisStatus.PARSING
    progress: int = 0
    message: str = "Starting analysis…"
    error: str = ""
    statistics: dict[str, int] = field(default_factory=dict)
    hydra_database: str = ""


# In-memory store: repository_id → (CodeGraph, AnalysisJob)
_graphs: dict[str, Any] = {}
_jobs: dict[str, AnalysisJob] = {}


class AnalysisService:
    """
    Coordinates the end-to-end repository analysis pipeline.
    Uses HydraDB BYOG ingestion for all graph data.
    """

    def __init__(self) -> None:
        from analyzer.repository import RepositoryScanner
        from analyzer.graph.graph_builder import GraphBuilder
        from analyzer.graph.hydra_mapper import HydraMapper
        from backend.hydra.client import get_hydra_client
        from backend.hydra.ingestion import HydraIngestion

        self._scanner = RepositoryScanner()
        self._graph_builder = GraphBuilder()
        self._mapper = HydraMapper()
        self._hydra = get_hydra_client()
        self._ingestion = HydraIngestion(self._hydra)

    def repository_id_from_url(self, source: str) -> str:
        """Generate a stable database-safe ID from a URL or path."""
        clean = source.strip().rstrip("/")
        if clean.endswith(".git"):
            clean = clean[:-4]
        # Use MD5 of the full URL for uniqueness
        h = hashlib.md5(clean.encode()).hexdigest()[:12]
        name = clean.split("/")[-1].lower()
        # HydraDB database names: alphanumeric + hyphens only
        name = "".join(c if c.isalnum() or c == "-" else "-" for c in name)
        return f"codemind-{name}-{h}"

    def analyze(self, source: str, *, force_reanalysis: bool = False) -> AnalysisJob:
        """
        Launch a synchronous repository analysis.
        Returns the completed AnalysisJob.
        
        In production this would be async / background task.
        For the hackathon demo, it runs synchronously.
        """
        repo_id = self.repository_id_from_url(source)
        repo_name = self._scanner.extract_repo_name(source)
        hydra_db = repo_id   # 1:1 mapping: repository ↔ HydraDB database

        if repo_id in _jobs and not force_reanalysis:
            existing = _jobs[repo_id]
            if existing.status == AnalysisStatus.READY:
                logger.info("Repository '%s' already analyzed — returning cached result", repo_name)
                return existing

        job = AnalysisJob(
            repository_id=repo_id,
            repository_name=repo_name,
            repository_url=source,
            hydra_database=hydra_db,
        )
        _jobs[repo_id] = job

        clone_path: str | None = None
        is_temp = False

        try:
            # ── Step 1: Load repository ──────────────────────────────────
            job.status = AnalysisStatus.CLONING
            job.message = "Cloning repository…"
            job.progress = 5

            if source.startswith("https://github.com/"):
                clone_path, is_temp = self._scanner.clone_github_repo(
                    source, clone_base_dir=os.environ.get("CLONE_DIR", "./tmp/repos")
                )
            else:
                clone_path, is_temp = self._scanner.prepare_local_directory(source)

            # ── Step 2: Parse + build graph ──────────────────────────────
            job.status = AnalysisStatus.PARSING
            job.message = "Parsing Python files…"
            job.progress = 20

            graph = self._graph_builder.build_from_directory(
                repo_root=clone_path,
                repository_url=source,
                repository_name=repo_name,
            )

            job.status = AnalysisStatus.BUILDING_GRAPH
            job.message = f"Graph built: {len(graph.nodes)} nodes, {len(graph.relationships)} relationships"
            job.progress = 50
            job.statistics = {
                "files": graph.file_count,
                "functions": graph.function_count,
                "classes": graph.class_count,
                "apis": graph.api_count,
                "tests": graph.test_count,
                "relationships": graph.relationship_count,
            }

            # ── Step 3: Map to BYOG format ───────────────────────────────
            app_knowledge_items, graph_payload = self._mapper.map_graph(graph, hydra_db)
            payload_stats = self._mapper.estimate_payload_size(graph_payload)
            logger.info("BYOG payload: %s", payload_stats)

            # ── Step 4: HydraDB ingestion ────────────────────────────────
            job.status = AnalysisStatus.INGESTING
            job.message = f"Ingesting {len(app_knowledge_items)} entities into HydraDB…"
            job.progress = 60

            # Verify connection first
            self._hydra.verify_connection()

            # Create database if needed
            self._hydra.ensure_database(hydra_db)

            job.message = "Uploading code graph to HydraDB (BYOG)…"
            job.progress = 70

            result = self._ingestion.ingest_code_graph(
                database=hydra_db,
                entities=app_knowledge_items,
                graph_payload=graph_payload,
                wait_for_completion=True,
                timeout_seconds=300,
            )

            if result.failed > 0:
                logger.warning("%d entities failed to ingest: %s", result.failed, result.errors[:3])

            job.progress = 95
            job.message = f"Indexed {result.succeeded}/{result.total} entities in HydraDB"

            # ── Step 5: Cache and complete ───────────────────────────────
            _graphs[repo_id] = graph
            job.status = AnalysisStatus.READY
            job.progress = 100
            job.message = "Analysis complete — graph queryable via HydraDB"

            logger.info(
                "Analysis complete for '%s': %d nodes, %d relationships, %d HydraDB entities",
                repo_name, len(graph.nodes), len(graph.relationships), result.succeeded,
            )

        except Exception as exc:
            logger.error("Analysis failed for '%s': %s", source, exc, exc_info=True)
            job.status = AnalysisStatus.ERROR
            job.error = str(exc)
            job.message = f"Analysis failed: {exc}"

        finally:
            if is_temp and clone_path:
                self._scanner.cleanup(clone_path)

        return job

    # ── Graph access ───────────────────────────────────────────────────────

    def get_graph(self, repository_id: str):
        """Return the cached CodeGraph for a repository, or None."""
        return _graphs.get(repository_id)

    def get_job(self, repository_id: str) -> AnalysisJob | None:
        """Return the analysis job for a repository."""
        return _jobs.get(repository_id)

    def get_hydra_database(self, repository_id: str) -> str | None:
        """Return the HydraDB database name for a repository."""
        job = _jobs.get(repository_id)
        return job.hydra_database if job else None

    def list_repositories(self) -> list[dict[str, Any]]:
        """List all analyzed repositories."""
        return [
            {
                "repository_id": job.repository_id,
                "repository_name": job.repository_name,
                "repository_url": job.repository_url,
                "status": job.status.value,
                "statistics": job.statistics,
            }
            for job in _jobs.values()
        ]
