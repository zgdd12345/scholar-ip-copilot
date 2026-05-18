---
id: humanize-evidence-preserve
title: "Humanize evidence preserve"
kind: hook
phase: paper
triggers:
  - "/scholar:polish::rewrite-pass"
  - "subagent:prose-polisher::emit-hunk"
behaviour: "Token-level diff between original and rewrite for every hunk; block on any drift in numeric literals, citation keys, named entities, or empirical hedging adverbs."
failure_mode: block
references:
  - doc: ../skills/humanize/SKILL.md
  - doc: ../agents/prose-polisher.md
  - doc: ../agents/evidence-auditor.md
  - doc: ../../../docs/legal-and-ethics.md
---

# humanize-evidence-preserve

## When it fires

Any hunk emitted by the `prose-polisher` agent during the `/scholar:polish` rewrite pass. The hook runs *before* the hunk is applied to disk (in `mode=all`) or surfaced to the user for acceptance (in `mode=interactive`). In `mode=none` it runs anyway and writes its verdict to the log.

## Rules

For each hunk `{original_span, rewritten_span}`, compute the multiset of tokens in each of the four categories below. The hunk passes only if all four multisets are byte-identical between original and rewrite.

1. **Numeric literals.** Regex: `\b\d+(?:[.,]\d+)?(?:%|°|×|x|pts?|pp|ms|s)?\b`. Includes `81.3`, `n=128`, `p<0.05`, `+2.4 pts`, `up to 4×`, `0.5 ms`. The regex captures the magnitude, the separator, and the unit suffix; all must match.

2. **Citation keys.** Extract the brace contents of every `\cite{...}`, `\citep{...}`, `\citet{...}`, `\citealt{...}`, `\citeauthor{...}`, `\citeyear{...}`, and inline `ev_\d{4}` markers. Compare the key sets as multisets (a key cited twice in the original must be cited twice in the rewrite). `\ref{...}`, `\cref{...}`, `\eqref{...}`, `\label{...}` targets are also preserved.

3. **Named entities.** The entity list is the union of:
   - all `evidence.jsonl` rows with `type=note` and `tags` containing `entity` (the `claim` or `support` of each row supplies the canonical surface form),
   - a small built-in seed list of high-frequency ML/NLP entities the user typically does not register manually (dataset names: `ImageNet`, `COCO`, `Cityscapes`, `GLUE`, `SuperGLUE`, `LAION`; model names: `ResNet`, `BERT`, `GPT-4`, `Llama`, `Transformer`; org names: `OpenAI`, `Anthropic`, `Google`, `Meta`, `DeepMind`).
   The match is case-sensitive and word-boundary anchored. A rewrite that replaces `ImageNet` with `the ImageNet dataset` is allowed *only if* `ImageNet` is still present in the rewrite — the entity must appear, even if surrounding text changes.

4. **Empirical hedging adverbs.** The list: `may`, `might`, `can`, `suggests`, `appears to`, `tends to`, `approximately`, `up to`, `roughly`, `on average`, `under our settings`, `in our experiments`. A hedge is classified as "empirical" if its containing sentence contains:
   - a digit, OR
   - a comparative verb (`outperform`, `improve`, `match`, `exceed`, `reduce`, `increase`), OR
   - a `\cite{...}` / `ev_\d{4}` marker.
   Empirical hedges must appear in the rewrite with the same multiset. Hedges in non-empirical sentences (framing, opinion, motivation) are unprotected and may be cut by the rewrite pass.

Any drift in any of the four categories → the hook surfaces the offending tokens and blocks the hunk. Other hunks in the same invocation continue to be evaluated; one bad hunk does not abort the whole run.

## Failure mode

`block` by default — the hunk is rejected and the user / log sees:

```
humanize-evidence-preserve: BLOCKED
  file: <path>
  hunk_lines: <start>-<end>
  category: numeric | citation | entity | hedge
  original_tokens: [<token>, ...]
  rewritten_tokens: [<token>, ...]
  drift: [<added>, ...] / [<removed>, ...]
  suggestion: re-emit the hunk preserving the listed tokens; or skip this hunk
```

Blocked hunks are recorded in `.evidraft/style/humanize-<ts>.log` with `# preserve: fail` and are **never** applied to the target file, regardless of `mode`.

Downgrade path:

```yaml
hooks:
  humanize_evidence_preserve: warn   # was: enabled (== block); NOT recommended
```

When downgraded, the hook still logs the drift (in `humanize-<ts>.log` and `humanize-<ts>.report.md` under "Evidence diff"), but the hunk is allowed through. This is logged at chat-level as `WARN (downgrade in effect)` and recorded in `.evidraft/manuscript/paper_check_report.md` under "Hooks downgraded" so it surfaces on the next `/scholar:paper-check`. Downgrading this hook is treated as a discipline regression — the chat output explicitly recommends restoring `block`.

`failure_mode: audit` is **not** a supported value for this hook — the choice is `block` (default) or `warn`. There is no silent-pass mode.

## Adapter notes

- **Claude Code** — register as a sub-agent post-tool hook on the `prose-polisher` agent. The orchestrating `/scholar:polish` command treats the hook's `block` verdict as a hard rejection for the offending hunk and continues with the remaining hunks. The hook reads `.evidraft/evidence/evidence.jsonl` once per invocation to build the entity list.
- **Codex CLI** — Codex does not expose a sub-agent hook; the adapter inlines the four token-set checks into the `/scholar:polish` command body. Codex prompts must explicitly invoke `evidence-auditor` on every emitted hunk and require it to print a `preserve: ok|fail` line before the next hunk is considered.
- **OpenCode** — planned; the rule will register on the host's pre-write event scoped to the `/scholar:polish` invocation. Until the OpenCode adapter ships, the OpenCode path runs `/scholar:polish` in `mode=none` (dry-run only) and asks the user to apply hunks manually after reviewing the log.
