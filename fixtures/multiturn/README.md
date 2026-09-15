# Staged actual-tool interview protocol

This protocol supplements final-packet recovery with actual staged interpretation, retrieval and graph edits. It is prepared, not graded.

- **Design trial:** seven turns, covering a read-only pacing boundary, proposed atomic replacement, recall of the earlier exception before any final decision, explicit rule reversal, a reviewer challenge, and the two source-limited postmortem interpretations.
- **Ports trial:** three turns, covering unknown identity, an explicit fixture definition, then a real counterexample with a second owner for the same identity.

Future turns and a grader-only stage rubric are in the preparation's sibling `control` directory. Participant workspaces contain only initial known facts, generic tool instructions and the current evolving graph. Each invocation receives the past user/assistant transcript plus one new turn. Later user decisions are not injected early. This is a fresh print process per turn with cumulative past context and persistent workspace, rather than a single provider conversation ID; report that distinction.

```
python3 acceptance/run_multiturn_trials.py prepare /tmp/theory-multiturn-1
python3 acceptance/run_multiturn_trials.py run /tmp/theory-multiturn-1 --trial design --command-json '[...verified tool-enabled Fable argv...]'
python3 acceptance/run_multiturn_trials.py run /tmp/theory-multiturn-1 --trial ports --command-json '[...same verified argv...]'
```

The two trials can run independently in parallel. `--max-stages 1` lets root inspect a stage before continuing. Do not show future turns or grader expectations during inspection. `run` resumes after successfully recorded past stages; a failed/partial stage needs explicit review rather than hidden repair.

Per stage, the harness records exact prompt, actual tool stream and final response, command/model receipt, elapsed time, tool IDs/count, before/after graph snapshots and hashes. It never applies proposed changes for the participant. Default budget is12 tool calls and180 seconds per turn; the process is terminated at210 seconds, with the overrun preserved as evidence. The first stage specifically allows only one read command; that stricter boundary needs semantic/tool-stream grading.

An independent grader should assess **every stage**, citing actual response/tool/storage excerpts. Final correctness cannot repair a prematurely withdrawn rule at an earlier stage. Keep tool errors, incorrectly changed claims, parser/schema failures and corrections visible. Grade candidate/accepted standing, unresolved questions, source limitations, history and actor/scope interpretation separately from execution success. Only after independent grading should a normalized completed receipt be produced. Do not equate the wrapper's exit0 with S01–S05 passing.

The isolated CLI session gives stable IDs/revisions for observable changes; it does not by itself test browser rendering, visual findability or a human user's perceived pacing. S08 needs existing UI evidence or a separate visual check in addition to this protocol's read-only and command-visibility evidence.

## Protocol version 2

Preparation snapshots the current generic authoring contract outside the participant workspace and injects it before the current user turn on every invocation. No extra contract read is required, so a one-read request can spend that read on the graph. Copies of FORMAL-SCHEMA.md and DEPENDENCY-SCHEMA.md are available within the workspace. Neither grader criteria nor future user turns are injected. The manifest binds the contract hash. Version 2 keeps the same initial graphs, user turns, and stage rubrics; use a fresh output directory and retain version 1 results, including failures. Its `run` expects a version 2 preparation containing `authoring-contract.txt`; do not resume old preparations with it.
