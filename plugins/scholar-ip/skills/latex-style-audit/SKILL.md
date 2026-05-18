---
id: latex-style-audit
title: "LaTeX style audit: caption / ref / math / microtypography rules over a clean-compiling manuscript"
kind: skill
phase: paper
description: >
  Runs after `latex-build` reports a clean compile. Sweeps the manuscript
  for style violations a human reviewer would mark — caption punctuation,
  `\eqref` vs `\ref`, booktabs hygiene, bare-URL usage, dash consistency,
  footnote placement, and more. Emits a structured findings JSON for the
  orchestrator and a human-readable log; never auto-fixes prose.
triggers:
  - "command:/scholar:paper-check"
  - "command:/scholar:paper-venue"
  - "subagent:latex-editor"
  - "auditing manuscript style"
  - "running style audit after clean compile"
provides:
  - latex-style-rule-set
  - latex-style-findings-schema
  - latex-style-regex-recipes
  - latex-style-severity-policy
  - latex-style-human-report
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:grep*"
  - "Bash:awk*"
hooks: [latex-compile]
references:
  - doc: ../latex-build/SKILL.md
  - doc: ../latex-writing/SKILL.md
  - doc: ../venue-formatting/SKILL.md
  - doc: ../scholar-search/SKILL.md
  - doc: ../../hooks/citation-guard.md
  - doc: ../../hooks/latex-compile.md
  - doc: ../../agents/latex-editor.md
  - doc: ../../commands/paper-check.md
---

# latex-style-audit

## 1. When to use

Runs as a sub-pass of `/scholar:paper-check` **after** `latex-build` reports a clean (or merely warning-level) compile. The skill is observational: it never edits `.tex`.

Also fires implicitly when the `latex-editor` subagent stages a manuscript revision — it lets the agent see the same style backlog a reviewer would, before the agent applies fixes on a separate pass.

Skip the run if `compile` from the preceding `latex-build` invocation is `FAIL` (style findings on a non-building manuscript would be noise) — exception: `/scholar:paper-venue` may still run the audit on the canonical `manuscript/` while the venue copy fails, because the upstream prose is what the venue pass will copy.

## 2. Shared cache + run_id convention

Style artefacts live alongside `latex-build` artefacts under `.evidraft/manuscript/`:

- `.evidraft/manuscript/style_audit-<ts>.log` — human-readable, one row per finding.
- `.evidraft/manuscript/style_audit-<ts>.findings.json` — structured rows for the orchestrator.

`<ts>` is UTC iso-basic (`20260518T143000Z`), matching `compile-<ts>` so the two files pair up trivially. When called from a command with a `run_id` in its `plan.yaml`, record the `run_id` as the top-level `run_id` field inside `style_audit-<ts>.findings.json`. The literature retrieval cache (`.evidraft/literature/.cache/`) is **not** touched.

## 3. Inputs

- `manuscript/main.tex` and `manuscript/sections/*.tex` (canonical tree), **or** `submissions/<venue>/main.tex` + `submissions/<venue>/sections/*.tex` (venue tree, when the caller passes a `--root submissions/<venue>/` flag).
- `.evidraft/manuscript/compile-<ts>.log` — most recent compile log, to know which symbols / files are in scope. Optional: if missing, scan everything `\input`-reachable from `main.tex`.
- `.evidraft/manuscript/compile-<ts>.errors.json` — optional; used only to skip the audit when `compile == "FAIL"` (see When to use).

## 4. Outputs

### 4.1 `.evidraft/manuscript/style_audit-<ts>.log`

One row per finding. Columns separated by ` | `:

```
<severity> | <file>:<line> | <rule_id> | matched: <text> | suggested: <text>
```

Trailing block: `summary: info=<n> warn=<n> fail=<n>`.

