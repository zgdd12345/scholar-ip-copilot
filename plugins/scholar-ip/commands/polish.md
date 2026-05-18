---
id: polish
title: "Williams-style prose polish: reduce AI-flavour, preserve evidence, ship diff log"
kind: command
slash: /scholar:polish
phase: paper
description: >
  Rewrite manuscript prose with a Williams/Pinker/Strunk-conditioned editor:
  cut hedge-padding, vary sentence length, drop AI-tell n-grams. Preserves
  numbers, citation keys, named entities, and empirical hedging adverbs
  verbatim. Ships a unified-diff log and a plain-English change report.
  Not a detector-evasion tool; refuses if framed as one.
inputs:
  - name: target
    type: path
    description: "File or directory to polish (e.g. manuscript/sections/introduction.tex or manuscript/sections/)."
  - name: section
    type: string
    optional: true
    description: "Narrow the polish to a single LaTeX section, matched by \\section{...} title."
  - name: mode
    type: enum
    values: [interactive, all, none]
    optional: true
    default: interactive
    description: "interactive = per-hunk accept/reject; all = apply every hunk that passes evidence-preserve; none = dry run (log + report only, no in-place edit)."
  - name: max_delta_ratio
    type: number
    optional: true
    default: 0.35
    description: "Hard ceiling on (changed-tokens / total-tokens) per hunk. Above this, the hunk is rejected as too aggressive."
outputs:
  - path: <target>
    description: "Rewritten target file in place (only in mode=interactive after acceptance, or mode=all)."
  - path: .evidraft/style/humanize-<ts>.log
    description: "Unified diff between original and rewrite, annotated per-hunk with the rule(s) that fired."
  - path: .evidraft/style/humanize-<ts>.report.md
    description: "Plain-English change report: banned-phrase counts before/after, evidence-diff verdict, ethics statement."
retention:
  keep_last: 30
  max_age_days: 90
  policy: "At command start, prune humanize-* pairs older than max_age_days OR beyond keep_last entries (whichever cuts more)."
allowed_tools: [Read, Write, Edit, Glob, Grep]
hooks: [scope-required, citation-guard, evidence-consistency, humanize-evidence-preserve]
subagents: [prose-polisher, evidence-auditor]
references:
  - doc: ../skills/humanize/SKILL.md
  - doc: ../agents/prose-polisher.md
  - doc: ../hooks/humanize-evidence-preserve.md
  - doc: ../../../docs/legal-and-ethics.md
---

# /scholar:polish

Williams-style prose polish for a draft that has already passed `/scholar:paper-check`. Reduces AI-flavour without changing meaning, preserves every claim-bearing token, and always ships a diff log so a human can review what changed and why.

This is **not** a detector-evasion tool. The skill defines the full refusal-flag list and regex in `skills/humanize/SKILL.md` §3 — invocation is rejected on any match.

## Steps

1. **Pre-flight.**
   - Refuse if the invocation matches any refusal flag / regex from `skills/humanize/SKILL.md` §3. Print the ethics block (from the skill) and exit non-zero.
   - Refuse if `.evidraft/evidence/evidence.jsonl` does not exist or is empty — no evidence to protect means no draft worth polishing; route the user back to `/scholar:paper-lit` and `/scholar:paper-draft`.
   - Refuse if `target` resolves to a path under `.evidraft/`. We polish manuscripts (`manuscript/...`), not the evidence store.
   - Refuse if `scope-required` is unsatisfied (Phase 2 projects that require an `approved` scope file).
   - Resolve `target`: if a directory, glob `*.tex` / `*.md` non-recursively; if a file, use it directly. If `section` is set, slice to the `\section{<section>}` block (inclusive of its `\subsection{}`s, exclusive of the next `\section{}`).

2. **Lint pass.** Before rewriting, scan the resolved target(s) for banned phrases and AI-tells (the list lives in `skills/humanize/SKILL.md`). Report counts per phrase to chat and into the report under "Banned-phrase counts (before)". Lint pass never mutates the file.

3. **Rewrite pass.** Invoke the `prose-polisher` subagent with the resolved target(s), the rule list from the skill, and `max_delta_ratio`. Model routing:
   - Read `.evidraft/project.yaml` `style.humanize.model` (default: in-host LLM, i.e. the agent's own model).
   - If an external provider is configured (e.g. `anthropic:claude-sonnet-4-6`, `openai:gpt-4o-mini`), check that its env var is present (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; Ollama needs none).
   - **If the env var is missing, log a warning and fall back to the in-host model.** Never block the command on missing keys.
   - The agent emits hunks: `{original_span, rewritten_span, rules_fired[], delta_ratio}`.

4. **Evidence-preserve pass.** Invoke the `evidence-auditor` subagent on each hunk to diff:
   - numeric literals (digit-bearing tokens, including `81.3`, `n=128`, `p < 0.05`, `+2.4 pts`),
   - `\cite{...}` / `\citep{...}` / `\citet{...}` keys,
   - inline `ev_NNNN` markers,
   - named entities resolved from `evidence.jsonl` `type=note` rows tagged `entity` (dataset names, model names, author surnames, place names),
   - hedging adverbs on empirical statements: `may`, `suggests`, `appears to`, `tends to`, `approximately`, `up to`.
   Any drift on any of those four categories → the `humanize-evidence-preserve` hook fires and **blocks** that hunk. Surface the offending tokens in chat and in the report.

5. **Write diff log + report.**
   - `.evidraft/style/humanize-<ts>.log` — unified diff format (`diff -u`), one block per hunk, with a trailing comment line `# rules: <rule-id>, <rule-id>; delta_ratio=<n>; preserve=ok|fail`.
   - `.evidraft/style/humanize-<ts>.report.md` — markdown with sections:
     - `# Summary` (file list, hunk counts, accept/reject counts),
     - `# Banned-phrase counts` (before / after table),
     - `# Per-hunk rule trace` (one row per hunk: file, line range, rules fired, preserve verdict),
     - `# Evidence diff` (PASS / FAIL with offending tokens if any),
     - `# Ethics` (the verbatim ethics block from the skill).
   - `<ts>` is `YYYYMMDDTHHMMSSZ` (UTC).

6. **Acceptance UI** depending on `mode`:
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
- Never introduces a new claim, a new citation, or a new number. The `evidence-consistency` hook will block on attempt; `humanize-evidence-preserve` is a stricter, hunk-level check on top.
- Refuses to remove a hedging adverb (`may`, `suggests`, `appears to`) that sits on an empirical claim. Hedges on opinion or framing may be cut.

## Done criteria

- `.evidraft/style/humanize-<ts>.log` and `.evidraft/style/humanize-<ts>.report.md` both exist and are non-empty.
- Every hunk in the log has a `# rules:` annotation and a `preserve=ok|fail` verdict.
- The report ends with the verbatim ethics block.
- Chat output prints: target file(s), hunks proposed, hunks accepted, hunks blocked by preserve, log + report paths, the ethics reminder.
