"""
backend/api/ask.py
Ask CodeMind endpoint — grounded natural language search and Q&A.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.models.api_models import AskRequest, AskResponse
from backend.services.analysis_service import AnalysisService
from backend.services.ai_service import AIService
from backend.hydra.retrieval import HydraRetrieval
from backend.hydra.client import get_hydra_client

router = APIRouter(prefix="/api/ask", tags=["Query"])
_analysis_service = AnalysisService()
_hydra_client = get_hydra_client()
_retrieval = HydraRetrieval(_hydra_client)
_ai_service = AIService(_retrieval)


@router.post("", response_model=AskResponse)
async def ask_codemind(request: AskRequest) -> Any:
    """
    Query CodeMind with a natural language question.
    grounded in HydraDB's retrieved code graph context and dependency paths.
    """
    hydra_db = _analysis_service.get_hydra_database(request.repository_id)
    if not hydra_db:
        # Check if database directly matches repository_id
        hydra_db = request.repository_id

    # Verify that database exists
    try:
        existing_dbs = _hydra_client.list_databases()
        if hydra_db not in existing_dbs:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{request.repository_id}' has not been analyzed or is not ingested in HydraDB.",
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"HydraDB service unavailable: {exc}",
        )

    try:
        response = _ai_service.answer_question(hydra_db, request.question)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate grounded Q&A response: {exc}",
        )
