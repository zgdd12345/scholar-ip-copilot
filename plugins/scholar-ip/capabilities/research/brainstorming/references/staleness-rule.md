# Staleness rule

Default: a scope file is **fresh** if `(today - approved_date) <= 14 days`. After 14 days it is **stale** — the user must run `workflow:scope.run` again, or explicitly re-confirm by re-setting `approved_date: <today>` and `staleness_until: <today + 14d>`.

Configurable in `.evidraft/project.yaml`:

```yaml
scope:
  staleness_days: 14    # raise or lower as the project's pace demands
```

Downstream commands may use this rule to report advisory context. A `draft`
(never-approved) file remains useful background but is not presented as current approved
scope. Missing, draft, or stale scope never hard-blocks generation.
