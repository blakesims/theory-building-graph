#!/usr/bin/env python3
"""Fable 5.1 gate-closure tamper probes. Copies real evidence into a temporary root and
mutates the copies only. Run: python3 reviews/fixtures/fable-5.1/gate-probes.py
"""
import copy, hashlib, json, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from acceptance.receipt_validation import validate_receipt_file
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
COPY = ['reviews/multiturn/v2/design', 'reviews/multiturn/pace4/design', 'reviews/multiturn/S08', 'reviews/multiturn/decision3/design', 'reviews/browser', 'acceptance']
S02 = 'reviews/multiturn/v2/design/graded-S02.json'; S08 = 'reviews/multiturn/S08/graded.json'
D3 = 'reviews/multiturn/decision3/design/graded-S01.json'

def fresh():
    d = tempfile.TemporaryDirectory(); root = Path(d.name)
    for rel in COPY: shutil.copytree(ROOT / rel, root / rel)
    return d, root
def v(root, rel, case):
    r = validate_receipt_file(root, rel, case); return 'VALID' if r['valid'] else r['errors']
def rw(root, rel, fn):
    p = root / rel; obj = json.loads(p.read_text()); fn(obj); p.write_text(json.dumps(obj)); return p

def run(label, fn):
    d, root = fresh()
    try: print(f'{label:70} ->', fn(root))
    except Exception as exc: print(f'{label:70} -> PROBE ERROR {exc!r}')
    finally: d.cleanup()

print('pinned:', {f: sha(ROOT / f)[:16] for f in ('acceptance/staged_receipts.py', 'acceptance/receipt_validation.py', 'acceptance/run.py')})
run('T0 clean S02 / S08 / decision3-S01', lambda r: (v(r, S02, 'S02'), v(r, S08, 'S08'), v(r, D3, 'S01')))
run('T1 S02: unbind failed stage 01 stdout', lambda r: (rw(r, S02, lambda o: [o['artifact_hashes'].pop(k) for k in list(o['artifact_hashes']) if k.endswith('01-read-only/stdout.jsonl')]), v(r, S02, 'S02'))[1])
run('T2 S02: parent_hard_failures=[]', lambda r: (rw(r, S02, lambda o: o.update(parent_hard_failures=[])), v(r, S02, 'S02'))[1])
run('T3 S02: relabel cases->S03', lambda r: (rw(r, S02, lambda o: o.update(cases=['S03'])), v(r, S02, 'S03'))[1])
def t4(r):
    pp = r / 'reviews/multiturn/v2/design/graded.json'
    rw(r, 'reviews/multiturn/v2/design/graded.json', lambda o: o.update(hard_failures=[], passed=True))
    rw(r, S02, lambda o: (o.update(parent_graded_sha256=sha(pp), parent_hard_failures=[]), o['artifact_hashes'].__setitem__('graded.json', sha(pp))))
    return v(r, S02, 'S02')
run('T4 parent rewritten passed (grades still 0) + child rehash', t4)
def t4b(r):
    pp = r / 'reviews/multiturn/v2/design/graded.json'
    rw(r, 'reviews/multiturn/v2/design/graded.json', lambda o: o.update(grades=[g for g in o['grades'] if g['score'] == 1], hard_failures=[], passed=True))
    rw(r, S02, lambda o: (o.update(parent_graded_sha256=sha(pp), parent_hard_failures=[]), o['artifact_hashes'].__setitem__('graded.json', sha(pp))))
    return v(r, S02, 'S02')
run('T4b parent omits failed grades + child rehash', t4b)
def t5c(r):
    D = r / 'reviews/multiturn/v2/design'
    rw(r, 'reviews/multiturn/v2/design/normalized-rubric.json', lambda o: o.update(criteria=[c for c in o['criteria'] if c['id'] not in ('01-read-only', '04-explicit-choice')]))
    keep = {c['id'] for c in json.loads((D / 'normalized-rubric.json').read_text())['criteria']}
    rw(r, 'reviews/multiturn/v2/design/graded.json', lambda o: (o.update(grades=[g for g in o['grades'] if g['id'] in keep], hard_failures=[], passed=True, rubric_sha256=sha(D / 'normalized-rubric.json')), o['artifact_hashes'].__setitem__('normalized-rubric.json', sha(D / 'normalized-rubric.json'))))
    return v(r, 'reviews/multiturn/v2/design/graded.json', 'S01')
run('T5c whole-run report: rubric narrowed to passing stages, hashes updated', t5c)
run('T6 S08: drop parent_disclosures', lambda r: (rw(r, S08, lambda o: o.update(parent_disclosures=[])), v(r, S08, 'S08'))[1])
run('T7 S08 partial proposal component used standalone', lambda r: v(r, 'reviews/multiturn/v2/design/graded-S08-proposal.json', 'S08'))
def t8(r):
    pp = 'reviews/multiturn/v2/design/graded.json'
    rw(r, S08, lambda o: (o['components'][1].__setitem__('receipt', pp), o['artifact_hashes'].__setitem__(pp, sha(r / pp))))
    return v(r, S08, 'S08')
run('T8 S08 component swapped to failed whole run', t8)
def t9(r):
    D = r / 'reviews/multiturn/v2/design'; bp = D / 'control/05-reviewer-challenge/before.graph.json'
    g = json.loads(bp.read_text()); g['revision'] = 999; bp.write_text(json.dumps(g))
    part = json.loads((D / 'participant.json').read_text()); st = next(s for s in part['stages'] if s['stage'] == '05-reviewer-challenge'); st['before_sha256'] = sha(bp)
    (D / 'control/05-reviewer-challenge/receipt.json').write_text(json.dumps(st)); (D / 'participant.json').write_text(json.dumps(part))
    rw(r, S02, lambda o: o.update(raw_sha256=sha(D / 'participant.json')))
    return [e for e in v(r, S02, 'S02') if 'chain' in e]
run('T9 consistent-hash state chain break', t9)
run('T10 S08: unbind browser receipt slot artifact', lambda r: (rw(r, S08, lambda o: o['artifact_hashes'].pop('reviews/browser/receipt.json')), v(r, S08, 'S08'))[1])
def f1(r):
    p = r / 'reviews/multiturn/decision3/design/fork-manifest.json'; m = json.loads(p.read_text()); m['contract_version'] = 'authoring/6'; p.write_text(json.dumps(m))
    return v(r, D3, 'S01')
run('F1 decision3: edit fork-manifest contract_version', f1)
def f2(r):
    bp = r / 'reviews/multiturn/decision3/design/control/02-atomic-proposal/stdout.jsonl'; bp.write_bytes(bp.read_bytes() + b'\n')
    return [e for e in v(r, D3, 'S01') if 'fork' in e or 'hash' in e or 'stage' in e][:5]
run('F2 decision3: alter a copied prior-stage artifact', f2)
def f3(r):
    shutil.rmtree(r / 'reviews/multiturn/decision3/design/control/03-reconsider-and-recall')
    return [e for e in v(r, D3, 'S01') if 'fork' in e or 'stage' in e or 'unbound' in e][:5]
run('F3 decision3: remove a copied prior stage', f3)
def f4(r):
    D = r / 'reviews/multiturn/decision3/design'; m = json.loads((D / 'fork-manifest.json').read_text())
    return {k: (str(m[k])[:120]) for k in m if k in ('source_run', 'continuation_stage', 'rerun_prior_stages', 'contract_version', 'scope', 'history_extraction')}
run('F4 decision3 manifest summary', f4)
