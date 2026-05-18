---
id: xref-audit
title: "Cross-reference audit: \\ref / \\eqref / \\cite / \\label graph validation"
kind: skill
phase: paper
description: >
  Static analysis of the LaTeX cross-reference graph. After `latex-build`
  reports a clean (or near-clean) compile, walk `manuscript/main.tex` +
  `sections/*.tex` and validate every `\label{}`, `\ref{}`, `\eqref{}`,
  `\autoref{}`, `\nameref{}`, and `\cite{}` against the resolved graph and
  the bib key set. Detects duplicates, orphans, broken refs, prefix-drift,
  caption/label placement, and float order. Read-only.
triggers:
  - "command:/scholar:paper-check"
  - "command:/scholar:paper-venue"
  - "subagent:latex-editor"
provides:
  - xref-graph-validation
  - label-hygiene
  - reference-hygiene
  - cite-bib-cross-check
  - float-order-check
  - autoref-consistency
allowed_tools:
  - Read
  - Glob
  - Grep
  - "Bash:grep*"
  - "Bash:awk*"
hooks: [latex-compile]
references:
  - doc: ../latex-build/SKILL.md
  - doc: ../latex-style-audit/SKILL.md
---

# xref-audit

## 1. When to use

Cross-reference auditing **requires a successful (or near-successful) compile** — a missing `\label{}` is already a LaTeX error and `latexmk` will catch it. This skill runs as a **sub-pass** of `/scholar:paper-check` between `latex-build` (compile + error taxonomy) and `latex-style-audit` (prose). Its job is to validate the **cross-reference graph**:

- which labels are defined (and where);
- which labels are referenced (and from where);
- which `\cite{}` keys resolve into `references.bib`;
- whether prefix convention (`fig:`, `tab:`, `eq:`, `sec:`, `alg:`) is followed;
- whether labels sit in the right place relative to captions and floats.

It is **static analysis** — it does **not** read `.aux` files (those are compile artefacts and may be stale).

## 2. Inputs

- `manuscript/main.tex` plus everything it `\input{}`s (recursively): `manuscript/sections/*.tex`, `manuscript/preamble.tex`.
- For `/scholar:paper-venue`: `submissions/<venue>/main.tex` + sections instead.
- `references.bib` (path resolved via `\bibliography{...}` or `\addbibresource{...}`, or default `.evidraft/literature/references.bib`).
- (Optional, **context only** — never authoritative) `.evidraft/manuscript/compile-<ts>.log` from a recent `latex-build` run.

## 3. Outputs

Two files per run, both under `.evidraft/manuscript/`:

- `xref_audit-<ts>.log` — one finding per line (`<severity> <rule_id> <file>:<line> <one-line explanation>`).
- `xref_audit-<ts>.findings.json`:

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "manuscript_root": "manuscript/",
  "labels": {"defined": 87, "duplicated": 0, "orphaned": 3},
  "refs":   {"resolved": 124, "broken": 0},
  "cites":  {"resolved": 56, "broken": 1},
  "findings": [
    {"rule_id": "REF_BROKEN",
     "severity": "fail",
     "file": "manuscript/sections/method.tex",
     "line": 142,
     "target": "fig:doesnotexist",
     "explanation": "\\ref{fig:doesnotexist} has no matching \\label{}."}
  ],
  "summary": {"info": 0, "warn": 0, "fail": 0}
}
```

`<ts>` is UTC iso-basic. When called with a `run_id`, embed it at the top level.

No edits to `.tex`. No edits to `references.bib`. Findings only.

## 4. Rule set (14 rules)

Each rule: `rule_id`, severity, detection pattern, example failing fragment, suggested fix, explanation.

### 4.1 Label hygiene

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `LABEL_DUPLICATED` | fail | the same `\label{X}` occurs in ≥ 2 distinct `(file, line)` positions. Detect via Grep `\\label\{[^}]+\}` across all sources; collect into `labels[key] -> [(file,line), ...]`; flag any key whose list length > 1. | `\label{fig:overview}` in `sections/intro.tex:42` and again in `sections/method.tex:11` | rename one (and update its referrers). | LaTeX emits "multiply-defined" warnings and only the last definition wins; references silently resolve to the wrong target. |
| `LABEL_ORPHANED` | warn | `\label{X}` defined but **no** `\ref{X}`, `\eqref{X}`, `\autoref{X}`, or `\nameref{X}` anywhere in the corpus. | `\label{eq:unused}` defined in `sections/method.tex` but never referenced | confirm intent; if scaffolding, leave; if dead weight, remove. | orphans often signal a deleted reference or a planned reference that was never written. |
| `LABEL_PREFIX_CONVENTION` | info | the corpus uses prefix conventions (`fig:`, `tab:`, `eq:`, `sec:`, `alg:`) — derive the dominant prefix for each environment from existing usage, then flag any label that violates it. Detection: walk each `\label{X}` and check that `X` carries the project-derived prefix matching its enclosing environment. | `\begin{figure} ... \label{overview} ... \end{figure}` (no `fig:` prefix) | rename to `\label{fig:overview}`. | prefixes make `\ref{}` self-documenting and let `\autoref` discover counter names. |
| `LABEL_PLACEMENT_FIGURE` | warn | inside a `figure` or `figure*` environment, the `\label{}` appears **before** the `\caption{}`. Detection: line-by-line walk within the env; record the line numbers of the first `\caption{...}` and the first `\label{...}`; flag if `label_line < caption_line`. | `\begin{figure} \includegraphics{x} \label{fig:x} \caption{X} \end{figure}` | move `\label{fig:x}` to **after** `\caption{X}`. | LaTeX assigns the float number on `\caption`; a label set before `\caption` records the wrong counter and `\ref` resolves to the surrounding section. |
| `LABEL_PLACEMENT_TABLE` | warn | same as above but for `table` / `table*` environments. | `\begin{table} \label{tab:x} \caption{...} ... \end{table}` | move `\label{tab:x}` to after `\caption{...}`. | identical mechanism to `LABEL_PLACEMENT_FIGURE`. |

### 4.2 Reference hygiene

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `REF_BROKEN` | fail | `\ref{X}` (or `\autoref{X}`) where `X` is never `\label{}`d in the corpus | `\ref{fig:doesnotexist}` | locate the intended label or rename the ref. | the PDF renders `??`; reviewers notice immediately. |
| `EQREF_BROKEN` | fail | `\eqref{X}` where `X` is never `\label{}`d | `\eqref{eq:nope}` | same as above. | `\eqref` is `amsmath`'s `(X)` form — broken refs render `(??)`. |
| `CITE_BROKEN` | fail | `\cite{X}` / `\citet{X}` / `\citep{X}` / `\citeauthor{X}` / `\citeyear{X}` where `X` is not a key in `references.bib`. **Overlaps with `bib-audit`'s `CITED_KEY_NOT_IN_BIB`**; both skills report it; both pass it to `/scholar:paper-check` for de-dup in the report. | `\cite{ghost2021nope}` with no entry in `references.bib` | add via `scholar-search` + `literature-review`, or remove the `\cite{}`. | identical to `bib-audit`'s mechanical missing-cite — duplicate enforcement is intentional (a future refactor may collapse one). |
| `REF_MIXED_KIND` | info | `\ref{X}` is used where the prefix of `X` suggests a different macro is more idiomatic: `\ref{eq:x}` (should be `\eqref`), `\eqref{sec:x}` (should be `\ref` or `\autoref`), `\ref{fig:x}` followed by literal "Figure " (should be `\autoref` if `\autoref` is otherwise used). | text `Equation \ref{eq:loss}` | switch to `Equation~\eqref{eq:loss}` or `\autoref{eq:loss}`. | mismatched macro produces ugly output (e.g. `Equation 3` vs `Equation (3)`). |

### 4.3 Counter / float consistency

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `FIGURE_NUMBER_GAP` | info | walk all `\begin{figure}` blocks in `\input` order; collect labels in float order. For each `\ref{fig:X}` / `\autoref{fig:X}`, check that the label was **defined before** the ref in source order (assuming `\input` ordering). Heuristic — only flags forward refs in the simple single-pass reading order. | `\ref{fig:results}` in `sections/intro.tex` before the figure is defined in `sections/results.tex` | move the figure earlier, or `\autoref{}` it (which prints "Figure 4" anyway), or accept the forward reference. | the prose flows better when the figure is introduced before its number appears; a forward reference forces the reader to scroll. |
| `TABLE_FIRST_USE_BEFORE_DEF` | info | identical to `FIGURE_NUMBER_GAP` but for `tab:*` labels and `\begin{table}` blocks. | `\ref{tab:ablation}` in `sections/method.tex` before the table appears in `sections/experiments.tex` | move the table earlier, or accept. | same rationale as `FIGURE_NUMBER_GAP`. |

### 4.4 Style consistency

| rule_id | sev | detection | example fail | suggested fix | explanation |
|---|---|---|---|---|---|
| `AUTOREF_INCONSISTENT_USE` | info | the corpus contains **both** `\autoref{}` and plain `\ref{}` for the same kind of target (e.g. some figures referenced as `\autoref{fig:x}`, others as `Figure~\ref{fig:y}`). Count usage per prefix; if both `autoref` and plain-ref counts > 0 for a prefix, flag every minority-side occurrence. | mixed `\autoref{fig:a}` and `Figure~\ref{fig:b}` | pick one (either is fine) and use it throughout. | reviewers notice cross-reference style drift; pick one. |
| `NAMEREF_USE` | info | any occurrence of `\nameref{X}`. | `\nameref{sec:method}` | confirm — `\nameref` prints the section title, which can become stale if the title changes. | rare macro; flag for human review rather than auto-fix. |
| `LABEL_INSIDE_VERBATIM` | info | a `\label{}` is detected inside `\begin{verbatim}...\end{verbatim}` / `\begin{lstlisting}...\end{lstlisting}` / `\verb|...|` / a `%`-comment line. These are **false positives** — the skill must suppress them. Flagged as `info` purely so the audit trail shows the suppression happened. | `\begin{verbatim} \label{fake} \end{verbatim}` | nothing — confirms the parser excluded it. | proves the verbatim-skip pass ran; useful when debugging false positives. |

**Total: 14 rules.** Counts: 5 label-hygiene, 4 reference-hygiene, 2 counter/float, 3 style.

## 5. Procedure

### 5.1 Discover the source set

```
Glob "manuscript/sections/**/*.tex"
Glob "manuscript/main.tex"
Glob "manuscript/preamble.tex"
```

For `/scholar:paper-venue`, swap the prefix to `submissions/<venue>/`.

Resolve `\input{X}` / `\include{X}` / `\subfile{X}` directives from `main.tex` to determine the **canonical reading order**. The reading order matters for `FIGURE_NUMBER_GAP` and `TABLE_FIRST_USE_BEFORE_DEF`.

### 5.2 Strip non-LaTeX regions

Build a per-file mask that excludes:

- lines starting with `%` (after leading whitespace); also inline `% ...` from the first un-escaped `%` to EOL;
- the body of `\begin{verbatim} ... \end{verbatim}`;
- the body of `\begin{lstlisting} ... \end{lstlisting}`;
- the body of `\verb|...|` and `\verb*|...|`;
- the body of `\begin{comment} ... \end{comment}` (the `comment` package);

Any later regex pass operates on the **masked** view. Findings re-cite the **original** line number (not the masked one).

### 5.3 Build the label set

```
Grep -nE '\\label\{[^}]+\}' <masked-source>
```

For each hit: `labels[key].append((file, line))`. After the sweep:

- `LABEL_DUPLICATED`: any key with `len(value) > 1`.
- `LABEL_PREFIX_CONVENTION`: bucket labels by enclosing environment (figure / table / equation / section / algorithm — detected by the nearest preceding `\begin{...}` or `\section{...}`); derive the dominant prefix per bucket; flag drift.

### 5.4 Build the ref set

```
Grep -nE '\\(ref|eqref|autoref|nameref)\{[^}]+\}' <masked-source>
```

For each hit: record `(macro, key, file, line)`.

- `REF_BROKEN`: `\ref{X}` / `\autoref{X}` / `\nameref{X}` where `X ∉ labels`.
- `EQREF_BROKEN`: `\eqref{X}` where `X ∉ labels`.
- `REF_MIXED_KIND`: macro vs prefix mismatch per the rule table.
- `NAMEREF_USE`: every occurrence (info).
- `LABEL_ORPHANED`: labels with zero entries in the ref set.

### 5.5 Build the cite set + resolve against bib

```
Grep -nE '\\cite[a-z]*\{[^}]+\}' <masked-source>
```

Multi-key cites split on `,`. Read the bib key set from `references.bib` (Grep `^@\w+\{([^,]+),`) — or delegate to `bib-manager`'s parser.

- `CITE_BROKEN`: cite keys not in the bib key set.

### 5.6 Caption / label placement

For each `\begin{figure}` / `\begin{figure*}` / `\begin{table}` / `\begin{table*}` block:

1. Find the (first) `\caption{...}` line within the env.
2. Find the (first) `\label{...}` line within the env.
3. If both exist and `label_line < caption_line`: emit `LABEL_PLACEMENT_FIGURE` / `LABEL_PLACEMENT_TABLE`.

### 5.7 Float order

Walk floats in `\input` reading order. Record, per float-key, the source position where it was **defined**. Then walk refs in the same reading order; emit `FIGURE_NUMBER_GAP` / `TABLE_FIRST_USE_BEFORE_DEF` for refs whose target is defined **later** in reading order.

### 5.8 Style passes

`AUTOREF_INCONSISTENT_USE`: count `\autoref{prefix:*}` vs `\ref{prefix:*}` per prefix; if both > 0, flag every minority-side occurrence.

### 5.9 Emit

Write `.log` + `.findings.json` under `.evidraft/manuscript/`. Print to chat:

```
xref-audit: <m> fail, <n> warn, <k> info  (.evidraft/manuscript/xref_audit-<ts>.log)
  labels:  defined=<a>  duplicated=<b>  orphaned=<c>
  refs:    resolved=<d>  broken=<e>
  cites:   resolved=<f>  broken=<g>
```

## 6. Quality checklist

- [ ] Comments (`% ...`) and verbatim / lstlisting envs excluded from every Grep pass (verified by the `LABEL_INSIDE_VERBATIM` self-test rule).
- [ ] `\input` / `\include` chain followed; cross-file references resolve.
- [ ] Source line numbers in findings refer to the **original** file, not a masked view.
- [ ] `labels.defined + labels.duplicated` ≥ unique label count; sums in the JSON header reconcile with the per-rule findings.
- [ ] `CITE_BROKEN` cross-checked against `references.bib` (not against `.aux`).
- [ ] When called with `run_id`, the value lands at the top level of `findings.json`.

## 7. Anti-patterns

- Reading `.aux` files. Those are compile artefacts; if the manuscript was edited after the last compile they are stale, and `xref-audit` is meant to be runnable **without** a fresh compile.
- Auto-fixing labels. An orphan label may be a deliberate placeholder for a section the author is still drafting.
- Failing on `\autoref` vs `\ref` style. Both are legitimate; the rule is **consistency**, not a particular choice.
- Treating `\label` inside `\begin{verbatim}` as real. The mask exists for exactly this reason.
- Renaming a `\cite{}` key to make it match the bib. That belongs to `bib-manager`, not here.
- Re-implementing `latex-build`'s `MISSING_REF` / `MISSING_CITE` parsing from `main.log`. `xref-audit` is static analysis; `latex-build` parses the compiler's view. Both views are useful; do not merge them.
