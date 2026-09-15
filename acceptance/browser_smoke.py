#!/usr/bin/env python3
"""Live browser smoke on an isolated graph. Requires npx agent-browser@0.27.0."""
import hashlib,json,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import graph
OUT=ROOT/'reviews'/'browser';OUT.mkdir(exist_ok=True)
log=[]
def browser(*args):
    cmd=['npx','--yes','agent-browser@0.27.0','--session','theory-smoke',*args]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
    log.append({'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    (OUT/'commands.json').write_text(json.dumps(log,indent=2)+'\n')
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    return r.stdout
before=(ROOT/'graph.json').read_bytes()
with tempfile.TemporaryDirectory(prefix='theory-browser-') as d:
    path=Path(d)/'graph.json';path.write_bytes(before)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    proc=subprocess.Popen([sys.executable,str(ROOT/'graph.py'),'--file',str(path),'serve','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:urllib.request.urlopen(url+'/api/status',timeout=1);break
            except OSError:time.sleep(.05)
        browser('open',url)
        browser('wait','--text','Live · r'+str(json.loads(before)['revision']))
        browser('snapshot','-i')
        browser('fill','#search','stopping-authority')
        browser('wait','--fn',"document.querySelector('#results button') !== null")
        browser('click','#results button')
        browser('wait','--text','Readiness:')
        browser('snapshot','-i')
        body=browser('get','text','#detail')
        assert 'Resolution: open' in body,body
        browser('find','role','button','click','--name','Show affected dependencies')
        browser('wait','--text','Declared dependency impact')
        browser('find','role','button','click','--name','Inspect checks')
        browser('wait','--text','Findings about this node')
        browser('screenshot',str(OUT/'readiness.png'))
        original=graph.load(path);anchor=next(k for k,v in original['nodes'].items() if v['type']=='entity')
        edits=[{'op':'add','collection':'nodes','id':'ui-observability-fixture','value':{'type':'question','status':'open','text':'SYNTHETIC: can the user see this new question?','meta':{'synthetic':True,'answer_shape':'verdict'}}}, {'op':'add','collection':'edges','id':'ui-fixture-about','value':{'type':'about','from':'ui-observability-fixture','to':anchor}}]
        (OUT/'edits.json').write_text(json.dumps(edits,indent=2)+'\n')
        r=subprocess.run([sys.executable,str(ROOT/'graph.py'),'--file',str(path),'apply',str(OUT/'edits.json'),'--actor','browser-smoke','--reason','Synthetic visual observability check','--expect',str(original['revision']),'--json'],capture_output=True,text=True)
        log.append({'command':['graph.py','--file','TEMP_GRAPH','apply','reviews/browser/edits.json'],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0,r.stderr
        browser('wait','--text',f"Live · r{original['revision']+1}")
        browser('fill','#search','ui-observability-fixture')
        browser('wait','--fn',"document.querySelector('#results button')?.textContent.includes('ui-observability-fixture')")
        browser('click','#results button')
        browser('wait','--text','SYNTHETIC: can the user see this new question?')
        browser('snapshot','-i')
        browser('screenshot',str(OUT/'live-change.png'))
        browser('click','#history-button')
        browser('wait','--text','Synthetic visual observability check')
        history=browser('get','text','#activity-body');assert 'ui-observability-fixture' in history and 'ui-fixture-about' in history
        browser('screenshot',str(OUT/'change-history.png'))
        assert (ROOT/'graph.json').read_bytes()==before
        (OUT/'receipt.json').write_text(json.dumps({'status':'completed','passed':True,'synthetic':True,'graph_revision':original['revision'],'live_graph_unchanged':True,'scope':'Browser integration on isolated graph: search, question resolution, impact, scoped findings, live add+edge update and history. Not an LLM or design evaluation.','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'index.html',ROOT/'graph.py',OUT/'commands.json',OUT/'edits.json']},'checks':['resolution-open','impact-visible','findings-visible','revision-live-update','new-node-findable','node-and-edge-history','live-data-unchanged']},indent=2)+'\n')
        print('Browser smoke passed:',OUT/'receipt.json')
    finally:
        browser('close');proc.terminate();proc.wait(timeout=10)
        receipt=OUT/'receipt.json'
        if receipt.exists():
            result=json.loads(receipt.read_text());result['files_sha256']['commands.json']=hashlib.sha256((OUT/'commands.json').read_bytes()).hexdigest();receipt.write_text(json.dumps(result,indent=2)+'\n')
