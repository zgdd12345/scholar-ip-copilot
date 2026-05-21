---
id: patent-claims
title: "Patent claim drafting discipline (advisory): anatomy, antecedent basis, claim chart"
kind: skill
phase: patent
description: >
  Load when /scholar:patent-claims or /scholar:patent-review run. Provides claim anatomy
  (preamble / transition / body elements), the antecedent-basis recipe,
  dependent-claim narrowness checklist, claim-chart construction
  (spec_support + code_support + prior_art + risk), 112(b)-style
  indefiniteness signals, and the jurisdiction note that claims drafted here
  are ADVISORY only (filed text remains the attorney's job).
triggers:
  - "/scholar:patent-claims"
  - "/scholar:patent-review"
  - "drafting claims.md"
  - "drafting claim_chart.md"
provides:
  - claim-anatomy
  - antecedent-basis-recipe
  - dependent-claim-checklist
  - claim-chart-construction
  - indefiniteness-signals
  - advisory-jurisdiction-note
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency]
references:
  - doc: ../../../../docs/legal-and-ethics.md
  - doc: ../patent-disclosure/SKILL.md
  - doc: ../evidence-check/SKILL.md
---

# patent-claims

## When to use

Load when drafting `.evidraft/patent/claims.md` and `.evidraft/patent/claim_chart.md`, or when running multi-role review on existing claims. The output is **advisory**: it helps an attorney see scope, evidence support, and prior-art overlap. It is **not** filed text; the attorney rewrites for the chosen jurisdiction.

## Inputs

- `.evidraft/patent/invention_disclosure.md` (must have §6 Technical solution and §7 Implementation details)
- `.evidraft/patent/invention_candidates.md`
- `.evidraft/patent/prior_art_map.md`
- `.evidraft/code/method_to_code.md`
- `.evidraft/evidence/evidence.jsonl`

## Outputs

- `.evidraft/patent/claims.md`
- `.evidraft/patent/claim_chart.md`

## Procedure

### 1. Claim anatomy

Every claim has three parts. Draft in this order.

**(1) Preamble.** Names the type of subject matter and sets context. Pick from:

- `A method comprising:` (method claim)
- `A system comprising:` (apparatus / system claim — when claiming hardware or software-as-component arrangement)
- `An apparatus, comprising:` (device claim)
- `A non-transitory computer-readable medium storing instructions that, when executed by one or more processors, cause the one or more processors to perform operations comprising:` (Beauregard-style — US-style software claim; in CN/EP the form differs, so the attorney will rewrite)

Rules:

- Preamble names the **statutory category**. Mixing categories ("a method and apparatus") in one claim is a defect.
- Match the noun used in §6 of the TID (`method`, `system`, `apparatus`). Do not introduce a new noun in the claim.

**(2) Transition.** One of:

- `comprising` — open-ended; allows additional unrecited elements. Default for breadth.
- `consisting of` — closed; excludes additional elements. Rare; only when you really mean it.
- `consisting essentially of` — middle ground; excludes elements that materially affect the basic and novel characteristics. Avoid in advisory drafts; attorney's call.

Use `comprising` unless there is a specific reason.

**(3) Body — elements.** A list of clauses, each a noun phrase (for system claims) or a step (for method claims). Each clause:

- starts with `a` / `an` on first mention of a structure or step;
- starts with `the` / `said` when referring back to a previously introduced element (antecedent basis — see §2);
- ends with `;` between elements and `.` after the last element;
- is labelled `[a]`, `[b]`, `[c]`, … in the advisory file (the attorney removes labels for filing).

Worked skeleton (method):

```
1. A method comprising:
   [a] receiving, by one or more processors, an input image x;
   [b] computing, from the input image, a feature map z via a backbone network;
   [c] partitioning the feature map z into a set of patches p_1, ..., p_n;
   [d] for each patch p_i, computing an attention-weighted summary using a set of learnable queries; and
   [e] producing an output prediction from the summaries.
```

### 2. Antecedent-basis recipe

