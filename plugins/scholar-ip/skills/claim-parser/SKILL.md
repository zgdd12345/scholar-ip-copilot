---
id: claim-parser
title: "Claim parser: structural parse of claims.md into JSON + antecedent-basis audit"
kind: skill
phase: patent
description: >
  Parses `.evidraft/patent/claims.md` (the output of `/scholar:patent-claims`)
  into a structured JSON form so downstream skills (`claim-chart-builder`,
  `novelty-heuristics`) and the multi-role review never have to re-tokenise
  free-text claims. Extracts preamble, transition, labelled elements, and the
  independent/dependent dependency graph; runs an antecedent-basis sweep and
  emits a small taxonomy of structural warnings. Advisory only —
  attorney-reviewable, not legal advice.
triggers:
  - "command:/scholar:patent-claims"
  - "command:/scholar:patent-review"
  - "subagent:claim-drafter"
provides:
  - structured-claim-form
  - antecedent-basis-chain
  - element-labelling
  - independent-dependent-graph
  - claim-parse-warning-taxonomy
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:grep*"
  - "Bash:awk*"
hooks: [evidence-consistency]
references:
  - doc: ../../agents/claim-drafter.md
  - doc: ../../commands/patent-claims.md
  - doc: ../../commands/patent-review.md
  - doc: ../../../../docs/legal-and-ethics.md
---

# claim-parser

## 1. When to use

Runs whenever `.evidraft/patent/claims.md` is (re)written or re-read:

- as a sub-pass of `/scholar:patent-claims` immediately after `claim-drafter` writes the file, so the rest of the pipeline can read JSON instead of prose;
- as a sub-pass of `/scholar:patent-review`, so the `claim drafter` reviewer role and the `novelty critic` role share the same structural view;
- on demand from the `claim-drafter` subagent itself, between drafts, to verify its own antecedent basis before publishing.

The skill is **observational**. It never rewrites `claims.md`. Downstream skills (`claim-chart-builder`, `novelty-heuristics`) consume the JSON and trust that the surface form in `claims.md` is authoritative.

Skip the run if `claims.md` does not exist; emit a single chat line and exit cleanly (this is the normal case before `/scholar:patent-claims` has ever produced output).

## 2. Inputs

- `.evidraft/patent/claims.md` — markdown with `# Draft claims (for attorney review)` H1, then per-claim `## Claim N (independent)` / `## Claim N (dependent on M)` H2 sections, each followed by a numbered claim with bracketed `[a]` / `[b]` / ... body elements, terminated by the mandatory attorney-review footer.
- (optional) `.evidraft/patent/invention_disclosure.md` — used **only** by `TERMINOLOGY_DRIFT` (§5) to resolve a claim noun back to its specification form. If absent, `TERMINOLOGY_DRIFT` is silently skipped (no false positives).

No other file is read. No file is written outside `.evidraft/patent/`.

## 3. Outputs

Two files per run, both under `.evidraft/patent/`:

- `.evidraft/patent/claims_parsed.json` — canonical structured view of the **current** `claims.md`. **Not** timestamped: downstream skills always read the latest. Overwritten on every run.
- `.evidraft/patent/claim_parse-<ts>.log` — timestamped human-readable trace (one line per parsed claim element, plus one line per warning). `<ts>` is UTC iso-basic (`20260518T143000Z`), matching the convention used by `latex-style-audit` and `bib-audit`.

When called from a command with a `run_id` in its `plan.yaml`, embed it at the top level of `claims_parsed.json`.

