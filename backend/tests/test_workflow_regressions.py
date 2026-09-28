"""Regression coverage for API validation and degraded review behavior.

These tests use deterministic collaborators and never send provider requests.
"""
import asyncio
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.requests import EvaluationRequest
from app.schemas.responses import EvaluationResponse
from app.services.evaluation_coordinator import EvaluationCoordinator


def test_batch_limits_rejected_before_evaluation():
    client = TestClient(app)
    item = {"question": "Question", "ai_response": "Answer"}
    assert client.post('/api/evaluate/batch', json=[]).status_code == 422
    assert client.post('/api/evaluate/batch', json=[item] * 51).status_code == 422
    assert client.post('/api/evaluate', json={"question": "  ", "ai_response": "Answer"}).status_code == 422


def test_explicit_none_disables_live_provider(monkeypatch):
    factory = Mock(side_effect=AssertionError('Must not instantiate a live provider'))
    monkeypatch.setattr('app.services.evaluation_coordinator.LLMProviderFactory.create_optional', factory)
    coordinator = EvaluationCoordinator(llm_provider=None)
    assert coordinator.llm_provider is None
    factory.assert_not_called()


def test_short_source_is_preserved_without_embedding_model():
    retriever = Mock()
    coordinator = EvaluationCoordinator(llm_provider=None, retriever=retriever)
    request = EvaluationRequest(question='What is the answer?', ai_response='42', source_document='The answer is 42.')
    package = asyncio.run(coordinator._build_package(request))
    assert package.context_text == 'The answer is 42.'
    retriever.retrieve_from_text.assert_not_called()


def test_failed_source_search_is_reported_to_user():
    retriever = Mock()
    retriever.retrieve_from_text.side_effect = RuntimeError('Embedding unavailable')
    coordinator = EvaluationCoordinator(llm_provider=None, retriever=retriever)
    request = EvaluationRequest(question='Question', ai_response='Answer', source_document='Long source. ' * 500)
    package = asyncio.run(coordinator._build_package(request))
    assert not package.has_context
    assert 'could not use your source text' in package.metadata['warnings'][0]


def test_batch_keeps_order_and_bounds_concurrency():
    coordinator = EvaluationCoordinator(llm_provider=None)
    active = 0
    peak = 0
    async def evaluate(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(.001)
        active -= 1
        return EvaluationResponse(metrics={}, overall_score=.5, verdict=request.question, confidence=1, processing_time_seconds=0)
    coordinator.evaluate = evaluate
    items = [EvaluationRequest(question=str(i), ai_response='Answer') for i in range(8)]
    result = asyncio.run(coordinator.evaluate_batch(items))
    assert [row.verdict for row in result.results] == [str(i) for i in range(8)]
    assert peak <= 3
    assert result.total_count == 8
    assert result.average_score == .5


def test_accuracy_without_evidence_does_not_invent_a_score():
    from app.evaluation.accuracy import AccuracyEvaluator
    from app.evaluation.base import EvaluationPackage
    provider = Mock()
    provider.generate = AsyncMock()
    evaluator = AccuracyEvaluator(llm_provider=provider)
    result = asyncio.run(evaluator.evaluate(EvaluationPackage(question='Who?', ai_response='Someone.')))
    assert result.score is None
    assert 'cannot be verified' in result.reason
    provider.generate.assert_not_called()
