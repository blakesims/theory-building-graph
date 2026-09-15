# Dependency and question schema

The JSON store remains version1. New fields are optional; the live theory was not migrated or reinterpreted. Use `./tg apply batch.json --actor ... --reason ... --expect REV` for atomic audited edits.

## Declared dependence

Register the `depends-on` relation through an `edge_types` add. Each directed edge goes **dependent → prerequisite**. `extracted-from` has the same content-invalidation direction but does not require the source to have accepted standing. Custom edge types can opt in with `invalidation: dependent-to-prerequisite` and separately `readiness: true`.

```json
{"from":"next-choice","to":"steward-rule","type":"depends-on","requires":["accepted"]}
```

`requires` defaults to `answered` for question prerequisites (derived resolution), and `accepted` for other prerequisites (authored status). Explicit question requirements must use `open | candidate-answer | partial-answer | answered | retired`; they do not use the question’s authored status vocabulary. For other types, requirements must belong to `node_types.TYPE.states` when that list is declared. Types without a declared state list remain extensible and cannot receive vocabulary typo checking; declare `states` to enable it. Invalid explicit requirements reject the entire batch with the edge ID and allowed values. Legacy question edges requiring `accepted` are rejected on load: preserve a backup, review their intended meaning and explicitly correct those edges before reloading. No automatic migration guesses whether the intended requirement was a full or partial answer. The default is mandatory all-of. Edges with the same nonempty `any_group` form an alternative group: any one available/current qualifying premise satisfies that group. Distinct groups and ungrouped edges are required together. Withdrawn or historical premises remain blockers; they are not filtered away, even when `requires` includes a retired status. Invalidation traverses historical intermediate nodes and can mark their current descendants for review; history does not sever the dependency chain. `answers`, `about`, `supports`, and `revises` never become logical dependencies automatically.

Semantic edits update `semantic_version` and mark transitive dependents `meta.review_state: needs-review`; they do not reject accepted claims. Changes to text, pattern, enforcement, assumptions and other non-presentation top-level data are semantic. Layout, color, title and aliases are presentation/identity lookup metadata. Source citation metadata alone is not a semantic edit, but a source node's corrected text is.

Explicitly setting a node's `meta.review_state` to `current` through apply records its exact prerequisite fingerprints in `meta.reviewed_inputs` and on its dependency edges. This is an agent's recorded review, not a mechanically proved implication. A subsequent prerequisite edit invalidates that receipt again. Atomic revision expectations prevent an obsolete review from overwriting a newer graph.

```
./tg impact steward-rule --limit 20 --offset 0 --path-limit 4 --json
./tg readiness next-choice --json
./tg review next-choice
```

Impact first computes all reachable IDs. It pages that list and reports `total_affected`, `truncated`, and `next_offset`. Path examples are bounded by the requested path limit and10000 search expansions per returned node; `paths_truncated` discloses incomplete examples. It never enumerates an exponential path set just to count it. Each returned path includes exact node and edge IDs.

## Question resolution is separate

Questions may declare `answer_shape: verdict | condition | exploration` (default verdict for legacy data), plus `required_parts: [id, ...]`. Answers are claim→question edges with explicit `coverage: full | partial | unknown`. Partial answers can list `covers: [part-id,...]`. The response includes the remaining `unresolved` parts.

For a condition question a full answer needs `answer: {condition: ...}` on the edge or answering claim. For exploration it needs `answer: {findings: [...], complete: true}`. Saying “yes” does not fill these shapes. The engine checks explicit shape, standing and currency; an agent must judge whether the condition/findings actually answer the user's question.

Readiness reports `ready | blocked | no-dependencies`. Resolution reports `open | candidate-answer | partial-answer | answered | retired`. Review currency is an independent field. The legacy `question_states` presentation still includes `needs-review`; use `resolutions` and `readiness` for independent machine semantics. Counts and excluded historical totals are explicit.

## Gaps and declared models

`check` adds deterministic content-derived finding IDs, revision-cycle/dependency-cycle witnesses, orphan anchors, ungoverned operations, unconnected questions, untested accepted claims, unresolved accepted revisions, and unknown pattern references. These are bounded structural observations, not a proof of completeness. `incomplete_by_design` tags informational findings as suppressed while retaining a count and inspectable finding details. Accepted/withdrawn status is never automatically changed by a finding.

Formal comparison input is authorable with collection `formal_model`, e.g. adding the `scopes` section with a JSON object or `role_disjoint` with an array. Updates replace that section. Every change is audited and relevant patterned statements need review. Deleting a still-referenced scope, relation or object is rejected; retiring a statement preserves its explanation chain.

## Compact reads

CLI node/walk/search/review/question/anchor reads omit arbitrary extra metadata by default. The output names omitted keys in `metadata_omitted`, and `--full` recovers them. Text, patterns, trace payloads and provenance references are retained without semantic truncation. Extra essential metadata can be declared in `node_types.TYPE.compact_meta_fields`. Web API views retain metadata for rendering. `export` emits a full canonical sorted JSON snapshot. It may be large intentionally.
