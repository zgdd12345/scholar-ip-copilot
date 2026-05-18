---
id: patent-claims
title: "Draft independent and dependent claims; emit structured parsed form and claim chart"
kind: command
slash: /scholar:patent-claims
phase: patent
inputs:
  - name: candidate_id
    type: string
    optional: true
  - name: independent_count
    type: integer
    optional: true
    default: 1
  - name: dependent_count
    type: integer
    optional: true
    default: 6
outputs:
  - path: .evidraft/patent/claims.md
  - path: .evidraft/patent/claims_parsed.json
  - path: .evidraft/patent/claim_chart.md
  - path: .evidraft/patent/claim_chart-<ts>.json
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:grep*", "Bash:awk*"]
hooks: [scope-required, citation-guard, evidence-consistency]
subagents: [claim-drafter, patent-engineer, novelty-critic, evidence-auditor]
references:
  - doc: ../skills/patent-claims/SKILL.md
  - doc: ../skills/claim-parser/SKILL.md
  - doc: ../skills/claim-chart-builder/SKILL.md
  - doc: ../../../docs/legal-and-ethics.md
---

# /scholar:patent-claims

Draft a first set of independent and dependent claims. Output is **attorney-reviewable**, not filed text. Every run produces both a human-readable `claims.md` AND a structured `claims_parsed.json` so downstream commands (`/scholar:patent-review`) can consume claims without re-parsing prose.

## Steps

1. **Anchor on the disclosure.** Load `invention_disclosure.md` for the candidate. Refuse to draft if the candidate lacks `Technical solution` or `Implementation details`.
2. **Independent claim(s).** Draft 1–`independent_count` independent claims. Each:
   - one preamble + one or more transition + body elements,
   - each element numbered and labelled (`[a]`, `[b]`, …),
   - language consistent with the specification (re-use the same nouns and verbs).
3. **Dependent claims.** Draft up to `dependent_count` dependent claims that narrow scope along axes the disclosure already supports.
4. **Write `claims.md`** containing:
   ```
   # Draft claims (for attorney review)
   ## Claim 1 (independent)
   1. A method comprising:
      a. <element>;
      b. <element>;
      c. <element>.
   ## Claim 2 (dependent on 1)
   ...
   ```
5. **Parse claims into structured form.** Drive `skills/claim-parser/SKILL.md`:
   - Reads the just-written `claims.md` and emits `.evidraft/patent/claims_parsed.json` (canonical structured form: per-claim preamble + transition + bracketed elements + antecedent chain + dependency graph) + a paired `claim_parse-<ts>.log`.
   - Surfaces parser warnings (≥ 9 rule taxonomy: `ANTECEDENT_MISSING`, `MULTIPLE_DEPENDENCY`, `TRANSITION_UNKNOWN`, `DEPENDENT_NO_NARROW`, `MISSING_TERMINUS` `fail`, `UNNUMBERED_ELEMENT` `fail`, `FORWARD_DEPENDENCY` `fail`, `EMPTY_CLAIM` `fail`, `TERMINOLOGY_DRIFT`).
   - Any `fail` row blocks the chart-building step and surfaces to the user for revision; `warn`/`info` rows are reported but do not block.
6. **Build claim chart.** Drive `skills/claim-chart-builder/SKILL.md`:
   - Reads `claims_parsed.json` + `prior_art_map.md` (+ optional `invention_disclosure.md` for spec support, `method_to_code.md` for code support).
   - Emits `.evidraft/patent/claim_chart.md` (replaces the previous template) AND `.evidraft/patent/claim_chart-<ts>.json` (structured, carries the same `run_id`).
   - Columns: `Claim` | `Element` | `Spec support` | `Code support` | `Prior art overlap` | `Risk` | `Suggested revision`.
   - `Prior art overlap` carries `overlap_score ∈ {none, low, medium, high, identical}`; `identical` requires a verbatim quote in `overlap_passage`.
   - `Risk` = max(per-element overlap_score), with no-support override to `high` when both `Spec support` and `Code support` are empty.
   - `Suggested revision` populated for medium / high risk; never widens scope.
7. **Required footer** appended to `claims.md` (identical in spirit to `patent-disclosure.md`):
   ```
   > Draft claims. Not filed text. Must be reviewed and adapted by a registered
   > patent agent / attorney before any filing decision.
   ```

## Constraints

- Every claim element must be traceable (spec + code). No "magic" elements.
- Avoid functional-only claiming where structural language exists.
- The claim drafter and novelty critic must both pass each element before it stays in `claims.md`.
- Strong-claim verbs (novel, unique, …) are not used inside claim text itself.
- The structured `claims_parsed.json` is canonical (no `<ts>` suffix); the `.log` trace is timestamped. `claim_chart-<ts>.json` is timestamped so multiple builds can be diffed.
- Parser `fail` warnings block downstream chart-building until resolved.

## Done criteria

- `claims.md` and `claim_chart.md` updated.
- `claims_parsed.json` exists and is schema-valid; parser warnings surface to chat.
- `claim_chart-<ts>.json` exists with `summary.rows_total` matching the markdown chart.
- No row in `claim_chart.md` has an empty `Specification support` or `Code support` cell (use `n/a` only with justification — and any `n/a` triggers a `high` risk override per the chart-builder skill).
- Required footer present in `claims.md`.
- Chat output recommends `/scholar:patent-review` next.
