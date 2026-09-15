#!/usr/bin/env python3
"""Independent CLI probes for the Fable 5.1 review. Every probe builds a temporary
graph, drives it only through `graph.py` subcommands, and prints observed output.
Nothing here touches the live graph.json. Run: python3 reviews/fixtures/fable-5.1/probes.py
"""
import json, subprocess, sys, tempfile, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TG = [sys.executable, str(ROOT / 'graph.py')]

def base():
    return {'version': 1, 'revision': 0, 'nodes': {}, 'edges': {}, 'changes': [],
            'node_types': {k: {} for k in ['claim', 'question', 'entity', 'operation', 'source', 'extraction', 'trace', 'case', 'check-result']},
            'edge_types': {'depends-on': {}, 'extracted-from': {}, 'about': {}, 'governs': {}, 'answers': {'coverage_required': True},
                           'revises': {}, 'supports': {}, 'informs': {}, 'checks': {}}}

def claim(text, status='accepted', **extra):
    return {'type': 'claim', 'text': text, 'status': status, **extra}

def tg(path, *args, ok=True):
    r = subprocess.run(TG + ['--file', str(path)] + list(args), capture_output=True, text=True)
    if ok and r.returncode != 0:
        return {'error': r.stderr.strip(), 'stdout': r.stdout.strip()}
    return r.stdout if not args or '--json' not in args else (json.loads(r.stdout) if r.stdout.strip() else {'stderr': r.stderr.strip()})

def apply(path, ops, reason='probe', ok=True):
    ops_file = path.with_name('ops.json'); ops_file.write_text(json.dumps(ops))
    r = subprocess.run(TG + ['--file', str(path), 'apply', str(ops_file), '--actor', 'fable-review', '--reason', reason], capture_output=True, text=True)
    return {'code': r.returncode, 'out': r.stdout.strip(), 'err': r.stderr.strip()}

def load(path): return json.loads(path.read_text())
def cur(g, n): return (g['nodes'][n].get('meta') or {}).get('review_state', 'current')

def probe(name):
    def deco(fn):
        def run():
            print(f'\n===== {name}')
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d) / 'g.json')
        run.__name__ = fn.__name__; return run
    return deco

@probe('P1 re-review of an unchanged prerequisite re-invalidates already-reviewed dependents')
def p1(path):
    g = base(); g['nodes'] = {'A': claim('A'), 'B': claim('B'), 'Q': {'type': 'question', 'text': 'Q', 'status': 'open'}}
    g['edges'] = {'B-dep-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}, 'Q-dep-B': {'from': 'Q', 'to': 'B', 'type': 'depends-on'}}
    path.write_text(json.dumps(g))
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'A', 'value': {'text': 'A revised'}}], 'edit premise')
    s = load(path); print('after A edit   :', {n: cur(s, n) for n in 'ABQ'})
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'Q', 'value': {'meta': {'review_state': 'current'}}}], 'review Q first')
    s = load(path); print('after Q review :', {n: cur(s, n) for n in 'ABQ'}, 'Q receipt on B =', s['nodes']['Q']['meta'].get('reviewed_inputs', {}).get('B', '')[:12])
    fp_b = s['nodes']['B']['semantic_version'] if 'semantic_version' in s['nodes']['B'] else None
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'B', 'value': {'meta': {'review_state': 'current'}}}], 'review B; content unchanged')
    s = load(path); print('after B review :', {n: cur(s, n) for n in 'ABQ'}, '| B semantic_version unchanged:', s['nodes']['B'].get('semantic_version') == fp_b)
    print('Q review_reason:', s['nodes']['Q']['meta'].get('review_reason'))

@probe('P2 custom dependency edge type: node edits propagate, but adding/removing the edge does not flag the dependent')
def p2(path):
    g = base(); g['edge_types']['derived-from'] = {'invalidation': 'dependent-to-prerequisite', 'readiness': True}
    g['nodes'] = {'A': claim('A'), 'B': claim('B'), 'C': claim('C')}
    path.write_text(json.dumps(g))
    apply(path, [{'op': 'add', 'collection': 'edges', 'id': 'B-derived-A', 'value': {'from': 'B', 'to': 'A', 'type': 'derived-from'}}], 'add custom dependency')
    apply(path, [{'op': 'add', 'collection': 'edges', 'id': 'C-dep-A', 'value': {'from': 'C', 'to': 'A', 'type': 'depends-on'}}], 'add builtin dependency')
    s = load(path); print('B (custom edge added):', cur(s, 'B'), '| C (depends-on added):', cur(s, 'C'))
    print('readiness B dependencies:', tg(path, 'readiness', 'B', '--json')['dependencies'])

