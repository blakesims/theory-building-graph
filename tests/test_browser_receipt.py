"""Recorded v0.1 browser evidence, not a claim of a fresh run on the current engine.
The original S08 composite evidence and observed engine bytes remain immutable.
"""
import hashlib,json,unittest
from pathlib import Path
from tests.paths import RepositoryPath as Path
ROOT=Path(__file__).resolve().parents[1]
class BrowserReceipt(unittest.TestCase):
    def test_live_observability(self):
        folder=ROOT/'reviews'/'browser'/'current';r=json.loads((folder/'receipt.json').read_text())
        self.assertTrue(r['passed']);self.assertTrue(r['live_graph_unchanged']);self.assertTrue(r['synthetic'])
        for name,digest in r['files_sha256'].items():
            p={'index.html':folder/'index.html','graph.py':folder/'graph.py'}.get(name,folder/name)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest,name)
        for name,digest in r['screenshots'].items():self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),digest)
        commands=json.loads((folder/'commands.json').read_text())
        self.assertTrue(all(c['exit_code']==0 for c in commands))
        self.assertTrue(any(('Live · r'+str(r['graph_revision']+1)) in c['stdout'] for c in commands))
        self.assertTrue(any('ui-fixture-about' in c['stdout'] and 'ui-observability-fixture' in c['stdout'] for c in commands))
        self.assertEqual(set(r['checks']),{'resolution-visible','impact-visible','findings-visible','revision-live-update','new-node-findable','node-and-edge-history','live-data-unchanged'})
