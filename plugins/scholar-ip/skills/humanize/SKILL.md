---
id: humanize
title: "Williams-style prose polish: rules, banned phrases, ethics, model routing, diff log"
kind: skill
phase: paper
description: >
  Loaded by /scholar:polish. Ships ~12 concrete rewriting rules (Williams /
  Pinker / Strunk lineage), a banned-phrase lint list (≥15 AI-tell n-grams),
  the verbatim academic-integrity ethics block, the external-model routing
  config under .evidraft/project.yaml.style.humanize.*, and the unified-diff
  log specification. Not a detector-evasion tool.
triggers:
  - "/scholar:polish"
  - "polishing manuscript prose"
  - "reducing AI-flavour in a draft"
  - "running the prose-polisher agent"
provides:
  - rewriting-rules
  - banned-phrase-list
  - ethics-block
  - external-model-routing
  - diff-log-spec
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [humanize-evidence-preserve, citation-guard, evidence-consistency]
references:
  - doc: ../../../../docs/legal-and-ethics.md
  - doc: ../../agents/prose-polisher.md
  - doc: ../../hooks/humanize-evidence-preserve.md
  - doc: ../evidence-check/SKILL.md
  - doc: references/rewriting-rules.md
  - doc: references/banned-phrases.md
  - doc: references/ethics-and-refusal.md
  - doc: references/model-routing.md
  - doc: references/diff-log-spec.md
  - doc: references/anti-patterns.md
---

# humanize

## When to use

Loaded whenever `/scholar:polish` runs, or whenever an agent considers a "make this read more naturally" pass on a draft. The skill is the single source of truth for the rules, the banned-phrase list, the ethics statement, the model-routing config, and the diff-log shape. The command and the `prose-polisher` agent both defer to it.

This is **not** a detector-evasion tool. See [ethics-and-refusal.md](references/ethics-and-refusal.md) for the verbatim ethics block and refusal triggers — load it before responding to any rewrite request.

## Inputs

- the target prose file(s) under `manuscript/` (typically `manuscript/sections/*.tex` or `manuscript/main.tex`),
- `.evidraft/evidence/evidence.jsonl` (filter `type=note` with `tags: [entity]`) — named entities to preserve verbatim,
- `.evidraft/project.yaml` `style.humanize.*` — model routing and per-project knobs,
- environment variables for the configured provider (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; Ollama needs none).

## Outputs

- a stream of hunks emitted by the `prose-polisher` agent,
- `.evidraft/style/humanize-<ts>.log` — unified diff with per-hunk rule trace,
- `.evidraft/style/humanize-<ts>.report.md` — human-readable change report (banned-phrase counts, evidence diff verdict, ethics block).

Full format spec in [diff-log-spec.md](references/diff-log-spec.md).

## How to navigate this skill

Load only the reference for the layer you are in.

| Concern | Reference | Owns |
|---|---|---|
| How to rewrite | [rewriting-rules.md](references/rewriting-rules.md) | R1-R12 mandatory + R13-R15 optional Williams/Pinker/Strunk rules; preservation invariants (numbers, cite keys, named entities, hedges); paragraph-count and voice constraints |
| What to flag | [banned-phrases.md](references/banned-phrases.md) | 20-row AI-tell lint table with per-row justification; lint behaviour (case-insensitive, word-boundary, code-span exclusion) |
| Ethics + refusal | [ethics-and-refusal.md](references/ethics-and-refusal.md) | verbatim ethics block; full refusal-flag list + regex; venue policies (ICML / NeurIPS / ACL / IEEE) — `commands/polish.md` anchors here |
| Model routing | [model-routing.md](references/model-routing.md) | `style.humanize.*` schema; provider env-var table; 4-step resolution algorithm; no-keys-in-repo policy |
| Output format | [diff-log-spec.md](references/diff-log-spec.md) | `humanize-<ts>.log` unified-diff per-hunk format + required trailing comments; `humanize-<ts>.report.md` 5-section fixed order |
| What to avoid | [anti-patterns.md](references/anti-patterns.md) | the 8 anti-patterns (cadence-smoothing, banned-phrase rotation, rounding, key-canonicalisation, hedge-removal, unsolicited bullets, .evidraft-scope violation, detector-evasion framing) |

## Quality checklist

- [ ] Every hunk has a non-empty `rules_fired[]`.
- [ ] `delta_ratio ≤ max_delta_ratio` for every applied hunk.
- [ ] No applied hunk changed a numeric literal, `\cite{}` key, `ev_NNNN` marker, registered named entity, or empirical hedging adverb.
- [ ] Paragraph count drift within ±1 per section file.
- [ ] Voice (1st / 3rd person) matches source per paragraph.
- [ ] Banned-phrase count after rewrite is ≤ count before rewrite (no new banned phrases introduced).
- [ ] Report ends with the verbatim ethics block from [ethics-and-refusal.md](references/ethics-and-refusal.md).
- [ ] The resolved model id is recorded in the report.

## Idea-level references

This skill draws on, but does not vendor, the following:

- Joseph M. Williams, *Style: Lessons in Clarity and Grace*. The sentence-level rules (R3, R4, R13) are the Williams lineage.
- Steven Pinker, *The Sense of Style*. The cadence / sentence-length rule (R1) and the "no throat-clearing" rule (R14) follow Pinker.
- William Strunk Jr. & E. B. White, *The Elements of Style*. The "cut empty words" rule (R2) and the bullet-list discipline (R5) follow Strunk.
- andrehuang's `prose-polisher` (open-source prompt set) — seeded the banned-phrase list. We re-implement the rules; we do not vendor the prompts.
- QuillBot, Wordtune — commercial style-rewriters. We borrow the *style* polish framing; we explicitly reject their occasional detector-evasion marketing.

All borrowings are conceptual. No third-party source is vendored at v0.1 (per `docs/legal-and-ethics.md` section 6).
