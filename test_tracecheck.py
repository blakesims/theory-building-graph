import copy, json, tempfile, unittest
from pathlib import Path
import graph, tracecheck as checker

class TraceChecks(unittest.TestCase):
 def setUp(self):
  role=lambda:{'type':'entity','text':'Role','meta':{'kind':'agent-role'}}
  self.g={'version':1,'revision':0,'node_types':{'claim':{},'trace':{},'entity':{},'operation':{}},'edge_types':{},'edges':{},'changes':[], 'nodes':{
   'steward-role':role(),'orchestrator-role':role(),'record-type':{'type':'entity','text':'Record'},
   'choose-work':{'type':'operation','text':'Choose subsequent work'},'end-attempt':{'type':'operation','text':'End attempt'},
   'c':{'type':'claim','text':'Only steward chooses after end','status':'proposed','pattern':{'kind':'exclusive_actor','operation':'choose-work','allowed_role':'steward-role','scope':'after_attempt_ended'}},
   't':{'type':'trace','text':'Synthetic example','status':'recorded','meta':{'synthetic':True},'trace':{'complete':True,'events':[
    {'id':'end','operation':'end-attempt','actor':'o1','actor_role':'orchestrator-role','attempt':'a'},
    {'id':'choose','operation':'choose-work','actor':'s1','actor_role':'steward-role','attempt':'a','after':'end'}]}}}}
 def evaluate(self):return checker.evaluate(self.g,'c','t')
 def choice(self):return self.g['nodes']['t']['trace']['events'][1]
 def test_positive_and_counterexample(self):
  self.assertEqual(self.evaluate()['outcome'],'satisfies');self.choice()['actor_role']='orchestrator-role';r=self.evaluate();self.assertEqual(r['outcome'],'violates');self.assertEqual(r['witnesses'][0]['event'],'choose')
 def test_missing_information(self):
  original=copy.deepcopy(self.g)
  for field in ('actor_role','actor','attempt','after'):
   with self.subTest(field=field):
    self.g=copy.deepcopy(original);self.choice().pop(field);self.assertEqual(self.evaluate()['outcome'],'insufficient-information')
 def test_scope_links(self):
  original=copy.deepcopy(self.g)
  for change in ('attempt','order','wrong-operation','duplicate'):
   with self.subTest(change=change):
    self.g=copy.deepcopy(original);events=self.g['nodes']['t']['trace']['events']
    if change=='attempt':self.choice()['attempt']='different'
    elif change=='order':events.reverse()
    elif change=='wrong-operation':events[0]['operation']='choose-work'
    else:events.append(copy.deepcopy(events[0]))
    self.assertEqual(self.evaluate()['outcome'],'insufficient-information')
 def test_nonvacuous_and_complete(self):
  self.g['nodes']['t']['trace']['complete']=False;self.assertEqual(self.evaluate()['outcome'],'insufficient-information')
  self.g['nodes']['t']['trace']['complete']=True;self.g['nodes']['t']['trace']['events'].pop();r=self.evaluate();self.assertEqual(r['outcome'],'insufficient-information');self.assertEqual(r['out_of_scope_events'],['end'])
 def test_violation_precedes_unknown(self):
  self.choice()['actor_role']='orchestrator-role';extra=copy.deepcopy(self.choice());extra['id']='unknown';extra.pop('actor_role');self.g['nodes']['t']['trace']['events'].append(extra);r=self.evaluate();self.assertEqual(r['outcome'],'violates');self.assertTrue(r['diagnostics'])
 def test_unsupported(self):
  original=copy.deepcopy(self.g)
  for mutation in ('no-pattern','scope','kind','operation','missing-operation','nonrole'):
   with self.subTest(mutation=mutation):
    self.g=copy.deepcopy(original);p=self.g['nodes']['c']['pattern']
    if mutation=='no-pattern':self.g['nodes']['c'].pop('pattern')
    elif mutation=='missing-operation':del self.g['nodes']['end-attempt']
    elif mutation=='nonrole':p['allowed_role']='record-type'
    else:p[mutation]='unsupported'
    self.assertEqual(self.evaluate()['outcome'],'not-checked')
 def test_event_nonrole(self):
  self.choice()['actor_role']='record-type';self.assertEqual(self.evaluate()['outcome'],'insufficient-information')
 def test_input_freshness(self):
  original=copy.deepcopy(self.g);r=self.evaluate();self.assertEqual(checker.result_state(self.g,r),'current')
  for input_id in ('c','t','steward-role','orchestrator-role','choose-work','end-attempt'):
   with self.subTest(input=input_id):
    self.g=copy.deepcopy(original);self.g['nodes'][input_id]['text']+=' changed';self.assertEqual(checker.result_state(self.g,r),'stale')
  self.g=copy.deepcopy(original);self.g['nodes']['c']['meta']={'review_state':'needs-review','review_reason':'Unrelated review'};self.assertEqual(checker.result_state(self.g,r),'current')
  self.g['nodes']['c']['pattern']['allowed_role']='orchestrator-role';self.assertEqual(checker.result_state(self.g,r),'stale');self.assertEqual(self.evaluate()['outcome'],'violates')
 def test_missing_dependency_becomes_known(self):
  self.choice()['actor_role']='new-role';r=self.evaluate();self.assertEqual(r['outcome'],'insufficient-information');self.g['nodes']['new-role']=copy.deepcopy(self.g['nodes']['steward-role']);self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_saved_audit_and_beliefs_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'g.json';p.write_text(json.dumps(self.g));r=self.evaluate();saved=graph.save_evaluation(p,self.g,r);g=graph.load(p)
   self.assertEqual(len(g['changes']),1);self.assertEqual(g['nodes']['c'],self.g['nodes']['c']);self.assertEqual(g['nodes']['t'],self.g['nodes']['t']);self.assertEqual(checker.result_state(g,r),'current');self.assertEqual(g['nodes'][saved['saved_as']]['result'],r)
   g['nodes']['t']['trace']['events'][1]['actor_role']='orchestrator-role';self.assertEqual(checker.evaluations(g,'c')['results'][0]['result_state'],'stale')

