import copy
import json
import tempfile
import unittest
from pathlib import Path
from theorygraph import replay

A=lambda name:{'$arg':name}
S=lambda *path:{'$state':list(path)}
E=lambda name:{'$event':name}

def theory_model():
    """Synthetic explicit interpretation of agreed rules; no stopping rule invented."""
    record=['records',A('record')]
    duty=lambda owner:{'owner':owner,'state':'pending','record':A('record'),'intention':S(*record,'intention'),'evidence':A('evidence')}
    return {'meta':{'synthetic':True,'source':'Morphisms design session; executable interpretation requires separate review'},'initial':{
        'intentions':{'I':{'state':'open','text':'reduce CPU','valid':True}},
        'records':{'A':{'intention':'I','lifecycle':'running','outcome':None},'B':{'intention':'I','lifecycle':'running','outcome':None}},
        'responses':{},'decisions':{'D':{'owner':'operator','answer':None}},
        'config':{'desk':True,'next_work_roles':['steward']},'pulse':[],
        'roles':{'assistant':{'start':'user','drive':'user'},'architect':{'start':'user','drive':'user'},'orchestrator':{'start':'user','drive':'autonomous'},'steward':{'start':'event','drive':'autonomous'}}},
      'rules':[
        {'id':'blocked-report','on':'blocked','guards':[{'path':record+['lifecycle'],'equals':'running'}],'effects':[
          {'op':'set','path':record+['lifecycle'],'value':'blocked'},
          {'op':'create','path':['responses',E('id')],'value':duty('orchestrator')}]},
        {'id':'recovery','on':'recover','guards':[{'path':['responses',A('response'),'owner'],'equals':'orchestrator'}],'effects':[
          {'op':'set','path':record+['lifecycle'],'value':'running'},
          {'op':'set','path':['responses',A('response'),'state'],'value':'resolved'}]},
        {'id':'terminal-result','on':'end','guards':[{'path':record+['lifecycle'],'not_equals':'ended'}],'effects':[
          {'op':'set','path':record+['lifecycle'],'value':'ended'},
          {'op':'set','path':record+['outcome'],'value':A('outcome')},
          {'op':'create','path':['responses',E('id')],'value':duty('steward')}]},
        {'id':'choose-subsequent-work','on':'choose','guards':[{'path':['config','next_work_roles'],'includes':A('role')},{'path':['roles',A('role')],'exists':True},{'path':['responses',A('response'),'owner'],'equals':A('role')},{'path':['responses',A('response'),'state'],'equals':'pending'}],'effects':[
          {'op':'create','path':['records',A('new_record')],'value':{'intention':S('responses',A('response'),'intention'),'lifecycle':'running','outcome':None}},
          {'op':'set','path':['responses',A('response'),'state'],'value':'resolved'}]},
        {'id':'consider-completion','on':'consider','effects':[{'op':'set','path':['responses',A('response'),'state'],'value':'resolved'}]},
        {'id':'answer-decision','on':'answer','guards':[{'path':['decisions',A('decision'),'answer'],'equals':None}],'effects':[
          {'op':'set','path':['decisions',A('decision'),'answer'],'value':A('answer')},
          {'op':'set','path':['decisions',A('decision'),'owner'],'value':'orchestrator'}]},
        {'id':'route-with-dial','on':'route','effects':[{'op':'append','path':['pulse'],'value':{'intention':A('intention'),'desk':S('config','desk')}}]}
      ]}

def event(eid,kind,**args):return {'id':eid,'kind':kind,'args':args}

