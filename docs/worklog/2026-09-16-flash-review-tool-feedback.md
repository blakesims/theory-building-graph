# Tool feedback from three DeepSeek Flash reviewers, 2026-09-16

Three read-only reviewers each got a private copy of the morphisms graph (revision 116,
124 nodes) via `--file`, a one-page briefing on the model and the read commands, and a
different focus (actors and waking; intention lifecycle; obstructions and cases). About
20 turns and $0.05 to $0.10 each. Together they produced 21 findings; roughly half were
real (stale entity text after a ruling, a wrong dependency edge, missing wake rules, two
accepted claims that disagree), the rest wording or already-answered. Overlap between
reviewers was low, so focus prompts worked.

## What helped (all three agreed)

- `node <id> --full`: text, metadata and every incident edge on one screen. The workhorse.
- `check --all` for ungoverned operations.
- `frontier` for the proposed-claims block, which is exactly the set to test for staleness.
- `review <id>` pulled in withdrawn neighbours, which made "does a current claim re-admit
  a rejected idea" fast (one reviewer); the other two found it no better than `node`.

## What was missing

1. A status-filtered listing: `claim ls --status withdrawn|proposed|accepted` with full
   text. All three fell back to jq or Python over the export.
2. `check` does not flag a current claim whose `depends-on` target is withdrawn. This was
   a real defect in the graph and every reviewer found it by hand.
3. `check` does not flag an operation named in an accepted claim that has no operation
   node (`claim` in intention-operation-set).
4. `search` mixes withdrawn and current results and truncates; no `--status` filter.
5. No edge-type or state-word query ("which current claims mention waiting").
6. `impact <id>` does not traverse `about`, so `impact run` reported zero dependents while
   five current claims are about it. Direction of `walk`/`impact` was not obvious.
7. `frontier` prints nothing under findings/conflicts when there are none; a "0 conflicts,
   3 informational" line would show that the check ran.
8. Entities and operations have no retired state (found by the assistant, same day).

## Verdict

Useful. The graph made an outside model productive on a design it had never seen, for
cents, and the findings were citeable by node id. Items 1 and 2 are the ones to do first.