if __name__=='__main__':unittest.main()

class EvidenceChecks(unittest.TestCase):
 setUp=TraceChecks.setUp
 evaluate=TraceChecks.evaluate
 choice=TraceChecks.choice
 def with_provenance(self):
  self.g['nodes']['source']={'type':'source','text':'Synthetic: operator ended attempt; steward chose next.', 'meta':{'synthetic':True}}
  self.g['nodes']['extract']={'type':'extraction','text':'Interpretation, not the source itself','provenance':{'author':'agent','assumptions':['Order reflects observed sequence.']}}
  self.g['edges']={'source-edge':{'from':'extract','to':'source','type':'extracted-from'},'trace-edge':{'from':'t','to':'extract','type':'extracted-from'}}
 def test_E01_provenance_and_transitive_freshness(self):
  self.with_provenance();r=self.evaluate()
  self.assertEqual(r['provenance']['nodes'],['c','extract','source','t'])
  self.assertEqual(set(r['provenance']['edges']),{'source-edge','trace-edge'})
  self.assertEqual(self.g['nodes']['extract']['provenance']['author'],'agent')
  self.g['nodes']['source']['text']+=' Correction.'
  self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_E01_extraction_assumption_and_edge_changes_stale(self):
  self.with_provenance();original=copy.deepcopy(self.g);r=self.evaluate()
  self.g['nodes']['extract']['provenance']['assumptions'].append('Different role identity.')
  self.assertEqual(checker.result_state(self.g,r),'stale')
  self.g=copy.deepcopy(original);del self.g['edges']['source-edge']
  self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_E02_current_role_does_not_rewrite_event_role(self):
  self.g['nodes']['s1']={'type':'entity','text':'Session','meta':{'role':'steward-role'}}
  self.choice()['actor_role']='orchestrator-role'
  r=self.evaluate();self.assertEqual(r['outcome'],'violates');self.assertEqual(r['witnesses'][0]['actor_role'],'orchestrator-role')
 def test_E05_intended_violation_does_not_edit_beliefs(self):
  self.g['nodes']['c']['status']='accepted';self.g['nodes']['t']['polarity']='intended';self.choice()['actor_role']='orchestrator-role'
  original=copy.deepcopy(self.g);r=self.evaluate();self.assertEqual(r['assessment']['findings'][0]['code'],'intention-theory-mismatch')
  self.assertEqual(r['assessment']['findings'][0]['possible_causes'],['claim wrong','case mislabeled','extraction wrong']);self.assertEqual(self.g,original)
 def test_E06_defect_passing_is_coverage_gap(self):
  self.g['nodes']['t']['polarity']='defect';r=self.evaluate()
  self.assertEqual(r['outcome'],'satisfies');self.assertEqual(r['assessment']['findings'][0]['code'],'known-defect-unexplained')
 def test_E07_synthetic_propagates_and_never_establishes_history(self):
  self.with_provenance();self.g['nodes']['t']['meta']={};r=self.evaluate()
  self.assertTrue(r['synthetic']);self.assertEqual(r['assessment']['historical_behavior'],'not-established')
 def test_E08_reachability_is_not_implemented(self):
  self.choice()['actor_role']='orchestrator-role';r=self.evaluate()
  self.assertEqual(r['outcome'],'violates');self.assertEqual(r['assessment']['reachability']['outcome'],'not-checked')
 def test_provenance_cycle_and_visual_edits(self):
  self.with_provenance();self.g['edges']['cycle']={'from':'source','to':'extract','type':'extracted-from'}
  r=self.evaluate();self.g['nodes']['source']['position']={'x':1,'y':2};self.assertEqual(checker.result_state(self.g,r),'current')
 def test_missing_provenance_not_silently_omitted(self):
  self.with_provenance();del self.g['nodes']['source'];r=self.evaluate()
  self.assertEqual(r['provenance']['missing'],['source']);self.assertIn('missing-provenance-input',[d['code'] for d in r['diagnostics']])

