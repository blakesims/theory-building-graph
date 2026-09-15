"""Validate archived actual maintenance evidence; never run a new model in unit tests."""
import hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT/'reviews'/'maintenance';RAW=BASE/'raw'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class MaintenanceReceipts(unittest.TestCase):
 def setUp(self):self.receipt=read(BASE/'study-receipt.json')
 def test_bound_actual_artifacts_and_independent_core_grades(self):
  r=self.receipt;self.assertEqual(r['status'],'completed');self.assertTrue(r['passed']);self.assertFalse(r['hard_failures']);self.assertEqual(len(r['grades']),12)
  self.assertEqual(sha(ROOT/r['rubric_path']),r['rubric_sha256'])
  self.assertEqual(set(read(ROOT/r['rubric_path'])['required_grades']),{g['id'] for g in r['grades']})
  for path,expected in r['artifact_hashes'].items():self.assertEqual(sha(ROOT/path),expected,path)
  for item in r['omitted_transient_artifacts']:self.assertTrue('__pycache__' in item['path'] or item['path'].endswith('.lock'))
  for arm in ('graph','prose'):
   grade=read(ROOT/r['arms'][arm]['semantic_review']);self.assertEqual(grade['core_semantic_score'],6);self.assertEqual(grade['core_semantic_possible'],6)
   self.assertEqual(grade['status'],'completed-independent-semantic-review')
   for g in grade['core_semantic_grades']:self.assertEqual(g['score'],1);self.assertTrue(g['excerpt']);self.assertTrue(g['location'])
   self.assertEqual([g['id'].split('/',1)[1] for g in r['grades'] if g['id'].startswith(arm+'/')],[g['id'] for g in grade['core_semantic_grades']])
   self.assertEqual([g for g in r['grades'] if g['id'].startswith(arm+'/')],[{**g,'id':arm+'/'+g['id'],'source_review':r['arms'][arm]['semantic_review']} for g in grade['core_semantic_grades']])
 def test_same_facts_dependencies_sources_and_budget(self):
  gb=read(RAW/'control'/'graph-before.json');pb=read(RAW/'control'/'prose-before.json');graph=json.loads(gb['graph.json'])
  for field in ('sources.md','unrelated-history.md'):self.assertEqual(gb[field],pb[field])
  sections={m.group(1):dict(re.findall(r'^(Type|Standing|Currency|Depends on|Source|Text|Rationale): (.*)$',m.group(2),re.M)) for m in re.finditer(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',pb['theory.md'],re.M|re.S)}
  claims={i:n for i,n in graph['nodes'].items() if n['type']=='claim'};self.assertEqual(len(claims),30)
  for nid,n in claims.items():
   p=sections[nid];self.assertEqual(p['Text'],n['text']);self.assertEqual(p['Standing'],n['status']);self.assertEqual(p['Rationale'],n['meta']['rationale']);self.assertEqual(p['Source'],n['meta']['source_ref'])
   targets=sorted(e['to'] for e in graph['edges'].values() if e['type']=='depends-on' and e['from']==nid)
   self.assertEqual(targets,[] if p['Depends on']=='(none)' else sorted(x.strip() for x in p['Depends on'].split(',')))
  runs=[read(RAW/'control'/f'{arm}-run.json') for arm in ('graph','prose')];self.assertEqual(runs[0]['command'],runs[1]['command']);self.assertNotEqual(runs[0]['result']['session_id'],runs[1]['result']['session_id'])
  tasks=[(RAW/arm/'TASK.md').read_text() for arm in ('graph','prose')];self.assertEqual(tasks[0].split('## Graph tools')[0],tasks[1].split('## Prose tools')[0])
 def test_observed_calls_tokens_time_and_real_writes(self):
  for arm in ('graph','prose'):
   raw=read(RAW/'control'/f'{arm}-run.json');graded=self.receipt['arms'][arm]['metrics'];calls={}
   for line in (RAW/'control'/f'{arm}-stdout.jsonl').read_text().splitlines():
    item=json.loads(line)
    for block in (item.get('message') or {}).get('content',[]):
     if block.get('type')=='tool_use':calls[block['id']]=block
   self.assertGreater(len(calls),0);self.assertEqual(len(calls),raw['tool_call_count']);self.assertEqual(len(calls),graded['actual_tool_calls'])
   self.assertEqual(raw['exit_code'],0);self.assertFalse(raw['result']['is_error']);self.assertFalse(raw['timed_out'])
   self.assertEqual(raw['elapsed_seconds'],graded['wall_seconds']);self.assertGreater(graded['wall_seconds'],0);self.assertLessEqual(len(calls),20);self.assertLessEqual(graded['wall_seconds'],300)
   tokens=graded['primary_tokens'];usage=raw['usage']
   for field in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens'):self.assertEqual(tokens[field],usage[field])
   self.assertEqual(tokens['total_input_exposure_tokens'],sum(usage[f] for f in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens')))
   self.assertEqual(tokens['total_accounted_tokens'],tokens['total_input_exposure_tokens']+usage['output_tokens'])
   edits=graded['edit_files'];self.assertGreater(graded['edit_diff_bytes'],0);self.assertEqual(sum(x['diff_bytes'] for x in edits),graded['edit_diff_bytes'])
   for edit in edits:self.assertEqual(sha(RAW/arm/edit['file']),edit['after_sha256'])
   commands='\n'.join(b.get('input',{}).get('command','') for b in calls.values())
   self.assertIn('./tg apply',commands) if arm=='graph' else self.assertIn('theory.md',commands)
   self.assertIsNone(graded['human_correction_count']);self.assertIsNone(graded['human_correction_seconds'])
 def test_preserves_negative_findings_and_limited_conclusion(self):
  r=self.receipt;self.assertFalse(r['measured_outcome']['graph_accuracy_advantage_established']);self.assertEqual(r['scope']['observed_pairs'],1)
  self.assertEqual(r['arms']['prose']['mechanical_receipt']['failed'],['exact_dependents_need_review'])
  self.assertEqual([g['score'] for g in r['arms']['prose']['observability_grades']],[1,0])
  self.assertTrue(r['arms']['prose']['review_notes']);self.assertIsNone(r['scope']['human_review_seconds'])
  self.assertEqual(r['scope']['general_superiority'],'not-established')
  # Preserve the original ambiguous labels: neither repair the artifact nor falsely say dependencies were missed.
  prose=(RAW/'prose'/'theory.md').read_text()
  for nid in ('C02','C03','C04','C05'):
   block=re.search(r'^## '+nid+r'\n(.*?)(?=^## |\Z)',prose,re.M|re.S).group(1)
   self.assertIn('Currency: current',block);self.assertIn('Review: needs-review',block)
