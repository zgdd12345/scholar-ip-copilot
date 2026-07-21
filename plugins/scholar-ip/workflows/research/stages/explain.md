# workflow:research.explain

Load the private [paper-explanation](../../../capabilities/research/paper-explanation/spec.md)
spec. Load [scholar-search](../../../capabilities/research/scholar-search/spec.md) only
when the conditional external-comparison branch is selected.

## 1. Resolve the source and destination

1. Classify `source` before opening it. For a local PDF, run
   `evidraft workflow preflight research.explain --read-target <source>` before reading
   it. Resolve DOI, arXiv, and web identifiers through their canonical remote source.
2. Resolve exactly one paper and verify title, authors, year, venue, canonical URL, and
   research problem. Ask for a more precise identifier if identity is ambiguous.
3. Try to obtain readable full text. Record unreadable equations, figures, tables,
   appendices, or extraction defects as gaps; an abstract is not a substitute for full
   text. When full text is unavailable, write a limited evidence-boundary note from
   verified identity and any canonical abstract instead of refusing the whole action.
4. Default `mode` to `graduate`. Derive a deterministic ASCII paper slug and resolve
   `out` or `.evidraft/notes/paper-explanations/<paper-slug>.md`.
5. Never overwrite a non-empty note silently. Offer `reuse`, a collision-safe dated
   sibling, or explicitly confirmed replacement. Immediately before the single final
   write, re-check the path and repeat this decision if it became non-empty.
6. Run `evidraft workflow prepare-output research.explain --target <resolved-output>`
   only after the concrete collision-safe path is known.

## 2. Explain adaptively

Build a best-effort explanation from the readable source portions. Cover the paper identity and
takeaway, problem and prerequisites, contributions, method, key equations and symbols,
experiments and results, limitations and claim boundaries, reproduction notes, and a
verification record. Apply mode as emphasis:

- `beginner`: terminology, intuition, prerequisites, and careful analogies;
- `graduate`: method mechanics, equations, experiments, and reproduction guidance;
- `reviewer`: assumptions, novelty boundaries, missing controls, validity, statistical
  support, and overclaiming risk.

Use `[Paper section ...]`, `[Equation ...]`, `[Figure ...]`, and `[Table ...]` for
source evidence and `[Interpretation]` for reasoning not stated by the authors. Preserve
uncertainty instead of filling unreadable or absent details.

If full text is unavailable, write a limited evidence-boundary note. Include verified
bibliographic identity, the exact source material that was readable, an `## Evidence
boundary` section, unsupported requested sections, and a concrete recovery action. Do
not infer unseen methods, equations, figures, tables, or results. This note has status
`complete_with_gaps`; it is not presented as a full-paper explanation.

The coordinator may explain directly or delegate bounded independent checks when doing
so improves quality and the host supports it. Delegation has no fixed cardinality,
dependency waves, or retry count. A failed optional check becomes a reported gap; it
does not force the whole explanation to stop. Only `paper-explainer` owns the resolved
destination and performs the single final write.

## 3. Expand related research conditionally

Expand beyond the source paper only in reviewer mode or the user explicitly requests
comparison, similar methods, subsequent work, improvements, or current alternatives.
Ordinary beginner and graduate explanations do not require external research.

For the expansion branch, use the reusable `literature-reviewer` and `scholar-search`
contracts. Open a canonical source for every included work, verify title and authorship,
record the search date and scope, distinguish abstract-only evidence, and state a
concrete relationship to the source paper. Search-result snippets are discovery only.
External shortfalls remain visible and never invalidate a useful source-paper analysis.

## 4. Write and report status

Write at most one Markdown note. Include related-method sections only when the external
branch ran. End the note and chat report with exactly one status:

- `complete`: the requested explanation was written from readable source evidence with
  no material requested coverage missing;
- `complete_with_gaps`: a useful note was written, but unreadable source material,
  unavailable optional checks, or requested external comparison left named gaps;
- `blocked`: the paper cannot be identified or a safe collision-free destination cannot
  be prepared, so no note is written.

For `complete_with_gaps`, name missing coverage and a concrete recovery action. For
`blocked`, report why identity or safe writing could not be established. Blocked is
limited to unresolved paper identity or an unsafe output destination. Report the mode, verified
source identity, concrete output path when written, whether external comparison ran,
and final status.

## Constraints

- Produce at most one Markdown note; do not modify BibTeX, evidence records,
  manuscripts, or project status.
- Never invent a paper, author, date, venue, URL, equation, symbol, result, locator, or
  external relationship.
- Do not claim comprehensive or newest coverage unless the performed search supports
  that bounded statement.

## Done criteria

- Source identity and full-text availability were checked; missing full text produced an
  explicit evidence-boundary note rather than invented detail.
- The note clearly separates paper evidence, interpretation, and any external evidence.
- Every explained equation defines its symbols or names the extraction gap.
- Existing non-empty notes were preserved unless replacement was explicitly confirmed.
- The report uses `complete`, `complete_with_gaps`, or `blocked` accurately.
