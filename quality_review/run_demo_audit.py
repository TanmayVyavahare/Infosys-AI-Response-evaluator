"""Explicit live Groq audit of diverse interview-style inputs; consumes API quota."""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.schemas.requests import EvaluationRequest
from app.services.evaluation_coordinator import EvaluationCoordinator
from app.services.llm_provider import GroqProvider

HISTORY_Q = 'Who was the first President of the United States and when did he serve?'
HISTORY_REF = 'George Washington served as the first President of the United States from 1789 to 1797.'
# Bounds are declared before running. They express case expectations, not
# calibrated accuracy probabilities or a representative benchmark.
CASES = [
    ('history_complete', HISTORY_Q, 'George Washington was the first President of the United States, serving from 1789 to 1797.', HISTORY_REF,
     {'relevance': [.9, 1], 'accuracy': [1, 1], 'completeness': [1, 1]}),
    ('history_incomplete', HISTORY_Q, 'George Washington was the first President of the United States.', HISTORY_REF,
     {'accuracy': [1, 1], 'completeness': [0, .5]}),
    ('history_wrong_dates', HISTORY_Q, 'George Washington was the first President of the United States, serving from 1780 to 1790.', HISTORY_REF,
     {'accuracy': [0, .5], 'completeness': [1, 1]}),
    ('short_answer', 'What is the capital of France?', 'Paris.', 'Paris is the capital of France.',
     {'relevance': [.9, 1], 'accuracy': [1, 1], 'completeness': [1, 1]}),
    ('programming_paraphrase', 'How do Python lists and tuples differ in mutability?', 'A list can be changed after creation; a tuple cannot.', 'Python lists are mutable. Tuples are immutable.',
     {'accuracy': [1, 1], 'completeness': [1, 1]}),
    ('unit_conversion', 'Convert 2.5 hours to minutes.', '150 minutes.', 'One hour equals 60 minutes, so 2.5 hours equals 150 minutes.',
     {'accuracy': [1, 1], 'completeness': [1, 1]}),
    ('arithmetic_error', 'What is 3 times 7?', '3 times 7 equals 24.', '3 times 7 equals 21.',
     {'accuracy': [0, 0], 'completeness': [1, 1]}),
    ('reversed_roles', 'Who defeated whom in the final?', 'Bob defeated Alice.', 'Alice defeated Bob in the final.',
     {'accuracy': [0, 0], 'completeness': [1, 1]}),
    ('negation', 'Does the plan include phone support?', 'Yes, phone support is included.', 'The plan includes email support only. Phone support is not included.',
     {'accuracy': [0, 0], 'completeness': [1, 1]}),
    ('unknown_fact', 'When was Cedar Instruments founded?', 'Cedar Instruments was founded in 1999.', 'Cedar Instruments manufactures weather sensors.',
     {'accuracy': None, 'completeness': [1, 1]}),
    ('unrequested_reference_detail', 'What is the monthly price?', '20 credits.', 'The monthly price is 20 credits. The plan includes five projects and a 14-day trial.',
     {'accuracy': [1, 1], 'completeness': [1, 1]}),
    ('hindi_short_answer', 'भारत की राजधानी क्या है?', 'नई दिल्ली।', 'भारत की राजधानी नई दिल्ली है।',
     {'relevance': [.9, 1], 'accuracy': [1, 1], 'completeness': [1, 1]}),
]


async def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise SystemExit('Refusing to overwrite an audit run.')
    selected = set(sys.argv[2:])
    if selected - {c[0] for c in CASES}:
        raise SystemExit('Unknown case ID.')
    provider = GroqProvider()
    coordinator = EvaluationCoordinator(llm_provider=provider)
    rows = []
    try:
        for name, question, answer, reference, expected in CASES:
            if selected and name not in selected:
                continue
            request = EvaluationRequest(question=question, ai_response=answer, reference_answer=reference)
            report = await coordinator.evaluate(request)
            failures = []
            for metric, bounds in expected.items():
                actual = report.metrics[metric]
                if actual.evaluated_with != 'llm':
                    failures.append(f'{metric}: no live AI judgment')
                if bounds is None:
                    if actual.score is not None:
                        failures.append(f'{metric}: expected unavailable, got {actual.score}')
                elif actual.score is None or not bounds[0] <= actual.score <= bounds[1]:
                    failures.append(f'{metric}: expected {bounds}, got {actual.score}')
            rows.append(dict(id=name, input=request.model_dump(), expected=expected,
                             passed=not failures, failures=failures, report=report.model_dump()))
            output.write_text(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                model=provider._model, cases=rows), ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(dict(id=name, passed=not failures, failures=failures,
                                  scores={k: v.score for k, v in report.metrics.items()})), flush=True)
            if (any('limit' in (m.review_warning or '') for m in report.metrics.values())
                    or all(m.evaluated_with != 'llm' for m in report.metrics.values())):
                break  # Do not hammer a provider that is unavailable.
            await asyncio.sleep(8)
    finally:
        if provider._client:
            await provider._client.close()
    raise SystemExit(0 if rows and all(r['passed'] for r in rows) else 1)


if __name__ == '__main__':
    asyncio.run(main())
