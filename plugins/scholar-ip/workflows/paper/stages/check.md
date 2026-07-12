# workflow:paper.check

Produce a single audit report covering everything that can break a paper before submission. The audit pipeline runs cheap → expensive: mechanical cite + LaTeX checks first, then structured rule-based audits (style / bib quality / cross-refs), then semantic consistency.

## Steps

1. **Citation audit.** Drive via `../../../capabilities/evidence/bib-manager/spec.md`:
   - List `\cite{}` keys with no entry in `references.bib`.
   - List `references.bib` entries that are never cited.
   - Flag strong-claim verbs not within 30 chars of a `\cite{}` or `evidence_id` marker.
2. **LaTeX compile.** Drive via `../../../capabilities/latex/latex-build/spec.md`. Use the `latex-editor` subagent to triage any compile errors before continuing:
   - Compile with `latexmk -pdf -interaction=nonstopmode -file-line-error manuscript/main.tex`.
   - Parse `manuscript/main.log` into the six-entry error taxonomy (MISSING_CITE, MISSING_REF, UNDEFINED_COMMAND, UNBALANCED_BRACES, PACKAGE_NOT_FOUND, OTHER) and write `.evidraft/manuscript/compile-<ts>.errors.json`.
   - Report errors and warnings.
   - If `latexmk` is unavailable on `$PATH`, mark "Compile" as `SKIPPED` and continue — Steps 2.5–2.7 still run.
3. **Style audit.** Drive via `../../../capabilities/latex/latex-style-audit/spec.md` (runs only when Step 2 is not `FAIL`):
   - Sweep `manuscript/main.tex` and `manuscript/sections/*.tex` against the 28-rule taxonomy (captions, cross-refs, math, tables/figures, microtypography, common misuses).
   - Run the `STRONG_CLAIM_VERB_NO_CITE` scan defined by the private LaTeX style-audit capability and include every resulting row.
   - Write `.evidraft/manuscript/style_audit-<ts>.findings.json` and `.evidraft/manuscript/style_audit-<ts>.log` (paired `<ts>` with the Step 2 compile artefact).
   - Any rule with severity `fail` downgrades the overall verdict (PASS → WARN, WARN → FAIL).
