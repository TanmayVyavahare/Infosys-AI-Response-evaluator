"""Validation tests for the batch evaluation service and endpoint.
"""

import asyncio
import pytest
from app.evaluation.base import EvaluationPackage
from app.schemas.requests import EvaluationRequest
from app.services.evaluation_coordinator import EvaluationCoordinator


@pytest.fixture(scope="module")
def coordinator():
    """Module-level evaluation coordinator instance in fallback mode."""
    return EvaluationCoordinator(llm_provider=None)


def test_evaluate_batch_coordinator_empty(coordinator):
    """Empty batch should return correct empty aggregate response."""
    result = asyncio.get_event_loop().run_until_complete(
        coordinator.evaluate_batch([])
    )
    assert result.total_count == 0
    assert result.results == []
    assert result.average_score is None
    assert result.verdict_counts == {}
    assert result.average_metrics == {}


def test_evaluate_batch_coordinator_multiple(coordinator):
    """Multiple evaluations in batch should succeed and aggregate stats."""
    requests = [
        EvaluationRequest(
            question="Who was the first president of the USA?",
            ai_response="George Washington served as the first president of the United States from 1789 to 1797.",
            reference_answer="George Washington was the first US president.",
        ),
        EvaluationRequest(
            question="What is photosythesis?",
            ai_response="Photosynthesis is off-topic. The stock market is down.",
            reference_answer="Photosynthesis is the process plants use to make food.",
        ),
    ]

    result = asyncio.get_event_loop().run_until_complete(
        coordinator.evaluate_batch(requests)
    )

    assert result.total_count == 2
    assert len(result.results) == 2
    
    # Verify individual results
    r1, r2 = result.results
    assert r1.overall_score is not None
    assert r2.overall_score is not None
    
    # r1 should score better than r2 (which is off-topic/poor)
    assert r1.overall_score > r2.overall_score
    
    # Verify aggregate stats
    assert result.average_score is not None
    assert result.average_score == round((r1.overall_score + r2.overall_score) / 2, 4)
    
    # Verdict counts should contain the labels
    assert r1.verdict in result.verdict_counts
    assert r2.verdict in result.verdict_counts
    assert sum(result.verdict_counts.values()) == 2

    # Average metrics should calculate average score per dimension
    assert "relevance" in result.average_metrics
    assert "accuracy" in result.average_metrics
    assert "completeness" in result.average_metrics
