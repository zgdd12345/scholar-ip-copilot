# Banned-phrase lint list

These n-grams are flagged in the lint pass before rewriting and counted in the report (before / after). Each entry below has a one-line justification — the phrase is a public AI-tell (it shows up disproportionately in LLM output relative to human-edited academic prose; sources: public detector feature lists, the Stanford / Sheffield AI-fingerprint studies, and the andrehuang/prose-polisher seed list).

| Phrase | Why it's flagged |
|---|---|
| `delve` | High-frequency LLM verb; rarely used by careful human writers; usually `examine` or `study` is more honest about depth. |
| `tapestry` | Metaphor cliché; almost never appears in human ML/NLP papers; classic GPT-3.5 tell. |
| `navigate the landscape` | Empty motion metaphor; usually replaceable by the literal action ("survey", "compare"). |
| `pivotal` | Strong evaluative adjective with no measurable referent; AI-tell for hyped framing. |
| `crucial` | Same as `pivotal`; pads the claim without earning the emphasis. |
| `in conclusion` | LLM-style sectional flag; in a paper, the section heading already says it. |
| `moreover` | Connective inflation; usually `also` or no word at all suffices. |
| `furthermore` | Same as `moreover`; pairs of these in one paragraph is a strong AI signal. |
| `it is important to note that` | Pure padding; the importance should be shown, not asserted. |
| `it is worth noting that` | Same as above. |
| `unleash` | Marketing verb; never appropriate in academic prose. |
| `harness` | Marketing verb; replace with the concrete action ("use", "exploit"). |
| `realm of` | Empty domain metaphor; usually `field of` or just the noun. |
| `embark on` | Journey metaphor; usually `begin` or the literal verb. |
| `seamlessly` | Hand-waving adverb; if integration is seamless, show it; otherwise the word is a lie. |
| `cutting-edge` | Marketing adjective; the citation should establish recency, not the adjective. |
| `robust` (without quantitative support) | Frequently used by LLMs as a generic positive adjective; flag when no metric or confidence interval is nearby. |
| `paradigm shift` | Hyperbole almost always unsupported in a single paper. |
| `state-of-the-art` (without a `\cite{}` or `ev_NNNN`) | Already in `citation-guard`'s strong-claim list; the lint pass surfaces it here too. |
| `at the forefront of` | Marketing phrase; replace with the citation that establishes precedence. |

## Lint behaviour

- Match is case-insensitive, word-boundary anchored.
- The lint pass only **counts** occurrences; it does not auto-delete. The rewrite pass is what actually changes prose.
- The report records counts before and after; a banned-phrase count that stays positive after rewrite is surfaced in chat as "residual banned phrases — review manually".
- If a banned phrase appears inside a `\verb|...|`, a `\begin{lstlisting}` block, a `$...$` math span, or a `\cite{}` key, it is **not** counted. Phrases inside prose are.