### 4.2 `.evidraft/manuscript/style_audit-<ts>.findings.json`

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "manuscript_root": "manuscript/",
  "findings": [
    {
      "rule_id": "FIG_CAPTION_PUNCT",
      "severity": "warn",
      "file": "manuscript/sections/method.tex",
      "line": 142,
      "matched": "\\caption{Figure 1 The architecture}",
      "suggested": "\\caption{Figure 1.\\ The architecture}",
      "explanation": "Captions use sentence form with terminating period."
    }
  ],
  "summary": {"info": 0, "warn": 0, "fail": 0}
}
```

Severity totals reflect the emitted findings only; rules that did not fire do not contribute zeros for their own bucket — the bucket counts severities, not rules.

## 5. Rule set

All `rule_id`s are UPPER_SNAKE and stable across runs. Regexes below are Python / POSIX-ERE compatible; the implementation uses `Grep` (preferred) with `awk` fall-backs for multi-line conditions.

**Universal pre-filter for every rule:** strip lines whose first non-whitespace character is `%` (LaTeX comment) and any line inside a `verbatim`, `lstlisting`, `minted`, or `comment` environment. Without this, every rule will false-positive on documentation snippets.

### 5.1 Captions

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `FIG_CAPTION_PUNCT` | warn | `\\caption\{[^}]*[^.?!}]\}` | `\caption{The architecture}` | `\caption{The architecture.}` | Captions are sentences; terminate with `.`, `?`, or `!`. |
| `TAB_CAPTION_POSITION` | warn | in a `table` env, the offset of `\caption{` is **greater than** the offset of `\begin{tabular}` | `\begin{table}\begin{tabular}{cc}...\end{tabular}\caption{X.}\end{table}` | move `\caption{X.}` to **before** `\begin{tabular}` | Table captions sit above the body (booktabs convention). |
| `CAPTION_SENTENCE_CASE` | info | `\\caption\{(Figure|Table) \d+ +[a-z]` | `\caption{Figure 1 the architecture.}` | `\caption{Figure 1. The architecture.}` | First word after `Figure N` / `Table N` is capitalised. |
| `CAPTION_LABEL_ORDER` | info | inside a `figure` / `table` env, `\label{` appears **before** `\caption{` | `\begin{figure}\label{fig:x}\caption{...}\end{figure}` | swap so `\label` follows `\caption` | `\label` must follow `\caption` or it binds to the section's counter. |

Known false-positive note: `FIG_CAPTION_PUNCT` triggers on captions ending in a closing macro like `\cite{x}}`; allow the pattern to look back through one balanced macro before declaring missing terminal punctuation.

### 5.2 Cross-references

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `REF_VS_EQREF` | warn | `\\ref\{eq:[^}]+\}` (anywhere outside math mode) | `Equation \ref{eq:loss}` | `Equation~\eqref{eq:loss}` | Equations render with parentheses via `\eqref`. |
| `REF_NONBREAKING_SPACE` | warn | `\b(Fig|Tab|Sec|Eq)\.[ ]\\ref\{` (a single ASCII space, not `~` and not `\ ` , before `\ref`) | `Fig. \ref{fig:x}` | `Fig.~\ref{fig:x}` or `Fig.\ \ref{fig:x}` | Prevents line break between abbreviation and number. |
| `CITE_BEFORE_PUNCT` | warn | `[\.\,\;\:]\\cite\{` | `.\cite{foo2020}` | `\cite{foo2020}.` | Citation precedes the terminal punctuation. |
| `CREF_VS_REF` | info | `\\ref\{(fig|tab|sec|alg):[^}]+\}` (when `cleveref` is loaded in the preamble) | `Section \ref{sec:method}` | `\cref{sec:method}` | With `cleveref` loaded, prefer `\cref` for prefix-aware refs. |
| `DUPLICATE_LABEL` | fail | two `\label{<key>}` occurrences across input-reachable files where `<key>` is identical | two `\label{fig:arch}` | rename one | A duplicate label silently breaks `\ref` / `\cref` resolution. |

Known false-positive note: `REF_VS_EQREF` is suppressed when the `\ref{eq:...}` is itself **inside** an `\eqref{}` or an `\autoref{}` macro; the pattern excludes preceding `\eqref{` by checking the 7 chars before the match.

### 5.3 Math

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `INLINE_DISPLAY_MIX` | warn | `\$\$[^$]*\$\$` (a `$$...$$` pair on one line) or balanced `$$` across lines | `$$ x = y $$` | `\[ x = y \]` | `$$...$$` is plain-TeX; use `\[ ... \]` or `equation`. |
| `BARE_SYMBOL_NUMBER` | info | `[^$\\][A-Za-z]=[0-9]+` (a variable=number outside math mode) | `n=10` | `$n=10$` | Symbol-equals-number belongs in math mode. |
| `EQ_LABEL_PREFIX` | fail | inside `equation` / `align` / `gather` env, a `\label{` whose argument does **not** start with `eq:` | `\begin{equation}\label{loss}` | `\begin{equation}\label{eq:loss}` | Label-prefix convention from `latex-writing` (`eq:<section-tag>-<thing>`). |
| `OPERATORNAME_MISSING` | info | inside math mode, the bare word `softmax`, `argmax`, `argmin`, `topk`, `sup`, `inf` not preceded by `\` or `\operatorname{` | `$y = softmax(x)$` | `$y = \operatorname{softmax}(x)$` | Operator names render upright via `\operatorname` (or a preamble macro). |
| `EQNARRAY_DEPRECATED` | warn | `\\begin\{eqnarray\*?\}` | `\begin{eqnarray}` | `\begin{align}` | `eqnarray` is deprecated; `align` (amsmath) is the supported form. |

Known false-positive note: `BARE_SYMBOL_NUMBER` skips matches inside `\texttt{...}` and `\path{...}` (variable names in code prose).

### 5.4 Tables & figures

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `BOOKTABS_MIXED_RULES` | warn | a `tabular` block containing both `\toprule` and one or more `\hline` | `\toprule ... \hline ...` | replace `\hline` with `\midrule` or `\bottomrule` | `booktabs` and `\hline` produce visually inconsistent rules. |
| `INCLUDEGRAPHICS_PATH` | fail | `\\includegraphics(\[[^\]]*\])?\{(/[^}]+|[A-Z]:\\[^}]+)\}` (absolute Unix or Windows path) | `\includegraphics{/Users/fsm/fig.pdf}` | `\includegraphics{figures/fig.pdf}` | Absolute paths break every other build host. |
| `FLOAT_SPECIFIER_OVERUSE` | info | `\\begin\{figure\}\[H\]` or `\\begin\{table\}\[H\]` | `\begin{figure}[H]` | `\begin{figure}[tbp]` | `[H]` (from `float`) forbids the float — prefer `[tbp]` and let LaTeX place. |
| `MISSING_GRAPHIC_EXT` | info | `\\includegraphics(\[[^\]]*\])?\{[^.}]+\}` (no `.` in the filename) | `\includegraphics{arch}` | `\includegraphics{arch.pdf}` | Implicit extension breaks under engines without `\DeclareGraphicsExtensions`. |

Known false-positive note: `INCLUDEGRAPHICS_PATH` ignores the `graphicspath{...}` macro itself, which legitimately holds absolute prefixes during local development.

### 5.5 Bibliography proximity (LaTeX-side only)

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `STRONG_CLAIM_VERB_NO_CITE` | fail | echo of the `citation-guard` hook taxonomy (verbs: `state-of-the-art`, `SOTA`, `novel`, `first`, `outperform(s|ed)?`, `significant(ly)?`) within 30 chars of neither a `\cite{}` nor an `[ev_NNNN]` token | `Our method achieves state-of-the-art performance.` | `Our method achieves state-of-the-art performance \cite{...}.` or attach an `[ev_NNNN]` | Strong claims need a citation or evidence id. **Defer to the hook's output**; this skill only echoes the hook so the report surface is unified. |

Implementation note: do **not** re-implement the verb scan. Read the hook's per-run output (`.evidraft/manuscript/citation_guard-<ts>.json` if produced) and copy each row into our `findings[]` with `rule_id = "STRONG_CLAIM_VERB_NO_CITE"`. If the hook produced no output (it did not fire this run), emit zero findings for this rule — never invent.

### 5.6 Microtypography

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `ELLIPSIS_PERIODS` | info | `[^.]\.\.\.[^.]` (exactly three ASCII periods, not part of a longer run) | `Many factors... matter.` | `Many factors\dots\ matter.` | `\dots` renders with correct spacing. |
| `DASH_OVERUSE` | info | inside one section file, **both** `--` (en) **and** `---` (em) appear, or `---` is preceded / followed by a space (em-dash convention is unspaced in US English) | `a long --- complicated --- proof` | pick em-dash style; remove spaces around `---` | Dash inconsistency is the most common micro-typography reviewer complaint. |
| `QUOTES_STRAIGHT` | warn | `"[^"]+"` (ASCII straight quotes around a token of ≥ 1 char) | `the "method"` | `the \`\`method''` | LaTeX renders straight quotes as both-opening — use `` `` `` and `''`. |

