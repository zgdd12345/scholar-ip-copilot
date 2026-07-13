# Paper Explanation Workflow Design

**Date:** 2026-07-13  
**Status:** Approved for implementation planning  
**Public action:** `workflow:research.explain`

## Purpose

Add a durable, evidence-grounded single-paper explanation workflow. A user can
ask `workflow:using.run` to analyse a named paper or provide a local PDF, arXiv
identifier, DOI, or paper URL. The router identifies the single-paper intent,
asks for confirmation, and hands off to `workflow:research.explain`. The action
writes an academic reading note rather than returning only a chat explanation.

The note explains the source paper and always places it in a verified research
landscape containing similar methods, subsequent work, and methods that are
current as of the recorded search date.

## Goals

- Expose paper explanation as a native `research` action on every supported
  host.
- Accept a local PDF path, arXiv URL or identifier, DOI, or paper URL.
- Generate one persistent Markdown reading note without requiring project
  initialisation or an approved scope.
- Support `beginner`, `graduate`, and `reviewer` explanation modes, defaulting
  to `graduate`.
- Ground statements in the source paper or clearly identified external
  sources.
- Make external research mandatory, including similar methods and the latest
  verified related methods.
- Route unambiguous single-paper analysis requests from `workflow:using.run`.

## Non-goals

- Drafting a manuscript section or modifying `manuscript/`.
- Creating or updating `references.bib`, `evidence.jsonl`, or project status.
- Replacing `workflow:research.deep`, which remains the systematic multi-paper
  review path.
- Claiming an absolute state of the art. The note reports the newest methods
  found within a dated and documented search scope.
- Producing a complete note from an abstract when full text cannot be read.

## Public Contract

The public invocation is:

```text
workflow:research.explain <source> [--mode beginner|graduate|reviewer] [--out PATH]
```

Host renderers expose the action through their existing research workflow
entrypoint, for example `$scholar-research explain` on Codex.

Inputs:

| Input | Type | Required | Default | Meaning |
|---|---|---:|---|---|
| `source` | string/path | yes | none | Local PDF, arXiv ID/URL, DOI, or paper URL |
| `mode` | enum | no | `graduate` | Explanation depth and emphasis |
| `out` | path | no | derived | Override the Markdown output path |

The default output is:

```text
.evidraft/notes/paper-explanations/<paper-slug>.md
```

This action has no `scope` precondition. Its only normal persistent artefact is
the Markdown note and, when necessary, its parent directory.

## Routing From `using`

`workflow:using.run` recommends `workflow:research.explain` when the request:

- supplies a PDF, DOI, arXiv ID, or paper URL and asks for analysis,
  explanation, close reading, formula explanation, or critique;
- names one uniquely identifiable paper and requests analysis; or
- uses equivalent Chinese intents such as paper explanation, close reading,
  formula analysis, or academic reading notes.

The router remains read-only and asks for confirmation before invoking the
recommended action.

Ambiguous names are not silently resolved. If a phrase might name a method,
project, research direction, or several papers, the router searches for or
asks for a specific paper. Requests about an entire research direction route
to `workflow:research.deep`, not `research.explain`.

## Processing Flow

1. Resolve and validate the source.
2. Read enough metadata to identify title, authors, year, venue, canonical URL,
   and the paper's research problem.
3. Obtain readable full text and identify sections, equations, figures, and
   tables.
4. After metadata and topic resolution, run two bounded work streams:
   - source-paper close reading and formula/experiment analysis;
   - external retrieval and verification of related methods.
5. Combine both work streams while preserving source labels.
6. Validate the required note sections and evidence boundaries.
7. Resolve any output collision and write the Markdown note.
8. Report the path, mode, source status, external search cutoff, and related
   work counts.

Where the host supports delegated roles, the two work streams may run in
parallel after source identity is established. They must not write competing
versions of the output file.

## Explanation Modes

All modes produce the same required sections and external research. They vary
only in emphasis:

