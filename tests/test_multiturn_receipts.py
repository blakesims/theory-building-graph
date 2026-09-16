"""Integrity and exact-state assertions on independently graded staged trials.

Failing trials are retained and rejected by the gate. These tests demonstrate
record integrity and observed behavior; they do not make failed acceptance pass.
"""
import hashlib,json,unittest
from pathlib import Path
from tests.paths import RepositoryPath as Path
from tests.acceptance.receipt_validation import validate_receipt_file
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reviews/multiturn/v1'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(b'' if p.suffix=='.lock' and not p.exists() else p.read_bytes()).hexdigest()  # lock files are empty and gitignored
def snapshot(trial,stage,side):return load(BASE/trial/'control'/stage/(side+'.graph.json'))
class StagedTrialReceipts(unittest.TestCase):
 def test_ports_artifact_hashes_and_stage_chain(self):
  report=load(BASE/'ports/graded.json');prior=None
  for rel,digest in report['artifact_hashes'].items():self.assertEqual(sha(BASE/'ports'/rel),digest,rel)
  for s in load(BASE/'ports/participant.json')['stages']:
   d=BASE/'ports/control'/s['stage']
   for name,field in [('prompt.txt','prompt_sha256'),('before.graph.json','before_sha256'),('after.graph.json','after_sha256'),('stdout.jsonl','stdout_sha256')]:self.assertEqual(sha(d/name),s[field])
   if prior:self.assertEqual(s['before_sha256'],prior)
   prior=s['after_sha256']
 def test_failed_ports_receipt_does_not_pass_gate(self):
  p='reviews/multiturn/v1/ports/graded.json';r=load(ROOT/p)
  self.assertFalse(r['passed']);self.assertEqual(set(r['hard_failures']),{'protocol-budget','source-integrity'})
  check=validate_receipt_file(ROOT,p,'S05');self.assertFalse(check['valid']);self.assertIn('not-passed',check['errors']);self.assertNotIn('rubric-hash-mismatch',check['errors'])
 def test_ports_no_identity_invented_before_answer(self):
  a=snapshot('ports','01-identity-unknown','before');b=snapshot('ports','01-identity-unknown','after')
  self.assertEqual(a,b);self.assertNotIn('identity_key',b['nodes']['port-rule']['pattern']['slot'])
 def test_ports_defined_identity_actual_result(self):
  g=snapshot('ports','02-identity-defined','after');p=g['nodes']['port-rule']['pattern']
  self.assertEqual(p['slot']['identity_key'],['host','number']);self.assertEqual((p['min'],p['max']),(1,1))
  r=g['nodes']['port-rule-check-host-number']['result'];self.assertEqual(r['outcome'],'satisfies');self.assertEqual([s['distinct_count'] for s in r['subjects']],[1,1]);self.assertTrue(r['synthetic'])
 def test_ports_same_rule_counterexample_retains_prior_reports(self):
  a=snapshot('ports','03-counterexample','before');b=snapshot('ports','03-counterexample','after')
  self.assertEqual(a['nodes']['port-rule'],b['nodes']['port-rule'])
  x=a['nodes']['port-observations']['trace']['reports'];y=b['nodes']['port-observations']['trace']['reports'];self.assertEqual(y[:2],x);self.assertEqual(len(y),3)
  r=b['nodes']['port-rule-check-host-number-r6']['result'];self.assertEqual(r['outcome'],'violates')
  witness=next(s for s in r['subjects'] if s['identity']=={'host':'host-a','number':8080});self.assertEqual(witness['distinct_count'],2);self.assertEqual(witness['outcome'],'violates')
 def test_ports_budget_failure_is_visible(self):
  r=load(BASE/'ports/control/02-identity-defined/receipt.json');self.assertEqual(r['tool_call_count'],13);self.assertEqual(r['budget']['tool_limit'],12);self.assertTrue(r['budget']['calls_exceeded'])
 def test_design_artifact_hashes_and_failure_gate(self):
  report=load(BASE/'design/graded.json')
  for rel,digest in report['artifact_hashes'].items():self.assertEqual(sha(BASE/'design'/rel),digest,rel)
  self.assertEqual(set(report['hard_failures']),{'01-read-only','02-atomic-proposal'})
  r=validate_receipt_file(ROOT,'reviews/multiturn/v1/design/graded.json','S01');self.assertFalse(r['valid']);self.assertIn('grade-not-passed',r['errors'])
 def test_design_no_premature_withdrawal_but_currentness_failure(self):
  a=snapshot('design','02-atomic-proposal','after');b=snapshot('design','03-reconsider-and-recall','after')
  for g in (a,b):
   self.assertEqual(g['nodes']['replacement-exception']['status'],'accepted');self.assertEqual(g['nodes']['replacement-question']['status'],'open')
  self.assertEqual(a['nodes']['replacement-exception']['meta']['review_state'],'needs-review')
  self.assertEqual(a['nodes']['atomic-replacement-hypothesis']['status'],'proposed');self.assertEqual(b['nodes']['steward-always-chooses-hypothesis']['status'],'proposed')
 def test_design_explicit_reversal_keeps_history_and_open_consultation(self):
  a=snapshot('design','04-explicit-choice','before');b=snapshot('design','04-explicit-choice','after')
  self.assertEqual(b['nodes']['steward-always-chooses-decision']['status'],'accepted')
  self.assertEqual(b['nodes']['replacement-exception']['status'],'superseded');self.assertEqual(b['nodes']['atomic-replacement-hypothesis']['status'],'rejected')
  self.assertEqual(b['nodes']['replacement-exception']['meta']['rationale'],a['nodes']['replacement-exception']['meta']['rationale'])
  self.assertEqual(b['nodes']['replacement-question']['status'],'answered');self.assertEqual(a['nodes']['consultation-question'],b['nodes']['consultation-question'])
 def test_design_challenge_does_not_answer_or_mutate(self):
  self.assertEqual(snapshot('design','05-reviewer-challenge','before'),snapshot('design','05-reviewer-challenge','after'))
 def test_design_cases_remain_proposed_and_concern_unchanged(self):
  a=snapshot('design','06-M1688-summary','before');b=snapshot('design','07-M1689-summary','after')
  self.assertEqual(a['nodes']['cpu-intention'],b['nodes']['cpu-intention'])
  for key in ('m1688-review-loop-failure-mode','m1688-stop-and-handoff-proposal','m1689-goal-substitution-failure-mode','implementation-vs-intention-distinction','m1689-cheaper-requests-alternative'):
   self.assertEqual(b['nodes'][key]['status'],'proposed',key)
  self.assertEqual(b['nodes']['consultation-question']['status'],'open')
  self.assertEqual(b['nodes']['m1689-mechanism-reconsideration-question']['meta']['owner_under_accepted_design'],'steward-role')
  for key in ('m1688-summary-source','m1689-summary-source'):
   self.assertTrue(b['nodes'][key]['meta']['synthetic']);self.assertIn('primary',json.dumps(b['nodes'][key]).lower());self.assertIn('unavailable',json.dumps(b['nodes'][key]).lower())