Known false-positive note: `QUOTES_STRAIGHT` skips lines that look like code (presence of `\verb`, `\texttt{`, `\path{`, or `\url{` on the same line); also skip inside `lstlisting` / `verbatim` (universal pre-filter handles this).

### 5.7 Common misuses

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `URL_NO_HREF` | info | `https?://[^\s}\\]+` not preceded by `\url{` or `\href{`  (`grep -E 'https?://' \| grep -v -E '\\\\(url\|href)\{'` ) | `see https://arxiv.org/abs/2401.01234` | `see \url{https://arxiv.org/abs/2401.01234}` | Bare URLs do not break correctly and are not hyperlinked. |
| `FIRST_PERSON_PLURAL` | info | inside `\begin{abstract}` ... `\end{abstract}`, count word-boundary occurrences of `\bWe\b` / `\bwe\b` / `\bour\b`; report a single finding when count > 5 | abstract uses "we" 9 times | consider rephrasing 2-3 instances passively | Heavy first-person plural in the abstract reads as PR copy; **do not auto-rewrite**, just count. |
| `FOOTNOTE_AFTER_PUNCT` | warn | `\\footnote\{[^}]*\}[\.,;:!?]` (a punctuation char **after** the closing `}`) | `claim\footnote{See A}.` | `claim.\footnote{See A}` | `\footnote{}` sits **after** the terminating punctuation. |
| `NONBREAKING_CITE` | warn | `\b\w+ \\cite\{` (a normal ASCII space between word and `\cite`, expected `~`) | `Smith \cite{smith2020}` | `Smith~\cite{smith2020}` | A `~` keeps the author name and citation on the same line. |
| `PERCENT_UNESCAPED` | fail | `(^\|[^\\])%(?!.*$)` evaluated only on **non-comment** lines (universal pre-filter applied), i.e. a literal `%` we missed and that LaTeX will treat as a comment | `a 5% drop` | `a 5\% drop` | Bare `%` truncates the rest of the line silently. |
| `TODO_LEFT_IN_PROSE` | warn | `\\todo\{` or `\\TODO\{` or `% ?TODO\b` (the comment form counts) | `\todo{add citation}` | resolve or remove before submission | Tracking leftover `\todo` markers before submit. |

