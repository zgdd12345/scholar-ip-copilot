# Procedure — 6 steps

## 1. Enumerate input files

```
find manuscript/sections -name '*.tex' -type f
find manuscript -maxdepth 1 -name 'main.tex' -type f
```

(For a venue-tree run, swap `manuscript/` for `submissions/<venue>/`.) Resolve every `\input{...}` from `main.tex` to cover files that live outside `sections/`. Build the working set.

## 2. Apply universal pre-filter

For each working-set file, produce a stripped view that:

- drops lines whose first non-whitespace char is `%`,
- drops everything between `\begin{verbatim}` / `\begin{lstlisting}` / `\begin{minted}` / `\begin{comment}` and their matching `\end{...}`.

The stripped view is what every rule scans. The **reported `line` number** must remain the original line number from the source file — preserve line offsets (e.g. replace verbatim-block lines with empty strings rather than removing them).

## 3. Run rules

For each rule that is in scope (skip rules whose precondition is absent — e.g. `BOOKTABS_MIXED_RULES` only fires if at least one file contains `\toprule`; `CREF_VS_REF` only fires if `\usepackage{cleveref}` is in the preamble):

1. Run the rule's `grep -nE '<regex>' <file>` (or the awk recipe for multi-line rules: `TAB_CAPTION_POSITION`, `CAPTION_LABEL_ORDER`, `DUPLICATE_LABEL`, `DASH_OVERUSE`, `INLINE_DISPLAY_MIX` cross-line).
2. For each hit, fill in `{rule_id, severity, file, line, matched, suggested, explanation}` (see [output-schemas.md](output-schemas.md)).
3. `suggested` is a templated rewrite — never write it back to the `.tex` file.

For `STRONG_CLAIM_VERB_NO_CITE`, do not run regex — read the citation-guard hook's per-run output and import its rows (see [rule-taxonomy.md](rule-taxonomy.md) §5 implementation note).

## 4. Aggregate

Concatenate all rule findings. Sort by `(file, line, severity)` with `fail > warn > info`. Tally the `summary` block.

## 5. Emit artefacts

Write `.evidraft/manuscript/style_audit-<ts>.findings.json` (machine) and `.evidraft/manuscript/style_audit-<ts>.log` (human, format per [output-schemas.md](output-schemas.md)).

## 6. Surface to chat

Print one summary block:

```
LaTeX style audit (manuscript/): info=<a> warn=<b> fail=<c>
  rules fired:  <comma-separated rule_ids>
  log:          .evidraft/manuscript/style_audit-<ts>.log
  findings:     .evidraft/manuscript/style_audit-<ts>.findings.json
```

Return the summary to the calling command / agent. Do **not** print every finding line in chat — the caller (e.g. `paper-check`) renders its own report from the JSON.