class PassingPortsTrial(unittest.TestCase):
 base=ROOT/'reviews/multiturn/v2/ports'
 def test_S05_independent_receipt_integrity(self):
  r=load(self.base/'graded.json');self.assertTrue(r['passed'])
  for rel,digest in r['artifact_hashes'].items():self.assertEqual(sha(self.base/rel),digest,rel)
  gate=validate_receipt_file(ROOT,'reviews/multiturn/v2/ports/graded.json','S05');self.assertTrue(gate['valid'],gate)
  for stage in load(self.base/'participant.json')['stages']:
   self.assertEqual(stage['exit_code'],0);self.assertFalse(stage['budget']['calls_exceeded']);self.assertFalse(stage['budget']['time_exceeded'])
 def outputs(self,stage):
  found=[]
  for line in (self.base/'control'/stage/'stdout.jsonl').read_text().splitlines():
   entry=json.loads(line)
   for c in entry.get('message',{}).get('content',[]):
    if c.get('type')!='tool_result' or not isinstance(c.get('content'),str):continue
    for part in c['content'].splitlines():
     try:r=json.loads(part)
     except ValueError:continue
     if isinstance(r,dict) and r.get('claim')=='port-rule' and 'subjects' in r:found.append(r)
  return found
 def test_S05_actual_evaluator_and_unchanged_rule(self):
  a=self.outputs('02-identity-defined');b=self.outputs('03-counterexample');self.assertEqual(len(a),1);self.assertEqual(len(b),1)
  self.assertEqual(a[0]['outcome'],'satisfies');self.assertEqual([s['distinct_count'] for s in a[0]['subjects']],[1,1])
  self.assertEqual(b[0]['outcome'],'violates');self.assertEqual([s['distinct_count'] for s in b[0]['subjects']],[2,1]);self.assertTrue(b[0]['synthetic'])
  stage=self.base/'control/03-counterexample';before=load(stage/'before.graph.json');after=load(stage/'after.graph.json')
  self.assertEqual(before['nodes']['port-rule'],after['nodes']['port-rule']);self.assertEqual(before['nodes']['port-observations']['trace']['reports'],after['nodes']['port-observations']['trace']['reports'][:2])
 def test_S05_initial_unknown_and_exact_identity_source(self):
  stage=self.base/'control/01-identity-unknown';self.assertEqual((stage/'before.graph.json').read_bytes(),(stage/'after.graph.json').read_bytes())
  g=load(self.base/'control/02-identity-defined/after.graph.json');self.assertEqual(g['nodes']['port-rule']['pattern']['slot']['identity_key'],['host','number'])
  source=g['nodes']['src-port-identity-user-answer'];self.assertEqual(source['text'],'For this fixture, I define a port as the ordered pair (host, number).');self.assertEqual(source['meta']['speaker'],'user');self.assertNotIn('author',source['meta'])