class FormalDispatchTests(unittest.TestCase):
 setUp=TraceChecks.setUp
 evaluate=TraceChecks.evaluate
 choice=TraceChecks.choice
 def test_authority_dispatch_and_fragment_freshness(self):
  self.g['nodes']['c']['pattern']={'kind':'authority','modality':'only','role':'steward-role','operation':'choose-work','scope':'after_attempt_ended'}
  r=self.evaluate();self.assertEqual(r['outcome'],'satisfies');self.assertEqual(checker.result_state(self.g,r),'current')
  self.g['formal_model']={'role_disjoint':[['steward-role','orchestrator-role']]};self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_undeclared_pattern_references_remain_unchecked(self):
  self.g['nodes']['c']['pattern']={'kind':'cardinality','min':1,'max':1,'scope':'all','slot':{'subject_type':'record-type','target_type':'steward-role','relation':'missing-relation','identity_key':['id'],'count':'distinct'}}
  self.g['nodes']['t']['trace']={'complete':True,'reports':[{'subject':{'id':'r1'},'target':'s1'}]}
  r=self.evaluate();self.assertEqual(r['outcome'],'not-checked');self.assertEqual(r['diagnostics'][0]['code'],'undeclared-pattern-reference')

class DefinitionAcceptanceTests(unittest.TestCase):
 setUp=TraceChecks.setUp
 evaluate=TraceChecks.evaluate
 choice=TraceChecks.choice
 def test_D03_role_policy_applies_to_distinct_sessions(self):
  self.g['nodes']['session-A']={'type':'entity','text':'Session A','meta':{'kind':'agent-session'}}
  self.g['nodes']['session-B']={'type':'entity','text':'Session B','meta':{'kind':'agent-session'}}
  for session in ('session-A','session-B'):
   self.choice()['actor']=session;r=self.evaluate();self.assertEqual(r['outcome'],'satisfies')
   # The same role policy accepts either session, but witnesses identify the
   # particular actor when its event-time role changes.
   self.choice()['actor_role']='orchestrator-role';failed=self.evaluate()
   self.assertEqual(failed['outcome'],'violates')
   self.assertEqual(failed['witnesses'][0]['actor'],session)
   self.choice()['actor_role']='steward-role'
  self.assertEqual(sum(n['type']=='claim' for n in self.g['nodes'].values()),1)
 def test_D08_pattern_evaluation_does_not_ratify_prose(self):
  self.g['nodes']['c']['status']='accepted';self.g['nodes']['c']['meta']={'pattern_standing':'proposed'}
  original=copy.deepcopy(self.g);r=self.evaluate();self.assertEqual(r['outcome'],'satisfies');self.assertEqual(r['pattern_standing'],'proposed');self.assertEqual(r['claim_standing'],'accepted');self.assertIn('Does not check',r['scope']);self.assertEqual(self.g,original)
 def test_I07_all_semantic_inputs_and_checker_are_bound(self):
  original=copy.deepcopy(self.g);r=self.evaluate()
  for identity in ('c','t','steward-role','orchestrator-role','choose-work','end-attempt'):
   self.g=copy.deepcopy(original);self.g['nodes'][identity]['text']+=' changed meaning';self.assertEqual(checker.result_state(self.g,r),'stale',identity)
  self.g=copy.deepcopy(original);old=checker.CHECKER_VERSION
  try:
   checker.CHECKER_VERSION='different';self.assertEqual(checker.result_state(self.g,r),'stale')
  finally:checker.CHECKER_VERSION=old
  self.g['nodes']['unrelated']={'type':'entity','text':'unrelated entity'};self.assertEqual(checker.result_state(self.g,r),'current')
 def test_review_receipts_do_not_invalidate(self):
  r=self.evaluate();self.g['nodes']['c']['meta']={'review_state':'needs-review','reviewed_inputs':{'x':'abc'},'reviewed_input_versions':{'x':2},'review_roots':['x'],'sources':['a display citation']};self.g['nodes']['c']['semantic_version']=10
  self.assertEqual(checker.result_state(self.g,r),'current')

