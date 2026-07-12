# Rule taxonomy — 28 LaTeX style rules

All `rule_id`s are UPPER_SNAKE and stable across runs. Regexes are Python / POSIX-ERE compatible; the implementation uses `Grep` (preferred) with `awk` fall-backs for multi-line conditions.

**Universal pre-filter for every rule:** strip lines whose first non-whitespace character is `%` (LaTeX comment) and any line inside a `verbatim`, `lstlisting`, `minted`, or `comment` environment. Without this, every rule will false-positive on documentation snippets. See [procedure.md](procedure.md) §2 for the offset-preservation recipe.

## 1. Captions

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `FIG_CAPTION_PUNCT` | warn | `\\caption\{[^}]*[^.?!}]\}` | `\caption{The architecture}` | `\caption{The architecture.}` | Captions are sentences; terminate with `.`, `?`, or `!`. |
| `TAB_CAPTION_POSITION` | warn | in a `table` env, the offset of `\caption{` is **greater than** the offset of `\begin{tabular}` | `\begin{table}\begin{tabular}{cc}...\end{tabular}\caption{X.}\end{table}` | move `\caption{X.}` to **before** `\begin{tabular}` | Table captions sit above the body (booktabs convention). |
| `CAPTION_SENTENCE_CASE` | info | `\\caption\{(Figure|Table) \d+ +[a-z]` | `\caption{Figure 1 the architecture.}` | `\caption{Figure 1. The architecture.}` | First word after `Figure N` / `Table N` is capitalised. |
| `CAPTION_LABEL_ORDER` | info | inside a `figure` / `table` env, `\label{` appears **before** `\caption{` | `\begin{figure}\label{fig:x}\caption{...}\end{figure}` | swap so `\label` follows `\caption` | `\label` must follow `\caption` or it binds to the section's counter. |

Known false-positive note: `FIG_CAPTION_PUNCT` triggers on captions ending in a closing macro like `\cite{x}}`; allow the pattern to look back through one balanced macro before declaring missing terminal punctuation.

## 2. Cross-references

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `REF_VS_EQREF` | warn | `\\ref\{eq:[^}]+\}` (anywhere outside math mode) | `Equation \ref{eq:loss}` | `Equation~\eqref{eq:loss}` | Equations render with parentheses via `\eqref`. |
| `REF_NONBREAKING_SPACE` | warn | `\b(Fig|Tab|Sec|Eq)\.[ ]\\ref\{` (a single ASCII space, not `~` and not `\ ` , before `\ref`) | `Fig. \ref{fig:x}` | `Fig.~\ref{fig:x}` or `Fig.\ \ref{fig:x}` | Prevents line break between abbreviation and number. |
| `CITE_BEFORE_PUNCT` | warn | `[\.\,\;\:]\\cite\{` | `.\cite{foo2020}` | `\cite{foo2020}.` | Citation precedes the terminal punctuation. |
| `CREF_VS_REF` | info | `\\ref\{(fig|tab|sec|alg):[^}]+\}` (when `cleveref` is loaded in the preamble) | `Section \ref{sec:method}` | `\cref{sec:method}` | With `cleveref` loaded, prefer `\cref` for prefix-aware refs. |
| `DUPLICATE_LABEL` | fail | two `\label{<key>}` occurrences across input-reachable files where `<key>` is identical | two `\label{fig:arch}` | rename one | A duplicate label silently breaks `\ref` / `\cref` resolution. |

Known false-positive note: `REF_VS_EQREF` is suppressed when the `\ref{eq:...}` is itself **inside** an `\eqref{}` or an `\autoref{}` macro; the pattern excludes preceding `\eqref{` by checking the 7 chars before the match.

