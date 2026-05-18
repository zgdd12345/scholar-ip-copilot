---
id: latex-build
title: "LaTeX build: latexmk invocation, structured error parsing, PDF preview"
kind: skill
phase: paper
description: >
  Host-native recipe replacing latex-build-mcp. Wraps `latexmk` via Bash,
  parses main.log into the same error taxonomy the latex-compile hook
  consumes (MISSING_CITE, MISSING_REF, UNDEFINED_COMMAND, UNBALANCED_BRACES,
  PACKAGE_NOT_FOUND, OTHER), writes a structured errors.json beside the
  log, and optionally renders a first-page PNG preview.
triggers:
  - "/scholar:paper-check"
  - "/scholar:paper-venue"
  - "compiling manuscript"
  - "compiling submissions/<venue>/main.tex"
  - "parsing latex log"
provides:
  - latexmk-invocation
  - latex-error-taxonomy
  - latex-error-regex
  - pdf-preview-recipe
  - structured-compile-report
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:latexmk*"
  - "Bash:pdftoppm*"
  - "Bash:convert*"
  - "Bash:ls*"
hooks: [latex-compile, citation-guard, evidence-consistency]
references:
  - doc: ../latex-writing/SKILL.md
  - doc: ../venue-formatting/SKILL.md
  - doc: ../../hooks/latex-compile.md
  - doc: ../../commands/paper-check.md
  - doc: ../../commands/paper-venue.md
---

# latex-build

## When to use

Load whenever a command needs to **compile a manuscript** (or submission copy) and produce a structured error report:

- `/scholar:paper-check` — compile + classify errors for the audit report.
- `/scholar:paper-venue` — compile sanity-check after the preamble rewrite.
- The `latex-compile` hook fires this same recipe under the hood when a `.tex` write triggers it.

## Shared cache + run_id convention

Compile artefacts and parsed error tables live under `.evidraft/manuscript/`:

- `.evidraft/manuscript/compile-<ts>.log` — copy of the raw `main.log`
- `.evidraft/manuscript/compile-<ts>.errors.json` — structured taxonomy rows
- `.evidraft/manuscript/compile-<ts>.pdf` (optional) — copy of `main.pdf`
- `.evidraft/manuscript/compile-<ts>.png` (optional) — first-page preview

`<ts>` is UTC iso-basic (`20260518T143000Z`). When called from a command with a `run_id` in its `plan.yaml`, record the `run_id` inside `compile-<ts>.errors.json` as the top-level `run_id` field. Web-retrieval cache (`.evidraft/literature/.cache/`) is **not** touched by this skill.

## Inputs

- `manuscript/main.tex` or `submissions/<venue>/main.tex` (the `<main.tex>` argument)
- the LaTeX sources it `\input`s
- any `.bib` referenced by `\bibliography{...}` / `\addbibresource{...}`

## Outputs

- the compile artefact bundle under `.evidraft/manuscript/` (above)
- a structured report returned to the caller:

  ```json
  {
    "main_tex": "manuscript/main.tex",
    "compile": "PASS" | "FAIL" | "SKIPPED",
    "errors": [
      {"category": "MISSING_CITE", "file": "sections/method.tex", "line": 42,
       "raw": "LaTeX Warning: Citation 'foo2020bar' on page 3 undefined ...",
       "fix": "add bib entry 'foo2020bar' via scholar-search + literature-review"}
    ],
    "warnings": [...],
    "pdf_path": ".evidraft/manuscript/compile-<ts>.pdf",
    "preview_png": null,
    "run_id": "..."
  }
  ```

## Procedure

### 1. Compile invocation

Run from the directory containing `<main.tex>`:

```
latexmk -pdf -interaction=nonstopmode -file-line-error <main.tex>
```

Flags:

- `-pdf` — pdflatex (override with `-xelatex` / `-lualatex` only if the venue spec mandates).
- `-interaction=nonstopmode` — never block on an interactive prompt.
- `-file-line-error` — emit `file:line: <msg>` so the regex parser can extract source locations.

For `/scholar:paper-venue`, the working directory is `submissions/<venue>/`; for everything else, `<project root>/manuscript/`.

If `latexmk` is **not** on `$PATH`, mark `compile: "SKIPPED"`, surface the reason in chat, and continue — never invent a PASS verdict.

### 2. Log file location

After `latexmk` returns, read the log from `<dirname(main.tex)>/main.log`:

- `manuscript/main.log` for the canonical manuscript
- `submissions/<venue>/main.log` for the venue copy

Copy the file to `.evidraft/manuscript/compile-<ts>.log` for the audit trail. **Do not move it** — `latexmk` re-uses it on the next run.

### 3. Structured error taxonomy

Walk the log line-by-line. Classify each error / warning into one of six categories (mirrors the `latex-compile` hook). For each: a **regex pattern**, a **file:line extraction rule**, and a **fix-suggestion template**.

