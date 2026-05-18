# paper-project template

This directory is a **template**, not a working project. `/scholar:paper-init`
materialises this tree (without overwriting existing files) into the user's
project root.

## What lands on disk

```
<project>/
  .evidraft/
    project.yaml                  paper-typed project descriptor
    evidence/evidence.jsonl       append-only evidence store
    literature/
      references.bib              canonical BibTeX
      matrix.md                   paper x method x dataset x result x gap
    ideas/
      novelty_matrix.md
      risk_matrix.md
      experiment_to_validate.md
    code/
      repo_summary.md
      method_to_code.md
      paper_code_audit.md
    experiments/
      result_analysis.md
      tables/                     LaTeX tables ready to \input
  manuscript/
    main.tex                      arXiv-neutral \documentclass{article}
    references.bib                symlink/copy of .evidraft/literature/references.bib
    sections/
      introduction.tex
      related_work.tex
      method.tex
      experiments.tex
      conclusion.tex
```

## Drafting style: arXiv neutral

The default `\documentclass` is plain `article` with `graphicx`, `amsmath`,
`amssymb`, `booktabs`, `hyperref`, and `natbib`. There is no venue-specific
class file in this template.

When the user is ready to submit, `/scholar:paper-venue <venue>` converts this
manuscript into the target venue's template (CVPR, NeurIPS, ICCV, ECCV, ICML,
ICLR, EMNLP, ACL, AAAI, IEEEtran, ACM-generic, ...). Keeping the draft style
stable until submission time decouples writing from publication-target churn.

## Authoring rules echoed by this template

- Every literature claim cites a `citation_key` in `references.bib`.
- Every number cites a row in `.evidraft/experiments/result_analysis.md`.
- Every code claim cites a `file_path` (+ line range) via
  `.evidraft/code/method_to_code.md`.
- `citation-guard` and `evidence-consistency` hooks enforce the above.
