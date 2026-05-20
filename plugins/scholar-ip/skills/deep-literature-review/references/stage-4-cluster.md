# Stage 4 — Cluster

**Preconditions.** `screening_log.csv` exists with ≥1 `include` row.

**Procedure.**

1. Group included candidates into 3–6 clusters by **technical mechanism**, not by application (see `../../literature-review/SKILL.md` — same family rules as the light command).
2. For each cluster, surface the method lineage, dataset lineage, theory lineage by walking one hop of references (parent works) and one hop of citations (follow-on works) via `skills/scholar-search/SKILL.md`, capped by `depth`.
3. Write `clusters.yaml` and `evidence_map.json`. Every member paper gets a provisional `citation_key` following the `firstauthorYEARkeyword` convention from `../../literature-review/SKILL.md`.

**Artefact schema — `clusters.yaml`.**

```yaml
run_id: <utc-timestamp>
clusters:
  - id: c1
    name: <short technical-mechanism phrase>
    members: [cand_0001, cand_0007, ...]
    method_lineage: [<citation_key>, ...]      # ancestors via get_paper_references
    dataset_lineage: [<dataset name>, ...]
    theory_lineage: [<concept>, ...]
    why_one_cluster: <one sentence>
```

Rules:
- 3–6 clusters per run; a 7th cluster is a signal to collapse two existing ones.
- Every paper belongs to at most one cluster (borderline cases get a secondary cluster note inside the cluster file).
- Cluster names describe **technical mechanism**, not application ("DETR-style set prediction" not "object detection").

**Artefact schema — `evidence_map.json`.**

```json
{"cand_0001":{"citation_key":"smith2023foo","cluster":"c1",
              "evidence_ids":["ev_0123"],"source":"arxiv"}}
```

**Failure mode.** If the reference / citation hops return no data (network down, provider 429 after retries, paper id unresolvable), skip the lineage fields (leave `[]`) and note `"lineage: degraded (retrieval unavailable)"` per cluster. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 5 reads `clusters.yaml` and (for the SWOT inputs) the candidate abstracts from `candidates.jsonl`.
