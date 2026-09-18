"""v0.2.3 backlog regressions. All graph writes use temporary fixtures."""
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from theorygraph import graph, locks
from tests.test_dependency import fixture, edge

ROOT = Path(__file__).resolve().parents[1]
TG = str(ROOT / 'tg')


class TemporaryGraph(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'graph.json'
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.env = {**os.environ, 'TG_REGISTRY': str(Path(self.tmp.name) / 'registry.json'),
                    'XDG_RUNTIME_DIR': str(Path(self.tmp.name) / 'runtime')}

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, TG, '--file', str(self.path), *args],
                                capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result


class RetiredTargets(unittest.TestCase):
    def test_current_claims_and_questions_report_retired_relation_targets(self):
        for source_type in ('claim', 'question'):
            for relation in ('depends-on', 'answers'):
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

    def test_revises_to_withdrawn_is_how_revision_works_and_is_not_reported(self):
        model = fixture(['current', 'old'])
        model['nodes']['current'].update(type='claim', status='accepted')
        model['nodes']['old']['status'] = 'withdrawn'
        edge(model, 'current', 'old', 'revises')
        self.assertFalse(any(f['code'] == 'retired-target' for f in graph.check(model)['findings']))

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


class RuntimeLocks(TemporaryGraph):
    def test_writes_leave_no_lock_files_beside_graph(self):
        self.cli('entity', 'add', 'subject', 'Subject', '--reason', 'anchor')
        with patch.dict(os.environ, self.env):
            for suffix in ('.lock', '.write.lock'):
                path = locks.lock_path(self.path, suffix)
                self.assertTrue(path.is_file())
                self.assertTrue(path.is_relative_to(Path(self.env['XDG_RUNTIME_DIR'])))
                self.assertEqual(path.name, 'graph.json' + suffix)
        self.assertFalse(list(self.path.parent.glob('*.lock')))

    def test_lock_identity_uses_canonical_path_and_cache_fallback(self):
        alias = self.path.parent / 'alias.json'; alias.symlink_to(self.path)
        with patch.dict(os.environ, {'HOME': self.tmp.name, 'XDG_RUNTIME_DIR': ''}):
            path = locks.lock_path(self.path)
            self.assertTrue(path.is_relative_to(Path(self.tmp.name) / '.cache/theory-graph/locks'))
            self.assertEqual(path, locks.lock_path(alias))
            self.assertNotEqual(path, locks.lock_path(self.path.parent / 'other/graph.json'))
            self.assertNotEqual(path, locks.lock_path(self.path, '.write.lock'))

    def test_both_locks_block_cli_writers_until_released(self):
        for suffix in ('.lock', '.write.lock'):
            with self.subTest(suffix=suffix), patch.dict(os.environ, self.env):
                lock_path = locks.lock_path(self.path, suffix)
                before = self.path.read_bytes()
                with open(lock_path, 'a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    code = "from theorygraph import graph; import sys; print('ready', flush=True); sys.exit(graph.main())"
                    proc = subprocess.Popen([sys.executable, '-c', code, '--file', str(self.path),
                                             'entity', 'add', suffix, 'Subject', '--reason', 'lock test'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                    try:
                        self.assertEqual(proc.stdout.readline().strip(), 'ready')
                        with self.assertRaises(subprocess.TimeoutExpired): proc.wait(timeout=0.2)
                        self.assertEqual(self.path.read_bytes(), before)
                        fcntl.flock(lock, fcntl.LOCK_UN)
                        stdout, stderr = proc.communicate(timeout=10)
                        self.assertEqual(proc.returncode, 0, stdout + stderr)
                    finally:
                        if proc.poll() is None: proc.kill(); proc.communicate()
                self.assertIn(suffix, graph.load(self.path)['nodes'])


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


if __name__ == '__main__':
    unittest.main()
