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
tg -p my-program claim add RULE "text" --about SUBJECT --reason 'Record proposal'
tg -p my-program reviewed ID --reason 'Reviewed the tension'
tg -p my-program history          # audited revisions
tg -p my-program serve            # http://127.0.0.1:8767 — serves every registered graph
```

## Worked example

Use a new project, never somebody else's live theory:

```sh
tg new example --dir /tmp/theory-example
tg -p example entity add owner "The program owner." --reason 'Name the subject'
tg -p example source add decision "The owner approves releases." --kind verbatim --author user --reason 'Preserve the decision'
tg -p example question add release-authority "Who approves releases?" --about owner --reason 'Record the question'
tg -p example claim add owner-approves "The owner approves releases." --about owner --source decision --kind paraphrase --status accepted --answers release-authority --reason 'Record the explicit decision'
tg -p example questions
```

Each typed write is one audited revision. `--dry-run` previews its effects without
writing. Claims default to proposed until affirmed. `--revises OLD --withdraw-old`
records a replacement and preserves its history. `tg apply` remains the JSON escape
hatch. A question's declared status is authoritative, not inferred from metadata.

`tg -p example config autosync on` makes successful writes commit and push with the
write reason. Default is off. It pulls with rebase before pushing and never forces.
A sync failure leaves the write saved locally and reports the problem. `--no-sync`
skips the sync for one write; run `tg sync` once after a burst of writes.

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
observations, not fresh paid model trials. Superseded v0.1 requirements are reported
separately from the six v0.2 checks. `make baseline` checks a temporary copy
of the live graph. Tests and all archived trial artifacts live under `tests/`.
`tests/relocations.json` records every cleanup move without rewriting hash-bound
inputs or receipts. Historical decisions and findings live in `docs/worklog/`.

`theorygraph/` is the Python package. Graph data does not live in this repo: each graph lives in the git repo of the program it describes (`tg new <name> --dir DIR`, or `tg register <name> <path>`), and `tg sync` commits it there. Keep
backups and do not edit a graph file by hand while an agent is writing. The original
notebook remains a separate project on port 8766, not this viewer on 8767.