Known false-positive note: `PERCENT_UNESCAPED` is the hardest rule — the universal pre-filter already strips comment lines, but a line like `a 5\% drop \% bad` still has a real comment after the escaped `%`. Match only the **first** `%` per line; if it is preceded by `\`, skip the line.

---

Total distinct `rule_id`s: **28** — FIG_CAPTION_PUNCT, TAB_CAPTION_POSITION, CAPTION_SENTENCE_CASE, CAPTION_LABEL_ORDER, REF_VS_EQREF, REF_NONBREAKING_SPACE, CITE_BEFORE_PUNCT, CREF_VS_REF, DUPLICATE_LABEL, INLINE_DISPLAY_MIX, BARE_SYMBOL_NUMBER, EQ_LABEL_PREFIX, OPERATORNAME_MISSING, EQNARRAY_DEPRECATED, BOOKTABS_MIXED_RULES, INCLUDEGRAPHICS_PATH, FLOAT_SPECIFIER_OVERUSE, MISSING_GRAPHIC_EXT, STRONG_CLAIM_VERB_NO_CITE, ELLIPSIS_PERIODS, DASH_OVERUSE, QUOTES_STRAIGHT, URL_NO_HREF, FIRST_PERSON_PLURAL, FOOTNOTE_AFTER_PUNCT, NONBREAKING_CITE, PERCENT_UNESCAPED, TODO_LEFT_IN_PROSE.

## 6. Procedure

### 6.1 Enumerate input files

```
find manuscript/sections -name '*.tex' -type f
find manuscript -maxdepth 1 -name 'main.tex' -type f
```

(For a venue-tree run, swap `manuscript/` for `submissions/<venue>/`.) Resolve every `\input{...}` from `main.tex` to cover files that live outside `sections/`. Build the working set.

### 6.2 Apply universal pre-filter

For each working-set file, produce a stripped view that:

- drops lines whose first non-whitespace char is `%`,
- drops everything between `\begin{verbatim}` / `\begin{lstlisting}` / `\begin{minted}` / `\begin{comment}` and their matching `\end{...}`.

The stripped view is what every rule scans. The **reported `line` number** must remain the original line number from the source file (preserve line offsets — e.g. replace verbatim-block lines with empty strings rather than removing them).

### 6.3 Run rules

For each rule that is in scope (skip rules whose precondition is absent — e.g. `BOOKTABS_MIXED_RULES` only fires if at least one file contains `\toprule`; `CREF_VS_REF` only fires if `\usepackage{cleveref}` is in the preamble):

1. Run the rule's `grep -nE '<regex>' <file>` (or the awk recipe for multi-line rules: `TAB_CAPTION_POSITION`, `CAPTION_LABEL_ORDER`, `DUPLICATE_LABEL`, `DASH_OVERUSE`, `INLINE_DISPLAY_MIX` cross-line).
2. For each hit, fill in `{rule_id, severity, file, line, matched, suggested, explanation}`.
3. `suggested` is a templated rewrite — never write it back to the `.tex` file.

For `STRONG_CLAIM_VERB_NO_CITE`, do not run regex — read the citation-guard hook's per-run output (see § 5.5 implementation note) and import its rows.

### 6.4 Aggregate

Concatenate all rule findings. Sort by `(file, line, severity)` with `fail > warn > info`. Tally the `summary` block.

### 6.5 Emit artefacts

Write `.evidraft/manuscript/style_audit-<ts>.findings.json` (machine) and `.evidraft/manuscript/style_audit-<ts>.log` (human, format per § 4.1).

### 6.6 Surface to chat

Print one summary block:

```
LaTeX style audit (manuscript/): info=<a> warn=<b> fail=<c>
  rules fired:  <comma-separated rule_ids>
  log:          .evidraft/manuscript/style_audit-<ts>.log
  findings:     .evidraft/manuscript/style_audit-<ts>.findings.json
