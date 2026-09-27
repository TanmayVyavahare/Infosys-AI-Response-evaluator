"""Shared types used across schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ClaimDetail(BaseModel):
    """A single atomic claim with its verification status."""

    claim: str = Field(description="The atomic claim text")
    supported: Optional[bool] = Field(
        default=None, description="Whether the claim is supported by evidence"
    )
    score: Optional[float] = Field(
        default=None, description="Similarity/support score for this claim"
    )
    evidence: Optional[str] = Field(
        default=None, description="Evidence text supporting or refuting this claim"
    )


class RequirementCoverage(BaseModel):
    """Coverage status for a single requirement."""

    requirement: str = Field(description="The extracted requirement")
    status: str = Field(
        description="Coverage status: 'covered', 'partial', or 'missing'"
    )
    evidence: Optional[str] = Field(
        default=None, description="Snippet from the response that covers this requirement"
    )


class MetricResult(BaseModel):
    """Result from a single evaluation metric.

    Every evaluator MUST return this schema. Fields may be None when
    evaluation cannot be performed (e.g., no reference for accuracy).
    """

    metric_name: str = Field(description="Name of the evaluation metric")
    score: Optional[float] = Field(
        default=None,
        description="Score from 0.0 to 1.0, or None if evaluation is not possible",
    )
    reason: str = Field(description="Human-readable explanation of the score")
    evidence: list[str] = Field(
        default_factory=list, description="Supporting evidence for the score"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Identified strengths"
    )
    weaknesses: list[str] = Field(
        default_factory=list, description="Identified weaknesses"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Actionable improvement suggestions"
    )
    claims: list[ClaimDetail] = Field(
        default_factory=list,
        description="Claim-level details (for accuracy/groundedness)",
    )
    requirements: list[RequirementCoverage] = Field(
        default_factory=list,
        description="Requirement coverage details (for completeness)",
    )
    evaluated_with: str = Field(
        default="fallback",
        description="'llm' if LLM was used, 'fallback' if local NLP was used",
    )
