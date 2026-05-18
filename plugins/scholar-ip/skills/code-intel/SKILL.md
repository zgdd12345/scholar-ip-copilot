---
id: code-intel
title: "Code intelligence: repo summary, entrypoints, method-to-code mapping, code search"
kind: skill
phase: shared
description: >
  Host-native recipe replacing code-intel-mcp. Uses Grep / Glob / Read (and
  optionally `tree-sitter` when available) to produce repo_summary.md,
  method_to_code.md rows, and trustworthy file:line citations for any claim
  about what the code does. Sister skill of codebase-audit, which owns the
  verdict assignment.
triggers:
  - "/scholar:paper-code-audit"
  - "/scholar:patent-scout"
  - "/scholar:patent-disclosure"
  - "mapping a method to code"
  - "summarising a repo"
  - "searching code by symbol"
provides:
  - repo-summary-recipe
  - entrypoint-heuristics
  - method-to-code-search-recipe
  - config-schema-extraction
  - tree-sitter-fallback
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:git*"
  - "Bash:ls*"
  - "Bash:tree-sitter*"
hooks: [evidence-consistency, sensitive-file-guard]
references:
  - doc: ../codebase-audit/SKILL.md
  - doc: ../evidence-check/SKILL.md
  - doc: ../../commands/paper-code-audit.md
  - doc: ../../commands/patent-scout.md
---

# code-intel

## When to use