class PacingTrial(unittest.TestCase):
 def test_S08_exact_command_precedes_only_tool(self):
  base=ROOT/'reviews/multiturn/pace4/design';r=load(base/'graded.json')
  for rel,digest in r['artifact_hashes'].items():self.assertEqual(sha(base/rel),digest,rel)
  gate=validate_receipt_file(ROOT,'reviews/multiturn/pace4/design/graded.json','S08');self.assertTrue(gate['valid'],gate)
  stage=base/'control/01-read-only';receipt=load(stage/'receipt.json');self.assertEqual(receipt['tool_call_count'],1)
  blocks=[]
  for line in (stage/'stdout.jsonl').read_text().splitlines():blocks.extend(json.loads(line).get('message',{}).get('content',[]))
  index=next(i for i,c in enumerate(blocks) if c.get('type')=='tool_use');tool=blocks[index]
  self.assertEqual(tool['name'],'Bash');self.assertEqual(tool['input']['command'],'./tg review steward-next-work')
  self.assertTrue(any(c.get('type')=='text' and './tg review steward-next-work' in c['text'] for c in blocks[:index]))
  self.assertEqual((stage/'before.graph.json').read_bytes(),(stage/'after.graph.json').read_bytes())
class ScopedDesignTrial(unittest.TestCase):
 base=ROOT/'reviews/multiturn/v2/design'
 def accepted(self,case):
  r=load(self.base/f'graded-{case}.json')
  for rel,digest in r['artifact_hashes'].items():self.assertEqual(sha(self.base/rel),digest,rel)
  gate=validate_receipt_file(ROOT,f'reviews/multiturn/v2/design/graded-{case}.json',case);self.assertTrue(gate['valid'],gate)
 def graph(self,stage,side='after'):return load(self.base/'control'/stage/(side+'.graph.json'))
 def test_S01_failed_question_reconciliation_cannot_pass(self):
  gate=validate_receipt_file(ROOT,'reviews/multiturn/v2/design/graded-S01.json','S01');self.assertFalse(gate['valid'])
  g=self.graph('04-explicit-choice');self.assertEqual(g['nodes']['replacement-question']['status'],'open');self.assertEqual(g['nodes']['consultation-question']['status'],'open')
 def test_S02_reviewer_challenge_preserves_policy_and_unknown(self):
  self.accepted('S02');a=self.graph('05-reviewer-challenge','before');b=self.graph('05-reviewer-challenge');self.assertEqual(a,b);self.assertEqual(b['nodes']['consultation-question']['status'],'open');self.assertEqual(b['nodes']['steward-always-chooses-policy']['status'],'accepted')
 def test_S03_summary_proposed_threshold_unknown(self):
  self.accepted('S03');g=self.graph('06-M1688-summary')
  for k in ['review-cascade-failure-mode','stop-threshold-handoff-proposal']:self.assertEqual(g['nodes'][k]['status'],'proposed')
  for k in ['stop-threshold-value-question','stopping-authority-question','post-termination-concern-question']:self.assertEqual(g['nodes'][k]['status'],'open')
  self.assertTrue(g['nodes']['m1688-summary-source']['meta']['synthetic']);self.assertIn('unavailable',json.dumps(g['nodes']['m1688-summary-source']))
 def test_S04_means_revisable_intention_retained(self):
  self.accepted('S04');a=self.graph('07-M1689-summary','before');b=self.graph('07-M1689-summary');self.assertEqual(a['nodes']['cpu-intention'],b['nodes']['cpu-intention'])
  for k in ['chosen-mechanism','objective-substitution-failure-mode','implementation-vs-intention-distinction','cheaper-requests-alternative','reconsideration-owned-by-steward']:self.assertEqual(b['nodes'][k]['status'],'proposed')
  self.assertEqual(b['nodes']['mechanism-reconsideration-question']['status'],'open')
  self.assertTrue(any(e['from']=='reconsideration-owned-by-steward' and e['to']=='steward-always-chooses-policy' and e['type']=='depends-on' for e in b['edges'].values()))
