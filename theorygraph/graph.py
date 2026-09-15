#!/usr/bin/env python3
"""Local theory graph: compact reads, atomic audited batch writes, read-only web view."""
import argparse, collections, copy, datetime, fcntl, hashlib, json, os, sys, tempfile, re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from . import tracecheck
from . import dependency
from . import projects
HERE = Path(__file__).resolve().parent

class GraphError(Exception): pass

def load(path):
    with open(path) as f: g = json.load(f)
    validate(g)
    return g

def validate(g):
    if g.get('version') != 1 or not isinstance(g.get('revision'), int): raise GraphError('Expected version 1 and integer revision')
    for key in ('nodes','edges','node_types','edge_types'):
        if not isinstance(g.get(key), dict): raise GraphError(f'{key} must be an object')
    if not isinstance(g.get('changes'), list): raise GraphError('changes must be a list')
    if 'formal_model' in g and not isinstance(g['formal_model'],dict): raise GraphError('formal_model must be an object')
    for collection in ('node_types','edge_types'):
        for key,definition in g[collection].items():
            if not isinstance(definition,dict):raise GraphError(collection+'/'+key+' must be an object')
    for nid,n in g['nodes'].items():
        if not nid or not isinstance(n,dict) or n.get('type') not in g['node_types'] or not isinstance(n.get('text'),str): raise GraphError(f'Invalid node {nid}')
        if 'meta' in n and not isinstance(n['meta'],dict):raise GraphError('meta must be an object on '+nid)
        allowed=g['node_types'][n['type']].get('states')
        if allowed and n.get('status') not in allowed: raise GraphError(f'Invalid state for {nid}: {n.get("status")} (allowed: {allowed})')
        if review_state(n) not in ('current','needs-review','historical'): raise GraphError(f'Invalid review_state on {nid}')
    for eid,e in sorted(g['edges'].items()):
        if not eid or not isinstance(e,dict) or e.get('type') not in g['edge_types']: raise GraphError(f'Invalid edge {eid}')
        if e.get('from') not in g['nodes'] or e.get('to') not in g['nodes']: raise GraphError(f'Unknown endpoint on edge {eid}')
        if e['type']=='answers' and g['edge_types']['answers'].get('coverage_required'):
            if e.get('coverage') not in ('full','partial','unknown'): raise GraphError(f'Answer {eid} requires coverage: full|partial|unknown')
            if g['nodes'][e['to']]['type']!='question' or g['nodes'][e['from']]['type']!='claim': raise GraphError(f'Answer {eid} must link claim to question')
    try: dependency.validate(g)
    except ValueError as e: raise GraphError(str(e))


def review_state(n): return (n.get('meta') or {}).get('review_state','current')

def questions(g, limit=30, historical=False):
    if limit < 1: raise GraphError('limit must be >= 1')
    states={}; nodes={}; totals=collections.Counter()
    all_questions={i:n for i,n in sorted(g['nodes'].items()) if n['type']=='question'}
    for i,n in all_questions.items():
        if review_state(n)=='historical':
            state='historical'
            if not historical: continue
        else:
            answers=[e for e in g['edges'].values() if e['to']==i and e['type']=='answers' and review_state(g['nodes'][e['from']])!='historical']
            accepted=[e for e in answers if g['nodes'][e['from']].get('status')=='accepted']
            if review_state(n)=='needs-review': state='needs-review'
            elif any(e.get('coverage')=='full' and review_state(g['nodes'][e['from']])=='current' for e in accepted): state='answered'
            elif any(review_state(g['nodes'][e['from']])=='needs-review' for e in answers): state='needs-review'
            elif any(e.get('coverage')=='partial' for e in accepted): state='partial-answer'
            elif answers: state='candidate-answer'
            else: state='open'
        if state not in ('needs-review','historical'): state=dependency.resolution(g,i)['resolution']
        states[i]=state; nodes[i]=n; totals[state]+=1
    ids=sorted(nodes)[:limit]
    return {'revision':g['revision'],'total_questions':len(all_questions),'included_questions':len(nodes),'historical_excluded':sum(review_state(n)=='historical' for n in all_questions.values()) if not historical else 0,'counts':dict(totals),'question_states':{i:states[i] for i in ids},'truncated':len(nodes)>limit,'nodes':{i:nodes[i] for i in ids},'resolutions':{i:dependency.resolution(g,i) for i in ids},'readiness':{i:dependency.readiness(g,i) for i in ids}}

