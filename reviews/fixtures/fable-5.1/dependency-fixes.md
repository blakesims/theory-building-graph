# Dependency/storage fixes following Fable 5.1 review

All work uses isolated synthetic fixtures. The live theory graph is untouched. `dependency-regressions-before.txt` captures the first eight test methods before fixes (16 failed assertions/subtests, plus the passing retired-path control). `dependency-regressions-after.txt` captures13 passing regression methods, including five subsequently added scope/presentation controls. The independently supplied `pre-fix-output.txt` remains unchanged.

| Probe | Resolution |
|---|---|
| P1 | Clearing `needs-review` acknowledges a review; it does not change the reviewed semantic input or invalidate an already-reviewed dependent. A real content edit still propagates. Retiring/reactivating a prerequisite changes availability and still propagates. |
| P2 | Custom relations declaring dependency semantics now behave consistently for adding/removing edges and for editing their semantic declaration. A mere description edit or absent→explicit-none does not invalidate. |
| P3 / H2 | Prerequisite questions are checked against derived answer resolution; their default requirement is `answered`. Claim defaults remain `accepted`. Explicit `requires` is honored against the relevant derived resolution or standing. Stored `status: answered` cannot satisfy an actually unanswered question. |
| P5 | All known formal-model section shapes are validated before automatic interpretation, including when no pattern currently exists. Null maps, malformed pairs and missing write values produce explicit atomic graph errors, without revisions/audit changes. This is syntax validation, not an invented existence assumption. |
| P26 | `meta` must be an object when supplied. Null metadata is rejected atomically with a named error rather than reaching a crashing checker. Other consumed payload fields similarly require their documented object shape. |
| P28 | Question state disagreement has one finding, `answer-state-drift`, with explicit `stored_state` and `derived_resolution`. It covers both disagreement directions without duplicate conflicting labels. |
| P32 | Finding identity excludes observation revision/time fields. `computed_revision` remains in the receipt; unrelated revisions preserve the finding ID. |
| P20 | Coverage is derived through the evidence module's explicit coverage helper. A current supported saved evaluation counts; mere proximity/about-links to a trace do not. Declared case evidence remains distinct from executed checks. |
| M3 | Compact question output renders resolution/readiness per row instead of dumping all derived objects into the header. Text findings display severity and suppression labels. Structured JSON remains available. |
| L3 | Deletion guards inspect typed node references: pattern roles/operations, provenance IDs, event operation/role definitions and result inputs. Trace-local attempt/event labels and arbitrary text no longer create false references. |
| L5 | Historical pattern declarations are excluded from default current-gap reporting. Their historical data remains stored. |

## Cases that require explanation, not a false repair

**P24:** Invalidation through a retired intermediate remains intentional. If C still explicitly depends on retired B and B depends on changed A, C must not silently become current/ready. B stays historical, C is flagged, and readiness explains the unavailable prerequisite. Removing/replacing the dependency is a deliberate edit.

**P4:** Finite-trace `scope: all` means all events in the supplied trace. It is not a declaration that a normative comparison domain is inhabited. Policy comparison requires an explicit scope definition and an overlap/existence witness. The regression checks missing declaration and possibly-empty declaration do not yield a policy conflict; an explicit nonempty declaration enables the comparison. No universal witness is fabricated.

**P9:** Compact evaluation output now displays the checked event IDs (including empty), assessment/reachability, vacuity, permission-only status, evidence basis and empirical-support flag when returned by the checker. Updated evidence/checker semantics remain owned and tested in their modules.

The improvements do not formalize the user's unresolved Morphisms stopping/cancellation policy, prove arbitrary prose, or make stale historical evidence disappear.