## 3. Math

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `INLINE_DISPLAY_MIX` | warn | `\$\$[^$]*\$\$` (a `$$...$$` pair on one line) or balanced `$$` across lines | `$$ x = y $$` | `\[ x = y \]` | `$$...$$` is plain-TeX; use `\[ ... \]` or `equation`. |
| `BARE_SYMBOL_NUMBER` | info | `[^$\\][A-Za-z]=[0-9]+` (a variable=number outside math mode) | `n=10` | `$n=10$` | Symbol-equals-number belongs in math mode. |
| `EQ_LABEL_PREFIX` | fail | inside `equation` / `align` / `gather` env, a `\label{` whose argument does **not** start with `eq:` | `\begin{equation}\label{loss}` | `\begin{equation}\label{eq:loss}` | Label-prefix convention from `latex-writing` (`eq:<section-tag>-<thing>`). |
| `OPERATORNAME_MISSING` | info | inside math mode, the bare word `softmax`, `argmax`, `argmin`, `topk`, `sup`, `inf` not preceded by `\` or `\operatorname{` | `$y = softmax(x)$` | `$y = \operatorname{softmax}(x)$` | Operator names render upright via `\operatorname` (or a preamble macro). |
| `EQNARRAY_DEPRECATED` | warn | `\\begin\{eqnarray\*?\}` | `\begin{eqnarray}` | `\begin{align}` | `eqnarray` is deprecated; `align` (amsmath) is the supported form. |

Known false-positive note: `BARE_SYMBOL_NUMBER` skips matches inside `\texttt{...}` and `\path{...}` (variable names in code prose).

## 4. Tables & figures

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `BOOKTABS_MIXED_RULES` | warn | a `tabular` block containing both `\toprule` and one or more `\hline` | `\toprule ... \hline ...` | replace `\hline` with `\midrule` or `\bottomrule` | `booktabs` and `\hline` produce visually inconsistent rules. |
| `INCLUDEGRAPHICS_PATH` | fail | `\\includegraphics(\[[^\]]*\])?\{(/[^}]+|[A-Z]:\\[^}]+)\}` (absolute Unix or Windows path) | `\includegraphics{/Users/fsm/fig.pdf}` | `\includegraphics{figures/fig.pdf}` | Absolute paths break every other build host. |
| `FLOAT_SPECIFIER_OVERUSE` | info | `\\begin\{figure\}\[H\]` or `\\begin\{table\}\[H\]` | `\begin{figure}[H]` | `\begin{figure}[tbp]` | `[H]` (from `float`) forbids the float — prefer `[tbp]` and let LaTeX place. |
| `MISSING_GRAPHIC_EXT` | info | `\\includegraphics(\[[^\]]*\])?\{[^.}]+\}` (no `.` in the filename) | `\includegraphics{arch}` | `\includegraphics{arch.pdf}` | Implicit extension breaks under engines without `\DeclareGraphicsExtensions`. |

Known false-positive note: `INCLUDEGRAPHICS_PATH` ignores the `graphicspath{...}` macro itself, which legitimately holds absolute prefixes during local development.

## 5. Bibliography proximity (LaTeX-side only)

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `STRONG_CLAIM_VERB_NO_CITE` | fail | a strong-claim verb (`state-of-the-art`, `SOTA`, `novel`, `first`, `outperform(s|ed)?`, `significant(ly)?`) occurs within 30 chars of neither a `\cite{}` nor an `[ev_NNNN]` token | `Our method achieves state-of-the-art performance.` | `Our method achieves state-of-the-art performance \cite{...}.` or attach an `[ev_NNNN]` | Strong claims need a citation or evidence id. Run this bounded scan during the audit. |

Implementation note: scan the selected manuscript text once with the declared verb and proximity rules. Copy each match into `findings[]` with `rule_id = "STRONG_CLAIM_VERB_NO_CITE"`; emit zero rows when no match exists.

## 6. Microtypography

| Rule | Severity | Pattern | Matched example | Suggested fix | Explanation |
|---|---|---|---|---|---|
| `ELLIPSIS_PERIODS` | info | `[^.]\.\.\.[^.]` (exactly three ASCII periods, not part of a longer run) | `Many factors... matter.` | `Many factors\dots\ matter.` | `\dots` renders with correct spacing. |
| `DASH_OVERUSE` | info | inside one section file, **both** `--` (en) **and** `---` (em) appear, or `---` is preceded / followed by a space (em-dash convention is unspaced in US English) | `a long --- complicated --- proof` | pick em-dash style; remove spaces around `---` | Dash inconsistency is the most common micro-typography reviewer complaint. |
| `QUOTES_STRAIGHT` | warn | `"[^"]+"` (ASCII straight quotes around a token of ≥ 1 char) | `the "method"` | `the \`\`method''` | LaTeX renders straight quotes as both-opening — use `` `` `` and `''`. |

Known false-positive note: `QUOTES_STRAIGHT` skips lines that look like code (presence of `\verb`, `\texttt{`, `\path{`, or `\url{` on the same line); also skip inside `lstlisting` / `verbatim` (universal pre-filter handles this).

## 7. Common misuses

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

## Total

**28 distinct `rule_id`s** — FIG_CAPTION_PUNCT, TAB_CAPTION_POSITION, CAPTION_SENTENCE_CASE, CAPTION_LABEL_ORDER, REF_VS_EQREF, REF_NONBREAKING_SPACE, CITE_BEFORE_PUNCT, CREF_VS_REF, DUPLICATE_LABEL, INLINE_DISPLAY_MIX, BARE_SYMBOL_NUMBER, EQ_LABEL_PREFIX, OPERATORNAME_MISSING, EQNARRAY_DEPRECATED, BOOKTABS_MIXED_RULES, INCLUDEGRAPHICS_PATH, FLOAT_SPECIFIER_OVERUSE, MISSING_GRAPHIC_EXT, STRONG_CLAIM_VERB_NO_CITE, ELLIPSIS_PERIODS, DASH_OVERUSE, QUOTES_STRAIGHT, URL_NO_HREF, FIRST_PERSON_PLURAL, FOOTNOTE_AFTER_PUNCT, NONBREAKING_CITE, PERCENT_UNESCAPED, TODO_LEFT_IN_PROSE.
