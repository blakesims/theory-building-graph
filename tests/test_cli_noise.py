"""Noise reduction for the agent-facing CLI: check presentation, evidence filtering,
fingerprint tolerance for review commentary, dry runs, reviewed, frontier, where, sync."""
import copy, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from theorygraph import graph as g, dependency as d, tracecheck, projects
from tests.test_dependency import fixture, edge

ROOT=Path(__file__).resolve().parents[1]; TG=str(ROOT/'tg')

def run(*args, cwd=None):
    r=subprocess.run([sys.executable,TG,*args],capture_output=True,text=True,cwd=cwd)
    return r.returncode,r.stdout,r.stderr

def with_trace(model):
    model['nodes']['T']={'type':'trace','status':'recorded','text':'synthetic trace','meta':{'synthetic':True,'review_state':'needs-review'},'trace':{'complete':True,'events':[]}}
    edge(model,'T','A','about');return model


class CheckPresentation(unittest.TestCase):
    def test_informational_counted_review_listed(self):
        model=fixture(['A','B']);full=g.check(model)
        self.assertIn('untested-claim',full['counts']);self.assertIn('unanchored-claim',full['counts'])
        view=g.check_view(full)
        self.assertTrue(all(f['severity']!='informational' for f in view['findings']))
        self.assertEqual(view['informational_counts'],{'untested-claim':2})
        self.assertEqual(g.check_view(full,True),full)
        text=g.compact(view);self.assertIn('2 untested-claim (informational; --all to list)',text);self.assertIn('unanchored-claim',text)
    def test_cli_all_flag(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'graph.json';p.write_text(json.dumps(fixture(['A'])))
            code,out,_=run('--file',str(p),'--json','check');data=json.loads(out)
            self.assertEqual(code,0);self.assertEqual(data['informational_counts'],{'untested-claim':1});self.assertEqual([f['code'] for f in data['findings']],['unanchored-claim'])
            code,out,_=run('--file',str(p),'check','--all','--json');data=json.loads(out)
            self.assertNotIn('informational_counts',data);self.assertEqual(sorted(f['code'] for f in data['findings']),['unanchored-claim','untested-claim'])


class EvidenceFiltering(unittest.TestCase):
    def setUp(self):self.model=with_trace(fixture(['A','B']))
    def test_overview_search_walk_review_hide_evidence(self):
        o=g.overview(self.model);self.assertEqual(o['nodes'],2);self.assertEqual(o['evidence'],{'trace':1});self.assertNotIn('trace',o['node_types'])
        self.assertEqual(g.overview(self.model,evidence=True)['nodes'],3)
        self.assertEqual(g.search(self.model,'synthetic')['total'],0);self.assertEqual(g.search(self.model,'synthetic',evidence=True)['total'],1)
        self.assertNotIn('T',g.walk(self.model,'A')['nodes']);self.assertIn('T',g.walk(self.model,'A',evidence=True)['nodes'])
        self.assertEqual(set(g.walk(self.model,'T')['nodes']),{'T','A'})  # evidence root stays readable
        self.assertEqual(g.review(self.model)['total'],0);self.assertEqual(g.review(self.model,evidence=True)['total'],1)
        self.assertNotIn('T',g.review(self.model,'A')['nodes']);self.assertIn('T',g.review(self.model,'A',evidence=True)['nodes'])
    def test_declaration_overrides_legacy_names(self):
        m=copy.deepcopy(self.model);m['node_types']['trace']['evidence']=False;m['node_types']['claim']['evidence']=True
        self.assertFalse(g.is_evidence(m,m['nodes']['T']));self.assertTrue(g.is_evidence(m,m['nodes']['A']))
        self.assertEqual(g.overview(m)['evidence'],{'claim':2})
    def test_node_and_evidence_cli(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'graph.json';p.write_text(json.dumps(self.model))
            code,out,_=run('--file',str(p),'--json','node','T');self.assertEqual(code,0);self.assertIn('T',json.loads(out)['nodes'])
            code,out,_=run('--file',str(p),'--json','overview');self.assertEqual(json.loads(out)['evidence'],{'trace':1})
            code,out,_=run('--file',str(p),'overview','--evidence','--json');self.assertEqual(json.loads(out)['node_types'].get('trace'),1)


class FingerprintTolerance(unittest.TestCase):
    def test_review_note_keeps_result_current_text_change_stales(self):
        from tests.test_tracecheck import TraceChecks
        case=TraceChecks();case.setUp();model=case.g;receipt=tracecheck.evaluate(model,'c','t')
        self.assertEqual(tracecheck.result_state(model,receipt),'current')
        noted=copy.deepcopy(model)
        for field in ('review_note','review_result','review','note','notes','review_reason'):noted['nodes']['c'].setdefault('meta',{})[field]='commentary '+field
        self.assertEqual(tracecheck.result_state(noted,receipt),'current')
        changed=copy.deepcopy(model);changed['nodes']['c']['text']+=' changed';self.assertEqual(tracecheck.result_state(changed,receipt),'stale')
        meta_changed=copy.deepcopy(model);meta_changed['nodes']['c'].setdefault('meta',{})['modality']='must';self.assertEqual(tracecheck.result_state(meta_changed,receipt),'stale')


class DryRun(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'graph.json'
        model=fixture(['A','B','Q']);edge(model,'A','B');model['nodes']['A']['meta']={'review_state':'current'};self.model=model
        self.path.write_text(json.dumps(model));self.before=self.path.read_bytes()
    def tearDown(self):self.tmp.cleanup()
    def test_effects_without_writing(self):
        ops=[{'op':'update','collection':'nodes','id':'B','value':{'text':'B revised'}},
             {'op':'add','collection':'nodes','id':'N','value':{'type':'claim','text':'new','status':'accepted'}},
             {'op':'add','collection':'edges','id':'N-answers-Q','value':{'from':'N','to':'Q','type':'answers','coverage':'full'}}]
        r=g.dry_run(self.path,ops,'test','probe',0)
        self.assertTrue(r['dry_run']);self.assertFalse(r['written']);self.assertEqual((r['revision_before'],r['revision_after']),(0,1))
        self.assertEqual(self.path.read_bytes(),self.before);self.assertFalse((Path(self.tmp.name)/'graph.json.lock').exists())
        flagged={n['id']:n['review_reason'] for n in r['newly_needs_review']}
        self.assertEqual(set(flagged),{'A','B','Q'});self.assertIn('B',flagged['A']);self.assertIn('N-answers-Q',flagged['Q'])
        self.assertIn({'id':'Q','before':'open','after':'answered'},r['question_resolution_changed'])
        self.assertIn('unanchored-claim',{f['code'] for f in r['findings_added'] if 'N' in f['nodes']})
        self.assertIn('unconnected-question',{f['code'] for f in r['findings_removed']})
        self.assertEqual([e['action'] for e in r['edits'][:3]],['update','add','add'])
        text=g.compact(r);self.assertIn('DRY RUN',text);self.assertIn('nothing written',text)
    def test_expect_and_validation_errors(self):
        with self.assertRaises(g.GraphError):g.dry_run(self.path,[{'op':'update','collection':'nodes','id':'B','value':{'text':'x'}}],'test','probe',5)
        with self.assertRaises(g.GraphError):g.dry_run(self.path,[{'op':'add','collection':'edges','id':'bad','value':{'from':'A','to':'nope','type':'about'}}],'test','probe')
        self.assertEqual(self.path.read_bytes(),self.before)
    def test_cli_dry_run_then_apply(self):
        ops=Path(self.tmp.name)/'ops.json';ops.write_text(json.dumps([{'op':'update','collection':'nodes','id':'B','value':{'text':'B revised'}}]))
        code,out,_=run('--file',str(self.path),'apply',str(ops),'--actor','t','--reason','r','--dry-run','--json');data=json.loads(out)
        self.assertEqual(code,0);self.assertTrue(data['dry_run']);self.assertEqual(self.path.read_bytes(),self.before)
        code,out,_=run('--file',str(self.path),'apply',str(ops),'--actor','t','--reason','r','--json');self.assertEqual(code,0);self.assertEqual(json.loads(out)['revision'],1)
        self.assertEqual(g.load(self.path)['revision'],1)
    def test_evidence_becoming_stale(self):
        from tests.test_tracecheck import TraceChecks
        case=TraceChecks();case.setUp();model=case.g;model['nodes']['c'].setdefault('meta',{})
        p=Path(self.tmp.name)/'trace.json';p.write_text(json.dumps(model));result=tracecheck.evaluate(model,'c','t');g.save_evaluation(p,model,result,'receipt')
        stale=g.dry_run(p,[{'op':'update','collection':'nodes','id':'c','value':{'text':model['nodes']['c']['text']+' changed'}}],'t','r')['evidence_becoming_stale']
        self.assertEqual(stale,['receipt'])
        fresh=g.dry_run(p,[{'op':'update','collection':'nodes','id':'c','value':{'meta':{'review_note':'commentary'}}}],'t','r')['evidence_becoming_stale']
        self.assertEqual(fresh,[])


class Reviewed(unittest.TestCase):
    def test_marks_current_through_audit(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'graph.json';model=fixture(['A','B']);edge(model,'A','B')
            model['nodes']['A']['meta']={'review_state':'needs-review','review_reason':'premise changed'};p.write_text(json.dumps(model))
            with self.assertRaises(g.GraphError):g.reviewed(p,['A','missing'],'looked')
            self.assertEqual(g.load(p)['revision'],0)
            r=g.reviewed(p,['A','A'],'looked at B; A still holds',actor='reviewer',expected=0)
            self.assertEqual(r['reviewed'],['A']);after=g.load(p)
            self.assertEqual(after['revision'],1);self.assertEqual(d.currency(after['nodes']['A']),'current')
            self.assertEqual(after['nodes']['A']['meta']['review_reason'],'looked at B; A still holds');self.assertIn('reviewed_inputs',after['nodes']['A']['meta'])
            self.assertEqual(after['changes'][-1]['actor'],'reviewer')
            code,out,_=run('--file',str(p),'reviewed','A','--reason','again','--json');self.assertEqual(code,0);self.assertEqual(json.loads(out)['revision'],2)
            code,_,err=run('--file',str(p),'reviewed','nope','--reason','x');self.assertEqual(code,1);self.assertIn('Unknown node',err)


class Frontier(unittest.TestCase):
    def test_sections_and_exclusions(self):
        model=with_trace(fixture(['A','B','Q']));model['nodes']['B'].update(status='proposed');model['nodes']['A']['meta']={'review_state':'needs-review','review_reason':'x'}
        model['nodes']['H']={'type':'claim','text':'old','status':'proposed','meta':{'review_state':'historical'}}
        model['changes']=[{'revision':i,'actor':'a','reason':f'r{i}','edits':[]} for i in range(1,8)];model['revision']=7
        f=g.frontier(model)
        self.assertEqual(f['counts']['open_questions'],1);self.assertEqual(f['open_questions'][0]['id'],'Q');self.assertEqual(f['open_questions'][0]['resolution'],'open')
        self.assertEqual([n['id'] for n in f['needs_review']],['A'])  # T (evidence) excluded
        self.assertEqual([n['id'] for n in f['proposed_claims']],['B'])  # H (historical) excluded
        self.assertTrue(all(x['code']!='untested-claim' for x in f['findings']));self.assertIn('unanchored-claim',{x['code'] for x in f['findings']})
        self.assertEqual([c['revision'] for c in f['recent_changes']],[3,4,5,6,7]);self.assertEqual(f['evidence_stale'],0)
        text=g.compact(f);self.assertIn('frontier:',text);self.assertIn('open questions',text);self.assertIn('Q [open; no-dependencies]',text)
    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'graph.json';p.write_text(json.dumps(fixture(['A','Q'])))
            code,out,_=run('--file',str(p),'--json','frontier');data=json.loads(out);self.assertEqual(code,0);self.assertEqual(data['counts']['open_questions'],1)
            code,out,_=run('--file',str(p),'frontier');self.assertEqual(code,0);self.assertIn('frontier:',out)


class Where(unittest.TestCase):
    def test_reports_selection(self):
        with tempfile.TemporaryDirectory() as t:
            reg=Path(t)/'registry.json';old=projects.REGISTRY;projects.REGISTRY=reg
            try:
                p=Path(t)/'graph.json';p.write_text(json.dumps(fixture(['A'])))
                w=projects.where(p,'file');self.assertEqual(w['selected_by'],'file');self.assertIsNone(w['project']);self.assertEqual(w['engine'],str(ROOT));self.assertEqual(w['registry'],str(reg))
                projects.register('demo',p);self.assertEqual(projects.where(p,'file')['project'],'demo');self.assertEqual(projects.where(p,'project','demo')['project'],'demo')
                env={**os.environ,'TG_REGISTRY':str(reg)};r=subprocess.run([sys.executable,TG,'--file',str(p),'where','--json'],capture_output=True,text=True,env=env)
                self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['graph'],str(p.resolve()))
            finally:projects.REGISTRY=old


class Sync(unittest.TestCase):
    def git(self,cwd,*args):
        r=subprocess.run(['git','-C',str(cwd),*args],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);return r.stdout.strip()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();t=Path(self.tmp.name);self.bare=t/'remote.git';self.git(t,'init','-q','--bare',str(self.bare))
        self.env={**os.environ,'GIT_AUTHOR_NAME':'t','GIT_AUTHOR_EMAIL':'t@x','GIT_COMMITTER_NAME':'t','GIT_COMMITTER_EMAIL':'t@x'};os.environ.update({k:v for k,v in self.env.items() if k.startswith('GIT_')})
        self.a=t/'a';self.git(t,'clone','-q',str(self.bare),str(self.a));self.git(self.a,'config','user.email','t@x');self.git(self.a,'config','user.name','t')
        self.graph=self.a/'theory'/'graph.json';self.graph.parent.mkdir();self.graph.write_text(json.dumps(fixture(['A'])))
        self.git(self.a,'add','.');self.git(self.a,'commit','-q','-m','init');self.git(self.a,'push','-q','-u','origin','HEAD')
    def tearDown(self):self.tmp.cleanup()
    def test_commit_message_from_audit_and_push(self):
        g.apply(self.graph,[{'op':'update','collection':'nodes','id':'A','value':{'text':'A2'}}],'agent','Recorded the decision')
        r=projects.sync(self.graph);self.assertEqual(r['message'],'Recorded the decision');self.assertIsNotNone(r['committed'])
        self.assertEqual(self.git(self.bare,'log','-1','--format=%s'),'Recorded the decision')
        self.assertEqual(self.git(self.a,'status','--porcelain','--untracked-files=no'),'')  # only the gitignored-in-practice lock file is untracked
        again=projects.sync(self.graph,'unused');self.assertIsNone(again['committed'])
    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'graph.json';p.write_text(json.dumps(fixture(['A'])))
            with self.assertRaises(projects.ProjectError):projects.sync(p)
            code,_,err=run('--file',str(p),'sync');self.assertEqual(code,1);self.assertIn('not inside a git repository',err)
    def test_conflict_aborts_rebase(self):
        b=Path(self.tmp.name)/'b';self.git(Path(self.tmp.name),'clone','-q',str(self.bare),str(b));self.git(b,'config','user.email','t@x');self.git(b,'config','user.name','t')
        g.apply(b/'theory'/'graph.json',[{'op':'update','collection':'nodes','id':'A','value':{'text':'from b'}}],'agent','b edit');self.git(b,'commit','-q','-am','b edit');self.git(b,'push','-q')
        g.apply(self.graph,[{'op':'update','collection':'nodes','id':'A','value':{'text':'from a'}}],'agent','a edit');self.git(self.a,'commit','-q','-am','a edit')
        with self.assertRaises(projects.ProjectError) as ctx:projects.sync(self.graph)
        self.assertIn('theory/graph.json',str(ctx.exception));self.assertFalse((self.a/'.git'/'rebase-merge').exists());self.assertFalse((self.a/'.git'/'rebase-apply').exists())
        self.assertEqual(self.git(self.a,'log','-1','--format=%s'),'a edit')


if __name__=='__main__':unittest.main()
