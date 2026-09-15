# Response to Fable 5.1 review

This records implementation decisions, not new Morphisms policy. The original
review and every failed participant trial remain available.

| Finding | Response and evidence |
|---|---|
| H1 | Agent mechanisms require graded agent receipts in addition to mechanical tests. Partial mappings do not become passes merely because another authored fixture is full. Independent interpretation and sustained conversation trials supplement engine tests. `acceptance/run.py` and receipt regression tests enforce the evidence gate. |
| H2 | Question prerequisites use derived resolution, not stored `answered`. A false stored completion blocks its dependent. |
| H3 | A review acknowledgment is not a semantic edit. Clearing `needs-review` without changing content no longer invalidates reviewed dependents again. Availability changes still propagate. |
| M1 | Generic vacuous satisfaction and permission-only checks explicitly say what was (not) checked and disclaim empirical support. These results do not classify a defect as unexplained. |
| M2 | One deterministic `answer-state-drift` finding contains stored and derived values, covering disagreement in either direction without duplicate emitters. |
| M3 | Compact question output has per-question readiness/resolution and blocker counts; large nested dictionaries are omitted from headers. Findings show severity and suppression. |
| M4 | Custom declared dependency edge changes propagate by the same direction declaration as node changes. |
| M5 | Finite trace scope `all` does not establish a nonempty normative scope. The comparison requires an explicit scope declaration; undeclared references are named gaps. No fabricated witness is introduced. |
| M6 | Coverage distinguishes real current saved checks, stale checks, explicit evidence and mere topic links. |
| M7 | Finding identity excludes computed revision. Unrelated edits retain stable IDs. |
| M8 | Added independent tool-enabled interpretation, staged authoring trials and paired real maintenance, with raw receipts and separately graded answers. Strengthened may-versus-must with an actual absent-response obligation check. Constant-reading tests remain narrow schema/mechanics checks, not proof of agent behavior. |
| L1 | Referenced event roles and operations are fingerprinted, including multi-role events. |
| L2, L7 | Invalid metadata/formal payloads reject atomically with explicit schema errors. |
| L3 | Deletion guard uses typed reference positions; arbitrary labels do not create references. |
| L4 | Retired prerequisites remain visible and dependency propagation crosses retired intermediates. Losing an earlier premise cannot silently validate its descendants. Documented in DEPENDENCY-SCHEMA.md. |
| L5 | Current gap checks suppress retired pattern-reference noise. |
| L6 | `only(R)` plus `never(R)` reports possible overconstraint, without claiming contradiction absent an occurrence requirement. |
| L8 | Conservative formal-model fingerprinting remains. Changing broad schema declarations may stale more checks than strictly necessary. It is safe but not an optimal incremental dependency compiler. |
| L9 | Selected-node inspector now exposes question readiness/resolution, declared dependency impact and scoped findings with severity. An actual browser smoke checks these and a live synthetic node/edge update on a temporary graph. |
| L10 | The live theory still needs deliberate dependency authoring. Zero declared impact is not a claim of zero semantic impact. Acceptance tests do not insert invented dependencies into the user's theory. |

## Scope that stays open

- Agent guidance protects source fidelity; storage validation is not proof that an
  agent interpreted Blake faithfully. The first failed trials demonstrated this.
- Acceptance tests concern supported fragments, explicit finite models, and recorded
  participant behavior. They do not prove arbitrary prose consistency, unbounded
  reachability or general agent reliability.
- The generic authority fragment preserves logical vacuity with visible diagnostics;
  the older exclusive-actor demonstration requires an actual choosing witness.
  Results identify their checker and limits.
- The runtime of Morphisms is not implemented by this project. Its stopping
  authorization, cancellation policy and other unresolved choices remain open.
- Paired evaluation does not establish graph superiority: both formats recovered the
  core semantic change. Prose was cheaper in the measured maintenance trial. Human
  review/correction time was not measured and is explicitly null.

## Follow-up findings

- N1: three live synthetic evaluations were rerun with new stable result IDs;
  older computations were retained as historical. `reviews/live-refresh/` preserves
  before/after snapshots and all four CLI commands. Non-result nodes are identical.
- N2: receipt validation now derives validity from case-bound complete grades,
  exact rubric coverage, source/raw/rubric hashes, and successful original execution.
  Original blind grades were restored byte-for-byte; normalized wrappers are separate.
- N3: explicit prerequisite states receive type-aware validation, including derived
  question resolution vocabulary. Invalid legacy values require an explicit author
  migration; they are not silently interpreted.
- N4: packet-only cold-start recovery and actual tool-enabled maintenance remain
  separate experiments. Mapping notes and receipts identify which was exercised.

## Final evidence gate findings

- G1: parent rubrics bind criteria to case IDs. Scoped grades must exactly match
  every criterion assigned to that case; partial components cannot pass alone.
- G2: the gate verifies every participant stage, its original receipt, prompt,
  raw output and before/after graphs, including continuity between stages.
- G3: scoped receipts bind the original parent grade and disclose its hard failures
  in a verified field. Tampering with parent failures, hashes, stage coverage or
  copied grades fails validation.
- G4: evidence records the actual authoring contract per stage. The S01 decision
  fork uses original stages under authoring/6 and a new decision under authoring/9.
  S08 combines a paced read under authoring/8, a proposal under authoring/6 and
  a separately observed browser update. Neither is presented as a new uninterrupted
  full session under the latest contract. Failed full sessions remain preserved.

The S01 rerun resolves replacement policy while retaining the separate consultation
question as open. The correction was to general authoring guidance about question
scope; the user turn, prior state and criterion were retained. See the bound fork
manifest and receipts under `reviews/multiturn/decision3/`.

- B1/B2 (final gate review): parent verdicts and disclosed failures are derived
  consistently from the complete grade set. The parent rubric must cover every
  recorded stage. Rewriting success labels, dropping failed grades, narrowing the
  whole-run rubric, or renaming a scoped receipt now fails validation. Fable's
  T4/T4b/T5c probes and deterministic regressions verify these repairs.
