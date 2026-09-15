# Fable 5.1 final focused review

Working tree on top of `2a70003`, uncommitted. Live `graph.json` is revision 16, sha256 prefix `304a456b032e16a1`, unchanged by anything I ran. No implementation file edited. Reproduction scripts: `reviews/fixtures/fable-5.1/probes.py` and `followup-probes.py` (the latter's N4b line now raises on purpose, see N3 below).

## Verdict on the implementation and evidence gate

**No blocking implementation issue found.** Every follow-up code finding (N2, N3, M5, L4, M8) is verified fixed with independent probes. The live refresh for N1 is exactly what was described. The receipt gate fails closed under every tamper I tried. Acceptance is honestly not all-passed: 76 passed, 4 partial (S01–S04), 3 criteria incomplete (AC15, AC16, AC17).

**One evidence-structure gap to close before any per-case carve-out from a failed staged trial (G1–G3 below).** The gate currently has no generic way to verify that a per-case receipt binds every stage of its parent trial or discloses the parent's hard failures, and the rubrics carry no criterion-to-case binding. Today this is harmless because no such carved receipt exists and S01–S04 are honestly partial. It becomes a hiding risk the moment one is produced.

## State

| Check | Result |
|---|---|
| `python3 -m unittest discover -s . -p 'test_*.py'` | 226 tests, OK, no skips |
| `python3 acceptance/run.py --report <tmp>` | 76 passed, 4 partial (S01–S04), 0 failed, `all_passed: false`; criteria 19 passed / 3 incomplete |
| Original probes P1–P32 | All fixed outcomes stable; P4 and P24 remain by-design as recorded in the follow-up |
| Live graph | Before/after snapshots and current file verified, see N1 |

## Follow-up findings verified

### N1 Live refresh (deliberate write, revisions 13–16)

- `reviews/live-refresh/before.graph.json` hashes to `1b894f7d3676f6e9`, the exact live hash I recorded in both earlier reviews. `after.graph.json` equals the current `graph.json` byte for byte.
- Every non-`check-result` node is identical before and after. Node types, edge types and the absence of `formal_model` are unchanged. Six edges added (three `checks` pairs), none removed.
- Revisions 13–15 are the three `evaluate --save` calls in `commands.json`; revision 16 is the audited batch in `retire-old-checks.json` that sets the three `exclusive-actor/1` results to `historical` with a stated reason. The three new results are `current` under `exclusive-actor/3` with the same outcomes as before (satisfies, violates, insufficient-information).
- `tg check` now reports four informational `untested-claim` findings, none on `steward-chooses-next-work`. Correct.

### N2 Receipt gate derives validity

`acceptance/receipt_validation.py` is used by `run.py` via `agent_evidence()`. Verified on a copied minimal root (`reviews/author-trials-v3/identity` plus its fixture):

| Tamper | Gate result |
|---|---|
| Clean copy | valid |
| One grade score 1 → 0, stored `passed` left true | `grade-not-passed` |
| One byte appended to `fixtures/.../input.json` | `input-hash-mismatch` |
| Raw receipt `exit_code` set to 1 | `participant-process-failed`, `raw-hash-mismatch` |
| Receipt asked to cover a case not in its `cases` list | `case-not-covered` |

Across all mapped cases, every receipt the gate accepts has an empty error list, and every receipt it rejects names why (the failed v1 multiturn receipts: `grade-not-passed`, `not-passed`, `hard-failures-missing-or-present`; the unbound blind `graded-*` files: `missing explicit provenance binding`). The four blind `graded-*.json` files are restored byte-for-byte (`git diff` empty); the `bound-*.json` wrappers carry the bindings and pass the gate for S06. `test_acceptance_receipt_gate.py` covers the same tamper classes plus path escape and aggregate rewrite. This closes N2.

### N3 `requires` vocabulary

`dependency.py:273-283`. Probed on load: question edge requiring `accepted` → rejected with the edge ID and the allowed resolution vocabulary; misspelled `answerd` → rejected; claim edge with a typo against declared `states` → rejected; claim type with no declared `states` → accepted, as DEPENDENCY-SCHEMA.md now states. No live data affected (no `depends-on` edges in the live graph). Closed.

### M5 Missing-scope diagnostic

P4 now reports: `Undeclared scope IDs: 'all'. Declare their justified semantics in formal_model.scopes. Use explicit members or justified nonempty evidence and containment/overlap facts; do not invent an all-scope witness.` Actionable. Closed as a diagnostic; the design position that trace scope `all` is not a comparison domain stands.

### L4 Schema documentation

DEPENDENCY-SCHEMA.md now states that invalidation traverses historical intermediates and that retired premises stay blockers even when `requires` names a retired status. Closed.

### M8 Test strength

- `test_replay.py` M08: replaced constant read-back with a two-axis fixture where changing `drive` does not change launch, and a wrong launch signal does not start. Establishes the mechanics claim.
- `test_replay.py` S08: no longer asserts a substring of its own command; asserts the read returned the node and left bytes unchanged.
- `test_tracecheck.py` D03: adds a failing witness bound to the specific session actor.
- A07: permission versus bounded obligation with an absent response, verified in the follow-up.
Closed for the items named. The `test_gaps_and_repairs` `supports`-edge case was superseded by the coverage helper tests.

## Receipt architecture audit: the pacing distinction

You asked me to scrutinise the rule that a failed pacing stage cannot invalidate unrelated completed scenarios but also cannot be hidden. What exists today:

- `reviews/multiturn/v1/design/graded.json` covers S01, S02, S03, S04, S08 as one receipt. Stages 01 (read-only pacing) and 02 (atomic proposal) scored 0; stages 03–07 scored 1. The gate rejects the whole receipt. `test_multiturn_receipts.py` asserts the failure is preserved and that all 7 stages are hash-bound. S01–S04 are therefore honestly `partial`.
- `reviews/multiturn/pace3/design` and `pace4/design` are single-stage reruns of stage 01, both passed, both `cases: ["S08"]`, not yet cited by any mapping.
- S08 currently reports `passed` on `reviews/author-trials-v4/graded-slow-next-step.json`, a single-turn proposal trial.

Gaps that would let a future carve-out hide a failure:

- **G1 No criterion-to-case binding.** `normalized-rubric.json` criteria have no `cases` field; the receipt's `cases` is a flat list. Nothing declares that stage 03 evidences S01 rather than S03. A per-case receipt could cite any passing stage for any listed case.
- **G2 Gate does not check stage completeness.** `receipt_validation.py` verifies the hashes a receipt declares but never reads `participant.json` to confirm every stage has bound `control/<stage>/` artifacts. A per-case receipt that omits the failed stage's artifacts passes. The v1 stage-chain check lives only in a hand-written test for v1.
- **G3 Parent failure not disclosed.** There is no `parent_trial` / `parent_graded_sha256` / `parent_hard_failures` field. A per-case receipt must have `hard_failures: []` to pass, so the parent's pacing failure would have nowhere to be recorded on the receipt itself.
- **G4 Rerun prompts are not the failed prompt.** pace3 inlines the authoring contract (removing the preliminary read that failed stage 01 in v1); pace4 adds a "Use supplied references directly" section under `authoring/8` that addresses the exact v1 failure. This is a legitimate input-contract repair, and it is disclosed in the prompt bytes, but a pass on pace4 is evidence under `authoring/8`, not under the conditions S01–S04 were attempted in. The full seven-stage design trial has not been rerun under `authoring/8`.

Recommended gate rule before any carve-out is mapped: a per-case receipt from a staged trial must (a) declare `parent_trial` and the parent `graded.json` hash, (b) copy the parent's `hard_failures` into a `parent_hard_failures` field that the gate verifies against the parent, (c) cite criteria that carry `cases` in the rubric, and (d) bind every stage listed in `participant.json`. Until that exists, S01–S04 should pass only on a full rerun of the design sequence, which is what the current partial status reflects.

**S08 specifically.** Reporting S08 `passed` on a single-turn trial while the only multi-stage pacing attempt failed and two targeted reruns are unmapped is the shape of the concern you described, even though nothing is hidden (v1 is retained and rejected). Either map pace3/pace4 with the contract version and the v1 failure cited, or hold S08 at partial. Not blocking; a mapping decision.

## Substantive receipt spot-check

`reviews/author-trials-v3/operation-modality.json` (D04, D06, A07): the raw proposal stores the user turn verbatim as `source-4` with `speaker: Blake` and an explicit note that "I" and "me" are not resolved to a role; both derived claims are `proposed` with `actor_scope: unresolved`; the earlier v1 hard failure (rewriting "I" as "steward" and accepting) is genuinely absent. The `answers` edge places `coverage` under `meta`, so the engine does not count it as a partial answer; harmless for the rubric, worth a note in the authoring contract.

Graders for the author, interpretation and maintenance receipts are disclosed as checker contributors and not arm-blinded. That limitation is recorded in the receipts and should stay in the final report.

## Limits and unverified

- Browser: `reviews/browser/receipt.json` lists seven passed checks on synthetic data with the live graph unchanged, and `readiness.png` shows the inspector with question state and declared dependency impact. I did not drive the browser myself.
- I read one author receipt in depth and the summary fields of the rest. I did not re-grade interpretation, maintenance or multiturn answers.
- `reviews/maintenance/timed-review-1` records model review latency only; human time is null, as stated. The comparison makes no superiority claim and I found nothing contradicting that.
- Final pacing and design trial grades had not arrived when this was written; the acceptance rerun after they land is out of this report's scope.
- Unchanged from earlier passes: no scale fixture, no replay CLI run, sixty-five case specs not read line by line.

## Commands executed

```sh
cd /Users/blake/projects/theory-building-graph
sha256sum graph.json; git status --short; git log --oneline
git diff -- DEPENDENCY-SCHEMA.md test_replay.py test_tracecheck.py acceptance/run.py; grep -n requires dependency.py
python3 -m unittest discover -s . -p 'test_*.py'
python3 acceptance/run.py --report /tmp/.../run-report-4.json
python3 reviews/fixtures/fable-5.1/probes.py; python3 reviews/fixtures/fable-5.1/followup-probes.py
./tg check; ./tg node check-steward-next
python3 - (live-refresh snapshot comparison; requires-vocabulary load probes; gate tamper tests on a copied root; agent_evidence over every mapping; multiturn receipt/stage binding audit; prompt and input diffs v1/pace3/pace4)
git diff --stat -- reviews/blind-trials/
```
