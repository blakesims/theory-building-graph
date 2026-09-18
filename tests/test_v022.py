"""v0.2.2: performed-by coverage and claim add --status withdrawn."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from theorygraph import graph
from tests.test_dependency import fixture

ROOT = Path(__file__).resolve().parents[1]
TG = str(ROOT / 'tg')


def roles_model():
    """One role reached only by performed-by, one entity reached by nothing."""
    model = fixture(['claim'])
    model['nodes'].update({
        'worker-role': {'type': 'entity', 'text': 'A role that performs operations.'},
        'lonely': {'type': 'entity', 'text': 'Nothing touches this one.'},
        'start-run': {'type': 'operation', 'text': 'Start a run.'},
    })
    model['edge_types']['performed-by'] = {'description': 'Operation -> the role that performs it.'}
    model['edges']['perf-start-run-worker-role'] = {'from': 'start-run', 'to': 'worker-role', 'type': 'performed-by'}
    return model


class PerformedByCoverage(unittest.TestCase):
    def test_performed_by_covers_a_role(self):
        findings = [f for f in graph.check(roles_model())['findings'] if f['code'] == 'entity-without-operations']
        self.assertEqual([f['nodes'] for f in findings], [['lonely']])

    def test_acts_on_still_covers_and_direction_still_matters(self):
        model = roles_model()
        model['edge_types']['acts-on'] = {'description': 'Operation acts on entity'}
        model['edges']['wrong-direction'] = {'from': 'lonely', 'to': 'start-run', 'type': 'acts-on'}
        findings = [f for f in graph.check(model)['findings'] if f['code'] == 'entity-without-operations']
        self.assertEqual([f['nodes'] for f in findings], [['lonely']])
        model['edges']['acts'] = {'from': 'start-run', 'to': 'lonely', 'type': 'acts-on'}
        self.assertEqual([f for f in graph.check(model)['findings'] if f['code'] == 'entity-without-operations'], [])

    def test_graph_without_the_edge_type_behaves_as_before(self):
        model = roles_model()
        del model['edges']['perf-start-run-worker-role']; del model['edge_types']['performed-by']
        findings = [f for f in graph.check(model)['findings'] if f['code'] == 'entity-without-operations']
        self.assertEqual([f['nodes'] for f in findings], [['lonely'], ['worker-role']])
        self.assertEqual(findings[0]['message'], 'Entity has no incoming acts-on edge from an operation.')


class WithdrawnOnCreate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'graph.json'
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.env = {**os.environ, 'TG_REGISTRY': str(Path(self.tmp.name) / 'registry.json')}

    def cli(self, *args, ok=True):
        r = subprocess.run([sys.executable, TG, '--file', str(self.path), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def test_rejected_idea_is_recorded_in_one_command(self):
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor')
        self.cli('claim', 'add', 'rejected-idea', 'We could shard the store.', '--about', 'subject',
                 '--status', 'withdrawn', '--reason', 'Blake rejected this in session 3')
        node = graph.load(self.path)['nodes']['rejected-idea']
        self.assertEqual(node['status'], 'withdrawn')
        self.assertEqual(node['meta']['review_state'], 'current')
        self.assertEqual(graph.load(self.path)['changes'][-1]['reason'], 'Blake rejected this in session 3')

    def test_other_statuses_are_unchanged_and_nonsense_is_still_refused(self):
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor')
        self.cli('claim', 'add', 'kept', 'Kept.', '--about', 'subject', '--reason', 'r')
        self.assertEqual(graph.load(self.path)['nodes']['kept']['status'], 'proposed')
        r = self.cli('claim', 'add', 'nope', 'No.', '--about', 'subject', '--status', 'retired', '--reason', 'r', ok=False)
        self.assertIn('invalid choice', r.stderr)


if __name__ == '__main__':
    unittest.main()
