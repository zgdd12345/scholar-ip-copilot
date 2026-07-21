# Rule taxonomy — 14 cross-reference rules

Each rule: `rule_id`, severity, detection pattern, example failing fragment, suggested fix, explanation.

## 1. Label hygiene

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `LABEL_DUPLICATED` | fail | the same `\label{X}` occurs in ≥ 2 distinct `(file, line)` positions. Detect via Grep `\\label\{[^}]+\}` across all sources; collect into `labels[key] -> [(file,line), ...]`; flag any key whose list length > 1. | `\label{fig:overview}` in `sections/intro.tex:42` and again in `sections/method.tex:11` | rename one (and update its referrers). | LaTeX emits "multiply-defined" warnings and only the last definition wins; references silently resolve to the wrong target. |
| `LABEL_ORPHANED` | warn | `\label{X}` defined but **no** `\ref{X}`, `\eqref{X}`, `\autoref{X}`, or `\nameref{X}` anywhere in the corpus. | `\label{eq:unused}` defined in `sections/method.tex` but never referenced | confirm intent; if scaffolding, leave; if dead weight, remove. | orphans often signal a deleted reference or a planned reference that was never written. |
| `LABEL_PREFIX_CONVENTION` | info | the corpus uses prefix conventions (`fig:`, `tab:`, `eq:`, `sec:`, `alg:`) — derive the dominant prefix for each environment from existing usage, then flag any label that violates it. Detection: walk each `\label{X}` and check that `X` carries the project-derived prefix matching its enclosing environment. | `\begin{figure} ... \label{overview} ... \end{figure}` (no `fig:` prefix) | rename to `\label{fig:overview}`. | prefixes make `\ref{}` self-documenting and let `\autoref` discover counter names. |
| `LABEL_PLACEMENT_FIGURE` | warn | inside a `figure` or `figure*` environment, the `\label{}` appears **before** the `\caption{}`. Detection: line-by-line walk within the env; record the line numbers of the first `\caption{...}` and the first `\label{...}`; flag if `label_line < caption_line`. | `\begin{figure} \includegraphics{x} \label{fig:x} \caption{X} \end{figure}` | move `\label{fig:x}` to **after** `\caption{X}`. | LaTeX assigns the float number on `\caption`; a label set before `\caption` records the wrong counter and `\ref` resolves to the surrounding section. |
| `LABEL_PLACEMENT_TABLE` | warn | same as above but for `table` / `table*` environments. | `\begin{table} \label{tab:x} \caption{...} ... \end{table}` | move `\label{tab:x}` to after `\caption{...}`. | identical mechanism to `LABEL_PLACEMENT_FIGURE`. |

## 2. Reference hygiene

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `REF_BROKEN` | fail | `\ref{X}` (or `\autoref{X}`) where `X` is never `\label{}`d in the corpus | `\ref{fig:doesnotexist}` | locate the intended label or rename the ref. | the PDF renders `??`; reviewers notice immediately. |
| `EQREF_BROKEN` | fail | `\eqref{X}` where `X` is never `\label{}`d | `\eqref{eq:nope}` | same as above. | `\eqref` is `amsmath`'s `(X)` form — broken refs render `(??)`. |
| `CITE_BROKEN` | fail | `\cite{X}` / `\citet{X}` / `\citep{X}` / `\citeauthor{X}` / `\citeyear{X}` where `X` is not a key in `references.bib`. **Overlaps with `bib-audit`'s `CITED_KEY_NOT_IN_BIB`**; both skills report it; both pass it to `workflow:paper.check` for de-dup in the report. | `\cite{ghost2021nope}` with no entry in `references.bib` | add via `scholar-search` + `literature-review`, or remove the `\cite{}`. | identical to `bib-audit`'s mechanical missing-cite — duplicate enforcement is intentional (a future refactor may collapse one). |
| `REF_MIXED_KIND` | info | `\ref{X}` is used where the prefix of `X` suggests a different macro is more idiomatic: `\ref{eq:x}` (should be `\eqref`), `\eqref{sec:x}` (should be `\ref` or `\autoref`), `\ref{fig:x}` followed by literal "Figure " (should be `\autoref` if `\autoref` is otherwise used). | text `Equation \ref{eq:loss}` | switch to `Equation~\eqref{eq:loss}` or `\autoref{eq:loss}`. | mismatched macro produces ugly output (e.g. `Equation 3` vs `Equation (3)`). |

## 3. Counter / float consistency

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `FIGURE_NUMBER_GAP` | info | walk all `\begin{figure}` blocks in `\input` order; collect labels in float order. For each `\ref{fig:X}` / `\autoref{fig:X}`, check that the label was **defined before** the ref in source order (assuming `\input` ordering). Heuristic — only flags forward refs in the simple single-pass reading order. | `\ref{fig:results}` in `sections/intro.tex` before the figure is defined in `sections/results.tex` | move the figure earlier, or `\autoref{}` it (which prints "Figure 4" anyway), or accept the forward reference. | the prose flows better when the figure is introduced before its number appears; a forward reference forces the reader to scroll. |
| `TABLE_FIRST_USE_BEFORE_DEF` | info | identical to `FIGURE_NUMBER_GAP` but for `tab:*` labels and `\begin{table}` blocks. | `\ref{tab:ablation}` in `sections/method.tex` before the table appears in `sections/experiments.tex` | move the table earlier, or accept. | same rationale as `FIGURE_NUMBER_GAP`. |

## 4. Style consistency

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `AUTOREF_INCONSISTENT_USE` | info | the corpus contains **both** `\autoref{}` and plain `\ref{}` for the same kind of target (e.g. some figures referenced as `\autoref{fig:x}`, others as `Figure~\ref{fig:y}`). Count usage per prefix; if both `autoref` and plain-ref counts > 0 for a prefix, flag every minority-side occurrence. | mixed `\autoref{fig:a}` and `Figure~\ref{fig:b}` | pick one (either is fine) and use it throughout. | reviewers notice cross-reference style drift; pick one. |
| `NAMEREF_USE` | info | any occurrence of `\nameref{X}`. | `\nameref{sec:method}` | confirm — `\nameref` prints the section title, which can become stale if the title changes. | rare macro; flag for human review rather than auto-fix. |
| `LABEL_INSIDE_VERBATIM` | info | a `\label{}` is detected inside `\begin{verbatim}...\end{verbatim}` / `\begin{lstlisting}...\end{lstlisting}` / `\verb|...|` / a `%`-comment line. These are **false positives** — the skill must suppress them. Flagged as `info` purely so the audit trail shows the suppression happened. | `\begin{verbatim} \label{fake} \end{verbatim}` | nothing — confirms the parser excluded it. | proves the verbatim-skip pass ran; useful when debugging false positives. |

## Total

**14 rules.** Counts: 5 label-hygiene, 4 reference-hygiene, 2 counter/float, 3 style.