| Category | Regex (Python-style) | file:line extraction | Fix-suggestion template |
|---|---|---|---|
| `MISSING_CITE` | `LaTeX Warning: Citation [`']([^`']+)[`'] on page (\d+) undefined` | from the preceding `(./<file>.tex)` block; line via `-file-line-error` echo if present | "add bib entry `<key>` via scholar-search + literature-review; never fabricate" |
| `MISSING_REF` | `LaTeX Warning: Reference [`']([^`']+)[`'] on page (\d+) undefined` | same | "locate the intended `\label{<ref>}` or rename the `\ref{}`" |
| `UNDEFINED_COMMAND` | `! Undefined control sequence\.` followed by `l\.(\d+) (.*)` | `l.<line>` from the follow-up line; file from the most recent `(./<file>.tex)` block | "define the macro in `manuscript/preamble.tex`, or check spelling" |
| `UNBALANCED_BRACES` | `! Missing \$ inserted\.`  OR  `! Extra \}, or forgotten \\endgroup\.`  OR  `Runaway argument\?` | file:line from `-file-line-error` or `l.<line>` | "open `<file>` at line `<line>` and balance braces / math delimiters" |
| `PACKAGE_NOT_FOUND` | `! LaTeX Error: File [`']([^`']+\.sty)[`'] not found\.` | preamble | "`tlmgr install <pkg>` (or `apt install texlive-<...>`); or remove the `\usepackage` line" |
| `OTHER` | anything starting with `! ` not matched above | best-effort `l.<line>` | "include raw log excerpt in chat; ask the user" |

Notes:

- The `-file-line-error` flag yields lines of the form `./sections/method.tex:42: ! Undefined control sequence.`; parse those first; fall back to the `l.<line>` echo line.
- Multi-line errors (TeX prints up to 3 lines of context) are coalesced into one `raw` field.
- Warnings get the same taxonomy but are emitted on the `warnings` list, not `errors`.

### 4. Emit the structured report

Write `.evidraft/manuscript/compile-<ts>.errors.json`:

```json
{
  "main_tex": "manuscript/main.tex",
  "compile": "PASS|FAIL|SKIPPED",
  "run_id": "...",
  "errors": [
    {"category": "MISSING_CITE", "file": "sections/method.tex", "line": 42,
     "raw": "...", "fix": "..."}
  ],
  "warnings": [...]
}
```

`compile: "PASS"` iff `latexmk` exit code is 0 **and** no `! ` lines remain in the log. Any unresolved `\ref` / `\cite` warning downgrades to `FAIL` for `/scholar:paper-venue` (the venue copy must build cleanly to submit) but only to `WARN` for `/scholar:paper-check` (the working manuscript can still have open ends).

### 5. PDF preview (optional)

Only run when the caller asks (`preview=true`) or the user explicitly requests "show me the PDF". Two options, in preference order:

```
pdftoppm -r 120 -f 1 -l 1 -png <pdf> .evidraft/manuscript/compile-<ts>
```

or, if `pdftoppm` is missing but ImageMagick is on `$PATH`:

```
convert -density 120 <pdf>[0] .evidraft/manuscript/compile-<ts>.png
```

If neither tool is present, set `preview_png: null` and surface a one-line note.

### 6. Surface to chat

Print to chat (the same lines the `latex-compile` hook prints):

```
LaTeX compile (<main.tex>): PASS|FAIL|SKIPPED
  errors:   <n>  (MISSING_CITE:<a> MISSING_REF:<b> UNDEFINED_COMMAND:<c> ...)
  warnings: <n>
  log:      .evidraft/manuscript/compile-<ts>.log
  errors:   .evidraft/manuscript/compile-<ts>.errors.json
```

## Quality checklist

- [ ] Used `-file-line-error` so source locations are extractable.
- [ ] Every error row carries a category from the six-entry taxonomy.
- [ ] `.errors.json` written even when `compile: "PASS"` (empty `errors` / `warnings` arrays).
- [ ] Raw log preserved under `.evidraft/manuscript/compile-<ts>.log`.
- [ ] Never edited a `.tex` file as part of "fixing" an error.

## Anti-patterns

- Editing `.tex` automatically to silence an error — the skill is **observational**. Surface errors; let the user (or `latex-editor` subagent) decide.
- Marking `compile: "PASS"` because `latexmk` exited 0 but the log still contains `LaTeX Warning: Citation 'x' undefined`. Always re-scan the log.
- Running `latexmk -bibtex-cond` flags silently to mask missing references.
- Skipping the `.errors.json` write because the compile passed — the empty file is part of the audit trail.
- Calling `pdftoppm` / `convert` on every run; PDF preview is opt-in (rendering is slow).
- Treating `! Emergency stop` as a generic error; classify it under `PACKAGE_NOT_FOUND` (it usually fires when the preceding `\usepackage` failed).
