# Anti-patterns

- **Auto-rewriting prose.** This skill reports; `latex-editor` agent applies fixes on a separate pass.
- **False positives from comments.** Every rule's regex must run against the **pre-filtered** view, never the raw file.
- **False positives from `verbatim` / `lstlisting`.** Same pre-filter; if you find yourself adding `# verbatim hack` to a single rule, your pre-filter is wrong.
- **Re-implementing `citation-guard`.** `STRONG_CLAIM_VERB_NO_CITE` echoes the hook's output. Two implementations of the same taxonomy will drift.
- **Rule inflation.** A rule earns its place only when (a) the regex is clean, (b) the false-positive shape is documented, and (c) you can paste a concrete failure example. Don't add "looks weird" rules.
- **Mixing severities arbitrarily.** Promoting a style-of-taste rule to `fail` because the manuscript happens to violate it once is how reviewers learn to ignore the tool.
- **Skipping the `findings.json` write because nothing fired.** The empty file is the audit-trail proof that the audit ran.
- **Running the audit on a `FAIL` compile.** Style findings on a non-building draft buries the real fix in noise.
