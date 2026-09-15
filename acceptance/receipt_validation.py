"""Fail-closed empirical receipt checks. Semantic grading remains independent work."""
import hashlib
import json
from pathlib import Path
try:
    from .staged_receipts import staged_errors
except ImportError:
    from staged_receipts import staged_errors

def _read(root, relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('evidence path outside repository')
    return path,json.loads(path.read_text())

def grade_errors(receipt, case=None, expected_ids=None):
    errors=[]
    if receipt.get('status')!='completed':errors.append('not-completed')
    if receipt.get('passed') is not True:errors.append('not-passed')
    if receipt.get('hard_failures')!=[]:errors.append('hard-failures-missing-or-present')
    if not receipt.get('grader'):errors.append('missing-grader')
    if case is not None and case not in receipt.get('cases',[]):errors.append('case-not-covered')
    grades=receipt.get('grades')
    if not isinstance(grades,list) or not grades:return errors+['missing-grades']
    ids=[g.get('id') for g in grades if isinstance(g,dict)]
    if len(ids)!=len(grades) or any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):errors.append('invalid-or-duplicate-grade-ids')
    if expected_ids is not None and set(ids)!=set(expected_ids):errors.append('rubric-coverage-mismatch')
    for g in grades:
        if not isinstance(g,dict):continue
        if type(g.get('score')) is not int or g['score']!=1:errors.append('grade-not-passed')
        if not isinstance(g.get('excerpt'),str) or not g['excerpt'].strip():errors.append('missing-excerpt')
        if not isinstance(g.get('explanation'),str) or not g['explanation'].strip():errors.append('missing-explanation')
    return sorted(set(errors))

def validate_receipt_file(root,relative,case, *, _component=False, _seen=()):
    root=Path(root);errors=[]
    try:
        path,r=_read(root,relative)
        if str(path) in _seen:raise ValueError('cyclic receipt components')
        _seen=(*_seen,str(path))
        if not isinstance(r,dict):raise ValueError('receipt must be object')
        errors.extend(grade_errors(r,case))
        if all(k in r for k in ('raw_path','input_path','rubric_path')):
            bindings=[('raw',r['raw_path'],r.get('raw_sha256')),('input',r['input_path'],r.get('input_sha256')),('rubric',r['rubric_path'],r.get('rubric_sha256'))]
        elif r.get('arms') and r.get('rubric_path'):
            bindings=[('rubric',r['rubric_path'],r.get('rubric_sha256'))]
        elif path.name.startswith('graded-') and r.get('id'):
            version=path.parent.name
            base=Path('fixtures')/version/r['id']
            bindings=[('raw',str(path.with_name(path.name[7:]).relative_to(root.resolve())),r.get('raw_receipt_sha256')),('input',str(base/'input.json'),r.get('input_file_sha256')),('rubric',str(base/'grader-only.json'),r.get('rubric_sha256'))]
        else:raise ValueError('missing explicit provenance binding')
        data={}
        for kind,rel,expected in bindings:
            item=(root/rel).resolve()
            if not item.is_relative_to(root.resolve()):raise ValueError('evidence path outside repository')
            content=item.read_bytes()
            if not expected or hashlib.sha256(content).hexdigest()!=expected:errors.append(kind+'-hash-mismatch')
            # Input can be a task Markdown rather than JSON; raw/rubric must parse.
            if kind=='rubric':data[kind]=json.loads(content)
            elif kind=='input':
                try:data[kind]=json.loads(content)
                except json.JSONDecodeError:data[kind]={}
            elif kind=='raw':
                try:data[kind]=json.loads(content)
                except json.JSONDecodeError:
                    entries=[json.loads(line) for line in content.decode().splitlines() if line.strip()]
                    finals=[entry for entry in entries if isinstance(entry,dict) and entry.get('type')=='result']
                    if not finals:raise ValueError('raw JSONL has no terminal result')
                    data[kind]=finals[-1]
        for rel,expected_hash in r.get('artifact_hashes',{}).items():
            artifact=(root/rel).resolve()
            if not artifact.exists():artifact=(path.parent/rel).resolve()
            if not artifact.is_relative_to(root.resolve()):raise ValueError('artifact outside repository')
            if hashlib.sha256(artifact.read_bytes()).hexdigest()!=expected_hash:errors.append('artifact-hash-mismatch:'+rel)
        rubric=data['rubric']
        expected=list(rubric.get('required_grades',[]))+[g['id'] for key in ('criteria','regression_criteria','cross_cutting','rubric') for g in rubric.get(key,[])]
        if not expected:errors.append('empty-rubric')
        errors.extend(grade_errors(r,case,expected))
        raw=data.get('raw',{})
        if raw.get('stages') or r.get('parent_trial'):
            errors.extend(staged_errors(root,path,r,raw,data.get('input',{}),rubric,case))
        if r.get('component_partial') and not _component:errors.append('partial-component-not-full-evidence')
        if r.get('components'):
            errors.extend(_component_errors(root,path,r,rubric,case,_seen))
        if r.get('arms'):
            required_arms={i.split('/')[0] for i in expected}
            if set(r['arms'])!=required_arms:errors.append('aggregate-arm-coverage-mismatch')
            for arm,info in r['arms'].items():
                for field in ('raw_receipt','semantic_review'):
                    if info.get(field) not in r.get('artifact_hashes',{}):errors.append('aggregate-unbound-'+field)
                _,arm_raw=_read(root,info['raw_receipt'])
                _,review=_read(root,info['semantic_review'])
                if arm_raw.get('exit_code')!=0 or arm_raw.get('timed_out'):errors.append('aggregate-participant-process-failed')
                source={g['id']:g for g in review.get('core_semantic_grades',[])}
                for g in r['grades']:
                    if g['id'].startswith(arm+'/'):
                        original=source.get(g['id'].split('/',1)[1],{})
                        if any(g.get(k)!=original.get(k) for k in ('score','excerpt','explanation')):errors.append('aggregate-grade-differs-from-original')
        if 'exit_code' in raw and raw['exit_code']!=0:errors.append('participant-process-failed')
        if raw.get('parse_error') or raw.get('is_error') or raw.get('claude_result',{}).get('is_error'):errors.append('participant-result-error')
        if raw.get('proposal',{}).get('proposed_operations') and raw.get('apply',{}).get('returncode')!=0:errors.append('proposal-not-applied')
        elif 'proposal' in raw and not raw['proposal'].get('proposed_operations') and raw.get('apply',{}).get('unchanged') is not True:errors.append('no-edit-receipt-missing')
        return {'valid':not errors,'errors':sorted(set(errors)),'receipt':relative}
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        return {'valid':False,'errors':['invalid-receipt:'+str(exc)],'receipt':relative}

