# Structured fragment v1

`formalcheck.py` checks explicitly authored coordinates. It neither parses prose nor proves fidelity of a pattern to its source. `review_formalization(proposed, authorized)` flags differing extracted coordinates for human/agent review; its `coordinates-match` outcome is not user acceptance.

A graph can carry `formal_model`:

```json
{
  "scopes": {
    "all-work": {"members": ["normal", "repair"]},
    "repair": {"members": ["repair"]},
    "review": {"nonempty": true}
  },
  "scope_subset": [["repair", "all-work"]],
  "scope_disjoint": [["review", "all-work"]],
  "scope_overlap": [{"scopes": ["a", "b"], "witness": "shared-context"}],
  "role_disjoint": [["steward-role", "orchestrator-role"]],
  "actors": {"session-a": {"roles": ["steward-role"], "roles_complete": true}},
  "subjects": [{"id": "port-a", "type": "Port", "scopes": ["all-work", "repair"]}]
}
```

This example declares fixture assumptions; it does not assert those roles are disjoint in Morphisms. `members` means the complete finite set of scope context IDs. A subset fact means the first scope is strictly contained in the second; cycles are errors. A same-name scope still needs an existence/nonempty witness before a permission conflict is reported. A subject witness explicitly lists each applicable scope. No type inheritance or free-text predicate inference is assumed.

## Authority

```json
{"kind":"authority","modality":"only","role":"steward-role","operation":"choose-work","scope":"all-work"}
```

A selector uses `role` or `actor`, not both. `only` restricts eligible permitted actors. `may` asserts a positive permission in an inhabited matching scope, and `must` entails that permission. `never` forbids it. Two `only` restrictions don't require a permitted occurrence, so different roles alone cannot imply contradiction. Unknown role overlap yields `role-overlap-unknown`. Two policies governing different operation IDs are independent unless a future explicit operation implication fragment is introduced.

`compare_patterns(a,b,model)` and `compare_graph(graph)` return deterministic receipts with the exact compared claims and pattern witnesses. Graph comparisons inspect accepted/current structured claims only. Historical receipts are separate persisted data; the pure checker does not delete them. The API reports `policy-conflict`, `compatible`, `independent`, `overlap-unknown`, `no-overlap`, `role-overlap-unknown`, `no-inconsistency-established`, `schema-error`, or `not-checked`.

`evaluate_authority(pattern,trace)` accepts scope `all` or `after_attempt_ended`. The latter requires an explicit earlier `end-attempt` event in the same attempt. Events have `actor_roles` (complete event-time roles) or the legacy single `actor_role`. Permissions alone do not require events. This generic checker permits vacuous satisfaction of restrictions on an explicitly complete empty trace; the existing `exclusive_actor` demo's requirement for at least one event remains unchanged. These conventions are distinct and labeled.

## Cardinality

```json
{
 "kind":"cardinality", "scope":"all-work", "min":1, "max":1,
 "slot":{"subject_type":"Port","relation":"owners","target_type":"Service",
         "direction":"out","identity_key":["host","number"],"count":"distinct"}
}
```

`max:null` means unbounded. Distinct incompatible slots are not compared without explicit equivalence. Missing identity is unknown. A contradictory interval requires a subject witness present in both scopes to establish inconsistency; otherwise the result explains empty-domain satisfiability.

`evaluate_cardinality(pattern,reports,complete)` groups reports by the declared subject key and counts distinct stable target IDs:

```json
[{"subject":{"host":"A","number":8080},"target":"service-a","sources":["log-a"]}]
```

An explicit subject-only report establishes a subject with no observed targets. It does not establish zero actual targets without completeness. Duplicate reports retain both sources but count once. A known upper-bound violation is decisive even if evidence is incomplete. Absence of all subject reports is insufficient empirical information, not evidence of universal truth.

## Bounded obligations

```json
{"kind":"bounded_obligation","trigger":"complete","response":"consider",
 "role":"steward-role","within_ticks":5}
```

`evaluate_obligation(pattern,trace)` requires responses to link via `responds_to` to a trigger event ID. Events use logical integer ticks; trace `complete_through_tick` explicitly certifies the observation horizon. A response must occur from trigger tick through the inclusive deadline. Missing event-time role/timing information remains unknown. An unbounded eventuality cannot be falsified from a finite prefix. These are fixture semantics, not a mandated Morphisms deadline.

## Scope and limitations

These are comparison/evaluation APIs, not rule reachability or general satisfiability solvers. No-counterexample and satisfaction refer only to supplied patterns, witnesses and bounded traces. `references(pattern)` enumerates referenced graph nodes, scope IDs and relation vocabulary IDs for write integrity. Atomic writes, dependency invalidation, provenance/version receipts and agent interviewing are implemented separately and must be exercised in integration tests.