Load whenever a command needs to **discover, map, or cite source code** without making a verdict (verdicts are `codebase-audit`'s job). Specifically:

- `/scholar:paper-code-audit` — refresh `repo_summary.md` and `method_to_code.md` rows; gather `file:line` citations for the audit table.
- `/scholar:patent-scout` — find non-obvious technical mechanisms and back each candidate with `file:line` evidence.
- `/scholar:patent-disclosure` "Code traceability" section — reuse `method_to_code.md`.
- Any ad-hoc "where is X implemented?" query the user asks.

This skill is the **search + summary** layer. The taxonomy of verdicts (CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE) lives in `codebase-audit`.

## Shared cache + run_id convention

This skill is read-only and writes summary artefacts under `.evidraft/code/`. It does **not** write to the retrieval cache (`.evidraft/literature/.cache/`). When called from a command with a `run_id` in `plan.yaml`, every row appended to `.evidraft/code/method_to_code.md` and every new `type=code` evidence record carries the `run_id` for traceability.

## Inputs

- repo root (cwd with `.git/`)
- `README*`, `DESIGN*`, `RFC*`, `MODEL_CARD*`, `DATASHEET*` (free-form docs)
- build / package manifests: `pyproject.toml`, `setup.py`, `package.json`, `Cargo.toml`, `go.mod`, `CMakeLists.txt`, `Makefile`
- configs (`configs/*.yaml`, `conf/*.json`, ...)
- a list of method components / candidate inventions to map (from the caller)
- `.evidraft/evidence/evidence.jsonl` (existing `type=code` rows)

## Outputs

- `.evidraft/code/repo_summary.md` (refreshed)
- new rows appended to `.evidraft/code/method_to_code.md`
- new `type=code` records appended to `.evidraft/evidence/evidence.jsonl` (`file_path` + `line_range` mandatory)

## Procedure

### 1. Repo summary recipe

Generate `.evidraft/code/repo_summary.md` (template + hygiene live in `codebase-audit` §1). The host-native execution is:

1. **File inventory**:
   ```
   git ls-files | head -200
   ```
   Capture top-level directories from the first 200 lines; for repos with > 200 files, complement with `git ls-files -- '<lang>/**' | head -50` per detected language.
2. **Language detection** by extension count:
   ```
   git ls-files | sed -E 's/.*\.//' | sort | uniq -c | sort -rn | head -10
   ```
   Map extensions to languages (`.py` Python, `.ts/.tsx` TypeScript, `.js/.jsx` JS, `.rs` Rust, `.go` Go, `.c/.cc/.cpp/.h/.hpp` C/C++, `.kt` Kotlin, `.java` Java, `.rb` Ruby).
3. **Entrypoint detection** per language — see §2 below.
4. **Config / docs / CI** sections — read top-level files via `Read`; one-line summary per file.

Top-level layout only; deep trees belong in `method_to_code.md`. Mark any section `n/a` if the repo genuinely has none.

### 2. Entrypoint heuristics

**Python**
- `[project.scripts]` in `pyproject.toml`; or `entry_points` in `setup.py` / `setup.cfg`.
- `src/<pkg>/cli.py`, `<pkg>/__main__.py` -> `python -m <pkg>`.
- Top-level `main.py`, `run.py`, `train.py`, `infer.py`, `serve.py` containing `if __name__ == "__main__":`.
- `Grep` pattern: `^if __name__ == ["']__main__["']:` across `src/` and project root.

**Node / TypeScript**
- `package.json` `"bin"` field and `"scripts"`.
- `bin/*.js`, `dist/cli.js`, `src/cli.ts` with shebang `#!/usr/bin/env node`.

**Rust**
- `[[bin]]` entries in `Cargo.toml`.
- `src/main.rs` is the default binary; `src/bin/*.rs` is one binary per file.

**Go**
- Each `cmd/<name>/main.go`.
- Any package with `package main` and `func main()`.

**Other**
- Shell scripts under `bin/` or `scripts/` with the executable bit.
- C/C++: `add_executable(...)` in `CMakeLists.txt`; `main()` in `src/main.c*`.
- Java/Kotlin: `application { mainClass = ... }` in Gradle.

Stop at the first hit per language; record `n/a` for languages present in the repo with no recognisable entrypoint.

### 3. Method-to-code mapping recipe

Given a list of method components from the caller, for each component:

1. **Pick search terms.** Extract the core technical noun(s) from the component description (e.g., "two-stage detector", "set prediction loss", "diffusion posterior sampling").
2. **Coarse grep** by extension:
   ```
   Grep -i '<core noun>' --include='*.py'        # or *.rs / *.ts / *.go / *.cpp ...
   ```
   For multi-word terms, prefer the head noun and re-rank by hits per file.
3. **Narrow to defs.** Re-grep the candidate files for the symbol-definition regex:
   - Python: `^(def|class|async def)\s+\w+`
   - TS/JS: `^(export\s+)?(async\s+)?(function|class|const|let)\s+\w+`
   - Rust: `^(pub\s+)?(fn|struct|enum|trait|impl)\s+\w+`
   - Go: `^func\s+\(?\w+\)?\s*\w+`
4. **Cite the symbol** as `file:start-end` (use the line of the `def` / `class` / `fn` opener through the closing brace or dedent). Always include both ends — single-line citations are usually evidence of an under-narrowed grep.
5. **Append a row** to `.evidraft/code/method_to_code.md` (table format owned by `codebase-audit` §4).
6. **Create a `type=code` evidence record** in `evidence.jsonl` per row, with `file_path` and `line_range` populated; never elide either field.

### 4. Code search defaults

Default search stack:

1. `Glob` to find candidate files by name pattern (`**/*.py`, `**/<term>*.rs`).
2. `Grep` for the textual symbol or core noun.
3. `Read` the matching files to verify before citing.

`Grep` flag conventions for this skill:

- case-insensitive (`-i`) for the first pass;
- `--include='*.<ext>'` to narrow by language;
- `-n` so the result already carries line numbers;
- `-B 1 -A 5` to capture a definition's neighbourhood for the second pass.

### 5. tree-sitter fallback (optional)

If `tree-sitter` is on `$PATH` **and** the project has a parser available for the target language, prefer it for semantic node matching (catches indirection that text search misses, e.g. `class FasterRCNN` defined in a string template).

Invocation pattern (Bash):

```
tree-sitter query -- <(printf '(class_definition name: (identifier) @class.name)\n') src/**/*.py
```

When to reach for `tree-sitter`:

- the textual `Grep` returns > 50 hits and you cannot narrow them by definition regex;
- the target language has user-defined indentation rules that `Grep` mis-parses (Python decorators wrapping a class, Rust macro expansions);
- the user explicitly asks "is this symbol *defined* anywhere, or only referenced?".

When `tree-sitter` is missing, fall back to `Grep`'s definition-regex narrowing (§3 step 3). Never claim a symbol exists without the textual citation.

### 6. Config schema extraction

For every language manifest found in §1, read and summarise:

- Python: `pyproject.toml` (`[project]`, `[tool.<X>]`, `[project.scripts]`, `[project.optional-dependencies]`).
- Node: `package.json` (`name`, `version`, `bin`, `scripts`, `dependencies`, `devDependencies`).
- Rust: `Cargo.toml` (`[package]`, `[dependencies]`, `[[bin]]`, `[features]`).
- Go: `go.mod` (`module`, `go`, `require`).
- Any `configs/*.yaml`, `conf/*.json`, `hydra/conf/*.yaml` — list keys, not values; values often contain secrets.

Write the extracted keys (not values) into the `## Configs` section of `repo_summary.md`.

## Sensitive-path discipline

The `sensitive-file-guard` hook blocks reads of `.env*`, `secrets/`, `**/*.pem`, `**/*.key`, `credentials.json`. This skill **never** attempts to override the guard. If a config under `configs/` references a secret path, record only the path, never the loaded content.

## Quality checklist

- [ ] `repo_summary.md` under ~200 lines, every command copy-pasteable.
- [ ] Entrypoints found via the language-specific heuristic, not guessed.
- [ ] Every `method_to_code.md` row has both `file_path` and a non-empty line range.
- [ ] Every claim about a symbol is cited as `file:start-end` (no bare file paths).
- [ ] `tree-sitter` used only when `Grep` is genuinely under-narrowed.
- [ ] No file matched by `sensitive-file-guard` was opened.

## Anti-patterns

- Claiming a symbol exists without a `file:start-end` citation.
- Listing an entire file as evidence (no line range) — that defeats the audit.
- Inferring an entrypoint from the README rather than from the manifest.
- Editing source code "to make it match the method description" — this skill is read-only.
- Running `tree-sitter` against a language without a parser installed (silent zero hits).
- Reading `.env` / `secrets/` / `*.pem` / `*.key` — `sensitive-file-guard` blocks; do not attempt to override.
- Flattening a monorepo's many entrypoints into one row (re-run §2 per workspace).
