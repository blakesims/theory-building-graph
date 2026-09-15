# Handoff to the implementation/evaluation agent

Read CONTRACT.md and REVIEW.md before turning cases into code. cases.json is a behavior specification. It is intentionally not a claim that the current CLI accepts every proposed shape or that80 tests already exist as executable fixtures.

## Objective

Make the tool reliably preserve and revise an evolving design theory. Implement the smallest general mechanisms needed to meet the acceptance cases. Do not build Morphisms runtime behavior, invent the user's unresolved answers, implement a universal theorem prover, or overfit node names such as steward/port.

## Delivery order

1. **Baseline:** reproduce existing25 unit tests and `baseline_smoke.py`. Record exact engine version/hash. Demonstrate the three synthetic trace outcomes.
2. **Dependency and meaning contract:** explicit depends-on relation, typed answer shapes, declared sources/standing/currency. Implement transitive invalidation, blockers and version-bound re-review. Pass D,I,Q and structural gap fixtures.
3. **Comparison fragment:** implement a documented authority language and cardinality slot language with scope/identity semantics. Pass positive AND negative A,C cases. P2 items may remain unsupported with a named reason until their fragment is deliberately added; do not count unsupported as a completed target test.
4. **Evidence:** extraction provenance, bounded completeness and event roles, stale result receipts, polarity/coverage classification. Pass E.
5. **Conversation integration:** implement an agent procedure that retrieves anchors/related answers before proposing edits; run S01–S08 with human-readable diffs. M scenarios can begin as agent-led theory tests, and become executable traces only when their trigger/obligation language is supported.
6. **Growth and reliability:** run R, including large hub fixtures and failure injection. Measure exact output sizes and latency against the same machine baseline. No new database is mandated until measurements justify it.

A passing storage test does not imply a passing conversation test. A passing authored scenario does not establish theoretical completeness.

## Fixture bundle structure

Translate each scenario into an isolated directory:

```text
fixtures/A03/
  manifest.json        # scenario ID, semantic fragment version, assumptions, supported phase
  initial.graph.json   # exact fixture, not the user's live graph
  turns.jsonl          # user utterances and source IDs for agent tests
  steps/
    01.apply.json      # exact atomic operation batch after adapter mapping
    02.apply.json
  expected/
    00.check.json
    01.check.json
    01.stale.json
    01.readiness.json
    01.questions.json
  evidence/            # synthetic or supplied sources, explicitly labelled
  run-report.json      # actual result, assertions, timings, hashes, failure explanation
```

Do not pretend the neutral `arrange/actions/assertions` objects in cases.json are already CLI operations. Build one explicit adapter mapping the contract to your chosen schema. Keep expected results independent of the production implementation; never generate the expected answer by calling the function under test.

Each sequence must compare after every mutation, not just final state. Capture a no-write hash before reads. Random IDs, wall-clock timestamps and UI coordinates may be normalized where irrelevant; never normalize away semantic IDs, witness order, dependency paths, exclusions or error categories.

Exact output ordering should be documented and deterministic (e.g. stable sort by finding code then node IDs then edge IDs). A semantic expected-result schema is preferable to snapshotting arbitrary presentation wording.

## Test assumptions and oracle discipline

- The role/existence/scope assumptions in A03–A05 and C02–C04 are part of the fixture. Do not import them into every model.
- A failing intended fixture and a deliberately violating defect fixture have different expected assessments. A known-defect fixture passing authority checks is a coverage finding, not an excuse to fabricate a new authority violation.
- Preserve unknown versus false. Unspecified role overlap, incomplete evidence and unsupported scope are not licenses to guess.
- Distinguish a current claim from an accepted claim and an accepted claim from a faithful formal extraction.
- Never resolve stopping-authority or arbitrary cancellation merely to make a fixture pass. S02 expects these uncertainties to remain.
- Tests about claim independence must explicitly declare their dependencies. Topic adjacency alone is insufficient.
- A new role or operation alias must not silently merge two concepts. Explain ambiguity and ask through the test turn sequence.

## Agent evaluation rubric

For each session replay, grade independently:

1. **Current rule recovery:** states the applicable present rule without reviving retired exceptions.
2. **Revision memory:** explains the relevant former proposal and why it changed.
3. **Scope honesty:** distinguishes choosing/inserting and may/must; doesn't resolve unasked questions.
4. **Provenance:** exact stable source/node references; paraphrases identified.
5. **Uncertainty:** names unanswered questions and unsupported formal checks.
6. **Update discipline:** proposes only authorized edits, reconciles affected dependents, retains history.
7. **Communication:** one manageable next question, respects the requested pace.

Use0/1 per named semantic expectation with an explanation; reserve hard failures for invented user acceptance, misrepresented proof, corrupted data, source-instruction execution, or lost durable responsibility. Have a grader see the rubric and source facts, not the answer's preferred graph vocabulary. Graph IDs are evidence addresses, not bonus points unavailable to the prose baseline.

Report accuracy alongside input/output tokens, retrieval calls, wall-clock latency and human correction/maintenance time. Do not pool invented certainty into an average that hides it. Use multiple independent cold-start runs and unfamiliar domains before claiming superiority. One success on this session is an initial demonstration only.

## Scale fixture recipe

Generate2500 claims,50 anchors,500 questions and an explicit dependency DAG with a depth20 chain, a wide fanout and a diamond. Include historical alternatives and long source metadata. Fix the generator seed and record actual counts. Add separate deliberate cycle and corrupt-reference fixtures. This is large enough to expose unbounded context output without becoming a storage benchmark project.

Suggested **provisional** local output budgets (measure and revise openly): ordinary history of one revision without full metadata ≤8KiB for a20-edit fixture; a20-node/30-edge compact walk with ≤160-character statements ≤12KiB. Larger statements may require an explicit summary flag with drill-down; do not silently truncate a quantifier or condition. These are fixture budgets, not mathematical guarantees or context compression targets for arbitrary prose.

## Current-engine smoke check

From this package directory:

```sh
python3 validate_suite.py
python3 baseline_smoke.py --engine ../theory-graph
```

The first validates the spec package, not the product. The second executes a narrow set of currently supported checker behaviors on a temporary copy. Neither claims80-case compliance. Test reports must identify `passed`, `failed`, `not-implemented`, `blocked-on-semantics` or `not-run` for each target scenario; no silent skips and no count inflation by treating unsupported as success.

## Completion report

Return: implemented mechanisms; exact scenario IDs passed/failed/deferred; unresolved semantics; false-positive/false-negative examples; CLI transcripts; fixture hashes and runner command; update/read performance; cold-start agent evaluation results; and remaining risks. Preserve the user's live graph and notebook throughout.
