"""Regressions from independent Fable 5.1 CLI probes; isolated graphs only."""
import copy,json,tempfile,unittest
from pathlib import Path
import graph
import dependency
from test_dependency import fixture,edge

class FableDependencyRegressions(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'graph.json'
 def tearDown(self):self.tmp.cleanup()
 def put(self,model):self.path.write_text(json.dumps(model))
 def edit(self,nid,**value):graph.apply(self.path,[{'op':'update','collection':'nodes','id':nid,'value':value}],'regression','Independent review probe');return graph.load(self.path)
 def test_N3_question_requirement_typos_and_legacy_reject_atomically(self):
  for required in ['answerd','accepted']:
   with self.subTest(required=required):
    model=fixture();self.put(model);before=self.path.read_bytes()
    batch=[{'op':'update','collection':'nodes','id':'A','value':{'text':'Must roll back'}},
           {'op':'add','collection':'edges','id':'B-depends-on-Q','value':{'type':'depends-on','from':'B','to':'Q','requires':[required]}}]
    with self.assertRaisesRegex(graph.GraphError,'B-depends-on-Q.*question resolution'):
     graph.apply(self.path,batch,'regression','Invalid question prerequisite')
    self.assertEqual(self.path.read_bytes(),before)
    edge(model,'B','Q',requires=[required]);self.put(model)
    with self.assertRaisesRegex(graph.GraphError,'No automatic migration'):
     graph.load(self.path)
 def test_N3_partial_question_resolution_is_valid_requirement(self):
  model=fixture();edge(model,'B','Q',requires=['partial-answer']);edge(model,'A','Q','answers',coverage='partial')
  graph.validate(model)
  self.assertEqual(dependency.resolution(model,'Q')['resolution'],'partial-answer')
  self.assertEqual(dependency.readiness(model,'B')['readiness'],'ready')
 def test_N3_declared_custom_status_vocabulary_respected(self):
  model=fixture();model['node_types']['milestone']={'states':['queued','verified']};model['nodes']['A'].update(type='milestone',status='verified')
  edge(model,'B','A',requires=['verified']);self.put(model)
  self.assertEqual(dependency.readiness(graph.load(self.path),'B')['readiness'],'ready')
  before=self.path.read_bytes()
  with self.assertRaisesRegex(graph.GraphError,'milestone.*verified'):
   graph.apply(self.path,[{'op':'update','collection':'edges','id':'B-depends-on-A','value':{'requires':['verifed']}}],'regression','Typo must not persist')
  self.assertEqual(self.path.read_bytes(),before)
 def test_P1_clearing_unchanged_review_does_not_stale_receipt(self):
  model=fixture();edge(model,'B','A');edge(model,'Q','B');self.put(model)
  self.edit('A',text='new premise')
  second=self.edit('Q',meta={'review_state':'current'});receipt=copy.deepcopy(second['nodes']['Q']['meta']['reviewed_inputs'])
  third=self.edit('B',meta={'review_state':'current'})
  self.assertEqual(dependency.currency(third['nodes']['Q']),'current');self.assertEqual(third['nodes']['Q']['meta']['reviewed_inputs'],receipt)
  self.assertEqual(dependency.currency(self.edit('B',text='changed consequence')['nodes']['Q']),'needs-review')
 def test_P2_custom_edge_add_remove_invalidates_dependents(self):
  for action in ['add','delete']:
   with self.subTest(action=action):
    model=fixture();model['edge_types']['derived']={'invalidation':'dependent-to-prerequisite','readiness':True};edge(model,'Q','B')
    if action=='delete':edge(model,'B','A','derived')
    self.put(model);op={'op':action,'collection':'edges','id':'B-derived-A'}
    if action=='add':op['value']={'type':'derived','from':'B','to':'A'}
    graph.apply(self.path,[op],'regression','Custom dependency topology edit');after=graph.load(self.path)
    self.assertEqual(dependency.currency(after['nodes']['B']),'needs-review');self.assertEqual(dependency.currency(after['nodes']['Q']),'needs-review')
 def test_P3_question_prerequisite_uses_derived_answer(self):
  model=fixture();model['nodes']['B'].update(type='question',status='answered');edge(model,'Q','B',requires=['answered'])
  self.assertEqual(dependency.resolution(model,'B')['resolution'],'open');self.assertEqual(dependency.readiness(model,'Q')['readiness'],'blocked')
  model['nodes']['B']['status']='open';edge(model,'A','B','answers',coverage='full')
  self.assertEqual(dependency.readiness(model,'Q')['readiness'],'ready')
  model['nodes']['A']['meta']={'review_state':'needs-review'};self.assertEqual(dependency.readiness(model,'Q')['readiness'],'blocked')
 def test_P5_malformed_formal_sections_are_atomic_without_patterns(self):
  for key,value in [('scopes',None),('scopes',[]),('scopes',{'all':None}),('scopes',{'all':{'members':None}}),('scope_subset',[['a']]),('role_disjoint',{}),('actors',{'actor':None}),('subjects',None)]:
   with self.subTest(key=key,value=value):
    self.put(fixture());before=self.path.read_bytes()
    with self.assertRaises(graph.GraphError):graph.apply(self.path,[{'op':'add','collection':'formal_model','id':key,'value':value}],'regression','Invalid shape')
    self.assertEqual(self.path.read_bytes(),before)
  self.put(fixture());before=self.path.read_bytes()
  with self.assertRaisesRegex(graph.GraphError,'value'):graph.apply(self.path,[{'op':'add','collection':'formal_model','id':'scopes'}],'regression','Missing value')
  self.assertEqual(self.path.read_bytes(),before)
 def test_P26_null_meta_rejected_atomically(self):
  self.put(fixture());before=self.path.read_bytes()
  with self.assertRaisesRegex(graph.GraphError,'meta'):self.edit('A',meta=None)
  self.assertEqual(self.path.read_bytes(),before)
 def test_P28_single_directional_answer_drift_finding(self):
  model=fixture();model['nodes']['Q']['status']='answered'
  relevant=[f for f in graph.check(model)['findings'] if f['code'] in ['answer-state-drift','unsupported-answered-state']]
  self.assertEqual(len(relevant),1);self.assertEqual(relevant[0]['code'],'answer-state-drift');self.assertEqual(relevant[0]['stored_state'],'answered');self.assertEqual(relevant[0]['derived_resolution'],'open')
  model['nodes']['Q']['status']='open';edge(model,'A','Q','answers',coverage='full')
  relevant=[f for f in graph.check(model)['findings'] if f['code']=='answer-state-drift'];self.assertEqual(len(relevant),1);self.assertEqual(relevant[0]['derived_resolution'],'answered')
 def test_P32_formal_finding_id_ignores_observation_revision(self):
  model=fixture();model['formal_model']={'scopes':{'all':{'members':['w']}},'role_disjoint':[['B','C']]}
  model['nodes']['A']['pattern']={'kind':'authority','modality':'only','role':'B','operation':'Q','scope':'all'}
  model['nodes']['B']['pattern']={'kind':'authority','modality':'may','role':'C','operation':'Q','scope':'all'}
  first=next(f for f in graph.check(model)['findings'] if f['code']=='policy-conflict');model['revision']+=1
  second=next(f for f in graph.check(model)['findings'] if f['code']=='policy-conflict');self.assertEqual(first['id'],second['id']);self.assertNotEqual(first['computed_revision'],second['computed_revision'])
 def test_P24_retired_dependency_path_remains_actionable(self):
  model=fixture();edge(model,'B','A');edge(model,'C','B');model['nodes']['B']['meta']={'review_state':'historical'};self.put(model)
  after=self.edit('A',text='new premise');self.assertEqual(dependency.currency(after['nodes']['B']),'historical');self.assertEqual(dependency.currency(after['nodes']['C']),'needs-review')
  self.assertEqual(dependency.readiness(after,'C')['readiness'],'blocked')

class FableScopeAndPresentationRegressions(unittest.TestCase):
 def test_H2_default_question_requirement_is_answered(self):
  model=fixture();model['nodes']['B'].update(type='question',status='open');edge(model,'Q','B')
  self.assertEqual(dependency.readiness(model,'Q')['readiness'],'blocked')
  edge(model,'A','B','answers',coverage='full');self.assertEqual(dependency.readiness(model,'Q')['readiness'],'ready')
 def test_M3_question_header_and_severity_are_readable(self):
  model=fixture()
  for i in range(30):
   model['nodes'][f'Q{i}']={'type':'question','text':'Unanswered question','status':'open'};edge(model,f'Q{i}','A')
  output=graph.compact(graph.questions(model));firstline=output.splitlines()[0]
  self.assertNotIn('blockers',firstline);self.assertNotIn('readiness={',firstline);self.assertLess(len(firstline),500)
  findings=graph.compact(graph.check(model));self.assertIn('[informational]',findings);self.assertIn('[review]',findings)
 def test_L3_attempt_label_is_not_global_reference(self):
  model=fixture();model['nodes']['T']={'type':'trace','text':'Trace','trace':{'events':[{'id':'event','operation':'C','actor':'local-session','actor_role':'B','attempt':'A'}]}}
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'graph.json';path.write_text(json.dumps(model))
   graph.apply(path,[{'op':'delete','collection':'nodes','id':'A'}],'regression','Remove unrelated ID matching local attempt label')
   after=graph.load(path);self.assertEqual(after['nodes']['T']['trace']['events'][0]['attempt'],'A')
   with self.assertRaisesRegex(graph.GraphError,'semantic reference'):
    graph.apply(path,[{'op':'delete','collection':'nodes','id':'C'}],'regression','Cannot remove referenced operation')
 def test_L5_historical_patterns_do_not_emit_current_gap(self):
  model=fixture();model['nodes']['A'].update(pattern={'kind':'authority','role':'missing','operation':'also-missing','scope':'all'},meta={'review_state':'historical'})
  self.assertNotIn('undeclared-pattern-reference',graph.check(model)['counts'])
 def test_P4_comparison_does_not_invent_scope_existence(self):
  model=fixture();model['nodes']['A']['pattern']={'kind':'authority','modality':'only','role':'B','operation':'Q','scope':'all'};model['nodes']['B']['pattern']={'kind':'authority','modality':'may','role':'C','operation':'Q','scope':'all'}
  model['formal_model']={'role_disjoint':[['B','C']]}
  self.assertNotIn('policy-conflict',graph.check(model)['counts'])
  model['formal_model']['scopes']={'all':{}};self.assertNotIn('policy-conflict',graph.check(model)['counts'])
  model['formal_model']['scopes']['all']['nonempty']=True;self.assertIn('policy-conflict',graph.check(model)['counts'])
