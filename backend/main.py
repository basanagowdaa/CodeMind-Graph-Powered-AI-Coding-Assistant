"""
backend/main.py
Main entrypoint for the CodeMind FastAPI Backend.
"""
from __future__ import annotations

import os
import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("codemind")

# Import routers
from backend.api.repository import router as repository_router
from backend.api.graph import router as graph_router
from backend.api.ask import router as ask_router
from backend.api.impact import router as impact_router
from backend.api.dependencies import router as dependencies_router
from backend.api.benchmark import router as benchmark_router

# Import HydraClient
from backend.hydra.client import get_hydra_client
from backend.models.api_models import ConnectionStatus

app = FastAPI(
    title="CodeMind API",
    description="Graph-Powered AI Coding Assistant API backed by HydraDB",
    version="1.0.0",
)

# CORS middleware config
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health / Connection Route ────────────────────────────────────────────────

@app.get("/api/health", response_model=ConnectionStatus)
async def check_hydradb_health() -> ConnectionStatus:
    """
    Perform a real health-check query to HydraDB to verify connection.
    Shows 'connected' only after a real successful connection.
    """
    try:
        client = get_hydra_client()
        client.verify_connection()
        db_names = client.list_databases()
        return ConnectionStatus(
            connected=True,
            message="Successfully connected to HydraDB API v2.",
            databases_count=len(db_names),
        )
    except Exception as exc:
        logger.error("HydraDB health check failed: %s", exc)
        return ConnectionStatus(
            connected=False,
            message=f"Connection failed: {exc}",
            databases_count=None,
        )

# Register routers
app.include_router(repository_router)
app.include_router(graph_router)
app.include_router(ask_router)
app.include_router(impact_router)
app.include_router(dependencies_router)
app.include_router(benchmark_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "project": "CodeMind — Graph-Powered AI Coding Assistant",
        "hackathon": "Hack Hydra 2026",
        "track": "2B: Code Graphs for IDE Assistants",
        "docs": "/docs",
    }
