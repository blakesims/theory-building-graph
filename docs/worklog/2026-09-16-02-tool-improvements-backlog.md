# Tool Improvements Backlog

**Date:** 2026-09-16
**Type:** note

## Summary

Actionable backlog for `tg`, distilled from one full design session (morphisms graph,
revisions 59 to 150, 2026-09-16), three outside reviewers, and the assistant's own use.
Ordered by value. Evidence for each item is in `2026-09-16-01-flash-review-tool-feedback.md`.
Pick up with any agent; each item is bounded.

## Details

1. **`check` flags a current claim whose `depends-on` (or `answers`, `revises`) target is
   withdrawn.** This was a real defect in the live graph and every reviewer found it by
   hand. Done when `check` reports it as a finding with both ids.
2. **Status-filtered listing with full text**: `tg claims --status accepted|proposed|withdrawn`
   (and the same for questions). Every reviewer fell back to jq. Done when the listing prints
   id, status and full text, optionally `--json`.
3. **`sync` tolerates a dirty working repo.** Graphs now live inside working repos, so
   unrelated unstaged changes are the normal case. Use `git pull --rebase --autostash` or
   fetch-and-fast-forward-check; never touch files outside the graph path. Done when sync
   succeeds with an unrelated modified file present and fails clearly on a real conflict.
4. **Retire for entities and operations.** No typed way exists; the assistant used raw
   `apply` to set `review_state: historical`. Done when `tg retire <id> --reason` works for
   entity and operation and retired nodes drop out of default reads.
5. **Revise an accepted claim in place, keeping history.** Today a revision means a new id
   with `-v2`, `-v3` and `--withdraw-old`; ids will rot. Proposal: `tg claim revise <id>
   --text ... --reason ...` bumps a version on the same id and keeps the old text in the
   audit log. Done when the id is stable across revisions and `history <id>` shows versions.
6. **`impact` and `walk` traverse `about`/`governs` toward the subject's dependents.**
   `impact run` reported zero dependents while five current claims were about it. Done when
   impact lists claims about an entity.
7. **`frontier` prints an explicit "0 conflicts, N informational findings" line** when the
   sections are empty, so a reader knows the check ran.
8. **A derived roles table**: `tg roles` walks each role to its `performed-by` operations
   and their `acts-on` entities and prints one table. The who-claims-what table lives only in
   claim prose today.
9. **`search --status` and no truncation with `--json`.**
10. **Lock files next to the graph** (`graph.json.lock`, `.write.lock`) need to be ignored by
    the host repo; either write them to a runtime dir or document the gitignore line.
11. **`recent changes` in `frontier` is useless above ~20 revisions a day.** Group by reason
    or show only the last five distinct reasons.
12. **Store the session method in the graph**, or at least a pointer: the one thing a
    handover note still has to carry is how to run the conversation (cases first, one move
    per turn). A project-level `meta.method` field with a path would let the frontier print
    it at session start.

## Follow-ups

- Items 1 to 3 first; they are the ones that cost real time today.
