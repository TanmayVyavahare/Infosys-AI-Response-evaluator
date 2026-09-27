"""Completeness Evaluator Agent.

Determines whether the response covers every requested requirement
from the question. The question is the PRIMARY source; reference
answer only enriches extracted requirements.

LLM path: Completeness prompt → coverage assessment.
Fallback path: Requirement extraction + semantic presence checking.
"""

from __future__ import annotations

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.fallbacks.concepts import ConceptExtractor
from app.evaluation.fallbacks.semantic import SemanticFallback
from app.evaluation.prompts.completeness import (
    COMPLETENESS_SYSTEM_MESSAGE,
    build_completeness_prompt,
)
from app.schemas.common import MetricResult, RequirementCoverage
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CompletenessEvaluator(BaseEvaluator):
    """Evaluate the completeness of an AI response.

    Extracts requirements from the question (primary) and optionally
    enriches from the reference answer. Then checks each requirement
    against the response: Covered / Partial / Missing.
    """

    @property
    def metric_name(self) -> str:
        return "completeness"

    def _build_llm_prompt(
        self, package: EvaluationPackage
    ) -> tuple[str, str]:
        """Build completeness prompt for LLM evaluation.

        Args:
            package: EvaluationPackage.

        Returns:
            Tuple of (prompt, system_message).
        """
        prompt = build_completeness_prompt(
            question=package.question,
            ai_response=package.ai_response,
            reference_answer=package.reference_answer,
        )
        return prompt, COMPLETENESS_SYSTEM_MESSAGE

    def _evaluate_with_fallback(
        self, package: EvaluationPackage
    ) -> MetricResult:
        """Evaluate completeness using local NLP.

        Process:
        1. Extract requirements from question and baseline.
        2. Assess requirement coverage in the AI response.
        3. Compile and return a MetricResult report.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult with requirement coverage details.
        """
        concept_extractor = ConceptExtractor()
        semantic = SemanticFallback(self.embedder)

        # 1. Extract requirements
        requirements = concept_extractor.extract_requirements(
            question=package.question,
            reference=package.reference_answer,
        )
        if not requirements:
            return self._build_no_requirements_result()

        # 2. Get sentence structure from AI response
        from app.utils.text_processing import split_into_sentences
        response_sentences = split_into_sentences(package.ai_response)
        if not response_sentences:
            return self._build_empty_response_result()

        # 3. Assess each requirement
        requirement_results = [
            self._verify_completeness_requirement(
                req["text"], response_sentences, package.ai_response, semantic
            )
            for req in requirements
        ]

        # 4. Generate coverage report
        return self._generate_completeness_report(requirement_results)

    def _build_no_requirements_result(self) -> MetricResult:
        """Return MetricResult when no requirements could be identified in the prompt."""
        return MetricResult(
            metric_name=self.metric_name,
            score=0.5,
            reason="Could not extract specific requirements from the question.",
            weaknesses=["Unable to determine what the question requires."],
            evaluated_with="fallback",
        )

    def _build_empty_response_result(self) -> MetricResult:
        """Return MetricResult when the response is empty."""
        return MetricResult(
            metric_name=self.metric_name,
            score=0.0,
            reason="The response is empty or contains no assessable content.",
            weaknesses=["Response is empty."],
            evaluated_with="fallback",
        )

    def _verify_completeness_requirement(
        self,
        req_text: str,
        response_sentences: list[str],
        ai_response: str,
        semantic: SemanticFallback,
    ) -> RequirementCoverage:
        """Verify if a single requirement is covered in the AI response."""
        # Find best matching sentence in response
        best_sim, best_match = semantic.best_chunk_similarity(req_text, response_sentences)

        # Broad check against full response
        full_sim = semantic.text_similarity(req_text, ai_response)

        # Use maximum of sentence-level similarity and full-text check
        coverage_score = max(best_sim, full_sim * 0.9)

        if coverage_score >= self.settings.similarity_threshold_high:
            status = "covered"
        elif coverage_score >= self.settings.similarity_threshold_medium:
            status = "partial"
        else:
            status = "missing"

        return RequirementCoverage(
            requirement=req_text,
            status=status,
            evidence=best_match[:150] if best_sim > 0.3 else "Not addressed",
        )

    def _generate_completeness_report(self, requirement_results: list[RequirementCoverage]) -> MetricResult:
        """Compile a list of requirement results into a consolidated MetricResult."""
        total = len(requirement_results)
        covered_count = sum(1 for r in requirement_results if r.status == "covered")
        partial_count = sum(1 for r in requirement_results if r.status == "partial")
        missing_count = sum(1 for r in requirement_results if r.status == "missing")

        # Covered = 1.0, Partial = 0.5, Missing = 0.0
        score = (covered_count * 1.0 + partial_count * 0.5) / total
        score = round(max(0.0, min(1.0, score)), 4)

        # Build list feedback
        strengths: list[str] = []
        weaknesses: list[str] = []
        evidence: list[str] = []

        for r in requirement_results:
            if r.status == "covered":
                strengths.append(f"Covers: {r.requirement[:60]}")
            elif r.status == "partial":
                evidence.append(f"Partially covers: {r.requirement[:60]}")
            else:
                weaknesses.append(f"Missing: {r.requirement[:60]}")

        reason = (
            f"Coverage: {covered_count} covered, {partial_count} partial, "
            f"{missing_count} missing out of {total} requirements. "
            f"Completeness score: {score:.2f}."
        )

        suggestions: list[str] = []
        if missing_count > 0:
            suggestions.append(f"Address the {missing_count} missing requirement(s) to improve completeness.")
        if partial_count > 0:
            suggestions.append(f"Expand on {partial_count} partially covered area(s) for full coverage.")

        return MetricResult(
            metric_name=self.metric_name,
            score=score,
            reason=reason,
            evidence=evidence[:10],
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            suggestions=suggestions,
            requirements=requirement_results,
            evaluated_with="fallback",
        )
