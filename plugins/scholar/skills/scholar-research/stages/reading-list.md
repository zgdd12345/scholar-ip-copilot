# workflow:research.reading-list

Build a personal literature reading list. No project init, no BibTeX, no evidence chain, no audit cascade. The output is ONE markdown file that you read and edit yourself.

## When NOT to use this command

- Building toward a paper submission → use `workflow:paper.lit` (populates `references.bib` + `evidence.jsonl` + runs audit chain).
- Need a PRISMA-style systematic review with cluster critique → use `workflow:research.deep`.
- Drafting a related-work section in LaTeX → use `workflow:paper.review`.

## Steps

1. **Resolve topic, slug, date.**
   - Use the `topic` argument verbatim as the search query.
   - `<topic-slug>` = lowercase the topic, replace non-alphanumeric with `-`, collapse repeats, trim leading/trailing `-`.
   - `<date>` = `date -u +%Y-%m-%d`.

2. **Resolve output path.**
   - If `out` is supplied, use it.
   - Otherwise default to `.evidraft/notes/<topic-slug>-<date>.md`.
   - `mkdir -p` the parent directory. Do **not** create `.evidraft/project.yaml`. The lite path runs in any directory.

2a. **Resolve collisions without surprising the user.** Never silently replace a
   non-empty file.

   - If the default path is non-empty, select an automatic unique sibling without
     pausing: append a numeric suffix before `.md` (`-2`, `-3`, and so on) until the
     path is unused. Leave every existing note untouched and report both paths.
   - If explicit `out` is non-empty, read its header and ask for confirmation before
     replacing it. The user may instead keep it unchanged or choose a unique sibling.
     Treat overwrite approval as applying only to that concrete explicit path.
   - An empty existing file may be used after normal workspace preparation; it never
     authorizes replacing a non-empty sibling.

3. **Retrieve candidates.** Load the `scholar-search` skill and request up to `max`
   candidates (default 20) across arXiv, Semantic Scholar, and OpenAlex. The skill's
   `webfetch` variant is allowed for non-paper sources. When network access or WebFetch
   is unavailable, do not invent metadata: write the one output note with an
   `## Evidence boundary` section naming the unavailable providers, the fact that no
   entries were verified, and a recovery action. Return `complete_with_gaps`.

4. **Review retrieved candidates.** The coordinator may handle a small result directly
   or dispatch `literature-reviewer` when independent review materially helps. Dispatch
   according to task independence, with no fixed cardinality, waves, or retry count.
   Supply these instructions when delegating:
   - Topic: the resolved topic.
   - **Per-candidate verification**: before inclusion, `WebFetch` the canonical URL and
     confirm title and first author. Reject a mismatch with a one-sentence reason. If
     verification is unavailable, include no unverified entry and use the evidence-boundary
     path from step 3.
   - Cluster the included candidates into ≤6 method families.
   - Return the file body using the schema below.
   - Append the rejection list at the bottom under `## Rejected candidates`, one bullet per rejection.
   - **Author truncation**: if a verified entry has more than 8 authors, render the `**Authors**:` field as the first three names followed by `, et al. (N authors)` instead of dumping the full list. The canonical URL still resolves the full author list — this is purely signal-to-noise hygiene.
   - **Rejection metadata discipline**: every `## Rejected candidates` bullet MUST include a square-bracketed tag immediately after the title — either `[<verified canonical URL>]` (the URL was actually `WebFetch`-resolved) or `[canonical metadata not confirmed]` (no resolved URL). Never assert an author name, arXiv id, year, or venue inside a rejection bullet unless the canonical URL was confirmed; otherwise the rejection section becomes a vector for the very fabrication the verify-then-reject rule exists to prevent.

5. **Write the file.** Single markdown file at the path from step 2. Schema:

   ```markdown
   # Reading list: <topic>

   - Generated: <UTC date>
   - Source providers: arxiv, semantic-scholar, openalex[, webfetch]
   - Topic source: command argument
   - Verification: <verified entries and unavailable-provider boundary>

   ## Method families

   - **Family A — <name>**: <one-sentence cluster description>
   - **Family B — <name>**: …

   ## Entries

   ### <Title>
   - **Authors**: <names; if N > 8 authors, render as the first 3 names then ", et al. (N authors)">
   - **Year / Venue**: <year> / <venue or arXiv class>
   - **URL**: <canonical URL>
   - **Summary**: <2-3 sentences from the verified page>
   - **Why relevant**: <one sentence tying back to topic>

   ### <next entry>
   …

   ## Rejected candidates

   - <Title or guessed identifier> [<verified canonical URL> OR "canonical metadata not confirmed"] — <one-sentence reason>

   ## Evidence boundary

   - <providers attempted, unavailable checks, unsupported coverage, and recovery action>
   ```

6. **Report back** in chat (≤120 words):
   - Path written.
   - N candidates considered / N verified / N rejected.
   - The method-family names.
   - Final status: `complete`, `complete_with_gaps`, or `blocked`.
   - One-line next step, **verbatim** (the subagent must emit this sentence exactly, not paraphrase it; do not substitute another `workflow:<id>`): `If you later decide to write a paper section on this topic, run workflow:paper.init then workflow:paper.lit.` If the surrounding chat is in a non-English language (e.g. Chinese), emit the English sentence on its own line first, then add a translation BELOW it — never replace the English with the translation. The verbatim line is the machine-readable handoff to the next workflow stage.
   - Do not name internal policies in the report. This action declares no publish policies; naming them would confuse the user about the lightweight workflow.
   - **Sibling file** (only when the default path collided): name the prior file path
     that was left untouched and the automatic unique sibling that was written.

## Constraints

- **Never** invent a paper, author, year, venue, or URL. Do not invent metadata when
  retrieval or verification is unavailable. Drop unverifiable candidates; record the
  boundary without emitting a candidate-shaped TODO entry.
- **Never** write to `references.bib`, `evidence.jsonl`, `matrix.md`, `manuscript/`, or `project.yaml`. The lite path explicitly does NOT integrate with those.
- The output file is the ONLY artefact (the parent directory under `.evidraft/notes/` may be auto-created if missing).
- This action declares no publish policies. The "verify-then-reject" rule in step 4 is its explicit discipline against hallucination.

## Done criteria

- Output file exists at the resolved path.
- Every `### <Title>` block carries Authors + Year/Venue + URL + Summary + Why-relevant. No partial / TODO blocks.
- `## Rejected candidates` section exists (may be empty).
- No writes outside the output file and its parent directory.
- Chat report names the file path and the considered/verified/rejected counts.
- If the default output path existed at start, the report names the automatic unique
  sibling. If explicit `out` existed, the report names the user's confirmed outcome.
- Status is `complete` when requested entries are verified, `complete_with_gaps` when
  network or verification gaps are recorded in the note, or `blocked` only when workspace
  safety prevents the output write.
