"""Integrity of scoped judgments over actual staged participant transcripts."""
import hashlib
import json
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def staged_errors(root, path, receipt, raw, inputs, rubric, case):
    errors=[];root=Path(root).resolve();path=Path(path).resolve()
    def located(rel,base=path.parent):
        p=(root/rel).resolve()
        if not p.exists():p=(base/rel).resolve()
        if not p.is_relative_to(root):raise ValueError('staged evidence outside repository')
        return p
    bound={located(k):v for k,v in receipt.get('artifact_hashes',{}).items()}
    def require(p):
        if p not in bound:errors.append('stage-artifact-unbound:'+str(p.relative_to(root)))
        elif bound[p]!=digest(p):errors.append('stage-artifact-hash-mismatch')
    if receipt.get('parent_trial'):
        parent_dir=located(receipt['parent_trial'])
        parent_path=parent_dir/'graded.json';require(parent_path)
        parent=json.loads(parent_path.read_text())
        if digest(parent_path)!=receipt.get('parent_graded_sha256'):errors.append('parent-grade-hash-mismatch')
        if receipt.get('parent_hard_failures')!=parent.get('hard_failures'):errors.append('parent-failures-not-disclosed')
        if 'parent_passed' in receipt and receipt['parent_passed'] is not parent.get('passed'):errors.append('parent-passed-disclosure-mismatch')
        if any(receipt.get(k)!=parent.get(k) for k in ('fork_manifest_path','fork_manifest_sha256')):errors.append('scoped-fork-provenance-mismatch')
        if receipt.get('raw_sha256')!=parent.get('raw_sha256') or receipt.get('input_sha256')!=parent.get('input_sha256'):errors.append('scoped-parent-input-mismatch')
        parent_rubric_path=located(parent['rubric_path'],parent_dir);require(parent_rubric_path)
        if digest(parent_rubric_path)!=parent.get('rubric_sha256'):errors.append('parent-rubric-hash-mismatch')
        parent_rubric=json.loads(parent_rubric_path.read_text())
        parent_ids=[g['id'] for g in parent.get('grades',[])]
        rubric_ids=[g['id'] for g in parent_rubric.get('criteria',[])]
        if len(parent_ids)!=len(set(parent_ids)) or set(parent_ids)!=set(rubric_ids):errors.append('parent-grade-rubric-coverage-mismatch')
        if any(type(g.get('score')) is not int or g['score'] not in (0,1) for g in parent.get('grades',[])):errors.append('parent-invalid-grade-score')
        failed={g['id'] for g in parent.get('grades',[]) if g.get('score')==0}
        failures=parent.get('hard_failures')
        if not isinstance(failures,list) or not failed <= set(failures):errors.append('parent-grade-failure-disclosure-mismatch')
        if parent.get('passed') is not (not failed and failures==[]):errors.append('parent-verdict-inconsistent-with-grades')
        if not {s['stage'] for s in raw.get('stages',[])} <= set(rubric_ids):errors.append('parent-rubric-omits-participant-stage')

        relevant=[g for g in parent_rubric['criteria'] if case in g.get('cases',[])]
        if not relevant:errors.append('case-has-no-parent-criteria')
        expected={g['id'] for g in relevant}
        if receipt.get('component_partial'):
            requested=set(receipt.get('criterion_ids',[]))
            if not requested or not requested<=expected:errors.append('invalid-component-criteria')
            expected=requested
        actual={g['id'] for g in receipt['grades']}
        if actual!=expected:errors.append('scoped-parent-criteria-mismatch')
        parent_grades={g['id']:g for g in parent['grades']}
        child_rubric={g['id']:g for g in rubric['criteria']}
        for g in receipt['grades']:
            if g!=parent_grades.get(g['id']):errors.append('scoped-grade-differs-from-parent')
            definition=next((x for x in relevant if x['id']==g['id']),None)
            if definition!=child_rubric.get(g['id']):errors.append('scoped-rubric-differs-from-parent')
        # A child cannot hide an omitted failed stage by pointing to a shortened raw file.
        raw_path=located(parent['raw_path'],parent_dir)
        if digest(raw_path)!=parent['raw_sha256']:errors.append('parent-raw-hash-mismatch')
        if json.loads(raw_path.read_text())!=raw:errors.append('scoped-raw-differs-from-parent')
    elif path.name!='graded.json' and raw.get('stages'):
        errors.append('scoped-stage-parent-missing')
    stages=raw.get('stages')
    if not isinstance(stages,list) or not stages:return errors
    if any(not isinstance(g.get('cases'),list) or not g['cases'] for g in rubric.get('criteria',[])):
        errors.append('staged-criterion-case-binding-missing')
    if not any(case in g.get('cases',[]) for g in rubric.get('criteria',[])):
        errors.append('staged-case-has-no-criteria')
    ids=[s['stage'] for s in stages]
    if len(ids)==1 and 'prompt' in inputs and 'prompts' not in inputs:
        inputs={**inputs,'prompts':{ids[0]:inputs['prompt']}}
    if len(ids)!=len(set(ids)):errors.append('duplicate-participant-stage')
    if not receipt.get('parent_trial') and not set(ids)<={g['id'] for g in rubric.get('criteria',[])}:
        errors.append('whole-trial-rubric-omits-participant-stage')
    if set(ids)!=set(inputs.get('prompts',{})):errors.append('stage-input-coverage-mismatch')
    stage_root=located(receipt['raw_path']).parent/'control'
    on_disk={p.parent.name for p in stage_root.glob('*/receipt.json')}
    if set(ids)!=on_disk:errors.append('stage-artifact-coverage-mismatch')
    if receipt.get('fork_manifest_path'):
        manifest_path=located(receipt['fork_manifest_path']);require(manifest_path)
        if digest(manifest_path)!=receipt.get('fork_manifest_sha256'):errors.append('fork-manifest-hash-mismatch')
        manifest=json.loads(manifest_path.read_text())
        source_trial=located(manifest['source_trial'])
        fork_stage=manifest['fork_stage']
        if fork_stage not in ids:errors.append('fork-stage-not-present')
        else:
            preserved=ids[:ids.index(fork_stage)]
            copied=set()
            for b in manifest['bindings']:
                source=located(b['source_path']);target=located(b['copy_path']);require(target)
                if digest(source)!=b['sha256'] or digest(target)!=b['sha256']:errors.append('fork-source-copy-mismatch')
                copied.add((source,target))
            for prior in preserved:
                for name in ('receipt.json','prompt.txt','stdout.jsonl','before.graph.json','after.graph.json'):
                    pair=(source_trial/'control'/prior/name,stage_root/prior/name)
                    if pair not in copied:errors.append('fork-prior-artifact-binding-missing')
    current=inputs.get('initial_graph')
    for s in stages:
        base=stage_root/s['stage']
        files={'prompt_sha256':'prompt.txt','before_sha256':'before.graph.json','after_sha256':'after.graph.json','stdout_sha256':'stdout.jsonl'}
        require(base/'receipt.json')
        if json.loads((base/'receipt.json').read_text())!=s:errors.append('stage-receipt-differs-from-participant')
        for key,name in files.items():
            p=base/name;require(p)
            if digest(p)!=s.get(key):errors.append('stage-declared-hash-mismatch')
        before=json.loads((base/'before.graph.json').read_text());after=json.loads((base/'after.graph.json').read_text())
        if before!=current:errors.append('stage-state-chain-broken')
        current=after
        if (base/'prompt.txt').read_text()!=inputs['prompts'].get(s['stage']):errors.append('stage-prompt-differs-from-input')
        if s.get('exit_code')!=0 or s.get('timed_out') or s.get('result',{}).get('is_error'):errors.append('stage-process-failed')
        if s.get('data_changed')!=((base/'before.graph.json').read_bytes()!=(base/'after.graph.json').read_bytes()):errors.append('stage-change-flag-mismatch')
    return errors
