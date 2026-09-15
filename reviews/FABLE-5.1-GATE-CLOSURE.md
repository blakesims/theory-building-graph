# Fable 5.1 gate closure review

Uncommitted working tree on top of `838e9ae`. Not committed by me, per request. Live `graph.json` unchanged at `304a456b032e16a1` throughout. Gate files pinned for every probe below:

| File | sha256 prefix |
|---|---|
| `acceptance/staged_receipts.py` | `9c0e21c9e599fcae` (earlier pass at `96cf0788cb429917`, see G3) |
| `acceptance/receipt_validation.py` | `56cd60367ce48e91` |
| `acceptance/run.py` | `bc376e4afbd389df` |

Reproduce: `python3 reviews/fixtures/fable-5.1/gate-probes.py` (copies real evidence into a temporary root and mutates only the copies).

## State

- `make test`: 256 tests, OK, no skips (252 at the earlier pinned state).
- `make acceptance`: 80 passed, 0 partial, criteria 22/22, `all_passed: true`, exit 0. Note that this target writes the tracked `acceptance/run-report.json`; it was already modified in your tree before I ran it.
- S01 is evidenced by `reviews/multiturn/decision3/design/graded-S01.json`, gate-valid and mapped in `multiturn-mapping.json`. The whole-run `decision3/design/graded.json` correctly remains `passed: false` on the copied failed stage 01.

## G1 criterion-to-case binding: closed

`normalized-rubric.json` criteria now carry `cases`. v2: 01→S08, 02→S01+S08, 03→S01, 04→S01, 05→S02, 06→S03, 07→S04, protocol-budget→all. The gate derives a scoped receipt's expected criteria from the parent rubric's `cases`, so a child cannot choose its own subset.

- T3 relabel `cases` S02→S03: `scoped-parent-criteria-mismatch`, `scoped-rubric-differs-from-parent`.

## G2 every stage bound with state chain: closed

- T1 unbind the failed stage's stdout from a passing scoped receipt: `stage-artifact-unbound`.
- T9 rewrite a stage's before-graph with all declared hashes updated consistently: `stage-state-chain-broken`.
- F3 delete a copied prior stage directory: fails closed as `invalid-receipt` (missing file).
- Stage ids are checked against input prompts and on-disk control directories; per-stage receipts must equal the participant record.

## G3 parent failure disclosure: closed

Child-side tampering:

- T2 child sets `parent_hard_failures: []`: `parent-failures-not-disclosed`.
- T6 composite drops `parent_disclosures`: `component-parent-failure-undisclosed`.

Parent-side tampering. At the earlier pinned state (`96cf0788cb429917`) three probes passed the gate, because it checked child-parent agreement and hashes but never the parent report against its own grades or its rubric against its stages. That was reported as blockers B1 and B2 during this review. Against the current code (`9c0e21c9e599fcae`) all three are rejected:

- **T4** parent edited to `passed: true, hard_failures: []` with score-0 grades left in place; child re-hashed: `parent-verdict-inconsistent-with-grades`, `parent-grade-failure-disclosure-mismatch`.
- **T4b** score-0 grades deleted from the parent as well: `parent-grade-rubric-coverage-mismatch`.
- **T5c** whole-run rubric narrowed to passing stages, grades and hashes updated: `whole-trial-rubric-omits-participant-stage`.

The real parents were also checked by hand: v2 and decision3 `hard_failures` equal exactly the ids of their score-0 grades. B1 and B2 are closed.

Residual, inherent limit: a parent whose failed grade is forged to score 1 is internally consistent and no structural check can detect it. That is what the preserved v1/v2 originals and git history are for; the gate verifies binding and consistency, not the honesty of a score.

## S08 composite: closed

- T7 the partial proposal component used alone as S08 evidence: `partial-component-not-full-evidence`.
- T8 component swapped to the failed v2 whole run: `component-scope-mismatch`, `component-criteria-mismatch`, plus the component's own failures.
- T10 browser slot artifact unbound: `component-slot-artifact-unbound`.
- The rubric's `required_evidence_slots` pin each slot to a component and its criteria; unused or missing components are errors.

## Fork source and copy semantics: verified

`decision3/design` copies v2 stages 01–03 and stage 04's before-graph. I compared the files directly: before, after, prompt and stdout are byte-identical for stages 01–03; stage 04 shares the before-graph and has a new prompt, stdout and after-graph. The gate binds the normalized fork manifest into both parent and child (`scoped-fork-provenance-mismatch`) and verifies every copied file against source and copy hashes.

- F1 edit `fork-manifest.json`: `artifact-hash-mismatch`.
- F2 alter a copied prior-stage stdout: `fork-source-copy-mismatch`, `stage-declared-hash-mismatch`, `stage-artifact-hash-mismatch`.
- F5 move `fork_stage` earlier in the manifest and re-hash the child: `fork-manifest-hash-mismatch`, `scoped-fork-provenance-mismatch`.

Stage-4 outcome checked in the after-graph: `replacement-question` answered, `replacement-exception` superseded, `consultation-question` open, current, and byte-identical to the before-graph. That is the criterion v2 failed.

## Honest scope of S01

S01 passes on v2 stages 02–03 under `authoring/6` plus one fork stage 04 under `authoring/9`, with the prior transcript replayed rather than re-executed. The fork was run once after one failure, with new guidance on scope-local reconciliation, which is the failure mode it addresses. The receipt's `contract_versions_note` says this. The gate does not verify contract-version claims, only the bytes of the prompts, which do contain the version line. This is a single successful rerun, not a reliability measure, and the receipt does not present it as one.

## Non-blocking notes

- `make acceptance` rewrites `acceptance/run-report.json` in place; run it with `--report` elsewhere when reviewing.
- The gate error `stage-artifact-unbound` includes the path, which made T1 easy to read; most other codes do not name the offending artifact. Optional.

## Verdict

**No remaining blockers.** G1, G2, G3, the S08 composite rules and the fork semantics all fail closed under every tamper in `gate-probes.py`, including the two parent-side bypasses found and fixed during this review. The 80/80 acceptance result and 22/22 criteria stand on receipts the gate can now verify without relying on the honesty of a parent report's summary fields. What the gate cannot verify, and no gate can, is the correctness of an individual grader's score; the archived failed trials and the disclosed contract-version history are the record for that.

## Commands executed

```sh
cd /Users/blake/projects/theory-building-graph
make test; make acceptance
python3 reviews/fixtures/fable-5.1/gate-probes.py
python3 - (F3 unfiltered; F5 manifest fork_stage tamper; direct byte comparison of v2 and decision3 stage files; stage-4 after-graph inspection)
sha256sum graph.json acceptance/staged_receipts.py acceptance/receipt_validation.py acceptance/run.py
```