class ReviewRegressionTests(unittest.TestCase):
 setUp=TraceChecks.setUp
 evaluate=TraceChecks.evaluate
 choice=TraceChecks.choice
 def modern(self):
  self.g['nodes']['c']['pattern']={'kind':'authority','modality':'only','role':'steward-role','operation':'choose-work','scope':'after_attempt_ended'}
 def save_memory(self,result):
  self.g['nodes']['receipt']={'type':'check-result','text':'Bounded receipt','result':result}
 def test_P11_witness_only_event_role_revision_stales_modern_check(self):
  self.modern();self.choice()['actor_role']='orchestrator-role';r=self.evaluate()
  self.assertEqual(r['outcome'],'violates');self.assertIn('orchestrator-role',r['input_fingerprints']);self.assertEqual(checker.result_state(self.g,r),'current')
  self.g['nodes']['orchestrator-role']['text']='Changed role meaning'
  self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_P11_role_lists_and_event_operations_are_bound(self):
  self.modern();self.choice().pop('actor_role');self.choice()['actor_roles']=['orchestrator-role'];r=self.evaluate()
  self.assertEqual(r['outcome'],'violates');self.assertIn('orchestrator-role',r['input_fingerprints']);self.assertIn('end-attempt',r['input_fingerprints'])
  self.g['nodes']['end-attempt']['text']='New terminal semantics';self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_P11_missing_event_role_definition_becoming_known_stales(self):
  self.modern();self.choice()['actor_role']='new-role';r=self.evaluate();self.assertIsNone(r['input_fingerprints']['new-role'])
  self.g['nodes']['new-role']={'type':'entity','text':'New role','meta':{'kind':'agent-role'}};self.assertEqual(checker.result_state(self.g,r),'stale')
 def test_P20_receipt_counts_without_topic_edge(self):
  self.save_memory(self.evaluate());r=checker.coverage(self.g,'c')
  self.assertTrue(r['has_coverage']);self.assertEqual(r['state'],'evaluated');self.assertEqual(r['current_evaluations'][0]['id'],'receipt');self.assertTrue(r['current_evaluations'][0]['synthetic'])
 def test_P20_stale_receipt_no_longer_current_coverage(self):
  self.save_memory(self.evaluate());self.g['nodes']['c']['text']+=' revised';r=checker.coverage(self.g,'c')
  self.assertFalse(r['has_coverage']);self.assertEqual(len(r['stale_evaluations']),1)
 def test_P20_about_trace_does_not_mean_tested(self):
  self.g['edges']['topic']={'from':'c','to':'t','type':'about'}
  self.assertFalse(checker.coverage(self.g,'c')['has_coverage'])
 def test_P20_explicit_evidence_link_is_declared_not_evaluated(self):
  for relation,src,dst in [('tests','t','c'),('supports','t','c'),('tested-by','c','t')]:
   self.g['edges']={'e':{'from':src,'to':dst,'type':relation}};r=checker.coverage(self.g,'c')
   self.assertTrue(r['has_coverage']);self.assertEqual(r['state'],'declared-evidence');self.assertEqual(r['current_evaluations'],[]);self.assertEqual(r['declared_evidence'][0]['evaluation'],'not-implied')
 def test_P20_unsupported_check_receipt_is_not_test_coverage(self):
  self.g['nodes']['c'].pop('pattern');self.save_memory(self.evaluate());r=checker.coverage(self.g,'c')
  self.assertFalse(r['has_coverage']);self.assertEqual(len(r['unchecked_evaluations']),1)

