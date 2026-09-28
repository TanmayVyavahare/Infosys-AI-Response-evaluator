"""Check saved live reports against case-specific, human-defined expectations.

Usage: python quality_review/check_audit.py after.json [refinement.json ...]
Later files replace earlier reports for the same case. No API calls are made.
"""
import json
import sys
from pathlib import Path


def assess(case_id, report):
    scores = {name: metric['score'] for name, metric in report['metrics'].items()}
    issues = []

    def require(condition, message):
        if not condition:
            issues.append(message)

    def high(*names):
        return all(scores.get(name) is not None and scores[name] >= .8 for name in names)

    def low(*names):
        return all(scores.get(name) is not None and scores[name] <= .1 for name in names)

    for name, metric in report['metrics'].items():
        if metric['score'] is not None:
            require(metric['evaluated_with'] == 'llm', f'{name} was not scored by the live model')

    if case_id in ('correct', 'paraphrase', 'approximation', 'unit_conversion', 'reference_extra_detail'):
        require(high('relevance', 'accuracy', 'groundedness', 'completeness'), 'A valid equivalent answer was penalized')
        require(report['verdict'] in ('Good', 'Excellent'), 'Valid answer did not get a positive verdict')
    elif case_id in ('wrong_numbers', 'negation', 'answer_injection', 'source_injection', 'wrong_date'):
        require(low('accuracy', 'groundedness'), 'Contradicted facts were not rejected')
        require(high('relevance', 'completeness'), 'Factual errors leaked into relevance or coverage')
        require(report['overall_score'] <= .3, 'Wrong facts received a high overall score')
    elif case_id == 'off_topic':
        require(low('relevance', 'completeness'), 'Off-topic answer received topic/coverage credit')
        require(report['verdict'] == 'Off-Topic', 'Missing off-topic verdict')
    elif case_id == 'incomplete':
        require(high('relevance', 'accuracy', 'groundedness'), 'Omissions leaked into another dimension')
        require(scores['completeness'] == .25, 'One of four requested items must mean 25% coverage')
        require(report['verdict'] == 'Incomplete' and report['overall_score'] < .55, 'Severe omissions not reflected in overall verdict')
    elif case_id == 'unsupported_extra':
        require(report['verdict'] == 'Limited Evidence', 'Unsupported addition received unconditional endorsement')
        require(0 < scores['groundedness'] < 1, 'Mixed source support not reflected')
        require(any(c.get('verdict') == 'UNVERIFIABLE' for c in report['metrics']['accuracy']['claims']), 'Unknown claim was not distinguished from false')
        require(any(c.get('verdict') == 'UNSUPPORTED' for c in report['metrics']['groundedness']['claims']), 'Unsupported source claim not identified')
    elif case_id in ('unknown_fact', 'unknown_location'):
        require(scores['accuracy'] is None, 'Missing evidence was treated as proof of factual error')
        require(low('groundedness') and report['verdict'] == 'Unsupported Claims', 'Missing source support not reported')
        require(high('relevance', 'completeness'), 'Unverifiable answer incorrectly treated as absent')
    elif case_id == 'no_evidence':
        require(scores['accuracy'] is None and scores['groundedness'] is None, 'Facts were scored without evidence')
        require(report['verdict'] == 'Limited Evidence' and report['confidence'] == .5, 'Missing checks not reflected in verdict/coverage')
    elif case_id == 'appropriate_abstention':
        require(high('relevance', 'completeness'), 'Justified source-only abstention was penalized')
        require(all(scores[k] is None or scores[k] >= .8 for k in ('accuracy', 'groundedness')), 'Abstention was mistaken for a fabricated fact')
    elif case_id == 'conflicting_evidence':
        require(report['verdict'] == 'Conflicting Evidence', 'Evidence conflict mistaken for a definite factual failure')
        require(any(c.get('verdict') == 'CONFLICTING' for c in report['metrics']['accuracy']['claims']), 'Conflict not disclosed at claim level')
    else:
        issues.append('No expectations defined for this case')
    return issues


if __name__ == '__main__':
    results = {}
    for filename in sys.argv[1:]:
        for row in json.loads(Path(filename).read_text(encoding='utf-8')):
            results[row['case']['id']] = row
    if not results:
        raise SystemExit('Provide at least one saved audit JSON file.')
    failed = 0
    for case_id, row in results.items():
        issues = assess(case_id, row['report'])
        failed += bool(issues)
        print(f"{'FAIL' if issues else 'PASS'} {case_id}" + (': ' + '; '.join(issues) if issues else ''))
    print(f'{len(results) - failed}/{len(results)} case expectations passed.')
    raise SystemExit(bool(failed))
