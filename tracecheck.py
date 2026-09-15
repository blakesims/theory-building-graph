"""One finite-trace pattern checker. Outcomes concern the pattern, never the whole claim."""
import copy, hashlib, json
CHECKER_VERSION = 'exclusive-actor/1'
SCOPE_NOTE = 'Checks the recorded chooser role after a linked ended attempt. Does not check consultation, liveness, trace truth, or all possible behavior.'

def fingerprint(node):
    content=copy.deepcopy(node)
    if isinstance(content.get('meta'),dict):
        for field in ('review_state','review_reason'): content['meta'].pop(field,None)
        if not content['meta']: content.pop('meta')
    content.pop('result_state',None)
    return hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def evaluate(g,claim_id,trace_id):
    claim,trace=g['nodes'][claim_id],g['nodes'][trace_id]
    result={'claim':claim_id,'trace':trace_id,'outcome':'not-checked','witnesses':[],'diagnostics':[],'checked_events':[],'out_of_scope_events':[],
            'input_fingerprints':{claim_id:fingerprint(claim),trace_id:fingerprint(trace)},'computed_revision':g['revision'],'checker_version':CHECKER_VERSION,
            'scope':SCOPE_NOTE,'synthetic':bool((trace.get('meta') or {}).get('synthetic'))}
    def dependency(i):
        if isinstance(i,str): result['input_fingerprints'][i]=fingerprint(g['nodes'][i]) if i in g['nodes'] else None
    def is_role(i):
        n=g['nodes'].get(i,{}) if isinstance(i,str) else {}
        return n.get('type')=='entity' and (n.get('meta') or {}).get('kind')=='agent-role'
    def diagnostic(code,event=None,detail=None):
        result['diagnostics'].append({'code':code,**({'event':event} if event is not None else {}),**({'detail':detail} if detail else {})})
    pattern=claim.get('pattern')
    if claim.get('type')!='claim' or not isinstance(pattern,dict):
        diagnostic('no-supported-pattern'); return result
    if pattern.get('kind')!='exclusive_actor' or pattern.get('scope')!='after_attempt_ended' or pattern.get('operation')!='choose-work':
        diagnostic('unsupported-pattern'); return result
    allowed=pattern.get('allowed_role')
    dependency(allowed)
    for operation in ('choose-work','end-attempt'): dependency(operation)
    if any(g['nodes'].get(op,{}).get('type')!='operation' for op in ('choose-work','end-attempt')):
        diagnostic('unsupported-operation-reference'); return result
    if not is_role(allowed):
        diagnostic('unsupported-allowed-role'); return result
    payload=trace.get('trace')
    if trace.get('type')!='trace' or not isinstance(payload,dict) or not isinstance(payload.get('events'),list):
        result['outcome']='insufficient-information'; diagnostic('missing-trace-events'); return result
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
    return result

def result_state(g,result):
    expected=result.get('input_fingerprints',{})
    if not expected or result.get('checker_version')!=CHECKER_VERSION:return 'stale'
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
