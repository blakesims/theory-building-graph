"""Read the existing engine and evaluate TEMPORARY fixture copies only."""
import argparse,json,subprocess,tempfile,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path(__file__).resolve().parent.parent);a=p.parse_args();engine=a.engine.resolve();original=engine/'projects'/'morphisms'/'graph.json';raw=original.read_bytes()
with tempfile.TemporaryDirectory() as d:
 graph=Path(d)/'graph.json';graph.write_bytes(raw)
 def run(*args):
  r=subprocess.run(['python3',str(engine/'tg'),'--file',str(graph),'--json',*args],text=True,capture_output=True)
  assert r.returncode==0,r.stderr
  return json.loads(r.stdout)
 claim='steward-chooses-next-work'
 outcomes={}
 for fixture,expected in [('fixture-steward-next','satisfies'),('fixture-orchestrator-next','violates'),('fixture-missing-role','insufficient-information')]:
  result=run('evaluate',claim,fixture);assert result['outcome']==expected;outcomes[fixture]=result['outcome']
  if expected=='violates':assert result['witnesses'][0]['event']=='choose1'
 assert run('evaluate','steward-planning','fixture-steward-next')['outcome']=='not-checked'
 g=json.loads(graph.read_text());g['nodes'][claim]['pattern']['allowed_role']='orchestrator-role';graph.write_text(json.dumps(g))
 assert run('evaluate',claim,'fixture-steward-next')['outcome']=='violates'
 assert run('evaluate',claim,'fixture-orchestrator-next')['outcome']=='satisfies'
 g['nodes'][claim]['pattern']['allowed_role']='steward-role';del g['nodes']['fixture-steward-next']['trace']['events'][1]['after'];graph.write_text(json.dumps(g))
 assert run('evaluate',claim,'fixture-steward-next')['outcome']=='insufficient-information'
assert original.read_bytes()==raw,'Live graph unexpectedly changed'
print(json.dumps({'baseline':'passed','scope':'7 current-checker outcome assertions; not80-case compliance','graph_revision':json.loads(raw)['revision'],'engine_sha256':hashlib.sha256((engine/'theorygraph'/'graph.py').read_bytes()).hexdigest(),'outcomes':outcomes,'live_graph_unchanged':True},indent=2))
