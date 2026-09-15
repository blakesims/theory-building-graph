#!/usr/bin/env python3
"""Independent agent proposals, followed by isolated CLI validation. No live writes."""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'reviews'/'author-trials'

def run(item):
    raw=(ROOT/item['input']).read_text();data=json.loads(raw)
    command=['claude','-p','--safe-mode','--tools','','--no-session-persistence','--output-format','json']
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='theory-author-') as directory:
        result=subprocess.run(command,input=raw,text=True,capture_output=True,cwd=directory,timeout=240)
        receipt={'id':item['id'],'cases':item['cases'],'command':command,'input_sha256':hashlib.sha256(raw.encode()).hexdigest(),'input_bytes':len(raw.encode()),'elapsed_seconds':round(time.monotonic()-start,3),'exit_code':result.returncode,'stderr':result.stderr,'scope':'Agent proposes edits from supplied context; harness validates them with actual CLI against an isolated graph. No claim of autonomous retrieval.'}
        try:
            receipt['claude_result']=json.loads(result.stdout)
            text=receipt['claude_result']['result'].strip()
            if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
            proposal=json.loads(text);receipt['proposal']=proposal
            path=Path(directory)/'graph.json';path.write_text(json.dumps(data['graph']))
            before=path.read_bytes();operations=proposal.get('proposed_operations',[])
            if operations:
                cmd=[sys.executable,str(ROOT/'graph.py'),'--file',str(path),'apply','-','--actor','blind-participant','--reason','Synthetic authorized proposal validation','--expect',str(data['graph']['revision']),'--json']
                applied=subprocess.run(cmd,input=json.dumps(operations),text=True,capture_output=True,cwd=ROOT,timeout=20)
                receipt['apply']={'command':cmd,'returncode':applied.returncode,'stdout':applied.stdout,'stderr':applied.stderr,'final_graph':json.loads(path.read_text())}
            else:receipt['apply']={'status':'no-edits-proposed','unchanged':path.read_bytes()==before}
        except (ValueError,KeyError) as error:receipt['parse_error']=str(error);receipt['raw_stdout']=result.stdout
    (OUT/(item['id']+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'completed':item['id'],'exit_code':result.returncode,'apply':receipt.get('apply',{}).get('returncode',receipt.get('apply',{}).get('status'))}),flush=True)
    return result.returncode

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packets',default='fixtures/author-trials')
    parser.add_argument('--output',default='reviews/author-trials')
    args=parser.parse_args()
    OUT=ROOT/args.output;OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/args.packets/'manifest.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        codes=list(pool.map(run,manifest))
    raise SystemExit(int(any(codes)))
