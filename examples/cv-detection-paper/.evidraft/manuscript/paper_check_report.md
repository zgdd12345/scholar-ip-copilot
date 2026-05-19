<!-- ILLUSTRATIVE EXAMPLE -- /scholar:paper-check output for cv-detection-paper.
     Findings are illustrative; they model what the command WOULD write when
     run against this example's manuscript + audit inputs. Underlying values
     are not from a real LaTeX compile. -->

# Paper check report

Generated: 2026-05-18T14:00:30Z
run_id: paper-check-20260518T140000Z
Manuscript: manuscript/main.tex

Structured-audit artefacts (this run):
- compile errors:  .evidraft/manuscript/compile-20260518T140000Z.errors.json
- style audit:     .evidraft/manuscript/style_audit-20260518T140005Z.findings.json
- bib audit:       .evidraft/literature/bib_audit-20260518T140010Z.findings.json
- xref audit:      .evidraft/manuscript/xref_audit-20260518T140012Z.findings.json
- consistency:     .evidraft/manuscript/consistency_audit-20260518T140020Z.findings.json

## Citation
- Missing keys: 0 (all 2 \cite{}d keys -- smith2024examplekey, chen2023anchorfreebaseline -- resolve in references.bib).
- Unused keys: 0.
- Strong claims without citation: 1 -- conclusion.tex line 16 ("Method X is the first anchor-free head with distribution-focal decoding"). Already self-flagged as NOT_AUDITABLE in paper_code_audit.md; the citation-guard hook surfaces it again here.

## LaTeX
- Compile: PASS (`latexmk -pdf -interaction=nonstopmode -file-line-error manuscript/main.tex` exited 0).
- Errors: 0.
- Warnings: 2 -- one first-run "Citation undefined" (clears on second bibtex pass) + one hyperref-bookmark token warning. Full structured form in compile-20260518T140000Z.errors.json.

## Style
- Fail: 1 -- STRONG_CLAIM_VERB_NO_CITE at conclusion.tex:16 (echoed from citation-guard).
- Warn: 3 -- REF_NONBREAKING_SPACE (experiments.tex:9), NONBREAKING_CITE (related_work.tex:5), TODO_LEFT_IN_PROSE (conclusion.tex:18, soft TODO -- deferred literature claim).
- Info: 3 -- FIRST_PERSON_PLURAL self-test (abstract within threshold), DASH_OVERUSE (no drift), MISSING_GRAPHIC_EXT (no figures present; rule precondition absent).

## Bib quality
- Required-field failures: 0 (both entries have author, title, year; @article has journal, @inproceedings has booktitle).
- Year / venue / DOI / URL issues: 0 -- both years are in range, no embedded year tokens, neither entry carries a DOI/URL (one info advisory to add DOIs before submission).
- Cross-entry consistency: 0 -- both entries use Surname-Initial BibTeX canonical author form.
- Coverage (evidence <-> bib <-> manuscript): all 2 paper-type evidence rows resolve to bib keys; all 2 \cite{}s resolve; warn surfaced on placeholder content -- both bib entries are tagged "Fictional entry for the EviDraft cv-detection-paper example" and must be replaced before submission (BIB_KEY_NEVER_CITED_NEVER_EVIDENCED, used here for placeholder-marker tracking).

## Cross-references
- Duplicated / orphaned / mis-placed labels: 1 LABEL_ORPHANED -- \label{sec:related} in related_work.tex:3 is never \ref-ed (the introduction's narrative jumps from sec:method to sec:experiments and skips related work).
- Broken \ref / \eqref / \cite: 1 REF_BROKEN -- method.tex:23 references a planned ablation table tab:ablation_iou that is currently rolled into tab:main_results; either rename the ref or split the table.
- Style drift (autoref, prefix convention): 0 -- corpus uses Section~\ref{} consistently, no \autoref usage; sec:* / tab:* prefixes are followed by every label.

## Figures & tables
- Unreached figures: 0 (no \begin{figure} blocks in the corpus).
- Missing captions/labels: 0 -- the single table (tab:main_results) carries both \caption and \label, and is \input-ed from sections/experiments.tex.

## Claim-evidence
- Claims without evidence: 1 -- the novelty claim in conclusion.tex line 16 ("first anchor-free head with distribution-focal decoding") is marked NOT_AUDITABLE in paper_code_audit.md and has no [ev_*] anchor. Same row as the citation block's strong-claim flag; reported once here, cross-referenced.
- Every numeric token in the manuscript (0.418, 0.612, 0.823, 0.564, 0.402, 0.547, -1.6) resolves to a row in .evidraft/experiments/result_analysis.md.

## Numbers
- Numbers without source: 0.
- Mismatches (cross-section drift, vs result_analysis): 1 -- the ablation delta is reported as -1.6 points in the abstract, experiments section, and result_analysis.md; the underlying per-seed means give -1.61 to two decimal places. The 0.01 gap sits at the rounding boundary; reviewers will catch the precision inconsistency. See consistency block below -- same row, fail severity.

## Consistency
- TERM_DRIFT / ABBREVIATION_ORDER / SYMBOL_NOTATION_DRIFT / VOICE_DRIFT / TENSE_DRIFT:
  - 2 TERM_DRIFT (warn): "shared per-level tower(s)" vs "four-conv tower per task"; "Method X" prose label vs "AnchorFreeHead" code-side class.
  - 1 ABBREVIATION_ORDER (warn): mAP@0.5:0.95 used in abstract without first expanding "mean Average Precision".
  - 0 SYMBOL_NOTATION_DRIFT (no math symbols defined in body).
  - 0 TENSE_DRIFT.
  - 1 VOICE_DRIFT (info): method.tex (3rd person descriptive) vs experiments.tex (1st person plural). Below the section-internal threshold; informational.
- SECTION_ORDER_VS_FLOW / DATASET_NAME_NORMALISATION:
  - 0 SECTION_ORDER_VS_FLOW.
  - 1 DATASET_NAME_NORMALISATION (warn-as-audit-trail): COCO val2017 / VOC test2007 consistent across corpus; rule fired and resolved cleanly.
- NUMBER_DRIFT: **1 (fail)** -- abstract / experiments / result_analysis.md all report delta -1.6 points; underlying csvs yield -1.61. Hook downgrade applies (see Overall verdict).
- CLAIM_VS_RESULT_MISMATCH: 0.

## Hook configuration applied this run
- `hooks.consistency_audit: warn` -- the user-configurable downgrade for consistency_audit fail rows when the drift sits at the rounding boundary. With this config the single NUMBER_DRIFT (fail) is treated as WARN for the overall verdict, but the row itself stays at `fail` severity in the structured findings JSON so the audit trail is preserved. To restore strict mode, set `hooks.consistency_audit: fail` (the default) and re-run.

Overall verdict: WARN

(without the hook downgrade the verdict would be FAIL due to the single NUMBER_DRIFT row; with the downgrade the manuscript is good enough to circulate to co-authors while the precision pinning and the deferred novelty literature pass remain open work items.)

## Top-3 next actions

1. Pin a single precision for the ablation delta (one decimal place) across abstract, experiments, and result_analysis.md; regenerate main_results.tex from the canonical source.
2. Resolve or rename the orphaned label `sec:related` and the broken ref to `tab:ablation_iou` (cross-references block).
3. Run a literature pass on the "first anchor-free head with distribution-focal decoding" novelty claim in conclusion.tex; attach a citation or mark explicitly as scope-limited, clearing the STRONG_CLAIM_VERB_NO_CITE flag.
