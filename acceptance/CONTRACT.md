# Acceptance contract for an agent-assisted theory graph

**Status: proposed test contract, 2026-09-15.** This is a handoff for developing the theory-design tool, not authorization to implement any proposed Morphisms runtime rule. It includes fixture-specific assumptions, accepted conversational decisions, and deliberately unresolved decisions. Those categories must not be merged.

The goal is to preserve the user's developing theory across revisions and conversations, identify consequential uncertainty, and check a small formal fragment without claiming more than was encoded. A graph is valuable only if it makes these tasks better at acceptable authoring cost.

## Deliverables in this package

- `CASES.md`: 80 detailed Given/When/Then cases, including eight multi-turn design-session replays.
- `cases.json`: the same cases in a machine-readable, engine-neutral representation.
- `IMPLEMENTER.md`: implementation order, fixture/harness conventions, evaluation rubric and stopping rules.
- `REVIEW.md`: corrections to the supplied agent review and a map from its proposed ACs to this contract.
- `validate_suite.py`: validates the acceptance package's internal structure. It does not test engine compliance.

The current engine baseline was inspected at graph revision12:31 nodes,99 relations;25 existing unit tests passed. It supports one optional `exclusive_actor` finite-trace fragment, not the full acceptance contract. No case in this package is reported passed without running an implementation and recording evidence. Test cases labelled mechanical may target functionality not yet built.

## Semantics that a conforming first implementation must state

### Object and statement layers

Entities and operations name the modeled world. Claims/questions/extractions/results speak about it. A role is distinct from a session instance. An operation is distinct from the permission to execute it, the responsibility for deciding it, and a recorded event where it happened. Layers may share a physical store.

Every machine-comparable statement uses stable declared IDs. Aliases resolve identity; they do not redefine it. Ambiguity produces a question. Free text is never silently converted into a formal predicate by the checker. Formalizing prose is an agent-authored extraction with separate standing, sources and coverage. A supported pattern can be evaluated before it is accepted, but its results never establish that the extraction matches user intent.

### Edges have different jobs

Proposed canonical directions:

| Relation | Direction | Consequence |
|---|---|---|
| about / governs | statement → entity or operation | Retrieval candidate; not logical dependence or proof |
| depends-on | dependent → prerequisite | Explicit semantic/readiness dependency, with an input version and satisfaction requirement |
| answers | claim → question | Candidate/full/partial coverage; does not create a prerequisite |
| revises | newer formulation → older formulation | Historical order; does not itself retract the old statement |
| supports | source/evidence/claim → claim | A reason; do not assume the target logically requires this one reason |
| potential-conflict | claim → claim | An agent's review hypothesis, with rationale; not a proved inconsistency |
| extracted-from | extraction → source | Provenance and content dependence, explicitly versioned |

Dependency propagation follows declared dependency semantics only. It does not traverse every about, supports, answers or historical edge. There may be multiple independent supports for a conclusion. Mandatory all-of prerequisites are the first supported readiness form; any-of alternatives must either be implemented explicitly or reported unsupported. The relation vocabulary can grow, but new relation types must declare whether and how they participate in invalidation, readiness and provenance.

### Acceptance, review and answers

Keep normative modality, epistemic standing, review currency, source attribution and enforcement distinct. A statement can remain accepted as a recorded user decision while needing review because its premise changed. A checker must never silently withdraw it.

Readiness: `ready | blocked | no-dependencies` concerns declared prerequisites. Answer resolution: `open | partial-answer | candidate-answer | answered | retired` concerns the question's answer shape and accepted/current answers. These are separate outputs. Include review flags and blockers explicitly.

A historical or withdrawn prerequisite is unavailable, not magically satisfied. It remains an explainable blocker until the dependency is removed/replaced or a declared alternative satisfies the requirement. Historical answer candidates, on the other hand, do not block readiness merely because they once answered the same question.

### Supported authority fragment

Do not compare a permission statement to an observed-event statement as if they were identical. For one explicitly chosen normative fragment:

