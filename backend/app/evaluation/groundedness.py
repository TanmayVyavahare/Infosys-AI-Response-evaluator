"""Groundedness / Hallucination Detection Evaluator Agent.

Determines whether claims in the AI response are supported by the
retrieved context. Does NOT assess factual correctness in general —
only whether claims are grounded in the provided evidence.

LLM path: Faithfulness prompt → supported/unsupported claims.
Fallback path: Explicit abstention when AI verification is unavailable.

If no context exists, returns "Groundedness cannot be verified" — never 100%.
"""

from __future__ import annotations

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.prompts.groundedness import (
    GROUNDEDNESS_SYSTEM_MESSAGE,
    build_groundedness_prompt,
)
from app.schemas.common import MetricResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GroundednessEvaluator(BaseEvaluator):
    """Evaluate whether AI response claims are grounded in context.

    Detects hallucinations by checking each extracted claim against
    the retrieved context chunks. A claim is SUPPORTED if it can be
    traced back to the context, and UNSUPPORTED (hallucinated) if not.
    """

    @property
    def metric_name(self) -> str:
        return "groundedness"

    def _build_llm_prompt(
        self, package: EvaluationPackage
    ) -> tuple[str, str]:
        """Build groundedness prompt for LLM evaluation.

        Args:
            package: EvaluationPackage.

        Returns:
            Tuple of (prompt, system_message).
        """
        prompt = build_groundedness_prompt(
            ai_response=package.ai_response,
            context=package.context_text,
        )
        return prompt, GROUNDEDNESS_SYSTEM_MESSAGE

    async def evaluate(self, package: EvaluationPackage) -> MetricResult:
        """Override to handle the no-context case before attempting evaluation.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult.
        """
        if not package.has_context:
            return MetricResult(
                metric_name=self.metric_name,
                score=None,
                reason=(
                    "Groundedness cannot be verified — no source context available. "
                    "Provide a source document to enable hallucination detection."
                ),
                weaknesses=[
                    "No context available to check claims against."
                ],
                suggestions=[
                    "Upload a source document to enable groundedness evaluation."
                ],
                evaluated_with="fallback",
            )

        return await super().evaluate(package)

    def _evaluate_with_fallback(self, package: EvaluationPackage) -> MetricResult:
        """Abstain: text similarity cannot prove that a claim follows from evidence."""
        return self._unverified_fact_result(package)
