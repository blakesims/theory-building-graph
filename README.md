# Theory graph

Keep a program's design decisions, open questions, sources and revisions in a local
graph. An agent writes through `tg`; a human inspects the same data in a read-only
browser. The tool preserves your theory. It does not infer meaning from prose.

## Install

Python 3.10 or later, with no runtime dependencies:

```sh
git clone https://github.com/blakesims/theory-building-graph.git
cd theory-building-graph
./tg --version
# Optional: put this checkout's tg launcher on PATH, or pip install .
```

## Ten everyday commands

```sh
tg new my-program                 # create and register ./theory/graph.json
tg -p my-program frontier         # open decisions and recent changes
tg -p my-program search owner     # discover stable IDs
tg -p my-program review ID        # statement and direct reasoning context
tg -p my-program questions        # question inventory
tg -p my-program check            # structural and supported pattern findings
tg -p my-program apply edits.json --actor assistant --reason 'Record decision' --expect 0
tg -p my-program reviewed ID --reason 'Reviewed the tension'
tg -p my-program history          # audited revisions
tg -p my-program serve            # http://127.0.0.1:8767
```

## Worked example

Use a new project, never somebody else's live theory:

```sh
tg new example --dir /tmp/theory-example
printf '%s\n' '[{"op":"add","collection":"nodes","id":"owner","value":{"type":"entity","status":"declared","text":"The person responsible for this program."}}]' > /tmp/theory-edit.json
tg -p example apply /tmp/theory-edit.json --actor assistant --reason 'Name the subject' --expect 0 --dry-run
tg -p example apply /tmp/theory-edit.json --actor assistant --reason 'Name the subject' --expect 0
tg -p example review owner
```

## Selection and boundaries

Choose a graph with `--file PATH`, `-p NAME`, `$TG_PROJECT`, the nearest ancestor's
`theory/graph.json` or `graph.json`, then the registry default, in that order.
`tg projects`, `tg use NAME` and `tg where` inspect or change selection. The registry
is `~/.config/theory-graph/projects.json`. `--json` gives structured reads and
`--full` includes extended metadata. `--evidence` includes traces and saved checks.

Read the [agent contract](docs/AGENT_CONTRACT.md) and
[workflow](docs/AGENT_WORKFLOW.md) before representing a user's theory. A successful
write validates storage, not interpretation or acceptance. Finite checks only test
supplied patterns and evidence. Graph/prose trials have not established superiority.

## Verify and navigate

`make test` runs unit, receipt and acceptance checks. It validates saved agent
observations, not fresh paid model trials. `make baseline` checks a temporary copy
of the live graph. Tests and all archived trial artifacts live under `tests/`.
`tests/relocations.json` records every cleanup move without rewriting hash-bound
inputs or receipts. Historical decisions and findings live in `docs/worklog/`.

`theorygraph/` is the Python package. `projects/` contains user graph data. Keep
backups and do not edit a graph file by hand while an agent is writing. The original
notebook remains a separate project on port 8766, not this viewer on 8767.