### 3.1 Schema of `claims_parsed.json`

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "claims_md_path": ".evidraft/patent/claims.md",
  "claims": [
    {
      "id": "c1",
      "number": 1,
      "kind": "independent",
      "depends_on": null,
      "preamble": "A method comprising:",
      "transition": "comprising",
      "elements": [
        {
          "label": "a",
          "text": "obtaining a query and a set of candidate documents;",
          "antecedents_introduced": ["query", "set of candidate documents"],
          "antecedents_referenced": []
        },
        {
          "label": "b",
          "text": "the query being preprocessed by a tokenizer;",
          "antecedents_introduced": ["tokenizer"],
          "antecedents_referenced": ["query"]
        }
      ],
      "terminus": "."
    },
    {
      "id": "c2",
      "number": 2,
      "kind": "dependent",
      "depends_on": "c1",
      "preamble": "The method of claim 1,",
      "transition": null,
      "elements": [
        {
          "label": "a",
          "text": "wherein the tokenizer is a BPE tokenizer.",
          "antecedents_introduced": [],
          "antecedents_referenced": ["tokenizer"]
        }
      ],
      "terminus": "."
    }
  ],
  "antecedent_chain": {
    "query": ["c1[a]"],
    "set of candidate documents": ["c1[a]"],
    "tokenizer": ["c1[b]", "c2[a]"]
  },
  "warnings": [
    {
      "rule_id": "ANTECEDENT_MISSING",
      "severity": "warn",
      "claim": "c3",
      "element": "b",
      "noun": "the index",
      "explanation": "Definite article references a noun not introduced earlier in c3 or in c1 (its parent)."
    }
  ],
  "summary": {
    "independent_count": 1,
    "dependent_count": 1,
    "warning_count": 0,
    "fail_count": 0
  }
}
```

Field rules:

- `id` is always `c<number>` (lowercase `c`, no padding).
- `kind` ∈ `{independent, dependent}`.
- `depends_on` is `c<M>` for dependents, `null` for independents.
- `transition` is one of `comprising` / `consisting of` / `consisting essentially of` for independents; **may be `null`** on a dependent that inherits the parent's transition (the typical `The method of claim N, wherein ...` form).
- `terminus` MUST be `.` — anything else triggers `MISSING_TERMINUS` (fail) and the literal char is still recorded for the trace.
- `antecedent_chain` keys are the canonical lowercase noun-phrase form; values are the ordered list of `c<N>[<label>]` sites that **introduce or reference** the noun (introductions come first).
- `summary.warning_count` counts `severity in {info, warn}`; `summary.fail_count` counts `severity == fail`. These two together equal `len(warnings)`.

## 4. Parse procedure

### 4.1 Read `claims.md`

```
Read .evidraft/patent/claims.md
```

If the file is missing, print `claim-parser: no claims.md (skip)` and exit. Otherwise continue.

### 4.2 Split into H2 claim sections

Match the H2 header regex:

```
^## Claim (\d+) \((independent|dependent on (\d+))\)\s*$
```

Everything before the first matching H2 (the H1 `# Draft claims (for attorney review)` and any preamble paragraph) is discarded. Everything **after** the last claim's terminating period up to the mandatory `> Draft claims. ... attorney ...` blockquote footer is discarded. The footer itself is **not** part of any claim.

For each H2 section, capture:

- `number` = the integer in group 1,
- `kind` = `independent` if group 2 == `independent`, else `dependent`,
- `depends_on` = `c<group 3>` if dependent, else `null`.

### 4.3 Per-claim body parse

Within each H2 section's body:

1. **Preamble.** First non-blank line is the numbered prose line (e.g. `1. A method comprising:` or `2. The method of claim 1, wherein:`). Strip the leading `<number>.` and surrounding whitespace; the result up to and including the line's trailing `:` is the `preamble`. If no `:` is found before the first labelled element, the preamble is the entire pre-element prose verbatim (and `TRANSITION_UNKNOWN` will fire in §5).
2. **Transition.** From the preamble, extract the word(s) immediately preceding the `:`. Validate against the enum `{comprising, consisting of, consisting essentially of}`. If the preamble has no `:` or the preceding word is not in the enum, set `transition = null` for dependents (which legitimately inherit) and emit `TRANSITION_UNKNOWN` (warn) for independents.
3. **Body elements.** A body-element line matches one of:
   ```
   ^\s+([a-z])\.\s+(.*)$         # `   a. text...`
   ^\s+([a-z])\)\s+(.*)$         # `   a) text...`
   ^\s+\[([a-z])\]\s+(.*)$       # `   [a] text...`
   ```
   `label` = group 1 (single lowercase letter). `text` = group 2 (trimmed). An element's text may continue on subsequent indented continuation lines until the next labelled element or the end of the claim block — concatenate with a single space.
4. **Terminus.** The last element's `text` must end with `.`. Record the actual trailing character as `terminus`; if it is not `.`, fire `MISSING_TERMINUS` (fail) but keep the element.
5. **Element-less claim.** If zero element matches fire inside an H2 block, fire `EMPTY_CLAIM` (fail) and emit a single element with `label = "a"`, `text = "<no body parsed>"` so downstream JSON shape stays consumable.

