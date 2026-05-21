# Procedure — 9 steps

## 1. Discover the source set

```
Glob "manuscript/sections/**/*.tex"
Glob "manuscript/main.tex"
Glob "manuscript/preamble.tex"
```

For `/scholar:paper-venue`, swap the prefix to `submissions/<venue>/`.

Resolve `\input{X}` / `\include{X}` / `\subfile{X}` directives from `main.tex` to determine the **canonical reading order**. The reading order matters for `FIGURE_NUMBER_GAP` and `TABLE_FIRST_USE_BEFORE_DEF`.

## 2. Strip non-LaTeX regions

Build a per-file mask that excludes:

- lines starting with `%` (after leading whitespace); also inline `% ...` from the first un-escaped `%` to EOL;
- the body of `\begin{verbatim} ... \end{verbatim}`;
- the body of `\begin{lstlisting} ... \end{lstlisting}`;
- the body of `\verb|...|` and `\verb*|...|`;
- the body of `\begin{comment} ... \end{comment}` (the `comment` package);

Any later regex pass operates on the **masked** view. Findings re-cite the **original** line number (not the masked one).

## 3. Build the label set

```
Grep -nE '\\label\{[^}]+\}' <masked-source>
```

For each hit: `labels[key].append((file, line))`. After the sweep:

- `LABEL_DUPLICATED`: any key with `len(value) > 1`.
- `LABEL_PREFIX_CONVENTION`: bucket labels by enclosing environment (figure / table / equation / section / algorithm — detected by the nearest preceding `\begin{...}` or `\section{...}`); derive the dominant prefix per bucket; flag drift.

## 4. Build the ref set

```
Grep -nE '\\(ref|eqref|autoref|nameref)\{[^}]+\}' <masked-source>
```

For each hit: record `(macro, key, file, line)`.

- `REF_BROKEN`: `\ref{X}` / `\autoref{X}` / `\nameref{X}` where `X ∉ labels`.
- `EQREF_BROKEN`: `\eqref{X}` where `X ∉ labels`.
- `REF_MIXED_KIND`: macro vs prefix mismatch per the rule table.
- `NAMEREF_USE`: every occurrence (info).
- `LABEL_ORPHANED`: labels with zero entries in the ref set.

## 5. Build the cite set + resolve against bib

```
Grep -nE '\\cite[a-z]*\{[^}]+\}' <masked-source>
```

Multi-key cites split on `,`. Read the bib key set from `references.bib` (Grep `^@\w+\{([^,]+),`) — or delegate to `bib-manager`'s parser.

- `CITE_BROKEN`: cite keys not in the bib key set.

## 6. Caption / label placement

For each `\begin{figure}` / `\begin{figure*}` / `\begin{table}` / `\begin{table*}` block:

1. Find the (first) `\caption{...}` line within the env.
2. Find the (first) `\label{...}` line within the env.
3. If both exist and `label_line < caption_line`: emit `LABEL_PLACEMENT_FIGURE` / `LABEL_PLACEMENT_TABLE`.

## 7. Float order

Walk floats in `\input` reading order. Record, per float-key, the source position where it was **defined**. Then walk refs in the same reading order; emit `FIGURE_NUMBER_GAP` / `TABLE_FIRST_USE_BEFORE_DEF` for refs whose target is defined **later** in reading order.

## 8. Style passes

`AUTOREF_INCONSISTENT_USE`: count `\autoref{prefix:*}` vs `\ref{prefix:*}` per prefix; if both > 0, flag every minority-side occurrence.

## 9. Emit

Write `.log` + `.findings.json` under `.evidraft/manuscript/` (see [output-schemas.md](output-schemas.md)). Print to chat:

```
xref-audit: <m> fail, <n> warn, <k> info  (.evidraft/manuscript/xref_audit-<ts>.log)
  labels:  defined=<a>  duplicated=<b>  orphaned=<c>
  refs:    resolved=<d>  broken=<e>
  cites:   resolved=<f>  broken=<g>
```
