"""
backend/services/ai_service.py
LLM reasoning layer for CodeMind.

Grounds LLM answers in HydraDB-retrieved graph context.
Never invents relationships or code structure.
Evidence is sourced from actual graph data retrieved from HydraDB.

Supports: Google Gemini (default), OpenAI, Anthropic (configured via .env)
"""
from __future__ import annotations

import logging
import os
from typing import Any

from backend.hydra.retrieval import HydraRetrieval, RetrievalResult
from backend.models.api_models import AskResponse, EvidenceItem, DependencyPathItem

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.0-flash")


def _build_context_string(result: RetrievalResult) -> str:
    """
    Format HydraDB retrieval result into a structured context string for the LLM.
    Includes both chunk content and graph dependency paths.
    """
    parts: list[str] = ["## Retrieved Code Context (from HydraDB)\n"]

    # Code chunks
    if result.chunks:
        parts.append("### Relevant Code Entities:")
        for i, chunk in enumerate(result.chunks[:10], 1):
            text = chunk.get("text", "").strip()
            if text:
                parts.append(f"\n[{i}] {text[:500]}")

    # Graph dependency paths
    if result.dependency_paths:
        parts.append("\n\n### Dependency Paths (from code graph):")
        for i, path in enumerate(result.dependency_paths[:5], 1):
            chain = path.as_text_chain()
            if chain:
                parts.append(f"\n  Path {i}: {chain}")
                for t in path.triplets:
                    if t.context:
                        parts.append(f"    ↳ {t.context}")

    # Chunk relations
    if result.chunk_relations:
        parts.append("\n\n### Related Entity Connections:")
        for path in result.chunk_relations[:3]:
            chain = path.as_text_chain()
            if chain:
                parts.append(f"  {chain}")

    return "\n".join(parts)


def _system_prompt() -> str:
    return """You are CodeMind, an AI coding assistant that helps developers understand code structure and dependencies.

You answer questions about code using ONLY the retrieved context provided. You do not invent relationships or code structure.

Rules:
- Base your answers ONLY on the provided code context.
- If the context doesn't contain enough information, say so clearly.
- Cite specific functions, files, and lines when you reference them.
- When describing dependency chains, use arrows: functionA → calls → functionB.
- Do not invent test coverage, function signatures, or file paths.
- Be concise and developer-focused."""


class AIService:
    """
    LLM reasoning layer that grounds answers in HydraDB-retrieved graph context.
    """

    def __init__(self, hydra_retrieval: HydraRetrieval) -> None:
        self._hydra = hydra_retrieval
        self._model = self._init_model()

    def _init_model(self):
        """Initialize the LLM client based on LLM_PROVIDER env variable."""
        if LLM_PROVIDER == "gemini":
            try:
                import google.generativeai as genai
                api_key = os.environ.get("GOOGLE_API_KEY", "")
                if not api_key:
                    logger.warning("GOOGLE_API_KEY not set — AI answers disabled")
                    return None
                genai.configure(api_key=api_key)
                return genai.GenerativeModel(
                    LLM_MODEL,
                    system_instruction=_system_prompt(),
                )
            except ImportError:
                logger.warning("google-generativeai not installed — AI answers disabled")
                return None

        elif LLM_PROVIDER == "openai":
            try:
                from openai import OpenAI
                api_key = os.environ.get("OPENAI_API_KEY", "")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not set — AI answers disabled")
                    return None
                return OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai not installed — AI answers disabled")
                return None

        logger.warning("Unknown LLM_PROVIDER '%s' — AI answers disabled", LLM_PROVIDER)
        return None

    def answer_question(
        self,
        database: str,
        question: str,
    ) -> AskResponse:
        """
        Answer a natural language question about the codebase.
        Retrieves context from HydraDB first, then passes to LLM.
        """
        # Step 1: Retrieve context from HydraDB
        logger.info("Querying HydraDB for: %s", question)
        retrieval = self._hydra.query_with_graph(
            database=database,
            query=question,
            top_k=15,
        )

        # Step 2: Build context string
        context = _build_context_string(retrieval)

        # Step 3: Generate LLM answer
        if self._model is None:
            answer = (
                "AI reasoning is not configured. "
                "Set GOOGLE_API_KEY in .env to enable LLM answers. "
                "The graph data retrieved from HydraDB is shown below."
            )
        else:
            try:
                answer = self._call_llm(question, context)
            except Exception as exc:
                logger.error("LLM call failed: %s", exc)
                answer = f"LLM error: {exc}. See retrieved context for raw graph data."

        # Step 4: Build evidence list from chunks
        evidence = []
        for chunk in retrieval.chunks[:8]:
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            evidence.append(EvidenceItem(
                chunk_id=chunk.get("id"),
                text=text[:300],
                entity_name=meta.get("name", ""),
                entity_type=meta.get("entity_type", ""),
                file=meta.get("file", ""),
                relevance_score=chunk.get("score", 0.0),
            ))

        # Step 5: Build dependency path items
        dep_paths: list[list[DependencyPathItem]] = []
        for path in retrieval.dependency_paths[:5]:
            items = [
                DependencyPathItem(
                    source=t.source_name,
                    predicate=t.predicate,
                    target=t.target_name,
                    context=t.context,
                )
                for t in path.triplets
            ]
            if items:
                dep_paths.append(items)

        return AskResponse(
            question=question,
            answer=answer,
            evidence=evidence,
            dependency_paths=dep_paths,
            hydradb_chunks=len(retrieval.chunks),
            hydradb_graph_paths=len(retrieval.dependency_paths),
        )

    def _call_llm(self, question: str, context: str) -> str:
        """Call the configured LLM with the question and retrieved context."""
        prompt = f"{context}\n\n## Question\n{question}\n\n## Answer"

        if LLM_PROVIDER == "gemini":
            response = self._model.generate_content(prompt)
            return response.text

        elif LLM_PROVIDER == "openai":
            response = self._model.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.1,
            )
            return response.choices[0].message.content or ""

        return "LLM provider not supported."
