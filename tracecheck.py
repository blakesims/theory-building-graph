"""One finite-trace pattern checker. Outcomes concern the pattern, never the whole claim."""
import copy, hashlib, json
import formalcheck
CHECKER_VERSION = 'exclusive-actor/2'
SCOPE_NOTE = 'Checks the recorded chooser role after a linked ended attempt. Does not check consultation, liveness, trace truth, or all possible behavior.'

def fingerprint(node):
    content=copy.deepcopy(node)
    if isinstance(content.get('meta'),dict):
        for field in ('review_state','review_reason','layout','position','color','reviewed_inputs','reviewed_input_versions','review_roots','sources','aliases','title'): content['meta'].pop(field,None)
        if not content['meta']: content.pop('meta')
    content.pop('result_state',None)
    for field in ('layout','position','color','reviewed_inputs','reviewed_input_versions','review_roots','sources','aliases','title','semantic_version'): content.pop(field,None)
    return hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def provenance(g, roots):
    """Declared provenance only: adjacency and supporting reasons are not dependencies.

    Edges are captured as a closure signature too, so replacing a source edge stales
    a result even when neither endpoint's content changes.
    """
    seen=set(); links={}; missing=set(); pending=list(roots)
    while pending:
        current=pending.pop()
        if not isinstance(current,str) or current in seen: continue
        seen.add(current)
        node=g.get('nodes',{}).get(current)
        if node is None: missing.add(current); continue
        for edge_id,edge in sorted(g.get('edges',{}).items()):
            if edge.get('from')==current and (edge.get('type') in ('extracted-from','depends-on') or g.get('edge_types',{}).get(edge.get('type'),{}).get('invalidation')=='dependent-to-prerequisite'):
                links[edge_id]=fingerprint(edge)
                pending.append(edge.get('to'))
        declared=node.get('provenance',{})
        if isinstance(declared,dict):
            for source in declared.get('sources',[]):
                pending.append(source if isinstance(source,str) else source.get('id') if isinstance(source,dict) else None)
    return {'nodes':sorted(seen),'missing':sorted(missing),'edges':links,
            'fingerprints':{i:fingerprint(g['nodes'][i]) if i in g['nodes'] else None for i in sorted(seen)}}

def classify(g, result):
    trace=g['nodes'].get(result.get('trace'),{})
    claim=g['nodes'].get(result.get('claim'),{})
    polarity=trace.get('polarity',(trace.get('meta') or {}).get('polarity','unspecified'))
    findings=[]
    if polarity=='intended' and result['outcome']=='violates' and claim.get('status')=='accepted':
        findings.append({'code':'intention-theory-mismatch','possible_causes':['claim wrong','case mislabeled','extraction wrong']})
    if polarity=='defect' and result['outcome']=='satisfies':
        findings.append({'code':'known-defect-unexplained','scope':'The checked fragment does not explain this defect; this is not a contradiction.'})
    return {'polarity':polarity,'findings':findings,
            'historical_behavior': 'not-established' if result.get('synthetic') else 'source-dependent',
            'reachability':{'outcome':'not-checked','reason':'No rewrite reachability engine is implemented. Explaining an observed defect requires implementation rules, not necessarily intended rules.'}}

