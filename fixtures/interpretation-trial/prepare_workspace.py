"""Copy only engine + participant inputs into a NEW isolated workspace (no rubric)."""
import argparse,shutil,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('destination',type=Path);a=p.parse_args();source=Path(__file__).resolve().parent;repo=source.parents[1]
if a.destination.exists():raise SystemExit('Destination must not exist')
shutil.copytree(source/'participant',a.destination)
for name in ['graph.py','dependency.py','formalcheck.py','tracecheck.py','replay.py','tg']:
 shutil.copy2(repo/name,a.destination/name)
(a.destination/'tg').chmod(0o755)
manifest={str(f.relative_to(a.destination)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.destination.rglob('*') if f.is_file()}
(a.destination/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(a.destination.resolve())
