import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from acceptance.receipt_validation import validate_receipt_file

class StagedGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.d=self.root/'trial';self.d.mkdir();self.artifacts={}
        self.initial={'revision':0};current=self.initial;stages=[]
        for i,name in enumerate(['pace','theory']):
            folder=self.d/'control'/name;folder.mkdir(parents=True)
            before=current;current={'revision':i+1}
            values={'before.graph.json':json.dumps(before),'after.graph.json':json.dumps(current),'prompt.txt':'prompt '+name,'stdout.jsonl':'{"type":"result"}\n'}
            for n,v in values.items():self.write('trial/control/'+name+'/'+n,v,raw=True)
            stage={'stage':name,'exit_code':0,'timed_out':False,'result':{'is_error':False},'data_changed':True}
            for key,n in [('before_sha256','before.graph.json'),('after_sha256','after.graph.json'),('prompt_sha256','prompt.txt'),('stdout_sha256','stdout.jsonl')]:stage[key]=self.sha(folder/n)
            self.write('trial/control/'+name+'/receipt.json',stage);stages.append(stage)
        self.participant={'exit_code':0,'stages':stages}
        self.input={'initial_graph':self.initial,'prompts':{'pace':'prompt pace','theory':'prompt theory'}}
        self.rubric={'criteria':[{'id':'pace','cases':['S08']},{'id':'theory','cases':['S01']}]}
        self.grades=[{'id':n,'score':i,'excerpt':'observed '+n,'explanation':'judged '+n} for n,i in [('pace',0),('theory',1)]]
        self.parent={'status':'completed','passed':False,'cases':['S01','S08'],'grader':'independent','hard_failures':['pace'],'grades':self.grades}
        for k,v in [('raw',self.participant),('input',self.input),('rubric',self.rubric)]:
            name='trial/'+k+'.json';self.write(name,v);self.parent[k+'_path']=name;self.parent[k+'_sha256']=self.sha(self.root/name)
        self.write('trial/graded.json',self.parent)
        self.child={**copy.deepcopy(self.parent),'cases':['S01'],'passed':True,'hard_failures':[],'grades':[self.grades[1]],'parent_trial':'trial','parent_graded_sha256':self.sha(self.d/'graded.json'),'parent_hard_failures':['pace']}
        self.write('trial/scoped-rubric.json',{'criteria':[self.rubric['criteria'][1]]});self.child['rubric_path']='trial/scoped-rubric.json';self.child['rubric_sha256']=self.sha(self.d/'scoped-rubric.json')
    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def write(self,name,value,raw=False):
        p=self.root/name;p.write_text(value if raw else json.dumps(value));self.artifacts[name]=self.sha(p)
    def check(self):
        self.child['artifact_hashes']=self.artifacts.copy();self.write('trial/scoped.json',self.child)
        return validate_receipt_file(self.root,'trial/scoped.json','S01')
    def test_correct_scoped_pass_discloses_failed_parent(self):self.assertTrue(self.check()['valid'])
    def test_cannot_omit_failed_stage_binding(self):
        self.artifacts.pop('trial/control/pace/stdout.jsonl');self.assertIn('stage-artifact-unbound:trial/control/pace/stdout.jsonl',self.check()['errors'])
    def test_cannot_change_parent_failure_disclosure(self):
        self.child['parent_hard_failures']=[];self.assertIn('parent-failures-not-disclosed',self.check()['errors'])
    def test_cannot_rehash_child_to_wrong_parent(self):
        self.child['parent_graded_sha256']='0'*64;self.assertIn('parent-grade-hash-mismatch',self.check()['errors'])
    def test_cannot_relabel_passing_criterion_for_other_case(self):
        self.child['grades'][0]=dict(self.child['grades'][0],id='pace')
        self.assertIn('scoped-parent-criteria-mismatch',self.check()['errors'])
    def test_cannot_rewrite_parent_grade_excerpt(self):
        self.child['grades']=copy.deepcopy(self.child['grades']);self.child['grades'][0]['excerpt']='invented'
        self.assertIn('scoped-grade-differs-from-parent',self.check()['errors'])
    def test_cannot_omit_failed_stage_from_raw(self):
        self.participant['stages']=self.participant['stages'][1:];self.write('trial/raw.json',self.participant)
        self.child['raw_sha256']=self.sha(self.d/'raw.json')
        self.assertIn('stage-input-coverage-mismatch',self.check()['errors'])
    def test_state_chain_checked_even_with_all_hashes_updated(self):
        p='trial/control/theory/before.graph.json';self.write(p,{'revision':99})
        self.participant['stages'][1]['before_sha256']=self.sha(self.root/p)
        self.write('trial/control/theory/receipt.json',self.participant['stages'][1]);self.write('trial/raw.json',self.participant)
        self.child['raw_sha256']=self.sha(self.d/'raw.json')
        self.assertIn('stage-state-chain-broken',self.check()['errors'])
    def test_partial_component_cannot_be_standalone_full_evidence(self):
        self.child['component_partial']=True;self.child['criterion_ids']=['theory']
        self.assertIn('partial-component-not-full-evidence',self.check()['errors'])

    def composite(self):
        self.child['component_partial']=True;self.child['criterion_ids']=['theory'];self.check()
        c={'status':'completed','passed':True,'cases':['S01'],'hard_failures':[],'grader':'independent',
           'grades':[{'id':'slot','score':1,'excerpt':'observed','explanation':'judged'}],
           'components':[{'id':'theory','receipt':'trial/scoped.json','case':'S01','criterion_ids':['theory'],'partial':True}],
           'parent_disclosures':[{k:self.child[k] for k in ('parent_trial','parent_graded_sha256','parent_hard_failures')}]}
        for k,v in [('raw',{'exit_code':0}),('input',{}),('rubric',{'criteria':[{'id':'slot','cases':['S01']}],'required_evidence_slots':{'slot':{'component':'theory','criteria':['theory']}}})]:
            n='combined-'+k+'.json';self.write(n,v);c[k+'_path']=n;c[k+'_sha256']=self.sha(self.root/n)
        c['artifact_hashes']={'trial/scoped.json':self.sha(self.d/'scoped.json')}
        return c
    def composite_check(self,c):
        self.write('combined.json',c);return validate_receipt_file(self.root,'combined.json','S01')
    def test_component_combination_valid_with_declared_slots(self):
        self.assertTrue(self.composite_check(self.composite())['valid'])
    def test_component_cannot_hide_failed_parent(self):
        c=self.composite();c['parent_disclosures']=[]
        self.assertIn('component-parent-failure-undisclosed',self.composite_check(c)['errors'])
    def test_component_cannot_drop_required_criterion(self):
        c=self.composite();c['components'][0]['criterion_ids']=[]
        self.assertIn('component-criteria-mismatch',self.composite_check(c)['errors'])

    def fork(self):
        folder=self.root/'source'/'control'/'pace';folder.mkdir(parents=True)
        bindings=[]
        for n in ('receipt.json','prompt.txt','stdout.jsonl','before.graph.json','after.graph.json'):
            original=self.d/'control'/'pace'/n;target=folder/n;target.write_bytes(original.read_bytes())
            bindings.append({'source_path':str(target.relative_to(self.root)),'copy_path':str(original.relative_to(self.root)),'sha256':self.sha(original)})
        self.manifest={'source_trial':'source','fork_stage':'theory','bindings':bindings}
        self.write('trial/fork.json',self.manifest)
        for item in (self.child,self.parent):
            item['fork_manifest_path']='trial/fork.json';item['fork_manifest_sha256']=self.sha(self.d/'fork.json')
        self.write('trial/graded.json',self.parent);self.child['parent_graded_sha256']=self.sha(self.d/'graded.json')
    def test_fork_preserves_original_prior_prompts_and_state(self):
        self.fork();self.assertTrue(self.check()['valid'])
    def test_fork_cannot_claim_new_contract_for_copied_stage(self):
        self.fork();(self.root/'source/control/pace/prompt.txt').write_text('different contract')
        self.assertIn('fork-source-copy-mismatch',self.check()['errors'])
    def test_fork_cannot_drop_prior_artifact_from_manifest(self):
        self.fork();self.manifest['bindings'].pop();self.write('trial/fork.json',self.manifest)
        self.child['fork_manifest_sha256']=self.sha(self.d/'fork.json')
        self.assertIn('fork-prior-artifact-binding-missing',self.check()['errors'])
    def test_child_cannot_hide_parent_fork(self):
        self.fork();self.child.pop('fork_manifest_path');self.child.pop('fork_manifest_sha256')
        self.assertIn('scoped-fork-provenance-mismatch',self.check()['errors'])

    def test_case_binding_required_even_without_scoped_parent(self):
        self.child.pop('parent_trial');self.child['raw_path']='trial/raw.json'
        self.child['grades']=copy.deepcopy(self.grades)
        self.child['grades'][0]['score']=1
        self.child['rubric_path']='trial/rubric.json';self.child['rubric_sha256']=self.sha(self.d/'rubric.json')
        self.child['cases']=['S01','unrelated']
        self.child['artifact_hashes']=self.artifacts.copy();self.write('trial/graded.json',self.child)
        checked=validate_receipt_file(self.root,'trial/graded.json','unrelated')
        self.assertIn('staged-case-has-no-criteria',checked['errors'])

    def rewrite_parent_binding(self):
        self.write('trial/graded.json',self.parent)
        self.child['parent_graded_sha256']=self.sha(self.d/'graded.json')
        self.child['parent_hard_failures']=self.parent['hard_failures']
    def test_parent_rewritten_passed_cannot_hide_its_zero_grades(self):
        self.parent['passed']=True;self.parent['hard_failures']=[];self.rewrite_parent_binding()
        errors=self.check()['errors']
        self.assertIn('parent-verdict-inconsistent-with-grades',errors)
        self.assertIn('parent-grade-failure-disclosure-mismatch',errors)
    def test_parent_cannot_drop_failed_grade_and_rehash(self):
        self.parent['grades']=[self.grades[1]];self.parent['passed']=True;self.parent['hard_failures']=[];self.rewrite_parent_binding()
        self.assertIn('parent-grade-rubric-coverage-mismatch',self.check()['errors'])
    def test_parent_cannot_narrow_rubric_away_from_failed_stages(self):
        self.parent['grades']=[self.grades[1]];self.parent['passed']=True;self.parent['hard_failures']=[]
        self.write('trial/rubric.json',{'criteria':[self.rubric['criteria'][1]]})
        self.parent['rubric_sha256']=self.sha(self.d/'rubric.json');self.rewrite_parent_binding()
        self.assertIn('parent-rubric-omits-participant-stage',self.check()['errors'])
    def test_renamed_scoped_receipt_does_not_become_whole_run(self):
        self.child.pop('parent_trial');self.child['artifact_hashes']=self.artifacts.copy()
        self.write('trial/graded.json',self.child)
        checked=validate_receipt_file(self.root,'trial/graded.json','S01')
        self.assertIn('whole-trial-rubric-omits-participant-stage',checked['errors'])

if __name__=='__main__':unittest.main()
