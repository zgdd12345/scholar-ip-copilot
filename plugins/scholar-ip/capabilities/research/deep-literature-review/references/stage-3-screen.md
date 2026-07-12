# Stage 3 — Screen

**Preconditions.** `candidates.jsonl` exists with ≥1 row.

**Procedure.** Dispatch `screener` (one pass per candidate). The discipline is borrowed from PRISMA-flow tooling (ASReview, Rayyan, open-paper-machine — see [upstream-credits.md](upstream-credits.md)): every drop has a reason; no silent rejects.

1. Score each candidate against the inclusion / exclusion rubric derived from `plan.yaml`. Use a 0–5 integer score; `decision in {include, include_with_caveat, exclude, maybe}`.
2. Every drop carries a single-sentence `reason`. No silent rejects.
3. `include_with_caveat` is for rows that are mechanistically relevant but match an exclusion keyword (e.g. a video-detection paper whose aux-branch trick is the relevant pattern but the modality is excluded). When used, `decision=include_with_caveat` AND the `caveat` column carries a one-sentence "cite as inspiration in Method, not as direct baseline" guidance. These rows still reach Stage 4 clustering but are tagged for non-baseline use only.
4. When the abstract is missing and the candidate's score is borderline (`maybe`), invoke `capability:scholar-search` with the candidate's `provider_id` to fetch the per-paper detail (S2 `/paper/<id>?fields=abstract` is the cheapest retry); if that still fails, set `decision=exclude` with `reason="abstract unavailable"`.
5. Emit PRISMA counts: `retrieved`, `after_dedup`, `screened_in`, `screened_in_with_caveat`, `screened_out`, plus `excluded_by_reason` histogram. See [prisma-recipe.md](prisma-recipe.md) for the canonical formula.

**Artefact schema — `screening_log.csv`.**

```
id,score,decision,reason,caveat,run_id
cand_0001,5,include,"matches q1 method perspective, dataset overlap",,dr-...
cand_0002,1,exclude,"out of year range (1998 < 2018)",,dr-...
cand_0003,3,include_with_caveat,"mechanism matches q1 but modality is video","cite as inspiration in Method, not as direct baseline",dr-...
```

`caveat` is empty for `include` / `exclude` / `maybe`; non-empty only for `include_with_caveat`.

PRISMA counts append to `plan.yaml.prisma:`.

**Failure mode.** If the abstract fetch fails for every borderline row, surface that explicitly in the chat summary; do not invent abstracts. Full degradation catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 4 reads only rows with `decision=include` or `decision=include_with_caveat`.
