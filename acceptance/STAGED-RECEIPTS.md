# Scoped staged evidence

A failed staged session may support a narrower case only through an explicit
scoped receipt. `parent_trial` identifies the parent directory;
`parent_graded_sha256` and `parent_hard_failures` bind and disclose its full grade.
Each parent rubric criterion declares `cases`. A scoped receipt must contain
exactly every parent criterion assigned to its case, with unchanged grades and
criterion definitions. A failed relevant criterion remains a failure. The parent verdict and failure list
must agree with its own complete grade set. Its rubric must cover every recorded
participant stage; renaming a scoped report or deleting failed criteria does not
turn it into a successful whole-trial report.

The child binds the same input and participant JSON as its parent. Every listed
stage must retain its original `control/<stage>/receipt.json`, `prompt.txt`,
`stdout.jsonl`, `before.graph.json`, and `after.graph.json`. The gate checks artifact
membership and hashes, exact receipt copies, input prompt coverage, successful
process termination, and graph continuity from the initial state through every
stage. Omitting an unrelated failed stage does not make a valid scoped receipt.

A targeted fork preserves copied stages as earlier observations, including their
actual prompt bytes and contract versions. A new stage does not retroactively
upgrade earlier stages to a newer authoring contract. The fork manifest records
source and copied hashes; the receipt's scope explains this mixed provenance.

`component_partial: true` with `criterion_ids` can name a passing subset of a
case's parent criteria. It cannot satisfy a full acceptance mapping on its own.
A composite receipt binds these components with explicit `required_evidence_slots`
in its rubric. Component criteria, source receipts, artifact slots, and parent
failure disclosures are verified recursively. A failed observation retained
outside a component's scope is disclosed rather than silently turned into a pass.

These are integrity checks, not independent semantic regrading. The grader must
still judge what the participant actually said and did. Hashes cannot establish
that the chosen rubric was adequate or that a quoted explanation is correct.