def review(g, root=None, limit=30, edge_limit=60):
    if root is None:
        items=[(i,n) for i,n in sorted(g['nodes'].items()) if review_state(n)=='needs-review']
        return {'revision':g['revision'],'total':len(items),'truncated':len(items)>limit,'nodes':dict(items[:limit])}
    if root not in g['nodes']: root=resolve(g,root)
    relevant={i:e for i,e in sorted(g['edges'].items()) if (e['to']==root and e['type'] in ('answers','revises','challenges','raises','motivates','informs','about','governs','potential-conflict','depends-on','extracted-from')) or (e['from']==root and (e['type'] in ('revises','challenges','depends-on','extracted-from') or g['nodes'][e['to']]['type']=='question'))}
    edge_truncated=len(relevant)>edge_limit
    relevant=dict(list(relevant.items())[:edge_limit])
    ids=list(dict.fromkeys([root]+[n for e in relevant.values() for n in (e['from'],e['to'])]))
    chosen=ids[:limit]
    return {'revision':g['revision'],'focus':root,'edge_truncated':edge_truncated,'truncated':len(ids)>limit,'nodes':{i:g['nodes'][i] for i in chosen},'edges':{i:e for i,e in relevant.items() if e['from'] in chosen and e['to'] in chosen}}

def overview(g):
    return {'revision':g['revision'],'nodes':len(g['nodes']),'edges':len(g['edges']),'node_types':dict(collections.Counter(n['type'] for n in g['nodes'].values())),'statuses':dict(collections.Counter(n.get('status','unset') for n in g['nodes'].values()))}

def walk(g, root, depth=1, direction='both', limit=40, edge_limit=100, current=True, anchors='stop', relations=None):
    root=resolve(g,root)
    if direction not in ('both','in','out'): raise GraphError('direction must be both, in or out')
    if anchors not in ('stop','cross','omit'): raise GraphError('anchors must be stop, cross or omit')
    if relations:
        selected=set(relations.split(','))
        unknown=selected-set(g['edge_types'])
        if unknown: raise GraphError('Unknown relations: '+','.join(sorted(unknown)))
        g={**g,'edges':{i:e for i,e in sorted(g['edges'].items()) if e['type'] in selected}}
    if anchors=='omit': g={**g,'edges':{i:e for i,e in sorted(g['edges'].items()) if e['type'] not in ('about','governs')}}
    if current:
        visible={i:n for i,n in sorted(g['nodes'].items()) if review_state(n)!='historical' or i==root}
        g={**g,'nodes':visible,'edges':{i:e for i,e in sorted(g['edges'].items()) if e['from'] in visible and e['to'] in visible}}
    if edge_limit < 0: raise GraphError('edge-limit must be >= 0')
    if depth < 0 or limit < 1: raise GraphError('depth must be >= 0 and limit >= 1')
    adj = collections.defaultdict(set)
    for e in g['edges'].values():
        if direction in ('out','both'): adj[e['from']].add(e['to'])
        if direction in ('in','both'): adj[e['to']].add(e['from'])
    distances={root:0}; q=collections.deque([root]); truncated=False
    while q:
        n=q.popleft()
        if distances[n] >= depth or (anchors=='stop' and n!=root and g['nodes'][n]['type'] in ('entity','operation')): continue
        for other in sorted(adj[n]):
            if other in distances: continue
            if len(distances)>=limit: truncated=True; continue
            distances[other]=distances[n]+1; q.append(other)
    nodes={n:g['nodes'][n] for n in distances}
    edges={i:e for i,e in sorted(g['edges'].items()) if e['from'] in nodes and e['to'] in nodes}
    boundary=sum((e['from'] in nodes)!=(e['to'] in nodes) for e in g['edges'].values())
    edge_truncated=len(edges)>edge_limit
    edges=dict(list(edges.items())[:edge_limit])
    return {'boundary_edges':boundary,'anchor_traversal':anchors,'edge_truncated':edge_truncated,'edge_limit':edge_limit,'revision':g['revision'],'root':root,'depth':depth,'direction':direction,'limit':limit,'truncated':truncated,'distances':distances,'nodes':nodes,'edges':edges}

def resolve(g, value):
    if value in g['nodes']: return value
    term=value.casefold()
    matches=[i for i,n in sorted(g['nodes'].items()) if term in [str(x).casefold() for x in [(n.get('meta') or {}).get('title','')]+(n.get('meta') or {}).get('aliases',[])]]
    if len(matches)==1: return matches[0]
    if matches: raise GraphError('Ambiguous name; use an id: '+', '.join(matches))
    raise GraphError('Unknown node: '+value+' (try anchors or search)')