### 4.4 Antecedent-basis analysis

For each element, derive `antecedents_introduced` and `antecedents_referenced`:

1. **Definite-reference spotting** — assist with a Grep-style regex pre-pass:
   - `\bthe\s+([a-z][a-z0-9\- ]+?)\b(?=[\s,;.])` — matches `the X`,
   - `\bsaid\s+([a-z][a-z0-9\- ]+?)\b(?=[\s,;.])` — matches `said X` (older claim style).
   Each captured `X` is a candidate **reference**.
2. **Indefinite-introduction spotting** — pre-pass:
   - `\b(?:a|an)\s+([a-z][a-z0-9\- ]+?)\b(?=[\s,;.])` — matches `a X` / `an X`.
   Each captured `X` is a candidate **introduction**.
3. **Phrase trimming (LLM-driven).** The regex captures a greedy slice; trim trailing function words (`of`, `and`, `or`, `to`, `for`, `from`, `by`, `with`, prepositions in general) so `a set of candidate documents` is captured as one noun phrase, not split mid-prepositional-phrase. Use the surface of the disclosure (when available) as a tie-breaker: prefer the longest phrase that also appears in `invention_disclosure.md`.
4. **Canonicalisation.** Lowercase, collapse whitespace. The canonical form is the dictionary key for `antecedent_chain`.
5. **Per-claim resolution.** Walk the elements in order. For each `referenced` noun in element E:
   - if it was `introduced` in an earlier element of the **same** claim → ok, append `c<N>[<E.label>]` to its chain entry;
   - else if this is a dependent claim and the noun was introduced anywhere in the **parent chain** (transitively follow `depends_on`) → ok, append;
   - else → fire `ANTECEDENT_MISSING` (warn) with the missing surface form.
6. **Chain population.** Every introduction also appends `c<N>[<E.label>]` to the chain. The first entry in a chain key's list is by definition the **introduction site**; subsequent entries are references.

### 4.5 Dependency-graph validation

1. Every `depends_on` must reference a **strictly earlier** claim number — otherwise fire `FORWARD_DEPENDENCY` (fail) and leave `depends_on` populated for downstream debugging.
2. A preamble matching `The method of claim \d+ (or|and) claim \d+` (or more disjuncts) fires `MULTIPLE_DEPENDENCY` (warn). Set `depends_on` to the **first** referenced parent only; record the alternates in the warning row's `explanation`.
3. A dependent claim whose body has no `wherein` / `further comprising` / `further including` token fires `DEPENDENT_NO_NARROW` (warn).

### 4.6 Write artefacts

Overwrite `.evidraft/patent/claims_parsed.json` with the structured form (§3.1). Write a new `.evidraft/patent/claim_parse-<ts>.log` with one line per parsed element:

```
c<N>[<label>]  intro=<noun, noun, ...>  ref=<noun, ...>  text="..."
```

followed by one line per warning:

```
<severity>  <rule_id>  c<N>[<label>]  <one-line explanation>
```

and a trailing `summary: independent=<i> dependent=<d> warn=<w> fail=<f>` block.

### 4.7 Surface to chat

Print one summary line:

```
claim-parser: <i> indep / <d> dep / <w> warn / <f> fail  (.evidraft/patent/claim_parse-<ts>.log)
```

Return the JSON path to the caller. Do **not** dump the JSON to chat — the orchestrator renders it.

## 5. Warning taxonomy

All `rule_id`s are UPPER_SNAKE and stable across runs. Each row: rule_id, severity, detection recipe, example, explanation.

