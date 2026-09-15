# Theory graph

A local tool for keeping the *theory* of a program (Naur, "Programming as Theory Building") as an inspectable graph while you design with an AI agent. Entities, operations, claims and questions carry explicit standing, provenance, declared dependencies and an audit history. The agent authors through the CLI; the human reads the browser view. The tool never infers meaning from prose.

## Use it anywhere

```sh
tg projects                       # registered projects, default marked *
tg -p morphisms overview          # counts by type and status
tg -p morphisms check             # structural findings and declared tensions
tg -p morphisms questions         # open, answered and needs-review questions
tg -p morphisms review steward-role
tg -p morphisms serve             # viewer at http://127.0.0.1:8767
tg new my-program                 # ./theory/graph.json from the template, registered as my-program
```

`tg` is on PATH via `~/bin/tg` (installed by `~/dotfiles/install.sh`). The graph a command targets is chosen by, in order: `--file`, `-p NAME`, `$TG_PROJECT`, the nearest `theory/graph.json` above the working directory, then the registry default (`tg use NAME`). The registry lives at `~/.config/theory-graph/projects.json`.

In Claude Code or Pi, `/theory <project>` starts a design session on a registered project and `/theory new <name>` creates one.

## Layout

| Path | What |
|---|---|
| `tg` | Launcher. Symlink-safe |
| `theorygraph/` | The engine: `graph.py` (CLI, store, serve), `dependency.py`, `formalcheck.py`, `tracecheck.py`, `replay.py`, `projects.py`, `template.json`, `viewer/` |
| `projects/morphisms/graph.json` | The Morphisms theory. Canonical user data |
| `docs/` | Agent contract, workflow, dependency schema, product notes, build report, worklog |
| `tests/` | Unit and receipt tests |
| `acceptance/` | 80-case acceptance contract, runner, trial and evaluation tooling |
| `fixtures/`, `reviews/` | Recorded trial inputs, receipts and independent reviews. Evidence, not code |

## Working with an agent

Read [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) before writing to a graph. [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) is the session loop: locate, separate source from interpretation, preview one change, apply one audited batch, reconcile with `impact` and `readiness`, stop with one useful question. [docs/DEPENDENCY-SCHEMA.md](docs/DEPENDENCY-SCHEMA.md) defines transitive review, readiness and version receipts.

Writes are one JSON operation array:

```sh
tg -p morphisms apply edits.json --actor assistant --reason 'Record the user clarification' --expect 16
```

`--expect` rejects stale revisions. Unknown endpoints, types or states reject the whole batch. Semantic edits mark declared dependents `needs-review`. The browser is read-only.

## Verify

```sh
make test          # 256 unit and receipt tests
make acceptance    # 80 cases, 22 criteria, against recorded receipts
make baseline      # checker outcomes on a temporary copy of the live graph
python3 acceptance/browser_smoke.py   # real browser run on an isolated graph (needs npx)
```

`make acceptance` validates saved LLM trial receipts. It does not rerun paid model calls. See [docs/BUILD-REPORT.md](docs/BUILD-REPORT.md) for what the evidence does and does not establish. The graph and prose experiments did not show that graphs beat prose. The supported benefit is explicit retrieval, dependency and check state with inspectable history.

## Boundaries

This is a tool for developing a theory, not the Morphisms runtime. It does not prove natural-language consistency, source fidelity or agent reliability. Finite pattern checks (`tg evaluate CLAIM TRACE`) cover only declared patterns against supplied traces. See [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) and [acceptance/FORMAL-SCHEMA.md](acceptance/FORMAL-SCHEMA.md).

Keep backups. There is no sync service, and the graph must not be edited by hand while an agent is writing.
