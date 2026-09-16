"""v0.2.2: performed-by coverage, --no-sync, and claim add --status withdrawn."""
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


class NoSyncFlag(unittest.TestCase):
    def git(self, cwd, *args):
        r = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        bare = t / 'remote.git'; self.git(t, 'init', '-q', '--bare', str(bare))
        self.repo = t / 'work'; self.git(t, 'clone', '-q', str(bare), str(self.repo))
        self.git(self.repo, 'config', 'user.email', 't@x'); self.git(self.repo, 'config', 'user.name', 't')
        self.path = self.repo / 'theory' / 'graph.json'; self.path.parent.mkdir()
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.git(self.repo, 'add', '.'); self.git(self.repo, 'commit', '-q', '-m', 'init')
        self.git(self.repo, 'push', '-q', '-u', 'origin', 'HEAD')
        self.env = {**os.environ, 'TG_REGISTRY': str(t / 'registry.json'),
                    'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@x',
                    'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@x'}
        self.cli('register', 'demo', str(self.path))
        self.cli('config', 'autosync', 'on')

    def cli(self, *args, ok=True):
        r = subprocess.run([sys.executable, TG, '-p', 'demo', *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def commits(self):
        return int(self.git(self.repo, 'rev-list', '--count', 'HEAD'))

    def test_writes_sync_by_default(self):
        out = self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor').stdout.strip()
        self.assertIn('synced', out)
        self.assertEqual(self.commits(), 2)

    def test_no_sync_skips_the_sync_and_says_so(self):
        for revision, (name, flags) in enumerate((
                ('one', ('--no-sync', 'entity', 'add', 'one', 'One')),
                ('two', ('entity', 'add', 'two', 'Two', '--no-sync'))), start=1):
            with self.subTest(flags=flags):
                out = self.cli(*flags, '--reason', 'burst').stdout.strip()
                self.assertEqual(out, f'r{revision} · added entity {name} · not synced (--no-sync)')
        self.assertEqual(self.commits(), 1)
        self.assertEqual(sorted(graph.load(self.path)['nodes']), ['one', 'two'])
        self.cli('sync')
        self.assertEqual(self.commits(), 2)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--', 'theory/graph.json'), '')

    def test_no_sync_is_reported_in_json_and_survives_dry_run(self):
        data = json.loads(self.cli('--json', '--no-sync', 'entity', 'add', 'three', 'Three', '--reason', 'burst').stdout)
        self.assertTrue(data['sync_skipped'])
        self.assertNotIn('sync', data)
        dry = json.loads(self.cli('--json', '--no-sync', 'entity', 'add', 'four', 'Four', '--reason', 'burst', '--dry-run').stdout)
        self.assertTrue(dry['dry_run']); self.assertFalse(dry['written'])
        self.assertEqual(self.commits(), 1)


if __name__ == '__main__':
    unittest.main()
