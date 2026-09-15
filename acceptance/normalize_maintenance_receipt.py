#!/usr/bin/env python3
"""Bind an observed maintenance study to its original participant and reviewer artifacts.
No participant artifacts or grades are changed. No missing measurements become zero.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'reviews'/'maintenance'; RAW=BASE/'raw'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def normalize():
    bindings={};arms={};grades=[];omitted=[]
    for arm in ('graph','prose'):
        grade_path=BASE/f'graded-{arm}.json';review=json.loads(grade_path.read_text())
        run_path=RAW/'control'/f'{arm}-run.json';run=json.loads(run_path.read_text())
        if review['status']!='completed-independent-semantic-review' or review['core_semantic_score']!=review['core_semantic_possible'] or not all(g['score']==1 and g['excerpt'] for g in review['core_semantic_grades']):
            raise ValueError('No completed passing core semantic review: '+arm)
        if run['exit_code']!=0 or run['result']['is_error'] or not run['tool_metrics_available'] or run['tool_call_count']<1:raise ValueError('No actual successful tool-enabled maintenance: '+arm)
        for relative,expected in review['artifact_hashes'].items():
            path=RAW/relative
            if not path.exists():
                if '__pycache__' in path.parts or path.name.endswith('.lock'):
                    omitted.append({'path':str(path.relative_to(ROOT)),'original_hash':expected,'reason':'Transient bytecode/lock omitted from archived study; not a theory, prompt, stream or grader input.'});continue
                raise ValueError('Missing persistent graded artifact: '+relative)
            if digest(path)!=expected:raise ValueError('Graded artifact changed: '+relative)
            bindings[str(path.relative_to(ROOT))]=expected
        bindings[str(grade_path.relative_to(ROOT))]=digest(grade_path)
        arms[arm]={'raw_receipt':str(run_path.relative_to(ROOT)),'semantic_review':str(grade_path.relative_to(ROOT)),
                   'model':review['model'],'metrics':review['metrics'],'mechanical_receipt':review['mechanical_receipt'],
                   'observability_grades':review['observability_grades'],'review_notes':review['review_notes']}
        grades.extend({**g,'id':arm+'/'+g['id'],'source_review':str(grade_path.relative_to(ROOT))} for g in review['core_semantic_grades'])
    for name in ('comparison.md','raw/pair-1/file-hashes.json','raw/control/graph-before.json','raw/control/prose-before.json'):
        path=BASE/name;bindings[str(path.relative_to(ROOT))]=digest(path)
    receipt={'receipt_version':1,'id':'paired-maintenance-1','cases':['S07'],'grader':{'agent':'/root/evidence_sessions','independence':'Did not author maintenance fixture or participant answers; tool-building team member, not format-blinded. Normalization does not change original scores.'},'status':'completed','passed':True,'hard_failures':[],
       'criterion':'A fair independently observed graph/prose comparison with successful bounded core theory maintenance and measured agent costs; graph superiority is not required.',
       'rubric_path':'fixtures/maintenance/grader-only.json','rubric_sha256':digest(ROOT/'fixtures'/'maintenance'/'grader-only.json'),
       'grades':grades,'arms':arms,'artifact_hashes':dict(sorted(bindings.items())),'omitted_transient_artifacts':omitted,
       'measured_outcome':{'graph_core':6,'prose_core':6,'core_possible':6,'graph_accuracy_advantage_established':False,
                          'graph_observability':2,'prose_observability':1,'observability_possible':2,
                          'graph_mechanical':13,'prose_mechanical':12,'mechanical_possible':13,
                          'prose_parser_limitation':'Review flags exist on all four correct dependents; parser read only Currency. One label ambiguity remains; no missed dependencies claimed.'},
       'scope':{'fixture_claims':30,'observed_pairs':1,'independent_participants':2,'recommended_pairs':2,
                'participant_steps':'Real retrieval and writes occurred before grading; no evaluator-applied proposals.',
                'review_independence':'Reviewer did not author fixture or participant answers; member of building team, not representation-blinded.',
                'general_superiority':'not-established','current_engine_retest':'Historical receipt bound to the archived engine snapshot, not a fresh run after subsequent fixes.',
                'human_correction_seconds':None,'human_correction_count':None,'human_review_seconds':None,
                'cost_boundary':'Agent whole-pass wall time, tool calls, token exposure and file diff measured. Read/write/review phase timings and human correction timing unmeasured.',
                'procedural_isolation_exception':'Prose participant created its own /tmp diff scratch file; no cross-arm or grader access observed.'}}
    path=BASE/'study-receipt.json';path.write_text(json.dumps(receipt,indent=2)+'\n');print(path)
if __name__=='__main__':normalize()
