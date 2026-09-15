"""Real writer/process and compact-context acceptance probes, isolated from live data."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import graph

ROOT = Path(__file__).resolve().parent

def fixture():
    return {'version': 1, 'revision': 0, 'node_types': {'claim': {}},
            'edge_types': {'supports': {}}, 'nodes': {'a': {'type': 'claim', 'text': 'original'}},
            'edges': {}, 'changes': []}

class ReliabilityTests(unittest.TestCase):
    def test_competing_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'graph.json'
            path.write_text(json.dumps(fixture()))
            code = """import graph,sys
try:
 graph.apply(sys.argv[1],[{'op':'update','collection':'nodes','id':'a','value':{'text':sys.argv[2]}}],'test','concurrent',0)
except graph.GraphError as e:
 print(str(e));sys.exit(2)
"""
            processes = [subprocess.Popen([sys.executable, '-c', code, str(path), text], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for text in ['one', 'two']]
            outputs = [p.communicate(timeout=20) for p in processes]
            self.assertEqual(sorted(p.returncode for p in processes), [0, 2], outputs)
            self.assertTrue(any('Revision conflict' in out for out, _ in outputs))
            state = graph.load(path)
            self.assertEqual(state['revision'], 1)
            self.assertEqual(len(state['changes']), 1)
            self.assertEqual(state['changes'][0]['revision'], 1)
            self.assertIn(state['nodes']['a']['text'], ['one', 'two'])

    def test_abrupt_exit_at_atomic_replace_boundary(self):
        for moment in ['before', 'after']:
            with self.subTest(moment=moment), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'graph.json'
                path.write_text(json.dumps(fixture()))
                before = path.read_bytes()
                code = """import graph,os,sys
replace=os.replace
def fault(a,b):
 if sys.argv[2]=='after': replace(a,b)
 os._exit(77)
graph.os.replace=fault
graph.apply(sys.argv[1],[{'op':'update','collection':'nodes','id':'a','value':{'text':'new'}}],'test','crash',0)
"""
                result = subprocess.run([sys.executable, '-c', code, str(path), moment], cwd=ROOT, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 77)
                state = graph.load(path)
                if moment == 'before':
                    self.assertEqual(path.read_bytes(), before)
                else:
                    self.assertEqual(state['revision'], 1)
                    self.assertEqual(state['nodes']['a']['text'], 'new')
                    self.assertEqual(state['changes'][0]['revision'], 1)
                # The kernel released the lock despite an abrupt process exit.
                graph.apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'a', 'value': {'text': 'recovered'}}], 'test', 'recovery', state['revision'])
                self.assertEqual(graph.load(path)['nodes']['a']['text'], 'recovered')

    def test_context_budgets_and_explicit_full_history(self):
        state = fixture()
        state['nodes'] = {f'n{i}': {'type': 'claim', 'text': f'Claim {i}: '+('x'*140), 'meta': {'long_source': 'z'*30000}} for i in range(20)}
        state['edges'] = {f'e{i}': {'type': 'supports', 'from': f'n{i%20}', 'to': f'n{(i+1)%20}'} for i in range(30)}
        state['changes'] = [{'revision': 1, 'actor': 'test', 'reason': 'twenty edits', 'edits': [{'collection': 'nodes', 'id': f'n{i}', 'before': {'text': 'x'*30000}, 'after': {'text': 'y'*30000}} for i in range(20)]}]
        compact_history = json.dumps(graph.history(state, limit=1)).encode()
        self.assertLessEqual(len(compact_history), 8192)
        self.assertGreater(len(json.dumps(graph.history(state, limit=1, full=True))), 1000000)
        result = graph.walk(state, 'n0', depth=20, limit=20, edge_limit=30)
        rendered = graph.compact(result)
        self.assertNotIn('z'*1000, rendered)
        self.assertLessEqual(len(rendered.encode()), 12288)
        self.assertEqual(len(result['nodes']), 20)
        self.assertEqual(len(result['edges']), 30)

if __name__ == '__main__':
    unittest.main()