Antecedent basis is the rule that every `the X` in a claim must refer back to an earlier `a X` (or `an X`) in the same claim or a claim it depends from. Violations are a top-tier indefiniteness defect under US 35 USC §112(b) and have similar effect under EP Art. 84.

Recipe:

1. First-mention rule. The first time a structural element or quantity appears, use `a` / `an`. ("…computing a feature map z…")
2. Subsequent-mention rule. Every later reference uses `the` (or `said`, but `said` is increasingly out of style — use `the`). ("…partitioning the feature map z…")
3. Sub-component rule. When introducing a sub-component of an already-introduced element, the sub-component itself is a new "a": "…the feature map comprising a set of channels…".
4. Plurality rule. When the first mention is plural ("a set of patches p_1, ..., p_n"), subsequent reference is "the set of patches" or "the patches".
5. Variable / index rule. Index variables (`i`, `n`) are introduced when used; if a later element references the same range, use "the" with the same identifier.
6. Reset rule. A new independent claim resets antecedent basis. Do not assume the reader carries antecedents across independent claims.
7. Dependent reset rule. A dependent claim inherits antecedents from the claim(s) it depends on, transitively.

Quick check before commit: for every `the X` in a claim, grep upward in the same claim (and in any claim it depends on) for `a X` or `an X`. No hit -> add the first mention or rewrite.

### 3. Dependent-claim narrowness checklist

A dependent claim must:

- [ ] Refer to exactly one earlier claim by number ("The method of claim 1, wherein …").
- [ ] **Narrow** the scope of the referenced claim. A dependent claim that does not narrow is malformed.
- [ ] Not contradict the parent claim's elements (e.g., parent says `comprising`, child cannot exclude an element the parent introduced).
- [ ] Be supported by the specification (TID §6 + §7) — verify with the claim chart.
- [ ] Address one narrowing axis at a time. Use multiple dependent claims for multiple narrowings rather than packing five constraints into one.

Common narrowing axes:

| Axis | Example wording |
|---|---|
| Component substitution | "…wherein the backbone network is a transformer encoder." |
| Hyperparameter range | "…wherein the number of patches n is between 196 and 1024." |
| Order constraint | "…wherein step [d] is performed before step [e]." |
| Output constraint | "…wherein the output prediction comprises a bounding box and a class label." |
| Operating condition | "…wherein the input image has a resolution of at least 224 by 224 pixels." |
| Combination | "…further comprising applying a learned projection to the attention-weighted summary before [e]." |

Dependent count: `/scholar:patent-claims` defaults to 6 dependent claims; pick the 6 strongest narrowings, do not pad.

### 4. Claim-chart construction

`.evidraft/patent/claim_chart.md` is one row per claim element (not per claim). Columns:

| Claim element | Specification support | Code support | Prior art overlap | Risk | Suggested revision |

- **Claim element**: identifier (`1[a]`, `1[b]`, …) and a short quote.
- **Specification support**: section reference into `invention_disclosure.md` (e.g., `§6 step 2`, `§7 paragraph 3`). Must be non-empty.
- **Code support**: one or more `ev_NNNN` (type=code) plus `file_path:lines`. Must be non-empty for advisory rows; mark `n/a` only with a one-line justification (e.g., "method step is data preprocessing handled outside the inventive system").
- **Prior art overlap**: reference id from `prior_art_map.md`, or `none flagged`. If multiple prior art hits, list all.
- **Risk** ∈ `{low, medium, high}`:
  - `low` — clear spec + code support, no prior-art overlap, language is structural.
  - `medium` — spec support present but code support partial, or one prior-art hit that does not fully overlap.
  - `high` — prior art reads on the element, or spec support is functional-only, or code support is absent.
- **Suggested revision**: if `Risk=high`, provide narrower phrasing that would survive the overlap. Otherwise empty.

Construction algorithm:

1. Decompose every independent claim into elements. Add one row per element.
2. For each row, fill Specification support by grep-ing `invention_disclosure.md` for the element's nouns and verbs.
3. For each row, fill Code support from `method_to_code.md`.
4. For each row, scan `prior_art_map.md` and flag overlap.
5. Assign Risk from the rules above.
6. For each `high` row, propose a revision and feed it back into a redraft of the claim.