- `may(actor, operation, scope)` asserts a positive permission.
- `never(actor, operation, scope)` forbids that permission.
- `must(actor, operation, scope)` entails permission and also an obligation; timing semantics require a supported bound/horizon.
- `only(role, operation, scope)` restricts permitted actors to those holding that role. It does not alone assert that any action occurs, that the role is inhabited, or that roles are disjoint.

For event constraints, `every chooser holds steward` and `every chooser holds orchestrator` may be jointly satisfied by no choosing events, or by a dual-role actor. Report policy conflict only with the needed scope/role/existence premises. Alternatively report an overconstraint or an unknown premise. A satisfiable witness within a bounded domain is stronger evidence than a string-label mismatch; no-counterexample in a bound is not a proof for all states.

Scopes are declared predicates/finite sets with explicit containment/disjointness facts in the first structured fragment. Free-text scopes stay retrievable but unchecked. Unknown overlap remains unknown. Cycles in declared strict scope containment are schema errors; ordinary dependency graph cycles have their own semantics.

### Cardinality fragment

A relation slot identifies subject type, relation direction, target type, distinct-count semantics, scope and identity key. Bounds are integer `[min,max]`, with an unbounded maximum allowed. Two interval restrictions on the same subject slot overlap iff `max(minima) <= min(maxima)`.

`exactly1` and `atMost2` intersect at1; they are compatible. Disjoint intervals imply no permissible instance of that subject in the overlap. They imply global inconsistency only when a subject must exist there. Universal claims can otherwise hold vacuously on an empty domain. Unknown scope overlap or identity must not produce a definitive contradiction.

Observed cardinality requires declared completeness for that relation slot. Two reports of the same owner are not two distinct owners unless the model explicitly counts occurrences. Port identity is a design decision: `(host,number)` is one fixture answer, not a universal networking ontology.

### Evidence and finite traces

Preserve source → extraction/assumptions → instance/trace → check result. Store event-time role information and explicit attempt/end-event links. Missing, contradictory or incomplete extracted information is not automatically false or zero.

Polarity says which design expectation a fixture represents. An intended case violating a constraint prompts review of the claim, case labeling or extraction. A known defect satisfying the currently checked fragment indicates unexplained defect/coverage, not a logically inconsistent theory. Defect traces can belong to an implementation model that the intended model deliberately forbids. Reachability requires an explicit rule model and search bound; without them it is `not-checked`.

Supported evaluation outcomes: `satisfies | violates | insufficient-information | not-checked`. A known witness can establish violation despite other unknowns; retain both the witness and diagnostics. The current demo deliberately refuses vacuous satisfaction when there is no scoped event. A future universal checker may use logical vacuity, but must state that change and cannot present absence of data as empirical support.

## Acceptance criteria

