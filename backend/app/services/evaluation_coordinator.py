"""Evaluation Coordinator.

Orchestrates the concurrent execution of all evaluation agents.
Builds the EvaluationPackage, runs evaluators via asyncio.gather(),
and assembles the final response.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.config.settings import get_settings
from app.evaluation.accuracy import AccuracyEvaluator
from app.evaluation.base import EvaluationPackage
from app.evaluation.completeness import CompletenessEvaluator
from app.evaluation.groundedness import GroundednessEvaluator
from app.evaluation.relevance import RelevanceEvaluator
from app.retrieval.embedder import Embedder
from app.retrieval.retriever import FAISSRetriever
from app.schemas.common import MetricResult
from app.schemas.requests import EvaluationRequest
from app.schemas.responses import EvaluationResponse, BatchEvaluationResponse
from app.services.llm_provider import LLMProvider, LLMProviderFactory
from app.utils.logging import get_logger

logger = get_logger(__name__)
_AUTO_PROVIDER = object()


class EvaluationCoordinator:
    """Orchestrate concurrent evaluation of AI responses.

    Manages the full evaluation lifecycle:
    1. Build EvaluationPackage (with optional RAG retrieval)
    2. Run all evaluators concurrently via ``asyncio.gather()``
    3. Compute aggregate verdict
    4. Return structured response
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] | object = _AUTO_PROVIDER,
        embedder: Optional[Embedder] = None,
        retriever: Optional[FAISSRetriever] = None,
    ) -> None:
        self.embedder = embedder or Embedder()
        self.retriever = retriever or FAISSRetriever(embedder=self.embedder)
        self.settings = get_settings()

        # Try to create LLM provider; None means fallback-only mode
        if llm_provider is _AUTO_PROVIDER:
            self.llm_provider = LLMProviderFactory.create_optional()
        else:
            self.llm_provider = llm_provider

        if self.llm_provider:
            logger.info(
                "Evaluation coordinator initialized with LLM provider: %s",
                self.llm_provider.provider_name,
            )
        else:
            logger.info(
                "Evaluation coordinator initialized in fallback-only mode (no LLM)"
            )

        # Create evaluators — all receive the same LLM provider and embedder
        self.evaluators = {
            "relevance": RelevanceEvaluator(
                llm_provider=self.llm_provider, embedder=self.embedder
            ),
            "accuracy": AccuracyEvaluator(
                llm_provider=self.llm_provider, embedder=self.embedder
            ),
            "groundedness": GroundednessEvaluator(
                llm_provider=self.llm_provider, embedder=self.embedder
            ),
            "completeness": CompletenessEvaluator(
                llm_provider=self.llm_provider, embedder=self.embedder
            ),
        }

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Run the full evaluation pipeline.

        Args:
            request: Validated evaluation request.

        Returns:
            EvaluationResponse with all metrics and aggregate verdict.
        """
        start_time = time.perf_counter()

        # 1. Build evaluation package
        package = await self._build_package(request)
        logger.info(
            "Built evaluation package (context=%d chunks, has_reference=%s)",
            len(package.retrieved_context),
            package.has_reference,
        )

        # 2. Run all evaluators concurrently
        results = await asyncio.gather(
            self.evaluators["relevance"].evaluate(package),
            self.evaluators["accuracy"].evaluate(package),
            self.evaluators["groundedness"].evaluate(package),
            self.evaluators["completeness"].evaluate(package),
            return_exceptions=True,
        )

        # 3. Process results — handle exceptions from gather
        metrics: dict[str, MetricResult] = {}
        metric_names = ["relevance", "accuracy", "groundedness", "completeness"]

        for name, result in zip(metric_names, results):
            if isinstance(result, Exception):
                logger.error("Evaluator %s raised: %s", name, result)
                metrics[name] = MetricResult(
                    metric_name=name,
                    score=None,
                    reason=f"Evaluation failed: {result}",
                    evaluated_with="error",
                )
            else:
                metrics[name] = result

        # 4. Compute aggregate verdict
        overall_score, verdict, confidence = self._compute_verdict(metrics)

        # 5. Aggregate strengths, weaknesses, recommendations
        all_strengths = []
        all_weaknesses = []
        all_recommendations = []
        for m in metrics.values():
            all_strengths.extend(m.strengths[:2])
            all_weaknesses.extend(m.weaknesses[:2])
            all_recommendations.extend(m.suggestions[:2])

        processing_time = time.perf_counter() - start_time

        return EvaluationResponse(
            metrics=metrics,
            warnings=package.metadata.get("warnings", []) + list(dict.fromkeys(
                m.review_warning for m in metrics.values() if m.review_warning
            )) + (
                ["The reference and source disagree. Resolve the conflicting evidence before relying on the score."] if verdict == "Conflicting Evidence" else []
            ) + (
                ["The overall score covers only assessable checks; it does not verify unsupported facts."] if verdict == "Limited Evidence" else []
            ),
            overall_score=overall_score,
            verdict=verdict,
            confidence=confidence,
            processing_time_seconds=round(processing_time, 3),
            strengths=list(dict.fromkeys(all_strengths))[:8],
            weaknesses=list(dict.fromkeys(all_weaknesses))[:8],
            recommendations=list(dict.fromkeys(all_recommendations))[:8],
        )

    async def _build_package(
        self, request: EvaluationRequest
    ) -> EvaluationPackage:
        """Build EvaluationPackage from request, including RAG retrieval.

        Args:
            request: Validated evaluation request.

        Returns:
            EvaluationPackage with all fields populated.
        """
        retrieved_context: list[dict] = []
        warnings: list[str] = []

        # Run retrieval if source document is provided
        if request.source_document:
            try:
                # Short sources fit in full: preserve all evidence without requiring
                # a vector model download or discarding a short but relevant fact.
                if len(request.source_document) <= self.settings.chunk_size * self.settings.retrieval_top_k:
                    retrieved_context = [{"text": request.source_document, "score": 1.0, "metadata": {"source": "provided_text"}}]
                else:
                    retrieved_context = self.retriever.retrieve_from_text(
                        query=request.question,
                        document_text=request.source_document,
                        top_k=self.settings.retrieval_top_k,
                    )
                logger.info(
                    "Retrieved %d context chunks from source document",
                    len(retrieved_context),
                )
            except Exception as exc:
                logger.warning("Retrieval failed: %s", exc)
                warnings.append("Source document search is unavailable. This review could not use your source text. Try a shorter excerpt or check the backend's embedding model setup.")

        return EvaluationPackage(
            question=request.question,
            ai_response=request.ai_response,
            reference_answer=request.reference_answer,
            retrieved_context=retrieved_context,
            metadata={
                "has_source_document": bool(request.source_document),
                "has_reference": bool(request.reference_answer),
                "context_chunks": len(retrieved_context),
                "warnings": warnings,
            },
        )

    def _compute_verdict(
        self, metrics: dict[str, MetricResult]
    ) -> tuple[float | None, str, float]:
        """Compute weighted aggregate verdict from metric results.

        Args:
            metrics: Dict of metric name → MetricResult.

        Returns:
            Tuple of (overall_score, verdict_label, confidence).
        """
        available_scores = {name: m.score for name, m in metrics.items() if m.score is not None}
        if not available_scores:
            return None, "Insufficient Data", 0.0

        # Weighted score calculation
        overall_score = self._calculate_weighted_score(available_scores)

        # Heuristic estimates must not trigger authoritative "Incomplete" or
        # "Excellent" verdicts, including mixed AI/local reviews.
        if any(m.evaluated_with == "fallback" and m.score is not None for m in metrics.values()):
            return round(overall_score, 4), "Local Estimate", self._calculate_confidence(available_scores, metrics)

        # Labels distinguish missing evidence from demonstrated contradiction.
        accuracy = metrics.get("accuracy")
        evidence_conflict = accuracy is not None and any(c.verdict == "CONFLICTING" for c in accuracy.claims)
        verdict = self._apply_override_rules(available_scores)
        if available_scores.get("relevance", 1) < self.settings.off_topic_threshold:
            verdict = "Off-Topic"
            overall_score = min(overall_score, available_scores["relevance"])
        elif evidence_conflict:
            verdict = "Conflicting Evidence"
        elif verdict:
            overall_score *= self.settings.critical_penalty_factor
        elif available_scores.get("completeness", 1) <= .5:
            verdict = "Incomplete"
            overall_score = min(overall_score, self.settings.verdict_acceptable - .01)
        elif len(available_scores) < 4 or (accuracy is not None and accuracy.evidence_coverage is not None and accuracy.evidence_coverage < 1):
            verdict = "Limited Evidence"
        else:
            # A weak dimension must not disappear inside a high weighted average.
            weakest = min(available_scores.values())
            if weakest < self.settings.verdict_acceptable:
                overall_score = min(overall_score, self.settings.verdict_good - .01)
            elif weakest < self.settings.verdict_good:
                overall_score = min(overall_score, self.settings.verdict_excellent - .01)
            verdict = self._determine_standard_verdict(overall_score)

        overall_score = round(max(0.0, min(1.0, overall_score)), 4)
        confidence = self._calculate_confidence(available_scores, metrics)

        return overall_score, verdict, confidence

    def _calculate_weighted_score(self, available_scores: dict[str, float]) -> float:
        """Compute weighted average of available metrics, normalizing weights."""
        weights = {
            "relevance": self.settings.weight_relevance,
            "accuracy": self.settings.weight_accuracy,
            "groundedness": self.settings.weight_groundedness,
            "completeness": self.settings.weight_completeness,
        }
        total_weight = sum(weights[name] for name in available_scores)
        if total_weight == 0:
            return 0.0
        return sum(available_scores[name] * (weights[name] / total_weight) for name in available_scores)

    def _apply_override_rules(self, available_scores: dict[str, float]) -> Optional[str]:
        """Apply safety overrides based on configured metric thresholds."""
        # 1. Relevance check (Off-topic)
        relevance = available_scores.get("relevance")
        if relevance is not None and relevance < self.settings.off_topic_threshold:
            return "Off-Topic"

        # Demonstrated factual contradiction takes precedence over source coverage.
        accuracy = available_scores.get("accuracy")
        if accuracy is not None and accuracy < self.settings.factually_unreliable_threshold:
            return "Factually Unreliable"

        groundedness = available_scores.get("groundedness")
        if groundedness is not None and groundedness < self.settings.critical_hallucination_threshold:
            return "Unsupported Claims"

        return None

    def _determine_standard_verdict(self, score: float) -> str:
        """Determine standard verdict label based on score brackets."""
        if score >= self.settings.verdict_excellent:
            return "Excellent"
        if score >= self.settings.verdict_good:
            return "Good"
        if score >= self.settings.verdict_acceptable:
            return "Acceptable"
        if score >= self.settings.verdict_poor:
            return "Poor"
        return "Unacceptable"

    def _calculate_confidence(self, available_scores: dict[str, float], metrics: dict[str, MetricResult]) -> float:
        """Estimate evaluation confidence based on metric availability and source type."""
        # Backward-compatible field: coverage only, NOT a probability of correctness.
        return round(len(available_scores) / 4, 2)

    async def evaluate_batch(
        self, requests: list[EvaluationRequest]
    ) -> BatchEvaluationResponse:
        """Run batch evaluation pipeline concurrently.

        Args:
            requests: List of EvaluationRequest objects.

        Returns:
            BatchEvaluationResponse with aggregate metrics and list of individual results.
        """
        # Bound each batch so large uploads do not burst provider rate limits.
        semaphore = asyncio.Semaphore(3)

        async def evaluate_one(request):
            async with semaphore:
                return await self.evaluate(request)

        tasks = [evaluate_one(req) for req in requests]
        results: list[EvaluationResponse] = await asyncio.gather(*tasks)

        total_count = len(results)
        if total_count == 0:
            return BatchEvaluationResponse(
                results=[],
                total_count=0,
                average_score=None,
                verdict_counts={},
                average_metrics={},
            )

        # Calculate average overall score and verdict counts
        overall_scores = [r.overall_score for r in results if r.overall_score is not None]
        avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else None
        if avg_score is not None:
            avg_score = round(avg_score, 4)

        verdict_counts: dict[str, int] = {}
        for r in results:
            verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1

        # Calculate average scores for each metric
        metric_sums: dict[str, float] = {}
        metric_counts: dict[str, int] = {}

        for r in results:
            for metric_name, metric_res in r.metrics.items():
                if metric_res.score is not None:
                    metric_sums[metric_name] = metric_sums.get(metric_name, 0.0) + metric_res.score
                    metric_counts[metric_name] = metric_counts.get(metric_name, 0) + 1

        avg_metrics: dict[str, float] = {}
        for metric_name in metric_sums:
            count = metric_counts[metric_name]
            if count > 0:
                avg_metrics[metric_name] = round(metric_sums[metric_name] / count, 4)

        return BatchEvaluationResponse(
            results=results,
            total_count=total_count,
            average_score=avg_score,
            verdict_counts=verdict_counts,
            average_metrics=avg_metrics,
        )
