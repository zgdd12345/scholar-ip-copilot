# Authoring a new skill

Hands-on walkthrough for adding a skill to `plugins/scholar-ip/skills/`. Reference docs: [`plugin-format.md`](plugin-format.md) for the data shape, [`architecture.md`](architecture.md) §2 for the layered design, [`optimization-status.md`](optimization-status.md) for the C-list split rule-of-thumb that this guide codifies.

## When to add a skill

A skill is a **reusable how-to** that one or more commands / agents pull in. Add one when a procedure, rule set, or schema is referenced from ≥ 2 places, or when it has clear standalone semantics (e.g. `scholar-search` retrieves papers regardless of which command asked).

Don't add a skill if the content is a one-off paragraph in a single command — keep it in the command body.

## Step 1 — Create the bundle

```
plugins/scholar-ip/skills/<id>/
  SKILL.md            # entry — frontmatter + load-before-every-call rules + navigation
  references/         # optional, on-demand spec / taxonomy / procedure (see Step 3)
  assets/             # optional, templates / fixtures
  scripts/            # optional, executable helpers
```

`<id>` is the skill id and the directory name — lowercase kebab-case. Loader is one-skill-per-directory (`packages/adapters/_shared/loader.py:_load_skill_dir`); files under `references/` are **never** misread as separate skills.

## Step 2 — Write SKILL.md (the thin entry)

Frontmatter (full spec in [`plugin-format.md`](plugin-format.md) §Per-skill folder):

```yaml
---
id: my-skill
title: "One-line marketing-style summary"
kind: skill
phase: paper          # or: patent | shared
description: >        # ≥ 1 paragraph; this is what the agent matches against
  ...
triggers:             # selector strings the orchestrator dispatches on
  - "/scholar:my-command"
  - "auditing X"
provides: [thing-a, thing-b]
allowed_tools: [Read, Glob, Grep, Write]
hooks: [citation-guard]
references:           # YAML metadata pointers — NOT markdown links
  - doc: ../other-skill/SKILL.md
  - doc: references/procedure.md
  - url: "https://..."
---
```

Body sections (in this order):

1. **`## When to use`** — one paragraph; the load-before-every-call decision rule (e.g. "skip if `compile == FAIL`").
2. **`## Inputs`** / **`## Outputs`** — file paths, JSON schemas (or pointers to references).
3. **`## How to navigate this skill`** — a table mapping concern → reference file. Each row is a markdown link `[name](references/X.md)`.
4. **`## Quality checklist`** — load-before-every-call assertions the agent must satisfy.

**Target**: ~80–120 lines. If a body section blows past 30–50 lines, split it to `references/<topic>.md` and replace it with a one-line pointer in the navigation table.

## Step 3 — Decide on references/

The **rule of thumb** (twelve splits, lower bound `xref-audit` 232L→88L confirmed): **≥ 232 lines is split-worth**; 220–231 is a judgement call (depends on whether the file has clean group structure to extract); ≤ 220 is fine as a single file under Anthropic's recommended 300-line bound.

When you split, the patterns that have landed cleanly:

| Pattern | Examples | Typical references |
|---|---|---|
| Rule-table heavy | `latex-style-audit`, `xref-audit` | `rule-taxonomy.md` + `output-schemas.md` + `procedure.md` + `anti-patterns.md` |
| Multi-provider retrieval | `scholar-search`, `patent-search` | `provider-matrix.md` + `procedure.md` + `anti-patterns.md` |
| Multi-step procedure | `claim-chart-builder` (7 refs), `deep-literature-review` (12 refs — one per stage + cross-cutting) | per-step / per-stage references + schemas + anti-patterns |
| Templated artefact | `brainstorming` | `question-schemas` + `verdict-matrix` + `scope-file-template` + `staleness-rule` + per-technique references |

Cross-skill links: at SKILL.md level write `(../other-skill/SKILL.md)` (works on all 3 hosts); at command-body level the Codex adapter rewrites `](../skills/<X>/` to `](../scholar-skill-<X>/` automatically. **Do not** put cross-skill markdown links inside `references/*.md` files — keep them at SKILL.md level so Codex's prefix logic stays consistent.

## Step 4 — Register with the conformance suite

```
tests/fixtures/adapter_invariants/expected_counts.json
```

Bump `skills` by 1. The conformance suite re-counts the source tree and asserts equality; a missing bump is a deliberate PR-visible CI signal, not silent drift.

If the skill declares `retention:`, also append its id to `retention_commands`.

## Step 5 — Verify

```bash
source .venv/bin/activate
python -m pytest tests/        # should report 53+ passed
make install                   # render to all 3 adapters
```

Twelve conformance invariants (A–L) gate the work, including:

- **I**: every non-`SKILL.md` file under your bundle ships to all 3 host outputs.
- **J**: every relative markdown link in source resolves.
- **K**: every relative markdown link in the **rendered** output resolves (catches Codex path-flattening drift).
- **L**: every YAML `references[].doc:` resolves.

See [`tests/README.md`](../tests/README.md) for the full invariant table.

## Common pitfalls

These all bit real commits during the 12-split refactor + audit rounds:

- **Slash-command syntax in a path.** `doc: ../scholar:patent-claims/SKILL.md` is a typo — `scholar:` is the command prefix, not a directory name. Write `doc: ../patent-claims/SKILL.md`.
- **Off-by-one `..` to cross out of the plugin.** From `skills/<X>/SKILL.md`, reaching repo-root `docs/` takes **four** `..` (`../../../../docs/foo.md`), not three. From `hooks/<X>.md` it's three.
- **Markdown links inside fenced code or inline code spans.** Invariant J strips ` ``` ... ``` ` and `` `...` `` before parsing to avoid false positives from backticked regex examples; but if you write a *real* link inside a code span by accident, the link-check won't see it.
- **Updating callers when content moves.** When you split a `## §3 Ethics` section into `references/ethics.md`, grep the whole repo for `SKILL.md §3` and `<your-skill>/SKILL.md` prose anchors. Commands and agents that pointed at the old section need re-pointing.
- **`references/X.md` inside YAML frontmatter.** The `references:` block expects `doc:` paths that resolve to a file or directory — these are pointer metadata, not markdown links. They are not auto-checked by invariant J (which scans body links only); invariant L gates them.

## Walked example

`skills/deep-literature-review/` is the canonical heavy bundle:

```
SKILL.md                              98 lines (thin entry)
references/stage-1-frame.md          per-stage spec ×6
references/stage-2-retrieve.md
references/stage-3-screen.md
references/stage-4-cluster.md
references/stage-5-critique.md
references/stage-6-synthesise.md
references/breadth-depth-budget.md   cross-cutting ×6
references/prisma-recipe.md
references/resume-protocol.md
references/failure-modes.md
references/upstream-credits.md
references/anti-patterns.md
```

Persistent context: the agent loads only `SKILL.md` (98 lines) plus the one stage reference it's currently executing — not the 233-line monolith the file used to be. Tracked in [`optimization-status.md`](optimization-status.md) Path B row 2.
