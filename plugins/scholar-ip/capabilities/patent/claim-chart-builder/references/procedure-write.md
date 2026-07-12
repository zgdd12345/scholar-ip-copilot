# Procedure — write outputs

Render `claim_chart.md` (markdown table per candidate; the capability specification "Advisory-only framing" paragraph at the end). Write `claim_chart-<ts>.json` next to it (schema in [schemas.md](schemas.md)).

Print one chat summary line:

```
claim-chart-builder: <C> candidates, <R> rows  (high=<h>, medium=<m>, low=<l>)
  .evidraft/patent/claim_chart.md
  .evidraft/patent/claim_chart-<ts>.json
```
