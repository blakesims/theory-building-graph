# Assessment of the supplied review

The supplied review reports experiments on a scratch copy, not the live graph. This package uses those findings as input, reads the current engine and graph, and expands the oracles using our conversation. It does not claim to have reproduced all six reported experiments.

## Findings I accept

- One-hop claim-to-question invalidation is inadequate for genuine premise chains.
- Explicit dependency semantics are required for readiness and useful transitive staleness.
- Gap checks should include more than unanchored claims.
- Structured patterns can support stronger comparison than declared potential-conflict edges alone.
- Provenance, stable identity, atomic writes and exact revision tracking are a useful foundation.
- Informal claims and optional formal fragments should coexist. Retrieval/agent reasoning still matters for informal content.
- Synthetic multi-turn fixtures are a better implementation target than a list of attractive features.

## Corrections needed before turning the review into tests

### 1. Exactly-one and at-most-two are compatible

The review's cardinality example is mathematically wrong. `[1,1] ∩ [0,2] = [1,1]`. Exactly-one versus at-least-two has disjoint bounds for a subject required to exist. Universal constraints over an empty subject domain still require an existence qualification before claiming global inconsistency. C01–C04 explicitly guard against these false positives.

### 2. Different exclusive roles do not automatically imply contradiction

Two observed-event invariants can both hold if no events occur, or if an actor holds both roles. Conversely, an explicit permission for an orchestrator-only actor conflicts with a policy forbidding every non-steward in the same applicable scope. These are different semantic objects. A03–A05 make the premises explicit. Evaluating one trace as satisfying C1 and violating C2 proves that trace is a counterexample to C2; it does not by itself prove C1 and C2 have no jointly satisfying model.

### 3. Do not propagate through arbitrary relations

The review suggests full transitive propagation is merely a missing function over existing edges. It is only well-defined after identifying which edges mean semantic dependence. Topic links, alternative answers, historical revision links and defeasible support do not all mean 'cannot remain valid without this premise.' I03 and Q04 are mandatory negative controls.

### 4. Withdrawal must not erase a mandatory blocker

AC7 in the supplied text says historical/withdrawn claims are removed from readiness computation. That would make a broken prerequisite disappear. Exclude them from active consistency assertions, but report them as unavailable when a live node still requires them. Old answer candidates are not prerequisites unless separately declared. See I04 and Q03–Q04.

### 5. Case polarity does not make every bug derivable or contradictory

A known defect satisfying all currently encoded patterns may concern a property the fragment does not express. This is a coverage gap, not necessarily inconsistent evidence. Explaining a defect requires a model of the implementation/environment that can exhibit it; the intended rules may deliberately prohibit it. A state/trace evaluator is not a reachability engine. See E05,E06,E08,S03,S04.

### 6. The observed Morphisms stopping tension remains ambiguous

'It ends the attempt at a configured threshold' and 'it may ask the operator whether to end' can coexist. The word may does not mean must. We should retrieve both and ask about the missing condition. We must not undo the separately accepted rule assigning next-work choice to the steward. A07,S02 are designed to catch exactly that overreach.

### 7. Lean is not the boundary between proof and no proof

Lean is one proof assistant, not the sole route to proof. Restricted decision procedures, other proof systems and mathematical proofs can establish results. Our practical boundary is the declared semantics and supported checker, plus its evidence and bounds. No tests should hardcode a product name as the logical limit.

### 8. Small type-graph size is not enough to promise tractability

Twenty types says nothing by itself about how many instances, trace steps or quantified assignments a checker considers. Bounded checking needs explicit finite domains, supported predicates, time/resource limits and an inconclusive result. Add a later generator only after these are specified.

### 9. The formalization ratio is not the whole value metric

The tool can help recover decisions, track dependencies and expose unresolved scope even when most claims remain prose. Conversely, many formalized claims can be useless if they encode the wrong interpretation. Compare fresh-agent semantic performance and maintenance cost against equivalent prose. S06–S07 prevent 'number of patterns' becoming a vanity metric.

## Mapping supplied acceptance criteria to corrected ones

| Supplied | Treatment |
|---|---|
| AC1 all transitive dependents | Adopt only for explicit dependency semantics; preserve acceptance and show paths. AC04–06. |
| AC2 readiness | Adopt, separate from answer state and alternatives. AC07–08. |
| AC3 gaps/cycles/revisions | Adopt with severity and explicit incomplete-by-design exceptions. AC09 gap matrix. |
| AC4 authority conflicts | Require modality, role overlap, scope and existence semantics; avoid empty-event false positives. AC10. |
| AC5 cardinality conflicts | Correct interval example and require identity/subject existence qualifications. AC11. |
| AC6 missing declarations | Adopt not-checked plus exact missing references. AC12. |
| AC7 withdrawal | Exclude from active assertions; retain as unavailable prerequisites and historical evidence. AC04,07,15. |
| AC8 polarity | Distinguish true mismatch from coverage gap; derivability deferred. AC13,17. |
| AC9 prose silence | No deterministic proof claims from prose; agent may report sourced potential conflicts. AC16. |
| AC10 exact deterministic findings | Adopt stable IDs, explicit versions, witnesses and reproducible ordering. AC20. |

## Conversation decision ledger used by the suite

**Accepted during our session:** intention persists across attempted records; steward chooses/sequences next work; direct operator-approved orchestrator replacement exception was explicitly retired; ending an attempt as failed returns next-work choice to steward; durable responsibility survives sessions; desk and thread can address the same durable decision; each linked completion can wake steward; user configuration can allow intentions to proceed without visiting the desk.

**Still not settled:** whether consultation before stopping is mandatory under every threshold; general cancellation wake policy; formal derivation of all agent types; exact identity/scope/pattern languages; multi-role representation.

**Assistant proposals, not user axioms:** tuple A=(responsibility,context,operations,judgment); exact object schema; formal extraction of the steward exclusivity pattern; any implementation-specific rule not explicitly chosen by the user.

**Cases:** M1688/M1689 summaries motivate investigation of review loops and solution-shaped briefs. They are not complete primary-source traces. Tests must preserve that limitation until the original case documents are provided.
