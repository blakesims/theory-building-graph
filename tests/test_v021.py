"""v0.2.1 relation, finding, frontier, and viewer behavior on isolated data."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from theorygraph import graph
from tests.test_dependency import edge, fixture

ROOT = Path(__file__).resolve().parents[1]
TG = ROOT / 'tg'


class OperationsAndDependencies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'graph.json'
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.env = {**os.environ, 'TG_REGISTRY': str(Path(self.tmp.name) / 'registry.json')}

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(TG), '--file', str(self.path), *args, '--reason', 'v0.2.1 test'],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_template_declares_both_relations(self):
        g = graph.load(self.path)
        self.assertIn('acts-on', g['edge_types'])
        self.assertIn('depends-on', g['edge_types'])
        self.assertTrue(g['edge_types']['depends-on']['readiness'])

    def test_typed_flags_add_all_requested_edges_atomically(self):
        self.cli('entity', 'add', 'one', 'One')
        self.cli('entity', 'add', 'two', 'Two')
        before = graph.load(self.path)['revision']
        result = self.cli('operation', 'add', 'act', 'Act', '--acts-on', 'one', 'two')
        self.assertIn(f'r{before + 1}', result.stdout)
        self.cli('claim', 'add', 'premise', 'Premise', '--about', 'one')
        self.cli('claim', 'add', 'rule', 'Rule', '--about', 'one', '--depends-on', 'premise', 'act')
        self.cli('question', 'add', 'question', 'Question?', '--about', 'two', '--depends-on', 'premise')
        g = graph.load(self.path)
        triples = {(e['from'], e['type'], e['to']) for e in g['edges'].values()}
        self.assertTrue({('act','acts-on','one'), ('act','acts-on','two'),
                         ('rule','depends-on','premise'), ('rule','depends-on','act'),
                         ('question','depends-on','premise')} <= triples)
        self.assertEqual(graph.check(g)['counts'].get('entity-without-operations'), None)
        self.assertEqual(graph.frontier(g)['open_questions'][0]['readiness'], 'blocked')

    def test_flags_reject_unknown_or_wrong_type_without_writing(self):
        self.cli('entity', 'add', 'entity', 'Entity')
        before = self.path.read_bytes()
        for args, expected in [
            (('operation','add','act','Act','--acts-on','missing'), 'missing'),
            (('operation','add','act','Act','--acts-on','act'), 'act'),
            (('claim','add','claim','Claim','--about','entity','--depends-on','missing'), 'missing'),
            (('question','add','q','Question?','--about','entity','--depends-on','missing'), 'missing')]:
            with self.subTest(args=args):
                result = self.cli(*args, ok=False)
                self.assertIn(expected, result.stderr)
                self.assertEqual(self.path.read_bytes(), before)


class FindingsAndFrontier(unittest.TestCase):
    def test_entity_without_operations_is_informational_and_directional(self):
        model = fixture(['claim'])
        model['nodes'].update({
            'entity-a': {'type':'entity','text':'A'},
            'entity-b': {'type':'entity','text':'B'},
            'operation': {'type':'operation','text':'Operation'},
        })
        model['edge_types']['acts-on'] = {'description':'Operation acts on entity'}
        model['edges']['wrong-direction'] = {'from':'entity-a','to':'operation','type':'acts-on'}
        model['edges']['valid'] = {'from':'operation','to':'entity-b','type':'acts-on'}
        findings = [f for f in graph.check(model)['findings'] if f['code']=='entity-without-operations']
        self.assertEqual([(f['nodes'], f['severity']) for f in findings], [(['entity-a'], 'informational')])
        default = graph.check_view(graph.check(model))
        self.assertEqual(default['informational_counts']['entity-without-operations'], 1)
        self.assertNotIn('entity-without-operations', [f['code'] for f in default['findings']])

    def test_frontier_open_questions_have_ready_or_blocked_column(self):
        model = fixture(['premise','ready-question','blocked-question'])
        for nid in ('ready-question','blocked-question'):
            model['nodes'][nid].update(type='question', status='open')
        model['nodes']['premise']['status'] = 'proposed'
        edge(model, 'blocked-question', 'premise')
        result = graph.frontier(model)
        self.assertEqual({q['id']:q['readiness'] for q in result['open_questions']},
                         {'blocked-question':'blocked', 'ready-question':'ready'})
        text = graph.compact(result)
        self.assertIn('QUESTION', text); self.assertIn('READINESS', text)
        self.assertIn('blocked-question', text); self.assertIn('blocked', text)
        self.assertIn('ready-question', text); self.assertIn('ready', text)


class ViewerRelations(unittest.TestCase):
    def test_acts_on_and_depends_on_are_dashed_labelled_and_colored(self):
        html = (ROOT / 'theorygraph/viewer/index.html').read_text()
        self.assertIn("'acts-on':'dashed'", html)
        self.assertIn("'depends-on':'dashed'", html)
        self.assertIn('edge[kind="acts-on"],edge[kind="depends-on"]', html)
        self.assertIn("label:'data(label)'", html)
        self.assertIn('--r-acts-on:', html)
        self.assertIn('--r-depends-on:', html)
