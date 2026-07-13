# workflow:research.explain

Load the private [paper-explanation](../../../capabilities/research/paper-explanation/spec.md)
and [scholar-search](../../../capabilities/research/scholar-search/spec.md) specs before
starting. They define the source, evidence, external-retrieval, collision, and failure
contracts for this stage.

## Phase 1: Resolve source and output

1. Classify `source` as a local PDF path, arXiv identifier or URL, DOI, or paper URL.
   Resolve exactly one paper and verify its title, authors, year, venue, canonical URL,
   and research problem against the source or a canonical record. Stop and request a
   more precise identifier when the identity is ambiguous.
2. Obtain readable full text and verify that its sections, equations, figures, and
   tables can be inspected. An abstract alone is not full text. If a PDF has no usable
   text layer or materially broken equation extraction, request a readable copy; any
   explicitly requested OCR draft remains incomplete.
3. Select `mode`, defaulting to `graduate`. Derive `<paper-slug>` from the verified title
   as deterministic ASCII: transliterate when possible, lowercase, replace each run of
   non-alphanumeric characters with one hyphen, trim hyphens, and fall back to a verified
   paper identifier if the title yields no characters. Resolve `out` or the default
   `.evidraft/notes/paper-explanations/<paper-slug>.md` to a concrete relative path.
4. If that path is a non-empty existing note, resolve one choice before writing:
   `reuse` keeps it and stops; `augment` preserves it and selects a unique dated sibling
   (adding a numeric suffix on collision); `overwrite` requires explicit user
   confirmation. Recommend `augment` for refreshed related-work requests.
5. Run `evidraft workflow preflight research.explain --target <resolved-output>` with the
   final concrete collision-safe path. Never pass an unresolved placeholder.

## Phase 2: Map the source paper

Build a source map from the readable full text before drafting. Record the paper's
section structure, research question, prerequisites, contributions, assumptions,
method steps, key equations and every symbol, figures, tables, datasets, baselines,
metrics, ablations, results, limitations, conclusion boundaries, implementation
details, and reproduction gaps. Tie each technical claim to its precise source-paper
location and distinguish author statements from explainer interpretation.

## Phase 3: Run bounded analysis work streams

1. Resolve and share the verified paper identity, full-text location, selected mode,
   concrete output path, and collision decision before dispatch.
2. Assign full-text source mapping, equation analysis, and final synthesis to the
   `paper-explainer` deep role.
3. Assign mandatory related-work retrieval to the `literature-reviewer` standard role.
   It must use the `scholar-search` capability to find cited or contemporary similar
   methods; subsequent, improved, applied, or critical work; newest verified related
   methods found as of the execution date; and official code or project material.
4. Once shared metadata is resolved, the two bounded work streams may run in parallel.
   Workers return structured analysis and verified evidence. Only `paper-explainer`
   may write the final note; neither worker may race on or create competing versions of
   the final file.
5. Open a canonical source for every included external candidate and verify title and
   authorship. Reject candidates that cannot be verified. Retain each query, provider,
   cutoff date, rejection reason, and the evidence scope of any abstract-only result.

## Phase 4: Synthesize the academic note

The `paper-explainer` writes exactly one Markdown note at the resolved output path using
all twelve headings below, in this order:

```markdown
## 1. Paper identity and one-sentence takeaway
## 2. Research problem and background
## 3. Core contributions
## 4. Method walkthrough
## 5. Key equations and symbol-by-symbol explanations
## 6. Experimental setup and results
## 7. Limitations, failure modes, and conclusion boundaries
## 8. Reproduction notes
## 9. Similar methods
## 10. Subsequent improvements and latest related methods
## 11. Learning-check questions
## 12. Sources and verification record
```

Use all applicable evidence labels exactly: `[Paper section 3.2]`, `[Equation 4]`,
`[Figure 2]`, and `[Table 1]` for source-paper evidence; `[External: citation]` for a
verified related paper; `[External: official-code]` for an official repository or
project page; `[Interpretation]` for a derivation, analogy, or assessment; and
`[abstract-only]` when only a verified external abstract was available. Define every
symbol in each explained key equation. Never use abstract-only evidence for unobserved
equations, experiments, implementation details, figures, or tables.

Include three to five verified similar or contemporary methods and three to five
verified subsequent, improved, or newest-found related methods when enough candidates
exist. For every included work record title, year, canonical link, relationship to the
source, and a concrete methodological difference. If either target cannot be met,
preserve the shortfall rather than weakening verification. Section 12 records all
queries, providers, search scope, execution-date cutoff, included counts, rejected
count, and each rejection reason. Describe results as the "newest verified methods found
in this search", never as an absolute latest method or state of the art.

Apply the selected-mode emphasis without removing any heading or external research:

- `beginner`: emphasize terminology, intuition, prerequisites, and careful analogies;
  retain equations and explain them conceptually.
- `graduate`: balance equation-level reasoning, method mechanics, experiments,
  limitations, and reproduction guidance.
- `reviewer`: emphasize assumptions, novelty boundaries, experimental validity,
  missing controls, statistical support, and overclaiming risk.

## Phase 5: Validate and report

Validate the source identity, readable-full-text status, twelve headings, evidence
labels, equation symbol definitions, related-work verification and target counts,
search metadata, and collision decision. Report the concrete output path, selected
mode, full-text status, search cutoff, similar-method included count,
subsequent/improved/newest-found included count, and rejected count. If source full text
or mandatory external retrieval failed, report the action as incomplete and provide
recovery options; do not claim a completed explanation even if temporary work exists.

## Constraints

- Produce one Markdown output only. Do not modify BibTeX, evidence records, manuscript
  files, project status, or a non-empty existing note without confirmed overwrite.
- Never fabricate paper identity, metadata, section labels, equations, figures, tables,
  results, external works, authors, dates, venues, DOIs, code, or URLs.
- Do not present `[Interpretation]` as an author claim or discovery-only search results
  as verified evidence.
- Mandatory external research cannot be disabled, and its cutoff cannot be omitted.
- Keep dispatch bounded to the two declared roles and keep final-file ownership with
  `paper-explainer`.

## Done criteria

- Source identity and readable full text are verified.
- The collision-safe concrete output passed preflight and exactly one note was written.
- All twelve headings, applicable evidence labels, and symbol-by-symbol key-equation
  explanations are present with the selected-mode emphasis.
- Three to five verified similar methods and three to five verified subsequent,
  improved, or newest-found methods are included, or the evidenced shortfall records
  queries, providers, cutoff, and rejection reasons.
- Every included external work has a title, year, canonical link, relationship, and
  concrete methodological difference.
- The final report states path, mode, full-text status, cutoff, both included counts,
  rejected count, and an accurate complete or incomplete status.
