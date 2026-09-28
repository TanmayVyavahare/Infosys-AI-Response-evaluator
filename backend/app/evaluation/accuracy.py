"""Factual Accuracy Evaluator Agent.

Determines factual correctness of the AI response by extracting
atomic claims and comparing them against a reference answer or
retrieved context.

LLM path: Accuracy prompt with claims + baseline → JSON.
Fallback path: Explicit abstention when AI verification is unavailable.

If no reference AND no context exists, returns "Accuracy cannot be verified"
with score=None — never returns 100%.
"""

from __future__ import annotations

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.prompts.accuracy import (
    ACCURACY_SYSTEM_MESSAGE,
    build_accuracy_prompt,
)
from app.schemas.common import MetricResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AccuracyEvaluator(BaseEvaluator):
    """Evaluate the factual accuracy of an AI response.

    Extracts atomic claims from the response and verifies each
    against the reference answer (primary) or retrieved context
    (secondary baseline).
    """

    @property
    def metric_name(self) -> str:
        return "accuracy"

    async def evaluate(self, package: EvaluationPackage) -> MetricResult:
        """Require evidence before either LLM or local fact checking."""
        if not package.has_reference and not package.has_context:
            return self._build_empty_baseline_result()
        return await super().evaluate(package)

    def _build_llm_prompt(
        self, package: EvaluationPackage
    ) -> tuple[str, str]:
        """Build accuracy prompt for LLM evaluation.

        Args:
            package: EvaluationPackage.

        Returns:
            Tuple of (prompt, system_message).
        """
        prompt = build_accuracy_prompt(
            question=package.question,
            ai_response=package.ai_response,
            reference_answer=package.reference_answer,
            context=package.context_text if package.has_context else None,
        )
        return prompt, ACCURACY_SYSTEM_MESSAGE

    def _evaluate_with_fallback(self, package: EvaluationPackage) -> MetricResult:
        """Abstain: text similarity cannot prove that a claim follows from evidence."""
        return self._unverified_fact_result(package)

    def _build_empty_baseline_result(self) -> MetricResult:
        return MetricResult(
            metric_name=self.metric_name, score=None,
            reason="Accuracy cannot be verified: no reference answer or source context available.",
            suggestions=["Supply a reference answer or source document for fact checking."],
            evaluated_with="fallback",
        )
