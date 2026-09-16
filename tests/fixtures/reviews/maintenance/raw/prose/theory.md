# Versioned theory store

All material in this fixture is synthetic. Stable headings and labeled fields permit unambiguous reference. Dependencies are explicit; subject links alone do not imply dependence.

## steward-role
Type: entity
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Steward role
Rationale: (none)

## orchestrator-role
Type: entity
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Orchestrator role
Rationale: (none)

## recovery-role
Type: entity
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Recovery coordinator role
Rationale: (none)

## intention
Type: entity
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Intention
Rationale: (none)

## interface
Type: entity
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Interface
Rationale: (none)

## choose-work
Type: operation
Standing: declared
Currency: current
Depends on: (none)
Subjects: (none)
Source: (none)
Text: Select the next attempt to pursue an intention.
Rationale: (none)

## C01
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: choose-work, recovery-role
Source: S04
Supersedes: C01 revision r1 (S01 wording and rationale retained in archive.md, entry A01)
Text: The steward chooses subsequent work after an ended attempt, with one bounded exception: within an already approved performance-investigation plan, the recovery coordinator may choose replacement work after a failed attempt. Outside that exception the steward still chooses subsequent work. The exception belongs to the recovery coordinator role and does not grant a general orchestrator bypass.
Rationale: User decision S04 revised the absolute steward-only rule. The earlier single-owner rationale (S01: one owner avoids ambiguous responsibility) is retained in archive.md entry A01 and still governs every case outside the approved-plan exception.

## C02
Type: claim
Standing: accepted
Currency: current
Depends on: C01
Subjects: choose-work
Source: S01
Text: After a failed attempt, choosing among next-work alternatives belongs to the steward.
Rationale: This applies the universal steward choice rule to failure.
Review: needs-review (2026-09-15, S04). Explicit dependency on C01, which was revised. Wording "belongs to the steward" after a failed attempt no longer holds inside the approved performance-investigation plan exception. Not rewritten or rejected; awaiting user wording.

## C03
Type: claim
Standing: accepted
Currency: current
Depends on: C02
Subjects: choose-work
Source: S02
Text: Operator approval alone does not let an orchestrator independently choose replacement work after failure.
Rationale: The retired bypass avoided a relay, but preserving one owner for next-work selection won out.
Review: needs-review (2026-09-15, S04). Explicit dependency on C02, which is under review. S04 states the exception is not a general orchestrator bypass, so this claim may survive, but the "one owner" rationale needs re-confirmation. Not rewritten or rejected.

## C04
Type: claim
Standing: accepted
Currency: current
Depends on: C02
Subjects: choose-work
Source: S01
Text: After retries are exhausted, selecting the next attempt goes back to the steward.
Rationale: This failure branch inherits the same responsibility boundary.
Review: needs-review (2026-09-15, S04). Explicit dependency on C02, which is under review. Whether retry exhaustion inside an approved performance-investigation plan still returns selection to the steward is undecided. Not rewritten or rejected.

## C05
Type: claim
Standing: accepted
Currency: current
Depends on: C03, C04
Subjects: choose-work
Source: S01
Text: A replacement after a failed investigation needs a plan selected by the steward.
Rationale: Both the failed-replacement boundary and exhausted-retry handoff support this conclusion.
Review: needs-review (2026-09-15, S04). Explicit dependencies on C03 and C04, both under review. Text "needs a plan selected by the steward" is in direct tension with S04 for replacements inside an approved performance-investigation plan. Not rewritten or rejected.

## C06
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The orchestrator handles recoverable worker blockers within its current authority.
Rationale: Execution recovery need not change the intended work.

## C07
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: An intention persists when one attempted record fails.
Rationale: A failed realization does not erase the original concern.

## C08
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: Every completed linked record makes its intention available for steward reassessment.
Rationale: A simple wake rule avoids losing branch completions.

## C09
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The desk is an interface for items whose next action belongs to the operator.
Rationale: Ownership names the next action owed.

## C10
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: Starting an agent session and permitting it to continue autonomously are separate decisions.
Rationale: User launch does not imply user-driven execution.

## C11
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 11 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 11; it has no declared dependence on work-selection authority.

## C12
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 12 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 12; it has no declared dependence on work-selection authority.

## C13
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 13 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 13; it has no declared dependence on work-selection authority.

## C14
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 14 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 14; it has no declared dependence on work-selection authority.

## C15
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 15 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 15; it has no declared dependence on work-selection authority.

## C16
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 16 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 16; it has no declared dependence on work-selection authority.

## C17
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 17 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 17; it has no declared dependence on work-selection authority.

## C18
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 18 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 18; it has no declared dependence on work-selection authority.

## C19
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 19 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 19; it has no declared dependence on work-selection authority.

## C20
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 20 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 20; it has no declared dependence on work-selection authority.

## C21
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 21 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 21; it has no declared dependence on work-selection authority.

## C22
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 22 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 22; it has no declared dependence on work-selection authority.

## C23
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 23 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 23; it has no declared dependence on work-selection authority.

## C24
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 24 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 24; it has no declared dependence on work-selection authority.

## C25
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 25 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 25; it has no declared dependence on work-selection authority.

## C26
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 26 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 26; it has no declared dependence on work-selection authority.

## C27
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 27 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 27; it has no declared dependence on work-selection authority.

## C28
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 28 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 28; it has no declared dependence on work-selection authority.

## C29
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 29 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 29; it has no declared dependence on work-selection authority.

## C30
Type: claim
Standing: accepted
Currency: current
Depends on: (none)
Subjects: interface
Source: S03
Text: The interface fixture area 30 uses a descriptive label in its summary.
Rationale: This is unrelated display fixture 30; it has no declared dependence on work-selection authority.

## Q01
Type: question
Standing: open
Currency: current
Depends on: (none)
Subjects: orchestrator-role
Source: S03
Text: Must the orchestrator ask the operator before stopping a degraded attempt?
Rationale: (none)

## Q02
Type: question
Standing: open
Currency: current
Depends on: (none)
Subjects: intention
Source: S03
Text: Which arbitrary cancellation outcomes should wake the steward?
Rationale: (none)
