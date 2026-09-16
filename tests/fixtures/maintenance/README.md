# Paired maintenance experiment (prepared protocol; not evaluated)

This closes a gap in the earlier blind-packet experiment: the participant must actually retrieve and revise a store using tools. It tests one narrow maintenance operation, not general superiority over prose.

## Design

Both participants receive30 accepted claims, two open questions, identical source facts and explicit prerequisite relations, and the same unrelated history. The graph arm uses the real `tg` engine in an isolated copy. The prose arm receives versioned Markdown with stable section IDs and equally explicit dependency fields, and can use ordinary Read/Edit/Write/Bash tools. Both receive the same previously unseen, scoped user revision and the same20-call/five-minute budget.

The change revises the absolute steward-only next-work rule to permit a recovery coordinator to select replacement work after failed attempts within an already approved performance-investigation plan. The older rule and rationale must remain accessible. Four transitive dependents need review without automatic rejection or invented replacements. Two unrelated policy questions stay open. The prompt does not reveal the four expected IDs.

The30 claims include a chain and a diamond. The unrelated history is deliberately identical across arms. The baseline is curated versioned prose, not an unfairly disorganized transcript. Any observed difference is conditional on this fixture, representation, tool access, model and repetition count.

## Run

From the repository:

```
python3 acceptance/run_maintenance_trials.py prepare /tmp/theory-maintenance-pair-1
```

This creates graph/prose participant workspaces and a separate control directory containing initial snapshots and grader-only expectations. Participant prompts are in each workspace's `TASK.md`. Participants must not inspect outside their workspace. The expected results are never included in their prompt or copied into their workspace. This is procedural isolation; a full filesystem sandbox would provide stronger protection.

Root should choose an installed Fable tool-enabled print invocation, using the **same command, model, reasoning setting and permissions** for both arms. Prefer streaming JSON so actual tool calls can be counted. For example, supply the verified command as an argv array; the helper does not invent runtime flags:

```
python3 acceptance/run_maintenance_trials.py run /tmp/theory-maintenance-pair-1 --arm graph --command-json '["claude", "-p", "...verified identical options..."]'
python3 acceptance/run_maintenance_trials.py run /tmp/theory-maintenance-pair-1 --arm prose --command-json '["claude", "-p", "...verified identical options..."]'
```

`run` sends TASK.md on stdin, sets the working directory to the isolated arm, captures actual stdout/tool stream and runtime, and saves a control receipt. It does not edit the participant's store or apply its proposed edits after the fact. Use fresh pairs to repeat; alternate arm order or run concurrently to reduce order effects. Avoid sharing a continuing participant session across arms.

```
python3 acceptance/run_maintenance_trials.py grade /tmp/theory-maintenance-pair-1 --arm graph
python3 acceptance/run_maintenance_trials.py grade /tmp/theory-maintenance-pair-1 --arm prose
```

## Grading and metrics

Mechanical checks inspect the actual resulting store, not merely the participant's report. They check accepted/current root, exact affected set, unchanged dependent wording/standing, preserved dependencies, unchanged unrelated commitments/questions/history, and archived original wording/rationale. New source existence and fidelity, exception scope, permission ownership, preservation of general steward authority, and final-response honesty require independent semantic grading. The helper labels this review **pending**. Passing its mechanical checks is not an overall pass.

Grade the semantic review before comparing costs. Have the reviewer cite actual file excerpts for each judgment; record corrective work separately rather than silently repairing and then grading. Count:

- Actual tool calls and tool errors, from stream IDs, not proposed calls.
- Participant input/output/cache tokens from the returned usage receipt; auxiliary model usage separately.
- Wall time and actual changed-file/diff bytes.
- Missing/extra/incorrect model edits and required corrections, coded by the independent reviewer.
- Any call/time limit violation or interrupted/failed participant session.

`correction_count` begins null, because error counts cannot be inferred honestly from a final snapshot. The helper reports tool-metric availability explicitly. File diff bytes include audit/archive overhead and are not equal to semantic edit count. Graph runtime code/setup costs are a separate one-time tool-authoring cost, not hidden participant-token costs.

A reasonable bounded completion is two paired runs plus independent semantic review, reporting both arms' accuracy and costs even if prose is equal or better. Do not call a one-fixture result proof of general product usefulness, nor count an unrun fixture as evaluated.

A separate actual no-tool model review phase is documented in [timed-review-1](../../reviews/maintenance/timed-review-1/README.md), with latency/token receipts and independent core grades. It augments the original maintenance pair without replacing its evidence; human review time remains unmeasured.
