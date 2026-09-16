"""Resolve recorded pre-cleanup evidence paths without rewriting hash-bound receipts.

Only paths inside this checkout are translated. Temporary tamper-test roots keep
ordinary pathlib behavior, so containment and missing-artifact checks still apply.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELOCATIONS = json.loads((ROOT / 'tests/relocations.json').read_text())['moved']


class RepositoryPath(type(Path())):
    def __truediv__(self, other):
        path = super().__truediv__(other)
        try:
            rel = str(path.relative_to(ROOT))
        except ValueError:
            return path
        # Exact prose relocations take precedence over directory relocations.
        original = rel.removeprefix('tests/') if rel.startswith('tests/acceptance/') else rel
        if original in RELOCATIONS:
            return type(self)(ROOT / RELOCATIONS[original])
        for old, new in (('acceptance', 'tests/acceptance'),
                         ('fixtures', 'tests/fixtures'),
                         ('reviews', 'tests/fixtures/reviews')):
            if rel == old or rel.startswith(old + '/'):
                return type(self)(ROOT / (new + rel[len(old):]))
        return path
