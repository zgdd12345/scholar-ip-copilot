---
id: latex-compile
title: "LaTeX compile"
kind: hook
phase: paper
triggers:
  - "write:manuscript/**/*.tex"
  - "write:submissions/*/**/*.tex"
  - "write:manuscript/preamble.tex"
  - "write:manuscript/references.bib"
behaviour: "Run latexmk on the touched manuscript root, parse errors, classify them, and surface fix suggestions."
failure_mode: warn
references:
  - doc: ../skills/latex-writing/SKILL.md
  - doc: ../skills/venue-formatting/SKILL.md
---

# latex-compile

## When it fires

Any write or edit to a `.tex` file under `manuscript/` or `submissions/<venue>/`, plus changes to `manuscript/preamble.tex` or `manuscript/references.bib`.

The hook resolves the affected manuscript root:

- `manuscript/main.tex` for edits under `manuscript/`,
- `submissions/<venue>/main.tex` for edits under `submissions/<venue>/`.

## Rules

1. Run `latexmk -pdf -interaction=nonstopmode <main.tex>` against the resolved main `.tex`. The `latex-build` skill packages this invocation plus the structured error parsing.
2. If `latexmk` is not available on PATH, mark the compile as `SKIPPED` and record it under `.evidraft/manuscript/paper_check_report.md` (or the venue-specific equivalent).
3. Parse the resulting `.log` (and `.blg`). Every error line gets classified into one of:

   - **MISSING_CITE** — log signature `LaTeX Warning: Citation '...' on page ... undefined`. Suggested fix: add the BibTeX entry via `literature-reviewer`; do not fabricate.
   - **MISSING_REF** — log signature `LaTeX Warning: Reference '...' on page ... undefined`. Suggested fix: locate the intended `\label{}` or rename the `\ref{}`.
   - **UNDEFINED_COMMAND** — log signature `Undefined control sequence`. Suggested fix: add the macro to `manuscript/preamble.tex`, or ask the author.
   - **UNBALANCED_BRACES** — log signature `Missing $ inserted` / `Extra }, or forgotten \\endgroup` / `Runaway argument?`. Suggested fix: open the file at the reported line offset.
   - **PACKAGE_NOT_FOUND** — log signature `File '....sty' not found`. Suggested fix: propose `\usepackage` removal or document the `tlmgr install ...` command for the host.
   - **OTHER** — anything else; include the raw log excerpt.

4. The hook returns a structured report:

   ```
   {
     "main_tex": "...",
     "compile": "PASS" | "FAIL" | "SKIPPED",
     "errors": [{"category": "...", "file": "...", "line": ..., "raw": "..."}],
     "warnings": [...]
   }
   ```

## Failure mode

`warn` — a failed compile does not block the write, but the report is surfaced in chat and persisted to `.evidraft/manuscript/compile_log.md`. `/scholar:paper-check` upgrades a `FAIL` compile to a top-level WARN in the audit report. `/scholar:paper-venue` upgrades it to FAIL for the submission tree (since you cannot submit something that does not build).

## Adapter notes

- **Claude Code** — register as a `PostToolUse` hook on `Write` / `Edit` for the trigger paths. The hook shells out to `latexmk` (via the `latex-build` skill recipe) and emits the structured report into chat.
- **Codex CLI** — Codex commands invoke the hook by ending the `/scholar:paper-draft`, `/scholar:paper-check`, and `/scholar:paper-venue` prompts with an explicit "Run latex-compile and include the report in chat output" instruction; the adapter inlines the rule.
- **OpenCode** — planned; will register on file-save events and call the host's terminal integration.