def evaluate(g,claim_id,trace_id):
    claim,trace=g['nodes'][claim_id],g['nodes'][trace_id]
    result={'claim':claim_id,'trace':trace_id,'outcome':'not-checked','witnesses':[],'diagnostics':[],'checked_events':[],'out_of_scope_events':[],
            'input_fingerprints':{claim_id:fingerprint(claim),trace_id:fingerprint(trace)},'computed_revision':g['revision'],'checker_version':CHECKER_VERSION,
            'scope':SCOPE_NOTE,'synthetic':bool((trace.get('meta') or {}).get('synthetic'))}
    declared=provenance(g,[claim_id,trace_id])
    result['claim_standing']=claim.get('status','unspecified')
    result['pattern_standing']=(claim.get('meta') or {}).get('pattern_standing','unspecified')
    result['provenance']=declared
    result['input_fingerprints'].update(declared['fingerprints'])
    result['provenance_roots']=[claim_id,trace_id]
    result['synthetic']=result['synthetic'] or any((g['nodes'].get(i,{}).get('meta') or {}).get('synthetic') is True for i in declared['nodes'])
    def finish():
        result['assessment']=classify(g,result)
        return result
    def dependency(i):
        if isinstance(i,str): result['input_fingerprints'][i]=fingerprint(g['nodes'][i]) if i in g['nodes'] else None
    def is_role(i):
        n=g['nodes'].get(i,{}) if isinstance(i,str) else {}
        return n.get('type')=='entity' and (n.get('meta') or {}).get('kind')=='agent-role'
    def diagnostic(code,event=None,detail=None):
        result['diagnostics'].append({'code':code,**({'event':event} if event is not None else {}),**({'detail':detail} if detail else {})})
    for missing in declared['missing']: diagnostic('missing-provenance-input',detail=missing)
    pattern=claim.get('pattern')
    if claim.get('type')!='claim' or not isinstance(pattern,dict):
        diagnostic('no-supported-pattern'); return finish()
    if pattern.get('kind') in ('authority','cardinality','bounded_obligation'):
        refs=formalcheck.references(pattern)
        for referenced in refs['nodes']: dependency(referenced)
        missing=[i for i in refs['nodes'] if i not in g['nodes']]
        missing += ['relation:'+i for i in refs['relations'] if i not in g.get('edge_types',{})]
        scopes=g.get('formal_model',{}).get('scopes',{})
        missing += ['scope:'+i for i in refs['scopes'] if i not in ('all','after_attempt_ended') and i not in scopes]
        result['definition_fingerprints']={'formal_model':fingerprint(g.get('formal_model',{})), 'edge_types':fingerprint(g.get('edge_types',{}))}
        if missing:
            diagnostic('undeclared-pattern-reference',detail=', '.join(missing)); return finish()
        payload=trace.get('trace',{})
        if pattern['kind']=='authority': checked=formalcheck.evaluate_authority(pattern,payload)
        elif pattern['kind']=='cardinality': checked=formalcheck.evaluate_cardinality(pattern,payload.get('reports',[]),payload.get('complete') is True)
        else: checked=formalcheck.evaluate_obligation(pattern,payload)
        result.update(checked)
        result['fragment_version']=formalcheck.VERSION
        result['checker_version']=CHECKER_VERSION
        if result['outcome']=='schema-error': result['outcome']='not-checked'
        return finish()
    if pattern.get('kind')!='exclusive_actor' or pattern.get('scope')!='after_attempt_ended' or pattern.get('operation')!='choose-work':
        diagnostic('unsupported-pattern'); return finish()
    allowed=pattern.get('allowed_role')
    dependency(allowed)
    for operation in ('choose-work','end-attempt'): dependency(operation)
    if any(g['nodes'].get(op,{}).get('type')!='operation' for op in ('choose-work','end-attempt')):
        diagnostic('unsupported-operation-reference'); return finish()
    if not is_role(allowed):
        diagnostic('unsupported-allowed-role'); return finish()
    payload=trace.get('trace')
    if trace.get('type')!='trace' or not isinstance(payload,dict) or not isinstance(payload.get('events'),list):
        result['outcome']='insufficient-information'; diagnostic('missing-trace-events'); return finish()
    uncertain=False
    if payload.get('complete') is not True:
        uncertain=True; diagnostic('trace-completeness-unspecified','', 'Set trace.complete=true only for the supplied bounded trace, not all system behavior.')
    events=payload['events']; indexed={}; duplicate=set()
    for i,event in enumerate(events):
        if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not event['id']:
            uncertain=True; diagnostic('invalid-event-id',detail='Event at index '+str(i));continue
        if event['id'] in indexed: duplicate.add(event['id']); uncertain=True;diagnostic('duplicate-event-id',event['id'])
        indexed[event['id']]=(i,event)
        dependency(event.get('actor_role'))
        dependency(event.get('operation'))
    targets=0
    for i,event in enumerate(events):
        if not isinstance(event,dict): continue
        eid=event.get('id')
        if not event.get('operation'):
            uncertain=True;diagnostic('missing-operation',eid);continue
        if event['operation']!=pattern['operation']:
            result['out_of_scope_events'].append(eid);continue
        targets+=1
        if not isinstance(eid,str) or not eid or eid in duplicate: continue
        after=event.get('after')
        if not isinstance(after,str) or after not in indexed or after in duplicate:
            uncertain=True; diagnostic('missing-or-ambiguous-end-link',eid);continue
        before_index,end=indexed[after]
        if end.get('operation')!='end-attempt':
            uncertain=True;diagnostic('link-is-not-ended-attempt',eid);continue
        if before_index>=i:
            uncertain=True;diagnostic('end-link-not-earlier',eid);continue
        if not isinstance(event.get('attempt'),str) or not event['attempt'] or not isinstance(end.get('attempt'),str) or not end['attempt']:
            uncertain=True;diagnostic('missing-attempt-identity',eid);continue
        if event['attempt']!=end['attempt']:
            uncertain=True;diagnostic('end-link-different-attempt',eid);continue
        role=event.get('actor_role')
        if not is_role(role):
            uncertain=True;diagnostic('missing-or-unknown-event-role',eid);continue
        if not isinstance(event.get('actor'),str) or not event['actor']:
            uncertain=True;diagnostic('missing-event-actor',eid);continue
        result['checked_events'].append(eid)
        if role!=allowed:
            result['witnesses'].append({'event':eid,'actor':event['actor'],'actor_role':role,'allowed_role':allowed,'attempt':event['attempt'],'after':after})
    if result['witnesses']: result['outcome']='violates'
    elif uncertain: result['outcome']='insufficient-information'
    elif result['checked_events']: result['outcome']='satisfies'
    else:
        result['outcome']='insufficient-information';diagnostic('no-scoped-choose-event',detail='Absence of a checked event is not treated as vacuous satisfaction.')
    return finish()