@probe('P3 a question prerequisite is judged by stored status, not derived resolution')
def p3(path):
    g = base(); g['nodes'] = {'Q1': {'type': 'question', 'text': 'Q1', 'status': 'answered'}, 'Q2': {'type': 'question', 'text': 'Q2', 'status': 'open'}}
    g['edges'] = {'Q2-dep-Q1': {'from': 'Q2', 'to': 'Q1', 'type': 'depends-on', 'requires': ['answered']}}
    path.write_text(json.dumps(g))
    r = tg(path, 'readiness', 'Q2', '--json'); print('Q2 readiness:', r['readiness'], 'blockers:', r['blockers'])
    print('Q1 resolution:', tg(path, 'readiness', 'Q1', '--json')['resolution'])
    findings = tg(path, 'check', '--json')['findings']; print('check findings for Q1:', [(f['code'], f['nodes']) for f in findings])

@probe('P4 authority patterns with the exempt scope "all" cannot be compared: check emits not-checked findings')
def p4(path):
    g = base(); g['nodes'] = {'steward': {'type': 'entity', 'text': 'S', 'meta': {'kind': 'agent-role'}}, 'orch': {'type': 'entity', 'text': 'O', 'meta': {'kind': 'agent-role'}},
        'choose': {'type': 'operation', 'text': 'choose'},
        'only-s': claim('only steward', pattern={'kind': 'authority', 'modality': 'only', 'role': 'steward', 'operation': 'choose', 'scope': 'all'}),
        'may-o': claim('orch may', pattern={'kind': 'authority', 'modality': 'may', 'role': 'orch', 'operation': 'choose', 'scope': 'all'})}
    g['edges'] = {f'{c}-gov': {'from': c, 'to': 'choose', 'type': 'governs'} for c in ('only-s', 'may-o')}
    g['formal_model'] = {'role_disjoint': [['steward', 'orch']]}
    path.write_text(json.dumps(g))
    print('with scope "all" undeclared :', [(f['code'], f['nodes'], f.get('reason')) for f in tg(path, 'check', '--json')['findings'] if f['code'] not in ('untested-claim',)])
    apply(path, [{'op': 'add', 'collection': 'formal_model', 'id': 'scopes', 'value': {'all': {'members': ['world']}}}], 'declare all')
    print('after declaring "all"        :', [(f['code'], f['nodes']) for f in tg(path, 'check', '--json')['findings'] if f['code'] not in ('untested-claim',)])
    print('trace evaluation of scope all pattern is', json.loads(json.dumps(tg(path, 'node', 'only-s', '--json')))['nodes']['only-s']['pattern']['scope'], '-> allowed by evaluate_authority; comparison needed a declaration')

@probe('P5 malformed formal_model section (null scopes) is accepted by apply and then crashes check')
def p5(path):
    g = base(); g['nodes'] = {'A': claim('A', pattern={'kind': 'authority', 'modality': 'only', 'role': 'A', 'operation': 'A', 'scope': 'all'})}
    g['formal_model'] = {'scopes': {'all': {'members': ['w']}}}
    path.write_text(json.dumps(g))
    r = apply(path, [{'op': 'update', 'collection': 'formal_model', 'id': 'scopes'}], 'update without value'); print('apply:', r)
    print('formal_model now:', load(path).get('formal_model'))
    r = subprocess.run(TG + ['--file', str(path), 'check'], capture_output=True, text=True); print('check exit', r.returncode, '|', (r.stderr.strip().splitlines() or [''])[-1])

@probe('P9 generic authority checker: complete trace with zero matching events reports "satisfies" with nothing visible in text output')
def p9(path):
    g = base(); g['nodes'] = {'steward': {'type': 'entity', 'text': 'S', 'meta': {'kind': 'agent-role'}}, 'choose': {'type': 'operation', 'text': 'choose'},
        'only-s': claim('only steward chooses', pattern={'kind': 'authority', 'modality': 'only', 'role': 'steward', 'operation': 'choose', 'scope': 'all'}),
        'T': {'type': 'trace', 'text': 'no choose events', 'status': 'recorded', 'polarity': 'defect', 'meta': {'synthetic': True}, 'trace': {'complete': True, 'events': [{'id': 'e1', 'operation': 'other', 'actor': 'x', 'actor_roles': ['steward']}]}}}
    path.write_text(json.dumps(g))
    print(tg(path, 'evaluate', 'only-s', 'T'))
    r = tg(path, 'evaluate', 'only-s', 'T', '--json'); print('checked_events:', r['checked_events'], '| assessment findings:', [f['code'] for f in r['assessment']['findings']])
    g['nodes']['only-s']['pattern']['modality'] = 'may'; path.write_text(json.dumps(g))
    r = tg(path, 'evaluate', 'only-s', 'T', '--json'); print('modality may ->', r['outcome'], '| assessment:', [f['code'] for f in r['assessment']['findings']])