- `beginner`: prioritises terminology, intuition, prerequisites, and careful
  analogies; equations remain present but are explained conceptually.
- `graduate`: balances equation-level explanation, method mechanics,
  experiments, limitations, and reproduction guidance.
- `reviewer`: prioritises assumptions, novelty boundaries, experimental
  validity, missing controls, statistical support, and overclaiming risk.

## Required Note Structure

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

The external landscape must contain, when enough verified candidates exist:

- three to five similar or contemporary methods; and
- three to five subsequent, improved, or latest related methods.

Fewer entries are acceptable only when the note records the queries, providers,
cutoff date, and rejection reasons showing that the target count could not be
met without weakening verification.

Each included external work records title, year, canonical link, relationship
to the source paper, and a concrete methodological difference.

## Evidence Labels

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

## Mandatory External Research

External research cannot be disabled. It searches for:

- cited or contemporary methods similar to the source paper;
- work that directly extends, improves, applies, or criticises the source;
- the newest verified related methods found as of the execution date; and
- official code, project pages, and author material when available.

Preferred sources are the paper full text, DOI or publisher records, arXiv,
official project pages, and official repositories. Search results are candidate
discovery only; a canonical page must be opened and checked before inclusion.
The note records the search cutoff date and scope and uses wording such as
"newest verified methods found in this search," not an unqualified "latest" or
"state of the art."

## Failure Behaviour

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

## Output Collision Behaviour

An existing non-empty output file is never overwritten silently. The action
offers:

- `reuse`: keep the existing note and stop;
- `augment`: write a dated sibling note containing a refreshed external
  landscape while preserving the original; or
- `overwrite`: replace the file only after explicit user confirmation.

`augment` is the default recommendation when the user asks for newer related
methods. If the derived sibling path exists, append a numeric suffix until it
is unique.

## Internal Components

- `workflow:research.explain` owns the public contract and executable stage.
- `capability:paper-explanation` owns source handling, mode semantics, the note
  schema, evidence labels, and completion checks.
- A new `paper-explainer` researcher mode owns source-paper analysis and final
  synthesis.
- Existing `capability:scholar-search` and the `literature-reviewer` mode own
  candidate discovery and external-work verification.
- `workflow:using.run` owns intent detection and confirmation, not explanation.

The new researcher mode is registered in the shared role registry so renderer
validation can map it consistently across Claude Code, Codex, and OpenCode.

## Test Strategy

Implementation follows strict Red-Green-Refactor. Tests are added before each
production contract change and are observed failing for the missing behaviour.

Focused contract tests cover:

- the public manifest exposes `research.explain`;
- the workflow action declares `source`, the three mode values, optional
  `out`, the default output, and its role assignments;
- the `paper-explainer` role is registered at one valid tier;
- the stage requires every note section, evidence labels, mandatory external
  research, target related-work counts, collision handling, and failure rules;
- `using` documents unambiguous, ambiguous, and research-direction routing;
- all three host renderers expose the action and include its capability bundle;
- the frozen v1-to-v2 migration fixture remains unchanged, while tests allow
  new native v2 actions that have no legacy command predecessor.

After focused tests pass, verification runs the full test suite, lint, plugin
schema validation, renderer generation or consistency tests, and a final diff
review for unintended changes or sensitive data.

## Acceptance Criteria

- A user can ask `workflow:using.run` to analyse one identifiable paper and is
  routed, after confirmation, to `workflow:research.explain`.
- The action accepts every declared source form and defaults to `graduate`.
- A successful run writes one complete academic Markdown reading note under
  the default directory or explicit `out` path.
- The note separates source-paper evidence, external evidence, abstract-only
  evidence, and interpretation.
- Similar methods and newer related methods are mandatory and verified; search
  scope and cutoff date are recorded.
- Missing full text or unavailable external retrieval prevents a completion
  claim.
- Existing notes are preserved unless overwrite is explicitly selected.
- Claude Code, Codex, and OpenCode render and expose the same action contract.