class ModelReplayTests(unittest.TestCase):
 def setUp(self):self.model=theory_model()
 def test_M01_intention_survives_replacement(self):
  result=replay.run(self.model,[event('endA','end',record='A',outcome='failed',evidence='failed brief'),event('next','choose',response='endA',role='steward',new_record='C')])
  first,last=result['receipts'];self.assertEqual(first['state']['intentions']['I']['state'],'open')
  self.assertEqual(last['state']['records']['A']['outcome'],'failed');self.assertEqual(last['state']['records']['C']['intention'],'I');self.assertEqual(list(result['state']['intentions']),['I'])
 def test_M02_recoverable_block_does_not_wake_steward(self):
  result=replay.run(self.model,[event('blockA','blocked',record='A',evidence='worktree missing'),event('recovered','recover',record='A',response='blockA')])
  self.assertEqual(result['receipts'][0]['state']['responses']['blockA']['owner'],'orchestrator')
  self.assertEqual(result['state']['records']['A']['lifecycle'],'running');self.assertEqual(result['state']['responses']['blockA']['state'],'resolved')
  self.assertFalse(any(r['owner']=='steward' for r in result['state']['responses'].values()))
 def test_M03_failed_is_ended_not_satisfied(self):
  r=replay.run(self.model,[event('endA','end',record='A',outcome='failed',evidence='operator selected end')])
  self.assertEqual(r['state']['records']['A'],{'intention':'I','lifecycle':'ended','outcome':'failed'})
  self.assertEqual(r['state']['responses']['endA']['owner'],'steward');self.assertEqual(r['state']['intentions']['I']['state'],'open')
 def test_M04_checkpoint_keeps_owed_response(self):
  result=replay.run(self.model,[event('blockA','blocked',record='A',evidence='no venue')])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'checkpoint.json';p.write_text(json.dumps(result));resumed=replay.run(self.model,[],checkpoint=json.loads(p.read_text()))
  self.assertEqual(resumed['state']['responses']['blockA'],{'owner':'orchestrator','state':'pending','record':'A','intention':'I','evidence':'no venue'})
  broken=copy.deepcopy(self.model);broken['rules'][0]['effects'].append({'op':'set','path':['missing'],'value':1})
  rejected=replay.run(broken,[event('blockA','blocked',record='A',evidence='no venue')])
  self.assertEqual(rejected['state']['records']['A']['lifecycle'],'running');self.assertEqual(rejected['revision'],0)
 def test_M05_each_completion_remains_pending(self):
  r=replay.run(self.model,[event('endA','end',record='A',outcome='succeeded',evidence='benchmark A'),event('endB','end',record='B',outcome='succeeded',evidence='benchmark B'),event('reviewA','consider',response='endA')])
  self.assertEqual(r['receipts'][0]['state']['records']['B']['lifecycle'],'running');self.assertEqual(r['receipts'][0]['state']['responses']['endA']['owner'],'steward')
  self.assertEqual(r['state']['responses']['endA']['state'],'resolved');self.assertEqual(r['state']['responses']['endB']['state'],'pending')
 def test_M06_one_decision_across_interfaces(self):
  first=event('chat','answer',decision='D',answer='end failed');first['expect_revision']=0
  stale=event('desk','answer',decision='D',answer='keep trying');stale['expect_revision']=0
  r=replay.run(self.model,[first,stale]);self.assertEqual(r['state']['decisions']['D'],{'owner':'orchestrator','answer':'end failed'})
  self.assertEqual(r['receipts'][1]['reason'],'stale-revision');self.assertEqual(r['revision'],1)
 def test_M07_dials_change_route_not_validity(self):
  for enabled in (True,False):
   model=copy.deepcopy(self.model);model['initial']['config']['desk']=enabled;r=replay.run(model,[event('route','route',intention='I')])
   self.assertEqual(r['state']['intentions']['I'],model['initial']['intentions']['I']);self.assertEqual(r['state']['pulse'],[{'intention':'I','desk':enabled}])
 def test_M08_start_and_drive_are_independent(self):
  # Separate explicit finite fixture: changing drive does not change launch.
  # This exercises the two axes; it is not a Morphisms scheduling implementation.
  for drive in ('user','autonomous'):
   m={'initial':{'start':'user','drive':drive,'running':False,'turns':[]},'rules':[
    {'id':'launch','on':'launch','guards':[{'path':['start'],'equals':A('signal')}],
     'effects':[{'op':'set','path':['running'],'value':True}]},
    {'id':'turn','on':'turn','guards':[{'path':['running'],'equals':True},{'path':['drive'],'equals':A('signal')}],
     'effects':[{'op':'append','path':['turns'],'value':E('id')}]}]}
   r=replay.run(m,[event('start','launch',signal='user'),event('background','turn',signal='autonomous')])
   self.assertTrue(r['state']['running'])
   self.assertEqual(r['state']['turns'],['background'] if drive=='autonomous' else [])
   self.assertEqual(r['revision'],2 if drive=='autonomous' else 1)
   not_started=replay.run(m,[event('wrong-start','launch',signal='event')])
   self.assertFalse(not_started['state']['running'])
 def test_no_silent_stopping_or_cancellation_policy(self):
  r=replay.run(self.model,[event('threshold','threshold-reached',record='A'),event('cancel','cancel',record='A')]);self.assertEqual(r['state'],self.model['initial']);self.assertEqual([x['reason'] for x in r['receipts']],['no-enabled-rule','no-enabled-rule'])
 def test_model_identity_and_event_deduplication(self):
  e=event('route','route',intention='I');r=replay.run(self.model,[e,e]);self.assertEqual(r['receipts'][1]['reason'],'duplicate-event')
  changed=copy.deepcopy(self.model);changed['initial']['config']['desk']=False
  with self.assertRaisesRegex(replay.ReplayError,'checkpoint-model-mismatch'):replay.run(changed,[],checkpoint=r)
 def test_unrelated_vocabulary_uses_same_engine(self):
  model={'initial':{'books':{'b':{'shelf':'A'}}},'rules':[{'id':'move','on':'move','effects':[{'op':'set','path':['books',A('book'),'shelf'],'value':A('shelf')}]}]}
  self.assertEqual(replay.run(model,[event('m','move',book='b',shelf='B')])['state']['books']['b']['shelf'],'B')

