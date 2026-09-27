"""Response schemas for the evaluation API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import MetricResult


class EvaluationResponse(BaseModel):
    """Full evaluation result returned by POST /api/evaluate."""

    metrics: dict[str, MetricResult] = Field(
        description="Per-metric results keyed by metric name"
    )
    overall_score: Optional[float] = Field(
        default=None,
        description="Weighted aggregate score (0.0–1.0)",
    )
    verdict: str = Field(
        description="Overall verdict label (Excellent/Good/Acceptable/Poor/Unacceptable)"
    )
    confidence: float = Field(
        description="Confidence in the verdict (0.0–1.0)"
    )
    processing_time_seconds: float = Field(
        description="Total wall-clock time for evaluation"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Aggregated top strengths"
    )
    weaknesses: list[str] = Field(
        default_factory=list, description="Aggregated top weaknesses"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Aggregated recommendations"
    )


class BatchEvaluationResponse(BaseModel):
    """Aggregate result for a batch of evaluations."""

    results: list[EvaluationResponse] = Field(
        description="Individual evaluation results in the same order as requested"
    )
    total_count: int = Field(
        description="Total number of evaluated items"
    )
    average_score: Optional[float] = Field(
        default=None,
        description="Average overall score across all successful evaluations"
    )
    verdict_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each verdict type in the batch"
    )
    average_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Average score for each metric across the batch"
    )
