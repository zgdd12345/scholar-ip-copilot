---
id: patent-claims
title: "Draft independent and dependent claims with claim-chart traceability"
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
  - path: .evidraft/patent/claim_chart.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency]
subagents: [claim-drafter, patent-engineer, novelty-critic, evidence-auditor]
references:
  - doc: ../skills/patent-claims/SKILL.md
  - doc: ../../../docs/legal-and-ethics.md
---

# /scholar:patent-claims

Draft a first set of independent and dependent claims. Output is **attorney-reviewable**, not filed text.

## Steps

1. **Anchor on the disclosure.** Load `invention_disclosure.md` for the candidate. Refuse to draft if the candidate lacks `Technical solution` or `Implementation details`.
2. **Independent claim(s).** Draft 1–`independent_count` independent claims. Each:
   - one preamble + one or more transition + body elements,
   - each element numbered and labelled (`[a]`, `[b]`, …),
   - language consistent with the specification (re-use the same nouns and verbs).
3. **Dependent claims.** Draft up to `dependent_count` dependent claims that narrow scope along axes the disclosure already supports.
4. **Claim chart.** Update `claim_chart.md`:
   | Claim element | Specification support | Code support | Prior art overlap | Risk | Suggested revision |
   - **Specification support**: section number in `invention_disclosure.md`.
   - **Code support**: `file_path:lines` from `method_to_code.md`/evidence store.
   - **Prior art overlap**: reference id from `prior_art_map.md` (or "none flagged").
   - **Risk** ∈ {low, medium, high}.
   - **Suggested revision**: narrower phrasing if `Risk=high`.
5. **Write `claims.md`** containing:
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
6. **Required footer** identical in spirit to `patent-disclosure.md`:
   ```
   > Draft claims. Not filed text. Must be reviewed and adapted by a registered
   > patent agent / attorney before any filing decision.
   ```

## Constraints

- Every claim element must be traceable (spec + code). No "magic" elements.
- Avoid functional-only claiming where structural language exists.
- The claim drafter and novelty critic must both pass each element before it stays in `claims.md`.
- Strong-claim verbs (novel, unique, …) are not used inside claim text itself.

## Done criteria

- `claims.md` and `claim_chart.md` updated.
- No row in `claim_chart.md` has an empty `Specification support` or `Code support` cell (use `n/a` only with justification).
- Required footer present.
- Chat output recommends `/scholar:patent-review` next.
