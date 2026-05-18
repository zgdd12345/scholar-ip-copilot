---
id: paper-idea
title: "Brainstorm novelty hypotheses grounded in literature, code, and experiments"
kind: command
slash: /scholar:paper-idea
phase: paper
inputs:
  - name: seed_idea
    type: string
    optional: true
outputs:
  - path: .evidraft/ideas/novelty_matrix.md
  - path: .evidraft/ideas/risk_matrix.md
  - path: .evidraft/ideas/experiment_to_validate.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency]
subagents: [literature-reviewer, codebase-analyst, novelty-critic]
references:
  - doc: ../skills/codebase-audit/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:paper-idea

Generate **bounded** novelty hypotheses. Inputs are the literature matrix, the
code repo, and the experiments. Output is three structured markdown tables.

## Steps

1. **Gather.**
   - `.evidraft/literature/matrix.md` (method families, gaps).
   - `.evidraft/code/method_to_code.md` (what the code actually does).
   - `.evidraft/experiments/result_analysis.md` if it exists.
2. **Brainstorm 5–10 candidate ideas.** For each, fill `novelty_matrix.md`:
   | Idea | Problem | Prior Work | Novelty | Evidence | Experiment Needed | Patent Potential | Risk |
   - `Prior Work` cites `citation_key`s from `references.bib`.
   - `Evidence` lists `evidence_id`s justifying the claim of novelty.
   - `Patent Potential` ∈ {low, medium, high} (advisory only).
3. **Run the `novelty-critic` agent** over the matrix; drop or rewrite any row it shoots down.
4. **Risk pass.** Fill `.evidraft/ideas/risk_matrix.md`:
   | Idea | Technical risk | Data risk | Compute risk | Reproducibility risk | Mitigation |
5. **Experiments-to-run.** Fill `.evidraft/ideas/experiment_to_validate.md`:
   | Idea | Experiment | Dataset | Metric | Baseline | Expected effect size | Required artefacts | Owner | ETA |

## Constraints

- Reject ideas that have no evidence trail. Empty `Evidence` column == not novel for our purposes.
- Be honest about overlap with prior work; the `novelty-critic` agent must approve every row.
- Mark optimistic claims as `confidence=low` in any evidence record you create.

## Done criteria

- ≥ 3 novelty rows survive the critic.
- Risk matrix and experiment matrix exist with at least one row per surviving idea.
- Chat output suggests `/scholar:paper-code-audit` or `/scholar:paper-experiment` next.
