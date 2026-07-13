---
id: paper-explanation
title: Evidence-grounded single-paper explanation
kind: skill
phase: shared
description: >
  Read one paper at full-text level, explain it at beginner, graduate, or
  reviewer depth, and produce a durable academic note with mandatory verified
  similar, subsequent, and newest-found related methods.
triggers:
  - "workflow:research.explain"
  - "explain this paper"
  - "close-read this paper"
  - "explain the equations in this paper"
provides:
  - paper-source-resolution
  - three-mode-explanation
  - evidence-labelled-note-schema
  - mandatory-related-method-landscape
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
policies: [workspace-safety]
references:
  - doc: capability:scholar-search
---

# paper-explanation

## Source resolution

1. Accept a local PDF path, arXiv URL or identifier, DOI, or paper URL.
2. Resolve one unique source paper before analysis. If the source cannot be
   uniquely identified, stop and request a more precise identifier.
3. Verify title, authors, year, venue, canonical URL, and the paper's research
   problem against the source or a canonical record.
4. Obtain readable full text and map its sections, equations, figures, and
   tables. A source-paper abstract alone cannot satisfy this requirement.

## Mode contract

All modes produce the same required sections and external research. They vary
only in emphasis:

- `beginner`: prioritises terminology, intuition, prerequisites, and careful
  analogies; equations remain present but are explained conceptually.
- `graduate`: balances equation-level explanation, method mechanics,
  experiments, limitations, and reproduction guidance.
- `reviewer`: prioritises assumptions, novelty boundaries, experimental
  validity, missing controls, statistical support, and overclaiming risk.

Use `graduate` when no mode is supplied. Do not drop a required note section or
mandatory external research for any mode.

## Required note schema

Every completed note contains these sections:

1. Paper identity and one-sentence takeaway
2. Research problem and background
3. Core contributions
4. Method walkthrough
5. Key equations and symbol-by-symbol explanations
6. Experimental setup and results
7. Limitations, failure modes, and conclusion boundaries
8. Reproduction notes
9. Similar methods
10. Subsequent improvements and latest related methods
11. Learning-check questions
12. Sources and verification record

For every explained key equation, define each symbol and label any derivation
or analogy that is not stated by the authors.

## Evidence labels

Technical statements use explicit evidence labels:

- `[Paper section 3.2]`, `[Equation 4]`, `[Figure 2]`, or `[Table 1]` for
  source-paper evidence;
- `[External: citation]` for a verified related paper;
- `[External: official-code]` for an official repository or project page;
- `[Interpretation]` for the explainer's derivation, analogy, or assessment;
- `[abstract-only]` when only a verified abstract was available.

An abstract-only external source may support bibliographic facts and claims
stated in its abstract. It must not support claims about unobserved equations,
experiments, implementation details, figures, or tables. Interpretations must
not be presented as author claims.

## Mandatory external research

External research cannot be disabled. It searches for:

- cited or contemporary methods similar to the source paper;
- work that directly extends, improves, applies, or criticises the source;
- the newest verified related methods found as of the execution date; and
- official code, project pages, and author material when available.

The external landscape must contain, when enough verified candidates exist:

- three to five similar or contemporary methods; and
- three to five subsequent, improved, or latest related methods.

Fewer entries are acceptable only when the note records the queries, providers,
cutoff date, and rejection reasons showing that the target count could not be
met without weakening verification.

Each included external work records title, year, canonical link, relationship
to the source paper, and a concrete methodological difference.

Preferred sources are the paper full text, DOI or publisher records, arXiv,
official project pages, and official repositories. Search results are candidate
discovery only; a canonical page must be opened and checked before inclusion.
The note records the search cutoff date and scope and uses wording such as
"newest verified methods found in this search," not an unqualified "latest" or
"state of the art."

## Collision protocol

An existing non-empty output file is never overwritten silently. The action
offers:

- `reuse`: keep the existing note and stop;
- `augment`: write a dated sibling note containing a refreshed external
  landscape while preserving the original; or
- `overwrite`: replace the file only after explicit user confirmation.

`augment` is the default recommendation when the user asks for newer related
methods. If the derived sibling path exists, append a numeric suffix until it
is unique.

## Failure contract

- If the source paper cannot be uniquely identified, stop and request a more
  precise identifier.
- If readable full text is unavailable, do not produce a completed explanation
  from the abstract. Report recovery options instead.
- If a PDF lacks a usable text layer or equation extraction is materially
  broken, request a readable copy. An OCR-derived draft is allowed only when
  clearly marked incomplete and must not satisfy the action's done criteria.
- If mandatory external retrieval is unavailable, preserve any explicitly
  marked temporary work but report the action as incomplete.
- Reject an external candidate whose title and authorship cannot be verified
  against a canonical source.
- Never fabricate a section, equation, figure, table, paper, author, date,
  venue, DOI, result, or URL.

## Completion checklist

- Confirm the source identity and readable full text are verified.
- Confirm all twelve required note headings are present.
- Confirm technical statements carry the correct evidence labels.
- Confirm every explained key equation defines its symbols.
- Confirm three to five verified similar methods and three to five verified
  subsequent, improved, or newest-found methods are included, or evidence the
  shortfall with queries, providers, cutoff date, and rejection reasons.
- Confirm every included external work has a title, year, canonical link,
  relationship, and concrete methodological difference.
- Confirm the search cutoff date and scope are recorded without an absolute
  state-of-the-art claim.
- Confirm collision handling preserved every non-empty existing note unless
  overwrite was explicitly approved.
- Report incomplete when readable source full text or mandatory external
  retrieval is unavailable.
