"""Factual Accuracy Evaluator Agent.

Determines factual correctness of the AI response by extracting
atomic claims and comparing them against a reference answer or
retrieved context.

LLM path: Accuracy prompt with claims + baseline → JSON.
Fallback path: Per-claim semantic similarity + NER comparison + number matching.

If no reference AND no context exists, returns "Accuracy cannot be verified"
with score=None — never returns 100%.
"""

from __future__ import annotations

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.fallbacks.claims import ClaimExtractor
from app.evaluation.fallbacks.ner import NERExtractor
from app.evaluation.fallbacks.semantic import SemanticFallback
from app.evaluation.prompts.accuracy import (
    ACCURACY_SYSTEM_MESSAGE,
    build_accuracy_prompt,
)
from app.schemas.common import ClaimDetail, MetricResult
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

    def _evaluate_with_fallback(
        self, package: EvaluationPackage
    ) -> MetricResult:
        """Evaluate accuracy using local NLP.

        Process:
        1. Check and prepare baseline data.
        2. Extract atomic claims from the AI response.
        3. Verify each claim against the baseline using semantic and entity rules.
        4. Aggregate findings into a MetricResult report.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult with verification findings.
        """
        # 1. Determine baseline text
        baseline_text = package.reference_answer or package.context_text
        if not baseline_text or not baseline_text.strip():
            return self._build_empty_baseline_result()

        # 2. Extract atomic claims
        claim_extractor = ClaimExtractor()
        claims_text = claim_extractor.extract_claims(package.ai_response)
        if not claims_text:
            return self._build_no_claims_result()

        # 3. Prepare NLP helper tools and baseline data
        semantic = SemanticFallback(self.embedder)
        ner = NERExtractor()
        from app.utils.text_processing import split_into_sentences
        baseline_sentences = split_into_sentences(baseline_text)
        baseline_entities = ner.extract_entities(baseline_text)
        baseline_numbers = baseline_entities.get("number", [])

        # 4. Verify all claims
        claim_details = [
            self._verify_single_claim(
                claim_text, baseline_sentences, baseline_entities, baseline_numbers, semantic, ner
            )
            for claim_text in claims_text
        ]

        # 5. Generate final evaluation report
        return self._generate_accuracy_report(claim_details)

    def _build_empty_baseline_result(self) -> MetricResult:
        """Return MetricResult when no baseline reference/context is available."""
        return MetricResult(
            metric_name=self.metric_name,
            score=None,
            reason="Accuracy cannot be verified — no reference answer or context available.",
            weaknesses=["No baseline for fact-checking. Provide a reference answer or source document."],
            suggestions=["Supply a reference answer or source document to enable accuracy verification."],
            evaluated_with="fallback",
        )

    def _build_no_claims_result(self) -> MetricResult:
        """Return MetricResult when no factual claims could be extracted."""
        return MetricResult(
            metric_name=self.metric_name,
            score=0.5,
            reason="No verifiable factual claims could be extracted from the response.",
            weaknesses=["Response contains no clear factual assertions to verify."],
            evaluated_with="fallback",
        )

    def _verify_single_claim(
        self,
        claim_text: str,
        baseline_sentences: list[str],
        baseline_entities: dict[str, list[str]],
        baseline_numbers: list[str],
        semantic: SemanticFallback,
        ner: NERExtractor,
    ) -> ClaimDetail:
        """Verify an atomic claim against the baseline data."""
        # Semantic check
        best_sim, best_match = semantic.best_chunk_similarity(claim_text, baseline_sentences)

        # Entity check
        claim_entities = ner.extract_entities(claim_text)
        entity_overlap = ner.entity_overlap(claim_entities, baseline_entities)

        # Numerical comparison
        claim_numbers = claim_entities.get("number", [])
        num_match = ner.number_match(claim_numbers, baseline_numbers)

        # Compute claim-level validation score
        claim_score = (
            0.50 * best_sim
            + 0.25 * entity_overlap
            + 0.25 * num_match
        )
        claim_score = round(max(0.0, min(1.0, claim_score)), 4)
        supported = claim_score >= self.settings.similarity_threshold_medium

        return ClaimDetail(
            claim=claim_text,
            supported=supported,
            score=claim_score,
            evidence=best_match if best_sim > 0.3 else None,
        )

    def _generate_accuracy_report(self, claim_details: list[ClaimDetail]) -> MetricResult:
        """Aggregate verified claim details and compile final evaluation report."""
        scores = [c.score for c in claim_details if c.score is not None]
        overall_score = round(sum(scores) / len(scores), 4) if scores else 0.0

        verified_count = sum(1 for c in claim_details if c.supported)
        total_count = len(claim_details)

        # Build feedback elements
        evidence: list[str] = []
        strengths: list[str] = []
        weaknesses: list[str] = []

        for c in claim_details:
            status = "✓ Verified" if c.supported else "✗ Unverified"
            evidence.append(f"{status} (score={c.score:.2f}): {c.claim[:80]}")
            if c.supported:
                strengths.append(f"Verified: {c.claim[:60]}...")
            else:
                weaknesses.append(f"Unverified: {c.claim[:60]}...")

        reason = (
            f"Verified {verified_count}/{total_count} claims against the baseline. "
            f"Overall accuracy score: {overall_score:.2f}."
        )

        suggestions: list[str] = []
        if overall_score < self.settings.similarity_threshold_high:
            suggestions.append("Cross-check factual claims against authoritative sources.")
        if total_count > verified_count:
            suggestions.append("Review unverified claims for potential inaccuracies.")

        return MetricResult(
            metric_name=self.metric_name,
            score=overall_score,
            reason=reason,
            evidence=evidence[:10],
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            suggestions=suggestions,
            claims=claim_details,
            evaluated_with="fallback",
        )