def search(g, query, limit=20):
    if limit < 1: raise GraphError('limit must be >= 1')
    def tokens(text):
        # Deliberately tiny vocabulary normalization, not semantic/full-text search.
        synonyms={'failure':'fail','failures':'fail','failed':'fail','failing':'fail'}
        return [synonyms.get(t,t) for t in re.findall(r"[\w-]+",text.casefold())]
    terms=tokens(query)
    matches=[]
    for i,n in sorted(g['nodes'].items()):
        meta=n.get('meta') or {}
        hay=' '.join([i,n['type'],n['text'],n.get('status',''),review_state(n),str(meta.get('title','')),' '.join(meta.get('aliases',[]))])
        words=tokens(hay)
        if all(any(t in w for w in words) for t in terms): matches.append((i,n))
    return {'revision':g['revision'],'total':len(matches),'truncated':len(matches)>limit,'nodes':dict(matches[:limit])}

def graph_view(g,current=True,limit=500,edge_limit=2000):
    if limit<1 or edge_limit<0: raise GraphError('Invalid graph limits')
    eligible={i:n for i,n in sorted(g['nodes'].items()) if not current or review_state(n)!='historical'}
    nodes=dict(list(eligible.items())[:limit]); edges={i:e for i,e in sorted(g['edges'].items()) if e['from'] in nodes and e['to'] in nodes}
    return {'revision':g['revision'],'total_nodes':len(eligible),'truncated':len(eligible)>limit,'edge_truncated':len(edges)>edge_limit,'nodes':nodes,'edges':dict(list(edges.items())[:edge_limit])}

def history(g,limit=10,full=False):
    if limit<1: raise GraphError('limit must be >= 1')
    changes=copy.deepcopy(g['changes'][-limit:])
    if not full:
        for change in changes:
            change['edits']=[{'collection':e['collection'],'id':e['id'],'action':'add' if e['before'] is None else 'delete' if e['after'] is None else 'update','fields':([k for k in sorted(set(e['before'] or {})|set(e['after'] or {})) if (e['before'] or {}).get(k)!=(e['after'] or {}).get(k)] if isinstance(e['before'],(dict,type(None))) and isinstance(e['after'],(dict,type(None))) else ['value']),**({'automatic':e['automatic']} if 'automatic' in e else {})} for e in change['edits']]
    return {'revision':g['revision'],'total_revisions':len(g['changes']),'changes':changes,'full':full}