@probe('P11 authority path: a role referenced only by trace events is not a fingerprinted input (demo path fingerprints it)')
def p11(path):
    g = base(); g['nodes'] = {'steward': {'type': 'entity', 'text': 'S', 'meta': {'kind': 'agent-role'}}, 'orch': {'type': 'entity', 'text': 'O', 'meta': {'kind': 'agent-role'}}, 'choose': {'type': 'operation', 'text': 'choose'},
        'only-s': claim('only steward', pattern={'kind': 'authority', 'modality': 'only', 'role': 'steward', 'operation': 'choose', 'scope': 'all'}),
        'T': {'type': 'trace', 'text': 't', 'status': 'recorded', 'meta': {'synthetic': True}, 'trace': {'complete': True, 'events': [{'id': 'e1', 'operation': 'choose', 'actor': 'x', 'actor_roles': ['orch']}]}}}
    path.write_text(json.dumps(g))
    print(tg(path, 'evaluate', 'only-s', 'T', '--save', 'receipt').splitlines()[0])
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'orch', 'value': {'text': 'Orchestrator redefined'}}], 'redefine the role that appears in the witness')
    print('receipt after redefining orch:', tg(path, 'node', 'receipt', '--json')['nodes']['receipt']['result_state'])
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'steward', 'value': {'text': 'Steward redefined'}}], 'redefine pattern role')
    print('receipt after redefining steward:', tg(path, 'node', 'receipt', '--json')['nodes']['receipt']['result_state'])

@probe('P20 untested-claim ignores saved check-results; any edge to a trace counts as a test')
def p20(path):
    g = base(); g['nodes'] = {'steward': {'type': 'entity', 'text': 'S', 'meta': {'kind': 'agent-role'}}, 'choose': {'type': 'operation', 'text': 'choose'},
        'A': claim('only steward', pattern={'kind': 'authority', 'modality': 'only', 'role': 'steward', 'operation': 'choose', 'scope': 'all'}),
        'B': claim('unrelated accepted claim'),
        'T': {'type': 'trace', 'text': 't', 'status': 'recorded', 'meta': {'synthetic': True}, 'trace': {'complete': True, 'events': [{'id': 'e1', 'operation': 'choose', 'actor': 'x', 'actor_roles': ['steward']}]}}}
    g['edges'] = {'A-gov': {'from': 'A', 'to': 'choose', 'type': 'governs'}, 'B-gov': {'from': 'B', 'to': 'choose', 'type': 'governs'}, 'B-about-T': {'from': 'B', 'to': 'T', 'type': 'about'}}
    path.write_text(json.dumps(g))
    tg(path, 'evaluate', 'A', 'T', '--save', 'receipt-A')
    print('after saving a real evaluation of A:', [(f['code'], f['nodes']) for f in tg(path, 'check', '--json')['findings'] if f['code'] == 'untested-claim'])
    print('B has only an about-edge to the trace and no evaluation; flagged untested?', any(f['nodes'] == ['B'] for f in tg(path, 'check', '--json')['findings'] if f['code'] == 'untested-claim'))

@probe('P24 propagation passes through a historical (retired) dependent')
def p24(path):
    g = base(); g['nodes'] = {'A': claim('A'), 'B': claim('B', 'withdrawn', meta={'review_state': 'historical'}), 'C': claim('C')}
    g['edges'] = {'B-dep-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}, 'C-dep-B': {'from': 'C', 'to': 'B', 'type': 'depends-on'}}
    path.write_text(json.dumps(g))
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'A', 'value': {'text': 'A2'}}], 'edit A')
    s = load(path); print({n: cur(s, n) for n in 'ABC'}, '| impact A affected:', tg(path, 'impact', 'A', '--json')['affected'])

