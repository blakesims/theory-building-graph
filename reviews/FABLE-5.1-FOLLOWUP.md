# Fable 5.1 focused follow-up review

Reviewed the uncommitted working tree on top of `8f8f229`. Live `graph.json` sha256 prefix `1b894f7d3676f6e9` before and after every command. No implementation file edited. Reproduction: `python3 reviews/fixtures/fable-5.1/probes.py` (original P-probes) and `python3 reviews/fixtures/fable-5.1/followup-probes.py` (new N-probes).

## State

The working tree changed while I reviewed, as `reviews/FOLLOWUP_PROGRESS.md` discloses. Two snapshots, both with the live graph unchanged:

| Snapshot | Unit tests | Acceptance | Criteria | Partial cases |
|---|---|---|---|---|
| Start of this pass | 183, OK, no skips | 65 passed / 15 partial | 16 / 6 incomplete | E01, E07, M01–M08, S01–S05 |
| After M/E receipts arrived | 202, OK, no skips | 74 passed / 6 partial | 18 / 4 incomplete (AC15, AC16, AC17, AC22) | S01–S05, S07 |

`all_passed` is `false` in both. No case reports `failed`. The M/E receipts are mapped from `acceptance/evidence-mapping.json` to `reviews/interpretation/graded.json`; the progress note's `interpretation-mapping.json` does not exist under that name. S07 moved from passed to partial between snapshots, consistent with the note that the maintenance evidence is still being bound. The fix verification below is independent of this movement: every probe was rerun on the current tree and the results were identical across both snapshots.
- HTTP smoke on a temporary copy of the live graph (`serve --port 8799`): `/api/status`, `/api/readiness`, `/api/impact`, `/api/check`, `/api/questions`, `/api/evaluations` all return 200 with well-formed JSON. `index.html` now references `api/readiness`, `api/impact`, `api/check`. Rendering itself not verified here.

## Original findings: status

| ID | Status | Evidence |
|---|---|---|
| H1 | Closed, with hardening note N2 | `run.py:64-74` caps agent-mechanism cases at partial unless a mapping with `evidence_kind: agent-receipt` points at a completed, passed, hard-failure-free receipt file. E01, E07, M01–M08 now report `partial`. Fourteen agent cases report `passed` on receipts I did not re-grade (see Unverified). |
| H2 | Closed | P3: Q2 `blocked` with reason `resolution-not-satisfied`; `dependency.py:142-143` uses `resolution()` for question prerequisites, default `requires: ["answered"]`. N4: explicit `partial-answer` requirement honoured. |
| H3 | Closed | P1: reviewing unchanged B leaves Q `current` with receipt intact. N1: review plus content edit still propagates. N2: reactivation historical→current propagates. N3: explicit `needs-review` on a prerequisite propagates. `dependency.py:284`. |
| M1 | Closed | P9: text output shows `checked events: []`, `vacuous: True`, `evidence_basis`, `empirical_support: False`, diagnostic `no-matching-event`; `may` marked `permission_only`; no `known-defect-unexplained` on vacuous or permission-only results. Legacy exclusive_actor still refuses vacuity (`test_P9_legacy_stays_nonvacuous`). |
| M2 | Closed | P28: one `answer-state-drift` finding per condition, carrying `stored_state` and `derived_resolution`. `unsupported-answered-state` removed. |
| M3 | Closed | Live `tg questions` header 3021 → 499 bytes, total 4266 → 1986; per-question `answer/readiness/blockers` line; findings print `[severity]` and `; suppressed`. |
| M4 | Closed | P2: custom `derived-from` edge add flags B; `dependency.py:309` uses the declaration; edge-type semantic edits also root (`dependency.py:291-297`). |
| M5 | Open by design, low | P4 unchanged. `dependency-fixes.md` argues trace scope `all` is not a comparison domain. Acceptable, but the pair finding still says only `unsupported scope semantics`; it should tell the author to declare the scope in `formal_model` with an existence witness. The exemption at `graph.py:172` remains inconsistent with `scope_overlap`. |
| M6 | Closed | P20: saved evaluation counts, `about` edge to a trace does not. N7: a stale receipt drops coverage to `none` with the stale evaluation listed. `tracecheck.coverage()`. |
| M7 | Closed | P32: `policy-conflict` ID stable across an unrelated revision; `graph.py:186` excludes `computed_revision`. |
| M8 | Partly open, low | A07 now exercises permission versus bounded obligation. `test_only_and_never_same_role_exposes_overconstraint` added. D03, M08 and S08 tests unchanged. |
| L1 | Closed | P11: redefining the witness-only role stales the receipt; `tracecheck.py:92-100`. |
| L2 | Closed | P26: `meta must be an object on A`, rejected atomically at `graph.py:27`. |
| L3 | Closed | N5: deleting an entity that only coincides with a trace-local label succeeds; deleting a role referenced by a pattern is refused. `graph.py:234-256`. |
| L4 | Accepted as intentional | P24 unchanged; `dependency-fixes.md` states the rule. Add one sentence to DEPENDENCY-SCHEMA.md. |
| L5 | Closed | N6: historical claim with undeclared role produces no `undeclared-pattern-reference`. `graph.py:169`. |
| L6 | Closed | P31: `only(r)` vs `never(r)` → `no-inconsistency-established`, `possible_overconstraint: true`. |
| L7 | Closed | P5: `add/update require an explicit value`, no write. |
| L8, L9, L10 | Not in scope | L9 partially addressed by `index.html` changes, unverified visually. |

