# Anti-patterns

- **Scoring `identical` on paraphrased prior art.** `identical` requires a verbatim quote in `overlap_passage`. When in doubt, downgrade to `high`. See [procedure-overlap.md](procedure-overlap.md).
- **Widening claim scope in `suggested_revision`.** Suggested rewrites are narrowing-only; the self-check refuses any rewrite that drops a noun present in the original element. See [procedure-risk-and-revise.md](procedure-risk-and-revise.md).
- **Auto-fixing the claim text.** This skill emits a chart; it never edits `claims.md` or `claims_parsed.json`. The drafter (`claim-drafter` agent) or the human applies revisions on a separate pass.
- **Silently dropping rows when spec/code support is missing.** The row stays, the empty cells stay, and the no-support override flips the row to `risk = high` so the gap is visible in the summary counters.
- **Citing prior-art passages that don't appear in `prior_art_map.md`.** Every `overlap_passage` must be a substring of the prior-art bullet's `summary` (or the bullet itself); inventing supporting quotes is a citation fabrication.
- **Re-implementing `claim-parser`'s element extraction.** The chart consumes `claims_parsed.json` as-is; if the parser is wrong the parser gets fixed, not patched here.
- **Probing the live patent record for the prior-art document.** The skill works entirely off `prior_art_map.md`; network probes would be slow, flaky, and would pull in claim text the map curator chose not to include.
- **Treating the chart as a patentability opinion.** It is reviewer convenience. The advisory paragraph in the SKILL.md "Advisory-only framing" section is not optional decoration.
