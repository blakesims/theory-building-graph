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
