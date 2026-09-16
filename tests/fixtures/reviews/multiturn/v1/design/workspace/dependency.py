"""Explicit dependency, question and structural semantics (no prose interpretation)."""
import collections
import copy
import hashlib
import json

RETIRED = {'withdrawn', 'rejected', 'retired', 'superseded'}
SHAPES = {'verdict', 'condition', 'exploration'}
SEMANTIC_META = {'assumptions', 'enforcement', 'modality', 'answer_shape', 'required_parts',
                 'pattern_standing', 'pattern_scope', 'source_kind', 'synthetic', 'identity_key',
                 'roles', 'role', 'entity_kind', 'scope', 'polarity'}


def currency(node):
    return (node.get('meta') or {}).get('review_state', 'current')


def retired(node):
    return currency(node) == 'historical' or node.get('status') in RETIRED


def semantic(node):
    # Audit, rendering and review receipts never change the proposition itself.
    result = {k: v for k, v in node.items() if k not in {'meta', 'layout', 'position', 'color', 'semantic_version', 'result_state'}}
    result['meta'] = {k: v for k, v in (node.get('meta') or {}).items() if k in SEMANTIC_META}
    return result


def fingerprint(node):
    return hashlib.sha256(json.dumps(semantic(node), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def dependency_edges(g):
    for eid, e in sorted(g['edges'].items()):
        declaration = g['edge_types'].get(e['type'], {})
        if e['type'] in {'depends-on', 'extracted-from'} or declaration.get('invalidation') == 'dependent-to-prerequisite':
            yield eid, e


def adjacency(g):
    out = collections.defaultdict(list)
    for eid, e in dependency_edges(g):
        out[e['from']].append((eid, e['to']))
    return out



def affected_ids(g, roots):
    reverse=collections.defaultdict(list)
    for eid,e in dependency_edges(g): reverse[e['to']].append(e['from'])
    roots=set(roots); reached=set(roots); queue=collections.deque(sorted(roots))
    while queue:
        for other in reverse[queue.popleft()]:
            if other not in reached: reached.add(other); queue.append(other)
    return sorted(reached-roots)


def impact(g, roots, limit=100, offset=0, path_limit=8):
    """All reachable dependents; bounded path examples, never silently exponential output."""
    if limit < 1 or offset < 0 or path_limit < 1:
        raise ValueError('limit/path-limit must be positive and offset nonnegative')
    roots = sorted(set(roots))
    ids=affected_ids(g,roots)
    # Paths use dependent -> prerequisite orientation, and include edge identities.
    forward = adjacency(g)
    def paths(start):
        found = []
        pending = [(start, [start], [])]
        # A bounded exploration avoids exponential diamonds; the reachability list above is complete.
        visits = 0
        while pending and len(found) < path_limit and visits < 10000:
            node, nodes, edges = pending.pop(); visits += 1
            if node in roots:
                found.append({'nodes': nodes, 'edges': edges}); continue
            for eid, target in reversed(forward[node]):
                if target not in nodes:
                    pending.append((target, nodes + [target], edges + [eid]))
        return {'paths': found, 'paths_truncated': bool(pending)}
    selected = ids[offset:offset + limit]
    return {'roots': roots, 'total_affected': len(ids), 'affected': selected,
            'offset': offset, 'limit': limit, 'truncated': offset + limit < len(ids),
            'next_offset': offset + limit if offset + limit < len(ids) else None,
            'explanations': {n: paths(n) for n in selected}}


def resolution(g, nid):
    n = g['nodes'][nid]
    if retired(n):
        return {'resolution': 'retired', 'answers': [], 'unresolved': []}
    shape = n.get('answer_shape', (n.get('meta') or {}).get('answer_shape', 'verdict'))
    accepted, candidates, stale, partial = [], [], [], []
    diagnostics = []
    required = n.get('required_parts', (n.get('meta') or {}).get('required_parts', []))
    covered = set()
    for eid, e in sorted(g['edges'].items()):
        if e['type'] != 'answers' or e['to'] != nid:
            continue
        a = g['nodes'][e['from']]
        if retired(a):
            continue
        candidates.append(e['from'])
        if currency(a) != 'current':
            stale.append(e['from']); continue
        if a.get('status') != 'accepted':
            continue
        payload = e.get('answer', a.get('answer', {}))
        shaped = shape == 'verdict' or (shape == 'condition' and bool(payload.get('condition'))) or (shape == 'exploration' and bool(payload.get('findings')) and payload.get('complete') is True)
        if not shaped:
            diagnostics.append({'answer':e['from'],'reason':'unresolved-condition-hole' if shape=='condition' else 'unresolved-exploration-task'})
            continue
        if e.get('coverage') == 'full':
            accepted.append(e['from']); covered.update(required)
        elif e.get('coverage') == 'partial':
            partial.append(e['from']); covered.update(e.get('covers', []))
    if accepted: state = 'answered'
    elif partial: state = 'partial-answer'
    elif candidates: state = 'candidate-answer'
    else: state = 'open'
    return {'resolution': state, 'answer_shape': shape, 'answers': sorted(set(accepted + partial)),
            'candidates': sorted(set(candidates)), 'stale_answers': sorted(set(stale)),
            'unresolved': sorted(set(required) - covered), 'diagnostics':diagnostics, 'review_state': currency(n)}


def readiness(g, nid):
    if nid not in g['nodes']: raise ValueError('Unknown node: ' + nid)
    adj = adjacency(g)
    memo = {}
    chosen = collections.defaultdict(set)
    def visit(node, stack):
        if node in stack:
            return [{'node': node, 'reason': 'dependency-cycle', 'path': [node], 'cycle': stack[stack.index(node):] + [node]}]
        if node in memo: return copy.deepcopy(memo[node])
        blockers = []
        edges = [(eid, target) for eid, target in adj[node] if g['edges'][eid]['type'] == 'depends-on' or g['edge_types'][g['edges'][eid]['type']].get('readiness')]
        groups = collections.defaultdict(list)
        for eid, target in edges:
            edge = g['edges'][eid]
            n = g['nodes'][target]
            reasons = []
            if retired(n): reasons.append('withdrawn' if n.get('status') == 'withdrawn' else 'unavailable')
            elif currency(n) != 'current': reasons.append('stale')
            elif n['type']=='question' and resolution(g,target)['resolution'] not in edge.get('requires',['answered']): reasons.append('resolution-not-satisfied')
            elif n['type']!='question' and n.get('status') not in edge.get('requires', ['accepted']): reasons.append('not-accepted')
            receipt = edge.get('input_fingerprint')
            if receipt and receipt != fingerprint(n): reasons.append('input-version-changed')
            elif edge.get('input_version') is not None and edge['input_version'] != n.get('semantic_version',1): reasons.append('input-version-changed')
            local = [{'node': target, 'reason': r, 'path': [node, target], 'edges': [eid]} for r in reasons]
            children = visit(target, stack + [node])
            for child in children:
                local.append({**child, 'path': [node] + child['path'], 'edges': [eid] + child.get('edges', [])})
            group = edge.get('any_group')
            if group: groups[group].append((target, local))
            else: blockers.extend(local)
        for group, choices in groups.items():
            chosen[node].update(target for target,local in choices if not local)
            if all(local for _, local in choices):
                blockers.extend({**item, 'any_group': group} for _, local in choices for item in local)
        unique = {json.dumps(b, sort_keys=True): b for b in blockers}
        result = [unique[k] for k in sorted(unique)]
        memo[node] = result
        return copy.deepcopy(result)
    blockers = visit(nid, [])
    deps = [eid for eid, _ in adj[nid] if g['edges'][eid]['type'] == 'depends-on' or g['edge_types'][g['edges'][eid]['type']].get('readiness')]
    return {'node': nid, 'readiness': 'blocked' if blockers else 'ready' if deps else 'no-dependencies',
            'blockers': blockers, 'dependencies': deps, 'satisfied_by': sorted(chosen[nid]),
            **(resolution(g, nid) if g['nodes'][nid]['type'] == 'question' else {})}


def cycles(g, relation):
    """One deterministic DFS witness per detected back-edge, without enumerating all cycles."""
    adj = collections.defaultdict(list)
    for eid, e in sorted(g['edges'].items()):
        if e['type'] == relation: adj[e['from']].append((eid, e['to']))
    done, active, stack, edge_stack, found = set(), set(), [], [], []
    def visit(n):
        active.add(n); stack.append(n)
        for eid, target in adj[n]:
            if target in active:
                start = stack.index(target)
                found.append({'nodes': stack[start:] + [target], 'edges': edge_stack[start:] + [eid]})
            elif target not in done:
                edge_stack.append(eid); visit(target); edge_stack.pop()
        stack.pop(); active.remove(n); done.add(n)
    for n in sorted(g['nodes']):
        if n not in done: visit(n)
    return found


def findings(g):
    out = []
    def add(code, nid, message, severity='informational', edges=None):
        nodes = [nid] if isinstance(nid, str) else nid
        suppressed = severity == 'informational' and any((g['nodes'][i].get('meta') or {}).get('incomplete_by_design') for i in nodes)
        out.append({'code': code, 'nodes': nodes, 'edges': edges or [], 'message': message, 'severity': severity, 'suppressed': suppressed})
    incident = collections.defaultdict(list)
    for eid, e in sorted(g['edges'].items()):
        incident[e['from']].append((eid, e)); incident[e['to']].append((eid, e))
        if e['type'] == 'revises':
            a, b = (g['nodes'][e[k]] for k in ('from', 'to'))
            if all(n.get('status') == 'accepted' and not retired(n) for n in (a, b)) and not (e.get('meta') or {}).get('intentional_coexistence'):
                add('unresolved-revision', [e['from'], e['to']], 'Both revised formulations remain accepted/current; retire one or explain coexistence.', 'review', [eid])
    for nid, n in sorted(g['nodes'].items()):
        if retired(n): continue
        refs = incident[nid]
        if n['type'] in {'entity', 'operation'} and not refs: add('orphan-anchor', nid, 'Anchor has no references.')
        if n['type'] == 'operation' and not any(e['type'] == 'governs' and e['to'] == nid for _, e in refs): add('ungoverned-operation', nid, 'Operation has no governing claim.')
        if n['type'] == 'question':
            if not refs: add('unconnected-question', nid, 'Question has no subject, answer or dependency.')
            derived=resolution(g,nid)['resolution']
            stored=n.get('status')
            if (stored in {'answered','complete'} and derived!='answered') or (stored=='open' and derived=='answered' and currency(n)=='current'):
                add('answer-state-drift',nid,'Stored question state disagrees with its derived answer resolution.','review')
                out[-1].update(stored_state=stored,derived_resolution=derived)

        if n['type']=='claim' and n.get('status')=='accepted':
            import tracecheck
            coverage=tracecheck.coverage(g,nid)
            if not coverage['has_coverage']:
                add('untested-claim',nid,'Accepted claim has no current evaluation or explicitly declared case evidence; this is a coverage gap.')
                out[-1]['coverage']=coverage
    for kind, code in [('depends-on', 'dependency-cycle'), ('revises', 'revision-cycle')]:
        for c in cycles(g, kind): add(code, c['nodes'], 'Dependency review group.' if kind == 'depends-on' else 'Invalid revision ordering.', 'review', c['edges'])
    return out



def validate_formal_shape(model):
    """Validate JSON shapes even if no policy happens to reference this model yet."""
    if not isinstance(model,dict): raise ValueError('formal_model must be an object')
    def strings(value,label,length=None):
        if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value) or (length is not None and len(value)!=length):
            raise ValueError(label+' must be a list of'+(' '+str(length) if length is not None else '')+' nonempty string IDs')
    for section in ('scopes','actors'):
        if section not in model: continue
        value=model[section]
        if not isinstance(value,dict): raise ValueError('formal_model.'+section+' must be an object')
        for key,definition in value.items():
            if not isinstance(key,str) or not key or not isinstance(definition,dict): raise ValueError('formal_model.'+section+' entries must be named objects')
            if section=='scopes':
                if 'members' in definition: strings(definition['members'],'scope members')
                if 'nonempty' in definition and not isinstance(definition['nonempty'],bool): raise ValueError('scope nonempty must be boolean')
            else:
                if 'roles' in definition: strings(definition['roles'],'actor roles')
                if 'roles_complete' in definition and not isinstance(definition['roles_complete'],bool): raise ValueError('actor roles_complete must be boolean')
    for section in ('scope_subset','scope_disjoint','role_disjoint'):
        if section not in model:continue
        if not isinstance(model[section],list): raise ValueError('formal_model.'+section+' must be a list of pairs')
        for pair in model[section]:strings(pair,section,2)
    for section in ('scope_overlap','subjects'):
        if section not in model:continue
        if not isinstance(model[section],list):raise ValueError('formal_model.'+section+' must be a list of objects')
        for item in model[section]:
            if not isinstance(item,dict):raise ValueError('formal_model.'+section+' entries must be objects')
            if 'scopes' in item:strings(item['scopes'],section+' scopes',2 if section=='scope_overlap' else None)
            for key in ('id','type'):
                if key in item and (not isinstance(item[key],str) or not item[key]):raise ValueError(section+' '+key+' must be a nonempty string')


def validate(g):
    validate_formal_shape(g.get('formal_model',{}))
    for relation,definition in g['edge_types'].items():
        if 'invalidation' in definition and definition['invalidation'] not in ('none','dependent-to-prerequisite'):raise ValueError('Unsupported invalidation semantics on '+relation)
        if 'readiness' in definition and not isinstance(definition['readiness'],bool):raise ValueError('readiness declaration must be boolean on '+relation)
    for nid, n in g['nodes'].items():
        for field in ('trace','provenance','result','answer'):
            if field in n and not isinstance(n[field],dict):raise ValueError(field+' must be an object on '+nid)
        if 'references' in n and (not isinstance(n['references'],list) or any(not isinstance(r,str) for r in n['references'])):raise ValueError('references must be string IDs on '+nid)
        shape = n.get('answer_shape', (n.get('meta') or {}).get('answer_shape'))
        if shape is not None and shape not in SHAPES: raise ValueError('Unknown answer shape on ' + nid)
        for ref in n.get('references', []):
            if ref not in g['nodes']: raise ValueError('Unknown semantic reference ' + str(ref) + ' on ' + nid)
    for eid, e in dependency_edges(g):
        if 'requires' in e and (not isinstance(e['requires'], list) or not e['requires'] or any(not isinstance(x,str) for x in e['requires'])): raise ValueError('requires must be nonempty status list: ' + eid)
        if e.get('any_group') is not None and not isinstance(e['any_group'], str): raise ValueError('any_group must be a string: ' + eid)


def refresh(original, g, edits, reviewed):
    """Apply transitive currency changes; receipts bind explicit re-review to final inputs."""
    roots = set()
    reasons = collections.defaultdict(list)
    for edit in list(edits):
        before, after, key = edit['before'], edit['after'], edit['id']
        if edit['collection'] == 'nodes' and before and after:
            if fingerprint(before) != fingerprint(after) or retired(before)!=retired(after) or (currency(before) != currency(after) and currency(after) != 'current'):
                roots.add(key)
                if fingerprint(before) != fingerprint(after):
                    version_before=copy.deepcopy(g['nodes'][key])
                    g['nodes'][key]['semantic_version'] = before.get('semantic_version', 1) + 1
                    edits.append({'collection':'nodes','id':key,'before':version_before,'after':copy.deepcopy(g['nodes'][key]),'automatic':'semantic-version'})
        elif edit['collection'] == 'edge_types':
            def declaration_signature(value):return ((value or {}).get('invalidation')=='dependent-to-prerequisite',bool((value or {}).get('readiness')))
            if declaration_signature(before)!=declaration_signature(after):
                for snapshot in (original,g):
                    for eid,edge in snapshot['edges'].items():
                        if edge['type']==key:
                            roots.add(edge['from']);reasons[edge['from']].append('Dependency relation semantics changed: '+key)
        elif edit['collection'] == 'formal_model':
            # The model is explicit semantic input. Scope-only edits can be narrowed by stable IDs.
            changed_scopes=set()
            if key=='scopes' and isinstance(before or {},dict) and isinstance(after or {},dict):
                changed_scopes={k for k in set(before or {})|set(after or {}) if (before or {}).get(k)!=(after or {}).get(k)}
            for nid,node in g['nodes'].items():
                pattern=node.get('pattern') or {}
                if pattern and (key!='scopes' or pattern.get('scope') in changed_scopes):
                    roots.add(nid); reasons[nid].append('Formal model input changed: '+key)
        elif edit['collection'] == 'edges':
            for edge in (before, after):
                if not edge: continue
                if edge['type'] in {'depends-on', 'extracted-from'} or any(snapshot['edge_types'].get(edge['type'],{}).get('invalidation')=='dependent-to-prerequisite' for snapshot in (original,g)):
                    roots.add(edge['from']); reasons[edge['from']].append('Dependency changed: ' + key)
                # Answer edits affect local interpretation only, not readiness dependencies.
                elif edge['type'] in {'answers', 'revises', 'challenges', 'potential-conflict'}:
                    reasons[edge['to']].append('Decision relation changed: ' + key)
    # Use both snapshots so replacing a dependency cannot hide the former premise's impact.
    affected = set()
    for snapshot in (original, g):
        affected.update(affected_ids(snapshot,roots))
    for key in roots:
        if key in original['nodes'] and key in g['nodes']:
            reasons[key].append('Semantic content or currency changed.')
        for snapshot in (original, g):
            for edge in snapshot['edges'].values():
                if edge['type'] == 'answers' and edge['from'] == key:
                    reasons[edge['to']].append('Answer changed: ' + key)
    for key in affected: reasons[key].append('Declared semantic prerequisite changed: ' + ', '.join(sorted(roots)))
    for key in sorted(reasons):
        if key in reviewed or key not in original['nodes'] or key not in g['nodes'] or retired(g['nodes'][key]): continue
        before = copy.deepcopy(g['nodes'][key])
        meta = g['nodes'][key].setdefault('meta', {})
        meta.update(review_state='needs-review', review_reason=' '.join(dict.fromkeys(reasons[key])))
        # Paths remain queryable without repeating potentially huge path sets on each node.
        meta['review_roots'] = sorted(roots)
        edits.append({'collection': 'nodes', 'id': key, 'before': before, 'after': copy.deepcopy(g['nodes'][key]), 'automatic': 'dependency-review'})
    for key in sorted(reviewed):
        if key not in g['nodes'] or currency(g['nodes'][key]) != 'current': continue
        receipts = {}
        versions = {}
        for eid, edge in dependency_edges(g):
            if edge['from'] != key: continue
            receipts[edge['to']] = fingerprint(g['nodes'][edge['to']])
            before = copy.deepcopy(edge)
            edge['input_fingerprint'] = receipts[edge['to']]
            versions[edge['to']] = g['nodes'][edge['to']].get('semantic_version',1)
            edge['input_version'] = versions[edge['to']]
            if before != edge: edits.append({'collection': 'edges', 'id': eid, 'before': before, 'after': copy.deepcopy(edge), 'automatic': 'review-receipt'})
        if receipts:
            before = copy.deepcopy(g['nodes'][key]); g['nodes'][key].setdefault('meta', {}).update(reviewed_inputs=receipts,reviewed_input_versions=versions)
            edits.append({'collection': 'nodes', 'id': key, 'before': before, 'after': copy.deepcopy(g['nodes'][key]), 'automatic': 'review-receipt'})
