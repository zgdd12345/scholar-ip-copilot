---
id: codebase-audit
title: "Codebase audit: repo summary, method-to-code map, verdict assignment"
kind: skill
phase: shared
description: >
  Load when /scholar:paper-code-audit or /scholar:patent-scout runs, or whenever a claim about
  what the code does must be traced to file_path + line range. Provides the
  repo-summary template, the method-to-code table recipe, audit-verdict
  definitions (CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE),
  language-specific entrypoint heuristics, and monorepo handling.
triggers:
  - "/scholar:paper-code-audit"
  - "/scholar:patent-scout"
  - "writing method_to_code.md"
  - "auditing paper claim against code"
  - "drafting code traceability section of TID"
provides:
  - repo-summary-template
  - method-to-code-recipe
  - audit-verdict-definitions
  - entrypoint-heuristics
  - monorepo-handling
allowed_tools: [Read, Glob, Grep, "Bash:git*", "Bash:ls*"]
hooks: [evidence-consistency, sensitive-file-guard]
references:
  - doc: ../evidence-check/SKILL.md
  - doc: ../code-intel/SKILL.md
  - doc: ../../../../docs/data-model.md
---

# codebase-audit

## When to use

Pull this skill whenever a downstream artefact needs a trustworthy mapping from a method description to actual source code. Specifically:

- `/scholar:paper-code-audit` builds `repo_summary.md`, `method_to_code.md`, and `paper_code_audit.md`.
- `/scholar:patent-scout` needs code evidence for each candidate.
- `/scholar:patent-disclosure` "Code traceability" section reuses `method_to_code.md`.

Use `Glob` / `Grep` / `Read` to walk the repo. The sibling `code-intel` skill packages the repo-summary, entrypoint-finding, config-schema-extraction, method-to-code-mapping, and code-search recipes into deterministic procedures — call it for any non-trivial lookup.

## Inputs

- repo root (cwd, with `.git/`)
- `README*`, `DESIGN*`, `RFC*`, `MODEL_CARD*`, `DATASHEET*`
- build / package manifests: `pyproject.toml`, `setup.py`, `package.json`, `Cargo.toml`, `go.mod`, `CMakeLists.txt`, `Makefile`
- configs (`configs/*.yaml`, `conf/*.json`, …)
- `.evidraft/evidence/evidence.jsonl` (read existing `type=code` records)

## Outputs

- `.evidraft/code/repo_summary.md`
- `.evidraft/code/method_to_code.md`
- `.evidraft/code/paper_code_audit.md`
- new `type=code` records appended to `evidence.jsonl`

## Procedure

### 1. Repo-summary template

Write `.evidraft/code/repo_summary.md` with these H2 sections, in order. Keep the whole file under ~200 lines.

```
# Repo summary

## Languages
- <lang>: <approx % or LOC>, <build tool>

## Layout (top level only)
- <dir>/ : <one line>
- ...

## Entry points
- <kind>: <command or file:function>
- ...

## Build / run
- install: <command>
- run: <command>
- test: <command>

## Configs
- <path>: <one-line purpose>

## Docs of record
- README*, MODEL_CARD*, DATASHEET*, DESIGN*

## CI
- <workflow file>: <triggers, what it runs>

## Notes / risks
- ...
```

Rules:

- Top-level layout only. Do not flatten a deep tree into this file; that goes in `method_to_code.md`.
- Every command in "Build / run" must be copy-pasteable from a fresh clone.
- Mark a section `n/a` if the repo genuinely has none — never invent one.

### 2. Entrypoint heuristics by language

Use these in order; stop at the first hit.

**Python**
1. `[project.scripts]` table in `pyproject.toml` (or `entry_points` in `setup.py/setup.cfg`) -> each entry is an entrypoint (`<command> = <module>:<function>`).
2. `src/<pkg>/cli.py`, `<pkg>/__main__.py`, or any `__main__.py` under the top-level package -> entrypoint via `python -m <pkg>`.
3. Top-level `main.py`, `run.py`, `train.py`, `infer.py`, `serve.py` containing `if __name__ == "__main__":`.
4. Grep `if __name__ == "__main__":` across `src/` and report each hit; pick the ones that parse argv or call into a recognised framework (`argparse`, `click`, `typer`, `hydra`).
5. If none: report `n/a` and look for library-only usage in README.

**Node / TypeScript**
1. `package.json` `"bin"` field -> each key is a CLI entry; the value is the script path.
2. `package.json` `"scripts"` -> `npm run <name>` entries; mark as task runner, not necessarily product entrypoints.
3. `bin/*.js`, `dist/cli.js`, `src/cli.ts` containing a shebang `#!/usr/bin/env node` or calling `program.parse()` (commander) / `yargs`.
4. For servers: `index.js` / `server.ts` exporting an HTTP handler or calling `app.listen(...)`.

**Rust**
1. `[[bin]]` entries in `Cargo.toml` (each gives a binary name and path).
2. `src/main.rs` -> the default binary (named after the crate).
3. `src/bin/*.rs` -> one binary per file.
4. Library-only crates (`src/lib.rs` only) have no entrypoint; record that.

