# Changelog

## Unreleased

- Removed sync/autosync; tg only writes the local graph file. `tg sync`, `tg config autosync` and `--no-sync` are gone.

## 0.2.3

- Report current claims and questions whose dependency, answer or revision targets are withdrawn or retired.
- Add full-text `claims` listings and status filters for claims and questions.
- Let `sync` rebase with unrelated dirty work using autostash, while reporting graph and restore conflicts.
- Add audited `retire` for entities and operations and hide historical nodes in default anchor, search and frontier reads.
- Show explicit zero-conflict and informational finding counts in an otherwise empty frontier.
- Store graph and writer locks in per-path runtime directories instead of beside graph files.
- Document repo-local graph storage and the Morphisms design graph as the reference example.

## 0.2.2

- Count `performed-by` as operation coverage, so roles stop showing as uncovered entities.
- Add a global `--no-sync` flag that skips autosync for one write; `tg sync` catches up.
- Allow `claim add --status withdrawn`, so a rejected idea is recorded in one command.

## 0.2.1

- Report entities that have no operation acting on them.
- Add typed `--acts-on` and `--depends-on` relation flags.
- Show `acts-on` and `depends-on` as labelled dashed edges in the viewer.
- Show ready or blocked status for each open question in `frontier`.

## 0.2.0

- Declared question status is authoritative. Answer structure is optional advice.
- Accepted claims no longer produce an untested-claim finding.
- Only new potential-conflict and challenges edges automatically flag review.
- Typed write commands record one ruling in one audited revision, with dry runs.
- Optional per-project autosync commits and pushes writes using their reasons.
- Reads omit metadata bookkeeping and show questions in compact tables.

## 0.1.0

- Local JSON graphs with typed entities, operations, claims, sources and questions.
- Atomic batch edits with revision checks and complete audit history.
- Bounded retrieval by stable ID, title or alias.
- Explicit dependencies, question readiness and review records.
- Optional finite authority, cardinality and obligation checks.
- Saved evidence with input fingerprints and explicit check limits.
- Read-only browser inspector and project registry.
- Mechanical tests and preserved, independently graded agent trial receipts.
- Consolidated tests and fixtures, with historical prose in dated worklog notes.