4. **Bib quality audit.** Drive via `../../../capabilities/evidence/bib-audit/spec.md` (runs after Step 1's `bib-manager` mechanics):
   - Apply the 20-rule audit (required-fields per BibTeX type, year sanity, venue drift, DOI / arXiv format, URL format, cross-entry author drift, coverage against `evidence.jsonl` + `\cite{}`s).
   - Write `.evidraft/literature/bib_audit-<ts>.log` and `.evidraft/literature/bib_audit-<ts>.findings.json` (carry this command's `run_id`).
   - Merge `fail` rows into the "Citation" block; merge `warn` / `info` rows under a new "Bib quality" subsection.
   - De-duplicate `CITED_KEY_NOT_IN_BIB` against Step 1's missing-cite list (report once).
5. **Cross-reference audit.** Drive via `../../../capabilities/latex/xref-audit/spec.md` (runs after Step 2's `latex-build` compile):
   - Build the label / ref / cite graph from `manuscript/main.tex` + `manuscript/sections/*.tex` (static analysis; do not consume `.aux`).
   - Apply the 14-rule audit (duplicated / orphaned / mis-prefixed / mis-placed labels; broken `\ref` / `\eqref` / `\cite`; macro-vs-prefix mismatches; float-order; `\autoref` vs `\ref` consistency).
   - Write `.evidraft/manuscript/xref_audit-<ts>.log` and `.evidraft/manuscript/xref_audit-<ts>.findings.json`.
   - Promote `fail` rows into the "LaTeX" block; emit `warn` / `info` rows under a new "Cross-references" subsection.
   - De-duplicate `xref-audit:CITE_BROKEN` against `bib-audit:CITED_KEY_NOT_IN_BIB` and Step 2's `MISSING_CITE` errors (report once, citing all three sources).
6. **Figure/Table reachability.**
   - Every `\includegraphics{}` and every `\input{*.tex}` table is reachable.
   - Every figure/table has a `\caption{}` and a `\label{}`.
   - Every figure/table is referenced at least once.
7. **Claim-evidence audit.** Use the `evidence-auditor` subagent to walk the claim × evidence matrix and the `methodology-reviewer` subagent to flag any methodology-vs-result mismatches it surfaces:
   - For each section, walk the prose for numeric tokens and strong-claim verbs.
   - Cross-check each match against the section's `*.plan.md` and `evidence.jsonl`.
   - Flag any claim without an evidence id.
8. **Number-source audit.**
   - Every number in tables should come from `.evidraft/experiments/result_analysis.md` (or an evidence record).
   - Numbers that don't match the source row flagged as `MISMATCH`.
9. **Consistency audit (semantic).** Delegate to `role-mode:consistency-checker`:
   - Builds terminology + numeric ground-truth maps from `.evidraft/code/method_to_code.md` and `.evidraft/experiments/result_analysis.md`.
   - Sweeps `manuscript/main.tex` and `manuscript/sections/*.tex` in narrative order and applies the 9 rules (TERM_DRIFT, NUMBER_DRIFT, ABBREVIATION_ORDER, SYMBOL_NOTATION_DRIFT, VOICE_DRIFT, TENSE_DRIFT, CLAIM_VS_RESULT_MISMATCH, SECTION_ORDER_VS_FLOW, DATASET_NAME_NORMALISATION).
   - Writes structured findings to `.evidraft/manuscript/consistency_audit-<ts>.findings.json` plus a paired `.log`.
   - `NUMBER_DRIFT` and `CLAIM_VS_RESULT_MISMATCH` are `fail`-severity and feed the "Numbers" / "Claim-evidence" blocks below; treat any `fail` finding as a `MISMATCH` for the overall verdict.

## Output

Write `.evidraft/manuscript/paper_check_report.md`:

```
# Paper check report

Generated: <iso datetime>
Manuscript: manuscript/main.tex

## Citation
- Missing keys: ...
- Unused keys: ...
- Strong claims without citation: ...

## LaTeX
- Compile: PASS / FAIL / SKIPPED
- Errors: ...
- Warnings: ...

## Style
- Fail: ...
- Warn: ...
- Info: ...

## Bib quality
- Required-field failures: ...
- Year / venue / DOI / URL issues: ...
- Cross-entry consistency: ...
- Coverage (evidence ↔ bib ↔ manuscript): ...

## Cross-references
- Duplicated / orphaned / mis-placed labels: ...
- Broken \ref / \eqref / \cite: ...
- Style drift (autoref, prefix convention): ...

## Figures & tables
- Unreached figures: ...
- Missing captions/labels: ...

## Claim-evidence
- Claims without evidence: ...

## Numbers
- Numbers without source: ...
- Mismatches (cross-section drift, vs result_analysis): ...

## Consistency
- TERM_DRIFT / ABBREVIATION_ORDER / SYMBOL_NOTATION_DRIFT / VOICE_DRIFT / TENSE_DRIFT: ...
- SECTION_ORDER_VS_FLOW / DATASET_NAME_NORMALISATION: ...

Overall verdict: PASS | WARN | FAIL
```

## Constraints

- Read-only: do not silently fix issues here. If a fix is obvious, recommend it, do not apply it.
- All audit artefacts share the same `run_id` so they can be cross-referenced.
- Each audit step is independent enough to run concurrently EXCEPT: Step 3 (style) and Step 5 (xref) require Step 2 (compile) to have written `compile-<ts>.errors.json`; Step 4 (bib quality) requires Step 1 (cite mechanics).

## Done criteria

- Report file exists and ends with an overall verdict line: `PASS` / `WARN` / `FAIL`.
- Chat output prints the verdict and counts per section (9 sections — Citation, LaTeX, Style, Bib quality, Cross-references, Figures & tables, Claim-evidence, Numbers, Consistency).
