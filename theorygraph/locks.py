"""Stable per-graph lock locations outside the graph's repository."""
import hashlib
import os
from pathlib import Path


def lock_path(graph_path, suffix='.lock'):
    path = Path(graph_path).resolve()
    key = hashlib.sha256(os.fsencode(path)).hexdigest()
    base = Path(os.environ.get('XDG_RUNTIME_DIR') or Path.home() / '.cache')
    directory = base / 'theory-graph' / 'locks' / key
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory / (path.name + suffix)
