"""Small explicit authority/cardinality fragment. No prose inference or universal proof.

Scopes are named finite sets, or have explicit subset/disjoint/nonempty facts.
Unknowns remain unknown. Results describe the supplied structured patterns only.
"""
from itertools import combinations
import json

VERSION = 'formal-fragment/2'

def result(outcome, **data):
    return {'outcome': outcome, 'checker_version': VERSION, **data}

def _closure(start, pairs):
    seen = {start}
    while True:
        more = {b for a, b in pairs if a in seen} - seen
        if not more: return seen
        seen.update(more)

def scope_overlap(a, b, model):
    scopes = model.get('scopes', {})
    if a not in scopes or b not in scopes:
        return result('not-checked', reason='unsupported scope semantics')
    subset = model.get('scope_subset', [])
    for x, y in subset:
        if x == y or x in _closure(y, subset):
            return result('schema-error', reason='strict scope containment cycle')
    def members(s):
        v = scopes[s]
        return v.get('members') if isinstance(v, dict) else None
    am, bm = members(a), members(b)
    if am is not None and bm is not None:
        overlap = sorted(set(am) & set(bm))
        return result('overlap' if overlap else 'no-overlap', witnesses=overlap)
    aa, bb = _closure(a, subset), _closure(b, subset)
    for x, y in model.get('scope_disjoint', []):
        if (x in aa and y in bb) or (y in aa and x in bb):
            return result('no-overlap', witnesses=[x, y])
    lower = a if b in aa else b if a in bb else None
    if lower is not None:
        definition = scopes[lower]
        if isinstance(definition, dict) and definition.get('nonempty') is True:
            return result('overlap', witnesses=[{'nonempty_scope': lower, 'contained_in': [a, b]}])
        return result('overlap-unknown', reason='scope may be empty')
    for entry in model.get('scope_overlap', []):
        if set(entry.get('scopes', [])) == {a, b} and entry.get('witness') is not None:
            return result('overlap', witnesses=[entry['witness']])
    return result('overlap-unknown', reason='no declared overlap witness')

def _disjoint(a, b, model):
    return any(set(pair) == {a, b} for pair in model.get('role_disjoint', []))

def _actor_relation(a, b, model):
    """Relationship between actors selected by policies; absent roles != disjoint."""
    if a.get('actor') and b.get('actor'):
        return 'same' if a['actor'] == b['actor'] else 'disjoint'
    if a.get('role') and b.get('role'):
        if a['role'] == b['role']: return 'same'
        return 'disjoint' if _disjoint(a['role'], b['role'], model) else 'unknown'
    role, actor = (a.get('role'), b.get('actor')) if a.get('role') else (b.get('role'), a.get('actor'))
    definition = model.get('actors', {}).get(actor, {})
    if role in definition.get('roles', []): return 'same'
    if definition.get('roles_complete') is True: return 'disjoint'
    if any(_disjoint(role, r, model) for r in definition.get('roles', [])): return 'disjoint'
    return 'unknown'

def compare_authority(a, b, model):
    if a.get('operation') != b.get('operation'):
        return result('independent', reason='different operations; no implication declared')
    overlap = scope_overlap(a.get('scope'), b.get('scope'), model)
    if overlap['outcome'] != 'overlap': return overlap
    ma, mb = a.get('modality'), b.get('modality')
    if ma not in ('only','may','must','never') or mb not in ('only','may','must','never'):
        return result('not-checked', reason='unsupported modality')
    relation = _actor_relation(a, b, model)
    witness = {'operation': a['operation'], 'scope': overlap.get('witnesses'),
               'selectors': [{k:p[k] for k in ('role','actor') if k in p} for p in (a,b)]}
    if ma == mb == 'only':
        return result('no-inconsistency-established', reason='restrictions do not require an event or permission',
                      possible_overconstraint=relation == 'disjoint', witness=witness)
    if 'only' in (ma, mb):
        positive = b if ma == 'only' else a
        if positive.get('modality') in ('may','must'):
            if relation == 'disjoint': return result('policy-conflict', witness=witness)
            if relation == 'unknown': return result('role-overlap-unknown', witness=witness)
        return result('compatible', witness=witness)
    if 'never' in (ma, mb) and any(m in ('may','must') for m in (ma,mb)):
        common=[actor for actor,definition in model.get('actors',{}).items() if a.get('role') and b.get('role') and a['role'] in definition.get('roles',[]) and b['role'] in definition.get('roles',[])]
        if common: return result('policy-conflict',witness={**witness,'actors':sorted(common)})
        if relation == 'same': return result('policy-conflict', witness=witness)
        if relation == 'unknown': return result('role-overlap-unknown', witness=witness)
    return result('compatible', witness=witness)

