#!/usr/bin/env python3
"""Run explicit acceptance mappings; never turn unsupported or skipped checks into passes."""
import argparse
import collections
import hashlib
import io
import json
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from acceptance.receipt_validation import agent_evidence

class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}
    def addSuccess(self, test):
        super().addSuccess(test); self.outcomes[test.id()] = 'passed'
    def addFailure(self, test, err):
        super().addFailure(test, err); self.outcomes[test.id()] = 'failed'
    def addError(self, test, err):
        super().addError(test, err); self.outcomes[test.id()] = 'failed'
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.outcomes[test.id()] = 'not-run'
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.outcomes[test.id()] = 'failed'
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.outcomes[test.id()] = 'failed'
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None: self.outcomes[test.id()] = 'failed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT/'acceptance'/'run-report.json')
    parser.add_argument('--case', action='append', help='Run only these case IDs (repeatable)')
    args = parser.parse_args()
    spec = json.loads((ROOT/'acceptance'/'cases.json').read_text())
    selected = [c for c in spec['cases'] if not args.case or c['id'] in args.case]
    unknown = set(args.case or []) - {c['id'] for c in selected}
    if unknown: parser.error('Unknown cases: '+', '.join(sorted(unknown)))
    maps = collections.defaultdict(list)
    for path in sorted((ROOT/'acceptance').glob('*-mapping.json')):
        data = json.loads(path.read_text())
        for key, mapping in data['cases'].items():
            if key not in {c['id'] for c in spec['cases']}:
                raise ValueError(f'Unknown mapped case {key} in {path}')
            maps[key].append(dict(mapping, mapping_source=path.name))
    criteria_spec=json.loads((ROOT/'acceptance'/'criteria.json').read_text())['criteria']
    names = sorted({name for c in selected for m in maps[c['id']] for name in m.get('tests', [])} | {name for c in criteria_spec for name in c.get('additional_tests',[])})
    start = time.monotonic()
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Results).run(unittest.TestLoader().loadTestsFromNames(names))
    cases = []
    for c in selected:
        mapped = maps[c['id']]
        tests = sorted({n for m in mapped for n in m.get('tests', [])})
        outcomes = {n: result.outcomes.get(n, 'not-run') for n in tests}
        full = any(m.get('coverage') == 'full' for m in mapped)
        agent_required = 'agent' in c.get('mechanism','')
        evidence=agent_evidence(ROOT,mapped,c['id'])
        if agent_required and not evidence['full']: full=False
        if not tests: status = 'not-implemented'
        elif any(s == 'failed' for s in outcomes.values()): status = 'failed'
        elif any(s != 'passed' for s in outcomes.values()): status = 'not-run'
        elif not full: status = 'partial'
        else: status = 'passed'
        cases.append({'id': c['id'], 'title': c['title'], 'mechanism': c['mechanism'], 'status': status, 'tests': outcomes, 'coverage_claims': mapped,'agent_evidence_required':agent_required,'agent_receipts':evidence['valid_receipts'],'agent_receipt_errors':evidence['errors']})
    counts = dict(collections.Counter(c['status'] for c in cases))
    case_status={c['id']:c['status'] for c in cases}
    criteria=[]
    for criterion in criteria_spec:
        dependencies={key:case_status.get(key,'not-run') for key in criterion['cases']}
        extra={key:result.outcomes.get(key,'not-run') for key in criterion.get('additional_tests',[])}
        criterion_passed=all(v=='passed' for v in [*dependencies.values(),*extra.values()])
        criteria.append({**criterion,'status':'passed' if criterion_passed else 'incomplete','case_status':dependencies,'additional_test_status':extra})
    report = {'suite_version': spec['suite_version'], 'case_count': len(cases), 'counts': counts,
              'all_passed': result.wasSuccessful() and all(v=='passed' for v in result.outcomes.values()) and bool(cases) and all(c['status']=='passed' for c in cases) and (bool(args.case) or all(c['status']=='passed' for c in criteria)),
              'criteria':criteria,'criteria_counts':dict(collections.Counter(c['status'] for c in criteria)),
              'unique_test_count': len(names), 'elapsed_seconds': round(time.monotonic()-start, 3),
              'files_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob('*.py'))},
              'scope': 'Mapped behavioral checks. Full coverage is an explicit reviewable claim, not inferred from number of assertions. Independent agent evaluations require recorded evidence in their mappings.',
              'cases': cases, 'test_log': log.getvalue()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'counts': counts, 'all_passed': report['all_passed'], 'tests': len(names), 'criteria_counts':report['criteria_counts'], 'report': str(args.report)}, indent=2))
    if not result.wasSuccessful(): print(log.getvalue(), file=sys.stderr)
    return 0 if report['all_passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
