# Failure modes and evidence boundaries

Never invent data to hide a failure. Preserve useful supported artefacts and record the
boundary that downstream stages must respect.

| Stage | Trigger | Best-effort behavior | Status |
|---|---|---|---|
| Frame | scope missing or stale | Continue from explicit topic or project metadata; note that scope is advisory | `complete_with_gaps` only if material context is missing |
| Retrieve | network or all providers unavailable | Reuse readable local PDFs/BibTeX; otherwise write an empty verified set plus provider boundary | `complete_with_gaps` |
| Screen | abstract unavailable | Exclude the candidate without guessed metadata and record the reason | `complete_with_gaps` when coverage is material |
| Cluster | citation lineage unavailable | Leave lineage empty and mark retrieval degradation | `complete_with_gaps` |
| Critique | fast mode | Skip Stage 5 and do not dispatch a critic | no gap |
| Critique | full mode PDF unavailable | Record an abstract-only boundary without unseen locators | `complete_with_gaps` |
| Synthesise | missing or failed citation audit | Preserve supported draft, list unresolved claims and recovery actions | `complete_with_gaps` |
| Budget | requested fan-out exceeds the ceiling | Stop that fan-out, keep completed work, and log truncation | `complete_with_gaps` |

Use `blocked` only when workspace safety prevents every useful write or Stage 1 cannot
resolve a topic. Every degraded artefact carries its marker so later stages do not
mistake bounded evidence for complete coverage.