def _bounds(pattern):
    lo, hi = pattern.get('min', 0), pattern.get('max')
    if isinstance(lo, bool) or not isinstance(lo,int) or lo < 0:
        raise ValueError('min must be a nonnegative integer')
    if hi is not None and (isinstance(hi,bool) or not isinstance(hi,int) or hi < lo):
        raise ValueError('max must be null or an integer >= min')
    return lo, hi

def compare_cardinality(a, b, model):
    sa, sb = a.get('slot', {}), b.get('slot', {})
    required = ('subject_type','relation','target_type','direction','identity_key','count')
    if any(k not in s or s[k] is None for s in (sa,sb) for k in required):
        return result('insufficient-information', reason='slot identity or semantics undeclared')
    if any(sa[k] != sb[k] for k in required):
        return result('independent', reason='different relation slots; equivalence not declared')
    if sa['count'] != 'distinct': return result('not-checked', reason='unsupported count semantics')
    overlap = scope_overlap(a.get('scope'), b.get('scope'), model)
    if overlap['outcome'] != 'overlap': return overlap
    try: al, ah = _bounds(a); bl, bh = _bounds(b)
    except ValueError as exc: return result('schema-error', reason=str(exc))
    lo = max(al, bl)
    hi = min([n for n in (ah,bh) if n is not None], default=None)
    if hi is None or lo <= hi: return result('compatible', intersection=[lo,hi])
    subjects = [s for s in model.get('subjects', []) if s.get('type') == sa['subject_type']
                and a['scope'] in s.get('scopes',[]) and b['scope'] in s.get('scopes',[])]
    if subjects:
        return result('cardinality-conflict', intersection=None, witnesses=subjects,
                      reason='empty interval intersection for an existing subject')
    return result('no-inconsistency-established', intersection=None,
                  reason='empty subject domain satisfies both universal bounds',
                  conditional_unsatisfiability=True)

def validate_model(model):
    errors=[]
    scopes=model.get('scopes',{})
    subset=model.get('scope_subset',[])
    for a,b in subset:
        if a not in scopes or b not in scopes: errors.append('undeclared scope in subset')
        elif a==b or a in _closure(b,subset): errors.append('strict scope containment cycle')
        else:
            am,bm=scopes[a].get('members'),scopes[b].get('members')
            if am is not None and bm is not None and not set(am)<set(bm): errors.append('finite members violate strict containment')
    for a,b in model.get('scope_disjoint',[]):
        if a not in scopes or b not in scopes: errors.append('undeclared scope in disjointness')
        elif scopes[a].get('members') is not None and scopes[b].get('members') is not None and set(scopes[a]['members'])&set(scopes[b]['members']): errors.append('finite members violate disjointness')
    for definition in model.get('actors',{}).values():
        for a,b in model.get('role_disjoint',[]):
            if a in definition.get('roles',[]) and b in definition.get('roles',[]): errors.append('actor violates declared role disjointness')
    return sorted(set(errors))

def _valid_authority(pattern):
    return bool(pattern.get('operation')) and bool(pattern.get('scope')) and (bool(pattern.get('actor')) != bool(pattern.get('role')))

def compare_patterns(a, b, model=None):
    model = model or {}
    errors=validate_model(model)
    if errors: return result('schema-error', diagnostics=errors)
    if a.get('kind')=='authority' and (not _valid_authority(a) or not _valid_authority(b)):
        return result('schema-error', reason='authority requires operation, scope and exactly one actor or role selector')
    if a.get('kind') != b.get('kind'): return result('independent', reason='different semantic fragments')
    if a.get('kind') == 'authority': return compare_authority(a,b,model)
    if a.get('kind') == 'cardinality': return compare_cardinality(a,b,model)
    return result('not-checked', reason='unsupported comparison fragment')

def compare_graph(graph):
    """Compare only current accepted structured policies; preserve originals unchanged."""
    nodes = graph.get('nodes', {})
    selected = [(i,n) for i,n in sorted(nodes.items()) if isinstance(n,dict) and n.get('type') == 'claim'
                and n.get('status') == 'accepted'
                and n.get('meta',{}).get('review_state','current') == 'current'
                and isinstance(n.get('pattern'),dict) and n['pattern'].get('kind') in ('authority','cardinality')]
    findings=[]
    for (aid,a),(bid,b) in combinations(selected,2):
        checked=compare_patterns(a['pattern'],b['pattern'],graph.get('formal_model',{}))
        if checked['outcome'] not in ('independent','compatible'):
            findings.append({'code':checked['outcome'],'nodes':[aid,bid], 'computed_revision':graph.get('revision'),
                             'pattern_standing':{i:n.get('meta',{}).get('pattern_standing','unspecified') for i,n in ((aid,a),(bid,b))},
                             'formalization_scope':'comparison of supplied patterns only; acceptance of prose does not accept extraction', **checked})
    return findings

