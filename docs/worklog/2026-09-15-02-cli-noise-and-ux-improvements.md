# Cli Noise And Ux Improvements

**Date:** 2026-09-15
**Type:** note

## Summary

A session report on the first real decision recorded through `tg` (revision 17) rated the tool at roughly 1 part signal to 3 parts noise. The assessment is largely warranted. The two real catches (the frontier pointed at the one decision, and the dry run on a scratch copy exposed a stale "may ask" claim) came from the tool's structure. Most of the cost came from four fixable sources: a four-command session opener, no dry run, informational findings shown as if they mattered, and evidence machinery mixed into the theory. One item was a bug: a review note invalidated six saved check results. All of that is now fixed on the `cli-noise` branch, merged to main.

## Details

### Verdict on the report

| Item | Report said | Verdict | What changed |
|---|---|---|---|
| S1 | Open question plus conflict link pointed at the one decision | Agree | `tg frontier` gives that in one command |
| S2 | Practice run caught a stale accepted claim | Agree, this is the tool's core value | `apply --dry-run` prints the effects report without a scratch copy |
| N1 | 13 edits, 3 practice runs, 474-line diff | Partly. The edit count is the decision's real footprint. The diff is the audit log stored inside graph.json | Dry run removes the practice copies. Audit-log storage unchanged (see follow-ups) |
| N2 | Four of six steps were tidying flags the tool raised about itself | Partly. The flags came from `answers` edges to a withdrawn claim, which is signal. Clearing them was expensive | `tg reviewed ID... --reason` clears them in one audited call |
| N3 | Adding a note marked six saved checks stale | Agree, a bug | Fingerprint now ignores `review_note`, `review_result`, `review`, `note`, `notes` |
| N4 | 12 of 34 nodes are test machinery | Agree | `trace` and `check-result` are evidence types, hidden from reads unless `--evidence`; overview counts them separately |
| N5 | 4 of 5 findings were coverage notes | Agree | `check` collapses informational findings to a count; `--all` lists them |
| Size | A one-page decisions file would hold the same content | Agree at 8 claims and 6 terms. Unproven either way at scale; the build's own prose/graph pair showed no graph advantage | Use it on real sessions and keep measuring |

### Before and after on the morphisms graph (r17)

`check` went from six informational lines to `0 findings · 5 informational` on one line. `frontier` shows one open question, one node needing review, one proposed claim, no findings, no conflicts, no stale evidence, and the last changes. `overview` reports 26 theory nodes plus 9 evidence nodes.

### New CLI surface

| Verb or flag | Purpose |
|---|---|
| `frontier` | Session opener: open questions, needs-review, proposed claims, review findings, conflicts, stale evidence, recent changes |
| `apply --dry-run` | Effects report: findings added or removed, nodes newly needing review, question resolution changes, evidence going stale |
| `reviewed ID... --reason` | Clear review flags through the audited path |
| `where` | Engine root, registry, resolved graph and how it was chosen |
| `sync` | Commit the graph if changed, pull with rebase, push. Aborts on conflict, never forces |
| `check --all`, `--evidence` | Show informational findings; include evidence nodes |

### Cross-machine setup

Server `zen` is primary: `~/repos/theory-building-graph`, `tg` in `~/bin`, `/theory` skill linked for Claude and Pi, `morphisms` registered as default. Mac mirrors it at `~/projects/theory-building-graph`. Dotfiles carry the skill and the install line. A fresh clone had failed 22 receipt tests because gitignored empty `.lock` files were hashed by receipts; they are tracked now and the validators also accept a missing lock as empty.

### Remaining UX ideas, not built

| ID | Idea | Effort |
|---|---|---|
| U3 | Decision queue in the viewer with accept / withdraw / answer actions written as `human-viewer` batches | Medium |
| U4 | `tg capture --actor user "verbatim"` to store a source node in one call | Low |
| U5 | `tg new` also writes `theory/CLAUDE.md` pointing agents at `tg` | Low |
| U6 | Lint on apply: one proposition per claim, missing anchors | Low |
| U7 | `tg render` to Markdown | Medium |
| U8 | Frontier size over time | Low |
| N1 | Move the audit log out of graph.json (append-only changes file) so graph diffs are readable | Medium, touches receipts |

## Follow-ups

- Run the next Morphisms decision through `/theory morphisms` on the server and compare the step count against this report.
- Decide whether the synthetic traces and check results should leave the morphisms graph for a fixtures project. Hidden by default now, still stored.
- The Mac main checkout has the frontend agent's uncommitted viewer work and is behind origin. It catches up when that agent commits and rebases.
