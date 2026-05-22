# Plan: Lite-mode literature research for EviDraft

Date: 2026-05-22
Status: proposal
Origin: dogfood1 session — `/scholar:paper-lit` + `/scholar:paper-review` chain triggered for a user request that turned out to be "personal lit research, no LaTeX". The audit chain caught a fabricated arXiv paper, but the pipeline took ~2 hours for what should have been a markdown reading list.

## Problem

The plugin assumes the terminal artefact is a publishable LaTeX paper. Every literature-touching command writes to `.evidraft/` + `manuscript/` and runs a 3-stage audit chain calibrated for publish-grade discipline. For personal reading research — the user's most common actual use case — this is over-engineered:

1. `paper-lit` auto-couples a markdown matrix to `references.bib` and `evidence.jsonl`, both only useful if you will later compile LaTeX.
2. `paper-review` only emits `.tex`. There is no markdown synthesis path.
3. `deepresearch` is gated behind `/scholar:brainstorming`, which is a Carlini-style "decide if you have a paper" gate.
4. The `literature-reviewer` subagent does not have `WebFetch` in its tool set; arXiv-id hallucinations slip past the audit chain unless the parent re-verifies. In the dogfood1 run, this leaked a wholly fabricated entry (`wang2025claudecode` against arXiv 2503.09747, which is actually a lattice-QCD paper).
5. There are TWO synced `references.bib` files (`.evidraft/literature/` and `manuscript/`); the duplication only exists for LaTeX compilation and is manually synced.
6. The `using-scholar-ip-copilot` skill's "first interaction" branch maps every request to a paper-init recommendation. No branch surfaces "this might be personal reading research".

## Goals

- Add a lightweight literature-research mode that emits a single markdown notes file with no bib, no evidence chain, no audit.
- Make intent disambiguation explicit before choosing the heavy vs. light path.
- Prevent the `literature-reviewer` subagent from hallucinating papers, by giving it `WebFetch` and enforcing per-paper URL verification before any append.

## Non-goals

- Remove the existing publish-grade pipeline. `paper-lit` / `paper-review` / `deepresearch` continue to exist for users who do want to publish.
- Change the patent workflow (this plan is paper / literature only).
- Build a markdown→LaTeX migration tool. If a user starts in notes mode and later decides to publish, that is a manual promotion; design the promotion later.

## P0 — `/scholar:reading-list` (new command)

**Surface.**

```
/scholar:reading-list <topic> [--max N] [--out PATH]
```

**Behaviour.**

1. No project init required. Runs in any directory.
2. Loads the `scholar-search` skill.
3. Dispatches `literature-reviewer` subagent (with `WebFetch` — see P1) to query arXiv + Semantic Scholar + OpenAlex + a configurable blog allow-list.
4. Subagent verifies each candidate by `WebFetch` on the canonical URL before accepting.
5. Writes ONE markdown file: `.evidraft/notes/<topic-slug>-<date>.md`. No bib, no `evidence.jsonl`, no audit chain.

**Output schema (one section per paper, ≤5 lines):**

```markdown
## <Title>
- **Authors**: <names>
- **Year / Venue**: <year> / <venue or arXiv class>
- **URL**: <canonical url>
- **Summary**: <2-3 sentence summary>
- **Why relevant**: <one sentence tying to topic>
```

Plus an opening `## Method families` section that clusters the entries (≤6 families).

**Done criteria.**

- Runs in a fresh directory with no `.evidraft/project.yaml`.
- Output file is the only artefact.
- No `citation-guard` / `evidence-consistency` / `scope-required` hooks fire.
- Subagent rejects every URL that does not WebFetch-verify; rejection appears in the report with a one-sentence reason.

## P0 — `using-scholar-ip-copilot` intent detection

**Change.** The skill's "first interaction" branch (step 2 of its body) gets a single intent question before the paper-init / patent-init recommendation:

> Is this for personal literature research (markdown notes only), or are you building toward a paper / patent? I can do either; they go through different paths.

**Skip heuristic.** Don't ask the question when context disambiguates:

- `.evidraft/project.yaml.status.manuscript` is `in_progress` or `done` → paper mode.
- `.evidraft/project.yaml.project_type` is `patent` or `mixed` → patent mode.
- The user's request explicitly names a venue, "投稿", "submit", "paper section", or similar → paper mode.

