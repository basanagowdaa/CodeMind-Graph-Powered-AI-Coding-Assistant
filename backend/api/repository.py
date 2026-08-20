"""
backend/api/repository.py
Repository analysis and listing endpoints.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from backend.models.api_models import AnalyzeRepositoryRequest, AnalysisStatusResponse
from backend.services.analysis_service import AnalysisService, AnalysisStatus

router = APIRouter(prefix="/api/repository", tags=["Repository"])
_service = AnalysisService()


def _run_analysis(source: str, force: bool) -> None:
    """Helper function to run analysis in the background."""
    _service.analyze(source, force_reanalysis=force)


@router.post("/analyze", response_model=AnalysisStatusResponse)
async def analyze_repository(
    request: AnalyzeRepositoryRequest,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Trigger analysis of a repository (local path or GitHub URL).
    Analysis runs in the background.
    """
    repo_id = _service.repository_id_from_url(request.source)
    
    # Check if already running/ready
    existing = _service.get_job(repo_id)
    if existing and not request.force_reanalysis:
        return AnalysisStatusResponse(
            repository_id=existing.repository_id,
            repository_name=existing.repository_name,
            repository_url=existing.repository_url,
            status=existing.status.value,
            progress=existing.progress,
            message=existing.message,
            statistics=existing.statistics or None,
            error=existing.error or None,
        )

    # Queue the job
    background_tasks.add_task(_run_analysis, request.source, request.force_reanalysis)
    
    # Return initial status
    return AnalysisStatusResponse(
        repository_id=repo_id,
        repository_name=request.source.split("/")[-1].replace(".git", ""),
        repository_url=request.source,
        status=AnalysisStatus.CLONING.value,
        progress=5,
        message="Queued for analysis...",
    )


@router.get("/list")
async def list_repositories() -> list[dict[str, Any]]:
    """List all repositories analyzed or currently being analyzed."""
    return _service.list_repositories()


@router.get("/{repository_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(repository_id: str) -> Any:
    """Get the current progress/status of a repository analysis job."""
    job = _service.get_job(repository_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis job found for repository '{repository_id}'",
        )
    return AnalysisStatusResponse(
        repository_id=job.repository_id,
        repository_name=job.repository_name,
        repository_url=job.repository_url,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        statistics=job.statistics or None,
        error=job.error or None,
    )
