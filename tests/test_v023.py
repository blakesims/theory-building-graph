"""v0.2.3 backlog regressions. All graph writes use temporary fixtures."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from theorygraph import graph
from tests.test_dependency import fixture, edge

ROOT = Path(__file__).resolve().parents[1]
TG = str(ROOT / 'tg')


class TemporaryGraph(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'graph.json'
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.env = {**os.environ, 'TG_REGISTRY': str(Path(self.tmp.name) / 'registry.json')}

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, TG, '--file', str(self.path), *args],
                                capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result


class RetiredTargets(unittest.TestCase):
    def test_current_claims_and_questions_report_retired_relation_targets(self):
        for source_type in ('claim', 'question'):
            for relation in ('depends-on', 'answers', 'revises'):
                for retirement in ({'status': 'withdrawn'}, {'status': 'retired'},
                                   {'meta': {'review_state': 'historical'}}):
                    with self.subTest(source=source_type, relation=relation, retirement=retirement):
                        model = fixture(['current', 'old'])
                        model['nodes']['current'].update(type=source_type, status='open' if source_type == 'question' else 'accepted')
                        model['nodes']['old'].update(retirement)
                        eid = edge(model, 'current', 'old', relation, coverage='full')
                        findings = [f for f in graph.check(model)['findings'] if f['code'] == 'retired-target']
                        self.assertEqual(len(findings), 1)
                        self.assertEqual(findings[0]['nodes'], ['current', 'old'])
                        self.assertEqual(findings[0]['edges'], [eid])
                        self.assertIn('current', findings[0]['message'])
                        self.assertIn('old', findings[0]['message'])

    def test_inactive_sources_and_other_relations_do_not_report(self):
        for source in ({'status': 'withdrawn'}, {'status': 'retired'},
                       {'meta': {'review_state': 'historical'}}, {'type': 'entity'}):
            model = fixture(['current', 'old'])
            model['nodes']['current'].update(source)
            model['nodes']['old']['status'] = 'withdrawn'
            edge(model, 'current', 'old')
            self.assertFalse(any(f['code'] == 'retired-target' for f in graph.check(model)['findings']))
        model = fixture(['current', 'old'])
        edge(model, 'current', 'old')
        self.assertFalse(any(f['code'] == 'retired-target' for f in graph.check(model)['findings']))
        model['nodes']['old']['status'] = 'withdrawn'
        model['edges'].clear(); edge(model, 'current', 'old', 'supports')
        self.assertFalse(any(f['code'] == 'retired-target' for f in graph.check(model)['findings']))


class StatusListings(TemporaryGraph):
    def test_claim_status_filters_include_full_text_and_withdrawn_history(self):
        model = fixture([])
        text = 'A complete proposition. ' * 100 + 'END OF TEXT'
        for status in ('accepted', 'proposed', 'withdrawn'):
            model['nodes'][status] = {'type': 'claim', 'status': status, 'text': text,
                                      'meta': {'review_state': 'historical' if status == 'withdrawn' else 'current'}}
        self.path.write_text(json.dumps(model))
        for status in ('accepted', 'proposed', 'withdrawn'):
            out = self.cli('claims', '--status', status).stdout
            self.assertIn(status + ' [claim;' + status, out)
            self.assertIn(text, out)
            data = json.loads(self.cli('claims', '--status', status, '--json').stdout)
            self.assertEqual(list(data['nodes']), [status])
            self.assertEqual(data['nodes'][status]['text'], text)
        self.assertEqual(len(json.loads(self.cli('claims', '--json').stdout)['nodes']), 3)
        self.cli('claims', '--status', 'invalid', ok=False)

    def test_question_filter_precedes_limit_and_keeps_full_text(self):
        model = fixture([])
        text = 'What is the full question? ' * 100 + 'END OF QUESTION'
        for status in ('open', 'answered', 'retired'):
            model['nodes'][status] = {'type': 'question', 'status': status, 'text': text}
        self.path.write_text(json.dumps(model))
        for status in ('open', 'answered', 'retired'):
            out = self.cli('questions', '--status', status, '--limit', '1').stdout
            self.assertIn(status, out); self.assertIn(text, out)
            data = json.loads(self.cli('questions', '--status', status, '--json', '--limit', '1').stdout)
            self.assertEqual(list(data['nodes']), [status])
            self.assertEqual(data['nodes'][status]['text'], text)
            self.assertFalse(data['truncated'])


if __name__ == '__main__':
    unittest.main()