class CombinedObservability(unittest.TestCase):
 def test_S08_component_receipt_and_hypothesis_visibility(self):
  p='reviews/multiturn/S08/graded.json';r=load(ROOT/p)
  for rel,digest in r['artifact_hashes'].items():self.assertEqual(sha(ROOT/rel),digest,rel)
  check=validate_receipt_file(ROOT,p,'S08');self.assertTrue(check['valid'],check)
  d=ROOT/'reviews/multiturn/v2/design/control/02-atomic-proposal';a=load(d/'before.graph.json');b=load(d/'after.graph.json')
  self.assertEqual(a['nodes']['replacement-exception'],b['nodes']['replacement-exception']);self.assertEqual(a['nodes']['steward-next-work'],b['nodes']['steward-next-work'])
  self.assertEqual(b['nodes']['atomic-replacement-hypothesis']['status'],'proposed');self.assertTrue(b['nodes']['atomic-replacement-hypothesis-source']['meta']['synthetic']);self.assertEqual(b['revision'],1)
  response=load(d/'receipt.json')['result']['result']
  for key in ['atomic-replacement-hypothesis','atomic-replacement-question','revision 1']:self.assertIn(key,response)
class ExplicitDecisionFork(unittest.TestCase):
 base=ROOT/'reviews/multiturn/decision3/design'
 def test_S01_exact_fork_provenance_and_independent_grade(self):
  r=load(self.base/'graded-S01.json')
  for rel,digest in r['artifact_hashes'].items():self.assertEqual(sha(self.base/rel),digest,rel)
  gate=validate_receipt_file(ROOT,'reviews/multiturn/decision3/design/graded-S01.json','S01');self.assertTrue(gate['valid'],gate)
  m=load(self.base/'normalized-fork-manifest.json');self.assertEqual(m['fork_stage'],'04-explicit-choice');self.assertFalse(m['rerun_prior_stages'])
  for b in m['bindings']:self.assertEqual(sha(ROOT/b['source_path']),b['sha256']);self.assertEqual(sha(ROOT/b['copy_path']),b['sha256'])
  self.assertEqual(r['parent_hard_failures'],['01-read-only']);self.assertFalse(load(self.base/'graded.json')['passed'])
 def test_S01_question_resolved_without_consultation_decision(self):
  d=self.base/'control/04-explicit-choice';a=load(d/'before.graph.json');b=load(d/'after.graph.json')
  self.assertEqual(b['nodes']['replacement-question']['status'],'answered');self.assertEqual(a['nodes']['consultation-question'],b['nodes']['consultation-question'])
  self.assertEqual(b['nodes']['steward-always-chooses-decision']['status'],'accepted');self.assertEqual(b['nodes']['replacement-exception']['status'],'superseded');self.assertEqual(b['nodes']['atomic-replacement-hypothesis']['status'],'retired')
  self.assertEqual(a['nodes']['replacement-exception']['meta']['rationale'],b['nodes']['replacement-exception']['meta']['rationale'])
  edges=[e for e in b['edges'].values() if e['type']=='answers' and e['to']=='replacement-question'];self.assertTrue(any(e.get('coverage')=='full' and e.get('answer',{}).get('complete') is True for e in edges))
if __name__=='__main__':unittest.main()
