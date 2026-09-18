# Agent workflow

Read [AGENT_CONTRACT.md](AGENT_CONTRACT.md). The graph records a theory and its
revisions. In other words: saving an interpretation does not establish its truth.

1. **Locate.** Select the project with `-p NAME`. Open `tg frontier`, then use the
   supplied reference directly with `tg review REFERENCE`. Search only when the
   reference is unknown. Honor any smaller read budget, including preparation.
2. **Separate source and interpretation.** Preserve exact wording with `source add`
   and its speaker. Use labelled paraphrases when exact wording is unavailable.
   Keep one proposition per claim, with a subject. Leave ambiguous interpretations
   proposed. A related accepted claim is context, not authority to rewrite a source.
3. **Record one authorized decision.** Use a typed command such as
   `tg claim add RULE "text" --about SUBJECT --source SRC --status accepted
   --reason "User affirmed this rule"`. Preview with `--dry-run` when useful.
   For a replacement, add `--revises OLD --withdraw-old`. Use `apply` only for
   changes the typed commands cannot express. Never hide several independent
   decisions inside one batch. A proposal-only request authorizes no write.
4. **Reconcile scope.** Link an answer using `tg answer Q --with CLAIM --reason "..."`.
   Full accepted answers declare the question answered. Partial coverage leaves
   independent unknowns open. Review potential conflicts before clearing their
   flags with `reviewed`. Use `impact`, `readiness` or `check` when relevant, not as
   mandatory ceremony after every sentence.
5. **Finish.** Writes land in the local graph file only; committing it is left to
   the user. End with one useful question, or stop when done.

One viewer serves every registered graph: `http://127.0.0.1:8767/?p=PROJECT#ID`, with a
switcher on `p`. Omit `?p=` for the graph the server was started on. Keep it open:
the user should watch every change land. Optional `evaluate CLAIM TRACE` checks
finite supplied evidence, not prose fidelity, source truth or unbounded reachability.

Use temporary copies for examples and experiments, never somebody's live graph.
