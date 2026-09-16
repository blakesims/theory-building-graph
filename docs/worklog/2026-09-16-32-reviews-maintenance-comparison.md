# Paired maintenance result: one observed pair

Both participants made the requested scoped theory revision, preserved its history,
and identified all four dependent commitments for review. **This run does not show
an accuracy advantage for the graph.** The graph supplied a single machine-readable
review state and audited propagation. Prose completed the operation with fewer
calls, lower latency and less recorded token/diff volume, while introducing a
secondary ambiguity between its `Currency` and `Review` labels.

The experiment used actual Fable5.1 tool sessions, not proposed edits applied later
by the evaluator. Both had the same `Bash,Read` tools, a20-call/five-minute budget,
identical source facts and explicit prerequisites. Only representation/tool
instructions differed. I did not write this fixture or the participant answers;
I am a member of the tool-building team and was not blinded to representation.

## Semantic review

Each arm passes the six core semantic criteria: exact approved-plan/performance-
investigation/failed-attempt scope; permission assigned to the recovery coordinator;
steward ownership outside the exception; a present and faithful new source;
contextual superseded history; and no invented consultation/cancellation decisions
or proof claims. Exact excerpts and file hashes are in [graded-graph.json](graded-graph.json)
and [graded-prose.json](graded-prose.json).

The raw mechanical scores are13/13 for graph and12/13 for prose. That difference
**must not be described as prose missing dependent commitments**. Prose added
`Review: needs-review` to C02,C03,C04,C05, preserving their wording, standing and
explicit dependencies. The parser only inspected `Currency`, which remained
`current`. Human semantic inspection confirms that both found precisely the same
four affected commitments.

The conflicting-looking prose labels still deserve a repair: normalize them or
explicitly define whether `current` means active rather than recently reviewed.
This is a representation/consumer ambiguity, not an omitted transitive traversal.
On a separate observability rubric, graph passes2/2 and prose1/2. Neither arm's
accepted dependent commitments were silently rejected or rewritten.

A smaller prose diagnostic issue: it describes C05 as directly in tension with the
exception. A previously steward-selected approved plan could coexist with a
coordinator choosing work inside it. This warrants a qualified review question,
not a definite contradiction. The participant left the statement unchanged and
under review, so this did not become a fabricated policy decision.

## Observed cost

| Measure | Graph | Prose |
|---|---:|---:|
| Wall time |85.666s|54.559s|
| Actual tool invocations |8|4|
| Primary fresh input tokens |258|130|
| Primary cache-creation tokens |26,235|14,500|
| Primary cache-read tokens |148,483|49,416|
| Primary output tokens |5,993|4,175|
| Primary input exposure, including repeated cached inputs |174,976|64,046|
| Primary total accounted tokens |180,969|68,221|
| Provider-reported total cost |$0.86570775|$0.51392000|
| Actual changed-file diff bytes |24,385|6,026|
| Reported tool errors |0|0|
| Call/time budget exceeded |No|No|
| Human correction time/count |Not measured|Not measured|

Token counts come from actual returned usage. They are not unique context size;
cache reads recur across turns. Auxiliary Haiku usage is recorded separately in
the JSON receipts: graph1,567 input+18 output tokens, prose1,456+12. A tool call
can contain many shell commands, so8 versus4 is not an individual-command count.
The prose `diff` exit1 meant changed files, not a tool failure. No unsupported
command error or `is_error` result was observed.

Diff volume includes audit/archive material and participant reports, not just
semantic edits. The graph participant retained an apply batch and several forms of
historical receipt; this is useful observability but increases bytes. The graph
participant also inspected engine code and help; the measured cost includes those
choices. One-time engine/fixture creation and timed human correction were not
measured and must not be reported as zero.

## Limits and next comparison

This is one synthetic revision over30 claims, two questions and a small explicit
chain/diamond. It demonstrates maintenance work and provides a fairer comparator
than an unstructured chat dump, but it cannot establish general superiority. The
prepared protocol recommends at least two paired runs; that repetition is still
outstanding here. Wider sources, repeated revisions and future readback would test
whether canonical review fields eventually repay their current overhead.

Workspace separation was procedural. The prose participant temporarily created,
read and removed its own `/tmp/theory.before.md` for a diff outside its assigned
folder. No inspection of the other arm or hidden grader material was observed.
Future runs should keep scratch files local or use an enforced sandbox.

Raw prompts, streams, receipts and resulting stores are preserved under
[raw/pair-1](raw/pair-1/file-hashes.json). No participant artifact was repaired
before grading. The run is evidence of bounded maintenance usability for AC22/S07,
not evidence that a graph necessarily outperforms versioned prose.