def result_state(g,result):
    expected=result.get('input_fingerprints',{})
    if result.get('fragment_version') and result['fragment_version']!=formalcheck.VERSION:return 'stale'
    if not expected or result.get('checker_version')!=CHECKER_VERSION:return 'stale'
    if any(fingerprint(g.get(key,{}))!=expected for key,expected in result.get('definition_fingerprints',{}).items()): return 'stale'
    if result.get('provenance_roots') and provenance(g,result['provenance_roots']) != result.get('provenance'): return 'stale'
    return 'current' if all((i not in g['nodes'] if f is None else i in g['nodes'] and fingerprint(g['nodes'][i])==f) for i,f in expected.items()) else 'stale'

def evaluations(g,node_id=None):
    found=[]
    for i,n in g['nodes'].items():
        if n.get('type')!='check-result' or not isinstance(n.get('result'),dict):continue
        r=n['result']
        if node_id and node_id not in (i,r.get('claim'),r.get('trace')):continue
        found.append({'id':i,**r,'result_state':result_state(g,r)})
    return {'revision':g['revision'],'results':found}

def annotate(g,response):
    """Attach derived freshness on response copies only, never canonical writes."""
    if isinstance(response.get('nodes'),dict):
        response={**response,'nodes':{i:{**n,**({'result_state':result_state(g,n['result'])} if n.get('type')=='check-result' and isinstance(n.get('result'),dict) else {})} for i,n in response['nodes'].items()}}
    elif response.get('type')=='check-result' and isinstance(response.get('result'),dict):
        response={**response,'result_state':result_state(g,response['result'])}
    return response
