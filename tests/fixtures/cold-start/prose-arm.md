# Versioned design notes
Same facts and source addresses as the graph arm.

## source-1
type: source
text: Session paraphrase: Blake initially allowed operator-approved orchestrator replacement to avoid a relay when the orchestrator already had the context.
status: recorded
source_kind: session-paraphrase

## source-2
type: source
text: Session paraphrase: Blake later chose the simpler rule: steward always chooses the work. Orchestrator can ask keep trying versus mark failed and let steward decide next.
status: recorded
source_kind: session-paraphrase

## source-3
type: source
text: Only summaries of M1688 and M1689 are supplied. M1688 describes repeated useful reviews without an effective ruling. M1689 describes planning a proposed solution instead of reassessing the original performance concern. The primary postmortems are unavailable in this fixture.
status: recorded
source_kind: summary

## steward-role
type: entity
text: Steward is the role responsible for selecting and sequencing work for a continuing intention.
status: declared

## choose-next-work
type: operation
text: Decide which subsequent work should pursue the intention. This decision is distinct from mechanically inserting a record.
status: declared

## replacement-exception
type: claim
text: Operator-approved orchestrator replacement can bypass steward.
status: withdrawn
review_state: historical
sources: ["source-1"]
rationale: Avoid a relay when the orchestrator has context; later rejected in favor of one owner of next-work choice.

## atomic-replacement
type: claim
text: Orchestrator replacement is atomic archive/add and does not wake steward until new work completes.
status: withdrawn
review_state: historical
sources: ["source-1", "source-2"]
rationale: An explored exception, retired when steward always choosing was selected.

## steward-next-work
type: claim
text: Steward always chooses next work after a failed attempt.
status: accepted
review_state: current
sources: ["source-2"]
rationale: Keep a clean responsibility boundary; orchestrator may end a failed attempt and return it to steward.

## consultation
type: question
text: Must the orchestrator consult the operator before ending degraded work, or may it end autonomously within a configured threshold?
status: open
review_state: current
sources: ["source-2"]
rationale: May ask does not establish mandatory consultation. This is not settled by next-work ownership.

## cancellation
type: question
text: Does every arbitrary cancellation wake steward, beyond the agreed failed terminal result?
status: open
review_state: current
sources: ["source-2"]

## concern-persists
type: claim
text: Ending a failed record attempt does not itself satisfy or withdraw the underlying intention.
status: accepted
review_state: current
sources: ["source-2"]

## Explicit relations
steward-next-work —about→ steward-role
steward-next-work —governs→ choose-next-work
steward-next-work —revises→ replacement-exception
steward-next-work —revises→ atomic-replacement
replacement-exception —governs→ choose-next-work
