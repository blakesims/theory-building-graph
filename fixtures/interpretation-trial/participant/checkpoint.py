"""Run the actual replay engine in save/resume modes, in separate processes."""
import argparse,json
from pathlib import Path
import replay
p=argparse.ArgumentParser();p.add_argument('mode',choices=['save','resume']);p.add_argument('fixture');p.add_argument('checkpoint');a=p.parse_args();f=json.loads(Path(a.fixture).read_text())
r=replay.run(f['model'],f['events'] if a.mode=='save' else [],checkpoint=json.loads(Path(a.checkpoint).read_text()) if a.mode=='resume' else None)
if a.mode=='save':Path(a.checkpoint).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
