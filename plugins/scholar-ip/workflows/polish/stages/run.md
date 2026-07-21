# workflow:polish.run

Williams-style prose polish that can run on any safe target, including a standalone
file outside an EviDraft project. It does not require an EviDraft project, approved
scope, or evidence store. It reduces AI-flavour without changing meaning, preserves
claim-bearing text, and always ships a diff log so a human can review what changed
and why. The default `mode=all` applies every hunk that passes fidelity review.

This is **not** a detector-evasion tool. Invocation framings like `--evade-detector` are refused. The skill defines the full refusal-flag list and regex in `../../../capabilities/editing/humanize/references/ethics-and-refusal.md` — that is the source of truth; the example here exists only so the LLM has an anchor before the skill is loaded.

## Steps

1. **Pre-flight.**
   - Refuse if the invocation matches any refusal flag / regex from `../../../capabilities/editing/humanize/references/ethics-and-refusal.md`. Print the ethics block (from the skill) and exit non-zero.
   - Refuse if `target` resolves to a path under `.evidraft/`. We polish manuscripts (`manuscript/...`), not the evidence store.
   - If an evidence store exists, load its entity records for the fidelity audit. A
     missing evidence store is allowed; report reduced entity-verification coverage
     and preserve entities directly observed in the original hunk.
   - Resolve `target`: if a directory, glob `*.tex` / `*.md` non-recursively; if a file, use it directly. If `section` is set, slice to the `\section{<section>}` block (inclusive of its `\subsection{}`s, exclusive of the next `\section{}`).

2. **Lint pass.** Before rewriting, scan the resolved target(s) for banned phrases and AI-tells (the list lives in `../../../capabilities/editing/humanize/references/banned-phrases.md`). Report counts per phrase to chat and into the report under "Banned-phrase counts (before)". Lint pass never mutates the file.

3. **Rewrite pass.** Invoke the `prose-polisher` subagent with the resolved target(s), the rule list from the skill, and `max_delta_ratio`. Model routing:
   - Read `.evidraft/project.yaml` `style.humanize.model` (default: in-host LLM, i.e. the agent's own model).
   - If an external provider is configured (e.g. `anthropic:claude-sonnet-4-6`, `openai:gpt-4o-mini`), check that its env var is present (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; Ollama needs none).
   - **If the env var is missing, log a warning and fall back to the in-host model.** Never block the command on missing keys.
   - The agent emits hunks: `{original_span, rewritten_span, rules_fired[], delta_ratio}`.

4. **Hunk-level fidelity audit.** Every hunk receives a fidelity verdict before
   application, regardless of its apparent risk. The hunk-level fidelity audit
   deterministically compares the
   original and rewrite and records four category verdicts on every hunk:
   `numbers=PASS|FAIL`, `citations=PASS|FAIL`, `entities=PASS|FAIL`, and
   `hedges=PASS|FAIL`. The overall preserve verdict is PASS only when all four
   category verdicts pass. Only the external evidence-auditor invocation is adaptive:
   invoke that subagent for risky or claim-bearing hunks; use no fixed worker count,
   waves, or retry count. Diff:
   - numeric literals (digit-bearing tokens, including `81.3`, `n=128`, `p < 0.05`, `+2.4 pts`),
   - `\cite{...}` / `\citep{...}` / `\citet{...}` keys,
   - inline `ev_NNNN` markers,
   - named entities resolved from `evidence.jsonl` `type=note` rows tagged `entity` (dataset names, model names, author surnames, place names),
   - hedging adverbs on empirical statements: `may`, `suggests`, `appears to`, `tends to`, `approximately`, `up to`.
   Any drift in those protected categories means the reviewer must **reject** that
   hunk before it is written. Surface the offending tokens in chat and in the
   report. Without an evidence store, preserve source-observed named entities and
   record the unavailable store-backed entity check as a coverage gap, not a
   refusal.

5. **Write diff log + report.**
   - `.evidraft/style/humanize-<ts>.log` — unified diff format (`diff -u`), one block per hunk, with a trailing comment line `# rules: <rule-id>, <rule-id>; delta_ratio=<n>; numbers=PASS|FAIL; citations=PASS|FAIL; entities=PASS|FAIL; hedges=PASS|FAIL; preserve=ok|fail`.
   - `.evidraft/style/humanize-<ts>.report.md` — markdown with sections:
     - `# Summary` (file list, hunk counts, accept/reject counts),
     - `# Banned-phrase counts` (before / after table),
     - `# Per-hunk rule trace` (one row per hunk: file, line range, rules fired, preserve verdict),
     - `# Evidence diff` (PASS / FAIL with offending tokens if any),
     - `# Ethics` (the verbatim ethics block from the skill).
   - `<ts>` is `YYYYMMDDTHHMMSSZ` (UTC).

6. **Acceptance behavior** depending on `mode`:
   - `interactive`: present hunks one at a time; for each, show original / rewrite / rules / preserve verdict; user replies `accept` / `reject` / `skip`. Only accepted hunks land in the file.
   - `all`: apply every hunk that passes the evidence-preserve pass. Hunks that fail the preserve check are written to the log as `# rejected: preserve-fail` and not applied.
   - `none`: dry run. Write log + report; do **not** modify `target`. Useful for review-only invocations.

7. **Ethics reminder.** Print this exact line in chat after writing the report:

   ```
   EviDraft polish is a Williams-style style tool, not a detector-evasion
   tool. Your venue's AI-disclosure policy is your responsibility
   (ICML / NeurIPS / ACL / IEEE all require disclosure).
   ```

## Constraints

- Touches only the resolved `target` files and the two artefacts under `.evidraft/style/`. Never edits `.evidraft/evidence/`, `references.bib`, or `*.plan.md`.
- Preserves paragraph count within ±1 per section. Larger structural changes are out of scope; use `latex-editor` for those.
- Voice (first-person vs third-person) inherits from the source; the polisher does not flip it.
- Never introduce a new claim, citation, or number. The evidence-reviewer mode performs the stricter hunk-level comparison before acceptance.
- Refuses to remove a hedging adverb (`may`, `suggests`, `appears to`) that sits on an empirical claim. Hedges on opinion or framing may be cut.

## Done criteria

- `.evidraft/style/humanize-<ts>.log` and `.evidraft/style/humanize-<ts>.report.md` both exist and are non-empty.
- Every hunk in the log has a `# rules:` annotation, all four category verdicts,
  and a `preserve=ok|fail` verdict.
- The report ends with the verbatim ethics block.
- Chat output prints: target file(s), hunks proposed, hunks accepted, hunks blocked by preserve, log + report paths, the ethics reminder.
- Status is `complete`, `complete_with_gaps` when store-backed entity verification
  or another non-blocking audit is unavailable, or `blocked` only for ethics,
  workspace-safety, or unreadable-target failures.
