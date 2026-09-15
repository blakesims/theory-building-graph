# Fable 5.1 independent review of the theory graph build

Reviewed: commit `55b610a` core files (hashes match `acceptance/run-report.json` for every core `.py` except `prepare_author_trials.py`, which the concurrent trial work modified). Live `graph.json` sha256 prefix `1b894f7d3676f6e9` before and after every command below. No implementation file was edited. Probe fixtures live in `reviews/fixtures/fable-5.1/probes.py` and run only on temporary graphs.

## Verdict

**Not ready for an honest all-scenarios completion claim.** The mechanical core is mostly sound: atomic audited writes, transitive invalidation over declared edges, receipt binding, interval math and vacuity handling in the formal fragment all behave as the contract specifies, and the unit tests reproduce. Three defects produce false readiness, false review churn, or inflated acceptance status, and must be fixed before re-review: H1, H2, H3. Six medium items degrade the honesty or usability of outputs an agent will read. The rest are low or product decisions.

Reproduction: `python3 reviews/fixtures/fable-5.1/probes.py` prints every probe cited as P-number below.

## What I verified as correct

- `python3 -m unittest discover -s . -p 'test_*.py'`: 138 tests, 8 failures, all 8 in `test_agent_receipts.py`, which fails by design until `reviews/author-trials-v2/` receipts exist. The other eight files total 129 passing, so the "129 pass" claim is accurate for the frozen core.
- `python3 acceptance/run.py --report <tmp>` reproduces 62 passed, 17 partial, 1 not-implemented, `all_passed: false`.
- `validate_suite.py` passes; `baseline_smoke.py --engine ..` reproduces the three demo outcomes and reports the live graph unchanged.
- I04 withdrawn prerequisite stays a named blocker. I03 topic links do not propagate. A03/A04/A05/A14 distinguish policy conflict, overconstraint, dual roles and unknown overlap. C01–C04 interval logic is right, and `test_metamorphic.py` is a genuine independent oracle for it.
- Deleting a prerequisite node together with its edge flags the dependent (P30). Deleting a node still referenced by a pattern is rejected without a partial write.
- Two competing writers and abrupt exit at the replace boundary behave as claimed.

## High severity

### H1 Acceptance report counts agent-mechanism cases as fully passed on mechanical evidence alone

Eleven cases whose declared mechanism includes `agent` are reported `passed` with coverage `full`: D08, E01, E07, M01–M08. Their tests exercise only authored fixtures or the replay engine. The mapping notes admit this ("does not establish automatic English extraction", "not a deployed Morphisms runtime"), but `acceptance/run.py:62-67` promotes any mapping marked `full` to `passed`, and the headline counts 62 passed. Meanwhile the author trials in `reviews/author-trials/comparison.md` show the agent portions of related cases failing 4 of 8.

- Evidence: `acceptance/run-report.json` rows for those IDs; mechanism field versus test names.
- Expected: a case whose mechanism includes `agent` cannot exceed `partial` without a recorded agent-evidence mapping (a graded receipt), exactly as S01–S08 are handled.
- Remedy: in `run.py`, cap status at `partial` when `'agent' in mechanism` and no mapping entry carries `evidence_kind: agent-receipt`; or change the eleven mappings from `full` to `partial`. Either way the count line changes.
- Blocks honest completion: yes.

### H2 Readiness trusts a question prerequisite's stored status, not its derived resolution

`dependency.py:142` satisfies a `depends-on` edge when `status in requires`. For a question prerequisite with `requires: ["answered"]`, the stored word `answered` is accepted even when the engine's own `resolution()` says `open` and `check` reports drift on that very node.

- Probe P3: Q1 stored `answered` with no answer edge; Q2 depends on Q1 requiring `answered`. Observed: `readiness Q2 = ready, blockers []`, while `readiness Q1` reports `resolution: open` and `check` reports both `answer-state-drift` and `unsupported-answered-state` on Q1.
- Expected (AC07, CONTRACT "Readiness ... concerns declared prerequisites", DEPENDENCY-SCHEMA "Explicit question status is retained as an author declaration"): a question prerequisite is satisfied only when its derived resolution is `answered`, or the blocker must say `stored-status-unverified`.
- Remedy: in `readiness()`, when the prerequisite node type is `question`, evaluate `resolution(g, target)['resolution']` against `requires` instead of `status`. Keep stored status as an author declaration only.
- Blocks honest completion: yes, this is a false `ready`.

