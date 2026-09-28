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
        result = asyncio.run(
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
        result = asyncio.run(
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
        result = asyncio.run(
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
        result = asyncio.run(
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
        result = asyncio.run(
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

@pytest.mark.parametrize('evaluator_name', ['accuracy_evaluator', 'groundedness_evaluator'])
@pytest.mark.parametrize('answer', [HISTORY_QA['response_correct'], HISTORY_QA['response_hallucinated'],
    'George Washington was not the first President of the United States.',
    'The first President served from 1797 to 1789.'])
def test_local_similarity_never_certifies_facts(request, evaluator_name, answer):
    evaluator = request.getfixturevalue(evaluator_name)
    package = EvaluationPackage(question=HISTORY_QA['question'], ai_response=answer,
        reference_answer=HISTORY_QA['reference'], retrieved_context=[{'text': HISTORY_QA['context']}])
    result = asyncio.run(evaluator.evaluate(package))
    assert result.score is None
    assert result.evidence_coverage == 0
    assert result.claims
    assert all(c.verdict == 'UNVERIFIABLE' and c.supported is None and c.score is None for c in result.claims)
    assert result.review_warning
    assert not result.strengths


@pytest.mark.parametrize('evaluator_name', ['accuracy_evaluator', 'groundedness_evaluator'])
def test_missing_evidence_is_explicit(request, evaluator_name):
    result = asyncio.run(request.getfixturevalue(evaluator_name).evaluate(
        EvaluationPackage(question=HISTORY_QA['question'], ai_response=HISTORY_QA['response_correct'])))
    assert result.score is None
    assert 'cannot be verified' in result.reason.lower()


class TestCompletenessEvaluator:
    """Test the Completeness evaluator (included for package consistency)."""

    def test_complete_response(self, completeness_evaluator):
        """A comprehensive response to a multi-part question should score well."""
        package = EvaluationPackage(
            question=MULTI_PART_QA["question"],
            ai_response=MULTI_PART_QA["response_complete"],
        )
        result = asyncio.run(
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
        result_complete = asyncio.run(
            completeness_evaluator.evaluate(package_complete)
        )
        result_incomplete = asyncio.run(
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

        async def evaluate_all():
            return await asyncio.gather(
                relevance_evaluator.evaluate(package),
                accuracy_evaluator.evaluate(package),
                groundedness_evaluator.evaluate(package),
            )
        results = asyncio.run(evaluate_all())

        # All should complete
        assert len(results) == 3
        # All should have different metric names
        names = {r.metric_name for r in results}
        assert names == {"relevance", "accuracy", "groundedness"}
        # All should have scores
        for r in results:
            assert (r.score is not None) == (r.metric_name == 'relevance')
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

        for evaluator in [relevance_evaluator, accuracy_evaluator, groundedness_evaluator]:
            result = asyncio.run(evaluator.evaluate(package))
            assert result.reason, f"{result.metric_name} has empty reason"
            assert len(result.reason) > 10, f"{result.metric_name} reason too short"


@pytest.mark.parametrize('question,answer,reference', [
    (HISTORY_QA['question'], 'George Washington was the first President of the United States, serving from 1789 to 1797.', HISTORY_QA['reference']),
    ('What is the capital of France?', 'Paris.', 'Paris is the capital of France.'),
    ('What is 2 + 2?', '4', '4'),
])
def test_answer_shaped_reference_improves_local_relevance(relevance_evaluator, question, answer, reference):
    result = asyncio.run(relevance_evaluator.evaluate(
        EvaluationPackage(question=question, ai_response=answer, reference_answer=reference)))
    assert result.score >= .8


def test_screenshot_answer_covers_both_requirements(completeness_evaluator):
    package = EvaluationPackage(question=HISTORY_QA['question'],
        ai_response='George Washington was the first President of the United States, serving from 1789 to 1797.',
        reference_answer=HISTORY_QA['reference'])
    full = asyncio.run(completeness_evaluator.evaluate(package))
    assert len(full.requirements) == 2
    assert full.score == 1.0
    package.ai_response = 'George Washington was the first President of the United States.'
    partial = asyncio.run(completeness_evaluator.evaluate(package))
    assert partial.score < full.score
