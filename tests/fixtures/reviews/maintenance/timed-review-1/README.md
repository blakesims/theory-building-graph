# Separate timed agent review phase

This supplements the [original maintenance comparison](../comparison.md), whose evidence and grades remain unchanged. Both fresh no-tool Fable sessions reviewed their actual before/after documents, the same user revision and the same questions. Neither received the other representation, previous grades or expected answers.

| Recorded measurement | Graph | Prose |
|---|---:|---:|
| Agent review latency |43.28228654101258 seconds|44.13623091697809 seconds|
| Accounted primary tokens |40,009|26,179|
| Tool invocations |0|0|
| Independently graded core recovery |5/5|5/5|
| Human review/correction time |Unmeasured|Unmeasured|

Primary tokens include fresh, cache creation, cache read and output tokens, not unique prompt size. Latency is measured around the real process and can include provider/startup overhead. Runs were concurrent and may share service contention. This is one small synthetic pair, not a general speed/quality comparison or evidence that either representation is superior.

The five core grades assess recovery of the current rule, dependencies, history, unresolved questions and changed claim. They do not endorse every review suggestion: the graph review overstated likely C05 tension because an approved plan could already have been selected by the steward. That limitation remains in both independent grade receipts.

See each arm's `input.json`, `prompt.txt`, `stdout.jsonl`, `receipt.json`, `review-outcome.json` and `graded.json`. The S07 acceptance mapping requires the original maintenance study **and both** independently graded review receipts. No prior failed/negative finding was removed. This phase measures model review latency; it does not measure human review effort, corrections, or repeated long-term theory maintenance.