End the chart with a counts line: `n low, n medium, n high`. A claim with any `high` row should be flagged in `claims.md` with a note.

### 5. 112(b)-style indefiniteness signals

Under US 35 USC §112(b) a claim must "particularly point out and distinctly claim the subject matter". EP Art. 84 imposes a similar clarity requirement. In an advisory draft, scan for these signals and rewrite before the attorney sees the file:

| Signal | Why it is indefinite | Fix |
|---|---|---|
| Antecedent-basis violation (`the X` without prior `a X`) | Reader cannot tell which X is meant. | Add first mention. |
| Relative terms without anchor (`about`, `substantially`, `approximately`) | Boundary unclear. | Specify a range or rewrite around a measurable threshold. |
| Subjective terms (`high-quality`, `user-friendly`, `efficient`) | No objective test. | Replace with a measurable property. |
| Functional-only without structure (`means for processing X` with no §7 disclosure) | In US, invokes 112(f) and the means is limited to disclosed structure plus equivalents — usually narrower than the drafter intended. | Provide structural language or cite §7 explicitly. |
| Negative limitation introduced only in the claim, not in spec | No support for what is excluded. | Add §8 alternative that names the excluded variant. |
| Plurality with mismatched cardinality (`a set of patches` … `the patch`) | Singular/plural mismatch. | Match cardinality. |
| Optional language in a claim (`preferably`, `may`, `optionally`) | Scope undefined. | Move to a dependent claim or remove. |
| Mixed categories (method + apparatus in one claim) | Statutory category unclear. | Split into two claims. |
| Reference to a figure or example by number ("as shown in Fig. 2") | Spec dependency in claim. | Reformulate in self-contained language. |

A claim with any indefiniteness signal is flagged in `claim_chart.md` row's "Suggested revision".

### 6. Advisory jurisdiction note

Claims drafted by this skill are **advisory** in every jurisdiction. The filed text — including category choice, transition phrase, dependency structure, and means-plus-function language — is the registered patent agent / attorney's responsibility. Specifically:

- US: 35 USC §§101, 102, 103, 112 apply; §112(f) means-plus-function interpretation is jurisdiction-specific.
- EP: Art. 52 (subject matter), Art. 54/56 (novelty / inventive step), Art. 83/84 (sufficiency / clarity) apply; two-part form (preamble + characterising portion) preferred.
- CN: 专利法 第二十二条 (新颖性 / 创造性 / 实用性), 第二十六条 (说明书充分公开), 第三十条 (优先权); claim style differs (前序部分 + 特征部分).
- JP: claim format and unity-of-invention rules differ.
- PCT: a unified application that national-stage examiners later re-examine under their own rules.

Always append to `claims.md`:

```
> Draft claims. Not filed text. Must be reviewed and adapted by a registered
> patent agent / attorney before any filing decision.
```

See `docs/legal-and-ethics.md`.

## Quality checklist

- [ ] Every claim has preamble + transition + body elements, in that order.
- [ ] `comprising` used unless there is a specific reason.
- [ ] Every `the X` has prior `a X` antecedent within the same / depended-on claim.
- [ ] Dependent claims each narrow the parent on one axis.
- [ ] Every element has a row in `claim_chart.md`.
- [ ] No `claim_chart.md` row has empty Specification support or Code support (or has a justified `n/a`).
- [ ] Indefiniteness signals checked and flagged.
- [ ] Advisory footer present in `claims.md`.
- [ ] No strong-claim verbs (`novel`, `unique`, `revolutionary`) inside claim text.

## Anti-patterns

- Treating advisory claims as filed text. They are not.
- Writing dependent claims that broaden ("further including optional X" without `further comprising`) — that is malformed.
- Packing several narrowings into one dependent claim and then re-using each part in another dependent claim (creates dependency-graph confusion).
- Using `said` everywhere because "patent claims do that". Modern practice prefers `the`.
- Means-plus-function language without describing the means in §7 of the TID.
- Optional clauses (`preferably`, `optionally`) in independent claims.
- Letting `claim_chart.md` rows drift from claim text. Re-derive the chart whenever a claim is edited.
