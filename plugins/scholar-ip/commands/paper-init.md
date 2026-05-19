---
id: paper-init
title: "Initialize an EviDraft paper project"
description: >
  Scaffold an EviDraft paper project in the current working directory:
  write `.evidraft/project.yaml`, create empty `evidence.jsonl` and
  `references.bib`, and a `manuscript/` skeleton in neutral arXiv style.
  Existing files are never moved or rewritten. Use at the start of a new
  paper project, or when adopting EviDraft on an existing code repository.
kind: command
slash: /scholar:paper-init
phase: paper
inputs:
  - name: project_type
    type: enum
    values: [paper, patent, mixed]
    optional: true
    default: paper
  - name: title
    type: string
    optional: true
  - name: field
    type: string
    optional: true
  - name: target_venue
    type: string
    optional: true
outputs:
  - path: .evidraft/project.yaml
  - path: .evidraft/evidence/evidence.jsonl
  - path: .evidraft/literature/references.bib
  - path: manuscript/main.tex
  - path: manuscript/sections/
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:git*", "Bash:ls*", "Bash:cat*"]
forbidden_tools: ["Bash:rm -rf*"]
hooks: [sensitive-file-guard]
references:
  - doc: ../../../docs/data-model.md
  - doc: ../templates/paper-project/
---

# /scholar:paper-init

Scaffold an EviDraft paper project in the **current working directory**. Treat the cwd as the user's project (which may already contain code and experiments). Do not move or rewrite existing files; only create new EviDraft artefacts.

## Steps

1. **Inspect.** Use `ls`, `git ls-files`, and `Glob` to see what the project already contains. Note:
   - whether `manuscript/`, `paper/`, or `latex/` already exists,
   - whether `experiments/`, `results/`, or `data/` exist,
   - whether `.evidraft/` already exists (if so, ask the user before overwriting),
   - top-level language / framework (`pyproject.toml`, `package.json`, etc.).
2. **Infer or ask** for: `project_type`, `title`, `field`, `target_venue`. Prefer asking concise questions over guessing; default to `project_type=paper` if the user is non-committal.
3. **Materialise the template.** Copy `plugins/scholar-ip/templates/paper-project/` into the project root, **without overwriting** any existing file. Specifically create:
   - `.evidraft/project.yaml`
   - `.evidraft/evidence/evidence.jsonl` (empty file)
   - `.evidraft/literature/references.bib` (empty `% BibTeX entries go here`)
   - `.evidraft/literature/matrix.md`
   - `.evidraft/ideas/novelty_matrix.md`
   - `.evidraft/code/method_to_code.md`
   - `manuscript/main.tex`
   - `manuscript/sections/{introduction,related_work,method,experiments,conclusion}.tex`
   - a symlink (or fallback copy on Windows) `manuscript/references.bib → ../.evidraft/literature/references.bib`
4. **Fill the project.yaml** with the values you collected. Validate against `packages/core/schemas/project.schema.json` (logically — schema lookup may be by path, not network).
5. **If the repo has code**, run a *fast* repo summary into `.evidraft/code/repo_summary.md`:
   - language(s), entry points, top-level modules, configs, test command if obvious.
   - mark unknowns as `TODO` — do not guess.
6. **Print a short next-steps block** in chat:
   ```
   Next:
     /scholar:paper-lit         start literature work
     /scholar:paper-code-audit  map your code to the planned method
     /scholar:paper-experiment  analyse experiment outputs (if any)
   ```

## Constraints

- Do **not** invent author names, affiliations, or venues.
- Do **not** delete or rewrite the user's existing manuscript files; create alongside.
- Respect `hooks/sensitive-file-guard.md`: skip `.env`, `secrets/`, etc.
- If `.evidraft/` already exists, summarise its current contents and ask before any write.

## Done criteria

- `.evidraft/project.yaml` exists and validates.
- `manuscript/main.tex` exists with a working `\documentclass` skeleton.
- Chat output ends with the "Next" block.
