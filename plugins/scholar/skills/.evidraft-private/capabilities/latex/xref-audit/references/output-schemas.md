# Output schemas

Two artefacts written under `.evidraft/manuscript/` per run — a human log + a machine JSON. `<ts>` is UTC iso-basic (e.g. `20260518T143000Z`).

## `xref_audit-<ts>.log`

One finding per line:

```
<severity> <rule_id> <file>:<line> <one-line explanation>
```

## `xref_audit-<ts>.findings.json`

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "manuscript_root": "manuscript/",
  "labels": {"defined": 87, "duplicated": 0, "orphaned": 3},
  "refs":   {"resolved": 124, "broken": 0},
  "cites":  {"resolved": 56, "broken": 1},
  "findings": [
    {"rule_id": "REF_BROKEN",
     "severity": "fail",
     "file": "manuscript/sections/method.tex",
     "line": 142,
     "target": "fig:doesnotexist",
     "explanation": "\\ref{fig:doesnotexist} has no matching \\label{}."}
  ],
  "summary": {"info": 0, "warn": 0, "fail": 0}
}
```

When called with `run_id`, embed it at the top level.

No edits to `.tex`. No edits to `references.bib`. Findings only.
