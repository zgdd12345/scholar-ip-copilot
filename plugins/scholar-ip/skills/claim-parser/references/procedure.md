# Parse procedure

## 1. Read `claims.md`

```
Read .evidraft/patent/claims.md
```

If the file is missing, print `claim-parser: no claims.md (skip)` and exit. Otherwise continue.

## 2. Split into H2 claim sections

Match the H2 header regex:

```
^## Claim (\d+) \((independent|dependent on (\d+))\)\s*$
```

Everything before the first matching H2 (the H1 `# Draft claims (for attorney review)` and any preamble paragraph) is discarded. Everything **after** the last claim's terminating period up to the mandatory `> Draft claims. ... attorney ...` blockquote footer is discarded. The footer itself is **not** part of any claim.

For each H2 section, capture:

- `number` = the integer in group 1,
- `kind` = `independent` if group 2 == `independent`, else `dependent`,
- `depends_on` = `c<group 3>` if dependent, else `null`.

## 3. Per-claim body parse

Within each H2 section's body:

1. **Preamble.** First non-blank line is the numbered prose line (e.g. `1. A method comprising:` or `2. The method of claim 1, wherein:`). Strip the leading `<number>.` and surrounding whitespace; the result up to and including the line's trailing `:` is the `preamble`. If no `:` is found before the first labelled element, the preamble is the entire pre-element prose verbatim (and `TRANSITION_UNKNOWN` will fire — see [warning-taxonomy.md](warning-taxonomy.md)).
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

## 4. Antecedent-basis analysis

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

## 5. Dependency-graph validation

1. Every `depends_on` must reference a **strictly earlier** claim number — otherwise fire `FORWARD_DEPENDENCY` (fail) and leave `depends_on` populated for downstream debugging.
2. A preamble matching `The method of claim \d+ (or|and) claim \d+` (or more disjuncts) fires `MULTIPLE_DEPENDENCY` (warn). Set `depends_on` to the **first** referenced parent only; record the alternates in the warning row's `explanation`.
3. A dependent claim whose body has no `wherein` / `further comprising` / `further including` token fires `DEPENDENT_NO_NARROW` (warn).

## 6. Write artefacts

Overwrite `.evidraft/patent/claims_parsed.json` with the structured form (see [schema.md](schema.md)). Write a new `.evidraft/patent/claim_parse-<ts>.log` with one line per parsed element:

```
c<N>[<label>]  intro=<noun, noun, ...>  ref=<noun, ...>  text="..."
```

followed by one line per warning:

```
<severity>  <rule_id>  c<N>[<label>]  <one-line explanation>
```

and a trailing `summary: independent=<i> dependent=<d> warn=<w> fail=<f>` block.

## 7. Surface to chat

Print one summary line:

```
claim-parser: <i> indep / <d> dep / <w> warn / <f> fail  (.evidraft/patent/claim_parse-<ts>.log)
```

Return the JSON path to the caller. Do **not** dump the JSON to chat — the orchestrator renders it.
