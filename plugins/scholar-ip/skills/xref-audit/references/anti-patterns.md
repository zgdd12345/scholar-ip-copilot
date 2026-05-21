# Anti-patterns

- Reading `.aux` files. Those are compile artefacts; if the manuscript was edited after the last compile they are stale, and `xref-audit` is meant to be runnable **without** a fresh compile.
- Auto-fixing labels. An orphan label may be a deliberate placeholder for a section the author is still drafting.
- Failing on `\autoref` vs `\ref` style. Both are legitimate; the rule is **consistency**, not a particular choice.
- Treating `\label` inside `\begin{verbatim}` as real. The mask exists for exactly this reason.
- Renaming a `\cite{}` key to make it match the bib. That belongs to `bib-manager`, not here.
- Re-implementing `latex-build`'s `MISSING_REF` / `MISSING_CITE` parsing from `main.log`. `xref-audit` is static analysis; `latex-build` parses the compiler's view. Both views are useful; do not merge them.
