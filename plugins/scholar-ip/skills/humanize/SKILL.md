---
id: humanize
title: "Williams-style prose polish: rules, banned phrases, ethics, model routing, diff log"
kind: skill
phase: paper
description: >
  Loaded by /scholar:polish. Ships ~12 concrete rewriting rules (Williams /
  Pinker / Strunk lineage), a banned-phrase lint list (≥15 AI-tell n-grams),
  the verbatim academic-integrity ethics block, the external-model routing
  config under .evidraft/project.yaml.style.humanize.*, and the unified-diff
  log specification. Not a detector-evasion tool.
triggers:
  - "/scholar:polish"
  - "polishing manuscript prose"
  - "reducing AI-flavour in a draft"
  - "running the prose-polisher agent"
provides:
  - rewriting-rules
  - banned-phrase-list
  - ethics-block
  - external-model-routing
  - diff-log-spec
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [humanize-evidence-preserve, citation-guard, evidence-consistency]
references:
  - doc: ../../../../docs/legal-and-ethics.md
  - doc: ../../agents/prose-polisher.md
  - doc: ../../hooks/humanize-evidence-preserve.md
  - doc: ../evidence-check/SKILL.md
---

# humanize

## When to use

Loaded whenever `/scholar:polish` runs, or whenever an agent considers a "make this read more naturally" pass on a draft. The skill is the single source of truth for the rules, the banned-phrase list, the ethics statement, the model-routing config, and the diff-log shape. The command and the `prose-polisher` agent both defer to it.

## Inputs

- the target prose file(s) under `manuscript/` (typically `manuscript/sections/*.tex` or `manuscript/main.tex`),
- `.evidraft/evidence/evidence.jsonl` (filter `type=note` with `tags: [entity]`) — named entities to preserve verbatim,
- `.evidraft/project.yaml` `style.humanize.*` — model routing and per-project knobs,
- environment variables for the configured provider (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; Ollama needs none).

## Outputs

- a stream of hunks emitted by the `prose-polisher` agent,
- `.evidraft/style/humanize-<ts>.log` — unified diff with per-hunk rule trace,
- `.evidraft/style/humanize-<ts>.report.md` — human-readable change report (banned-phrase counts, evidence diff verdict, ethics block).

## Procedure

### 1. Rules (numbered)

The polisher applies these rules, in this order. Each rule has a short id used in the hunk rule trace.

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

Optional R13-R15 (apply when the relevant signal is present):

13. **R13-prefer-active-over-passive.** When the agent of the action is named in the same sentence, prefer active voice. Do not invent an agent to "fix" a passive sentence.
14. **R14-no-throat-clearing-openers.** Drop sentence-initial `In this paper,`, `In this work,`, `To this end,`, `Furthermore,`, `Moreover,` when the paragraph context already supplies the connection.
15. **R15-emit-rule-trace.** Every emitted hunk carries a non-empty `rules_fired[]` list referencing the rule ids above. A hunk with no rules fired is the original — do not emit it.

### 2. Banned phrases (lint list)

These n-grams are flagged in the lint pass before rewriting and counted in the report (before / after). Each entry below has a one-line justification — the phrase is a public AI-tell (i.e., it shows up disproportionately in LLM output relative to human-edited academic prose; sources: public detector feature lists, the Stanford / Sheffield AI-fingerprint studies, and the andrehuang/prose-polisher seed list).

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

Lint behaviour:

- Match is case-insensitive, word-boundary anchored.
- The lint pass only **counts** occurrences; it does not auto-delete. The rewrite pass is what actually changes prose.
- The report records counts before and after; a banned-phrase count that stays positive after rewrite is surfaced in chat as "residual banned phrases — review manually".
- If a banned phrase appears inside a `\verb|...|`, a `\begin{lstlisting}` block, a `$...$` math span, or a `\cite{}` key, it is not counted. Phrases inside prose are.

### 3. Ethics block (ships verbatim)

Every `.evidraft/style/humanize-<ts>.report.md` ends with the following block, byte-identical:

```
EviDraft humanize is a Williams-style polish tool, not a detector-evasion tool. Users MUST comply with venue AI-disclosure policies (ICML / NeurIPS / ACL / IEEE) and institutional authorship rules. The skill refuses if invoked with `--evade-detector` or similar flags.
```

The `/scholar:polish` command also prints the shorter chat-line reminder ("EviDraft polish is a Williams-style style tool, not a detector-evasion tool. Your venue's AI-disclosure policy is your responsibility (ICML / NeurIPS / ACL / IEEE all require disclosure).") after writing the report.

Refusal triggers (the command exits non-zero, the rewrite pass does not run):

- the invocation includes `--evade-detector`, `--bypass-gptzero`, `--humanize-for-detection`, `--fool-ai-detector`, `--evade-ai-detection`, or any string matching `(?i)(evade|bypass|fool|defeat).{0,20}(detect|gptzero|originality|turnitin)`;
- the chat-side request explicitly asks for detector evasion ("rewrite this so GPTZero doesn't flag it").

The refusal message echoes the verbatim ethics block above and lists the standard venue policies for ICML, NeurIPS, ACL, and IEEE.

### 4. External-model routing config

The model used for the rewrite pass is configured in `.evidraft/project.yaml` under `style.humanize.*`. NO real keys live in the repo; the user supplies keys via environment variables.