def evaluate_cardinality(pattern, reports, complete=False):
    slot = pattern.get('slot',{})
    keys = slot.get('identity_key')
    if not isinstance(keys,list) or not keys:
        return result('insufficient-information', reason='identity-gap', question='Which fields define identity in this model?')
    if slot.get('count') != 'distinct': return result('not-checked', reason='unsupported count semantics')
    try: lo,hi = _bounds(pattern)
    except ValueError as exc: return result('schema-error',reason=str(exc))
    grouped={}; diagnostics=[]
    for i,report in enumerate(reports):
        subject=report.get('subject',{})
        if any(k not in subject for k in keys):
            diagnostics.append({'index':i,'reason':'missing identity field'}); continue
        key=json.dumps([subject[k] for k in keys],sort_keys=True)
        group=grouped.setdefault(key,{'identity':{k:subject[k] for k in keys},'owners':set(),'sources':[]})
        # An empty explicit report establishes a subject, not missing owners as zero.
        if report.get('target') is not None: group['owners'].add(report['target'])
        group['sources'].extend(report.get('sources',[]))
    outputs=[]
    for _,group in sorted(grouped.items()):
        count=len(group.pop('owners'))
        outcome='violates' if hi is not None and count>hi else ('satisfies' if lo<=count and (hi is None or count<=hi) else 'violates') if complete else 'insufficient-information'
        outputs.append({**group,'distinct_count':count,'outcome':outcome})
    outcome='violates' if any(g['outcome']=='violates' for g in outputs) else 'insufficient-information' if diagnostics or not outputs or any(g['outcome']=='insufficient-information' for g in outputs) else 'satisfies'
    return result(outcome,subjects=outputs,diagnostics=diagnostics,scope='supplied reports and declared completeness only')

def evaluate_authority(pattern, trace):
    """Finite recorded event check; normative may does not require an occurrence."""
    if pattern.get('kind') != 'authority' or pattern.get('scope') not in ('all','after_attempt_ended'):
        return result('not-checked',reason='unsupported scope semantics')
    modality=pattern.get('modality')
    if modality=='must': return result('not-checked',reason='use bounded obligation pattern for timing')
    if modality not in ('only','never','may'): return result('not-checked',reason='unsupported modality')
    events=trace.get('events',[]); indexed={e.get('id'):(i,e) for i,e in enumerate(events)}
    ids=[e.get('id') for e in events]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        return result('insufficient-information',reason='missing or duplicate event identity')
    witnesses=[]; diagnostics=[]; checked=[]
    for i,e in enumerate(events):
        if e.get('operation')!=pattern.get('operation'): continue
        if pattern['scope']=='after_attempt_ended':
            entry=indexed.get(e.get('after'))
            if not entry or entry[0]>=i or entry[1].get('operation')!='end-attempt' or not e.get('attempt') or entry[1].get('attempt')!=e['attempt']:
                diagnostics.append({'event':e.get('id'),'reason':'missing or invalid temporal link'}); continue
        if not isinstance(e.get('actor'),str) or not e['actor']:
            diagnostics.append({'event':e.get('id'),'reason':'missing actor identity'}); continue
        roles=e.get('actor_roles')
        if roles is None and e.get('actor_role') is not None: roles=[e['actor_role']]
        match=e.get('actor')==pattern['actor'] if pattern.get('actor') else pattern.get('role') in roles if isinstance(roles,list) else None
        if match is None:
            diagnostics.append({'event':e.get('id'),'reason':'missing event-time roles'}); continue
        checked.append(e.get('id'))
        if (modality=='only' and not match) or (modality=='never' and match): witnesses.append(e.get('id'))
    outcome='violates' if witnesses else 'insufficient-information' if diagnostics or trace.get('complete') is not True else 'satisfies'
    permission_only=modality=='may'
    vacuous=outcome=='satisfies' and not checked and not permission_only
    if vacuous:
        diagnostics.append({'code':'no-matching-event','reason':'No event was checked in the supplied scope; logical universal satisfaction is vacuous, not empirical support.'})
    if permission_only:
        diagnostics.append({'code':'permission-only','reason':'Permission does not require an occurrence and cannot be established merely by observing an event.'})
    basis='permission-only' if permission_only else 'vacuous-universal' if vacuous else 'recorded-events' if checked else 'incomplete'
    return result(outcome,witnesses=witnesses,diagnostics=diagnostics,checked_events=checked,
                  vacuous=vacuous,permission_only=permission_only,evidence_basis=basis,
                  empirical_support=False if vacuous or permission_only else None,
                  scope='Supplied finite trace only. Vacuous satisfaction is not empirical support; may does not imply liveness or prove permission from observed behavior.')

