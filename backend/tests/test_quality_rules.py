"""Deterministic regressions for problems found by the live quality audit."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.evaluation.accuracy import AccuracyEvaluator
from app.evaluation.base import EvaluationPackage
from app.evaluation.completeness import CompletenessEvaluator
from app.evaluation.groundedness import GroundednessEvaluator
from app.schemas.common import MetricResult, ClaimDetail
from app.services.evaluation_coordinator import EvaluationCoordinator
from app.services.llm_provider import GroqProvider
from app.config.settings import Settings
from app.core.exceptions import LLMProviderError
from app.utils.json_validator import validate_llm_response


def payload(claims=None, requirements=None, score=1):
    return {'score':score, 'reason':'Assessment from supplied evidence.', 'claims':claims or [], 'requirements':requirements or []}


def claim(verdict):
    return {'claim':'A factual assertion.', 'verdict':verdict, 'evidence':'Evidence for this classification.', 'contradicting_quote':'The price is 20.' if verdict == 'INCORRECT' else None}


def metrics(**scores):
    return {name:MetricResult(metric_name=name, score=scores.get(name, 1), reason='Test', evaluated_with='llm') for name in ('relevance','accuracy','groundedness','completeness')}


def test_unknown_claim_is_neither_false_nor_scored_as_zero():
    data = validate_llm_response(json.dumps(payload([claim('UNVERIFIABLE')], score=None)), 'accuracy')
    result = AccuracyEvaluator()._build_result_from_llm(data)
    assert result.score is None
    assert result.claims[0].supported is None
    assert result.claims[0].verdict == 'UNVERIFIABLE'
    assert result.claims[0].score is None
    assert result.evidence_coverage == 0


def test_completeness_receives_source_to_assess_justified_abstention():
    package = EvaluationPackage(question='Using only the source, what year?', ai_response='The source does not say.', retrieved_context=[{'text':'Only a monthly price is specified.'}])
    prompt, _ = CompletenessEvaluator()._build_llm_prompt(package)
    assert package.context_text in prompt


def test_mixed_verifiable_and_unknown_claims_disclose_partial_coverage():
    result = AccuracyEvaluator()._build_result_from_llm(payload([claim('CORRECT'),claim('UNVERIFIABLE')],score=.1))
    assert result.score == 1
    assert result.evidence_coverage == .5
    inputs = metrics()
    inputs['accuracy'] = result
    assert EvaluationCoordinator(llm_provider=None)._compute_verdict(inputs)[1] == 'Limited Evidence'


def test_accuracy_is_derived_from_claims_not_inconsistent_model_score():
    result = AccuracyEvaluator()._build_result_from_llm(payload([claim('CORRECT'),claim('INCORRECT')],score=1))
    assert result.score == .5
    assert result.claims[1].supported is False


def test_perfect_accuracy_does_not_report_another_dimensions_omissions():
    data = payload([claim('CORRECT')])
    data['weaknesses'] = ['Missing other requested details.']
    data['suggestions'] = ['Answer all parts of the question.']
    result = AccuracyEvaluator()._build_result_from_llm(data)
    assert result.weaknesses == []
    assert result.suggestions == []


def test_groundedness_distinguishes_unsupported_from_contradicted():
    result = GroundednessEvaluator()._build_result_from_llm(payload([claim('SUPPORTED'),claim('UNSUPPORTED'),claim('CONTRADICTED')],score=1))
    assert result.score == .3333
    assert [c.verdict for c in result.claims] == ['SUPPORTED','UNSUPPORTED','CONTRADICTED']


def test_one_of_four_requirements_cannot_receive_excellent():
    requirements = [{'requirement':str(i), 'status': 'covered' if i==0 else 'missing', 'evidence':'Answer' if i==0 else 'Not addressed'} for i in range(4)]
    result = CompletenessEvaluator()._build_result_from_llm(payload(requirements=requirements,score=1))
    assert result.score == .25
    inputs = metrics()
    inputs['completeness'] = result
    overall, verdict, _ = EvaluationCoordinator(llm_provider=None)._compute_verdict(inputs)
    assert verdict == 'Incomplete'
    assert overall < .55


@pytest.mark.parametrize('scores,verdict', [
    ({}, 'Excellent'),
    ({'accuracy':None,'groundedness':None}, 'Limited Evidence'),
    ({'accuracy':None,'groundedness':0}, 'Unsupported Claims'),
    ({'accuracy':0,'groundedness':0}, 'Factually Unreliable'),
    ({'relevance':0,'accuracy':0,'groundedness':0}, 'Off-Topic'),
    ({'completeness':.5}, 'Incomplete'),
])
def test_overall_verdict_preserves_important_limitations(scores,verdict):
    assert EvaluationCoordinator(llm_provider=None)._compute_verdict(metrics(**scores))[1] == verdict


def test_conflicting_evidence_does_not_become_certain_hallucination():
    inputs = metrics(accuracy=None,groundedness=0)
    inputs['accuracy'].claims = [ClaimDetail(claim='Price',verdict='CONFLICTING',supported=None)]
    assert EvaluationCoordinator(llm_provider=None)._compute_verdict(inputs)[1] == 'Conflicting Evidence'


def test_coverage_is_not_boosted_for_using_an_llm():
    _,_,coverage = EvaluationCoordinator(llm_provider=None)._compute_verdict(metrics(accuracy=None,groundedness=None))
    assert coverage == .5


@pytest.mark.parametrize('score', [float('nan'), float('inf'), -1, 1.2, 85, True, '0.9'])
def test_invalid_or_ambiguous_scores_are_rejected(score):
    assert validate_llm_response(json.dumps(payload(score=score)), 'relevance') is None


@pytest.mark.parametrize('bad_claim', [None, {'claim':'Test','verdict':'MAYBE'}, {'claim':'Test','verdict':None}, {'claim':'Test','verdict':'CORRECT','evidence':[]}])
def test_malformed_claims_trigger_retry_instead_of_false_certainty(bad_claim):
    assert validate_llm_response(json.dumps(payload([bad_claim])), 'accuracy') is None


def test_missing_claim_evidence_cannot_support_a_fact():
    assert validate_llm_response(json.dumps(payload([{'claim':'X','verdict':'CORRECT'}])), 'accuracy') is None


def test_factual_error_requires_a_real_opposing_quote():
    package = EvaluationPackage(question='Price?', ai_response='50', reference_answer='The price is 20.')
    evaluator = AccuracyEvaluator()
    data = payload([claim('INCORRECT')])
    assert evaluator._has_valid_contradiction_quotes(data, package)
    data['claims'][0]['contradicting_quote'] = 'The price is 30.'
    assert not evaluator._has_valid_contradiction_quotes(data, package)
    data['claims'][0]['contradicting_quote'] = None
    assert validate_llm_response(json.dumps(data), 'accuracy') is None


def test_groq_waits_for_rate_limit_then_returns_the_real_review(monkeypatch):
    class RateLimit(Exception):
        status_code=429
        response=SimpleNamespace(headers={'retry-after':'2'})
    monkeypatch.setattr('app.services.llm_provider.get_settings', lambda: Settings(_env_file=None, groq_api_key='test-only-key', llm_model='test-model'))
    provider=GroqProvider()
    create=AsyncMock(side_effect=[RateLimit('limited'), SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='OK'))])])
    provider._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    sleep=AsyncMock()
    monkeypatch.setattr('app.services.llm_provider.asyncio.sleep',sleep)
    assert asyncio.run(provider.generate('test')) == 'OK'
    assert create.await_count == 2
    sleep.assert_awaited_once_with(3)


def test_missing_contradiction_quote_is_retried_as_unverifiable():
    bad = payload([{'claim':'Released in 2020.', 'verdict':'INCORRECT', 'evidence':'The source does not mention a year.'}],score=0)
    corrected = payload([{'claim':'Released in 2020.', 'verdict':'UNVERIFIABLE', 'evidence':'The source does not mention a year.'}],score=None)
    provider = SimpleNamespace(generate=AsyncMock(side_effect=[json.dumps(bad), json.dumps(corrected)]))
    evaluator = AccuracyEvaluator(llm_provider=provider)
    result = asyncio.run(evaluator.evaluate(EvaluationPackage(question='Release year?', ai_response='2020.', reference_answer='The product is blue.')))
    assert result.score is None
    assert result.claims[0].verdict == 'UNVERIFIABLE'
    assert provider.generate.await_count == 2


def test_daily_quota_does_not_retry_early_or_hide_the_cause(monkeypatch):
    class RateLimit(Exception):
        status_code = 429
        response = SimpleNamespace(headers={})
    monkeypatch.setattr('app.services.llm_provider.get_settings', lambda: Settings(_env_file=None, groq_api_key='test-only-key', llm_model='test-model'))
    provider = GroqProvider()
    create = AsyncMock(side_effect=RateLimit('tokens per day (TPD). Please try again in 3m40.75s.'))
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    sleep = AsyncMock()
    monkeypatch.setattr('app.services.llm_provider.asyncio.sleep', sleep)
    with pytest.raises(LLMProviderError, match='daily token limit'):
        asyncio.run(provider.generate('test'))
    assert create.await_count == 1
    sleep.assert_not_awaited()


def test_report_preserves_provider_failure_when_local_review_is_unavailable(monkeypatch):
    evaluator = CompletenessEvaluator(llm_provider=SimpleNamespace(generate=AsyncMock(side_effect=LLMProviderError('Groq daily token limit reached.'))))
    def unavailable(_package):
        raise RuntimeError('local dependency blocked')
    monkeypatch.setattr(evaluator, '_evaluate_with_fallback', unavailable)
    result = asyncio.run(evaluator.evaluate(EvaluationPackage(question='Test?',ai_response='Test.')))
    assert result.score is None
    assert 'daily token limit' in result.reason
    assert 'Local review is also unavailable' in result.reason
