import contextlib,copy,importlib.util,io,json,tempfile,unittest
from pathlib import Path
from tests.paths import RepositoryPath as Path
from theorygraph import graph
spec=importlib.util.spec_from_file_location('maintenance',Path(__file__).resolve().parents[1]/'acceptance'/'run_maintenance_trials.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MaintenanceProtocolTests(unittest.TestCase):
 def test_preparation_has_equal_facts_and_no_grader_leak(self):
  with tempfile.TemporaryDirectory() as directory:
   out=Path(directory)/'pair'
   with contextlib.redirect_stdout(io.StringIO()):m.prepare(out)
   model=json.loads((out/'graph'/'graph.json').read_text());prose=m.parse_prose((out/'prose'/'theory.md').read_text())
   self.assertEqual(len([n for n in prose.values() if n['type']=='claim']),30)
   for nid,n in model['nodes'].items():
    if n['type']!='source':self.assertEqual(n['text'],prose[nid]['text'])
   for name in ['sources.md','unrelated-history.md']:self.assertEqual((out/'graph'/name).read_bytes(),(out/'prose'/name).read_bytes())
   self.assertFalse((out/'graph'/'expected.json').exists());self.assertFalse((out/'prose'/'expected.json').exists())
   self.assertNotIn('C02',(out/'graph'/'TASK.md').read_text());self.assertNotIn('C02',(out/'prose'/'TASK.md').read_text())
 def test_grader_requires_actual_changes_and_leaves_semantics_pending(self):
  with tempfile.TemporaryDirectory() as directory:
   out=Path(directory)/'pair'
   with contextlib.redirect_stdout(io.StringIO()):
    m.prepare(out);before=m.grade(out,'graph')
   self.assertIn('root_text_actually_changed',before['mechanical_failures']);self.assertIn('exact_dependents_need_review',before['mechanical_failures'])
   model=json.loads((out/'graph'/'graph.json').read_text());path=out/'graph'/'graph.json'
   graph.apply(path,[{'op':'update','collection':'nodes','id':'C01','value':{'text':'Deliberately bad revised meaning for a negative semantic control.','meta':{'review_state':'current','source_ref':'S04'}}},{'op':'add','collection':'nodes','id':'S04','value':{'type':'source','text':'Synthetic new source'}}],'synthetic-self-test','Test grader mechanics')
   (out/'graph'/'maintenance-report.json').write_text('{}')
   with contextlib.redirect_stdout(io.StringIO()):after=m.grade(out,'graph')
   # The preserved v0.1 rubric expects automatic flags, deliberately absent in v0.2.
   self.assertEqual(after['mechanical_failures'],['exact_dependents_need_review'])
   self.assertEqual(after['semantic_review']['status'],'pending-independent-review')
   # A wrong root is never presented as semantic success.
   self.assertNotIn('overall_pass',after)
 def test_stream_metrics_counts_actual_ids(self):
  messages=[{'type':'assistant','message':{'content':[{'type':'tool_use','id':'a','name':'Read'}]}},{'type':'assistant','message':{'content':[{'type':'tool_use','id':'a','name':'Read'}]}},{'type':'assistant','message':{'content':[{'type':'tool_use','id':'b','name':'Edit'}]}},{'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'b','is_error':True}]}},{'type':'result','usage':{'input_tokens':20}}]
  result=m.stream_metrics('\n'.join(json.dumps(x) for x in messages));self.assertEqual(result['tool_call_count'],2);self.assertEqual(result['tool_error_ids'],['b']);self.assertTrue(result['tool_metrics_available'])