**Go**
1. Each directory under `cmd/` is a binary (`cmd/<name>/main.go`).
2. Any package with `package main` and a `main()` function elsewhere.
3. `go.mod` `module` line tells you the import root.

**Other**
- Shell: scripts under `bin/`, `scripts/`, with executable bit.
- C/C++: `add_executable(...)` in `CMakeLists.txt`; `main()` in `src/main.c*`.
- Java/Kotlin: `application { mainClass = ... }` in Gradle; `Main-Class` in `MANIFEST.MF`.

### 3. Monorepo handling

If you find one of:

- `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json` (JS)
- `[workspace]` table in root `Cargo.toml` (Rust)
- top-level dir of `pyproject.toml` files (Python with `uv` / `rye` workspaces)
- `go.work` (Go)
- Bazel `WORKSPACE` / `MODULE.bazel`

then:

1. Treat each package / workspace as a sub-repo. Add a "Workspaces" subsection under "Layout" listing them.
2. Run the entrypoint heuristic **per workspace**.
3. In `method_to_code.md`, prefix `Source files` with the workspace name (`packages/core/src/foo.py`).
4. Do not collapse method components across workspaces unless the method genuinely spans them.

### 4. Method-to-code recipe

Write `.evidraft/code/method_to_code.md` as one table:

```
| Method component | Source files | Entry points | Configs | Key functions/classes | Evidence | Gaps |
```

Rules:

- One row per planned section/sub-section of the paper's Method. Granularity: roughly equation-level or module-level, not file-level.
- `Source files` lists paths with line ranges in parens where helpful: `src/models/head.py (118-204)`.
- `Entry points` references the repo_summary's entry points by name; a method component without any reachable entry point gets `unreachable` and is flagged in "Gaps".
- `Configs` lists config keys (not values) the component reads: `model.head.use_centerness`.
- `Key functions/classes` names the symbols a reader should grep for.
- `Evidence` lists ≥ 1 `ev_NNNN` of `type=code` whose `file_path:line_range` overlaps the row's Source files. If no record exists, create one via `evidence-check` rules and link it here.
- `Gaps`: what the paper plans to claim but the code does not (yet) implement. Empty cell means "no gap".

### 5. Audit-verdict definitions and assignment

Each row in `.evidraft/code/paper_code_audit.md` carries exactly one Verdict:

| Verdict | Definition | Required evidence |
|---|---|---|
| `CONFIRMED` | Code at the cited `file_path:line_range` implements the claim as stated. | `ev_NNNN` of `type=code` with file_path + line_range; reviewer's read of the code agrees with the claim. |
| `PARTIAL` | Code implements part of the claim. E.g., the feature exists but the ablation switch the paper promises does not, or a hyperparameter is hard-coded instead of configurable. | code evidence with a note in "Notes" describing the missing part. |
| `MISSING` | No code implements the claim. The claim is a plan, not a fact. | none; the row is the bug report. |
| `MISMATCH` | Code contradicts the claim (paper says β=0.5; code default is β=0.9). | code evidence pointing at the contradicting value. |
| `NOT_AUDITABLE` | The claim is empirical (`our method achieves X mAP`) or theoretical (`our loss is convex`) and cannot be verified from code alone. | reference to the matching `type=experiment` evidence or a math sketch in `support`. |

Assignment rules:

- A `CONFIRMED` row **must** have both `file_path` and a non-empty line range; otherwise downgrade to `PARTIAL`.
- A `MISMATCH` is more severe than `MISSING` and supersedes it.
- `NOT_AUDITABLE` is reserved for genuinely non-code claims. "I couldn't find it" is `MISSING`, not `NOT_AUDITABLE`.
- A claim that needs an experiment to verify gets `NOT_AUDITABLE` here and a `type=experiment` evidence record in the experiments analysis.

End the file with a counts line: `n CONFIRMED, n PARTIAL, n MISSING, n MISMATCH, n NOT_AUDITABLE`.

## Quality checklist

- [ ] `repo_summary.md` is < ~200 lines and every command is copy-pasteable.
- [ ] Entrypoints found via the language-specific heuristic, not guessed.
- [ ] Every method-to-code row has ≥ 1 evidence id of `type=code`.
- [ ] Every `CONFIRMED` row has both `file_path` and line range.
- [ ] Monorepo workspaces have one entrypoint scan each.
- [ ] No source files modified.
- [ ] `sensitive-file-guard` paths (`.env`, `secrets/`, `*.pem`, `*.key`) never opened.

## Anti-patterns

- Recording a `CONFIRMED` verdict from reading a docstring or comment instead of the implementation.
- Listing entire files (no line range) as evidence — that defeats the audit.
- Inflating verdicts. If the ablation switch is missing, the row is `PARTIAL` even if the rest is fine.
- Using `NOT_AUDITABLE` to dodge a `MISSING` verdict.
- Flattening a monorepo's many entrypoints into a single "training script" row.
- Editing source code "to make it match the paper" — this skill is read-only.
- Treating `repo_summary.md` as documentation for the project. It is an audit artefact: terse, factual, current.
