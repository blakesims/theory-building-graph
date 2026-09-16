"""Validate acceptance-package structure, NOT implementation compliance."""
import json
from pathlib import Path
import sys as _path_sys
_path_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.paths import RepositoryPath as Path
root=Path(__file__).resolve().parent
suite=json.loads((root/'cases.json').read_text());cases=suite['cases'];ids=[c['id'] for c in cases]
assert len(cases)==80 and len(set(ids))==80
required={'id','group','title','phase','mechanism','arrange','actions','assertions','must_not','assumptions','oracle_kind','implementation_status'}
for c in cases:
 assert required<=c.keys(),c['id']
 assert c['actions'] and c['assertions'] and c['must_not'],c['id']
 assert c['phase'] in ('P1','P2')
 assert c['oracle_kind']=='behavioral-specification'
 assert c['implementation_status']=='not-assessed'
for f in ('CONTRACT.md','IMPLEMENTER.md','REVIEW.md'):assert (root/f).is_file()
print('PASS:80 unique, complete behavioral test specifications and linked handoff documents. Engine compliance not evaluated.')
