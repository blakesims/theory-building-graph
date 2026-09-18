"""Finite, explicit theory-model replay. This is not a runtime for the modelled system.

A transition has an event kind, guards and ordered set/create/append/delete
mutations. Values support {$arg: name}, {$state: path}, {$event: field}.
The model is authored data; the engine never extracts rules from prose.
Each event commits atomically and failed events leave state/revision untouched.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

VERSION='finite-replay/1'
MISSING=object()

class ReplayError(ValueError):
    pass

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def value(spec,state,event):
    if isinstance(spec,dict):
        if len(spec)==1 and '$arg' in spec:
            key=spec['$arg']
            if key not in event.get('args',{}): raise ReplayError('missing-argument:'+str(key))
            return copy.deepcopy(event['args'][key])
        if len(spec)==1 and '$event' in spec:
            if spec['$event'] not in event: raise ReplayError('missing-event-field:'+spec['$event'])
            return copy.deepcopy(event[spec['$event']])
        if len(spec)==1 and '$state' in spec:
            result=read(state,path_value(spec['$state'],state,event))
            if result is MISSING: raise ReplayError('missing-state-reference')
            return copy.deepcopy(result)
        return {k:value(v,state,event) for k,v in spec.items()}
    if isinstance(spec,list): return [value(v,state,event) for v in spec]
    return copy.deepcopy(spec)

def path_value(path,state,event):
    if not isinstance(path,list) or not path: raise ReplayError('path-must-be-nonempty-list')
    result=[value(p,state,event) for p in path]
    if any(not isinstance(p,str) or not p for p in result): raise ReplayError('path-segments-must-be-strings')
    return result

def read(state,path):
    current=state
    for part in path:
        if not isinstance(current,dict) or part not in current:return MISSING
        current=current[part]
    return current

def guard_holds(guard,state,event):
    allowed={'path','equals','not_equals','exists','includes'}
    if set(guard)-allowed: raise ReplayError('unsupported-guard')
    actual=read(state,path_value(guard['path'],state,event))
    operators=[k for k in ('equals','not_equals','exists','includes') if k in guard]
    if len(operators)!=1: raise ReplayError('guard-needs-one-operator')
    op=operators[0];expected=value(guard[op],state,event)
    if op=='exists':return (actual is not MISSING)==expected
    if actual is MISSING:return False
    if op=='equals':return actual==expected
    if op=='not_equals':return actual!=expected
    if op=='includes':return isinstance(actual,(list,dict,str)) and expected in actual
    raise ReplayError('unsupported-guard')

def mutate(state,effect,event):
    op=effect.get('op');path=path_value(effect.get('path'),state,event)
    parent=read(state,path[:-1]) if len(path)>1 else state
    if not isinstance(parent,dict):raise ReplayError('missing-parent')
    key=path[-1]
    if op=='create':
        if key in parent:raise ReplayError('already-exists')
        parent[key]=value(effect['value'],state,event)
    elif op=='set':
        if key not in parent:raise ReplayError('missing-update-target')
        parent[key]=value(effect['value'],state,event)
    elif op=='delete':
        if key not in parent:raise ReplayError('missing-delete-target')
        del parent[key]
    elif op=='append':
        if not isinstance(parent.get(key),list):raise ReplayError('append-requires-list')
        parent[key].append(value(effect['value'],state,event))
    else:raise ReplayError('unsupported-effect:'+str(op))

def run(model,events,checkpoint=None):
    """Return exact finite state/receipts; resume only against the same model hash."""
    fingerprint=digest(model)
    if checkpoint is not None:
        if checkpoint.get('model_hash')!=fingerprint:raise ReplayError('checkpoint-model-mismatch')
        state=copy.deepcopy(checkpoint['state']);revision=checkpoint['revision'];seen=set(checkpoint['seen'])
    else:state=copy.deepcopy(model.get('initial',{}));revision=0;seen=set()
    receipts=[];rules=model.get('rules',[])
    if len({r.get('id') for r in rules})!=len(rules) or any(not r.get('id') for r in rules):raise ReplayError('unique-rule-ids-required')
    for event in events:
        before=digest(state);eid=event.get('id');receipt={'event':eid,'before_revision':revision,'before_hash':before}
        try:
            if not isinstance(eid,str) or not eid:raise ReplayError('event-id-required')
            if eid in seen:raise ReplayError('duplicate-event')
            if 'expect_revision' in event and event['expect_revision']!=revision:raise ReplayError('stale-revision')
            candidates=[r for r in rules if r.get('on')==event.get('kind') and all(guard_holds(g,state,event) for g in r.get('guards',[]))]
            if len(candidates)!=1:raise ReplayError('no-enabled-rule' if not candidates else 'ambiguous-rules')
            rule=candidates[0];candidate=copy.deepcopy(state)
            for effect in rule.get('effects',[]):mutate(candidate,effect,event)
            state=candidate;revision+=1;seen.add(eid)
            receipt.update({'outcome':'applied','rule':rule['id']})
        except (ReplayError,KeyError,TypeError) as exc:
            receipt.update({'outcome':'rejected','reason':str(exc)})
        receipt.update({'after_revision':revision,'after_hash':digest(state),'state':copy.deepcopy(state)})
        receipts.append(receipt)
    return {'engine':VERSION,'model_hash':fingerprint,'revision':revision,'state':state,'seen':sorted(seen),'receipts':receipts,
            'scope':'Replay of explicitly authored finite transitions only; no proof of all executions, prose interpretation, liveness, or historical truth.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path);parser.add_argument('--compact',action='store_true')
    args=parser.parse_args();fixture=json.loads(args.fixture.read_text());result=run(fixture['model'],fixture['events'])
    if args.compact:result['receipts']=[{k:v for k,v in r.items() if k!='state'} for r in result['receipts']]
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if any(r['outcome']=='rejected' for r in result['receipts']) else 0

if __name__=='__main__':raise SystemExit(main())
