import contextlib,importlib.util,io,json,tempfile,unittest
from pathlib import Path
import graph
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('multiturn',ROOT/'acceptance'/'run_multiturn_trials.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MultiturnProtocolTests(unittest.TestCase):
 def test_future_turns_are_not_in_participant_files(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'trial'
   with contextlib.redirect_stdout(io.StringIO()):m.prepare(out)
   for name in ('design','ports'):
    graph.load(out/name/'graph.json');self.assertFalse((out/name/'future-turns.json').exists());self.assertFalse((out/name/'grader-only.json').exists())
    self.assertEqual(json.loads((out/'control'/name/'history.json').read_text()),[])
   initial=json.loads((out/'design'/'graph.json').read_text());self.assertEqual(initial['nodes']['replacement-exception']['status'],'accepted');self.assertNotIn('atomic-replacement',initial['nodes'])
   self.assertNotIn('identity_key',json.loads((out/'ports'/'graph.json').read_text())['nodes']['port-rule']['pattern']['slot'])
 def test_each_turn_has_separate_grader_criteria(self):
  self.assertEqual(len(m.DESIGN_TURNS),7);self.assertEqual(len(m.PORT_TURNS),3)
  for trial,turns in [('design',m.DESIGN_TURNS),('ports',m.PORT_TURNS)]:
   self.assertEqual(set(m.RUBRIC[trial]),{t['id'] for t in turns})
   self.assertTrue(all(t['user'] and t['cases'] for t in turns))

 def test_contract_injected_before_turn_without_future_or_grader(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'trial'
   with contextlib.redirect_stdout(io.StringIO()):m.prepare(out)
   contract=(out/'control'/'design'/'authoring-contract.txt').read_text()
   prompt=m.build_prompt(contract,[],m.DESIGN_TURNS[0]['user'])
   self.assertIn(contract,prompt);self.assertLess(prompt.index(contract),prompt.index(m.DESIGN_TURNS[0]['user']))
   self.assertIn('no extra read of it is required',prompt)
   for turn in m.DESIGN_TURNS[1:]:self.assertNotIn(turn['user'],prompt)
   for criteria in m.RUBRIC['design'].values():
    for criterion in criteria:self.assertNotIn(criterion,prompt)
   for name in ('design','ports'):
    for doc in ('FORMAL-SCHEMA.md','DEPENDENCY-SCHEMA.md'):
     source=ROOT/'acceptance'/doc if doc=='FORMAL-SCHEMA.md' else ROOT/doc
     self.assertEqual((out/name/doc).read_bytes(),source.read_bytes())
