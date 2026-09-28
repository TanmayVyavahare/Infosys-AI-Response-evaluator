"""Relevance Evaluator Agent.

Determines whether the AI response answers the user's question.
Ignores factual correctness and hallucination.

LLM path: Answer relevancy prompt → JSON score.
Fallback path: Sentence embedding cosine similarity + NER overlap + topic similarity.
"""

from __future__ import annotations

from app.evaluation.fallbacks.alignment import content_tokens

from app.evaluation.base import BaseEvaluator, EvaluationPackage
from app.evaluation.fallbacks.ner import NERExtractor
from app.evaluation.fallbacks.semantic import SemanticFallback
from app.evaluation.prompts.relevance import (
    RELEVANCE_SYSTEM_MESSAGE,
    build_relevance_prompt,
)
from app.schemas.common import MetricResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RelevanceEvaluator(BaseEvaluator):
    """Evaluate the relevance of an AI response to the question.

    This evaluator ONLY checks whether the response addresses the
    question's topic. It does NOT check factual accuracy, hallucination,
    or completeness.
    """

    @property
    def metric_name(self) -> str:
        return "relevance"

    def _build_llm_prompt(
        self, package: EvaluationPackage
    ) -> tuple[str, str]:
        """Build relevance prompt for LLM evaluation.

        Args:
            package: EvaluationPackage.

        Returns:
            Tuple of (prompt, system_message).
        """
        prompt = build_relevance_prompt(
            question=package.question,
            ai_response=package.ai_response,
        )
        return prompt, RELEVANCE_SYSTEM_MESSAGE

    def _evaluate_with_fallback(
        self, package: EvaluationPackage
    ) -> MetricResult:
        """Evaluate relevance using local NLP.

        Combines direct semantic similarity, topic similarity, and named entity overlap.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult with weighted score from local signals.
        """
        semantic = SemanticFallback(self.embedder)
        ner = NERExtractor()

        # Extract signals
        direct_sim = semantic.text_similarity(package.question, package.ai_response)
        topic_sim = semantic.topic_similarity(package.question, package.ai_response)
        q_entities = ner.extract_entities(package.question)
        r_entities = ner.extract_entities(package.ai_response)
        entity_overlap = ner.entity_overlap(q_entities, r_entities)

        # 1. Compute composite score
        score = self._calculate_fallback_score(direct_sim, topic_sim, entity_overlap)

        # Compare answer to answer, too: short answers and paraphrases often
        # share little wording with their question. This does not verify facts.
        reference_sim = None
        if package.has_reference:
            reference_sim = semantic.text_similarity(package.reference_answer, package.ai_response)
            answer_tokens = content_tokens(package.ai_response)
            if answer_tokens and answer_tokens <= content_tokens(package.reference_answer):
                reference_sim = max(reference_sim, 0.9)
            score = round(max(score, reference_sim), 4)

        # 2. Build explanation reason and evidence list
        reason = self._determine_relevance_reason(score)
        evidence = [
            f"Semantic similarity: {direct_sim:.3f}",
            f"Topic similarity: {topic_sim:.3f}",
            f"Entity overlap: {entity_overlap:.3f}",
        ]

        # 3. Generate strengths, weaknesses, and suggestions
        strengths, weaknesses, suggestions = self._generate_feedback(
            direct_sim, topic_sim, entity_overlap, bool(q_entities)
        )
        if reference_sim is not None:
            evidence.append(f"Reference answer similarity: {reference_sim:.3f}")
            if reference_sim >= self.settings.similarity_threshold_high:
                strengths = ["Response closely aligns with the supplied reference answer."]
                weaknesses, suggestions = [], []

        return MetricResult(
            metric_name=self.metric_name,
            score=score,
            reason=reason,
            evidence=evidence,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            evaluated_with="fallback",
        )

    def _calculate_fallback_score(self, direct_sim: float, topic_sim: float, entity_overlap: float) -> float:
        """Compute weighted relevance score clamped to [0, 1]."""
        raw_score = (
            0.45 * direct_sim
            + 0.35 * topic_sim
            + 0.20 * entity_overlap
        )
        return round(max(0.0, min(1.0, raw_score)), 4)

    def _determine_relevance_reason(self, score: float) -> str:
        """Determine a descriptive reason based on the overall relevance score."""
        if score >= self.settings.similarity_threshold_high:
            return "The response is highly relevant to the question based on semantic and topic analysis."
        if score >= self.settings.similarity_threshold_medium:
            return "The response is moderately relevant to the question."
        if score >= self.settings.similarity_threshold_low:
            return "The response has limited relevance to the question."
        return "The response appears largely irrelevant to the question."

    def _generate_feedback(
        self, direct_sim: float, topic_sim: float, entity_overlap: float, has_q_entities: bool
    ) -> tuple[list[str], list[str], list[str]]:
        """Generate structured strengths, weaknesses, and suggestions."""
        strengths: list[str] = []
        weaknesses: list[str] = []
        suggestions: list[str] = []

        # Evaluate direct semantic similarity alignment
        if direct_sim >= self.settings.similarity_threshold_high:
            strengths.append("Response is semantically aligned with the question")
        elif direct_sim >= self.settings.similarity_threshold_medium:
            strengths.append("Response shows moderate semantic alignment with the question")
        else:
            weaknesses.append("Response has low semantic alignment with the question")
            suggestions.append("Ensure the response directly addresses the question topic")

        # Evaluate topic similarity
        if topic_sim >= self.settings.similarity_threshold_high:
            strengths.append("Response covers the same topic as the question")
        elif topic_sim < self.settings.similarity_threshold_low:
            weaknesses.append("Response appears to discuss a different topic")
            suggestions.append("Refocus the response on the subject matter of the question")

        # Evaluate entity overlap
        if entity_overlap > 0.5:
            strengths.append("Response mentions key entities from the question")
        elif entity_overlap < 0.1 and has_q_entities:
            weaknesses.append("Response does not reference key entities from the question")

        return strengths, weaknesses, suggestions
