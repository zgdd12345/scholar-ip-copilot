# Failure modes (degradation catalog)

Every stage has a defined degradation mode. The pipeline NEVER silently invents data on failure — it either falls back to a documented degraded path or stops the run.

| Stage | Trigger | Degradation | Marker |
|---|---|---|---|
| Stage 1 | `policy:scope` preflight blocks | Stop; ask user to run `workflow:scope.run` | preflight message |
| Stage 2 | `WebFetch` unavailable / all providers 429 / no network | Fall back to local `.evidraft/literature/references.bib` + PDFs under `references/` / `papers/`. Each fallback row uses `source: "local-bib"` or `source: "local-pdf"`. | `plan.yaml.notes` records the fallback |
| Stage 3 | Borderline row's abstract fetch fails | Set `decision=exclude` with `reason="abstract unavailable"`. Do NOT invent abstracts. | `screening_log.csv` reason column |
| Stage 3 | All borderline abstract fetches fail | Surface to chat summary; do not invent abstracts. | (chat output) |
| Stage 4 | References / citations hops return no data | Skip lineage fields (leave `[]`); note `"lineage: degraded (retrieval unavailable)"` per cluster. Cluster membership still produced. | `clusters.yaml` per-cluster note |
| Stage 5 | PDF unavailable, only abstract in hand | Mark each SWOT bullet `[abstract-only]`; reduce confidence; NEVER invent section numbers. | bullet tag |
| Stage 6 | Free-text citation resolution fails | Fall back to manual lookup against `references.bib` + `evidence.jsonl`. If still unresolvable, flag `status: failed` in `citation_audit.json` and refuse to mark the run complete. | `citation_audit.json.claims[].status` |
| Budget | Fan-out exceeds `breadth * 50` or other ceiling | Refuse the fan-out; log to `plan.yaml.budget_log[]`; surface to user. | `plan.yaml.budget_log` |

**Universal rules:**
- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one row.
- Every degraded artefact must carry its degradation marker so downstream stages can detect upstream weakness.
