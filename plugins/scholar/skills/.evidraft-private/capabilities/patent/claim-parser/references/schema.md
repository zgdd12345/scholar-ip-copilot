# Schema of `claims_parsed.json`

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
