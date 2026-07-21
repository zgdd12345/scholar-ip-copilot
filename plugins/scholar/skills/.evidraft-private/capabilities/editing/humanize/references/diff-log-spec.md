# Diff log spec

Two files per invocation, both under `.evidraft/style/`. `<ts>` is UTC `YYYYMMDDTHHMMSSZ`; two invocations in the same second use `<ts>` then `<ts>-v2`.

## `humanize-<ts>.log` — unified diff

One block per hunk:

```
--- manuscript/sections/introduction.tex
+++ manuscript/sections/introduction.tex
@@ -42,4 +42,4 @@
-It is important to note that our method outperforms the baseline by 4.2 points.
+Our method outperforms the baseline by 4.2 points.
# rules: R2-cut-hedge-padding, R3-one-idea-per-sentence
# delta_ratio: 0.18
# preserve: ok
```

Per-hunk trailing comments are **required**:

- `# rules: <rule-id>[, <rule-id>...]` — non-empty.
- `# delta_ratio: <float>` — must be ≤ `max_delta_ratio` (see [model-routing.md](model-routing.md)).
- `# preserve: ok|fail` — verdict from the `evidence-auditor` pass. `fail` hunks are recorded but **not** applied.

Hunks that the agent skipped (delta too large, self-check failed) are recorded as:

```
# skipped: delta-ratio-exceeded   (or: preserve-self-check-failed)
# original_lines: 42-47
```

## `humanize-<ts>.report.md` — markdown summary

Section order is **fixed**:

1. `# Summary` — target file list, mode (`interactive` / `all` / `none`), resolved model id, total hunks proposed / accepted / blocked.
2. `# Banned-phrase counts` — table with columns `phrase`, `before`, `after`.
3. `# Per-hunk rule trace` — one row per emitted hunk: `file`, `line_range`, `rules_fired`, `delta_ratio`, `preserve`.
4. `# Evidence diff` — `PASS` if every emitted hunk passed the preserve pass; `FAIL` with the list of offending tokens otherwise.
5. `# Ethics` — the verbatim ethics block from [ethics-and-refusal.md](ethics-and-refusal.md).
