"""Request schemas for the evaluation API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EvaluationRequest(BaseModel):
    """Input payload for POST /api/evaluate."""

    question: str = Field(
        ...,
        min_length=1,
        description="The original question or prompt",
    )
    ai_response: str = Field(
        ...,
        min_length=1,
        description="The AI-generated response to evaluate",
    )
    reference_answer: Optional[str] = Field(
        default=None,
        description="Optional ground-truth reference answer",
    )
    source_document: Optional[str] = Field(
        default=None,
        description="Optional source document text for RAG context",
    )

    @field_validator("question", "ai_response")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Strip whitespace and reject blank strings."""
        v = v.strip()
        if not v:
            raise ValueError("Field must not be empty or whitespace-only")
        return v

    @field_validator("reference_answer", "source_document")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from optional fields; convert blank to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None
