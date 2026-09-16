#!/usr/bin/env python3
"""Run isolated default-model Claude Code participants on equivalent packets.
No tools, repo context, history, customizations or grader rubric are supplied.
Receipts are measurements and answers, not self-grades.
"""
import concurrent.futures
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
import sys as _path_sys
_path_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.paths import RepositoryPath as Path
ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'fixtures'/'cold-start'
OUT=ROOT/'reviews'/'blind-trials'
OUT.mkdir(parents=True,exist_ok=True)

def run(arm,trial):
    payload=(PACK/('graph-arm.json' if arm=='graph' else 'prose-arm.md')).read_text()
    prompt=(PACK/'participant-instructions.md').read_text()+'\nSOURCE PACKET\n'+payload+'\nQUESTIONS\n'+(PACK/'questions.json').read_text()+'\nReturn a JSON object {"answers":{"q1":"...","q2":"...","q3":"...","q4":"..."}}. Do not wrap it in Markdown. Include evidence references in the answer strings.'
    command=['claude','-p','--safe-mode','--tools','','--no-session-persistence','--output-format','json']
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='theory-blind-') as cwd:
        process=subprocess.run(command,input=prompt,text=True,capture_output=True,cwd=cwd,timeout=240)
    receipt={'arm':arm,'trial':trial,'command':command,'input_bytes':len(prompt.encode()),'input_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'elapsed_seconds':round(time.monotonic()-start,3),'retrieval_calls':0,'packet_deliveries':1,'exit_code':process.returncode,'stderr':process.stderr,'scope':'Controlled cold-start on injected equivalent packet; no tool retrieval or graph authoring measured.'}
    try:receipt['claude_result']=json.loads(process.stdout)
    except ValueError:receipt['raw_stdout']=process.stdout
    path=OUT/f'{arm}-{trial}.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'completed':str(path),'exit_code':process.returncode,'elapsed_seconds':receipt['elapsed_seconds']}),flush=True)
    return process.returncode

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,arm,trial) for trial in (1,2) for arm in ('graph','prose')]
        codes=[f.result() for f in futures]
    raise SystemExit(int(any(codes)))
