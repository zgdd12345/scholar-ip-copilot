---
id: bib-audit
title: "BibTeX audit: required-field, year, venue, DOI/URL hygiene, cross-entry consistency, coverage"
kind: skill
phase: paper
description: >
  Quality layer above `bib-manager`. After dedup + key normalisation, scan
  every entry in `.evidraft/literature/references.bib` against a 20-rule
  audit covering required fields per BibTeX type, year sanity, venue
  normalisation, DOI / arXiv format, URL format, cross-entry author drift,
  and coverage against `evidence.jsonl` + `manuscript/sections/*.tex`.
  Read-only: emits findings.json + a human log; never auto-fixes.
triggers:
  - "command:/scholar:paper-check"
  - "command:/scholar:paper-lit"
  - "subagent:evidence-auditor"
provides:
  - bib-quality-audit
  - required-field-check
  - venue-normalisation
  - doi-hygiene
  - arxiv-id-hygiene
  - cross-entry-consistency
  - bib-coverage-check
allowed_tools:
  - Read
  - Glob
  - Grep
  - "Bash:grep*"
  - "Bash:awk*"
  - "Bash:bibtex-tidy*"
hooks: [citation-guard]
references:
  - doc: ../bib-manager/SKILL.md
  - doc: ../evidence-check/SKILL.md
---

# bib-audit

## 1. When to use

This skill is the **quality layer above `bib-manager`**. `bib-manager` handles mechanics: dedup, citation-key normalisation, missing-cite + unused-entry detection. `bib-audit` runs **after** those passes and answers a different question: *does each entry deserve to be cited?*

Concretely it audits, per entry:

- required fields per BibTeX type (`@article` needs `journal`, `@inproceedings` needs `booktitle`, etc.);
- year sanity (1900 ≤ y ≤ current_year+1);
- venue spelling drift across entries (`NeurIPS` vs `NIPS` vs the full proceedings title);
- DOI and arXiv id format (regex-only, no network probe);
- URL format (`^https?://`, trailing-slash consistency);
- cross-entry consistency (author name format drift, citation_key vs first-author surname);
- coverage (every `type=paper` row in `evidence.jsonl` resolves to a bib entry; every `\cite{}` resolves; every bib entry is either cited or evidenced).

Load it from `/scholar:paper-check` (the citation block), from `/scholar:paper-lit` (after a fresh import), and from the `evidence-auditor` subagent (when it walks the matrix).

## 2. Inputs

- `.evidraft/literature/references.bib` (canonical — source of truth).
- `manuscript/sections/*.tex`, `manuscript/main.tex` (for `\cite{}` cross-checks).
- `.evidraft/evidence/evidence.jsonl` (every `type=paper` row carries `citation_key`).
- (optional) `manuscript/references.bib` if the manuscript pins a separate copy — treat as a snapshot; the canonical copy wins.

## 3. Outputs

Two files per run, both under `.evidraft/literature/`:

- `bib_audit-<ts>.log` — human-readable, one row per finding (`<severity> <rule_id> <citation_key> <one-line explanation>`).
- `bib_audit-<ts>.findings.json` — structured:

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "bib_path": ".evidraft/literature/references.bib",
  "entry_count": 42,
  "findings": [
    {"rule_id": "REQ_FIELD_MISSING_BOOKTITLE",
     "severity": "fail",
     "citation_key": "smith2021methodx",
     "entry_type": "inproceedings",
     "missing_fields": ["booktitle"],
     "explanation": "@inproceedings requires booktitle."}
  ],
  "summary": {"info": 0, "warn": 0, "fail": 0}
}
```

`<ts>` is UTC iso-basic (`20260518T143000Z`). When called from a command with a `run_id` in `plan.yaml`, embed it as the top-level `run_id`.

No edits to `references.bib`. No edits to the manuscript. Findings only.

## 4. Rule set (20 rules)

Each rule below carries: `rule_id`, severity, detection pattern (regex / predicate), example failing entry, suggested fix, explanation.

### 4.1 Required-field check (per BibTeX entry type)

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `REQ_FIELD_MISSING_AUTHOR` | fail | entry has neither `author` nor `editor` field (case-insensitive) | `@book{foo2020bar, title={X}, year=2020}` | add `author = {Surname, Forename}` or `editor = {...}` | every BibTeX entry needs an authorial attribution; without it bibstyles render `[??]`. |
| `REQ_FIELD_MISSING_TITLE` | fail | entry lacks `title` | `@article{foo2020bar, author={X}, year=2020}` | add `title = {...}` | core identifier; bibstyles cannot render without it. |
| `REQ_FIELD_MISSING_YEAR` | fail | entry lacks `year` (and `date` is absent — biblatex allows `date={2020}`) | `@inproceedings{foo, author={X}, title={Y}, booktitle={Z}}` | add `year = {2020}` (or `date = {2020-05}`) | year sorts the bibliography and gates `YEAR_*` rules. |
| `REQ_FIELD_MISSING_BOOKTITLE` | fail | `entry_type ∈ {inproceedings, incollection, conference}` and no `booktitle` | `@inproceedings{foo2021bar, author={X}, title={Y}, year=2021}` | add `booktitle = {Proceedings of …}` | proceedings entries are unidentifiable without their venue. |
| `REQ_FIELD_MISSING_JOURNAL` | fail | `entry_type == article` and no `journal` (and no `journaltitle` for biblatex) | `@article{foo2021bar, author={X}, title={Y}, year=2021}` | add `journal = {Nature}` | journal articles must name the journal. |
| `REQ_FIELD_MISSING_PUBLISHER` | fail | `entry_type == book` and no `publisher` | `@book{foo2020bar, author={X}, title={Y}, year=2020}` | add `publisher = {MIT Press}` | books require the publisher per `plain.bst` / biblatex defaults. |
| `REQ_FIELD_MISSING_HOWPUBLISHED` | warn | `entry_type == misc` and no `howpublished` nor `url` | `@misc{foo2020bar, author={X}, title={Y}, year=2020}` | add `howpublished = {\url{https://…}}` | misc entries are anchorless unless they at least state where they live. |

### 4.2 Year sanity

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `YEAR_OUT_OF_RANGE` | fail | `year` parses as int and is **not** in `[1900, current_year+1]` | `year = {1899}` or `year = {3025}` | correct the typo or replace with `year = {n.d.}` (and mark unverified) | a year outside the plausible range is almost always a typo or a placeholder that leaked through. |
| `YEAR_FROM_FUTURE` | warn | `year` parses as int and is `> current_year` (but `≤ current_year+1`) | `year = {2027}` when today is 2026 | confirm in-press; otherwise correct | accepts the "in press" case at +1 but flags it for human confirmation. |

### 4.3 Venue normalisation

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `VENUE_ABBREVIATION_DRIFT` | warn | the same canonical venue (token-normalised: lowercase, strip punctuation, strip `proceedings of the`, strip year tokens) is spelled differently across ≥ 2 entries — e.g. `Conference on Neural Information Processing Systems`, `NeurIPS`, `NIPS` | entry A `booktitle = {Advances in Neural Information Processing Systems}`; entry B `booktitle = {NeurIPS}` | pick one canonical form (prefer the venue's current branding — `NeurIPS`); update both | bib styles render the venue verbatim; drift looks careless to reviewers. |
| `VENUE_YEAR_IN_BOOKTITLE` | info | `booktitle` matches `/\b(19|20|21)\d{2}\b/` | `booktitle = {Proceedings of CVPR 2022}` | move the year to `year = {2022}` and trim the booktitle to `Proceedings of CVPR` | year belongs in the `year` field; embedding it duplicates state and breaks sort-by-year. |

### 4.4 DOI / arXiv hygiene

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `DOI_FORMAT_INVALID` | fail | `doi` field present but does **not** match `^10\.\d{4,9}/\S+$` (after stripping `https://doi.org/` and `doi:` prefixes) | `doi = {https://example.com/foo}` | strip to the bare DOI (`10.xxxx/yyyy`); if it isn't a DOI, move to `url`. | a malformed DOI produces a broken hyperref link in the PDF. |
| `ARXIV_ID_FORMAT_INVALID` | fail | entry declares arXiv (`eprint` set, or `archivePrefix = {arXiv}`) but `eprint` does **not** match `^\d{4}\.\d{4,5}(v\d+)?$` (new style) nor `^[a-z\-]+/\d{7}$` (old style) | `eprint = {2401.1234abc}` or `eprint = {arxiv:2401.01234}` | strip prefixes; new-style ids are `YYMM.NNNNN`; old-style are `category/YYMMnnn`. | hyperref builds the arXiv URL from `eprint`; a malformed id yields a dead link. |
| `DOI_AND_URL_REDUNDANT` | info | entry has both `doi` and `url`, and `url` is a DOI URL (`https?://(dx\.)?doi\.org/<doi>` or `https?://doi\.org/<doi>`) | `doi = {10.1/x}` + `url = {https://doi.org/10.1/x}` | drop `url`; keep `doi`. | the doi field already renders as a clickable link via `hyperref`; the duplicate url is noise. |

### 4.5 URL health (format-only, no network probe)

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `URL_FORMAT_INVALID` | warn | `url` field present but does **not** match `^https?://` | `url = {www.example.com/foo}` | prepend `https://`. | `\url{}` typesets the raw string; missing scheme breaks the click target. |
| `URL_TRAILING_SLASH_STYLE` | info | the project mixes trailing-slash and non-trailing-slash URLs (count both; if both > 0, flag every entry on the minority side) | mixed `https://x.org/` and `https://y.org` | pick one convention. | bibstyle output looks more polished if one convention wins. |

### 4.6 Cross-entry consistency

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `AUTHOR_NAME_FORMAT_DRIFT` | warn | the same author (matched by `(surname_lower, first_initial_lower)`) appears across entries in ≥ 2 distinct rendered forms — `Yann LeCun`, `Y. LeCun`, `LeCun, Y.` | entry A `author = {Yann LeCun and ...}`; entry B `author = {LeCun, Y. and ...}` | pick BibTeX-canonical `Surname, Forename(s)` and re-render every occurrence. | natbib + plain.bst tolerates drift; biblatex with `firstinits` does not — and it looks sloppy regardless. |
| `KEY_AUTHOR_MISMATCH` | warn | `citation_key` starts with a recognisable surname token (lowercased ASCII letters before the 4-digit year), and that token does **not** equal the lowercased ASCII-stripped surname of the first author. Compare `re.match(r'^([a-z]+)\d{4}', key).group(1)` to the parsed first-author surname. | `@article{johnson2021foo, author = {Smith, J. and ...}}` | rename via `bib-manager` (`smith2021foo`) — never by hand. | the `firstauthorYEARkeyword` convention is the only fast cross-reference humans have. |

### 4.7 Coverage check (against the evidence store + manuscript)

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `EVIDENCE_REFERENCES_MISSING_KEY` | fail | a row in `.evidraft/evidence/evidence.jsonl` has `type == "paper"` and a `citation_key` that does **not** appear as the key of any entry in `references.bib` | evidence row `{"type":"paper","citation_key":"smith2021foo",...}` but no `@*{smith2021foo,...}` | add the entry via `literature-review` + `scholar-search`; never invent. | evidence is supposed to anchor in a real citation; an unanchored row will fail `evidence-auditor`. |
| `CITED_KEY_NOT_IN_BIB` | fail | a `\cite{X}` / `\citet{X}` / `\citep{X}` / `\citeauthor{X}` / `\citeyear{X}` in `manuscript/sections/*.tex` or `manuscript/main.tex` references key `X`, and `X` is not in `references.bib`. Overlaps with `bib-manager` mechanical missing-cite — re-asserted here as a quality verdict. | `\cite{smith2021foo}` in `sections/intro.tex` but no entry `smith2021foo` | add via `scholar-search` + `literature-review`, or remove the `\cite{}`. | duplicate enforcement: missing keys are both a mechanical bug and a quality bug. |
| `BIB_KEY_NEVER_CITED_NEVER_EVIDENCED` | warn | an entry in `references.bib` is never `\cite*{}`d in any `.tex` source **and** never referenced as `citation_key` in `evidence.jsonl` | `@article{ghost2019filler, ...}` with zero hits in both | confirm intent; if dead weight, remove (via `bib-manager`); if drafting an upcoming section, leave with `% TODO`. | dead entries inflate the bib, slow `bibtex`, and noise reviews. |

**Total: 20 rules.** Counts: 7 required-field, 2 year-sanity, 2 venue, 3 DOI/arXiv, 2 URL, 2 cross-entry, 3 coverage.

## 5. Procedure

### 5.1 Parse the bib

If `bibtex-tidy` is on `$PATH`:

```
bibtex-tidy --no-modify --duplicates=key --no-align references.bib
```

This emits a stable, normalised view to stdout that the LLM can read field-by-field. If `bibtex-tidy` is **not** on `$PATH`, hand-roll with the same parser shape `bib-manager` uses (greedy match on `@<type>{<key>,` followed by balanced `{...}`, then split fields on top-level commas).

Build an in-memory list of entry dicts:

```python
{"key": "...", "type": "article", "fields": {"author": "...", "title": "...", ...}, "src_line": 17}
```

### 5.2 Run §4 rules

For each rule, scan the parsed entries and emit findings. Rules that need cross-entry state (`VENUE_ABBREVIATION_DRIFT`, `AUTHOR_NAME_FORMAT_DRIFT`, `URL_TRAILING_SLASH_STYLE`) build their state in a first pass, then re-iterate.

### 5.3 Coverage cross-checks

1. **Cite set.** Reuse the `bib-manager` recipe (Grep `\\(?:cite|citet|citep|citeauthor|citeyear)\{[^}]+\}` across `manuscript/sections/*.tex` and `manuscript/main.tex`; split multi-key cites on `,`).
2. **Evidence-citation set.** Read `.evidraft/evidence/evidence.jsonl`; collect every `citation_key` from rows where `type == "paper"`.
3. **Bib key set.** Greppable as `^@\w+\{([^,]+),` on `references.bib`.
4. Apply:
   - `EVIDENCE_REFERENCES_MISSING_KEY` — evidence-citation set minus bib key set.
   - `CITED_KEY_NOT_IN_BIB` — cite set minus bib key set.
   - `BIB_KEY_NEVER_CITED_NEVER_EVIDENCED` — bib key set minus (cite set ∪ evidence-citation set).

### 5.4 Emit

Write the `.log` and `.findings.json` under `.evidraft/literature/`. Print a one-line summary to chat:

```
bib-audit: 3 fail, 5 warn, 2 info  (.evidraft/literature/bib_audit-<ts>.log)
```

## 6. Quality checklist

- [ ] Severity assigned consistently: `fail` for breaking citations (missing `author`/`title`/`year`, malformed DOI/arXiv, broken cite/evidence references); `warn` for quality issues a reviewer would mark (year-from-future, author drift, never-cited entries); `info` for taste (trailing-slash, year-in-booktitle, redundant doi+url).
- [ ] Every coverage finding traces to a real file path + line (no hallucinated keys).
- [ ] `entry_count` in `findings.json` equals the number of `@<type>{...}` blocks in `references.bib`.
- [ ] `summary` counts equal the per-severity counts in `findings`.
- [ ] When called with a `run_id`, the value lands at the top level of `findings.json`.
- [ ] The `.log` file is grep-friendly (one finding per line, leading `<severity>` token).

## 7. Anti-patterns

- Re-implementing `bib-manager` dedup. That is a different skill; this one is read-only quality.
- Probing URLs / DOIs against the network. Format-only here; probing belongs to a future `bib-link-check` skill and would be slow + flaky.
- Auto-fixing entries. Findings only. The author (or `bib-manager`) decides.
- Inventing a bib entry to satisfy `EVIDENCE_REFERENCES_MISSING_KEY` or `CITED_KEY_NOT_IN_BIB`. Missing means "fetch via `scholar-search`", not "make one up".
- Treating `BIB_KEY_NEVER_CITED_NEVER_EVIDENCED` as `fail`. The author may be drafting a section; warn only.
- Running before `bib-manager`. Dedup first, then audit — otherwise the same finding fires once per duplicate.
