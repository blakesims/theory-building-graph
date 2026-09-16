# Interpretation of the finite theory model

All statements below come from actual runs captured under `runs/` (see `answers.json` for receipt paths and exact state paths). The model is a synthetic, explicitly authored finite transition system; replays show what the authored rules do on the given events, not what a live runtime would do.

## M01 Continuation and intention identity (`runs/continuation.json`)
`endA` ends record A (lifecycle `ended`, outcome `failed`) and creates `responses.endA` owned by `steward`, pending, carrying intention `I` copied from the record. `next` consumes that response and creates record C with intention `I` copied from the response. Identity flows record A -> response -> record C; C is a new record, A's failure persists, and `intentions.I` never changes. The chooser role is an event argument checked against `config.next_work_roles` and the response owner, not an authenticated actor. Rule gap: no guard checks that the intention is still open or valid.

## M02 Blockage and recovery (`runs/recovery.json`)
`blockA` sets A to `blocked` and creates an orchestrator-owned pending response. `recovered` resolves it and returns the same record to `running`; no new record. Rule gap: `recovery` only guards the response owner, not lifecycle, pending state, or record linkage.

## M03 Terminal failure (`runs/continuation.json`, `runs/completions.json`)
Failed and succeeded ends run the same `terminal-result` rule and both create a steward-owned response. The outcome is stored but never read by any rule. A record's terminal failure does not close the intention.

## M04 Checkpoint restart (`runs/checkpoint-save.json`, `runs/checkpoint-resume.json`)
A separate process resumed with identical state, revision 1, and seen `[blockA]`, including the pending orchestrator-owned response. Responsibility survives as persisted data guarded by the model hash. It does not show anyone acting on it: zero events were replayed after resume, the owner is a string label, and the model has no liveness.

## M05 Multiple completions (`runs/completions.json`)
Both records end succeeded and each gets its own pending steward response. Only `endA` was considered, so `responses.endB` is pending work and the intention stays open. Ordering matters because `consider-completion` uses a `set` effect and would be rejected with `missing-update-target` if it preceded the matching end. Rule gap: no owner or pending guard on consider.

## M06 Two interfaces, one decision (`runs/decision.json`)
`chat` applied and set `decisions.D.answer = "end failed"`; `desk` was rejected with `stale-revision` and left state untouched (exit code 1 reflects the rejection, not a failure of the run). First arrival wins; without `expect_revision` the guard `answer == null` would reject it instead. The rule also moves the decision owner to `orchestrator`; the data does not explain that transfer. State does not record which interface answered.

## M07 Routing configuration (`runs/route-on.json`, `runs/route-off.json`)
The fixtures differ only in `config.desk`. The same rule fires and only the recorded `desk` flag on the pulse entry differs. The dial has no behavioral consequence in this model.

## M08 Launch versus drive (`runs/roles.json`)
The roles table declares start (user or event) separately from drive (user or autonomous): orchestrator is user-started but autonomous; steward is event-started and autonomous. The scenario has no events, and no rule reads `start` or `drive`, so this distinction is declared, not enforced.

## Unsettled events (`runs/unsettled.json`)
`threshold-reached` and `cancel` were both rejected with `no-enabled-rule`; state unchanged. The model does not cover threshold stopping or cancellation. What they should do, who may issue them, and whether they touch the intention needs design discussion.

## E01 Provenance and changed assumption (`runs/evaluate.json`, `runs/inspect-before.json`, `runs/apply-assumption.json`, `runs/inspect-after.json`)
The check evaluates claim `c` against trace `t` with provenance `t -> extract -> source`; outcome `satisfies` on the single checked event `choose`, computed at revision 0, saved as `evidence-check` at revision 1, state `current`. Applying the assumption edit (4 edits, revision 2) changed the extraction's ordering assumption and flagged `extract` and `t` as needs-review. The saved result is now `stale` by fingerprint mismatch, but the software did not re-run the check, change the outcome, revise the trace's `after: end` ordering, change the claim status, or update the saved node's own `meta.review_state`. Re-evaluation and deciding whether the trace still stands are human steps.

## E07 Synthetic versus historical evidence (`runs/node-source.json`, `runs/evaluate.json`)
The source declares itself a synthetic fixture with no historical incident. The checker carried that through: `synthetic: true`, `empirical_support: false`, `historical_behavior: not-established`. The satisfying result is a self-consistency check of authored data and changed no belief status; claim `c` remains proposed.

## Unresolved policy and limitations
See the `unresolved_policy` and `limitations` arrays in `answers.json`. Rule gaps above are assessments of the authored rules; the runtime behaved as the rules specify.
