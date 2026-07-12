# Staleness rule

Default: a scope file is **fresh** if `(today - approved_date) <= 14 days`. After 14 days it is **stale** — the user must run `workflow:scope.run` again, or explicitly re-confirm by re-setting `approved_date: <today>` and `staleness_until: <today + 14d>`.

Configurable in `.evidraft/project.yaml`:

```yaml
scope:
  staleness_days: 14    # raise or lower as the project's pace demands
```

Downstream creative commands consume this rule via `policy:scope`. A `draft` (never-approved) file is treated as missing, not stale.