**Done criteria.**

- Existing project users don't see the new question.
- Fresh users see exactly one intent question, then a tailored recommendation: `reading-list` path for notes, `paper-init` path for paper.

## P1 — Give `literature-reviewer` subagent `WebFetch` + per-paper verification

**Change.** Edit `plugins/scholar-ip/agents/literature-reviewer.md`:

- `tools:` line adds `WebFetch`.
- Procedure adds a non-skippable verification step: for every candidate `citation_key`, the subagent MUST `WebFetch` the canonical URL and confirm the title + first author match its own metadata before the row is committed.
- Failed verification → row is rejected with a one-sentence reason in the report; never silently downgraded to `confidence: medium`.

**Acceptance test.** Reproduce the dogfood1 hallucination: feed the subagent a topic where similar fabrications are tempting (e.g. ask for "the Claude Code arXiv paper" when none exists). The subagent must NOT emit a fabricated entry; rejection with reason is the correct behaviour.

**Risk.** Per-paper `WebFetch` increases subagent runtime. Mitigate by caching responses within a single subagent run (subagent already keeps URL cache per its description).

## P1 — `paper-lit --mode={notes,paper}`

**Change.** Add a `mode` argument to `/scholar:paper-lit`. Default `notes`.

- `--mode=notes` → behaviour equivalent to `/scholar:reading-list`. No `references.bib` writes, no `evidence.jsonl` writes, no audit chain.
- `--mode=paper` → current behaviour. `paper-init` / `paper-draft` / `paper-review` invoke `paper-lit` with `--mode=paper` internally.

This is a strict superset of P0: P0 introduces the new command surface, P1 unifies the existing `paper-lit` to use the same machinery and gives publish-track users an explicit flag.

### Decision — 2026-05-22 (P1 WITHDRAWN)

