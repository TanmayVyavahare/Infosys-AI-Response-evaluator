"""Evaluation API route.

POST /api/evaluate — submit a question + AI response for evaluation.
Returns metric reports, overall verdict, and processing time.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.requests import EvaluationRequest
from app.schemas.responses import EvaluationResponse, BatchEvaluationResponse
from app.services.evaluation_coordinator import EvaluationCoordinator
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["evaluation"])

# Module-level coordinator instance (initialized on first use)
_coordinator: EvaluationCoordinator | None = None


def _get_coordinator() -> EvaluationCoordinator:
    """Get or create the evaluation coordinator singleton."""
    global _coordinator
    if _coordinator is None:
        _coordinator = EvaluationCoordinator()
    return _coordinator


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate an AI-generated response",
    description=(
        "Submit a question and AI response for multi-dimensional evaluation. "
        "Optionally include a reference answer and/or source document."
    ),
)
async def evaluate(request: EvaluationRequest) -> EvaluationResponse:
    """Evaluate an AI response across relevance, accuracy, groundedness, and completeness.

    Args:
        request: Evaluation request with question, response, and optional references.

    Returns:
        Full evaluation response with per-metric results and aggregate verdict.
    """
    logger.info(
        "Received evaluation request (question=%d chars, response=%d chars)",
        len(request.question),
        len(request.ai_response),
    )

    try:
        coordinator = _get_coordinator()
        response = await coordinator.evaluate(request)
        logger.info(
            "Evaluation complete: verdict=%s, score=%s, time=%.2fs",
            response.verdict,
            response.overall_score,
            response.processing_time_seconds,
        )
        return response
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(exc)}",
        )


@router.post(
    "/evaluate/batch",
    response_model=BatchEvaluationResponse,
    summary="Evaluate a batch of AI-generated responses",
    description="Submit a list of evaluation requests for concurrent multi-dimensional evaluation.",
)
async def evaluate_batch(requests: list[EvaluationRequest]) -> BatchEvaluationResponse:
    """Evaluate multiple AI responses.

    Args:
        requests: List of EvaluationRequest objects.

    Returns:
        BatchEvaluationResponse with aggregate metrics and list of individual results.
    """
    logger.info("Received batch evaluation request (size=%d)", len(requests))
    try:
        coordinator = _get_coordinator()
        response = await coordinator.evaluate_batch(requests)
        logger.info(
            "Batch evaluation complete: count=%d, average_score=%s",
            response.total_count,
            response.average_score,
        )
        return response
    except Exception as exc:
        logger.error("Batch evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch evaluation failed: {str(exc)}",
        )