| rule_id | sev | detection | example | explanation |
|---|---|---|---|---|
| `ANTECEDENT_MISSING` | warn | a `the X` / `said X` reference whose canonicalised `X` has no prior `a X` / `an X` introduction in the same claim or in any parent (via `depends_on`) | c3[b] says `the index is updated` but neither c3 nor c1 (parent) ever introduced `an index` | definite-article references must trace back to an indefinite introduction; ambiguous antecedent risks 35 USC 112(b) indefiniteness. |
| `MULTIPLE_DEPENDENCY` | warn | preamble matches `claim \d+\s+(or\|and)\s+claim \d+` | `The method of claim 1 or claim 2, wherein ...` | multiple-dependent claims are disallowed or surcharged in some jurisdictions (e.g. USPTO); flag for attorney review even when locally legal. |
| `TRANSITION_UNKNOWN` | warn | transition extracted from preamble is non-null and not in `{comprising, consisting of, consisting essentially of}` | `A method including: a. ...` (`including` is not a recognised transition) | non-standard transitions create ambiguity about whether the claim is open, closed, or partially closed. |
| `DEPENDENT_NO_NARROW` | warn | `kind == dependent` and no element text contains `wherein` / `further comprising` / `further including` (case-insensitive) | `## Claim 2 (dependent on 1)` whose only element is `the method is implemented in Python.` | a dependent claim must actually narrow the parent; cosmetic dependents add prosecution cost without coverage benefit. |
| `MISSING_TERMINUS` | fail | last element's text does not end with `.` | `c. updating the index;` (semicolon instead of period) | a claim is a single sentence; non-period terminus is a parsing red flag and a formality defect. |
| `UNNUMBERED_ELEMENT` | fail | a non-blank, non-preamble line in a claim body that looks like an element (starts indented prose, ≥ 3 words) but does not match any of the `[a]` / `a.` / `a)` label forms | inside c1, the line `   updating the index;` with no leading label | every element must be labelled; an unnumbered element breaks `claim-chart-builder` row alignment. |
| `FORWARD_DEPENDENCY` | fail | `depends_on` refers to a claim number ≥ the current claim's number | `## Claim 3 (dependent on 5)` | a dependent claim cannot reference a later claim; either renumber or correct the parent reference. |
| `EMPTY_CLAIM` | fail | an H2 claim section contains zero body elements after preamble parsing | `## Claim 4 (independent)\n1. A method.` (no body) | a claim with no elements is not a claim; almost always a draft truncation. |
| `TERMINOLOGY_DRIFT` | info | the same conceptual noun appears under ≥ 2 surface forms across claims (e.g. `tokenizer` in c1 vs `token encoder` in c3), confirmed by both forms also appearing as the same concept in `invention_disclosure.md` (when available) | c1 uses `tokenizer`, c3 uses `token encoder` for the same component | claim terminology should be uniform; drift across claims invites construction disputes. Skipped (no false positive) when `invention_disclosure.md` is absent. |

**Total: 9 rule_ids.** Severity policy: `fail` only when the JSON shape or the formal claim shape is objectively broken (`MISSING_TERMINUS`, `UNNUMBERED_ELEMENT`, `FORWARD_DEPENDENCY`, `EMPTY_CLAIM`); `warn` for issues an attorney would flag in review (`ANTECEDENT_MISSING`, `MULTIPLE_DEPENDENCY`, `TRANSITION_UNKNOWN`, `DEPENDENT_NO_NARROW`); `info` for cross-claim hygiene (`TERMINOLOGY_DRIFT`).

## 6. Advisory-only framing

> The `claim-parser` skill performs **structural** parsing of claim text. It does not opine on patentability, claim scope, or legal validity. Parse warnings are advisory; they help an attorney spot issues earlier but are not a substitute for prosecution-grade review. A registered patent agent / attorney must review every output before any filing decision.

This paragraph is reproduced verbatim in every `claim_parse-<ts>.log` footer and must not be removed or paraphrased.

## 7. Anti-patterns

- **Rewriting claim text.** This skill parses and reports only. Edits to `claims.md` go through `claim-drafter` on a separate pass.
- **Inferring intent.** Do not write `"the inventor probably meant ..."` rows. Report the literal observation — `the index has no prior a index in c3 or c1` — and let a human decide.
- **Failing on legitimate but unusual formats.** Jepson claims (`A method, the improvement comprising ...`), product-by-process claims (`A product produced by the process of ...`), and means-plus-function claims (`means for ...ing`) are all valid; they get an INFO trace note in the `.log` but never a `fail` from this skill.
- **Reading outside `.evidraft/patent/`.** No bib, no manuscript, no code. The only optional input is `invention_disclosure.md` and only for `TERMINOLOGY_DRIFT`.
- **Timestamping `claims_parsed.json`.** It is the canonical current view; consumers always read the latest. The `.log` is the timestamped audit trail.
- **Inventing antecedents.** If a noun phrase is ambiguous (`the system` could mean half a dozen things), do **not** guess which earlier introduction it points to — fire `ANTECEDENT_MISSING` and let the attorney disambiguate.
- **Treating this as legal review.** See §6. Structural only.