```

Return the summary to the calling command / agent. Do **not** print every finding line in chat — the caller (e.g. `paper-check`) renders its own report from the JSON.

## 7. Quality checklist

- [ ] Every finding carries a `rule_id` from § 5 (UPPER_SNAKE, stable across runs).
- [ ] Severities follow the policy: `fail` only when the issue makes the paper objectively wrong (`INCLUDEGRAPHICS_PATH`, `EQ_LABEL_PREFIX`, `DUPLICATE_LABEL`, `PERCENT_UNESCAPED`, `STRONG_CLAIM_VERB_NO_CITE`); `warn` for reviewer-visible style violations; `info` for matters of taste.
- [ ] Universal pre-filter applied — no comment / verbatim / lstlisting false positives.
- [ ] Reported `line` matches the original source line (pre-filter preserves offsets).
- [ ] No `.tex` file edited. The skill writes only under `.evidraft/manuscript/`.
- [ ] `findings.json` emitted even when zero findings (empty `findings`, zero `summary` — part of the audit trail).
- [ ] Rules whose precondition is absent are silently skipped (not reported as "0 findings").
- [ ] When `compile == "FAIL"` from the preceding `latex-build`, the skill skips the run (with one chat line explaining why) unless the caller is `/scholar:paper-venue`.

## 8. Anti-patterns

- **Auto-rewriting prose.** This skill reports; `latex-editor` agent applies fixes on a separate pass.
- **False positives from comments.** Every rule's regex must run against the **pre-filtered** view, never the raw file.
- **False positives from `verbatim` / `lstlisting`.** Same pre-filter; if you find yourself adding `# verbatim hack` to a single rule, your pre-filter is wrong.
- **Re-implementing `citation-guard`.** `STRONG_CLAIM_VERB_NO_CITE` echoes the hook's output. Two implementations of the same taxonomy will drift.
- **Rule inflation.** A rule earns its place only when (a) the regex is clean, (b) the false-positive shape is documented, and (c) you can paste a concrete failure example. Don't add "looks weird" rules.
- **Mixing severities arbitrarily.** Promoting a style-of-taste rule to `fail` because the manuscript happens to violate it once is how reviewers learn to ignore the tool.
- **Skipping the `findings.json` write because nothing fired.** The empty file is the audit-trail proof that the audit ran.
- **Running the audit on a `FAIL` compile.** Style findings on a non-building draft buries the real fix in noise.
