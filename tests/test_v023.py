"""v0.2.3 backlog regressions. All graph writes use temporary fixtures."""
import unittest

from theorygraph import graph
from tests.test_dependency import fixture, edge


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


if __name__ == '__main__':
    unittest.main()
