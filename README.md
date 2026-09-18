# Theory graph

> "…programming properly should be regarded as an activity by which the programmers
> form or achieve a certain kind of insight, a theory, of the matters at hand."
> — Peter Naur, [*Programming as Theory Building*](https://pages.cs.wisc.edu/~remzi/Naur.pdf) (1985)

Theory graph is a shared workspace for designing software **together with an AI**.
While you talk through a design, the AI records the decisions, open questions and
reasons in a small graph. You watch that graph live in your browser. Together it
becomes a written record of the program's *theory*: what it is about, what it does,
and why.

**Watch everything the AI writes.** The tool is meant for sessions where you and
the AI work side by side. Left alone, an AI will build a graph that is too large
and not necessarily right. Keep the batches small, read each change in the
browser, and only you decide what is accepted.

## Quick start

```sh
git clone https://github.com/blakesims/theory-building-graph.git
cd theory-building-graph
pipx install .                # puts `tg` on your PATH (or just run ./tg from here)
tg skill install              # adds the /theory skill to Claude Code
tg --file examples/morphisms/graph.json serve   # open http://127.0.0.1:8767
```

Then, in the repo of the program you are designing, start Claude Code and type:

```
/theory new my-program
```

Keep the browser open next to the conversation and watch the graph grow.

## The building blocks

| Kind | What it holds | Example |
|---|---|---|
| **entity** | a thing the program is about | `invoice`, `user` |
| **operation** | something the program does | `send-invoice` |
| **claim** | one statement about an entity or operation, *proposed* or *accepted* | "An invoice is sent once." |
| **question** | something still undecided | "Who can void an invoice?" |
| **case** | a concrete scenario that tests the claims | "Customer pays twice." |

Secondary kinds support them:

| Kind | What it holds |
|---|---|
| **source** | your exact words, so every claim can point back to what was actually said |
| **trace** | a recorded run or sequence of events used as evidence |
| **check** | a saved result of testing a claim against a trace |

Relations between them (`about`, `answers`, `depends-on`, `challenges`, `revises`, …)
make the graph. Nothing is deleted: a revised claim keeps its history and reason.

## Example: the Morphisms graph

`examples/morphisms/graph.json` is a real design graph (about 280 nodes) built in
sessions like the ones above. Use it as a guide to what a careful graph looks like:

- every ruling has a verbatim **source** node with the user's words;
- claims are **proposed** until the user affirms them, then **accepted**;
- withdrawn claims stay, with the reason they were replaced;
- questions are answered by linking claims to them.

```sh
tg --file examples/morphisms/graph.json frontier   # open decisions
tg --file examples/morphisms/graph.json serve      # browse it
```

In the browser: press `/` to find a node, `Esc` to close the find panel, `p` to switch graph.

## For AI agents

If you are an AI agent and have just cloned or installed this tool:

1. Run `tg skill install` so the user can type `/theory <project>` in Claude Code.
   (`tg skill path` prints the skill file if you use another agent.)
2. Read [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) and
   [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) before writing to any graph.
3. Start the viewer (`tg -p <project> serve`) so the user can watch, record one small
   batch at a time, and never mark anything accepted without the user saying so.

## Everyday commands

```sh
tg new my-program                 # create and register ./theory/graph.json
tg -p my-program frontier         # open decisions and recent changes
tg -p my-program search owner     # find stable IDs
tg -p my-program review ID        # a node and its direct reasoning context
tg -p my-program questions        # question inventory
tg -p my-program check            # structural findings
tg -p my-program claim add RULE "text" --about SUBJECT --reason 'Record proposal'
tg -p my-program reviewed ID --reason 'Reviewed the tension'
tg -p my-program history          # audited revisions
tg -p my-program serve            # http://127.0.0.1:8767, serves every registered graph
```

A small worked example, in a throwaway project:

```sh
tg new example --dir /tmp/theory-example
tg -p example entity add owner "The program owner." --reason 'Name the subject'
tg -p example source add decision "The owner approves releases." --kind verbatim --author user --reason 'Preserve the decision'
tg -p example question add release-authority "Who approves releases?" --about owner --reason 'Record the question'
tg -p example claim add owner-approves "The owner approves releases." --about owner --source decision --kind paraphrase --status accepted --answers release-authority --reason 'Record the explicit decision'
tg -p example questions
```

Each write is one audited revision. `--dry-run` previews a write without saving it.
`--revises OLD --withdraw-old` replaces a claim and keeps its history. `tg apply`
takes a JSON batch for anything the typed commands cannot express (for example cases).

## Where graphs live

Each graph lives in the repo of the program it describes, usually `theory/graph.json`,
not in this tool's repo. `tg` only writes that local file; commit it like any other file.

`tg` picks a graph from `--file PATH`, then `-p NAME`, `$TG_PROJECT`, the nearest
`theory/graph.json` or `graph.json` above the current directory, then the registry
default. The registry is `~/.config/theory-graph/projects.json`; `tg projects`,
`tg use NAME` and `tg where` inspect or change it.

A successful write means the graph is valid, not that the interpretation is right.
That is what the human in the loop is for.

## Development

Python 3.10+, no runtime dependencies. `make test` runs the test suite.
`make browser-smoke` drives the viewer in a headless browser (needs `npx agent-browser`).
MIT licensed.
