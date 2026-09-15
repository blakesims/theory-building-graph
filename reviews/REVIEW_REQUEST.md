# Independent review request — Fable 5.1

Project: /Users/blake/projects/theory-building-graph
Private remote: https://github.com/blakesims/theory-building-graph

Review the new build against acceptance/CONTRACT.md, acceptance/REVIEW.md, acceptance/cases.json and acceptance/run-report.json. The proposed acceptance contract corrects several earlier review expectations; challenge these corrections where warranted, but do not silently revert semantic distinctions to make tests easier.

Read implementation and run real CLI/unit/acceptance checks on temporary graphs. Preserve graph.json and the original notebook (port 8766). You may write a review in reviews/FABLE-5.1-REVIEW.md and supporting temporary fixtures under reviews/fixtures. Do not edit implementation during review.

Look especially for false positives and false passes:
- unsupported, incomplete or ambiguous patterns counted as successful compliance;
- ordinary node adjacency accidentally treated as logical dependence;
- missing transitive versioning, withdrawn prerequisites disappearing;
- role intersection/existence and cardinality vacuity mistaken for contradictions;
- check results surviving semantic changes without staleness;
- tests mirroring production code or precomputed answers rather than independent oracles;
- scripted session replays misrepresented as independent LLM evaluation;
- mutation/retrieval holes, live-data regressions, unsafe source instructions;
- acceptance criteria covered only by test names with weaker assertions.

Report severity, exact reproduction commands, actual versus expected, file/line references, proposed minimal remedy and whether an issue prevents honest all-scenarios completion. Distinguish implementation bugs from unresolved product semantics. Do not invent Morphisms policy to close open design questions. At the end give a clear verdict and all commands executed.
