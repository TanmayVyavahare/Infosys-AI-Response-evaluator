"""Validation tests for the three evaluation agents.

Tests cover:
- Empty response handling
- Missing context and reference
- Factually correct content
- Hallucinated content
- Multi-part questions
- Programming questions
- History/science questions
- Scoring consistency and reasoning quality
"""

import asyncio
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.evaluation.base import EvaluationPackage
from app.evaluation.relevance import RelevanceEvaluator
from app.evaluation.accuracy import AccuracyEvaluator
from app.evaluation.groundedness import GroundednessEvaluator
from app.evaluation.completeness import CompletenessEvaluator
from app.retrieval.embedder import Embedder


# ── Shared fixtures ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def embedder():
    """Shared embedder instance (loads model once per module)."""
    return Embedder()


@pytest.fixture(scope="module")
def relevance_evaluator(embedder):
    """Relevance evaluator (fallback only, no LLM)."""
    return RelevanceEvaluator(llm_provider=None, embedder=embedder)


@pytest.fixture(scope="module")
def accuracy_evaluator(embedder):
    """Accuracy evaluator (fallback only, no LLM)."""
    return AccuracyEvaluator(llm_provider=None, embedder=embedder)


@pytest.fixture(scope="module")
def groundedness_evaluator(embedder):
    """Groundedness evaluator (fallback only, no LLM)."""
    return GroundednessEvaluator(llm_provider=None, embedder=embedder)


@pytest.fixture(scope="module")
def completeness_evaluator(embedder):
    """Completeness evaluator (fallback only, no LLM)."""
    return CompletenessEvaluator(llm_provider=None, embedder=embedder)


# ── Test Data ──────────────────────────────────────────────────────

HISTORY_QA = {
    "question": "Who was the first President of the United States and when did he serve?",
    "response_correct": "George Washington was the first President of the United States. He served from 1789 to 1797.",
    "response_hallucinated": "Benjamin Franklin was the first President of the United States. He served from 1780 to 1790 and invented electricity.",
    "reference": "George Washington served as the first President of the United States from 1789 to 1797.",
    "context": "George Washington (1732-1799) was the first President of the United States, serving two terms from April 30, 1789 to March 4, 1797. He was also the Commander-in-Chief of the Continental Army during the American Revolution.",
}

SCIENCE_QA = {
    "question": "What is photosynthesis and why is it important?",
    "response_correct": "Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen. It is important because it produces the oxygen we breathe and is the foundation of most food chains on Earth.",
    "response_irrelevant": "The stock market had a great day today. The Dow Jones rose by 500 points. Investors are optimistic about the economy.",
    "reference": "Photosynthesis is the biological process where plants use sunlight, CO2, and water to produce glucose and release oxygen. It is vital for life on Earth as it produces oxygen and organic compounds that form the base of food chains.",
}

PROGRAMMING_QA = {
    "question": "What is the difference between a list and a tuple in Python?",
    "response": "Lists are mutable, meaning you can modify their elements after creation. Tuples are immutable, meaning they cannot be changed. Lists use square brackets [] while tuples use parentheses (). Lists are generally used for collections of similar items, while tuples are used for fixed collections of related but different items.",
    "reference": "In Python, lists are mutable ordered collections denoted by square brackets [], while tuples are immutable ordered collections denoted by parentheses (). Lists can be modified after creation (append, remove, etc.), but tuples cannot. Tuples are slightly faster and use less memory.",
}

MULTI_PART_QA = {
    "question": "What are the advantages and disadvantages of renewable energy? Also, compare solar and wind energy.",
    "response_incomplete": "Renewable energy is good for the environment. Solar panels convert sunlight to electricity.",
    "response_complete": "Advantages of renewable energy include reduced carbon emissions, sustainability, lower long-term costs, and energy independence. Disadvantages include intermittency, high initial costs, land requirements, and weather dependency. Comparing solar and wind: solar energy works best in sunny regions and can be installed on rooftops, while wind energy requires open spaces with consistent wind. Solar has lower maintenance costs but wind turbines can generate power at night. Both are increasingly cost-competitive with fossil fuels.",
}

EMPTY_RESPONSE = {
    "question": "Explain quantum computing.",
    "response": "",
}

MATH_QA = {
    "question": "What is the Pythagorean theorem?",
    "response": "The Pythagorean theorem states that in a right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides. Mathematically, a² + b² = c², where c is the hypotenuse. For example, a 3-4-5 triangle satisfies this: 9 + 16 = 25.",
    "reference": "The Pythagorean theorem states that for a right triangle with legs a and b and hypotenuse c: a² + b² = c². A common example is the 3-4-5 right triangle.",
}


# ═══════════════════════════════════════════════════════════════════
# RELEVANCE EVALUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

