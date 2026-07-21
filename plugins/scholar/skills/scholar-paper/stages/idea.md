# workflow:paper.idea

Generate **bounded** novelty hypotheses. Inputs are the literature matrix, the
code repo, and the experiments. Output is three structured markdown tables.

## Best-effort reuse

This action is best effort. Build an `Input summary` from the seed idea and the
fingerprints of the literature, code-map, and experiment inputs. If an existing
idea artifact's `Input summary` matches the current normalized inputs and source
fingerprints, reuse its supported rows and evaluate only changed inputs. Put the
current `Input summary` at the top of every artifact. Missing literature, code, or
experiment inputs are gaps that narrow confidence; they do not prevent bounded
hypotheses from the material that is available.

## Steps

1. **Gather.** Use the `literature-reviewer` subagent to refresh `matrix.md` if stale, and the `codebase-analyst` subagent to update `method_to_code.md` if the repo moved since the last audit.
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
- Chat output suggests `workflow:paper.code-audit` or `workflow:paper.experiment` next.
- Status is `complete`, `complete_with_gaps` when any input or evidence remains
  missing, or `blocked` only when workspace safety prevents every useful output.