| ID | Required behavior | Principal cases |
|---|---|---|
| AC01 | Resolve existing typed identities and expose ambiguity; keep roles distinct from session instances. | D01–D04, C05–C07 |
| AC02 | Separate modality, standing, currency, enforcement and attribution. | D05–D08, A15 |
| AC03 | Explain every formalization with source, assumptions, scope and independently reviewable pattern standing. | D06,D08,E01,A15 |
| AC04 | On semantic input revision, compute complete transitive invalidation along declared dependency edges, without automatically changing acceptance. | I01–I05,I08 |
| AC05 | No broad invalidation through mere topic anchors, layouts or unrelated data. | I03,I06,R05 |
| AC06 | Return all affected IDs and dependency paths, with bounded rendering/pagination if needed; never confuse a truncated response with a complete set. | I02,R05 |
| AC07 | Compute readiness independently of answers; name all mandatory blockers, including retired/withdrawn prerequisites. | Q01–Q04 |
| AC08 | Resolve questions according to answer shape and coverage, with transparent totals and stale-answer handling. | D07,Q05–Q08 |
| AC09 | Report structural gaps with severity/context: orphan anchors, ungoverned operations, unanchored claims, edgeless questions and invalid revision cycles. Placeholder incompleteness is not logical inconsistency. | D01,Q07,R04 and gap matrix below |
| AC10 | Compare supported authority patterns using declared role/scope/modality semantics, with a witness or explicit unknown. | A01–A16 |
| AC11 | Compare supported cardinality patterns using interval intersection, identity, scope and existence assumptions. | C01–C08 |
| AC12 | Keep formal unsupported results, incomplete evidence and bounded absence of counterexamples distinct. | A12,A16,C08,E03,E08 |
| AC13 | Evaluate concrete traces at event time and cite exact witnesses; don't change beliefs or case labels automatically. | E02–E07 |
| AC14 | Invalidate saved results when any semantic input, extraction assumption, referenced definition or checker changes. | I05,I07,E01 |
| AC15 | Retrieve current positions, superseded alternatives and their rationale without conflating them. | S01,S06 |
| AC16 | Make a recorded potential tension inspectable; never present LLM semantic judgment as deterministic proof. | A07,S02,E08 |
| AC17 | Surface Morphisms responsibility gaps without pre-deciding unresolved policy. | M01–M08,S03–S04 |
| AC18 | Preserve atomic audited writes, references and optimistic concurrency across failure/retry. | R01–R04 |
| AC19 | Return compact bounded text and valid structured JSON; aliases/flags/help are sufficient for agent use. | R05–R07; baseline CLI gate |
| AC20 | Deterministic findings include exact node/edge/version witnesses and explicit check scope. | R07,E03,A03 |
| AC21 | Respect source trust boundaries and the user's requested pace. | R08,S08 |
| AC22 | Demonstrate semantic recovery versus an equivalent prose baseline, measuring maintenance cost too. | S06–S07 |

### Gap matrix: make AC09 independently executable

Each row is a separate fixture mutation and repair assertion in addition to the80 named scenarios:

| Planted condition | Expected finding | Repair / negative control |
|---|---|---|
| Declared entity with no references | orphan-anchor, informational | Add a legitimate reference; finding clears |
| Operation with no governing claim | ungoverned-operation, informational | Link a governing proposed claim; coverage now exists, acceptance separately visible |
| Claim without any subject anchor | unanchored-claim, review | Add explicit about/governs link |
| Question with no anchors/answers/dependencies | unconnected-question, informational | Link a subject; don't auto-answer |
| Accepted claim without any cases | untested-claim, informational | Add synthetic fixture; label synthetic coverage, not empirical evidence |
| Accepted current newer claim revises accepted current older claim | unresolved-revision, review | Explicitly supersede older or declare intentional coexistence/scopes |
| Revises cycle A→B→A | revision-cycle with path | Remove/correct mistaken edge; audit repair |
| Pattern references undeclared role/operation/relation/scope | undeclared-pattern-reference; not-checked | Declare correct identity/semantics; rerun |
| Supported pattern with unknown scope overlap | overlap-unknown | Add containment/disjointness/overlap witness |
| Completed question with no accepted current full answer | answer-state-drift | Reopen or provide/review a complete answer |

Explicit `incomplete_by_design` metadata may suppress an informational gap in the default view, but check output must expose suppressed counts and allow inspection. No gap is evidence that the entire theory is complete.

## What remains genuinely undecided

These are proposed tool/fixture choices, not discovered Morphisms facts:

1. Exact relation names, serialization and question answer-shape vocabulary.
2. Whether supported actors may hold multiple simultaneous roles and how roles inherit. Until specified, do not infer disjointness.
3. Scope language and what existence/overlap witnesses are required for a policy conflict.
4. Whether changes to source attribution alone stale a semantic result or only a provenance attestation. Distinguish the two.
5. Whether a content revert makes a deterministic result reusable. Recommended: preserve original receipt, label exact-content reuse explicitly, never rewrite its source revision.
6. Stopping authority in Morphisms: optional vs mandatory operator consultation. No fixture may silently settle this open design question.
7. Arbitrary cancellation versus failed terminal results. Failed-attempt handoff is agreed; every possible cancellation policy is not.
8. Countermodel generation/rewrite reachability: a later phase requiring explicit bounded semantics, not an implication of storing graphs.

Fixture-specific answers may be invented for tests only if labelled synthetic and scoped to the fixture. Keep contradictory alternatives in separate fixtures, never merge them as current user decisions.
