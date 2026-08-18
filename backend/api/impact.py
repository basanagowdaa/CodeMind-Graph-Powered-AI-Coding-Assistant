"""
backend/api/impact.py
Impact Analysis Endpoint — BEFORE YOU CHANGE IT.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.models.api_models import ImpactAnalysisRequest, ImpactAnalysisResponse
from backend.services.analysis_service import AnalysisService
from backend.services.impact_service import ImpactService
from backend.hydra.retrieval import HydraRetrieval
from backend.hydra.client import get_hydra_client

router = APIRouter(prefix="/api/impact-analysis", tags=["Impact"])
_analysis_service = AnalysisService()
_hydra_client = get_hydra_client()
_retrieval = HydraRetrieval(_hydra_client)
_impact_service = ImpactService(_retrieval)


@router.post("", response_model=ImpactAnalysisResponse)
async def analyze_impact(request: ImpactAnalysisRequest) -> Any:
    """
    Run impact analysis for a specific code entity (function, class, file, API).
    Determines what callers, tests, or other files could be affected if changed.
    """
    graph = _analysis_service.get_graph(request.repository_id)
    if not graph:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{request.repository_id}' has not been analyzed.",
        )

    hydra_db = _analysis_service.get_hydra_database(request.repository_id)
    if not hydra_db:
        hydra_db = request.repository_id

    try:
        response = _impact_service.analyze_impact(
            graph=graph,
            hydra_database=hydra_db,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            entity_type=request.entity_type,
        )
        response.repository_id = request.repository_id
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform impact analysis: {exc}",
        )