## New issues

### N1 Live graph: all three saved receipts are now stale and the central claim is reported untested

Bumping `CHECKER_VERSION` to `exclusive-actor/3` and `formalcheck.VERSION` to `formal-fragment/2` is correct, and it correctly stales `check-steward-next`, `check-orchestrator-next` and `check-missing-role`. Consequence on the live graph: `tg check` now reports `untested-claim` for `steward-chooses-next-work`, which was clean before, because the fixtures link to the claim with `informs`, which the new coverage helper does not treat as declared evidence.

- Repro: `./tg check` (six findings, five untested); `./tg node check-steward-next` shows `check freshness: stale`.
- Severity: medium as a live-data state change, not a code defect.
- Remedy: a deliberate write is needed. Either re-run `./tg evaluate steward-chooses-next-work <fixture> --save` for the three fixtures, or relink fixtures with `tests` edges if you want declared evidence without receipts. Your call; I made no write.

### N2 The acceptance gate trusts a stored `passed` field on receipts

`run.py:69-71` accepts a receipt when `status == completed`, `passed is True`, `grades` non-empty and `hard_failures` empty. The four blind-trial graded receipts were edited in the working tree to add `passed: true` (plus an ASCII re-escape of em-dashes; the excerpts are unchanged). I recomputed `session_evaluation.validate_receipt` on all eight graded/bound files: stored `passed` equals the computed value in every case, so nothing was falsified. But the gate should derive the verdict rather than read it.

- Remedy: in `run.py`, call `validate_receipt()` (or the author-trial equivalent) and require every grade score to be 1, and verify the hash bindings that `test_agent_receipts.py` checks, so the report cannot pass on a hand-edited field even when the tests are omitted from a mapping.
- Severity: low-medium, hardening.

### N3 `requires` vocabulary is not validated; legacy question edges are now permanently blocked

`dependency.validate()` checks that `requires` is a non-empty list of strings only. N4c: `requires: ["answerd"]` loads and blocks forever with `resolution-not-satisfied`. N4b: a pre-fix edge `Q2 -depends-on-> Q1` with `requires: ["accepted"]` is now permanently blocked because question prerequisites are judged by resolution vocabulary.

- Remedy: validate `requires` against the node type's declared states for claims and against `{open, candidate-answer, partial-answer, answered, retired}` for questions; reject or migrate `accepted` on question edges with a named error. The live graph has no `depends-on` edges, so no live data is affected today.
- Severity: low.

### N4 S06 and S07 evidence provenance should be stated in the mapping notes

S06 passes on `reviews/blind-trials/graded-graph-*.json`, whose `retrieval_calls` is 0: the participant received a packet and never used the graph tool. That satisfies the case text ("compact current graph plus addressable history"), but the mapping note should say the tool was not exercised. S07 passes on `reviews/maintenance/study-receipt.json`, which I did not review.

- Severity: informational.

## Unverified in this pass

- Browser rendering of the extended inspector (root is running that smoke). Only the HTTP routes were exercised.
- Contents of the author-trial receipts v2–v5 beyond the summary fields of `graded-operation-modality.json` v1 versus v3 (v1: hard failure, v3: 3/3 passed). I did not re-grade any participant answer.
- `reviews/maintenance/`, `reviews/interpretation/`, `fixtures/multiturn/` and their tests (`test_maintenance_*`, `test_interpretation_receipts.py`, `test_multiturn_protocol.py`, `test_browser_receipt.py`): they pass without skips, meaning receipts exist, but I did not read them. Per your request, they are not assessed as final.
- New documents `AGENTS.md`, `AGENT_CONTRACT.md`, `PRODUCT.md`, and `acceptance/receipt_validation.py`, `run_maintenance_trials.py`, `run_multiturn_trials.py`.
- Scale fixture, replay CLI, and the sixty-five case specs not read in the first pass remain unread.

## Commands executed

```sh
cd /Users/blake/projects/theory-building-graph
sha256sum graph.json; git status --short; git diff -- dependency.py formalcheck.py tracecheck.py graph.py acceptance/run.py test_formalcheck.py test_tracecheck.py
python3 reviews/fixtures/fable-5.1/probes.py
python3 reviews/fixtures/fable-5.1/followup-probes.py
python3 -m unittest discover -s . -p 'test_*.py'
python3 acceptance/run.py --report /tmp/.../run-report-2.json
./tg check; ./tg questions; ./tg node check-steward-next; ./tg evaluate steward-chooses-next-work fixture-steward-next
cp graph.json /tmp/.../live-copy.json; python3 graph.py --file /tmp/.../live-copy.json serve --port 8799; curl http://127.0.0.1:8799/api/{status,readiness,impact,check,questions,evaluations}
git diff -- reviews/blind-trials/; python3 -c 'session_evaluation.validate_receipt(...) for each blind receipt'
```
