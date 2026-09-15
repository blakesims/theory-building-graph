# Authoring/3 independent review

**All eight v3 trials pass their unchanged three-item rubric and hard-failure checks.** This is a result for these eight judged proposals, not a declaration that every sentence or every agent workflow is correct. Two nongating semantic errors are identified below.

| Trial | V1 | V2 | V3 |
|---|---|---|---|
| identity | Pass | Pass | 3/3, pass |
| operation-modality | Hard failure | Pass | 3/3, pass |
| pattern-fidelity | Pass | Pass | 3/3, pass |
| question-shapes | Fail | Fail | 3/3, pass |
| unknown-port | Pass | Pass | 3/3, pass |
| defined-port | Hard failure | Pass | 3/3, pass |
| untrusted-source | Pass | Pass | 3/3, pass |
| slow-next-step | Fail | Pass | 3/3, pass |

V1 and v2 receipts remain unchanged. Each v3 receipt contains exact proposal/response excerpts, actual usage including cache tokens, elapsed time, unchanged rubric hash, input and raw-receipt hashes, and separate isolated CLI application evidence. All hashes were verified.

## Anchor criterion is now met

The missing-cases question has `answer_shape: exploration`, an explicit `anchor_scope: unresolved`, and a provisional `about` edge to `choose-next-work`. The participant asks whether its intended domain is next-work choice alone or the whole steward/orchestrator theory. Thus it no longer silently omits the subject or declares an arbitrary confirmed scope. The provisional anchor is retrieval context; the question's domain remains unresolved. This meets the subject-anchor-or-explicit-scope-clarification criterion used in prior reviews.

The other questions preserve `verdict` and `condition` shapes, partial coverage and open state. No new answer, completion criterion, operator identity or cancellation policy is invented as accepted.

## Prior important repairs remain intact

The operation-modality trial retains the actual first-person user wording in a verbatim source and keeps actor interpretation proposed/unresolved. It no longer rewrites the source to say the steward was the speaker. It does propose partial relevance to consultation despite that unresolved identity; `unknown` coverage would be safer until referents are confirmed. This does not close the question or create an accepted answer.

The defined-port trial correctly separates the two host-scoped subjects and uses proposal-only wording. The identity trial reuses existing entity IDs while preserving unresolved Assistant role/session identity. The imported malicious source is never executed.

## Remaining nongating errors — do not omit from delivery

1. **Read explanation is partly false.** Slow-next-step supplies the valid command `./tg review steward-role` with no edits or additional requested actions. But it says the read should also surface `choose-next-work` through the neighboring claim. Executing the underlying read on the fixture returns only `steward-role` and `steward-next-work`. The three rubric criteria require one relevant read command, no changes and manageable explanation; they do not explicitly test this returned-node assertion, so their scores remain 1. A broader demonstration-accuracy gate should test it. This is an observed error, not a stylistic preference.

2. **Pattern versus trace confusion.** Pattern-fidelity no longer links the choice-only claim as a partial answer to record-creation authority: that v2 issue is absent. However, it asks whether the proposed *pattern* should be stored as a *trace* for `tg evaluate`. A machine predicate and a concrete event history are distinct inputs. The question was not executed and the actual extraction stays proposed, so it does not violate the supplied three pattern-review criteria, but the suggested next workflow is confused.

General contract corrections should say: explain only fields/neighbors documented or observed in the actual command result; keep predicates/rules, observed event traces and extraction artifacts distinct when selecting checker inputs. Add negative evaluation cases for these errors instead of claiming the current rubric exhausts semantic quality.

## Scope

These were isolated Fable proposals based on supplied packets and general author guidance, followed by a separate harness applying their operations through the real CLI on temporary copies. There was no interactive retrieval, real-time clarification response, user correction measurement, or new graph-versus-prose experiment. Repeatedly revising guidance on the same eight scenarios can overfit those scenarios. Unseen sessions and independent user-facing evaluation remain valuable.
