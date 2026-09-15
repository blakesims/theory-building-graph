# Morphisms theory graph

Standalone local project: code, graph.json, graph engine, tests and this guide live here. Original September14 notebook is a separate sibling project `../model-workspace` on8766; this project serves only8767.

Start from this directory: `python3 graph.py serve` → http://127.0.0.1:8767

## Read efficiently

From the project directory:

```sh
./tg overview
./tg anchors
./tg node steward
./tg walk steward --direction in --depth 1
./tg walk end-attempt --depth 2 --relations governs,answers,raises
./tg review stopping-authority
./tg questions
./tg check
./tg search failure
./tg history --limit 1
```

`--json` and `--full` work before or after the subcommand. Default output is readable text; JSON is a complete structured result. Normal history is a small edit summary, `history --full` returns before/after. Node returns statement and incident edge references; walk includes neighbor bodies. Alias/title resolution is exact case-insensitive, rejects ambiguity, and keeps stable IDs.

CLI and browser default to current material. `--historical` includes history; current includes items needing review but not explicitly historical entries. An explicitly requested historical root remains inspectable. `questions` reports total, included and historical-excluded counts.

Walk limits: `--limit 40`, `--edge-limit 100`, `--depth 1`, `--direction in|out|both`. Output reports truncation and the count of edges crossing beyond the selected node set. It does not claim omitted edges don't exist. `--anchors stop` (default) includes encountered entity/operation hubs but does not traverse through them; selecting a hub as root expands its own neighbors. `--anchors cross` allows passage through hubs; `--anchors omit` removes about/governs links. `--relations about,governs` filters the relation vocabulary before walking. Basic search matches ids, aliases, titles, types, state and text; a tiny failure/failed normalization is supported, not semantic search.

## State and meaning

Node type definitions declare allowed `states`, which the writer validates. Current vocabulary:

- claim: proposed, accepted, withdrawn
- question: open, answered, retired
- entity/operation: provisional, defined
- source/case: recorded

Attribution is separate: `meta.author`, `meta.source_kind` (e.g. assistant-paraphrase), source excerpts and references. Paraphrases remain labelled as paraphrases even when the underlying position was accepted. `meta.review_state` is current, needs-review or historical; current does not mean accepted. Legacy labels remain in metadata and the audit log, not in the active state vocabulary.

`answers` edges require `coverage: full|partial|unknown`. A current accepted full answer yields an answered question; partial coverage does not close it. Pending review is reported separately. Explicit question status is retained as an author declaration; `check` flags discrepancies. The check command finds structural inconsistencies, missing anchors, and explicitly recorded potential conflicts. It does NOT infer contradictions from natural-language text. A potential-conflict edge is a review item, never a proof.

## Change atomically

```sh
./tg apply edits.json --actor assistant --reason 'Record the user clarification' --expect 8
```

`--expect` rejects stale revisions. `apply --help` includes the format. JSON batch example (replace references with existing IDs):

```json
[
  {"op":"add","collection":"nodes","id":"a-new-claim","value":{"type":"claim","text":"A proposed statement.","status":"proposed","meta":{"author":"assistant","source_kind":"assistant-proposal"}}},
  {"op":"add","collection":"edges","id":"a-new-claim-about-steward","value":{"from":"a-new-claim","to":"steward-role","type":"about","meta":{"rationale":"The statement concerns this role."}}}
]
```

Operations: add/update/delete. Collections: nodes/edges/node_types/edge_types. Updates merge fields and meta one level. Add types with a description and optionally allowed states. Add edges with from/to/type and arbitrary meta. Reciprocal directed edges are independent. Unknown endpoints/types/states and invalid answer coverage reject the entire batch. IDs are caller-chosen stable identities; existing IDs cannot be added twice. No migration renames IDs just for appearance.

Edits acquire a single-host file lock and atomically replace the graph with its audit record. Text/state/currency edits flag directly connected questions; decision relation edits flag their targets. Explicit `meta.review_state` in a batch records deliberate reconciliation. Metadata-only provenance additions don't invalidate claims. This is bounded review assistance, not complete semantic propagation.

## Verify and limits

`python3 -m unittest discover -s . -p 'test_graph.py'`

The browser is read-only. All writes go through the CLI. Graph history remains inside the JSON and is excluded from ordinary AI reads. The host loads the file; only the selected subgraph enters agent context. File size and audit growth will eventually justify indexed storage. There is no synchronization or backup service. Keep backups; don't write graph.json with an external editor while agents are writing.

Cytoscape is vendored locally under vendor/ with its license; no runtime CDN needed. The visual graph is a representation of stored relations, not an inference engine.

## Optional finite-trace pattern checker

```sh
./tg evaluate steward-chooses-next-work fixture-steward-next
./tg evaluate steward-chooses-next-work fixture-orchestrator-next --save check-example
./tg node check-example --json
```

This checks one optional `claim.pattern` fragment, **not the complete prose claim**. Supported shape:

```json
{"kind":"exclusive_actor","operation":"choose-work","allowed_role":"steward-role","scope":"after_attempt_ended"}
```

Both `choose-work` and `end-attempt` must be operation anchors. Allowed/recorded roles must be entity anchors with `meta.kind: "agent-role"`. `meta.pattern_standing: "proposed"` keeps the proposed pattern interpretation separate from the claim's acceptance. No other pattern kind or scope is implemented.

A `trace` node has status `recorded` and a top-level payload:

```json
{"trace":{"complete":true,"events":[
  {"id":"end1","operation":"end-attempt","actor":"session1","actor_role":"orchestrator-role","attempt":"attempt1"},
  {"id":"choose1","operation":"choose-work","actor":"session2","actor_role":"steward-role","attempt":"attempt1","after":"end1"}
]},"meta":{"synthetic":true,"polarity":"intended"}}
```

`actor_role` is the role **at the event**, not looked up from a session's current role. `after` must name a unique, earlier `end-attempt` event for the same attempt. `complete:true` attests completeness only of this supplied finite trace; it is not a statement about all execution. Other operation IDs are recorded as out of scope. Missing/ambiguous linkage on a choose event is insufficient information, rather than evidence it was out of scope.

Outcomes:

- `satisfies`: at least one scoped choose event, every checked chooser has the allowed role, and no unresolved trace information.
- `violates`: an exact scoped event has a different known role; witnesses name its event, actor, role, attempt and end event. A definite witness takes precedence over other unknowns, whose diagnostics remain visible.
- `insufficient-information`: missing role, actor, completeness, scope linkage, mismatched attempt, wrong temporal order, or no scoped choose event. **No vacuous pass.**
- `not-checked`: prose only, unsupported pattern, or unusable pattern references.

`--save [new-id]` records a check-result and `checks` input links through the normal locked audited transaction, rejecting a concurrent graph revision. Saving never accepts, withdraws, or edits a belief. Computed outcomes are immutable records; run again to create a new result.

Saved result freshness is derived on read: SHA-256 fingerprints cover the claim and trace contents plus referenced role/operation anchors and checker version. Review flags/reasons are excluded; substantive metadata and source provenance are included. Missing referenced IDs are tracked too. Input deletion, content change, or checker version change makes the result `stale`; restoring identical input content makes it `current` again. Current means the calculation still applies to these inputs, **not** that the trace is true, the proposed pattern is ratified, consultation is correct, or liveness is established. These are content-based fingerprints, not a proof or a tamper-proof audit.

Click a patterned claim or trace to inspect its pattern, synthetic label, saved evaluations, witnesses and freshness. The three bundled fixtures are synthetic demonstrations, not observed Morphisms execution.
