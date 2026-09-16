"""Bind measured review latency to real no-tool review artifacts; not semantic grading."""
import hashlib,json,unittest
from pathlib import Path
from tests.paths import RepositoryPath as Path
ROOT=Path(__file__).resolve().parents[1]
PHASE=ROOT/'reviews/maintenance/timed-review-1'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class TimedReviewReceipts(unittest.TestCase):
 def test_real_paired_no_tool_measurements_bound(self):
  packets=[]
  for arm in ('graph','prose'):
   folder=PHASE/arm;r=json.loads((folder/'receipt.json').read_text());packets.append(json.loads((folder/'input.json').read_text()))
   self.assertEqual(r['exit_code'],0);self.assertFalse(r['timed_out']);self.assertFalse(r['is_error']);self.assertEqual(r['tool_call_count'],0)
   self.assertGreater(r['agent_review_latency_seconds'],0);self.assertEqual(r['elapsed_seconds'],r['agent_review_latency_seconds']);self.assertIsNone(r['human_review_seconds'])
   for key,file in [('input','input.json'),('prompt','prompt.txt'),('raw','stdout.jsonl')]:self.assertEqual(r[key+'_sha256'],digest(folder/file))
   events=[json.loads(line) for line in (folder/'stdout.jsonl').read_text().splitlines()];final=next(e for e in reversed(events) if e.get('type')=='result')
   self.assertEqual(final['usage'],r['usage']);self.assertGreater(r['usage']['output_tokens'],0);self.assertEqual(final['result'],(folder/'review.txt').read_text())
   outcome=json.loads((folder/'review-outcome.json').read_text());self.assertEqual(outcome['review_text_sha256'],digest(folder/'review.txt'));self.assertEqual(outcome['semantic_grade'],'not-graded');self.assertEqual(outcome['status'],'parsed')
   for field in ('current_rule','dependent_review_ids','still_open_questions','discrepancies'):self.assertIn(field,outcome['reviewer_outcome'])
   for name,path in r['source_paths']['after'].items():self.assertEqual(r['source_hashes']['after'][name],digest(ROOT/path))
   self.assertEqual(r['source_hashes']['before'],digest(ROOT/r['source_paths']['before']))
  self.assertEqual(packets[0]['user_revision'],packets[1]['user_revision'])
  for name in ('sources.md','unrelated-history.md'):self.assertEqual(packets[0]['before_documents'][name],packets[1]['before_documents'][name])

 def test_independent_review_grades_measurements_and_required_phases(self):
  from tests.acceptance.receipt_validation import validate_receipt_file
  mapping=json.loads((ROOT/'acceptance/maintenance-mapping.json').read_text())['cases']['S07']
  expected={'reviews/maintenance/study-receipt.json'}
  for arm in ('graph','prose'):
   path=f'reviews/maintenance/timed-review-1/{arm}/graded.json';expected.add(path)
   graded=json.loads((ROOT/path).read_text());receipt=json.loads((PHASE/arm/'receipt.json').read_text())
   self.assertTrue(validate_receipt_file(ROOT,path,'S07')['valid'])
   self.assertEqual({g['id'] for g in graded['grades']},{'scope','dependencies','history','unknowns','changes'})
   self.assertTrue(all(g['score']==1 for g in graded['grades']))
   for key in ('elapsed_seconds','agent_review_latency_seconds','human_review_seconds','tool_call_count','cost_usd'):
    self.assertEqual(graded['measurements'][key],receipt[key])
   total=sum(receipt['usage'][key] for key in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens'))
   self.assertEqual(graded['measurements']['accounted_primary_tokens'],total)
   self.assertTrue(any('C05' in limit for limit in graded['limitations']))
   self.assertTrue(any('human review time' in limit for limit in graded['limitations']))
  self.assertEqual(set(mapping['receipts']),expected)
  self.assertTrue(validate_receipt_file(ROOT,'reviews/maintenance/study-receipt.json','S07')['valid'])
