# Design Graph Spec Comparison

**Date:** 2026-09-15
**Type:** note

## Summary

Compared this tool against `~/Downloads/design-graph-spec.md` (v0.1 draft, "Design-Theory Graph"). Verdict: use the current tool first. The spec is a leaner re-cut of the same idea with better authoring ergonomics, not a different capability. On dependency invalidation, versioned review receipts, evidence checks and source fidelity the current tool is ahead. On the "what is missing" view and the write loop the spec is cleaner, and those pieces are cheap to add.

## Details

### Shape comparison

| Axis | Spec | Current tool |
|---|---|---|
| Node kinds | 2 fixed (`def`, `clm`), evidence in phase 3 | 8 declared, extensible (`entity`, `operation`, `claim`, `question`, `source`, `case`, `trace`, `check-result`) |
| Edge types | 5 fixed | 11 declared, extensible, plus `depends-on` / `extracted-from` |
| Questions | A `clm` with status `open` | First-class type with answer shapes, coverage, readiness |
| "Holes" | `def` status `open` (name, no body) | No equivalent. Every node needs text |
| Storage | One Markdown+YAML file per node, `edges.yaml`, SQLite index | Single `graph.json` with embedded audit log |
| Write loop | diff → `propose` (effects report) → `apply` → render → git commit | batch → `apply --expect REV` (atomic, audited). No dry run, no effects report, no git |
| Primary read | `frontier` (one aggregated work list) | Spread across `check`, `questions`, `review`, `history` |
| Invalidation | Only on `supersede`, via `mentions` | Any semantic edit, transitively along declared dependencies, with version-bound review receipts |
| Justification | `established` requires a `justifies` in-edge (blocking) | `accepted` is the user's decision. Missing evidence is an informational finding |
| Evidence | Phase 3: executable runner, pass/fail demotes claims | Present now: finite trace checks, formal model, fingerprinted staleness |
| Source fidelity | Not addressed | Central: agent contract, LLM trial receipts, 80 acceptance cases |
| Viewer | Frontier dashboard, node page, module view, one-field editing | Cytoscape network, inspector, search, history, review queue. Read-only |
| Rendered docs | `docs/` regenerated on apply | None |
| Lint | Body length, one proposition per claim | None |

### The spec's three core computations

| Computation | Current tool | Gap |
|---|---|---|
| Dangling references | Impossible by design; unknown endpoints reject the batch | Spec says dangling refs must be allowed and surfaced |
| Holes and obligation gaps | Hardcoded findings only (`unanchored-claim`, `ungoverned-operation`, `orphan-anchor`, `unconnected-question`) | No "open" hole status, no configurable obligation templates |
| Supersession debt | Stronger via `impact` and `needs-review`, but only along `depends-on` / `extracted-from` | Retiring an entity does not list the claims `about` or `governs` it |

### Ideas worth adopting regardless

| ID | Idea | Effort |
|---|---|---|
| I1 | `frontier` command and viewer landing page composed from `check`, `questions`, review queue, proposed claims, last changes | Low |
| I2 | `apply --dry-run` with an effects report (new findings, newly `needs-review`, resulting revision) | Low |
| I3 | Lint: one proposition per claim, body length | Low |
| I4 | Debt listing on retirement or revision: current claims `about`/`governs` the retired node, as review items | Low |
| I5 | Obligation templates in config, generalising the hardcoded findings, with a `promote` op | Medium |
| I6 | Inline `[[id]]` references in text deriving `about` edges; unresolved references become a finding | Medium |
| I7 | Frontier size over time from the audit log | Low |

Not adopting: two-kind collapse, blocking justification for accepted claims, per-node file storage and rendered docs (defer), auto git commit.

## Follow-ups

- Same day: repo reorganised into `theorygraph/` package, `projects/morphisms/`, `tests/`, `docs/`; `tg` installed in `~/bin`; project registry (`tg projects`, `tg new`, `tg use`); `/theory` skill in dotfiles.
- Use the tool on a real Morphisms design session before building I1/I2.
