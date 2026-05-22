---
id: reading-list
title: "Lite literature reading list"
description: >
  Lightweight literature research: query arXiv, Semantic Scholar, OpenAlex,
  and an optional blog allow-list; verify each candidate via WebFetch; emit
  ONE markdown reading-list file at .evidraft/notes/<slug>-<date>.md. No
  BibTeX, no evidence.jsonl, no audit chain — intended for personal
  reference reading rather than paper drafting. For publish-grade output
  use /scholar:paper-lit instead; for PRISMA-style systematic review use
  /scholar:deepresearch. If the target path already exists, the command
  surfaces a reuse/augment/overwrite triage instead of silently overwriting.
kind: command
slash: /scholar:reading-list
phase: shared
inputs:
  - name: topic
    type: string
    optional: false
    description: >
      The search topic / question. Used verbatim as the query and slugged
      for the output filename.
  - name: max
    type: integer
    optional: true
    default: 20
    description: Maximum number of candidates to consider (before verification rejects).
  - name: out
    type: path
    optional: true
    description: >
      Override the default output path. Default:
      .evidraft/notes/<topic-slug>-<UTC-date>.md
outputs:
  - path: .evidraft/notes/<topic-slug>-<date>.md
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, "Bash:mkdir*", "Bash:date*"]
hooks: []                          # lite path: no citation-guard, no evidence-consistency, no scope-required
subagents: [literature-reviewer]
references:
  - doc: ../skills/scholar-search/SKILL.md
  - doc: ../agents/literature-reviewer.md
---

# /scholar:reading-list

Build a personal literature reading list. No project init, no BibTeX, no evidence chain, no audit cascade. The output is ONE markdown file that you read and edit yourself.

## When NOT to use this command

- Building toward a paper submission → use `/scholar:paper-lit` (populates `references.bib` + `evidence.jsonl` + runs audit chain).
- Need a PRISMA-style systematic review with cluster critique → use `/scholar:deepresearch`.
- Drafting a related-work section in LaTeX → use `/scholar:paper-review`.

## Steps

1. **Resolve topic, slug, date.**
   - Use the `topic` argument verbatim as the search query.
   - `<topic-slug>` = lowercase the topic, replace non-alphanumeric with `-`, collapse repeats, trim leading/trailing `-`.
   - `<date>` = `date -u +%Y-%m-%d`.

2. **Resolve output path.**
   - If `out` is supplied, use it.
   - Otherwise default to `.evidraft/notes/<topic-slug>-<date>.md`.
   - `mkdir -p` the parent directory. Do **not** create `.evidraft/project.yaml`. The lite path runs in any directory.

2a. **If the resolved output path already exists and is non-empty, do NOT overwrite silently.** Read the existing file's header (first ~10 lines) and surface three options to the user in chat:

   - **reuse** — keep the existing file as-is; abort the command and point the user at the file path.
   - **augment** — generate a new file at `.evidraft/notes/<topic-slug>-<refine-tag>-<date>.md` where `<refine-tag>` is a short slug derived from the user's narrowing intent (e.g. `2024-2026-transformer-only`); leave the existing file untouched. This is the default for "narrow the scope" or "look at the new papers" follow-ups. **If the user gave no narrowing intent** (e.g. just said "augment" or "option 2"), ask ONE clarifying question to elicit a tag before proceeding — do not invent a tag. **If the augment path itself already exists** at the resolved `<refine-tag>-<date>` combination, append a numeric disambiguator (`-2`, `-3`, …) until unique.
   - **overwrite** — proceed to Step 3 and replace the existing file. Only do this if the user explicitly says "覆盖" / "overwrite" / "refresh in place". Never default to this.

   Do NOT proceed to Step 3 until the user picks one. The `out` argument bypasses this check only if `out` resolves to a path that does NOT already exist; if `out` points at an existing file, the same triage still applies.

3. **Retrieve candidates.** Load the `scholar-search` skill and request up to `max` candidates (default 20) across arXiv, Semantic Scholar, OpenAlex. The skill's `webfetch` variant is allowed for non-paper sources (engineering blogs, vendor docs, practitioner posts).

4. **Dispatch the `literature-reviewer` subagent** with these instructions:
   - Topic: the resolved topic.
   - **Mandatory per-candidate verification**: for every candidate the subagent MUST `WebFetch` the canonical URL and confirm the title + first author against its own metadata BEFORE the candidate is included. Any candidate that fails verification is rejected with a one-sentence reason. A failed verification is NEVER silently downgraded to "low confidence" — it is a rejection.
   - Cluster the included candidates into ≤6 method families.
   - Return the file body using the schema below.
   - Append the rejection list at the bottom under `## Rejected candidates`, one bullet per rejection.

5. **Write the file.** Single markdown file at the path from step 2. Schema:

   ```markdown
   # Reading list: <topic>

   - Generated: <UTC date>
   - Source providers: arxiv, semantic-scholar, openalex[, webfetch]
   - Topic source: command argument
   - Verification: every entry below was WebFetch-verified against its canonical URL

   ## Method families

   - **Family A — <name>**: <one-sentence cluster description>
   - **Family B — <name>**: …

   ## Entries

   ### <Title>
   - **Authors**: <names>
   - **Year / Venue**: <year> / <venue or arXiv class>
   - **URL**: <canonical URL>
   - **Summary**: <2-3 sentences from the verified page>
   - **Why relevant**: <one sentence tying back to topic>

   ### <next entry>
   …

   ## Rejected candidates

   - <Title or guessed identifier> — <one-sentence reason>
   ```

6. **Report back** in chat (≤120 words):
   - Path written.
   - N candidates considered / N verified / N rejected.
   - The method-family names.
   - One-line next step, **verbatim** (the subagent must emit this sentence exactly, not paraphrase it; do not substitute another `/scholar:<cmd>`): `If you later decide to write a paper section on this topic, run /scholar:paper-init then /scholar:paper-lit.`
   - Do NOT name `citation-guard`, `evidence-consistency`, or `scope-required` in the report — those hooks are disabled in lite mode by the per-command opt-out in `_lib.sh::hook_disabled_by_command`, and naming them confuses the user about the lite-path workflow.
   - **Sibling file** (only if the Step 2a triage resolved to `augment`): name the prior file path that was left untouched.

## Constraints

- **Never** invent a paper, author, year, venue, or URL. If a field cannot be verified by WebFetch, drop the candidate; do not emit a TODO entry. Verifying-then-rejecting is the correct outcome when an arXiv id or DOI does not match.
- **Never** write to `references.bib`, `evidence.jsonl`, `matrix.md`, `manuscript/`, or `project.yaml`. The lite path explicitly does NOT integrate with those.
- The output file is the ONLY artefact (the parent directory under `.evidraft/notes/` may be auto-created if missing).
- Hooks `citation-guard`, `evidence-consistency`, `scope-required` do NOT apply (the command declares `hooks: []`). The "verify-then-reject" rule in step 4 is the substitute discipline against hallucination.

## Done criteria

- Output file exists at the resolved path.
- Every `### <Title>` block carries Authors + Year/Venue + URL + Summary + Why-relevant. No partial / TODO blocks.
- `## Rejected candidates` section exists (may be empty).
- No writes outside the output file and its parent directory.
- Chat report names the file path and the considered/verified/rejected counts.
- If the resolved output path existed at start of run, the user-selected triage outcome (reuse/augment/overwrite) is named in the chat report.