def check(g):
    findings=[]
    def add(code,message,nodes,edges=None): findings.append({'code':code,'severity':'review','message':message,'nodes':nodes,'edges':edges or []})
    for eid,e in sorted(g['edges'].items()):
        a,b=g['nodes'][e['from']],g['nodes'][e['to']]
        if e['type']=='answers' and e.get('coverage') not in ('full','partial','unknown'): add('answer-coverage','Answer lacks explicit full/partial/unknown coverage.',[e['from'],e['to']],[eid])
        if review_state(a)=='historical' or review_state(b)=='historical': continue
        if e['type'] in ('potential-conflict','contradicts'): add('potential-conflict' if e['type']=='potential-conflict' else 'declared-contradiction','Declared tension between current claims; inspect wording, conditions and authority. Not an automatically proven contradiction.',[e['from'],e['to']],[eid])
    for i,n in sorted(g['nodes'].items()):
        if review_state(n)=='historical': continue
        if n['type']=='claim' and not any(e['from']==i and e['type'] in ('about','governs') for e in g['edges'].values()): add('unanchored-claim','Claim has no entity or operation anchor.',[i])
    findings.extend(dependency.findings(g))
    try:
        from . import formalcheck
        unchecked=set()
        for nid,node in sorted(g['nodes'].items()):
            if dependency.retired(node) or not isinstance(node.get('pattern'),dict): continue
            refs=formalcheck.references(node['pattern'])
            missing={'nodes':[r for r in refs['nodes'] if r not in g['nodes']],
                     'relations':[r for r in refs.get('relations',[]) if r not in g['edge_types']],
                     'scopes':[r for r in refs['scopes'] if r not in {'all','after_attempt_ended'} and r not in g.get('formal_model',{}).get('scopes',{})]}
            missing={k:v for k,v in missing.items() if v}
            if missing:
                unchecked.add(nid)
                findings.append({'code':'undeclared-pattern-reference','nodes':[nid],'edges':[],
                    'severity':'review','outcome':'not-checked','missing':missing,'message':'Pattern references undeclared identities; declare or correct them before checking.'})
        comparable={**g,'nodes':{i:n for i,n in g['nodes'].items() if i not in unchecked}}
        findings.extend(formalcheck.compare_graph(comparable))
    except ImportError: pass
    # Stable IDs are content-derived; insertion ordering never affects findings.
    for finding in findings:
        finding.setdefault('nodes',[]); finding.setdefault('edges',[])
        finding.setdefault('severity','review'); finding.setdefault('message',finding.get('reason',finding.get('outcome','Formal comparison finding.')))
        finding['id']='finding-'+hashlib.sha256(json.dumps({k:v for k,v in finding.items() if k not in {'id','computed_revision','revision','checked_at','at'}},sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    findings.sort(key=lambda f:(f['code'],f['nodes'],f['edges'],f['id']))
    return {'revision':g['revision'],'counts':dict(sorted(collections.Counter(f['code'] for f in findings).items())),
            'suppressed_count':sum(bool(f.get('suppressed')) for f in findings),'findings':findings,
            'scope':'Declared dependencies, structural gaps, recorded tensions, and supported formal patterns only. Prose requires agent review.'}


def apply(path, ops, actor, reason, expected=None):
    if not actor.strip() or not reason.strip(): raise GraphError('actor and reason are required')
    if not isinstance(ops,list) or not ops: raise GraphError('Expected a nonempty JSON array of operations')
    path=Path(path)
    with open(str(path)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        g=load(path)
        if expected is not None and expected!=g['revision']: raise GraphError(f'Revision conflict: expected {expected}, found {g["revision"]}')
        original=copy.deepcopy(g)
        edits=[]
        for op in ops:
            if not isinstance(op,dict): raise GraphError('Each operation must be an object')
            action=op.get('op'); collection=op.get('collection'); key=op.get('id')
            if collection not in ('nodes','edges','node_types','edge_types','formal_model') or not isinstance(key,str) or not key: raise GraphError('Operation needs collection and nonempty id')
            if action in ('add','update') and 'value' not in op:raise GraphError('add/update require an explicit value')
            if collection=='formal_model': g.setdefault(collection,{})
            before=copy.deepcopy(g[collection].get(key))
            if action=='add':
                if key in g[collection]: raise GraphError(f'Already exists: {collection}/{key}')
                after=op.get('value')
            elif action=='update':
                if key not in g[collection]: raise GraphError(f'Not found: {collection}/{key}')
                if collection=='formal_model': after=copy.deepcopy(op.get('value'))
                else:
                    if not isinstance(op.get('value'),dict): raise GraphError('update value must be an object')
                    after={**before,**op['value']}
                    if isinstance(before.get('meta'),dict) and isinstance(op['value'].get('meta'),dict): after['meta']={**before['meta'],**op['value']['meta']}
            elif action=='delete':
                if key not in g[collection]: raise GraphError(f'Not found: {collection}/{key}')
                after=None
            else: raise GraphError('op must be add, update, or delete')
            if action=='delete': del g[collection][key]
            else:
                if collection!='formal_model' and not isinstance(after,dict): raise GraphError('value must be an object')
                g[collection][key]=copy.deepcopy(after)
            edits.append({'collection':collection,'id':key,'before':before,'after':copy.deepcopy(after)})
        # Validate before automatic interpretation; malformed JSON must be an atomic domain error.
        validate(g)
        reviewed={o['id'] for o in ops if o.get('collection')=='nodes' and 'review_state' in (o.get('value',{}).get('meta') or {})}
        dependency.refresh(original,g,edits,reviewed)
        # Deleting a named semantic input must not leave a surviving opaque pattern dangling.
        deleted=set(original['nodes'])-set(g['nodes'])
        def node_references(node):
            from . import formalcheck
            refs=set(node.get('references',[]))
            if isinstance(node.get('pattern'),dict):refs.update(formalcheck.references(node['pattern']).get('nodes',[]))
            provenance=node.get('provenance') or {}
            for source in provenance.get('sources',[]):
                ref=source if isinstance(source,str) else source.get('id') if isinstance(source,dict) else None
                if isinstance(ref,str):refs.add(ref)
            # Event IDs, attempts, labels and report field values are trace-local data,
            # not graph references. Only declared operation/role fields point to nodes.
            trace=node.get('trace') or {}
            for event in (trace.get('events',[]) if isinstance(trace.get('events',[]),list) else []):
                if not isinstance(event,dict):continue
                for key in ('operation','actor_role'):
                    if isinstance(event.get(key),str):refs.add(event[key])
                refs.update(r for r in (event.get('actor_roles',[]) if isinstance(event.get('actor_roles',[]),list) else []) if isinstance(r,str))
            result=node.get('result') or {}
            refs.update(result.get('input_fingerprints',{}))
            for key in ('claim','trace'):
                if isinstance(result.get(key),str):refs.add(result[key])
            return refs
        for nid,node in g['nodes'].items():
            if not deleted:break
            dangling=sorted(deleted & node_references(node))
            if dangling:raise GraphError(f'Deletion leaves semantic reference {nid} -> '+', '.join(dangling)+'; retire the input instead')
        try:
            from . import formalcheck
            for nid,node in g['nodes'].items():
                refs=formalcheck.references(node.get('pattern') or {})
                for target in refs.get('scopes',[]):
                    if target in original.get('formal_model',{}).get('scopes',{}) and target not in g.get('formal_model',{}).get('scopes',{}):
                        raise GraphError(f'Deletion leaves scope reference {nid} -> {target}')
                for target in refs.get('relations',[]):
                    if target in original['edge_types'] and target not in g['edge_types']:
                        raise GraphError(f'Deletion leaves relation reference {nid} -> {target}')
        except ImportError: pass
        g['revision']+=1
        g['changes'].append({'revision':g['revision'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor':actor,'reason':reason,'edits':edits})
        validate(g)
        fd,name=tempfile.mkstemp(dir=path.parent,prefix='.graph-',suffix='.tmp')
        try:
            with os.fdopen(fd,'w') as f:
                json.dump(g,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(name,path)
            dfd=os.open(path.parent,os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        finally:
            if os.path.exists(name): os.unlink(name)
    return {'revision':g['revision'],'changes':len(edits)}

def save_evaluation(path,g,result,result_id=None,actor='assistant'):
    result_id=result_id or f"check-{result['claim']}-{result['trace']}-r{g['revision']}"
    if result_id in g['nodes']: raise GraphError('Result id already exists; use a new id to preserve check history')
    operations=[]
    if 'check-result' not in g['node_types']:
        operations.append({'op':'add','collection':'node_types','id':'check-result','value':{'description':'Saved finite-trace pattern evaluation. Freshness is derived from input fingerprints.','states':['recorded']}})
    node={'type':'check-result','status':'recorded','text':f"Pattern {result['outcome']}: {result['claim']} against {result['trace']}. This is a finite trace check, not proof of the whole claim.",
          'result':result,'meta':{'author':actor,'source_kind':'computed-pattern-check','synthetic':result['synthetic'],'title':f"Pattern {result['outcome']}", 'review_state':'current'}}
    operations.append({'op':'add','collection':'nodes','id':result_id,'value':node})
    if 'checks' not in g['edge_types']:
        operations.append({'op':'add','collection':'edge_types','id':'checks','value':{'description':'A saved computation checked this input; does not imply support or acceptance.'}})
    for suffix,target in [('claim',result['claim']),('trace',result['trace'])]:
        operations.append({'op':'add','collection':'edges','id':result_id+'-'+suffix,'value':{'type':'checks','from':result_id,'to':target}})
    saved=apply(path,operations,actor,'Save finite-trace pattern evaluation; do not change belief status',g['revision'])
    return {**result,'saved_as':result_id,'saved_revision':saved['revision'],'result_state':'current'}

def compact_read(data,g):
    """CLI projection only: preserve propositions and references, omit unrequested notes."""
    if not isinstance(data.get('nodes'),dict): return data
    data=copy.deepcopy(data)
    keep=dependency.SEMANTIC_META | {'title','aliases','author','source_ref','source_refs','sources','provenance',
        'review_state','review_reason','review_roots','reviewed_inputs','reviewed_input_versions','summary','decision_reason'}
    omitted={}
    for nid,node in data['nodes'].items():
        meta=node.get('meta') or {}
        declared=set(g['node_types'].get(node['type'],{}).get('compact_meta_fields',[]))
        hidden=sorted(set(meta)-(keep|declared))
        if hidden:
            omitted[nid]=hidden
            node['meta']={k:v for k,v in meta.items() if k in keep|declared}
    if omitted:
        data['metadata_omitted']=omitted
        data['metadata_access']='Use --full to include omitted metadata; semantic statements and patterns are not truncated.'
    return data

def compact(data, full=False):
    def display(v):
        return json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else str(v)
    if 'outcome' in data and 'checker_version' in data:
        lines=[f"Pattern {data['outcome']} · {data['claim']} × {data['trace']}",data['scope']]
        if data.get('synthetic'): lines.append('SYNTHETIC FIXTURE — not observed runtime evidence')
        if 'checked_events' in data: lines.append('checked events: '+display(data['checked_events']))
        for label in ('vacuous','permission_only','evidence_basis','empirical_support'):
            if label in data:lines.append(label+': '+display(data[label]))
        if 'assessment' in data: lines.append('assessment: '+display(data['assessment']))
        if 'reachability' in data: lines.append('reachability: '+display(data['reachability']))
        lines.extend('witness: '+display(w) for w in data['witnesses'])
        lines.extend('diagnostic: '+display(d) for d in data['diagnostics'])
        if data.get('saved_as'): lines.append('saved: '+data['saved_as'])
        return '\n'.join(lines)
    if 'changes' in data and isinstance(data['changes'],list):
        lines=[f"Revision {data['revision']} · {len(data['changes'])} of {data.get('total_revisions',len(data['changes']))} changes"]
        for c in data['changes']:
            lines.append(f"r{c['revision']} {c['actor']}: {c['reason']}")
            for e in c['edits']:
                lines.append('  '+(json.dumps(e,ensure_ascii=False) if full else f"{e['action']} {e['collection']}/{e['id']} ({', '.join(e['fields'])})"))
        return '\n'.join(lines)
    if 'findings' in data:
        return '\n'.join([f"Revision {data['revision']} · {len(data['findings'])} findings"]+[f"[{f.get('severity','review')}{'; suppressed' if f.get('suppressed') else ''}] {f['code']}: {f['message']} [{', '.join(f['nodes'])}]" for f in data['findings']]+[data['scope']])
    if not isinstance(data.get('nodes'),dict): return '\n'.join(f'{k}: {display(v)}' for k,v in data.items())
    lines=[' · '.join(f'{k}={display(v)}' for k,v in data.items() if k not in ('nodes','edges','distances','question_states','resolutions','readiness'))]
    for i,n in data['nodes'].items():
        meta=n.get('meta') or {}
        attribution=meta.get('source_kind')
        lines.append(f'{i} [{n["type"]};{n.get("status","unset")};{review_state(n)}'+(f';{attribution}' if attribution else '')+f'] {n["text"]}')
        if i in data.get('resolutions',{}):
            answer=data['resolutions'][i]; readiness=data.get('readiness',{}).get(i,{})
            lines.append('  answer: '+answer['resolution']+'; readiness: '+readiness.get('readiness','unknown')+'; blockers: '+str(len(readiness.get('blockers',[]))))
            if answer.get('unresolved'):lines.append('  unresolved: '+display(answer['unresolved']))
        if meta.get('review_reason'): lines.append('  review: '+meta['review_reason'])
        if n.get('result_state'): lines.append('  check freshness: '+n['result_state']+' · pattern '+n['result']['outcome'])
        if n.get('pattern'): lines.append('  pattern: '+display(n['pattern']))
        if full and n.get('trace'): lines.append('  trace: '+display(n['trace']))
        if full and n.get('result'): lines.append('  result: '+display(n['result']))
        if full and meta: lines.append('  '+json.dumps(meta,ensure_ascii=False,separators=(',',':')))
    for i,e in data.get('edges',{}).items():
        coverage=' ('+e['coverage']+')' if e.get('coverage') else ''
        lines.append(f'{i}: {e["from"]} -{e["type"]}{coverage}-> {e["to"]}')
        if full and e.get('meta'): lines.append('  '+json.dumps(e['meta'],ensure_ascii=False,separators=(',',':')))
    return '\n'.join(lines)

def serve(path,port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed=urlparse(self.path); params=parse_qs(parsed.query)
            def p(k,d): return params.get(k,[d])[0]
            try:
                route=parsed.path
                if route in ('/','/index.html'): return self.send((HERE/'viewer'/'index.html').read_bytes(),'text/html; charset=utf-8')
                if route=='/vendor/cytoscape.min.js': return self.send((HERE/'viewer'/'vendor'/'cytoscape.min.js').read_bytes(),'application/javascript')
                g=load(path)
                if route=='/api/status': result=overview(g)
                elif route=='/api/walk': result=walk(g,p('id',next(iter(g['nodes']),'')),int(p('depth','2')),p('direction','both'),min(200,int(p('limit','40'))),min(500,int(p('edge_limit','100'))),p('current','1')=='1',p('anchors','stop'),p('relations',None))
                elif route=='/api/graph': result=graph_view(g,p('current','1')=='1',min(2000,int(p('limit','500'))),min(10000,int(p('edge_limit','2000'))))
                elif route=='/api/evaluations': result=tracecheck.evaluations(g,p('id',None))
                elif route=='/api/readiness': result=dependency.readiness(g,resolve(g,p('id','')))
                elif route=='/api/impact': result=dependency.impact(g,[resolve(g,p('id',''))],min(200,int(p('limit','100'))),int(p('offset','0')))
                elif route=='/api/check': result=check(g)
                elif route=='/api/questions': result=questions(g,historical=p('historical','0')=='1')
                elif route=='/api/review': result=review(g,p('id',None))
                elif route=='/api/search': result=search(g,p('q',''),min(200,int(p('limit','30'))))
                elif route=='/api/node':
                    nid=resolve(g,p('id',''))
                    if nid not in g['nodes']: raise GraphError('Unknown node')
                    result={'id':nid,**g['nodes'][nid]}
                elif route=='/api/history': result=history(g,min(100,int(p('limit','10'))),p('full','0')=='1')
                elif route=='/api/types': result={k:g[k] for k in ('node_types','edge_types')}
                else: return self.send(b'Not found','text/plain',404)
                self.send(json.dumps(tracecheck.annotate(g,result),ensure_ascii=False).encode(),'application/json')
            except (GraphError,ValueError,KeyError,OSError) as e: self.send(json.dumps({'error':str(e)}).encode(),'application/json',400)
        def send(self,data,ctype,code=200):
            self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self,*a): pass
    print(f'Theory graph: http://127.0.0.1:{port} · {path}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

def main():
    p=argparse.ArgumentParser(description=__doc__,epilog='Default reads omit historical material. Use --historical to include it. JSON flags work before or after subcommands.')
    p.add_argument('--file',type=Path,default=None,help='Graph JSON file (default: -p project, $TG_PROJECT, nearest theory/graph.json, then the registry default)'); p.add_argument('-p','--project',default=None,help='Registered project name (see `tg projects`)'); p.add_argument('--json',action='store_true',help='Emit machine-readable JSON'); p.add_argument('--full',action='store_true',help='Include metadata or full history before/after values')
    sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('overview','types','anchors','check'): sub.add_parser(name,help={'anchors':'List entity and operation anchors','check':'Check declared tensions and structural consistency'}.get(name,name))
    q=sub.add_parser('readiness',help='Explicit prerequisites and independent answer resolution');q.add_argument('id')
    q=sub.add_parser('impact',help='Transitive dependent IDs and bounded dependency path witnesses');q.add_argument('id');q.add_argument('--limit',type=int,default=100);q.add_argument('--offset',type=int,default=0);q.add_argument('--path-limit',type=int,default=8)
    q=sub.add_parser('export',help='Canonical sorted JSON snapshot')
    q=sub.add_parser('questions',help='Question inventory with explicit inclusion and derived answer states');q.add_argument('--limit',type=int,default=30,help='Maximum question rows');q.add_argument('--historical',action='store_true',help='Include retired questions')
    q=sub.add_parser('review',help='Review a node and its direct reasoning context, or list review queue');q.add_argument('id',nargs='?',help='Node id, title or alias');q.add_argument('--limit',type=int,default=30,help='Maximum nodes');q.add_argument('--edge-limit',type=int,default=60,help='Maximum edges')
    q=sub.add_parser('search',help='Basic matching of id, title, alias, type, text and state');q.add_argument('query');q.add_argument('--limit',type=int,default=20,help='Maximum results')
    q=sub.add_parser('node',help='Read a node with all incident edge references');q.add_argument('id',help='Node id, title or alias');q.add_argument('--historical',action='store_true',help='Include historical neighbors')
    for name in ('walk','neighbors'):
        q=sub.add_parser(name,help='Bounded directed traversal; anchors stop expansion unless selected as root')
        q.add_argument('id',help='Node id, title or alias');q.add_argument('--depth',type=int,default=1,help='Maximum hop distance');q.add_argument('--direction',choices=['both','in','out'],default='both',help='Traversal direction; edge direction is preserved');q.add_argument('--limit',type=int,default=40,help='Maximum nodes');q.add_argument('--edge-limit',type=int,default=100,help='Maximum induced edges');q.add_argument('--current',action='store_true',help='Current material (default)');q.add_argument('--historical',action='store_true',help='Include historical nodes');q.add_argument('--anchors',choices=['stop','cross','omit'],default='stop',help='Stop at anchor hubs, cross them, or omit anchor links');q.add_argument('--relations',help='Only traverse comma-separated relation types')
    q=sub.add_parser('history',help='Compact change summaries; --full restores before/after');q.add_argument('--limit',type=int,default=10,help='Maximum revisions')
    q=sub.add_parser('apply',help='Apply an atomic audited JSON batch',description='Input: [{"op":"add|update|delete","collection":"nodes|edges|node_types|edge_types|formal_model","id":"stable-id","value":{...}}]. Node value: {"type":"claim","text":"...","status":"proposed","meta":{...}}. Edge value: {"from":"id","to":"id","type":"about","meta":{...}}. answers additionally require coverage full|partial|unknown. Updates merge fields and merge meta one level. Deletes omit value. Unknown references/types/states reject the entire batch. Explicit node meta.review_state reconciles that node in the same batch.')
    q.add_argument('operations',help='JSON array file path or - for stdin');q.add_argument('--actor',required=True,help='Who made this edit');q.add_argument('--reason',required=True,help='Why the batch is needed');q.add_argument('--expect',type=int,help='Reject the edit if current revision differs (recommended)')
    q=sub.add_parser('evaluate',help='Check one optional pattern against a finite trace; not a proof of the claim')
    q.add_argument('claim'); q.add_argument('trace'); q.add_argument('--save',nargs='?',const='',help='Save an audited check-result node, optionally with this new id');q.add_argument('--actor',default='assistant',help='Author of a saved evaluation')
    q=sub.add_parser('projects',help='List registered projects and the default')
    q=sub.add_parser('new',help='Create a new project graph from the template and register it');q.add_argument('name');q.add_argument('--dir',type=Path,default=None,help='Directory for graph.json (default: ./theory)');q.add_argument('--no-register',action='store_true')
    q=sub.add_parser('register',help='Register an existing graph.json under a name');q.add_argument('name');q.add_argument('path',type=Path);q.add_argument('--default',action='store_true',help='Also make it the default project')
    q=sub.add_parser('use',help='Set the default project');q.add_argument('name')
    q=sub.add_parser('serve',help='Serve this graph project only');q.add_argument('--port',type=int,default=8767,help='Local port; graph default8767, original notebook separate on8766')
    # Normalize these global flags so they also work after subcommands.
    argv=sys.argv[1:]; front=[];rest=[];i=0
    while i<len(argv):
        if argv[i] in ('--json','--full'): front.append(argv[i])
        elif argv[i] in ('--file','-p','--project'): front.extend(argv[i:i+2]);i+=1
        elif argv[i].startswith('--file=') or argv[i].startswith('--project='): front.append(argv[i])
        else: rest.append(argv[i])
        i+=1
    a=p.parse_args(front+rest)
    try:
        if a.cmd=='projects': result=projects.listing()
        elif a.cmd=='new': result={'created':str(projects.new(a.name,a.dir,not a.no_register)),'registered':not a.no_register,'next':f'tg -p {a.name} overview'}
        elif a.cmd=='register': result={'registered':a.name,'registry':projects.register(a.name,a.path,a.default)}
        elif a.cmd=='use': result={'default':a.name,'registry':projects.use(a.name)}
        if a.cmd in ('projects','new','register','use'):
            if a.json: print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=1))
            elif a.cmd=='projects':
                print(f"registry: {result['registry']}");print(f"default: {result['default']}")
                for r in result['projects']: print(f"{'*' if r['default'] else ' '} {r['name']:<20} r{r.get('revision','?')} {r.get('nodes','?')} nodes  {r['path']}{'' if r['exists'] else '  (missing)'}")
            else: print(compact(result,True))
            return 0
        a.file,selected_by=projects.resolve(a.file,a.project)
        if a.cmd=='serve': return serve(a.file,a.port)
        if a.cmd=='apply':
            ops=json.load(sys.stdin) if a.operations=='-' else json.loads(Path(a.operations).read_text());result=apply(a.file,ops,a.actor,a.reason,a.expect)
        else:
            g=load(a.file)
            if a.cmd=='evaluate':
                result=tracecheck.evaluate(g,resolve(g,a.claim),resolve(g,a.trace))
                if a.save is not None: result=save_evaluation(a.file,g,result,a.save or None,a.actor)
            elif a.cmd=='readiness': result=dependency.readiness(g,resolve(g,a.id))
            elif a.cmd=='impact': result=dependency.impact(g,[resolve(g,a.id)],a.limit,a.offset,a.path_limit)
            elif a.cmd=='export': result=g
            elif a.cmd=='overview': result=overview(g)
            elif a.cmd=='questions': result=questions(g,a.limit,a.historical)
            elif a.cmd=='check': result=check(g)
            elif a.cmd=='anchors': result={'revision':g['revision'],'nodes':{i:n for i,n in sorted(g['nodes'].items()) if n['type'] in ('entity','operation')}}
            elif a.cmd=='review': result=review(g,resolve(g,a.id) if a.id else None,a.limit,a.edge_limit)
            elif a.cmd=='types': result={k:g[k] for k in ('node_types','edge_types')}
            elif a.cmd=='search': result=search(g,a.query,a.limit)
            elif a.cmd in ('walk','neighbors'): result=walk(g,a.id,a.depth,a.direction,a.limit,a.edge_limit,not a.historical,a.anchors,a.relations)
            elif a.cmd=='node':
                nid=resolve(g,a.id);r=walk(g,nid,1,limit=200,edge_limit=500,current=not a.historical);result={'revision':g['revision'],'nodes':{nid:g['nodes'][nid]},'edges':{i:e for i,e in r['edges'].items() if nid in (e['from'],e['to'])},'neighbor_bodies':'omitted; use walk','truncated':r['truncated'],'edge_truncated':r['edge_truncated']}
            else: result=history(g,a.limit,a.full)
        if a.cmd!='apply': result=tracecheck.annotate(g,result)
        if not a.full and a.cmd in ('node','walk','neighbors','search','review','questions','anchors'): result=compact_read(result,g)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')) if a.json or a.cmd=='export' else compact(result,a.full))
    except (GraphError,projects.ProjectError,ValueError,KeyError,OSError,TypeError) as e: print('error: '+str(e),file=sys.stderr); return 1
    return 0
if __name__=='__main__': sys.exit(main())
