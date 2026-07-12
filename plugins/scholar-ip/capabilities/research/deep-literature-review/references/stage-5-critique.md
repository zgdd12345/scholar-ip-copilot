# Stage 5 — Critique

**Preconditions.** `clusters.yaml` exists.

**Procedure.** Dispatch `paper-critic` (one pass per included paper). Modelled on the per-section sub-agent pattern used by **GPT-Researcher** and the structured research-brief style of **Open Deep Research** — see [upstream-credits.md](upstream-credits.md).

1. For each `cluster c`, write `critique/<cluster-id>.md` containing one section per member paper.
2. Each section is a SWOT — **Strengths, Weaknesses, Opportunities, Threats** — plus a mandatory `Delta vs our angle` paragraph that names how *this* project differs.
3. Every SWOT bullet must trace to a section / figure / table / equation of the actual paper (not an abstract paraphrase).
4. In `mode=fast`, skip SWOT bullets that require opening the full PDF; keep only `Delta vs our angle`. See [breadth-depth-budget.md](breadth-depth-budget.md) for the full mode semantics.

**Concurrency.** Per-paper SWOT writes within a single cluster are independent — dispatch in parallel. Across clusters, serialise (one `critique/<id>.md` write at a time per cluster file to keep the append atomic). Net speedup at typical breadth=6 / 5 papers per cluster: ~5×.

**Per-paper SWOT template — `critique/<cluster-id>.md`.**

```markdown
# Cluster <id>: <name>

## <citation_key> — <paper title>

- **Strengths.**     - <bullet> (Section X.Y / Fig N / Tbl M / Eq K)
- **Weaknesses.**    - <bullet> (Section X.Y / ...)
- **Opportunities.** - <bullet> (what gap this opens for us)
- **Threats.**       - <bullet> (what blocks our angle if this paper is right)
- **Delta vs our angle.** <one paragraph; ends with the appended evidence id>

(repeat per member paper)
```

Rules:
- Strengths / Weaknesses describe the paper itself; Opportunities / Threats describe the paper *as it bears on our project*.
- Every bullet cites a section, figure, table, or equation. Abstract paraphrase is not a citation.
- `Delta vs our angle` is mandatory. If you cannot write it, the paper does not belong in related work.
- `mode=fast` drops bullets that require the full PDF; mark them `[skipped — fast mode]`. Abstract-only bullets are tagged `[abstract-only]`.

**Failure mode.** If the PDF is unavailable and only the abstract is in hand, mark each bullet `[abstract-only]` and reduce confidence; never invent a section number. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 6 reads `clusters.yaml`, `critique/*.md`, and `evidence_map.json`.
