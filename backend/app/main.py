"""FastAPI application entry point.

Configures CORS, registers routes, and sets up application lifecycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    settings = get_settings()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("LLM provider: %s", settings.llm_provider)
    logger.info("Embedding model: %s", settings.embedding_model_name)

    # Pre-warm the embedding model on startup
    try:
        from app.retrieval.embedder import Embedder
        embedder = Embedder()
        embedder.embed_text("warmup")
        logger.info("Embedding model warmed up successfully")
    except Exception as exc:
        logger.warning("Failed to warm up embedding model: %s", exc)

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI Response Quality Evaluator — evaluates AI-generated responses "
            "across relevance, accuracy, groundedness, and completeness."
        ),
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(evaluation_router)
    app.include_router(health_router)

    return app


# Application instance for uvicorn
app = create_app()
