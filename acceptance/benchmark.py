#!/usr/bin/env python3
"""Deterministic scale probe; output costs are measurements, not compression guarantees."""
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theorygraph import graph
from theorygraph import dependency

def make_fixture():
    g={'version':1,'revision':0,'node_types':{t:{} for t in ('claim','entity','question')},'edge_types':{'about':{},'depends-on':{}},'nodes':{},'edges':{},'changes':[]}
    for i in range(50):g['nodes'][f'anchor-{i}']={'type':'entity','text':f'Entity {i}'}
    for i in range(2500):
        key=f'claim-{i}'
        g['nodes'][key]={'type':'claim','text':f'Synthetic claim {i}.','status':'accepted','meta':{'source_detail':'x'*1000}}
        g['edges'][f'about-{i}']={'type':'about','from':key,'to':f'anchor-{i%50}'}
        if i:
            # Depth20 spine, followed by broad fanout; a second path makes diamonds.
            parent=i-1 if i<=20 else 20
            g['edges'][f'dep-{i}']={'type':'depends-on','from':key,'to':f'claim-{parent}'}
            if i>21 and i%7==0:g['edges'][f'diamond-{i}']={'type':'depends-on','from':key,'to':'claim-19'}
    for i in range(500):
        key=f'question-{i}'
        g['nodes'][key]={'type':'question','text':f'Question {i}?','status':'open'}
        g['edges'][f'question-dep-{i}']={'type':'depends-on','from':key,'to':f'claim-{i}'}
    return g

def main():
    g=make_fixture();raw=json.dumps(g,sort_keys=True).encode();graph.validate(g)
    results={}
    for name,fn in [('claim_walk',lambda:graph.walk(g,'claim-1',depth=4,limit=20,edge_limit=30)),('hub_walk',lambda:graph.walk(g,'anchor-0',depth=4,limit=20,edge_limit=30)),('impact_page',lambda:dependency.impact(g,['claim-0'],limit=20)),('question_page',lambda:graph.questions(g,limit=20))]:
        start=time.perf_counter();r=fn()
        results[name]={'seconds':round(time.perf_counter()-start,6),'compact_bytes':len(graph.compact(r).encode()),'json_bytes':len(json.dumps(r,separators=(',',':')).encode()),'truncated':r.get('truncated'),'total_affected':r.get('total_affected'),'boundary_edges':r.get('boundary_edges')}
    assert dependency.impact(g,['claim-0'],limit=20)['total_affected']==2999
    report={'fixture':{'nodes':len(g['nodes']),'edges':len(g['edges']),'claims':2500,'anchors':50,'questions':500,'sha256':hashlib.sha256(raw).hexdigest()},'measurements':results,'scope':'Single-machine synthetic probe. No LLM token estimate or unbounded scaling claim.'}
    (ROOT/'acceptance'/'benchmark-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
