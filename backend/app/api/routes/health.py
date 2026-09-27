"""Health check API route.

GET /api/health — returns system status.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns system status and configuration.",
)
async def health() -> dict:
    """Return system health status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model_name,
    }
