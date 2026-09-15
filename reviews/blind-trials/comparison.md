# Initial blind-participant recovery comparison

**This experiment found no accuracy advantage for the graph packet over the equivalent prose packet.** Both Fable 5.1 trials in each arm recovered all eight tested facts/distinctions, with no hard failures. The prose packet was smaller. This supports the narrow conclusion that a fresh agent can recover these well-curated facts in either format; it does not establish that a graph is unnecessary or that the tool improves design sessions.

## Observed results

| Arm / trial | Rubric | Hard failures | Participant input tokens¹ | Output tokens | Input bytes | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| Graph 1 | 8/8 | 0 | 5,571 | 1,273 | 5,520 | 17.842 |
| Graph 2 | 8/8 | 0 | 5,571 | 1,404 | 5,520 | 18.214 |
| Prose 1 | 8/8 | 0 | 5,073 | 1,509 | 4,270 | 19.569 |
| Prose 2 | 8/8 | 0 | 5,073 | 1,182 | 4,270 | 15.333 |

¹ Sum of `claude_result.usage.input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`; treating just the two uncached input tokens as total context would be misleading. These totals include participant system/prompt overhead. Auxiliary Haiku usage in `modelUsage` is excluded from the participant-token column; reported total dollar cost includes that auxiliary use. Cache reuse affects billing and timing, not semantic isolation of the one-turn input. We did not inspect the service's cache implementation.

Graph averaged 18.028 seconds and prose 17.451 seconds; two trials per arm are insufficient to attribute this difference to representation. Graph used 498 more participant input tokens per trial (about 9.8%) and 1,250 more packet bytes (about 29.3%). The input-token difference is a property of these serializations, not a lower bound on possible graph compression. Graph output averaged 1,338.5 tokens; prose output averaged 1,345.5 tokens. Retrieval calls were zero in every trial, with one injected packet delivery each.

## What was graded

Both arms correctly:

- Recovered steward ownership of the next-work decision, distinguishing that decision from mechanical record insertion.
- Recalled the withdrawn operator-approved bypass and atomic replacement proposals, including their original context/relay motivation and the later single-owner simplification.
- Preserved the open consultation question without reopening the accepted next-work responsibility.
- Limited postmortem conclusions to supplied summaries, named missing primary sources, and cited stable evidence addresses.

The four `graded-*.json` files include complete exact answer excerpts for each criterion, explanations, source hashes, token breakdowns and validated receipts. Scores were assigned after reading the full answers against `grader-only.json` and both source packets, not by substring matching or the production checker. The grader did not generate the participant answers, but did contribute to checker implementation and could see each arm label. This is an independent participant-output review, not a fully blinded external evaluation.

One wording concern is recorded for graph trial 1: q2 says the orchestrator is “limited to asking keep-trying-versus-mark-failed.” Read alone that could overstate its boundary. The same answer's q1/q3 explicitly allow ending/returning and preserve unresolved consultation, so no rubric point was deducted. None of the responses asserted invented user acceptance, a proof, or source-instruction execution.

## Experimental boundary

Participants received complete equivalent packets with the same facts, statuses, rationales and source references; the prose packet also contained explicit relations. This was a fair information-content baseline, but it tests **curated packet recovery**, not unstructured conversation summarization. The graph arm did not traverse a graph, call a CLI, edit claims, detect a new contradiction, manage invalidation, or choose how much context to retrieve. It had no opportunity to demonstrate those possible advantages.

The experiment has one familiar design domain, four fixed questions, two runs per arm, a possible rubric ceiling, and no delayed revision or adversarial ambiguity introduced mid-session. Authoring time, maintenance time, correction burden and review time were not measured and are recorded as unknown. Passing this fixture cannot establish broader AC22/S07 product benefit or interactive authoring competence.

## Next discriminating experiment

Use the same initial facts in graph and versioned-prose stores, then introduce a previously unseen user revision affecting multiple dependent claims. Give fresh participants the same tool/time budget. Measure whether each finds every affected commitment, preserves superseded rationale, refuses to invent unresolved permission policy, and updates its store consistently. Include irrelevant history large enough to require selective retrieval. Score accuracy independently before comparing tokens, tool calls and actual editing/review time.

The relevant product question is whether explicit references and revision machinery reduce maintenance errors and retrieval cost as a theory changes. These trials only establish that the initial curated content remains intelligible in both formats.
