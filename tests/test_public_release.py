"""Skill installation and serving a graph file that is not in the registry."""
import json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
from theorygraph import graph as m

ROOT=Path(__file__).resolve().parents[1]


class SkillInstall(unittest.TestCase):
    def test_install_copies_bundled_skill_and_refuses_to_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            m.install_skill(d); target=Path(d)/'theory'/'SKILL.md'
            self.assertEqual(target.read_text(),(m.HERE/'skill'/'SKILL.md').read_text())
            m.install_skill(d)  # identical content: reinstall is a no-op
            target.write_text('local edits')
            with self.assertRaises(m.GraphError): m.install_skill(d)
            m.install_skill(d,force=True)
            self.assertIn('name: theory',target.read_text())


class ServeUnregisteredFile(unittest.TestCase):
    def test_file_argument_is_what_the_viewer_gets(self):
        with tempfile.TemporaryDirectory() as d:
            other=Path(d)/'other'/'graph.json'; mine=Path(d)/'mine'/'graph.json'
            env={**os.environ,'TG_REGISTRY':str(Path(d)/'projects.json')}
            run=lambda *a:subprocess.run([sys.executable,'-m','theorygraph',*a],cwd=ROOT,env=env,check=True,capture_output=True)
            run('new','other','--dir',str(other.parent))  # registered and default
            run('new','mine','--dir',str(mine.parent),'--no-register')
            run('--file',str(mine),'entity','add','marker','Only in mine.','--reason','Mark this graph')
            with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
            server=subprocess.Popen([sys.executable,'-m','theorygraph','--file',str(mine),'serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
            try:
                get=lambda path:json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=2).read())
                for _ in range(50):
                    try: catalog=get('/api/projects'); break
                    except OSError: time.sleep(0.1)
                self.assertEqual(catalog['default'],'mine'); self.assertEqual(catalog['served'],'mine')
                self.assertTrue(catalog['projects'][0]['unregistered'])
                self.assertIn('marker',get('/api/graph?project=mine')['nodes'])
                self.assertNotIn('marker',get('/api/graph?project=other')['nodes'])
            finally: server.terminate(); server.wait()


if __name__=='__main__': unittest.main()
