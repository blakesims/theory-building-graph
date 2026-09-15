import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('graph',Path(__file__).with_name('graph.py')); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'graph.json'
  self.g={'version':1,'revision':0,'node_types':{'claim':{}},'edge_types':{'supports':{}},'nodes':{n:{'type':'claim','text':n,'meta':{'keep':1}} for n in 'abc'},'edges':{'ab':{'from':'a','to':'b','type':'supports'},'bc':{'from':'b','to':'c','type':'supports'}},'changes':[]};self.path.write_text(json.dumps(self.g))
 def tearDown(self):self.tmp.cleanup()
 def apply(self,ops,expect=None):return m.apply(self.path,ops,'test','verify',expect)
 def test_walk(self):
  self.assertEqual(list(m.walk(self.g,'a',0)['nodes']),['a']);self.assertEqual(len(m.walk(self.g,'a',1)['nodes']),2)
  self.assertEqual(len(m.walk(self.g,'c',4,'out')['nodes']),1);self.assertEqual(len(m.walk(self.g,'c',4,'in')['nodes']),3)
  r=m.walk(self.g,'a',4,limit=2);self.assertTrue(r['truncated']);self.assertEqual(len(r['edges']),1)
 def test_reverse_metadata_audit(self):
  self.apply([{'op':'add','collection':'edges','id':'ba','value':{'from':'b','to':'a','type':'supports'}},{'op':'update','collection':'nodes','id':'a','value':{'meta':{'new':2}}}])
  g=m.load(self.path);self.assertEqual(g['nodes']['a']['meta'],{'keep':1,'new':2});self.assertEqual(len(g['edges']),3);self.assertEqual(len(g['changes']),1);self.assertEqual(g['changes'][0]['edits'][1]['before']['meta'],{'keep':1})
 def test_failure_atomic(self):
  before=self.path.read_bytes()
  with self.assertRaises(m.GraphError):self.apply([{'op':'update','collection':'nodes','id':'a','value':{'text':'changed'}},{'op':'add','collection':'edges','id':'bad','value':{'from':'a','to':'missing','type':'supports'}}])
  self.assertEqual(self.path.read_bytes(),before)
  with self.assertRaises(m.GraphError):self.apply([{'op':'update','collection':'nodes','id':'a','value':{'text':'changed'}}],8)
  self.assertEqual(self.path.read_bytes(),before)
 def test_extensible(self):
  self.apply([{'op':'add','collection':'node_types','id':'idea','value':{'description':'new'}},{'op':'update','collection':'nodes','id':'a','value':{'type':'idea','extra':{'anything':True}}}]);self.assertTrue(m.load(self.path)['nodes']['a']['extra']['anything'])
 def test_edge_limit(self):
  r=m.walk(self.g,'a',4,edge_limit=1);self.assertTrue(r['edge_truncated']);self.assertEqual(len(r['edges']),1)
 def test_review_invalidation(self):
  self.g['nodes']['b']['type']='question';self.g['node_types']['question']={};self.g['edge_types']['answers']={};self.g['edges']['ab']['type']='answers';self.path.write_text(json.dumps(self.g))
  self.apply([{'op':'update','collection':'nodes','id':'a','value':{'text':'revised'}}])
  g=m.load(self.path);self.assertEqual(m.review_state(g['nodes']['b']),'needs-review');self.assertEqual(m.questions(g)['counts'],{'needs-review':1})
  self.apply([{'op':'update','collection':'nodes','id':'a','value':{'meta':{'review_state':'historical'}}},{'op':'update','collection':'nodes','id':'b','value':{'meta':{'review_state':'current'}}}])
  g=m.load(self.path);self.assertEqual(m.questions(g)['counts'],{'open':1});self.assertNotIn('a',m.walk(g,'b',2,current=True)['nodes'])
 def test_metadata_no_invalidation(self):
  self.apply([{'op':'update','collection':'nodes','id':'a','value':{'meta':{'source':'added citation'}}}]);g=m.load(self.path);self.assertEqual(len(g['changes'][0]['edits']),1);self.assertEqual(m.review_state(g['nodes']['a']),'current')
 def test_answer_edge_flags_target(self):
  self.g['edge_types']['answers']={};self.path.write_text(json.dumps(self.g))
  self.apply([{'op':'add','collection':'edges','id':'answer','value':{'type':'answers','from':'a','to':'b'}}]);self.assertEqual(m.review_state(m.load(self.path)['nodes']['b']),'needs-review')
 def test_corrupt(self):
  self.path.write_text('{')
  with self.assertRaises(ValueError):m.load(self.path)
if __name__=='__main__':unittest.main()

class ReviewUpgradeTests(unittest.TestCase):
 def setUp(self):
  self.g={'version':1,'revision':0,'node_types':{'claim':{'states':['accepted','proposed']},'question':{'states':['open','answered']},'entity':{}},'edge_types':{'answers':{'coverage_required':True},'about':{}},'nodes':{'c':{'type':'claim','text':'statement','status':'accepted'},'q':{'type':'question','text':'question','status':'open'},'hub':{'type':'entity','text':'hub','meta':{'title':'Steward','aliases':['steward'] }},'other':{'type':'claim','text':'other','status':'proposed'}},'edges':{'answer':{'from':'c','to':'q','type':'answers','coverage':'partial'},'anchor':{'from':'c','to':'hub','type':'about'},'other-anchor':{'from':'other','to':'hub','type':'about'}},'changes':[]}
 def test_partial_full_and_historical_counts(self):
  self.assertEqual(m.questions(self.g)['counts'],{'partial-answer':1})
  self.g['edges']['answer']['coverage']='full';self.assertEqual(m.questions(self.g)['counts'],{'answered':1})
  self.g['nodes']['q']['meta']={'review_state':'historical'}
  r=m.questions(self.g);self.assertEqual(r['total_questions'],1);self.assertEqual(r['historical_excluded'],1);self.assertEqual(r['included_questions'],0)
 def test_state_validation_and_answer_coverage(self):
  m.validate(self.g)
  self.g['nodes']['c']['status']='user-stated'
  with self.assertRaises(m.GraphError): m.validate(self.g)
  self.g['nodes']['c']['status']='accepted';del self.g['edges']['answer']['coverage']
  with self.assertRaises(m.GraphError): m.validate(self.g)
 def test_alias_hub_stop_and_boundary(self):
  self.assertEqual(m.resolve(self.g,'steward'),'hub')
  r=m.walk(self.g,'c',2);self.assertNotIn('other',r['nodes']);self.assertGreater(r['boundary_edges'],0)
  self.assertIn('other',m.walk(self.g,'c',2,anchors='cross')['nodes'])
 def test_history_summary(self):
  self.g['changes']=[{'revision':1,'actor':'a','reason':'r','edits':[{'collection':'nodes','id':'c','before':{'text':'x'*20000},'after':{'text':'y'*20000}}]}]
  self.assertLess(len(json.dumps(m.history(self.g))),1000)
  self.assertGreater(len(json.dumps(m.history(self.g,full=True))),40000)
 def test_check_recorded_tension(self):
  self.g['edge_types']['potential-conflict']={};self.g['edges']['t']={'from':'c','to':'other','type':'potential-conflict'}
  self.assertIn('potential-conflict',m.check(self.g)['counts'])
 def test_search_state_and_failure(self):
  self.g['nodes']['c']['text']='Attempt failed'
  self.assertIn('c',m.search(self.g,'failure')['nodes']);self.assertIn('c',m.search(self.g,'accepted')['nodes'])
