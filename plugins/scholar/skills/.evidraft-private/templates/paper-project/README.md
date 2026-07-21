# paper-project template

This directory is a **template**, not a working project. The `paper init` action
creates only four core files in the user's project root and never overwrites an
existing file. Later workflow actions create all other artifacts from the
additional reference assets stored in this template.

The four core files are `.evidraft/project.yaml`,
`.evidraft/evidence/evidence.jsonl`, `.evidraft/literature/references.bib`, and
`manuscript/main.tex`.

## What lands on disk

```
<project>/
  .evidraft/
    project.yaml                  paper-typed project descriptor
    evidence/evidence.jsonl       append-only evidence store
    literature/references.bib     canonical BibTeX
  manuscript/
    main.tex                      arXiv-neutral \documentclass{article}
```

`paper init` does not create `manuscript/sections/`, matrices, analyses, claims,
or other later-stage placeholders. Their owning workflow action creates them only
when requested.

## Drafting style: arXiv neutral

The default `\documentclass` is plain `article` with `graphicx`, `amsmath`,
`amssymb`, `booktabs`, `hyperref`, and `natbib`. There is no venue-specific
class file in this template.

When the user is ready to submit, `paper venue <venue>` converts this
manuscript into the target venue's template (CVPR, NeurIPS, ICCV, ECCV, ICML,
ICLR, EMNLP, ACL, AAAI, IEEEtran, ACM-generic, ...). Keeping the draft style
stable until submission time decouples writing from publication-target churn.

## Authoring rules echoed by this template

- Every literature claim cites a `citation_key` in `references.bib`.
- Every number cites a row in `.evidraft/experiments/result_analysis.md`.
- Every code claim cites a `file_path` (+ line range) via
  `.evidraft/code/method_to_code.md`.
- The `evidence-integrity` policy enforces the above before publish-class actions.