def agent_evidence(root,mappings,case):
    """One FULL agent mapping must have every declared receipt valid; no any-receipt shortcut."""
    valid=[];errors=[];full=False
    for mapping in mappings:
        if mapping.get('evidence_kind')!='agent-receipt':continue
        receipts=mapping.get('receipts',[])
        checked=[validate_receipt_file(root,p,case) for p in receipts]
        valid.extend(c['receipt'] for c in checked if c['valid'])
        errors.extend(c for c in checked if not c['valid'])
        if mapping.get('coverage')=='full' and receipts and all(c['valid'] for c in checked):full=True
    return {'full':full,'valid_receipts':sorted(set(valid)),'errors':errors}

def author_receipt_errors(raw,graded,rubric,input_packet,initial):
    expected=[g['id'] for key in ('criteria','regression_criteria') for g in rubric.get(key,[])]
    errors=grade_errors(graded,expected_ids=expected)
    if initial!=input_packet.get('graph'):errors.append('replay-input-differs-from-participant-input')
    if raw.get('proposal',{}).get('proposed_operations') and raw.get('apply',{}).get('returncode')!=0:errors.append('original-apply-failed')
    return sorted(set(errors))


def _component_errors(root,path,receipt,rubric,case,seen):
    errors=[];components=receipt['components'];ids=[c['id'] for c in components]
    if len(ids)!=len(set(ids)):errors.append('duplicate-evidence-component')
    slots=rubric.get('required_evidence_slots',{})
    if set(slots)!={g['id'] for g in rubric['criteria']}:errors.append('component-slot-coverage-mismatch')
    bound=receipt.get('artifact_hashes',{});loaded={}
    for c in components:
        if c['receipt'] not in bound:errors.append('component-receipt-unbound')
        checked=validate_receipt_file(root,c['receipt'],c['case'],_component=True,_seen=seen)
        if not checked['valid']:errors.extend('component:'+e for e in checked['errors'])
        _,child=_read(root,c['receipt']);loaded[c['id']]=child
        if c['case']!=case or bool(c.get('partial'))!=bool(child.get('component_partial')):errors.append('component-scope-mismatch')
        if set(c['criterion_ids'])!={g['id'] for g in child['grades']}:errors.append('component-criteria-mismatch')
        if child.get('parent_trial'):
            declaration={k:child[k] for k in ('parent_trial','parent_graded_sha256','parent_hard_failures')}
            if declaration not in receipt.get('parent_disclosures',[]):errors.append('component-parent-failure-undisclosed')
    used=set()
    for slot,definition in slots.items():
        cid=definition['component'];used.add(cid)
        if cid not in loaded:errors.append('missing-required-component');continue
        if not set(definition['criteria']) <= {g['id'] for g in loaded[cid]['grades']}:errors.append('missing-component-criterion')
        for p in definition.get('artifacts',[]):
            if p not in bound:errors.append('component-slot-artifact-unbound')
    if used!=set(ids):errors.append('unused-or-missing-evidence-component')
    return errors
