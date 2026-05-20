---
id: claim-parser
title: "Claim parser: structural parse of claims.md into JSON + antecedent-basis audit"
kind: skill
phase: patent
description: >
  Parses `.evidraft/patent/claims.md` (the output of `/scholar:patent-claims`)
  into a structured JSON form so downstream skills (`claim-chart-builder`,
  `novelty-heuristics`) and the multi-role review never have to re-tokenise
  free-text claims. Extracts preamble, transition, labelled elements, and the
  independent/dependent dependency graph; runs an antecedent-basis sweep and
  emits a small taxonomy of structural warnings. Advisory only —
  attorney-reviewable, not legal advice.
triggers:
  - "command:/scholar:patent-claims"
  - "command:/scholar:patent-review"
  - "subagent:claim-drafter"
provides:
  - structured-claim-form
  - antecedent-basis-chain
  - element-labelling
  - independent-dependent-graph
  - claim-parse-warning-taxonomy
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:grep*"
  - "Bash:awk*"
hooks: [evidence-consistency]
references:
  - doc: ../../agents/claim-drafter.md
  - doc: ../../commands/patent-claims.md
  - doc: ../../commands/patent-review.md
  - doc: ../../../../docs/legal-and-ethics.md
---

# claim-parser

## When to use

Runs whenever `.evidraft/patent/claims.md` is (re)written or re-read:

- as a sub-pass of `/scholar:patent-claims` immediately after `claim-drafter` writes the file, so the rest of the pipeline can read JSON instead of prose;
- as a sub-pass of `/scholar:patent-review`, so the `claim drafter` reviewer role and the `novelty critic` role share the same structural view;
- on demand from the `claim-drafter` subagent itself, between drafts, to verify its own antecedent basis before publishing.

The skill is **observational**. It never rewrites `claims.md`. Downstream skills (`claim-chart-builder`, `novelty-heuristics`) consume the JSON and trust that the surface form in `claims.md` is authoritative.

Skip the run if `claims.md` does not exist; emit a single chat line and exit cleanly (this is the normal case before `/scholar:patent-claims` has ever produced output).

## Inputs

- `.evidraft/patent/claims.md` — markdown with `# Draft claims (for attorney review)` H1, then per-claim `## Claim N (independent)` / `## Claim N (dependent on M)` H2 sections, each followed by a numbered claim with bracketed `[a]` / `[b]` / ... body elements, terminated by the mandatory attorney-review footer.
- (optional) `.evidraft/patent/invention_disclosure.md` — used **only** by `TERMINOLOGY_DRIFT` (see [references/warning-taxonomy.md](references/warning-taxonomy.md)) to resolve a claim noun back to its specification form. If absent, `TERMINOLOGY_DRIFT` is silently skipped (no false positives).

No other file is read. No file is written outside `.evidraft/patent/`.

## Outputs

Two files per run, both under `.evidraft/patent/`:

- `claims_parsed.json` — canonical structured view of the **current** `claims.md`. **Not** timestamped: downstream skills always read the latest. Overwritten on every run.
- `claim_parse-<ts>.log` — timestamped human-readable trace (one line per parsed claim element, plus one line per warning). `<ts>` is UTC iso-basic (`20260518T143000Z`), matching the convention used by `latex-style-audit` and `bib-audit`.

When called from a command with a `run_id` in its `plan.yaml`, embed it at the top level of `claims_parsed.json`.

Full `claims_parsed.json` schema + field rules: see [references/schema.md](references/schema.md).

## How to navigate this skill

Load only the reference for the step you are executing:

| Stage | Reference | Owns |
|---|---|---|
| Parse procedure (7 steps) | [procedure.md](references/procedure.md) | read → split H2 → per-claim body → antecedent-basis → dep-graph validation → write → chat |
| Warning taxonomy (9 rules) | [warning-taxonomy.md](references/warning-taxonomy.md) | `rule_id` / severity / detection recipe / example / explanation table |
| Output schema | [schema.md](references/schema.md) | `claims_parsed.json` JSON shape + field rules |
| Anti-patterns | [anti-patterns.md](references/anti-patterns.md) | what NOT to do |

## Advisory-only framing

> The `claim-parser` skill performs **structural** parsing of claim text. It does not opine on patentability, claim scope, or legal validity. Parse warnings are advisory; they help an attorney spot issues earlier but are not a substitute for prosecution-grade review. A registered patent agent / attorney must review every output before any filing decision.

This paragraph is reproduced verbatim in every `claim_parse-<ts>.log` footer and must not be removed or paraphrased.
