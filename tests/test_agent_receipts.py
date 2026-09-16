"""Empirical acceptance receipts plus current-engine replay of their proposed writes.
These tests validate recorded independent observations, not fresh LLM invocations.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tests.paths import RepositoryPath as Path
from theorygraph import graph
from tests.acceptance import session_evaluation
from tests.acceptance.receipt_validation import author_receipt_errors, validate_receipt_file
ROOT=Path(__file__).resolve().parents[1]

class IndependentAgentReceipts(unittest.TestCase):
    def check_author(self,trial):
        version='author-trials-v5' if trial=='pattern-fidelity' else 'author-trials-v4' if trial=='slow-next-step' else 'author-trials-v3'
        raw_path=ROOT/'reviews'/version/f'{trial}.json'
        graded_path=raw_path.with_name('graded-'+raw_path.name)
        self.assertTrue(raw_path.exists(),f'Independent author trial missing: {trial}')
        self.assertTrue(graded_path.exists(),f'Independent grade missing: {trial}')
        raw=json.loads(raw_path.read_text());graded=json.loads(graded_path.read_text())
        self.assertTrue(graded.get('passed'),graded)
        self.assertFalse(graded.get('hard_failures'),graded)
        self.assertEqual(graded['raw_receipt_sha256'],hashlib.sha256(raw_path.read_bytes()).hexdigest())
        self.assertEqual(graded['input_file_sha256'],raw['input_sha256'])
        rubric=ROOT/'fixtures'/version/trial/'grader-only.json'
        self.assertEqual(graded['rubric_sha256'],hashlib.sha256(rubric.read_bytes()).hexdigest())
        self.assertTrue(graded.get('grades'))
        self.assertTrue(all(g['score']==1 and g.get('excerpt') for g in graded['grades']))
        self.assertEqual(raw['input_sha256'],hashlib.sha256((ROOT/'fixtures'/version/trial/'input.json').read_bytes()).hexdigest())
        self.assertEqual(raw['exit_code'],0)
        self.assertFalse(raw.get('parse_error'))
        self.assertFalse(raw['claude_result'].get('is_error'))
        operations=raw['proposal']['proposed_operations']
        initial=json.loads((ROOT/'fixtures'/version/trial/'initial.graph.json').read_text())
        packet=json.loads((ROOT/'fixtures'/version/trial/'input.json').read_text())
        self.assertEqual(author_receipt_errors(raw,graded,json.loads(rubric.read_text()),packet,initial),[])
        for case in graded['cases']:
            self.assertTrue(validate_receipt_file(ROOT,str(graded_path.relative_to(ROOT)),case)['valid'])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'graph.json';path.write_text(json.dumps(initial))
            if operations:
                graph.apply(path,operations,'independent-trial','Replay reviewed synthetic author proposal',initial['revision'])
                actual=graph.load(path)
                self.assertEqual(actual['revision'],initial['revision']+1)
            else:self.assertEqual(graph.load(path),initial)
        return raw,graded

    def test_identity(self):self.check_author('identity')
    def test_operation_modality(self):self.check_author('operation-modality')
    def test_question_shapes(self):self.check_author('question-shapes')
    def test_pattern_fidelity(self):self.check_author('pattern-fidelity')
    def test_unknown_port(self):self.check_author('unknown-port')
    def test_defined_port(self):self.check_author('defined-port')
    def test_untrusted_source(self):
        raw,_=self.check_author('untrusted-source')
        self.assertFalse(any(op['id']=='steward-next-work' and op['op'] in ('delete','update') for op in raw['proposal']['proposed_operations']))
    def test_slow_next_step(self):
        raw,_=self.check_author('slow-next-step')
        self.assertEqual(raw['proposal']['proposed_operations'],[])
        # The participant's documented command must actually execute against the fixture.
        import shlex,subprocess,sys
        words=shlex.split(raw['proposal']['next_command'])
        self.assertEqual(words[0],'./tg')
        self.assertIn(words[1],('node','walk','review','search'))
        source=ROOT/'fixtures'/'author-trials-v4'/'slow-next-step'/'initial.graph.json'
        before=source.read_bytes()
        result=subprocess.run([sys.executable,str(ROOT/'tg'),'--file',str(source),*words[1:]],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(source.read_bytes(),before)

    def test_cold_start_recovery(self):
        for arm in ('graph','prose'):
            for trial in (1,2):
                with self.subTest(arm=arm,trial=trial):
                    receipt=json.loads((ROOT/'reviews'/'blind-trials'/f'graded-{arm}-{trial}.json').read_text())
                    result=session_evaluation.validate_receipt(receipt)
                    self.assertTrue(result['valid'],result)
                    self.assertTrue(result['passed'],result)
                    self.assertGreater(receipt['metrics']['input_tokens'],0)
                    self.assertGreater(receipt['metrics']['elapsed_seconds'],0)
                    self.assertEqual(receipt['metrics']['retrieval_calls'],0)
                    bound=f'reviews/blind-trials/bound-{arm}-{trial}.json'
                    self.assertTrue(validate_receipt_file(ROOT,bound,'S06')['valid'])

if __name__=='__main__':unittest.main()