if __name__=='__main__':unittest.main()

class SessionReplayTests(unittest.TestCase):
 def test_S01_reversal_preserves_each_stage(self):
  from theorygraph import graph; from acceptance import session_fixtures
  g,steps=session_fixtures.replacement_session()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'graph.json';p.write_text(json.dumps(g))
   for index,step in enumerate(steps):
    graph.apply(p,step['ops'],'fixture-user',step['source'],expected=index);current=graph.load(p)
    if index<2:
     self.assertEqual(current['nodes']['replacement-exception']['status'],'accepted')
     self.assertEqual(current['nodes']['replacement-question']['status'],'open')
     self.assertEqual(current['nodes']['atomic-replacement']['status'],'proposed')
    else:
     self.assertEqual(current['nodes']['steward-next-work']['status'],'accepted')
     for key in ('replacement-exception','atomic-replacement'):
      self.assertEqual(current['nodes'][key]['status'],'withdrawn');self.assertEqual(current['nodes'][key]['meta']['review_state'],'historical')
     self.assertEqual(current['nodes']['consultation']['status'],'open')
     self.assertEqual(current['nodes']['replacement-question']['status'],'retired')
   self.assertEqual(len(current['changes']),3)
   self.assertIn('replacement-exception',graph.walk(current,'steward-next-work',depth=1,current=False)['nodes'])
   self.assertNotIn('replacement-exception',graph.walk(current,'steward-next-work',depth=1,current=True)['nodes'])
 def test_S02_potential_conflict_does_not_resolve_policy(self):
  from theorygraph import graph; from acceptance import session_fixtures
  g=session_fixtures.base_graph()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'g.json';p.write_text(json.dumps(g))
   graph.apply(p,[session_fixtures.add('may-ask',type='claim',text='Orchestrator may ask operator before ending.',status='proposed'),session_fixtures.add('threshold-ending',type='claim',text='Orchestrator can end work above configured threshold.',status='proposed'),{'op':'add','collection':'edges','id':'possible-tension','value':{'from':'may-ask','to':'threshold-ending','type':'potential-conflict','meta':{'rationale':'Check whether consultation is required or optional; no formal contradiction established.'}}}],'reviewer','Flag ambiguity only',expected=0)
   current=graph.load(p);self.assertEqual(current['nodes']['consultation']['status'],'open');self.assertEqual(current['nodes']['steward-next-work']['status'],'accepted')
   self.assertIn('no formal contradiction',current['edges']['possible-tension']['meta']['rationale'])
 def test_S03_summary_provenance_and_candidate_only(self):
  from theorygraph import graph; from acceptance import session_fixtures
  g=session_fixtures.base_graph()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'g.json';p.write_text(json.dumps(g))
   graph.apply(p,[session_fixtures.add('loop-extraction',type='extraction',text='Repeated useful reviews lacked an effective ruling; motivates recovery boundary.',status='proposed',provenance={'author':'agent','sources':['source-3'],'assumptions':['Summary only; primary source not available.']}),session_fixtures.add('stop-threshold',type='question',text='What threshold should stop a degraded attempt?',status='open')],'assistant','Propose interpretation of summary',expected=0)
   current=graph.load(p);self.assertEqual(current['nodes']['loop-extraction']['status'],'proposed');self.assertEqual(current['nodes']['stop-threshold']['status'],'open')
   self.assertEqual(current['nodes']['consultation']['status'],'open');self.assertEqual(current['nodes']['source-3']['meta']['source_kind'],'summary')
 def test_S04_implementation_choice_can_change_without_goal(self):
  from theorygraph import graph; from acceptance import session_fixtures
  g=session_fixtures.base_graph();g['nodes']['cpu']={'type':'entity','text':'Intention: reduce CPU','status':'declared'}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'g.json';p.write_text(json.dumps(g))
   graph.apply(p,[session_fixtures.add('mechanism',type='claim',text='A notification mechanism will reduce CPU.',status='proposed',meta={'sources':['source-3']}),session_fixtures.add('serves-intention',type='question',text='Does this chosen work still serve the intention?',status='open',meta={'owner_role':'steward-role'}),{'op':'add','collection':'edges','id':'question-concern','value':{'from':'serves-intention','to':'cpu','type':'about'}}],'assistant','Review proposed means against continuing concern',expected=0)
   current=graph.load(p);self.assertEqual(current['nodes']['cpu'],g['nodes']['cpu']);self.assertEqual(current['nodes']['mechanism']['status'],'proposed');self.assertEqual(current['nodes']['serves-intention']['meta']['owner_role'],'steward-role')
 def test_S05_identity_changes_witness_not_prose_guess(self):
  from theorygraph import formalcheck
  pattern={'kind':'cardinality','min':1,'max':1,'slot':{'subject_type':'port','relation':'owned-by','target_type':'owner','count':'distinct'}}
  reports=[{'subject':{'host':'a','number':8080},'target':'alice'},{'subject':{'host':'b','number':8080},'target':'bob'}]
  self.assertEqual(formalcheck.evaluate_cardinality(pattern,reports,True)['outcome'],'insufficient-information')
  pattern['slot']['identity_key']=['host','number']
  self.assertEqual(formalcheck.evaluate_cardinality(pattern,reports,True)['outcome'],'satisfies')
  reports.append({'subject':{'host':'a','number':8080},'target':'bob'})
  self.assertEqual(formalcheck.evaluate_cardinality(pattern,reports,True)['outcome'],'violates')
 def test_S06_S07_packets_same_facts_and_no_fake_trial(self):
  from acceptance import session_evaluation as se
  with tempfile.TemporaryDirectory() as d:
   r=se.prepare(d);data=json.loads((Path(d)/'graph-arm.json').read_text());prose=(Path(d)/'prose-arm.md').read_text()
   for fact in data['facts']:
    self.assertIn('## '+fact['id'],prose)
    for key,val in fact.items():
     if key!='id':self.assertIn(key+': '+(json.dumps(val,ensure_ascii=False) if not isinstance(val,str) else val),prose)
   receipt=json.loads((Path(d)/'receipt-template.json').read_text());self.assertEqual(receipt['status'],'not-run');self.assertFalse(se.validate_receipt(receipt)['valid'])
   self.assertEqual(r['status'],'prepared-not-run')
 def test_S08_cli_read_then_authorized_single_batch(self):
  import subprocess,sys; from acceptance import session_fixtures
  g,steps=session_fixtures.replacement_session()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'graph.json';p.write_text(json.dumps(g));before=p.read_bytes()
   command=[sys.executable,str(Path(__file__).resolve().parents[1]/'tg'),'--file',str(p),'--json','review','steward-role']
   # The transcript artifact is a demonstration of exact commands and outcomes,
   # not proof that an independent agent obeyed a user's pacing instruction.
   read=subprocess.run(command,capture_output=True,text=True,check=True)
   self.assertEqual(p.read_bytes(),before);self.assertIn('steward-role',json.loads(read.stdout)['nodes'])
   batch=Path(d)/'change.json';batch.write_text(json.dumps(steps[0]['ops']))
   write=[sys.executable,str(Path(__file__).resolve().parents[1]/'tg'),'--file',str(p),'--json','apply',str(batch),'--actor','fixture-user','--reason',steps[0]['source'],'--expect','0']
   applied=subprocess.run(write,capture_output=True,text=True,check=True);self.assertEqual(json.loads(p.read_text())['revision'],1)
   self.assertEqual(json.loads(p.read_text())['nodes']['atomic-replacement']['status'],'proposed');self.assertIn('revision',json.loads(applied.stdout))
