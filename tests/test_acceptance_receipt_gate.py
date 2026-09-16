"""Regression tests for falsely green empirical acceptance receipts."""
import copy,json,tempfile,unittest,hashlib
from pathlib import Path
from tests.paths import RepositoryPath as Path
from tests.acceptance.receipt_validation import grade_errors,author_receipt_errors,validate_receipt_file,agent_evidence

class ReceiptGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.r={'status':'completed','passed':True,'cases':['A01'],'grader':'independent-reviewer','hard_failures':[], 'grades':[{'id':'core','score':1,'excerpt':'exact answer','explanation':'reason'},{'id':'regression','score':1,'excerpt':'exact proposal','explanation':'reason'}]}
        self.rubric={'criteria':[{'id':'core'}],'regression_criteria':[{'id':'regression'}]}
        self.bind('raw',{'exit_code':0,'claude_result':{'is_error':False}});self.bind('input',{'graph':{}});self.bind('rubric',self.rubric)
        self.save()
    def bind(self,kind,data):
        p=self.root/(kind+'.json');p.write_text(json.dumps(data));self.r[kind+'_path']=p.name;self.r[kind+'_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    def save(self): (self.root/'graded.json').write_text(json.dumps(self.r))
    def valid(self): self.save();return validate_receipt_file(self.root,'graded.json','A01')
    def test_valid_case_bound_receipt(self):self.assertTrue(self.valid()['valid'])
    def test_passed_flag_cannot_hide_zero_score(self):
        self.r['grades'][0]['score']=0;self.assertIn('grade-not-passed',self.valid()['errors'])
    def test_bool_score_not_integer_grade(self):
        self.r['grades'][0]['score']=True;self.assertFalse(self.valid()['valid'])
    def test_missing_added_regression_does_not_pass(self):
        self.r['grades'].pop();self.assertIn('rubric-coverage-mismatch',self.valid()['errors'])
    def test_duplicate_grade_does_not_cover_other_criterion(self):
        self.r['grades'][1]['id']='core';self.assertFalse(self.valid()['valid'])
    def test_receipt_cannot_be_reused_for_uncovered_case(self):
        self.assertIn('case-not-covered',validate_receipt_file(self.root,'graded.json','M01')['errors'])
    def test_stale_raw_or_rubric_hash_rejected(self):
        (self.root/'raw.json').write_text('{}');self.assertIn('raw-hash-mismatch',self.valid()['errors'])
    def test_failed_original_application_not_ignored(self):
        self.bind('raw',{'proposal':{'proposed_operations':[{'op':'add'}]},'apply':{'returncode':1}});self.assertIn('proposal-not-applied',self.valid()['errors'])
    def test_completed_and_hardfailures_required(self):
        self.r['status']='not-run';self.r['hard_failures']=['invented acceptance'];self.assertFalse(self.valid()['valid'])
    def test_full_mechanical_plus_partial_agent_stays_partial(self):
        maps=[{'coverage':'full','tests':['mechanical']},{'coverage':'partial','evidence_kind':'agent-receipt','receipts':['graded.json']}]
        self.assertFalse(agent_evidence(self.root,maps,'A01')['full'])
    def test_one_valid_receipt_cannot_hide_missing_required_receipt(self):
        m=[{'coverage':'full','evidence_kind':'agent-receipt','receipts':['graded.json','missing.json']}]
        self.assertFalse(agent_evidence(self.root,m,'A01')['full'])
    def test_empty_receipt_list_not_full(self):
        self.assertFalse(agent_evidence(self.root,[{'coverage':'full','evidence_kind':'agent-receipt','receipts':[]}],'A01')['full'])
    def test_replay_context_must_equal_participant_context(self):
        errors=author_receipt_errors({},self.r,self.rubric,{'graph':{'state':'before'}},{'state':'after'})
        self.assertIn('replay-input-differs-from-participant-input',errors)
    def test_artifacts_hash_bound(self):
        artifact=self.root/'events.jsonl';artifact.write_text('event');self.r['artifact_hashes']={'events.jsonl':hashlib.sha256(artifact.read_bytes()).hexdigest()};self.assertTrue(self.valid()['valid']);artifact.write_text('changed');self.assertFalse(self.valid()['valid'])
    def aggregate(self):
        for key in ('raw_path','raw_sha256','input_path','input_sha256'):self.r.pop(key)
        original=copy.deepcopy(self.r['grades'])
        self.r['grades']=[dict(g,id='graph/'+g['id']) for g in original]
        self.bind('rubric',{'required_grades':['graph/core','graph/regression']})
        self.r['arms']={'graph':{'raw_receipt':'arm.json','semantic_review':'review.json'}}
        self.r['artifact_hashes']={}
        for filename,data in [('arm.json',{'exit_code':0}),('review.json',{'core_semantic_grades':original})]:
            p=self.root/filename;p.write_text(json.dumps(data));self.r['artifact_hashes'][filename]=hashlib.sha256(p.read_bytes()).hexdigest()
    def test_aggregate_bound_original_reviews_pass(self):
        self.aggregate();self.assertTrue(self.valid()['valid'])
    def test_aggregate_cannot_drop_failed_required_criterion(self):
        self.aggregate();self.r['grades'].pop();self.assertIn('rubric-coverage-mismatch',self.valid()['errors'])
    def test_aggregate_cannot_rewrite_original_grade(self):
        self.aggregate();self.r['grades'][0]['excerpt']='different';self.assertIn('aggregate-grade-differs-from-original',self.valid()['errors'])
    def test_aggregate_cannot_omit_raw_binding(self):
        self.aggregate();self.r['artifact_hashes'].pop('arm.json');self.assertIn('aggregate-unbound-raw_receipt',self.valid()['errors'])
    def test_path_escape_rejected(self):
        self.r['raw_path']='../outside.json';self.assertFalse(self.valid()['valid'])

if __name__=='__main__':unittest.main()
