---
id: citation-guard
title: "Citation guard"
kind: hook
phase: shared
triggers:
  - "write:manuscript/sections/related_work.tex"
  - "write:manuscript/sections/introduction.tex"
  - "write:manuscript/sections/abstract.tex"
  - "write:manuscript/sections/*.tex"
  - "write:manuscript/main.tex"
  - "write:.evidraft/patent/invention_disclosure.md::Advantages"
  - "write:.evidraft/patent/invention_disclosure.md::技术效果"
behaviour: "Block strong-claim verbs without a nearby citation_key or evidence_id."
failure_mode: block
references:
  - doc: ../../../docs/legal-and-ethics.md
  - doc: ../skills/evidence-check/SKILL.md
---

# citation-guard

## When it fires

Any write or edit that touches:

- a `manuscript/sections/*.tex` file (with extra weight on `related_work.tex`, `introduction.tex`, `abstract.tex`),
- `manuscript/main.tex`,
- the `Advantages / technical effects` (`技术效果 / 有益效果`) block of `.evidraft/patent/invention_disclosure.md`.

The hook scans the *changed lines only* in the proposed diff before they land on disk.

## Rules

A sentence is flagged when it contains any of the **strong-claim verbs**:

- `SOTA`, `state-of-the-art`, `state of the art`,
- `novel`, `novelty`,
- `first` (in contexts like "the first to...", "first method that..."),
- `outperform`, `outperforms`, `outperformed`,
- `significant`, `significantly` (when paired with a comparative claim),
- `superior`, `unprecedented`, `breakthrough`.

A flagged sentence passes only if **within 30 characters** of the verb there is either:

- a BibTeX cite — `\cite{key}`, `\citep{key}`, `\citet{key}` — whose `key` exists in `.evidraft/literature/references.bib`, or
- an `evidence_id` marker matching `ev_\d{4}` whose row exists in `.evidraft/evidence/evidence.jsonl`.

Both checks require the referenced record to actually exist; a dangling key is treated as no citation.

## Failure mode

`block` by default — the write is rejected and the user sees:

```
citation-guard: BLOCKED
  file: <path>
  line: <n>
  verb: <verb>
  reason: no \cite{} or ev_NNNN within 30 chars
  suggestion: add a citation or evidence id; if claim is genuinely unsupported, soften the language
```

Users can downgrade to `warn` in `.evidraft/project.yaml`:

```yaml
hooks:
  citation_guard: warn   # was: enabled (== block)
```

When downgraded, the hook records every warning in `.evidraft/manuscript/paper_check_report.md` under "Citation-guard downgraded warnings".

## Adapter notes

- **Claude Code** — register as a `PreToolUse` hook on `Write` and `Edit` for the trigger paths. Returns `block` with the message above on violation.
- **Codex CLI** — Codex does not expose a tool-level hook; the adapter inlines the rule into the relevant command prompts (especially `/scholar:paper-draft`, `/scholar:paper-review`, `/scholar:patent-disclosure`) and into `evidence-check/SKILL.md`.
- **OpenCode** — planned; the rule will register on the host's file-modification event when the adapter ships.
