# Theory graph build

The project is now `/Users/blake/projects/theory-building-graph`, with a private
remote at https://github.com/blakesims/theory-building-graph. The theory graph runs
at http://127.0.0.1:8767; the original model notebook remains separate on 8766.

## What changed

- Durable, atomic CLI edits with revision checks, audit history, and crash/concurrent
  writer tests.
- Explicit dependency propagation, version-bound review, question readiness and
  answer resolution. Topic links are not treated as logical dependencies.
- Optional finite checks for authority, scopes, cardinality and bounded obligations,
  with witnesses, unknowns, vacuity and stale evidence shown explicitly.
- Generic replay of authored finite transition models for the design examples.
- A compact agent contract and retrieval workflow, plus a graph inspector for
  readiness, scoped findings and dependency impact. Actual browser testing observed
  a new node and relation become visible after a CLI write on an isolated graph.
- An acceptance runner that distinguishes mechanical coverage from actual recorded
  agent trials and validates source, rubric, stage and parent evidence bindings.

## Validation

The current acceptance report records all **80 cases and 22 criteria passed**.
See `acceptance/run-report.json` for the evidence attached to each case, and
`acceptance/STAGED-RECEIPTS.md` for the meaning of scoped and composite evidence.
Final verification: **256 tests passed, no skips**; baseline checks passed with the
live graph unchanged. Fable independently reran the suite and acceptance checks.
Its final gate review verifies all identified blocking findings closed, including
parent verdict laundering and omitted failed criteria. See
[the final review](reviews/FABLE-5.1-GATE-CLOSURE.md).

Run locally:

```sh
make test
make acceptance
make baseline
python3 acceptance/benchmark.py
```

These checks validate saved LLM trial receipts; they do not rerun paid model calls.
Fresh evaluation runners and their protocols are in `acceptance/` and `fixtures/`.
The 3,050-node synthetic benchmark measured local walks and impact queries around
5–6 ms and the question page around 0.72 seconds on this machine. These are local
measurements, not an unbounded scaling guarantee.

## What the evidence establishes

The original agent trials exposed real failures: actor misattribution, premature
acceptance, hidden extra reads, and mixing a resolved policy question with a separate
open question. General authoring guidance was revised and fresh trials were run.
Original failures, prompts, outputs and grades remain available for comparison.

Some cases pass through scoped evidence from sessions that failed elsewhere.
S01 combines unchanged earlier stages under authoring/6 with a new decision stage
under authoring/9. S08 combines a paced read under authoring/8, a proposal under
/6, and a separate browser observation. Neither is represented as a single flawless
continuous session. Graders are disclosed contributors and were not arm-blinded.

The graph/prose experiments do **not** establish that graphs are better. Both
recovered the core semantic change; prose used fewer resources in the measured
maintenance pair. Separate model review timings were roughly 43 versus 44 seconds.
Human review time remains unmeasured. The supported benefit is explicit retrieval,
dependency and check state, with inspectable history and bounded counterexamples.

## Boundaries

This implements a tool for developing the theory, not the Morphisms runtime.
It does not automatically prove natural-language consistency, source fidelity,
unbounded reachability, or universal agent reliability. The finite model and pattern
extractions must be authored and assessed. A passing example cannot ratify them.

The user's design remains revision 16. The only deliberate live data refresh in
this build reran three synthetic checks and retained their prior results as history;
all non-result nodes were unchanged. The current live theory still has legitimate
open questions and a potential conflict. Acceptance completion does not settle them.

Fable 5.1 reviewed through the existing Claude Code pane in tmux `projects`.
Reports and responses are retained in `reviews/`.
