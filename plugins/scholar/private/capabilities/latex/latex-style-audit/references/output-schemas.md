# Output schemas

Two artefacts written under `.evidraft/manuscript/` — a human log + a machine JSON.

## `.evidraft/manuscript/style_audit-<ts>.log`

One row per finding. Columns separated by ` | `:

```
<severity> | <file>:<line> | <rule_id> | matched: <text> | suggested: <text>
```

Trailing block: `summary: info=<n> warn=<n> fail=<n>`.

## `.evidraft/manuscript/style_audit-<ts>.findings.json`

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "manuscript_root": "manuscript/",
  "findings": [
    {
      "rule_id": "FIG_CAPTION_PUNCT",
      "severity": "warn",
      "file": "manuscript/sections/method.tex",
      "line": 142,
      "matched": "\\caption{Figure 1 The architecture}",
      "suggested": "\\caption{Figure 1.\\ The architecture}",
      "explanation": "Captions use sentence form with terminating period."
    }
  ],
  "summary": {"info": 0, "warn": 0, "fail": 0}
}
```

**Severity totals** reflect the emitted findings only; rules that did not fire do not contribute zeros for their own bucket — the bucket counts severities, not rules.