class VacuityRegressionTests(unittest.TestCase):
 setUp=TraceChecks.setUp
 evaluate=TraceChecks.evaluate
 def modern(self,modality='only'):
  self.g['nodes']['c']['pattern']={'kind':'authority','modality':modality,'role':'steward-role','operation':'choose-work','scope':'all'}
 def test_P9_modern_empty_is_explicitly_vacuous_not_defect_evidence(self):
  self.modern();self.g['nodes']['t']['trace']['events']=[];self.g['nodes']['t']['polarity']='defect';r=self.evaluate()
  self.assertEqual(r['outcome'],'satisfies');self.assertTrue(r['vacuous']);self.assertEqual(r['checked_events'],[]);self.assertFalse(r['empirical_support'])
  self.assertIn('no-matching-event',[d['code'] for d in r['diagnostics']]);self.assertEqual(r['assessment']['findings'],[])
  rendered=graph.compact(r);self.assertIn('checked events: []',rendered);self.assertIn('vacuous',rendered);self.assertIn('no-matching-event',rendered)
 def test_P9_may_is_not_empirical_permission_evidence(self):
  self.modern('may');self.g['nodes']['t']['polarity']='defect';r=self.evaluate()
  self.assertEqual(r['outcome'],'satisfies');self.assertTrue(r['permission_only']);self.assertFalse(r['empirical_support']);self.assertEqual(r['assessment']['findings'],[])
  self.assertIn('permission-only',[d['code'] for d in r['diagnostics']])
 def test_P9_nonempty_defect_fragment_still_reports_unexplained(self):
  self.modern();self.g['nodes']['t']['polarity']='defect';r=self.evaluate()
  self.assertEqual(r['outcome'],'satisfies');self.assertFalse(r['vacuous']);self.assertEqual(r['assessment']['findings'][0]['code'],'known-defect-unexplained')
  rendered=graph.compact(r);self.assertIn('known-defect-unexplained',rendered);self.assertIn('not-checked',rendered)
 def test_P9_legacy_stays_nonvacuous(self):
  self.g['nodes']['t']['trace']['events']=[];self.assertEqual(self.evaluate()['outcome'],'insufficient-information')
