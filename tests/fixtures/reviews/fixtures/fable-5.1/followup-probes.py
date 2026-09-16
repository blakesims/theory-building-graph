#!/usr/bin/env python3
"""Follow-up regression probes (N1-N7) for the Fable 5.1 re-review. Temporary graphs only.
Run: python3 reviews/fixtures/fable-5.1/followup-probes.py
"""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
TG = [sys.executable, str(ROOT / 'graph.py')]

def base():
    return {'version': 1, 'revision': 0, 'nodes': {}, 'edges': {}, 'changes': [],
            'node_types': {k: {} for k in ['claim', 'question', 'entity', 'operation', 'trace', 'check-result']},
            'edge_types': {'depends-on': {}, 'about': {}, 'governs': {}, 'answers': {'coverage_required': True}, 'checks': {}}}
def run(p, ops, reason):
    o = p.with_name('ops.json'); o.write_text(json.dumps(ops))
    r = subprocess.run(TG + ['--file', str(p), 'apply', str(o), '--actor', 'x', '--reason', reason], capture_output=True, text=True)
    return r.returncode, r.stderr.strip()
def cur(p, n):
    s = json.loads(p.read_text()); return (s['nodes'][n].get('meta') or {}).get('review_state', 'current')
def readiness(p, n): return json.loads(subprocess.check_output(TG + ['--file', str(p), 'readiness', n, '--json']))
def check(p): return json.loads(subprocess.check_output(TG + ['--file', str(p), 'check', '--json']))['findings']
cl = lambda t, s='accepted', **k: {'type': 'claim', 'text': t, 'status': s, **k}

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / 'g.json'
    g = base(); g['nodes'] = {'A': cl('A'), 'B': cl('B'), 'Q': {'type': 'question', 'text': 'q', 'status': 'open'}}
    g['edges'] = {'B-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}, 'Q-B': {'from': 'Q', 'to': 'B', 'type': 'depends-on'}}; p.write_text(json.dumps(g))
    run(p, [{'op': 'update', 'collection': 'nodes', 'id': 'A', 'value': {'text': 'A2'}}], 'edit'); run(p, [{'op': 'update', 'collection': 'nodes', 'id': 'Q', 'value': {'meta': {'review_state': 'current'}}}], 'review Q')
    run(p, [{'op': 'update', 'collection': 'nodes', 'id': 'B', 'value': {'text': 'B reworded during review', 'meta': {'review_state': 'current'}}}], 'review B with edit')
    print('N1 review+edit of B -> Q:', cur(p, 'Q'), '(expect needs-review)')

    g = base(); g['nodes'] = {'A': cl('A', 'withdrawn', meta={'review_state': 'historical'}), 'B': cl('B')}; g['edges'] = {'B-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}}; p.write_text(json.dumps(g))
    run(p, [{'op': 'update', 'collection': 'nodes', 'id': 'A', 'value': {'status': 'accepted', 'meta': {'review_state': 'current'}}}], 'reactivate A')
    print('N2 reactivate A -> B:', cur(p, 'B'), '(expect needs-review)')

    g = base(); g['nodes'] = {'A': cl('A'), 'B': cl('B')}; g['edges'] = {'B-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}}; p.write_text(json.dumps(g))
    run(p, [{'op': 'update', 'collection': 'nodes', 'id': 'A', 'value': {'meta': {'review_state': 'needs-review', 'review_reason': 'user doubt'}}}], 'flag A')
    print('N3 user flags A -> B:', cur(p, 'B'))

    g = base(); g['nodes'] = {'A': cl('A'), 'Q1': {'type': 'question', 'text': 'q1', 'status': 'open', 'required_parts': ['x', 'y']}, 'Q2': {'type': 'question', 'text': 'q2', 'status': 'open'}}
    g['edges'] = {'A-ans': {'from': 'A', 'to': 'Q1', 'type': 'answers', 'coverage': 'partial', 'covers': ['x']}, 'Q2-Q1': {'from': 'Q2', 'to': 'Q1', 'type': 'depends-on', 'requires': ['partial-answer', 'answered']}}; p.write_text(json.dumps(g))
    r = readiness(p, 'Q2'); print('N4 requires partial-answer|answered, Q1 partial ->', r['readiness'], [b['reason'] for b in r['blockers']])
    g['edges']['Q2-Q1']['requires'] = ['accepted']; p.write_text(json.dumps(g))
    r = readiness(p, 'Q2'); print('N4b legacy requires accepted on a question edge ->', r['readiness'], [b['reason'] for b in r['blockers']])
    g['edges']['Q2-Q1']['requires'] = ['answerd']; p.write_text(json.dumps(g))
    r = subprocess.run(TG + ['--file', str(p), 'readiness', 'Q2', '--json'], capture_output=True, text=True); print('N4c misspelled requires accepted by validate? exit', r.returncode)

    g = base(); g['nodes'] = {'a': {'type': 'entity', 'text': 'unrelated'}, 'r': {'type': 'entity', 'text': 'role', 'meta': {'kind': 'agent-role'}}, 'op': {'type': 'operation', 'text': 'op'},
        'C': cl('c', pattern={'kind': 'authority', 'modality': 'only', 'role': 'r', 'operation': 'op', 'scope': 'all'}),
        'T': {'type': 'trace', 'text': 't', 'status': 'recorded', 'trace': {'complete': True, 'events': [{'id': 'e', 'operation': 'op', 'attempt': 'a', 'actor': 'a', 'actor_role': 'r'}]}}}; p.write_text(json.dumps(g))
    print('N5 delete a (coincidence only):', run(p, [{'op': 'delete', 'collection': 'nodes', 'id': 'a'}], 'del a'))
    print('N5 delete r (pattern+event role):', run(p, [{'op': 'delete', 'collection': 'nodes', 'id': 'r'}], 'del r')[1][:70])

    g = base(); g['nodes'] = {'A': cl('old', 'withdrawn', meta={'review_state': 'historical'}, pattern={'kind': 'authority', 'modality': 'only', 'role': 'ghost', 'operation': 'op', 'scope': 'all'}), 'op': {'type': 'operation', 'text': 'op'}}; p.write_text(json.dumps(g))
    print('N6 historical undeclared ref:', [f['code'] for f in check(p)])

    g = base(); g['nodes'] = {'r': {'type': 'entity', 'text': 'role', 'meta': {'kind': 'agent-role'}}, 'op': {'type': 'operation', 'text': 'op'}, 'C': cl('c', pattern={'kind': 'authority', 'modality': 'only', 'role': 'r', 'operation': 'op', 'scope': 'all'}),
        'T': {'type': 'trace', 'text': 't', 'status': 'recorded', 'meta': {'synthetic': True}, 'trace': {'complete': True, 'events': [{'id': 'e', 'operation': 'op', 'actor': 's', 'actor_roles': ['r']}]}}}; g['edges'] = {'C-gov': {'from': 'C', 'to': 'op', 'type': 'governs'}}; p.write_text(json.dumps(g))
    subprocess.run(TG + ['--file', str(p), 'evaluate', 'C', 'T', '--save', 'rc'], check=True, capture_output=True)
    print('N7 untested after save:', [x['nodes'] for x in check(p) if x['code'] == 'untested-claim'])
    s = json.loads(p.read_text()); s['nodes']['rc']['result']['checker_version'] = 'exclusive-actor/2'; p.write_text(json.dumps(s))
    print('N7 untested after checker bump:', [(x['nodes'], x['coverage']['state'], len(x['coverage']['stale_evaluations'])) for x in check(p) if x['code'] == 'untested-claim'])
