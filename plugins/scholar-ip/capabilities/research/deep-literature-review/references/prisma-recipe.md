# PRISMA recipe + chat output

## Counts formula

Compute and persist:

```
retrieved        = len(candidates.jsonl, before dedup)
after_dedup      = len(candidates.jsonl, canonical rows only)
screened_in      = count(decision=include)
screened_out     = count(decision=exclude)
maybe            = count(decision=maybe)
clustered        = sum(len(cluster.members) for cluster in clusters.yaml)
cited_in_draft   = count(distinct citation_key referenced in related_work.draft.md)
```

`excluded_by_reason` is a histogram of the `reason` column from `screening_log.csv`.

## Mandatory chat output

At the end of every run, print to chat:

```
PRISMA flow (run <run_id>)
  candidates_retrieved : <int>
  after_dedup          : <int>
  screened_in          : <int>
  screened_out         : <int>   (top-3 reasons: ...)
  clustered            : <int>   (<N> clusters)
  cited_in_draft       : <int>
  citation_audit       : resolved=<int> failed=<int>
```

If `citation_audit.failed > 0`, refuse to mark the run done and tell the user which claims failed and which stage to re-run.

## Citation-guard interaction

Strong-claim verbs in `related_work.draft.md` (SOTA, novel, first, outperform, significant, superior, …) need a `\cite{}` or `ev_NNNN` within 30 chars. Run the style-audit strong-claim scan before accepting the draft; its `cited_in_draft` count is invalid if citations are missing.
