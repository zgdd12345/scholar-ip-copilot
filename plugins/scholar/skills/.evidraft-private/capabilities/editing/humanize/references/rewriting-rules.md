# Rewriting rules — R1 through R15

The polisher applies these rules, in this order. Each rule has a short id used in the per-hunk rule trace (see [diff-log-spec.md](diff-log-spec.md)).

## Mandatory (R1-R12)

1. **R1-vary-sentence-length.** Mix short (≤ 10 words) and long (≥ 25 words) sentences. If three or more consecutive sentences fall in the 15–22 word band (the AI-monotone band), break or merge.
2. **R2-cut-hedge-padding.** Delete openers like `it is important to note that`, `it is worth noting that`, `it should be emphasised that`, `notably`, `clearly`, `obviously` when they carry no information.
3. **R3-one-idea-per-sentence.** A sentence stating two unrelated points is split. A sentence with two main verbs joined by "and" that span different claims is split.
4. **R4-replace-nominalisation-with-verb.** `we performed an evaluation of X` → `we evaluated X`. `the determination of Y is made by Z` → `Z determines Y`. Preserve agent identity; do not flip first-person to third-person.
5. **R5-no-bullet-lists-unless-source-was-a-list.** If the original prose is paragraph form, do not introduce bullets. If the original was a list, keep it.
6. **R6-preserve-numbers-verbatim.** Numeric literals (digits, `n=128`, `p < 0.05`, `81.3`, `+2.4 pts`, `up to 4×`) are byte-identical between original and rewrite. No rounding. No unit normalisation.
7. **R7-preserve-citation-keys-verbatim.** `\cite{key}` / `\citep{key}` / `\citet{key}` / `\cref{...}` / `\ref{...}` / `\label{...}` / `\eqref{...}` and inline `ev_NNNN` markers are byte-identical.
8. **R8-preserve-named-entities-verbatim.** Dataset names (ImageNet, COCO, GLUE), model names (ResNet-50, GPT-4o), author surnames, place names, and any entry in `evidence.jsonl` with `tags: [entity]` are byte-identical.
9. **R9-preserve-empirical-hedges.** Adverbs / modal verbs that hedge an empirical claim — `may`, `suggests`, `appears to`, `tends to`, `approximately`, `up to`, `roughly`, `on average` — are preserved when the surrounding sentence contains a digit, a comparative verb, or a `\cite{}`. Hedges on opinion / framing may be cut.
10. **R10-no-new-claims.** A hunk that introduces a factual statement not present in the original is rejected. The polisher rewrites; it does not extend.
11. **R11-paragraph-count-pm-1.** Across a single section file, paragraph count after the rewrite is within ±1 of the original. Larger structural change is `latex-editor`'s job, not the polisher's.
12. **R12-inherit-voice.** First-person plural ("we") vs third-person impersonal ("the method") is inherited from the source per-paragraph. The polisher does not switch voice.

## Optional (R13-R15) — apply when the relevant signal is present

13. **R13-prefer-active-over-passive.** When the agent of the action is named in the same sentence, prefer active voice. Do not invent an agent to "fix" a passive sentence.
14. **R14-no-throat-clearing-openers.** Drop sentence-initial `In this paper,`, `In this work,`, `To this end,`, `Furthermore,`, `Moreover,` when the paragraph context already supplies the connection.
15. **R15-emit-rule-trace.** Every emitted hunk carries a non-empty `rules_fired[]` list referencing the rule ids above. A hunk with no rules fired is the original — do not emit it.