class TestRelevanceEvaluator:
    """Test the Relevance Judge Agent."""

    def test_relevant_response_scores_high(self, relevance_evaluator):
        """A correct, on-topic response should score high on relevance."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            relevance_evaluator.evaluate(package)
        )
        assert result.metric_name == "relevance"
        assert result.score is not None
        assert result.score >= 0.4, f"Relevant response scored too low: {result.score}"
        assert result.reason
        assert result.evaluated_with == "fallback"

    def test_irrelevant_response_scores_low(self, relevance_evaluator):
        """A completely off-topic response should score low."""
        package = EvaluationPackage(
            question=SCIENCE_QA["question"],
            ai_response=SCIENCE_QA["response_irrelevant"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            relevance_evaluator.evaluate(package)
        )
        assert result.score is not None
        assert result.score < 0.5, f"Irrelevant response scored too high: {result.score}"
        assert len(result.weaknesses) > 0

    def test_programming_relevance(self, relevance_evaluator):
        """A programming answer should be relevant to a programming question."""
        package = EvaluationPackage(
            question=PROGRAMMING_QA["question"],
            ai_response=PROGRAMMING_QA["response"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            relevance_evaluator.evaluate(package)
        )
        assert result.score is not None
        assert result.score >= 0.4

    def test_empty_response(self, relevance_evaluator):
        """An empty response should not crash but score low."""
        package = EvaluationPackage(
            question=EMPTY_RESPONSE["question"],
            ai_response="  ",  # Near-empty
        )
        result = asyncio.get_event_loop().run_until_complete(
            relevance_evaluator.evaluate(package)
        )
        assert result.score is not None
        assert result.score <= 0.5

    def test_result_has_required_fields(self, relevance_evaluator):
        """Result should have all required MetricResult fields."""
        package = EvaluationPackage(
            question=SCIENCE_QA["question"],
            ai_response=SCIENCE_QA["response_correct"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            relevance_evaluator.evaluate(package)
        )
        assert result.metric_name == "relevance"
        assert result.reason
        assert isinstance(result.evidence, list)
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.suggestions, list)


# ═══════════════════════════════════════════════════════════════════
# ACCURACY EVALUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

class TestAccuracyEvaluator:
    """Test the Accuracy Judge Agent."""

    def test_correct_facts_with_reference(self, accuracy_evaluator):
        """Factually correct response with reference should score well."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            reference_answer=HISTORY_QA["reference"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package)
        )
        assert result.metric_name == "accuracy"
        assert result.score is not None
        assert result.score >= 0.4, f"Correct facts scored too low: {result.score}"
        assert result.evaluated_with == "fallback"

    def test_hallucinated_facts(self, accuracy_evaluator):
        """Factually wrong response should score lower than correct one."""
        package_correct = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            reference_answer=HISTORY_QA["reference"],
        )
        package_wrong = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_hallucinated"],
            reference_answer=HISTORY_QA["reference"],
        )
        result_correct = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package_correct)
        )
        result_wrong = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package_wrong)
        )
        # Correct should score higher than wrong
        assert result_correct.score is not None
        assert result_wrong.score is not None
        assert result_correct.score > result_wrong.score, (
            f"Correct ({result_correct.score}) should beat hallucinated ({result_wrong.score})"
        )

    def test_no_reference_no_context(self, accuracy_evaluator):
        """Without reference or context, should return 'cannot be verified'."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package)
        )
        assert result.score is None, "Score should be None when no baseline exists"
        assert "cannot be verified" in result.reason.lower()

    def test_accuracy_with_context_only(self, accuracy_evaluator):
        """When only context (no reference) is available, use context as baseline."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        result = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package)
        )
        assert result.score is not None
        assert result.score > 0.0

    def test_claim_extraction(self, accuracy_evaluator):
        """Claims should be extracted and individually scored."""
        package = EvaluationPackage(
            question=MATH_QA["question"],
            ai_response=MATH_QA["response"],
            reference_answer=MATH_QA["reference"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            accuracy_evaluator.evaluate(package)
        )
        assert len(result.claims) > 0, "Should extract atomic claims"
        for claim in result.claims:
            assert claim.claim  # Non-empty claim text
            assert claim.score is not None


# ═══════════════════════════════════════════════════════════════════
# GROUNDEDNESS / HALLUCINATION EVALUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

class TestGroundednessEvaluator:
    """Test the Hallucination Detection Agent."""

    def test_grounded_response(self, groundedness_evaluator):
        """Response supported by context should score well."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        result = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package)
        )
        assert result.metric_name == "groundedness"
        assert result.score is not None
        assert result.score >= 0.3, f"Grounded response scored too low: {result.score}"

    def test_hallucinated_response(self, groundedness_evaluator):
        """Response with claims NOT in context should score lower."""
        package_grounded = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        package_hallucinated = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_hallucinated"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        result_good = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package_grounded)
        )
        result_bad = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package_hallucinated)
        )
        assert result_good.score is not None
        assert result_bad.score is not None
        assert result_good.score > result_bad.score, (
            f"Grounded ({result_good.score}) should beat hallucinated ({result_bad.score})"
        )

    def test_no_context_returns_unverifiable(self, groundedness_evaluator):
        """Without context, should return 'cannot be verified' and score=None."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package)
        )
        assert result.score is None
        assert "cannot be verified" in result.reason.lower()

    def test_never_returns_perfect_100(self, groundedness_evaluator):
        """Groundedness should never return exactly 1.0 without very strong evidence."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        result = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package)
        )
        # Should be high but capped
        if result.score is not None:
            assert result.score <= 0.99 or all(
                c.score is not None and c.score >= 0.9
                for c in result.claims
            )

    def test_claim_support_classification(self, groundedness_evaluator):
        """Each claim should be classified as supported or unsupported."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_hallucinated"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )
        result = asyncio.get_event_loop().run_until_complete(
            groundedness_evaluator.evaluate(package)
        )
        assert len(result.claims) > 0
        # Should have at least some unsupported claims (hallucinations)
        unsupported = [c for c in result.claims if c.supported is False]
        assert len(unsupported) > 0, "Should detect unsupported claims in hallucinated response"


