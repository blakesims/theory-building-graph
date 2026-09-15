"""Integrity and observed-state assertions for an actual independent tool trial.

The external semantic grade is retained with answer excerpts. These tests do not
re-grade English or pretend the authored model is the live Morphisms runtime.
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reviews/interpretation'
WORK=REPORT/'workspace'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())

class IndependentInterpretationReceipts(unittest.TestCase):
 def setUp(self):
  self.assertTrue((REPORT/'graded.json').exists(),'Actual interpretation trial and independent grading must exist; an unrun fixture is not a pass.')
  self.grade=load(REPORT/'graded.json');self.assertEqual(self.grade['status'],'completed');self.assertTrue(self.grade['passed']);self.assertEqual(self.grade['hard_failures'],[])
  for rel,digest in self.grade['artifact_hashes'].items():self.assertEqual(sha(REPORT/rel),digest,rel)
 def accepted(self,case):
  rows=[r for r in self.grade['grades'] if r.get('case')==case]
  self.assertEqual(len(rows),1,case);self.assertEqual(rows[0]['score'],1);self.assertTrue(rows[0]['excerpt']);self.assertTrue(rows[0]['output_witnesses'])
 def output(self,label):
  receipt=load(WORK/'runs'/f'{label}.json');self.assertIn('command',receipt);self.assertIsInstance(receipt['elapsed_seconds'],(int,float));return json.loads(receipt['stdout'])
 def test_commands_and_source_hashes(self):
  required={'continuation','recovery','checkpoint-save','checkpoint-resume','completions','decision','route-on','route-off','roles','unsettled','node-source','node-extract','evaluate','inspect-before','apply-assumption','inspect-after'}
  self.assertEqual(set(self.grade['command_receipts']),required)
  for label in sorted(required):
   entry=self.grade['command_receipts'][label];path=WORK/'runs'/f'{label}.json';r=load(path)
   self.assertEqual(sha(path),entry['sha256']);self.assertEqual(r['command'],entry['command']);self.assertEqual(r['returncode'],entry['returncode'])
   self.assertEqual(r['returncode'],1 if label in ('decision','unsettled') else 0,label)
  manifest=load(WORK/'input-manifest.json')
  for rel,digest in manifest.items():
   if rel!='evidence.graph.json':self.assertEqual(sha(WORK/rel),digest,rel)
  for row in self.grade['grades']:
   self.assertTrue(row['excerpt']);self.assertTrue(row['explanation']);self.assertEqual(row['score'],1)
 def test_evidence_changes_were_authorized(self):
  before=load(REPORT/'original-evidence.graph.json');after=load(WORK/'evidence.graph.json');manifest=load(WORK/'input-manifest.json')
  self.assertEqual(sha(REPORT/'original-evidence.graph.json'),manifest['evidence.graph.json'])
  self.assertEqual(after['revision'],2);self.assertEqual(len(after['changes']),2)
  self.assertEqual(after['nodes']['source']['text'],before['nodes']['source']['text'])
  self.assertEqual(after['nodes']['t']['trace'],before['nodes']['t']['trace'])
  for field in ('text','status','pattern'):self.assertEqual(after['nodes']['c'].get(field),before['nodes']['c'].get(field))
  change=load(WORK/'assumption-edit.json')[0]['value']['provenance']
  self.assertEqual(after['nodes']['extract']['provenance'],change)
  self.assertEqual(after['nodes']['evidence-check']['type'],'check-result')
 def test_M01_continuing_intention(self):
  self.accepted('M01');r=self.output('continuation');s=r['state'];self.assertEqual(list(s['intentions']),['I']);self.assertEqual(s['intentions']['I']['state'],'open');self.assertEqual(s['records']['A']['intention'],'I');self.assertEqual(s['records']['C']['intention'],'I')
 def test_M02_recovery(self):
  self.accepted('M02');r=self.output('recovery');self.assertEqual(r['receipts'][0]['state']['responses']['blockA']['owner'],'orchestrator');self.assertEqual(r['state']['records']['A']['lifecycle'],'running');self.assertEqual(r['state']['responses']['blockA']['state'],'resolved')
 def test_M03_failed_terminal(self):
  self.accepted('M03');s=self.output('continuation')['receipts'][0]['state'];self.assertEqual(s['records']['A']['lifecycle'],'ended');self.assertEqual(s['records']['A']['outcome'],'failed');self.assertEqual(s['intentions']['I']['state'],'open');self.assertEqual(s['responses']['endA']['owner'],'steward')
 def test_M04_separate_checkpoint_processes(self):
  self.accepted('M04');a=self.output('checkpoint-save');b=self.output('checkpoint-resume');self.assertEqual(a['state'],b['state']);self.assertEqual(b['state']['responses']['blockA']['owner'],'orchestrator');self.assertEqual(b['state']['responses']['blockA']['state'],'pending');self.assertEqual(b['receipts'],[])
  self.assertNotEqual(load(WORK/'runs/checkpoint-save.json')['command'],load(WORK/'runs/checkpoint-resume.json')['command'])
 def test_M05_completion_queue(self):
  self.accepted('M05');r=self.output('completions');self.assertEqual(r['receipts'][0]['state']['records']['B']['lifecycle'],'running');self.assertEqual(r['state']['responses']['endA']['state'],'resolved');self.assertEqual(r['state']['responses']['endB']['state'],'pending')
 def test_M06_one_decision(self):
  self.accepted('M06');r=self.output('decision');self.assertEqual(r['state']['decisions']['D'],{'owner':'orchestrator','answer':'end failed'});self.assertEqual(r['receipts'][1]['reason'],'stale-revision');self.assertEqual(r['revision'],1)
 def test_M07_routing_validity(self):
  self.accepted('M07');a=self.output('route-on')['state'];b=self.output('route-off')['state'];self.assertEqual(a['intentions'],b['intentions']);self.assertEqual(a['pulse'],[{'intention':'I','desk':True}]);self.assertEqual(b['pulse'],[{'intention':'I','desk':False}])
 def test_M08_start_drive(self):
  self.accepted('M08');roles=self.output('roles')['state']['roles'];self.assertEqual(roles['assistant'],{'start':'user','drive':'user'});self.assertEqual(roles['architect'],{'start':'user','drive':'user'});self.assertEqual(roles['orchestrator'],{'start':'user','drive':'autonomous'});self.assertEqual(roles['steward'],{'start':'event','drive':'autonomous'})
 def test_E01_provenance_and_freshness(self):
  self.accepted('E01');before=self.output('inspect-before')['results'][0];after=self.output('inspect-after')['results'][0]
  self.assertEqual(before['result_state'],'current');self.assertEqual(after['result_state'],'stale');self.assertEqual(before['outcome'],after['outcome']);self.assertTrue({'c','t','extract','source'}<=set(before['input_fingerprints']))
 def test_E07_synthetic_not_history(self):
  self.accepted('E07');r=self.output('evaluate');self.assertTrue(r['synthetic']);self.assertEqual(r['assessment']['historical_behavior'],'not-established');self.assertFalse(r['assessment']['empirical_support'])
 def test_unknown_policy_is_missing_rule_not_permission(self):
  r=self.output('unsettled');self.assertEqual(r['revision'],0);self.assertEqual([x['reason'] for x in r['receipts']],['no-enabled-rule','no-enabled-rule'])
  row=next(x for x in self.grade['grades'] if x['id']=='unknown-policy');self.assertEqual(row['score'],1);self.assertTrue(row['excerpt'])

if __name__=='__main__':unittest.main()
