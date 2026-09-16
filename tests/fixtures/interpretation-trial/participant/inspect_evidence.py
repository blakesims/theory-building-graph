"""Read saved computation freshness through the production checker API."""
import json,graph,tracecheck
from pathlib import Path
print(json.dumps(tracecheck.evaluations(graph.load(Path('evidence.graph.json')),'c'),indent=2))
