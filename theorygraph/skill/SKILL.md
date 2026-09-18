---
name: theory
description: Run a theory-building design session against a named theory graph project using the `tg` CLI (Naur, "Programming as Theory Building"). Use when the user invokes /theory <project>, asks to record, revise or inspect the theory of a program, wants to start a new theory project, or says "design session" / "theory graph".
user_invocable: true
---

# Theory graph session

`tg` keeps the theory of a program as a graph of entities, operations, claims, questions and cases, with explicit standing, sources, dependencies and audit history. The human talks and decides; you retrieve, propose and record. The tool never infers meaning from prose.

This is a collaborative tool. The user watches the graph in the browser while you work. Record small, reviewable batches and show each one before moving on. Never build large parts of the graph on your own: an unsupervised graph grows too big and records things the user never agreed to.

## Where things are

Run `tg where` first. It prints the engine root (the tool's source checkout or installed package), the registry, and which graph the current directory resolves to. Graphs do not live in the tool's repo: each graph lives in the repo of the program it describes, usually at `theory/graph.json`.

Read `docs/AGENT_CONTRACT.md` and `docs/AGENT_WORKFLOW.md` in the tool's repo (https://github.com/blakesims/theory-building-graph) before writing to any graph.

## Invocation

```
/theory <project>                 open a session on a registered project
/theory <project> <request>       same, then act on the request
/theory new <name> [--dir DIR]    create a project (default DIR: ./theory in the current repo)
/theory projects                  list registered projects
```

Every `tg` call takes `-p <project>`. Never rely on the registry default when a project name was given.

## Session start

1. `tg -p <project> frontier`. That is the work list: open questions, nodes needing review, proposed claims awaiting the user's decision, review-severity findings, unresolved tensions, recent changes. Report it as a short table.
2. If the request names a node, `tg -p <project> review <id>`. Otherwise `tg -p <project> search <term>` first.
3. Make sure the viewer is running so the user can watch: if nothing answers on http://127.0.0.1:8767, start `tg -p <project> serve` in the background. One server shows every registered graph. Link nodes as `http://127.0.0.1:8767/?p=<project>#<id>`.

## During the session

- Follow `docs/AGENT_WORKFLOW.md`: locate, separate source from interpretation, preview one change, apply one authorized batch, reconcile, stop with one useful next question.
- Preview every write with `--dry-run` and show the effects (new findings, nodes newly needing review, question resolutions) before asking approval. Then write for real, with `--expect <revision>` for `apply`.
- After a write, clear bookkeeping you have actually reviewed with `tg -p <project> reviewed ID [ID ...] --reason '...'`. Do not mark something reviewed to make the frontier shorter.
- Every claim and question needs an `about` or `governs` anchor. One proposition per claim. New interpretations start as `status: proposed`; only the user makes something `accepted`. Rationale goes in the reason, not in the claim text.
- Keep the user's own words as `source` nodes and link claims to them.
- `check` hides informational findings by default; `check --all` lists them. Evidence nodes (traces, saved checks) are hidden from reads by default; `--evidence` includes them.
- Use `--json` when you need to parse output. Read `tg <cmd> --help` rather than guessing flags.

## New project

`tg new <name>` copies the standard vocabulary into `DIR/graph.json` and registers the name. Start by recording the two or three entities and operations the program is about, then the claims the user already holds, each with its source. Ask before recording anything as `accepted`. The graph is a plain file; commit it with the rest of the program's repo when the user asks.