# ═══════════════════════════════════════════════════════════════════
# COMPLETENESS EVALUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

class TestCompletenessEvaluator:
    """Test the Completeness evaluator (included for package consistency)."""

    def test_complete_response(self, completeness_evaluator):
        """A comprehensive response to a multi-part question should score well."""
        package = EvaluationPackage(
            question=MULTI_PART_QA["question"],
            ai_response=MULTI_PART_QA["response_complete"],
        )
        result = asyncio.get_event_loop().run_until_complete(
            completeness_evaluator.evaluate(package)
        )
        assert result.score is not None
        assert result.score >= 0.2, f"Complete response scored too low: {result.score}"

    def test_incomplete_response(self, completeness_evaluator):
        """An incomplete response should score lower than a complete one."""
        package_complete = EvaluationPackage(
            question=MULTI_PART_QA["question"],
            ai_response=MULTI_PART_QA["response_complete"],
        )
        package_incomplete = EvaluationPackage(
            question=MULTI_PART_QA["question"],
            ai_response=MULTI_PART_QA["response_incomplete"],
        )
        result_complete = asyncio.get_event_loop().run_until_complete(
            completeness_evaluator.evaluate(package_complete)
        )
        result_incomplete = asyncio.get_event_loop().run_until_complete(
            completeness_evaluator.evaluate(package_incomplete)
        )
        assert result_complete.score is not None
        assert result_incomplete.score is not None
        assert result_complete.score > result_incomplete.score


# ═══════════════════════════════════════════════════════════════════
# CROSS-AGENT CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════

class TestCrossAgentConsistency:
    """Test that agents produce consistent, independent results."""

    def test_all_agents_run_independently(
        self, relevance_evaluator, accuracy_evaluator, groundedness_evaluator
    ):
        """All three agents should produce independent results for the same input."""
        package = EvaluationPackage(
            question=HISTORY_QA["question"],
            ai_response=HISTORY_QA["response_correct"],
            reference_answer=HISTORY_QA["reference"],
            retrieved_context=[
                {"text": HISTORY_QA["context"], "score": 0.9, "metadata": {}}
            ],
        )

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                relevance_evaluator.evaluate(package),
                accuracy_evaluator.evaluate(package),
                groundedness_evaluator.evaluate(package),
            )
        )

        # All should complete
        assert len(results) == 3
        # All should have different metric names
        names = {r.metric_name for r in results}
        assert names == {"relevance", "accuracy", "groundedness"}
        # All should have scores
        for r in results:
            assert r.score is not None
            assert r.reason
            assert r.evaluated_with == "fallback"

    def test_agents_have_reasoning(
        self, relevance_evaluator, accuracy_evaluator, groundedness_evaluator
    ):
        """Every agent must provide reasoning (not just a number)."""
        package = EvaluationPackage(
            question=SCIENCE_QA["question"],
            ai_response=SCIENCE_QA["response_correct"],
            reference_answer=SCIENCE_QA["reference"],
            retrieved_context=[
                {"text": SCIENCE_QA["response_correct"], "score": 0.9, "metadata": {}}
            ],
        )

        loop = asyncio.get_event_loop()
        for evaluator in [relevance_evaluator, accuracy_evaluator, groundedness_evaluator]:
            result = loop.run_until_complete(evaluator.evaluate(package))
            assert result.reason, f"{result.metric_name} has empty reason"
            assert len(result.reason) > 10, f"{result.metric_name} reason too short"