After the dogfood1-driven Codex review (point #3, 2026-05-22) the
`--mode` flag was withdrawn rather than shipped. Three reasons:

1. **Don't break heavy-user muscle memory.** A `default: notes` flip
   would silently change what `/scholar:paper-lit topic` does — no
   more bib, no more evidence, no more audit chain — for every
   existing paper user. Equivalent breakage to /scholar:paper-review
   defaulting to `--format=md` (also rejected; see P3 status block).
2. **One lite entry is enough.** P0 already ships
   `/scholar:reading-list` as the lite entry. Adding a second lite
   entry under `paper-lit` would create the "which one do I use?"
   confusion this PR series was supposed to remove.
3. **The unification gain is theoretical.** P1's framing
   ("a strict superset of P0") presupposed a future where
   `paper-init` / `paper-draft` / `paper-review` would dispatch
   through `paper-lit --mode=paper`. None of those currently invoke
   `paper-lit` programmatically — they all run as separate
   user-driven commands — so there is no machinery to unify.

P1 stays in this plan as a historical record of the original
intention. The lite/heavy boundary that P1 wanted to express now
lives in the command split itself: `/scholar:reading-list` for lite,
`/scholar:paper-lit` for heavy. No flag.

## P2 — Auto-sync `manuscript/references.bib`

**Change.** Make `manuscript/references.bib` a symlink to `.evidraft/literature/references.bib` at `paper-init` time. Document the symlink in `project.yaml` comments.

**Windows fallback.** If symlinks are problematic, add a `paper-sync-bib` hook that runs on every `paper-draft` / `paper-venue` invocation and copies the file.

## P2 — Narrow `scope-required` hook

**Change.** Current default `block` on 6 commands (`paper-idea`, `patent-scout`, `paper-draft`, `patent-claims`, `deepresearch`, `polish`). Narrow `block` to commands that **actually write to `manuscript/`** (`paper-draft`, `patent-claims`, `polish`). Other gated commands (`paper-idea`, `patent-scout`, `deepresearch`) become `warn` by default.

**Rationale.** The hook exists to prevent unscoped writes from polluting publishable material. Analysis and retrieval commands don't write publishable material; warning is sufficient.

### Status — 2026-05-22 (P2 narrow-scope CLOSED)

Shipped in this PR series:

- `plugins/scholar-ip/hooks/scope-required.sh` computes a per-command
  default via a `case` on `$CMD` right after parsing the prompt:
  writers (`paper-draft` / `patent-claims` / `polish`) default `block`;
  analysers (`paper-idea` / `patent-scout` / `deepresearch`) default
  `warn`; any future gated command falls through to a safe `block`.
  `project.yaml.hooks.scope_required` still overrides everything
  project-wide.
- `plugins/scholar-ip/hooks/scope-required.md` carries a per-command
  table under `## Failure mode` and reframes the override section as
  "Per-project override" (no per-command override; one project-wide
  policy or accept the built-in split).
- `tests/test_adapter_conformance.py` invariant N exercises all four
  branches end-to-end via a bash subprocess against the rendered hook:
  per-command default split, YAML uplift (warn → block), YAML
  downgrade (block → warn), and `disabled` (all pass).

## P3 — `paper-review --format={md,tex}`

**Change.** Add `--format` to `/scholar:paper-review`. Default `md` (writes to `.evidraft/literature/related_work.md`). `--format=tex` opts into the LaTeX render.

When `--format=tex`, also auto-run the bib sync from P2.

### Status — shipped with default flip (2026-05-22)

Implemented in this PR series. `format` is an enum input on `/scholar:paper-review` (`tex` / `md`); `format=md` writes `.evidraft/literature/<target_section>.md` with Pandoc-style `[@key]` inline citations.

**Deviation from this plan.** Default is **`tex`**, not `md`. Rationale: `paper-review` is a paper-mode command (`phase: paper`) — running it presupposes `/scholar:paper-init` has scaffolded the manuscript tree, so by construction its audience already wants LaTeX. Flipping the default would silently change the output filename and extension for every paper user; mirrors the same "don't break heavy-user muscle memory" principle that kept `/scholar:paper-lit`'s default in paper mode (Codex review point #3, 2026-05-22). The lite path remains `--format=md` as an explicit opt-in.

**Bib sync auto-run.** Not added. The bib symlink that P2 ships at `paper-init` time already keeps `manuscript/references.bib` in sync with the canonical `.evidraft/literature/references.bib`, so `format=tex` does not need an additional sync step. If the symlink is missing (Windows fallback path), `paper-lit` step 6 already re-syncs on every run.

**citation-guard extension.** `hooks/citation-guard.sh` regex now accepts `[@key]` (Pandoc) in addition to `\cite{}` and `ev_NNNN`, so the hook fires identically on the new `.md` output. No bypass.

## Order of execution

P0 first (reading-list + intent detection): one PR. Unblocks the user's primary use case.

P1 second (literature-reviewer hardening + paper-lit mode flag): one PR. Closes the hallucination hole and unifies the lit-search machinery.

P2 third (bib sync + scope-required narrowing): one PR. Maintenance cleanup.

P3 last (paper-review markdown format): one PR. Migration path for existing paper users who want a md preview before LaTeX.

## Open questions

1. Should `/scholar:reading-list` write under `.evidraft/notes/` even without an `.evidraft/project.yaml`? **Tentative answer**: yes, auto-create the directory, do not auto-create `project.yaml`. The user's working tree convention is `.evidraft/` for scholar outputs even outside a fully-scaffolded project.
2. Should `--mode=notes` `paper-lit` run any audits? **Tentative answer**: no audit chain, but the per-paper `WebFetch` verification inside the subagent runs regardless of mode — that's hallucination defence, not publish-grade audit.
3. Does the intent question (P0) belong in the `using-scholar-ip-copilot` skill or in each gated command's prompt? **Tentative answer**: in the skill, fired at session start. Per-command would create question fatigue across a multi-command session.

## Acceptance per item

- P0 reading-list: end-to-end run on a fresh dir produces one md file; no other writes.
- P0 intent: dogfood1-style "我想调研 X" produces the intent question, not a 3-option paper-writing matrix.
- P1 literature-reviewer: re-run the dogfood1 topic; no fabricated entries appear in the output.
- P1 paper-lit mode: `paper-lit topic` with no flag does no bib/evidence writes; `paper-lit topic --mode=paper` matches current behaviour.
- P2 bib sync: editing `.evidraft/literature/references.bib` immediately reflects in `manuscript/references.bib`.
- P2 scope hook: running `/scholar:paper-idea` without a scope file emits a warning, not a refusal.
- P3 paper-review md: default invocation writes `related_work.md`; `--format=tex` writes `related_work.tex`.
