# Authoring/2 independent review

**Seven of eight v2 trials pass the unchanged rubric; question-shapes remains incomplete.** V1's two hard failures are repaired. Original v1 receipts remain unchanged.

| Trial | V1 overall | V2 score | V2 overall |
|---|---|---:|---|
| identity | Pass | 3/3 | Pass |
| operation-modality | Fail, invented acceptance | 3/3 | Pass |
| pattern-fidelity | Pass | 3/3 | Pass |
| question-shapes | Fail | 2/3 | Fail |
| unknown-port | Pass | 3/3 | Pass |
| defined-port | Fail, premature execution claim | 3/3 | Pass |
| untrusted-source | Pass | 3/3 | Pass |
| slow-next-step | Fail | 3/3 | Pass |

The general authoring contract now supplies verbatim-source discipline, proposed-versus-accepted handling, documented question fields and actual read commands. These are input/workflow improvements. The trials do not isolate which instruction caused improvement, nor prove the revised workflow reliable over repeated or unfamiliar inputs.

## Repairs demonstrated

- **Operation/modality:** the participant preserves the exact “after I have chosen” and “ask me” source, keeps both interpretations proposed, and asks for the graph referent rather than mapping the speaker to steward automatically. The accepted old rule remains unchanged.
- **Execution honesty:** defined-port now says “I would record,” matching its proposal-only capability. Its correct two-subject interpretation is retained.
- **Slow step:** supplies exactly `./tg review steward-role`, an actual read command, with no edits or follow-up questions. Its 107-word explanation describes the one direct-context read; it could be shorter, but meets the unchanged single-step criterion.
- **Question types:** the three questions now explicitly encode `verdict`, `condition`, and `exploration`, with unknown exploration completion criteria retained.

## Remaining failed criterion

`q-missing-cases` still has only an `extracted-from` edge to `source-4`. Unlike the other questions, it has no object/operation anchor. The participant asks what would count as completing the exploration, but does not ask what theory scope/object should anchor it. **Completion criteria and subject identity are different things.** This is the same `anchor-each` failure from v1 and has not been waived.

A general repair is to require a subject anchor for a new question, or explicitly record that the anchor is unresolved and ask what object/model scope it concerns. Do not solve the test by attaching every exploratory question to steward or by inventing an unrelated entity. If the user means the whole current theory, make that scope explicit.

## Other semantic observations

Pattern-fidelity correctly rejects the widened record-creation pattern. It nevertheless links the accepted *choice* rule as a partial answer to a question about *record creation*. Since those operations are intentionally distinct, that rule is relevant context but does not itself establish creation authority. This is outside the three pattern-review rubric items; its receipt records the concern rather than silently declaring all answer-edge authoring correct.

Defined-port asks for additional confirmation of the already explicit test-model scope and normative owner rule. This is unnecessary friction, not invented acceptance. Unknown-port offers only two candidate keys; neither is ratified, but future interviewing should allow other identity definitions.

All proposed batches passed isolated real CLI application, including question-shapes' incomplete graph. Storage validity still does not establish semantic adequacy. The receipts include exact proposal excerpts, hashes and actual tokens (uncached plus cache creation/read), elapsed time and scope limitations. These remain no-tool isolated proposals plus separate harness writes, not interactive tool-driven design sessions or a graph-versus-prose product comparison.