@probe('P26 claim with "meta": null and a pattern crashes check')
def p26(path):
    g = base(); g['nodes'] = {'A': claim('A', pattern={'kind': 'authority', 'modality': 'only', 'role': 'A', 'operation': 'A', 'scope': 'x'}, meta=None),
                              'B': claim('B', pattern={'kind': 'authority', 'modality': 'may', 'role': 'B', 'operation': 'A', 'scope': 'x'})}
    g['formal_model'] = {'scopes': {'x': {'members': ['w']}}}
    path.write_text(json.dumps(g))
    r = subprocess.run(TG + ['--file', str(path), 'check'], capture_output=True, text=True); print('check exit', r.returncode, '|', (r.stderr.strip().splitlines() or [''])[-1])

@probe('P28 one condition, two findings with different codes; "answer-state-drift" means two different things')
def p28(path):
    g = base(); g['nodes'] = {'Q': {'type': 'question', 'text': 'Q', 'status': 'answered'}, 'A': claim('A')}
    g['edges'] = {'A-about-Q': {'from': 'A', 'to': 'Q', 'type': 'supports'}}
    path.write_text(json.dumps(g))
    print('answered-without-answer:', [(f['code'], f['nodes']) for f in tg(path, 'check', '--json')['findings'] if 'Q' in f['nodes']])
    g['nodes']['Q']['status'] = 'open'; g['edges']['A-ans-Q'] = {'from': 'A', 'to': 'Q', 'type': 'answers', 'coverage': 'full'}; path.write_text(json.dumps(g))
    print('open-with-full-answer   :', [(f['code'], f['nodes']) for f in tg(path, 'check', '--json')['findings'] if 'Q' in f['nodes']])

@probe('P30 deleting a prerequisite and its edge in one batch flags the dependent (positive control)')
def p30(path):
    g = base(); g['nodes'] = {'A': claim('A'), 'B': claim('B')}; g['edges'] = {'B-dep-A': {'from': 'B', 'to': 'A', 'type': 'depends-on'}}
    path.write_text(json.dumps(g))
    r = apply(path, [{'op': 'delete', 'collection': 'edges', 'id': 'B-dep-A'}, {'op': 'delete', 'collection': 'nodes', 'id': 'A'}], 'remove premise')
    s = load(path); print('apply code', r['code'], '| B:', cur(s, 'B'), '|', s['nodes']['B'].get('meta', {}).get('review_reason'))

@probe('P31 only(R) versus never(R) on the same scope is reported "compatible" (an overconstraint: nobody may act)')
def p31(path):
    sys.path.insert(0, str(ROOT)); import formalcheck as f
    m = {'scopes': {'s': {'members': ['w']}}}
    a = {'kind': 'authority', 'modality': 'only', 'role': 'r', 'operation': 'op', 'scope': 's'}
    print('only(r) vs never(r):', f.compare_patterns(a, {**a, 'modality': 'never'}, m)['outcome'])
    print('only(r) vs only(r) :', f.compare_patterns(a, a, m)['outcome'])
    print('must(r) vs only(r) :', f.compare_patterns({**a, 'modality': 'must'}, a, m)['outcome'])

@probe('P32 finding ids of formal comparisons change on every revision (computed_revision is hashed in)')
def p32(path):
    g = base(); g['nodes'] = {'s': {'type': 'entity', 'text': 'S'}, 'o': {'type': 'entity', 'text': 'O'}, 'op': {'type': 'operation', 'text': 'op'},
        'A': claim('A', pattern={'kind': 'authority', 'modality': 'only', 'role': 's', 'operation': 'op', 'scope': 'x'}),
        'B': claim('B', pattern={'kind': 'authority', 'modality': 'may', 'role': 'o', 'operation': 'op', 'scope': 'x'}), 'Z': claim('unrelated')}
    g['formal_model'] = {'scopes': {'x': {'members': ['w']}}, 'role_disjoint': [['s', 'o']]}
    path.write_text(json.dumps(g))
    before = {f['code']: f['id'] for f in tg(path, 'check', '--json')['findings']}
    apply(path, [{'op': 'update', 'collection': 'nodes', 'id': 'Z', 'value': {'text': 'unrelated edit'}}], 'unrelated')
    after = {f['code']: f['id'] for f in tg(path, 'check', '--json')['findings']}
    print('policy-conflict id stable across an unrelated revision:', before.get('policy-conflict') == after.get('policy-conflict'))
    print('untested-claim id stable:', before.get('untested-claim') == after.get('untested-claim'))

if __name__ == '__main__':
    for fn in [p1, p2, p3, p4, p5, p9, p11, p20, p24, p26, p28, p30, p31, p32]:
        try: fn()
        except Exception as exc: print('PROBE ERROR', fn.__name__, repr(exc))
