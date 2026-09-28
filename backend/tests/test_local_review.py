"""Failure-path regressions independent of the live provider and native ML stack."""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.evaluation.accuracy import AccuracyEvaluator
from app.evaluation.base import EvaluationPackage
from app.evaluation.completeness import CompletenessEvaluator
from app.evaluation.fallbacks.concepts import ConceptExtractor
from app.evaluation.groundedness import GroundednessEvaluator
from app.schemas.common import MetricResult
from app.services.evaluation_coordinator import EvaluationCoordinator


@pytest.mark.parametrize('question,count', [
    ('Who was the first President of the United States and when did he serve?', 2),
    ('What is the difference between a list and a tuple in Python?', 1),
    ('Explain bread and butter.', 1),
    ('Name one benefit of caching.', 1),
    ('What are the advantages and disadvantages of solar energy? Also, compare solar and wind.', 3),
    ('What is an API? Give an example.', 2),
    ('1. Define inertia. 2. Give an example.', 2),
    ('Describe "New York".', 1),
])
def test_requirements_follow_question_without_inventing_extra_tasks(question, count):
    reqs = ConceptExtractor().extract_requirements(question, 'Extra information includes several unrelated details.')
    assert len(reqs) == count
    assert all('Extra information' not in r['text'] for r in reqs)


@pytest.mark.parametrize('cls', [AccuracyEvaluator, GroundednessEvaluator])
@pytest.mark.parametrize('answer,reference', [
    ('Phone support is included.', 'Phone support is not included.'),
    ('Alice defeated Bob.', 'Bob defeated Alice.'),
    ('The service costs 200 credits.', 'The service costs 20 credits.'),
    ('The trial lasts 336 hours.', 'The trial lasts 14 days.'),
    ('Paris.', 'Paris.'),
])
def test_unavailable_ai_abstains_instead_of_guessing_facts(cls, answer, reference):
    provider = Mock(generate=AsyncMock(side_effect=RuntimeError('429 rate limit')))
    embedder = Mock()
    result = asyncio.run(cls(llm_provider=provider, embedder=embedder).evaluate(
        EvaluationPackage(question='Answer the question.', ai_response=answer,
                          reference_answer=reference, retrieved_context=[{'text': reference}])) )
    assert result.score is None
    assert result.evidence_coverage == 0
    assert 'usage limit' in result.review_warning
    assert all(c.verdict == 'UNVERIFIABLE' for c in result.claims)
    embedder.embed_text.assert_not_called()
    embedder.semantic_similarity.assert_not_called()


@pytest.mark.parametrize('score', [0, .5, 1])
def test_local_scores_never_produce_definitive_quality_verdict(score):
    metrics = {name: MetricResult(metric_name=name, score=score, reason='Estimate', evaluated_with='fallback')
               for name in ('relevance', 'completeness')}
    overall, verdict, coverage = EvaluationCoordinator(llm_provider=None)._compute_verdict(metrics)
    assert verdict == 'Local Estimate'
    assert overall == score
    assert coverage == .5


def test_successful_fallback_discloses_invalid_ai_output():
    evaluator = CompletenessEvaluator(llm_provider=Mock(generate=AsyncMock(return_value='invalid JSON')))
    evaluator._evaluate_with_fallback = Mock(return_value=MetricResult(metric_name='completeness', score=.5, reason='Estimate'))
    result = asyncio.run(evaluator.evaluate(EvaluationPackage(question='What is it?', ai_response='An example.')))
    assert 'could not complete a valid review' in result.review_warning
