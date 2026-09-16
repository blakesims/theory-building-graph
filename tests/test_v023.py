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


class FrontierSummary(TemporaryGraph):
    def test_empty_sections_explicitly_count_informational_findings(self):
        self.assertIn('0 conflicts, 0 informational findings', self.cli('frontier').stdout)
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor')
        self.assertIn('0 conflicts, 2 informational findings', self.cli('frontier').stdout)
        data = json.loads(self.cli('frontier', '--json').stdout)
        self.assertEqual(data['counts']['informational_findings'], 2)
        self.assertEqual(data['counts']['findings'], 0)
        self.assertEqual(data['counts']['unresolved_conflicts'], 0)

    def test_review_findings_are_not_replaced_by_an_empty_summary(self):
        self.path.write_text(json.dumps(fixture(['unanchored'])))
        out = self.cli('frontier').stdout
        self.assertIn('unanchored-claim', out)
        self.assertNotIn('0 conflicts,', out)


class RetireAnchors(TemporaryGraph):
    def test_retirement_is_audited_and_default_reads_hide_retired_anchors(self):
        model = fixture(['claim'])
        model['edge_types']['potential-conflict'] = {}
        for kind in ('entity', 'operation'):
            model['nodes'][kind] = {'type': kind, 'text': 'Old ' + kind, 'status': 'defined',
                                    'meta': {'title': 'Original title'}}
            edge(model, 'claim', kind, 'potential-conflict')
        self.path.write_text(json.dumps(model))
        for kind in ('entity', 'operation'):
            out = self.cli('retire', kind, '--reason', 'No longer part of the design').stdout
            self.assertIn('retired ' + kind, out)
            saved = graph.load(self.path)
            node = saved['nodes'][kind]
            self.assertEqual(node['meta']['review_state'], 'historical')
            self.assertEqual(node['meta']['review_reason'], 'No longer part of the design')
            self.assertEqual(node['meta']['title'], 'Original title')
            self.assertEqual(node['status'], 'defined')
            self.assertEqual(saved['changes'][-1]['reason'], 'No longer part of the design')
            for command in (('anchors',), ('search', kind)):
                self.assertNotIn(kind, json.loads(self.cli(*command, '--json').stdout)['nodes'])
                self.assertIn(kind, json.loads(self.cli(*command, '--historical', '--json').stdout)['nodes'])
            current = json.loads(self.cli('frontier', '--json').stdout)
            historical = json.loads(self.cli('frontier', '--historical', '--json').stdout)
            self.assertNotIn(kind, [e['to'] for e in current['unresolved_conflicts']])
            self.assertIn(kind, [e['to'] for e in historical['unresolved_conflicts']])
        self.assertEqual(graph.load(self.path)['edges'], model['edges'])

    def test_retire_requires_an_anchor_and_reason_and_supports_dry_run(self):
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor')
        self.cli('claim', 'add', 'claim', 'Claim', '--about', 'subject', '--reason', 'proposal')
        before = self.path.read_bytes()
        self.cli('retire', 'subject', ok=False)
        self.cli('retire', 'missing', '--reason', 'invalid', ok=False)
        self.cli('retire', 'claim', '--reason', 'invalid', ok=False)
        dry = json.loads(self.cli('retire', 'subject', '--reason', 'preview', '--dry-run', '--json').stdout)
        self.assertTrue(dry['dry_run']); self.assertFalse(dry['written'])
        self.assertEqual(self.path.read_bytes(), before)


class DirtyRepositorySync(TemporaryGraph):
    def git(self, cwd, *args):
        result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def setUp(self):
        super().setUp()
        root = Path(self.tmp.name)
        self.env.update(GIT_AUTHOR_NAME='test', GIT_AUTHOR_EMAIL='t@example.invalid',
                        GIT_COMMITTER_NAME='test', GIT_COMMITTER_EMAIL='t@example.invalid')
        self.remote = root / 'remote.git'; self.repo = root / 'repo'; self.other = root / 'other'
        self.git(root, 'init', '--bare', str(self.remote))
        self.git(root, 'clone', str(self.remote), str(self.repo))
        self.path = self.repo / 'graph.json'
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.unrelated = self.repo / 'work.txt'; self.unrelated.write_text('original\n')
        self.git(self.repo, 'add', 'graph.json', 'work.txt'); self.git(self.repo, 'commit', '-m', 'initial')
        self.git(self.repo, 'push', '-u', 'origin', 'HEAD')
        self.git(root, 'clone', str(self.remote), str(self.other))
        self.unrelated.write_text('unsaved user work\n')

    def test_sync_rebases_graph_with_unrelated_unstaged_work(self):
        (self.other / 'remote.txt').write_text('remote work\n')
        self.git(self.other, 'add', 'remote.txt'); self.git(self.other, 'commit', '-m', 'remote change')
        self.git(self.other, 'push')
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'local graph change')
        self.cli('sync')
        self.assertEqual(self.unrelated.read_text(), 'unsaved user work\n')
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--', 'work.txt'), 'M work.txt')
        self.assertEqual(self.git(self.repo, 'diff', '--cached', '--name-only'), '')
        self.assertEqual(self.git(self.repo, 'show', '--pretty=', '--name-only', 'HEAD'), 'graph.json')
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.git(self.remote, 'rev-parse', 'HEAD'))

    def test_autostash_conflict_is_not_reported_as_success(self):
        (self.other / 'work.txt').write_text('remote work conflicts with local work\n')
        self.git(self.other, 'commit', '-am', 'remote work'); self.git(self.other, 'push')
        remote_head = self.git(self.remote, 'rev-parse', 'HEAD')
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'local graph change')
        result = self.cli('sync', ok=False)
        self.assertIn('Autostash restore conflicted; not pushed', result.stderr)
        self.assertIn('work.txt', result.stderr)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'HEAD'), remote_head)
        self.assertIn('unsaved user work', self.git(self.repo, 'stash', 'show', '-p'))

    def test_graph_conflict_keeps_local_graph_and_unrelated_work(self):
        remote_graph = self.other / 'graph.json'
        model = json.loads(remote_graph.read_text()); model['revision'] = 99
        remote_graph.write_text(json.dumps(model))
        self.git(self.other, 'commit', '-am', 'remote graph'); self.git(self.other, 'push')
        remote_head = self.git(self.remote, 'rev-parse', 'HEAD')
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'local graph change')
        local = self.path.read_bytes()
        result = self.cli('sync', ok=False)
        self.assertIn('Conflicting files: graph.json', result.stderr)
        self.assertEqual(self.path.read_bytes(), local)
        self.assertEqual(self.unrelated.read_text(), 'unsaved user work\n')
        self.assertEqual(self.git(self.remote, 'rev-parse', 'HEAD'), remote_head)
        self.assertFalse((self.repo / '.git/rebase-merge').exists())


if __name__ == '__main__':
    unittest.main()