```yaml
style:
  humanize:
    model: anthropic:claude-sonnet-4-6     # default; falls back to in-host if env var missing
    fallback_chain:
      - openai:gpt-4o-mini
      - local:ollama/qwen2.5-7b
    preserve_citations: true               # always true in this skill; included for forward compatibility
    max_delta_ratio: 0.35                   # hard ceiling on (changed tokens / total tokens) per hunk
```

Env vars required per provider:

| Provider prefix | Required env var | Notes |
|---|---|---|
| `anthropic:` | `ANTHROPIC_API_KEY` | If unset, fall back to the next entry in `fallback_chain`. |
| `openai:` | `OPENAI_API_KEY` | If unset, fall back. |
| `local:ollama/...` | none | Requires a running local Ollama; if the daemon is unreachable, fall back. |
| `<none configured>` | none | Use the in-host LLM (the agent's own model). |

Resolution algorithm:

1. Read `model`. If its env var is set (or it is a local model), use it.
2. Otherwise walk `fallback_chain` in order; the first entry whose env var is present (or whose local backend is reachable) wins.
3. If every entry in the chain is unavailable, **fall back silently to the in-host LLM and log a warning to chat**. The command never blocks on missing keys.
4. The resolved model id is written to the report under `# Summary` so the user can audit which backend produced the rewrite.

No real keys, no hard-coded account URLs, no telemetry. The plugin reads the env var; it never echoes it.

### 5. Diff log spec

Two files per invocation, both under `.evidraft/style/`:

**`humanize-<ts>.log`** — unified diff format. One block per hunk:

```
--- manuscript/sections/introduction.tex
+++ manuscript/sections/introduction.tex
@@ -42,4 +42,4 @@
-It is important to note that our method outperforms the baseline by 4.2 points.
+Our method outperforms the baseline by 4.2 points.
# rules: R2-cut-hedge-padding, R3-one-idea-per-sentence
# delta_ratio: 0.18
# preserve: ok
```

Per-hunk trailing comments are required:

- `# rules: <rule-id>[, <rule-id>...]` — non-empty.
- `# delta_ratio: <float>` — must be ≤ `max_delta_ratio`.
- `# preserve: ok|fail` — verdict from the `evidence-auditor` pass. `fail` hunks are recorded but not applied.

Hunks that the agent skipped (delta too large, self-check failed) are recorded as:

```
# skipped: delta-ratio-exceeded   (or: preserve-self-check-failed)
# original_lines: 42-47
```

**`humanize-<ts>.report.md`** — markdown summary. Section order is fixed:

1. `# Summary` — target file list, mode (`interactive` / `all` / `none`), resolved model id, total hunks proposed / accepted / blocked.
2. `# Banned-phrase counts` — table with columns `phrase`, `before`, `after`.
3. `# Per-hunk rule trace` — one row per emitted hunk: `file`, `line_range`, `rules_fired`, `delta_ratio`, `preserve`.
4. `# Evidence diff` — `PASS` if every emitted hunk passed the preserve pass; `FAIL` with the list of offending tokens otherwise.
5. `# Ethics` — the verbatim ethics block from section 3 above.

Timestamps (`<ts>`) are UTC, `YYYYMMDDTHHMMSSZ`. Two invocations in the same second use `<ts>` then `<ts>-v2`.

## Quality checklist

- [ ] Every hunk has a non-empty `rules_fired[]`.
- [ ] `delta_ratio ≤ max_delta_ratio` for every applied hunk.
- [ ] No applied hunk changed a numeric literal, `\cite{}` key, `ev_NNNN` marker, registered named entity, or empirical hedging adverb.
- [ ] Paragraph count drift within ±1 per section file.
- [ ] Voice (1st / 3rd person) matches source per paragraph.
- [ ] Banned-phrase count after rewrite is ≤ count before rewrite (no new banned phrases introduced).
- [ ] Report ends with the verbatim ethics block.
- [ ] The resolved model id is recorded in the report.

## Anti-patterns

- "Smoothing" a deliberate short sentence into a longer one to match surrounding cadence — Williams-style writing *requires* short sentences for rhythm.
- Replacing one banned phrase with another (`crucial` → `pivotal`). Both are on the list.
- Rounding `81.3` to `81` because the rewrite reads better. Numbers are protected.
- "Normalising" `\cite{he2016deep}` to a different key the polisher thinks is "more canonical". Keys are protected.
- Removing `may` from `our model may improve robustness` because it sounds less confident. The hedge is the claim.
- Introducing a bullet list to "clarify" a paragraph. R5 forbids it unless the source was a list.
- Running the polish on `.evidraft/` files (evidence store, claim charts, scope notes). The polisher edits manuscripts only.
- Treating this skill as a detector-evasion tool. The ethics block is shipped verbatim for a reason.

## Idea-level references

This skill draws on, but does not vendor, the following:

- Joseph M. Williams, *Style: Lessons in Clarity and Grace*. The sentence-level rules (R3, R4, R13) are the Williams lineage.
- Steven Pinker, *The Sense of Style*. The cadence / sentence-length rule (R1) and the "no throat-clearing" rule (R14) follow Pinker.
- William Strunk Jr. & E. B. White, *The Elements of Style*. The "cut empty words" rule (R2) and the bullet-list discipline (R5) follow Strunk.
- andrehuang's `prose-polisher` (open-source prompt set) — seeded the banned-phrase list. We re-implement the rules; we do not vendor the prompts.
- QuillBot, Wordtune — commercial style-rewriters. We borrow the *style* polish framing; we explicitly reject their occasional detector-evasion marketing.

All borrowings are conceptual. No third-party source is vendored at v0.1 (per `docs/legal-and-ethics.md` section 6).
