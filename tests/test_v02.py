"""v0.2 contract tests on isolated graphs and local Git remotes. No agent trial claims."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from theorygraph import graph, projects, writes

ROOT = Path(__file__).resolve().parents[1]
TG = ROOT / 'tg'


class TypedWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.path = self.root / 'graph.json'
        self.registry = self.root / 'registry.json'
        self.env = {**os.environ, 'TG_REGISTRY': str(self.registry), 'TG_ACTOR': 'test-agent'}
        self.path.write_bytes((ROOT / 'theorygraph/template.json').read_bytes())
        self.cli('entity', 'add', 'subject', 'Subject', '--alias', 'Subject alias')
        self.cli('operation', 'add', 'act', 'Act')
        self.cli('source', 'add', 'src', 'Exact user words.', '--kind', 'verbatim', '--author', 'User')
        self.cli('question', 'add', 'q', 'When?', '--about', 'subject')
        self.cli('claim', 'add', 'old', 'Original rule.', '--about', 'subject', '--governs', 'act', '--status', 'accepted', '--answers', 'q')

    def cli(self, *args, reason='Test ruling', ok=True):
        cmd = [sys.executable, str(TG), '--file', str(self.path), *args]
        if reason is not None: cmd += ['--reason', reason]
        r = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def load(self): return graph.load(self.path)

    def test_declared_answer_is_authoritative_everywhere(self):
        g = self.load(); g['nodes']['q']['meta'].update(answer_shape='condition', required_parts=['when'])
        self.path.write_text(json.dumps(g))
        self.assertEqual(graph.check(g)['findings'], [])
        self.assertEqual(graph.questions(g)['question_states']['q'], 'answered')
        self.assertEqual(graph.frontier(g)['open_questions'], [])
        self.assertEqual(graph.frontier(g)['answered_questions'][0]['resolution'], 'answered')
        read = json.loads(self.cli('readiness', 'q', '--json', reason=None).stdout)
        self.assertEqual(read['resolution'], 'answered')
        self.assertEqual(read['answer_advice']['message'], 'no current accepted full answer edge')
        for command in ('questions', 'frontier', 'check'):
            data = self.cli(command, '--json', reason=None).stdout
            self.assertNotIn('answer_advice', data)
            self.assertNotIn('candidate-answer', data)

    def test_optional_answer_metadata_is_unvalidated(self):
        for value in (None, 'plain text', 7, [], {'unexpected': ['anything']}):
            with self.subTest(value=value):
                g = self.load()
                g['nodes']['q']['meta'].update(answer_shape=value, required_parts=value)
                g['nodes']['old']['answer'] = value
                g['edges']['old-answers-q']['answer'] = value
                graph.validate(g)
                self.path.write_text(json.dumps(g))
                self.cli('readiness', 'q', reason=None)
                self.assertEqual(graph.questions(g)['question_states']['q'], 'answered')

    def test_ruling_one_revision_and_exact_history(self):
        before = self.load()
        r = self.cli('claim', 'add', 'new', 'Replacement rule.', '--status', 'accepted',
                     '--governs', 'act', '--about', 'subject', '--source', 'src',
                     '--kind', 'paraphrase', '--author', 'Author', '--title', 'New title',
                     '--revises', 'old', '--withdraw-old', '--raises', 'q', '--supports', 'old')
        after = self.load()
        self.assertEqual(r.stdout, f'r{before["revision"] + 1} · added claim new\n')
        self.assertEqual(after['revision'], before['revision'] + 1)
        self.assertEqual(after['changes'][:-1], before['changes'])
        self.assertEqual(after['nodes']['old']['status'], 'withdrawn')
        self.assertEqual(after['nodes']['old']['meta']['superseded_by'], 'new')
        self.assertEqual(after['edges']['old-answers-q']['from'], 'new')
        self.assertEqual(after['edges']['old-answers-q']['coverage'], 'full')
        self.assertEqual(after['nodes']['new']['meta']['review_state'], 'current')
        self.assertEqual(after['nodes']['new']['meta']['author'], 'Author')
        self.assertEqual(after['changes'][-1]['actor'], 'test-agent')
        replay = copy.deepcopy(before)
        for edit in after['changes'][-1]['edits']:
            self.assertEqual(replay[edit['collection']].get(edit['id']), edit['before'])
            replay[edit['collection']][edit['id']] = edit['after']
        self.assertEqual(replay['nodes'], after['nodes']); self.assertEqual(replay['edges'], after['edges'])

    def test_replacement_preserves_partial_payload_and_declared_status(self):
        g = self.load(); g['edges']['old-answers-q'].update(coverage='partial', answer={'anything': 1}, covers=['part'])
        self.path.write_text(json.dumps(g))
        self.cli('claim', 'add', 'new', 'New', '--about', 'subject', '--revises', 'old', '--withdraw-old')
        after = self.load()
        self.assertEqual(after['edges']['old-answers-q'], {**g['edges']['old-answers-q'], 'from': 'new'})
        self.assertEqual(after['nodes']['q']['status'], 'answered')

    def test_all_typed_dry_runs_have_no_side_effects(self):
        commands = [
            ('claim', 'add', 'new', 'Text', '--about', 'subject'),
            ('question', 'add', 'new', 'Question?', '--about', 'subject', '--raised-by', 'old'),
            ('entity', 'add', 'new', 'Entity', '--alias', 'one', 'two'),
            ('operation', 'add', 'new', 'Operation'),
            ('source', 'add', 'new', 'Source', '--kind', 'paraphrase'),
            ('withdraw', 'old'), ('answer', 'q', '--with', 'old', '--coverage', 'partial'),
            ('edge', 'add', 'old', 'challenges', 'subject'), ('set', 'old', '--text', 'Revised'),
            ('set', 'q', '--status', 'open'), ('reviewed', 'old')]
        before = self.path.read_bytes()
        for command in commands:
            with self.subTest(command=command):
                result = json.loads(self.cli(*command, '--dry-run', '--json').stdout)
                self.assertTrue(result['dry_run']); self.assertFalse(result['written'])
                self.assertEqual(self.path.read_bytes(), before)
                self.assertIn('newly_needs_review', result)

    def test_errors_are_atomic_and_name_unknown_id(self):
        commands = [
            ('claim', 'add', 'new', 'Text', '--about', 'missing'),
            ('claim', 'add', 'new', 'Text', '--about', 'subject', '--source', 'missing'),
            ('claim', 'add', 'new', 'Text', '--about', 'subject', '--revises', 'missing'),
            ('question', 'add', 'new', 'Text', '--about', 'subject', '--raised-by', 'missing'),
            ('withdraw', 'old', '--superseded-by', 'missing'),
            ('answer', 'q', '--with', 'missing'), ('edge', 'add', 'old', 'about', 'missing'),
            ('set', 'missing', '--text', 'Text')]
        before = self.path.read_bytes()
        for command in commands:
            with self.subTest(command=command):
                self.assertIn('missing', self.cli(*command, ok=False).stderr)
                self.assertEqual(self.path.read_bytes(), before)
        self.cli('claim', 'add', 'new', 'Text', ok=False)
        self.cli('question', 'add', 'new', 'Text', ok=False)
        self.cli('claim', 'add', 'new', 'Text', '--about', 'subject', '--withdraw-old', ok=False)
        self.cli('set', 'old', '--status', 'nonsense', ok=False)
        self.cli('edge', 'add', 'old', 'unknown-relation', 'q', ok=False)
        self.cli('entity', 'add', 'new', 'Text', reason=None, ok=False)
        self.cli('edge', 'add', 'old', 'supports', 'old', reason=None, ok=False)
        self.assertEqual(self.path.read_bytes(), before)

    def test_question_raised_by_and_answer_commands(self):
        self.cli('question', 'add', 'q2', 'Other?', '--about', 'subject', '--raised-by', 'old')
        self.cli('answer', 'q2', '--with', 'old', '--coverage', 'partial')
        self.assertEqual(self.load()['nodes']['q2']['status'], 'open')
        self.cli('answer', 'q2', '--with', 'old')
        self.assertEqual(self.load()['nodes']['q2']['status'], 'answered')
        self.cli('set', 'q2', '--status', 'open')
        self.cli('claim', 'add', 'proposed', 'Maybe', '--about', 'subject', '--answers', 'q2')
        self.assertEqual(self.load()['nodes']['q2']['status'], 'open')
        self.cli('withdraw', 'old', '--superseded-by', 'proposed')
        self.assertEqual(self.load()['nodes']['old']['meta']['superseded_by'], 'proposed')

    def test_only_new_conflict_edges_flag_both_endpoints(self):
        self.cli('set', 'old', '--text', 'Edited')
        self.assertEqual(graph.review(self.load())['nodes'], {})
        self.cli('edge', 'add', 'old', 'potential-conflict', 'subject')
        self.assertEqual(set(graph.review(self.load())['nodes']), {'old', 'subject'})
        self.cli('reviewed', 'old', 'subject')
        self.cli('set', 'old', '--text', 'Edited again')
        self.assertEqual(graph.review(self.load())['nodes'], {})
        self.cli('edge', 'add', 'old', 'challenges', 'subject')
        self.assertEqual(set(graph.review(self.load())['nodes']), {'old', 'subject'})
        self.cli('reviewed', 'old', 'subject')
        self.cli('edge', 'add', 'old', 'supports', 'subject')
        self.assertEqual(graph.review(self.load())['nodes'], {})

    def test_conflicts_on_new_nodes_and_no_transitive_flag(self):
        g = self.load()
        ops = [{'op':'add','collection':'nodes','id':'new','value':{'type':'claim','text':'New','status':'proposed','meta':{'review_state':'current'}}},
               {'op':'add','collection':'edges','id':'dep','value':{'from':'q','to':'old','type':'depends-on'}},
               {'op':'add','collection':'edges','id':'conflict','value':{'from':'new','to':'old','type':'challenges'}}]
        after, edits = graph.simulate(g, ops, 'agent', 'Review hypothesis')
        self.assertEqual(set(graph.review(after)['nodes']), {'old','new'})
        self.assertEqual([e['automatic'] for e in edits if 'automatic' in e], ['conflict-review','conflict-review'])

    def test_actor_defaults_overrides_and_multiple_anchors(self):
        self.env.pop('TG_ACTOR')
        self.cli('claim','add','new','Text','--about','subject','act','--governs','act','--actor','explicit')
        self.assertEqual(self.load()['changes'][-1]['actor'],'explicit')
        self.cli('set','new','--text','Revised')
        self.assertEqual(self.load()['changes'][-1]['actor'],'assistant')
        edges=self.load()['edges'].values()
        self.assertEqual(sum(e['from']=='new' and e['type']=='about' for e in edges),2)
        self.assertEqual(self.load()['nodes']['new']['meta']['source_kind'],'assistant-proposal')

    def test_automatic_expect_prevents_overwrite(self):
        from argparse import Namespace
        a = Namespace(cmd='set', id='old', text='new', status=None, actor='test', reason='race', dry_run=False)
        original_apply = graph.apply
        def race(path, ops, actor, reason, expected):
            original_apply(path, [{'op':'update','collection':'nodes','id':'old','value':{'text':'concurrent'}}], 'other', 'concurrent')
            return original_apply(path, ops, actor, reason, expected)
        with patch.object(graph, 'apply', side_effect=race):
            with self.assertRaisesRegex(graph.GraphError, 'Revision conflict'):
                writes.execute(self.path, a)
        self.assertEqual(self.load()['nodes']['old']['text'], 'concurrent')

    def test_quiet_reads_full_metadata_and_legacy_fields(self):
        g = self.load(); g['nodes']['old']['semantic_version'] = 9
        g['nodes']['old']['meta'].update(legacy_status='user-stated', long_note='Retained detail')
        self.path.write_text(json.dumps(g))
        for command in (('node','old'), ('questions',), ('frontier',), ('review','subject')):
            output = self.cli(*command, reason=None).stdout
            self.assertEqual(output.count('Revision '), 1)
            for noise in ('metadata_omitted','metadata_access','truncated=False','semantic_version','legacy_status'):
                self.assertNotIn(noise, output)
        compact = self.cli('node','old','--json',reason=None).stdout
        full = self.cli('node','old','--full','--json',reason=None).stdout
        self.assertNotIn('Retained detail', compact); self.assertIn('Retained detail', full)
        self.assertNotIn('semantic_version', full); self.assertNotIn('legacy_status', full)
        self.assertEqual(self.load()['nodes']['old']['semantic_version'], 9)
        # Metadata names are not reserved node identities.
        g['nodes']['semantic_version']={'type':'entity','status':'defined','text':'A legitimate identity'}
        self.assertIn('semantic_version',graph.public_read(g)['nodes'])


class Autosync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.remote = self.root/'remote.git'; self.repo = self.root/'repo'
        self.env = {**os.environ, 'TG_REGISTRY':str(self.root/'registry.json'),
                    'GIT_AUTHOR_NAME':'test', 'GIT_AUTHOR_EMAIL':'test@example.invalid',
                    'GIT_COMMITTER_NAME':'test', 'GIT_COMMITTER_EMAIL':'test@example.invalid'}
        self.git(self.root,'init','--bare',str(self.remote))
        self.git(self.root,'clone',str(self.remote),str(self.repo))
        self.path=self.repo/'graph.json'; self.path.write_bytes((ROOT/'theorygraph/template.json').read_bytes())
        (self.repo/'.gitignore').write_text('*.lock\n')
        self.git(self.repo,'add','graph.json','.gitignore'); self.git(self.repo,'commit','-m','initial')
        self.git(self.repo,'push','-u','origin','HEAD')
        self.cli('register','demo',str(self.path)); self.cli('register','other',str(self.path))

    def git(self, cwd, *args):
        r=subprocess.run(['git','-C',str(cwd),*args],capture_output=True,text=True,env=self.env)
        self.assertEqual(r.returncode,0,r.stderr); return r.stdout.strip()

    def cli(self,*args,ok=True):
        r=subprocess.run([sys.executable,str(TG),*args],capture_output=True,text=True,env=self.env)
        self.assertEqual(r.returncode==0,ok,r.stderr); return r

    def test_default_off_per_project_and_every_write_path(self):
        self.cli('-p','demo','entity','add','a','A','--reason','local')
        self.assertEqual(self.git(self.remote,'log','-1','--format=%s'),'initial')
        self.cli('-p','demo','config','autosync','on')
        reg=json.loads((self.root/'registry.json').read_text())
        self.assertTrue(reg['settings']['demo']['autosync']); self.assertNotIn('other',reg['settings'])
        unrelated=self.repo/'unrelated.txt'; unrelated.write_text('unrelated')
        result=self.cli('-p','demo','set','a','--text','Changed','--reason','typed ruling')
        self.assertEqual(len(result.stdout.splitlines()),1); self.assertIn('synced',result.stdout)
        self.assertEqual(self.git(self.remote,'log','-1','--format=%s'),'typed ruling')
        self.assertEqual(self.git(self.repo,'ls-files','unrelated.txt'),'')
        self.assertEqual(unrelated.read_text(),'unrelated')
        self.cli('-p','demo','reviewed','a','--reason','review acknowledgement')
        self.assertEqual(self.git(self.remote,'log','-1','--format=%s'),'review acknowledgement')
        ops=self.root/'ops.json'; ops.write_text(json.dumps([{'op':'update','collection':'nodes','id':'a','value':{'text':'Applied'}}]))
        self.cli('-p','demo','apply',str(ops),'--reason','batch ruling')
        self.assertEqual(self.git(self.remote,'log','-1','--format=%s'),'batch ruling')
        before=self.path.read_bytes(); head=self.git(self.remote,'rev-parse','HEAD')
        self.cli('-p','demo','set','a','--text','Dry','--reason','not written','--dry-run')
        self.assertEqual(before,self.path.read_bytes());self.assertEqual(head,self.git(self.remote,'rev-parse','HEAD'))
        self.cli('-p','demo','config','autosync','off')
        self.cli('-p','demo','set','a','--text','Local','--reason','disabled')
        self.assertEqual(head,self.git(self.remote,'rev-parse','HEAD'))

    def test_saved_evaluation_syncs_and_requires_reason(self):
        self.cli('-p','demo','config','autosync','on')
        self.cli('-p','demo','entity','add','a','A','--reason','subject')
        self.cli('-p','demo','claim','add','c','C','--about','a','--reason','claim')
        ops=self.root/'trace.json';ops.write_text(json.dumps([{'op':'add','collection':'nodes','id':'t','value':{'type':'trace','status':'recorded','text':'Synthetic','trace':{'events':[]}}}]))
        self.cli('-p','demo','apply',str(ops),'--reason','trace')
        before=self.path.read_bytes()
        self.cli('-p','demo','evaluate','c','t','--save','result',ok=False)
        self.assertEqual(self.path.read_bytes(),before)
        r=self.cli('-p','demo','evaluate','c','t','--save','result','--reason','save evidence')
        self.assertEqual(len(r.stdout.splitlines()),1)
        self.assertEqual(self.git(self.remote,'log','-1','--format=%s'),'save evidence')
        self.assertEqual(graph.load(self.path)['nodes']['result']['result']['outcome'],'not-checked')

    def test_unrelated_staged_work_is_never_committed(self):
        self.cli('-p','demo','config','autosync','on')
        (self.repo/'unrelated.txt').write_text('Keep staged')
        self.git(self.repo,'add','unrelated.txt')
        r=self.cli('-p','demo','entity','add','a','A','--reason','local ruling',ok=False)
        self.assertIn('saved locally',r.stderr)
        self.assertEqual(self.git(self.repo,'diff','--cached','--name-only'),'unrelated.txt')
        self.assertEqual(self.git(self.repo,'show','--pretty=','--name-only','HEAD'),'graph.json')

    def test_conflict_keeps_local_write_and_reports_file(self):
        self.cli('-p','demo','config','autosync','on')
        other=self.root/'other'; self.git(self.root,'clone',str(self.remote),str(other))
        remote=json.loads((other/'graph.json').read_text());remote['revision']=99
        (other/'graph.json').write_text(json.dumps(remote));self.git(other,'commit','-am','remote change');self.git(other,'push')
        remote_head=self.git(self.remote,'rev-parse','HEAD')
        r=self.cli('-p','demo','entity','add','a','Local','--reason','local change',ok=False)
        self.assertIn('saved locally',r.stderr); self.assertIn('Conflicting files: graph.json',r.stderr)
        self.assertIn('a',graph.load(self.path)['nodes'])
        self.assertEqual(self.git(self.repo,'log','-1','--format=%s'),'local change')
        self.assertEqual(self.git(self.remote,'rev-parse','HEAD'),remote_head)
        self.assertFalse((self.repo/'.git/rebase-merge').exists())