def evaluate_obligation(pattern, trace):
    """Every trigger requires a linked response within N logical ticks."""
    if pattern.get('kind')!='bounded_obligation': return result('not-checked',reason='unsupported obligation semantics')
    delay=pattern.get('within_ticks')
    if delay is None: return result('insufficient-information',reason='unbounded eventuality cannot be falsified by finite prefix')
    if isinstance(delay,bool) or not isinstance(delay,int) or delay<0: return result('schema-error',reason='invalid logical bound')
    horizon=trace.get('complete_through_tick'); pending=[]; witnesses=[]; satisfied=[]
    if horizon is not None and (isinstance(horizon,bool) or not isinstance(horizon,int)):
        return result('schema-error',reason='horizon must be an integer logical tick')
    for e in trace.get('events',[]):
        if e.get('operation')!=pattern.get('trigger'): continue
        if isinstance(e.get('tick'),bool) or not isinstance(e.get('tick'),int): pending.append({'event':e.get('id'),'reason':'missing trigger tick'}); continue
        deadline=e['tick']+delay
        responses=[r for r in trace.get('events',[]) if r.get('operation')==pattern.get('response') and r.get('responds_to')==e.get('id')]
        found=any(not isinstance(r.get('tick'),bool) and isinstance(r.get('tick'),int) and e['tick']<=r['tick']<=deadline and (not pattern.get('role') or pattern['role'] in r.get('actor_roles',[])) for r in responses)
        uncertain=any(isinstance(r.get('tick'),bool) or not isinstance(r.get('tick'),int) or (pattern.get('role') and 'actor_roles' not in r) for r in responses)
        if found: satisfied.append(e.get('id'))
        elif uncertain: pending.append({'event':e.get('id'),'reason':'incomplete response timing or role'})
        elif isinstance(horizon,int) and horizon>=deadline:
            witnesses.append({'event':e.get('id'),'deadline':deadline,'complete_through_tick':horizon})
        else: pending.append({'event':e.get('id'),'deadline':deadline})
    outcome='violates' if witnesses else 'insufficient-information' if pending else 'satisfies'
    return result(outcome,witnesses=witnesses,pending=pending,satisfied=satisfied,scope='bounded linked obligations in supplied trace only')

def review_formalization(proposed, authorized):
    """Compare agent-extracted source coordinates, never infer them from prose."""
    widened=[k for k in ('operation','scope','modality','role') if authorized.get(k)!=proposed.get(k)]
    return result('extraction-review' if widened else 'coordinates-match',fields=widened,
                  pattern_standing='proposed' if widened else 'review-required',
                  reason='coordinate comparison only; prose fidelity still requires review')

def references(pattern):
    """Declared IDs, classified by namespace. Scope IDs belong to formal_model."""
    out={'nodes':[], 'scopes':[]}
    for key in ('operation','role','allowed_role','actor','trigger','response'):
        if isinstance(pattern.get(key),str): out['nodes'].append(pattern[key])
    slot=pattern.get('slot',{})
    for key in ('subject_type','target_type'):
        if isinstance(slot.get(key),str): out['nodes'].append(slot[key])
    # relation is a vocabulary ID, not a graph edge instance ID.
    out['relations']=[slot['relation']] if isinstance(slot.get('relation'),str) else []
    if isinstance(pattern.get('scope'),str): out['scopes'].append(pattern['scope'])
    return {k:sorted(set(v)) for k,v in out.items()}


# Public boundaries return an explicit invalid-input result for malformed JSON
# shapes; unsupported semantics remain separate outcomes in each implementation.
def _guard(function):
    from functools import wraps
    @wraps(function)
    def guarded(*args,**kwargs):
        try: return function(*args,**kwargs)
        except (TypeError,ValueError,KeyError,AttributeError) as exc:
            return result('schema-error',reason='invalid structured input',detail=str(exc))
    return guarded

for _name in ('compare_patterns','evaluate_authority','evaluate_cardinality','evaluate_obligation','review_formalization','scope_overlap'):
    globals()[_name]=_guard(globals()[_name])