### H3 Re-reviewing an unchanged prerequisite re-invalidates already-reviewed dependents

`dependency.py:234` adds a node to the invalidation roots whenever its currency changes, including the transition `needs-review -> current`. Reviewing a node whose content is byte-identical therefore marks every transitive dependent `needs-review` again, even dependents that hold a valid receipt for that exact fingerprint.

- Probe P1: chain Q depends on B depends on A. Edit A: A, B, Q flagged. Review Q (receipt binds B's fingerprint). Review B with no content change. Observed: Q back to `needs-review`, reason `Declared semantic prerequisite changed: B`, B `semantic_version` unchanged.
- Expected (I08, DEPENDENCY-SCHEMA: "A subsequent prerequisite edit invalidates that receipt again"): a review is not an edit. Only a fingerprint change, or a transition into `historical`, should root propagation. Review order must not change the final state.
- Remedy: root on `fingerprint(before) != fingerprint(after)` or `currency(after) == 'historical'`; do not root on a transition to `current`.
- Blocks honest completion: yes. The review queue never converges in the natural review order (dependents before prerequisites), and receipts are silently discarded.

## Medium severity

### M1 Vacuous satisfaction is invisible in the result an agent reads

The generic authority checker (`formalcheck.py:228`) returns `satisfies` for a complete trace with zero matching events, and always for modality `may`. FORMAL-SCHEMA states this convention, but the result itself carries no flag, `checked_events` is an empty list the reader must notice, and the text renderer (`graph.py:303-309`) prints only `Pattern satisfies`. `classify()` then reports `known-defect-unexplained` for a `may` pattern or an empty check, which is noise, because nothing was checked.

- Probe P9: `./tg evaluate only-s T` on a complete trace with no `choose` event prints `Pattern satisfies` and nothing else; JSON shows `checked_events: []` and a `known-defect-unexplained` finding. Same with modality `may`.
- Expected (AC12, REVIEW_REQUEST bullet 1): unsupported or vacuous compliance must not read as compliance.
- Remedy: add `vacuous: true` and a diagnostic `no-matching-event` when `checked_events` is empty; print both in `compact()`; skip polarity classification for `may` and for vacuous results.

### M2 One condition yields two findings, and one code means two different things

`graph.py:161-162` emits `unsupported-answered-state` (stored answered, no full answer) and `answer-state-drift` (stored open, has full answer). `dependency.py:208` also emits `answer-state-drift` for the first condition. A question stored `answered` without an answer therefore produces two findings with different codes, and the code `answer-state-drift` denotes opposite situations depending on the emitter.

- Probe P28 shows both outputs.
- Expected (AC20, gap matrix row "answer-state-drift"): one deterministic code per condition.
- Remedy: delete one emitter; use `answer-state-drift` for "stored completion unsupported" as the gap matrix defines it, and rename the open-with-answer case.

### M3 Compact text output regressed on the live graph

`questions()` (`graph.py:60`) now returns `resolutions` and `readiness` dictionaries, and `compact()` (`graph.py:320`) dumps every non-node key into the header line. On the live graph the header line grew from 143 bytes at commit `c101147` to 3021 bytes. Severity and `suppressed` flags on findings are not rendered in text mode at all, so the four informational `untested-claim` findings look identical to the review-severity tension.

- Repro: `./tg questions | head -1 | wc -c` versus the same on `git show c101147:graph.py`.
- Expected (AC19 compact bounded text).
- Remedy: exclude `resolutions` and `readiness` from the header, render one short line per question (`readiness=... resolution=... blockers=n`), and print `[severity]` on findings.

### M4 Custom dependency edge types propagate on node edits but not on edge changes

`dependency_edges()` honours `invalidation: dependent-to-prerequisite`, but the edge branch of `refresh()` (`dependency.py:252`) hardcodes `depends-on` and `extracted-from`. Adding or removing a custom dependency edge does not flag the dependent.

- Probe P2: adding `B -derived-from-> A` leaves B `current`; adding `C -depends-on-> A` flags C.
- Remedy: reuse the `dependency_edges` predicate in the edge branch.

### M5 Built-in scope names are exempt from the reference check but not comparable

`graph.py:172` and `tracecheck.py:85` treat `all` and `after_attempt_ended` as declared. `scope_overlap()` (`formalcheck.py:23`) requires both scopes in `formal_model.scopes`, so two accepted claims on scope `all` produce a `not-checked` finding per pair, while `evaluate_authority()` (`formalcheck.py:203`) happily evaluates the same scope against traces.

- Probe P4: `check` emits `('not-checked', ['may-o','only-s'], 'unsupported scope semantics')` until `all` is declared with members, after which `policy-conflict` appears.
- Remedy: define the two built-in scopes once (either auto-declare them as universal with an explicit `nonempty` decision, or drop the exemption so the gap check tells the author to declare them).

### M6 `untested-claim` ignores saved evaluations and accepts any edge to a trace

`dependency.py:209-210` clears the gap if any incident edge touches a `case` or `trace` node, regardless of edge type, and never looks at `checks` edges from `check-result` nodes.

- Probe P20: after `./tg evaluate A T --save receipt-A`, A is still `untested-claim`; B, which merely has an `about` edge to the trace and no evaluation, is not flagged.
- Remedy: count incoming `checks` edges from `check-result` nodes and only evidence-bearing relation types; `test_dependency.py:148` currently encodes the weak semantics by clearing the gap with a `supports` edge.

### M7 Formal finding IDs change on every revision

`compare_graph()` (`formalcheck.py:170`) embeds `computed_revision` in each finding, and `check()` (`graph.py:185`) hashes the whole finding into its ID. An unrelated edit changes the ID of every `policy-conflict` finding. R07 claims "stable sorted finding IDs"; `test_deterministic_checks` only compares two same-revision graphs, so it cannot detect this.

- Probe P32: `policy-conflict` id stable across unrelated revision: `False`; `untested-claim`: `True`.
- Remedy: exclude `computed_revision` (and any other revision-dependent field) from the ID hash.

### M8 Tests whose assertions are weaker than their names

- `test_formalcheck.py:46-49` (A07): the `independent` outcome comes from different operation IDs, not from may-versus-must semantics; the final assertion checks a literal the test itself built.
- `test_tracecheck.py:130-136` (D03): asserts the fixture still has the values it set; the only semantic assertion is `satisfies` for two actors, which any role-based check gives.
- `test_replay.py:81-83` (M08): reads back constants from `theory_model()`.
- `test_replay.py:159-172` (S08): asserts `'review steward-role' in shown` where `shown` is the command string the test composed.
- `test_dependency.py:145-149`: clears `untested-claim` with a `supports` edge from a trace, locking in M6.
- `test_agent_receipts.py:102` asserts `retrieval_calls == 0` for the blind trials: the graph arm never called the tool, so those receipts must not be mapped to AC22/S07 as evidence about the graph.

These tests pass, but their names promise semantics they do not establish. Mark them as mechanics checks or strengthen the assertions.

## Low severity

- **L1** The generic authority path fingerprints pattern roles only; roles that appear solely in trace events are not inputs (`tracecheck.py:79-97` versus the demo path at `tracecheck.py:119-120`). Probe P11: redefining the witness's role leaves the receipt `current`; redefining the pattern role makes it `stale`. Decide whether role definitions are semantic inputs and apply it in both paths.
- **L2** A claim with `"meta": null` and a pattern crashes `check` with `AttributeError` at `formalcheck.py:165` (`n.get('meta',{})`); `validate()` accepts null meta. Probe P26. Use `(n.get('meta') or {})`.
- **L3** The deletion guard (`graph.py:231-238`) matches any string anywhere in `pattern`, `trace`, `provenance`, `references`, `result`. Probe P41: deleting an entity whose ID coincides with an attempt label inside a trace is rejected. Match only reference positions.
- **L4** Propagation passes through historical dependents (P24: A ← B historical ← C; editing A flags C). Defensible, but undocumented; state it or stop at historical nodes.
- **L5** `undeclared-pattern-reference` fires for withdrawn/historical claims (P40). Skip retired nodes or mark the finding suppressed.
- **L6** `only(R)` versus `never(R)` on one scope returns `compatible` (`formalcheck.py:82-87`), hiding that nobody may act. Probe P31. `no-inconsistency-established` with `possible_overconstraint` fits the contract better.
- **L7** A `formal_model` update without `value` is rejected with a raw `TypeError` message rather than a `GraphError` (`graph.py:213`). Probe P5. The batch is correctly not written.
- **L8** Any `formal_model` key other than `scopes` flags every patterned node (`dependency.py:245-248`), and receipts hash the entire model and all edge types (`tracecheck.py:86`). Safe but noisy over-invalidation.
- **L9** `index.html` calls none of `/api/readiness`, `/api/impact`, or severity fields; the browser shows none of the new semantics.
- **L10** The live graph has no `depends-on` edges, so `impact steward-chooses-next-work` returns zero affected and AC04–AC07 are vacuous on live data until dependencies are authored. Not a bug; an authoring task that the report should name.

## Unresolved product semantics (not implementation bugs)

- **S1 Who may accept.** The author trial `operation-modality` rewrote "I" as "steward", attributed it to Blake in a new source node, and set `status: accepted` in the same batch. The CLI accepted it because nothing ties acceptance to an actor or to a source created outside the batch. Options: an actor allowlist for transitions into `accepted`; or refuse `accepted` on a claim whose only sources were added in the same batch. This is a policy choice for the user, not something the checker can infer.
- **S2 Two vacuity conventions.** The exclusive_actor demo refuses vacuous satisfaction; the generic authority checker permits it. Both are documented, but one modality with two conventions will mislead an agent. Pick one and flag it in the result (see M1).
- **S3 Meaning of `requires: answered`.** H2 recommends derived resolution. If the user wants stored status to count, the blocker vocabulary must say so.
- **S4 Historical pass-through** (L4) and **L1 role definitions as inputs** need a stated rule.

None of the fixtures resolve stopping authority or cancellation policy; S02 and `test_no_silent_stopping_or_cancellation_policy` hold.

## Checks not run in this pass

These are explicitly unverified. Nothing below should be read as passed or failed.

- **Browser UI.** I did not start `serve` or open `index.html`. L9 rests on a grep of the API routes the page calls, not on rendering. `/api/readiness` and `/api/impact` were not exercised over HTTP.
- **Scale fixture.** The IMPLEMENTER.md recipe (2500 claims, depth-20 chain, wide fanout) was not generated. Only the suite's own 1000-node hub test (R05) and the 20-node budget test (R06) ran. No latency or output-size measurements of my own.
- **Full case-by-case audit.** I read about fifteen of the eighty case specifications against their mapped tests (I02, I03, I04, Q04, A03, A04, A11, E01, E06, E07, D08, M01, M03, M06, S06, R07). The other sixty-five were judged only through the run-report mechanism and coverage fields.
- **Trial receipts.** I read both `comparison.md` files and the metrics of one graded blind-trial receipt. I did not re-grade any participant answer, verify receipt hashes, or inspect `fixtures/author-trials-v2/`, `acceptance/run_author_trials.py`, `run_blind_trials.py`, `prepare_author_trials.py`, `benchmark.py`, or `benchmark-report.json`.
- **Replay and evaluation CLIs.** `replay.py` and `session_evaluation.py` were exercised only through their unit tests, not invoked directly on `fixtures/design-session/`.
- **Formal-model paths.** `scope_overlap` witness entries, `actors` with `roles_complete`, `any_group` alternatives, `input_version` receipts, and `impact` pagination were reviewed by reading code and unit tests, not by my own CLI probes.
- **Exclusive_actor demo path.** Only `baseline_smoke.py` ran it; I wrote no new probes for the legacy checker beyond what the tests already cover.
- **Concurrent work.** Files that changed during the review (`AGENT_WORKFLOW.md`, `AGENTS.md`, `AGENT_CONTRACT.md`, `prepare_author_trials.py`, `acceptance/run_author_trials.py`) were not reviewed.

## Commands executed

```sh
cd /Users/blake/projects/theory-building-graph
sha256sum graph.json
python3 -m unittest discover -s . -p 'test_*.py'
for f in test_*.py; do python3 -m unittest $f; done
python3 acceptance/run.py --report /tmp/.../run-report.json
python3 acceptance/validate_suite.py
cd acceptance && python3 baseline_smoke.py --engine .. && cd ..
./tg overview; ./tg check; ./tg questions; ./tg review
./tg readiness stopping-authority --json
./tg impact steward-chooses-next-work --json
./tg --json types; ./tg node check-steward-next
./tg questions | head -1 | wc -c
git show c101147:graph.py > /tmp/.../old_graph.py && python3 /tmp/.../old_graph.py --file graph.json questions | head -1 | wc -c
python3 reviews/fixtures/fable-5.1/probes.py
git log --oneline; git status --short; git diff --stat
```

Plus the inline Python in this review's session that compared `run-report.json` hashes with current files, counted agent-mechanism cases marked passed, and ran probes P40–P42 (historical undeclared reference, deletion-guard collision, answer withdrawal propagation). P42 behaved acceptably: withdrawing a question's only answer left the dependent question `current` but `blocked` with reason `stale`.
