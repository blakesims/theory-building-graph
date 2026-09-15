# Tool-enabled interpretation trial

The independent Fable participant completed all16 required subprocess commands and
correctly interpreted the ten M/E cases plus the execution/unknown-policy criteria:
**12/12 semantic criteria**. The13 receipt tests additionally verify preserved
input hashes, command/output bindings, the actual states and the authorized
assumption edit. The participant's files were copied after process completion and
were not repaired for grading.

The useful observation is narrower than runtime correctness: the participant
recovered ownership, continuation, checkpoint persistence, pending completions,
stale decisions, routing flags, role configuration and stale provenance from actual
outputs. It explicitly distinguished a missing authored rule from a policy decision
and synthetic consistency from historical evidence. It also identified candidate
missing guards in the sample model without presenting those as observed Morphisms
failures.

Three wording caveats are retained in the grade. A hypothetical early consideration
would produce `missing-parent`, not the participant's `missing-update-target`.
The routing configuration itself differs in addition to its recorded pulse flag.
And “human step” for re-review is too specific: the checker does not repair an
extraction automatically, but that does not forbid a future agent from reviewing
it. None changes the correctly reported observed states or accepted policy.

This was substantial rather than lightweight:263.691 seconds,32 tool invocations,
16 captured commands and536,129 accounted primary tokens including repeated cache
reads. One exploratory shell marker produced an error and was recovered; the two
captured replay exit1 results were intentional rejected-event cases. Actual
provider usage and raw stream are preserved; timed human correction was not
measured. These costs should remain visible when judging tool usability.

The grader belongs to the tool-building team but did not produce the participant
answers. This is one isolated, explicitly authored finite-model interpretation
trial, not an external blinded panel, universal theorem, or live Morphisms runtime
integration test. See [graded.json](graded.json), [participant.json](participant.json),
and the unmodified [participant interpretation](workspace/interpretation.md).
