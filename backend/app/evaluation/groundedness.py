"""Groundedness / Hallucination Detection Evaluator Agent.

Determines whether claims in the AI response are supported by the
retrieved context. Does NOT assess factual correctness in general —
only whether claims are grounded in the provided evidence.

LLM path: Faithfulness prompt → supported/unsupported claims.
Fallback path: Per-claim cosine similarity against chunks + NER cross-reference.

If no context exists, returns "Groundedness cannot be verified" — never 100%.
"""

from __future__ import annotations

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.fallbacks.claims import ClaimExtractor
from app.evaluation.fallbacks.ner import NERExtractor
from app.evaluation.fallbacks.semantic import SemanticFallback
from app.evaluation.prompts.groundedness import (
    GROUNDEDNESS_SYSTEM_MESSAGE,
    build_groundedness_prompt,
)
from app.schemas.common import ClaimDetail, MetricResult
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

    def _evaluate_with_fallback(
        self, package: EvaluationPackage
    ) -> MetricResult:
        """Evaluate groundedness using local NLP.

        Process:
        1. Extract atomic claims from the AI response.
        2. Get context chunks.
        3. Verify each claim against context chunks.
        4. Generate final report.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult with per-claim support/hallucination details.
        """
        # 1. Extract claims
        claim_extractor = ClaimExtractor()
        claims_text = claim_extractor.extract_claims(package.ai_response)
        if not claims_text:
            return self._build_no_claims_result()

        # 2. Get context chunks
        context_chunks = [
            chunk.get("text", "") for chunk in package.retrieved_context
            if chunk.get("text", "").strip()
        ]
        if not context_chunks:
            return self._build_empty_chunks_result()

        # 3. Setup NLP tools and context metadata
        semantic = SemanticFallback(self.embedder)
        ner = NERExtractor()
        context_entities = ner.extract_entities(package.context_text)

        # 4. Verify each claim
        claim_details = [
            self._verify_groundedness_claim(
                claim, context_chunks, context_entities, semantic, ner
            )
            for claim in claims_text
        ]

        # 5. Generate final report
        return self._generate_groundedness_report(claim_details)

    def _build_no_claims_result(self) -> MetricResult:
        """Return MetricResult when no claims could be extracted."""
        return MetricResult(
            metric_name=self.metric_name,
            score=0.5,
            reason="No verifiable claims could be extracted from the response.",
            weaknesses=["Response contains no clear assertions to verify against context."],
            evaluated_with="fallback",
        )

    def _build_empty_chunks_result(self) -> MetricResult:
        """Return MetricResult when context chunks are empty."""
        return MetricResult(
            metric_name=self.metric_name,
            score=None,
            reason="Groundedness cannot be verified — context chunks are empty.",
            evaluated_with="fallback",
        )

    def _verify_groundedness_claim(
        self,
        claim_text: str,
        context_chunks: list[str],
        context_entities: dict[str, list[str]],
        semantic: SemanticFallback,
        ner: NERExtractor,
    ) -> ClaimDetail:
        """Verify grounding of a single claim against context chunks."""
        # Find best matching context chunk
        best_sim, best_chunk = semantic.best_chunk_similarity(claim_text, context_chunks)

        # Entity overlap check
        claim_entities = ner.extract_entities(claim_text)
        entity_overlap = ner.entity_overlap(claim_entities, context_entities)

        # Combine scores
        groundedness_score = (
            0.70 * best_sim
            + 0.30 * entity_overlap
        )
        groundedness_score = round(max(0.0, min(1.0, groundedness_score)), 4)
        supported = groundedness_score >= self.settings.similarity_threshold_medium

        return ClaimDetail(
            claim=claim_text,
            supported=supported,
            score=groundedness_score,
            evidence=best_chunk[:200] if supported and best_chunk else None,
        )

    def _generate_groundedness_report(self, claim_details: list[ClaimDetail]) -> MetricResult:
        """Compile verified claim detail lists into a final MetricResult."""
        total_count = len(claim_details)
        supported_count = sum(1 for c in claim_details if c.supported)

        # Raw ratio score
        overall_score = supported_count / total_count if total_count > 0 else 0.0

        # Confidence sanity check: cap at 0.95 if average claim scores are low
        if overall_score >= 1.0 and total_count > 0:
            scores = [c.score for c in claim_details if c.score is not None]
            avg_claim_score = sum(scores) / total_count
            if avg_claim_score < 0.9:
                overall_score = 0.95

        overall_score = round(overall_score, 4)

        # Build report structures
        evidence: list[str] = []
        strengths: list[str] = []
        weaknesses: list[str] = []
        suggestions: list[str] = []

        for c in claim_details:
            status = "✓ Supported" if c.supported else "✗ Unsupported"
            evidence.append(f"{status} (score={c.score:.2f}): {c.claim[:60]}...")

        if supported_count > 0:
            strengths.append(f"{supported_count}/{total_count} claims are supported by the context")

        unsupported_count = total_count - supported_count
        if unsupported_count > 0:
            weaknesses.append(f"{unsupported_count} claim(s) appear to be hallucinated (not supported by the context)")
            suggestions.append(
                "Review unsupported claims and either remove them or provide supporting evidence in the source material."
            )

        if overall_score < self.settings.critical_hallucination_threshold:
            weaknesses.append("CRITICAL: Most claims are not grounded in the provided context. This indicates significant hallucination.")
            suggestions.append("The response should be regenerated with stricter adherence to the source material.")

        reason = (
            f"{supported_count}/{total_count} claims are supported by the context. "
            f"Groundedness score: {overall_score:.2f}."
        )

        return MetricResult(
            metric_name=self.metric_name,
            score=overall_score,
            reason=reason,
            evidence=evidence[:10],
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            claims=claim_details,
            evaluated_with="fallback",
        )
