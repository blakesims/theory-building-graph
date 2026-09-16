"""Record actual subprocess receipts without interpreting their correctness."""
import sys,subprocess,time,json,hashlib
from pathlib import Path
label,*command=sys.argv[1:]
if not command or '/' in label or '..' in label:raise SystemExit('label then command required')
start=time.monotonic();r=subprocess.run(command,capture_output=True,text=True)
Path('runs').mkdir(exist_ok=True)
data={'command':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.monotonic()-start}
Path('runs',label+'.json').write_text(json.dumps(data,indent=2)+'\n')
print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr)
raise SystemExit(r.returncode)
