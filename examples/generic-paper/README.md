# Example: generic-paper (illustrative starter state)

> **Illustrative example.** This directory shows what an EviDraft paper
> project looks like immediately after `/scholar:paper-init`, before any
> literature, code, or experiment work has been done.

## What this example shows

The minimum viable scaffold that `/scholar:paper-init` writes:

```
generic-paper/
├── .evidraft/
│   ├── project.yaml                project_type: paper, all statuses not_started
│   ├── evidence/evidence.jsonl     (empty)
│   └── literature/
│       ├── references.bib          header comment only
│       └── matrix.md               table header only
└── manuscript/
    ├── main.tex                    arXiv-style placeholder
    ├── references.bib              -> ../.evidraft/literature/references.bib
    └── sections/
        ├── introduction.tex
        ├── related_work.tex
        ├── method.tex
        ├── experiments.tex
        └── conclusion.tex
```

All section files are placeholder skeletons that mirror
`plugins/scholar-ip/templates/paper-project/manuscript/`. They contain
TODO comments and reminders about which EviDraft hooks will block which
strong-claim verbs.

## What this example does NOT show

- No literature matrix entries -- run `/scholar:paper-lit` to populate.
- No codebase mapping -- run `/scholar:paper-code-audit` once you have code.
- No experiments -- run `/scholar:paper-experiment` once you have csv runs.
- No populated manuscript -- run `/scholar:paper-draft` after the steps above.

## When to look at the bigger example

For a fully worked end-to-end paper flow with real-looking content
(fictional CV detector, populated evidence, manuscript with citations
and an `\input`able results table), see
[`../cv-detection-paper/`](../cv-detection-paper/).
