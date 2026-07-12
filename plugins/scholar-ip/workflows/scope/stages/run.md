# workflow:scope.run

Clarify **what the project is actually for** before any creative command runs. Produces a single dated scope artefact under `.evidraft/scope/` that downstream commands (`workflow:paper.idea`, `workflow:patent.scout`, `workflow:paper.draft`, `workflow:patent.claims`, and forward `workflow:research.deep`, `workflow:polish.run`) refuse to bypass — enforced by `policy:scope`.

The agent runs one question per message, never drafts content until the user has acknowledged each section, and produces a Pursue / Refine / Kill verdict based on internal consistency, not encouragement.

## Steps

1. **Explore context.** Read silently before asking anything:
   - `.evidraft/project.yaml` (project type, status, scope, and safety settings).
   - any existing `.evidraft/scope/*.md` (prior scope iterations).
   - any prior `.evidraft/ideas/*.md` artefacts.
   - if `branch=auto`: infer paper vs patent from `project.yaml.project_type`; if `mixed` or unclear, ask once.
2. **One question per message.** Hand control to the `brainstormer` subagent. Questions are drawn from the axes below in order; never batch.
   - **Paper branch (范围澄清 — Paper)**
     1. Target venue and audience (`target_venue`, reader background).
     2. One-sentence contribution (`if I had to tell a reviewer in one sentence, it is…`).
     3. Closest 3 prior works (`citation_key` if known, otherwise author+year).
     4. Claim of novelty against those 3 — what is the contrast?
     5. Evidence / evaluation plan — datasets, metrics, ablations, baselines.
     6. Hard constraints — deadline, page limit, ethics / IRB / dataset-licence issues.
   - **Patent branch (范围澄清 — Patent / 技术交底)**
     1. Technical field (`技术领域`) and product context.
     2. Problem solved (`所要解决的技术问题`).
     3. Inventive step vs. closest prior art (`相对现有技术的发明点`).
     4. Claim type — apparatus / method / computer-readable medium (CRM) / system.
     5. Target jurisdictions (CN / US / EP / WO / …) and filing horizon.
     6. Freedom-to-operate concerns — known competitor patents or products.
     7. Disclosure status — already public? confidential? employer / funder agreement?
3. **Carlini conclusion-first test.** Ask the user to draft the abstract (paper) or 技术交底书 summary (patent) **as if the work were complete**. Read it back, flag missing or hand-waved pieces, and confirm each gap is acknowledged. This is non-skippable in `full` mode.
4. **Propose 2–3 approaches with tradeoffs** for the stated contribution. Each approach gets: scope, evidence cost, riskiest assumption, fallback if it fails. The user picks one or asks for another round.
5. **Section-by-section approval.** Do **not** write the scope file yet. Walk each section in turn (frontmatter values, then prose sections) and wait for an explicit "ok" / "next" / "stop, enough" cue per section.
6. **Self-review pass.** Before writing the file, scan the assembled draft for:
   - placeholders / `TODO` / "TBD" the user has not signed off on,
   - contradictions between sections (e.g., claim of novelty contradicts the closest-prior-work list),
   - scope creep (sections describing work outside the one-sentence contribution),
   - ambiguous success criteria.
   Report findings to the user; only proceed when they are resolved or explicitly accepted.
7. **Write the scope file** to `.evidraft/scope/YYYY-MM-DD-<slug>.md`, where:
   - `YYYY-MM-DD` is today.
   - `<slug>` is a lowercase, hyphen-separated, ASCII summary of the contribution (≤ 6 words).
   The frontmatter follows the canonical schema in `../../../capabilities/research/brainstorming/spec.md`:
   ```yaml
   ---
   kind: paper            # or patent
   status: draft          # promoted to approved on user confirmation
   verdict: pursue        # one of: pursue | refine | kill
   riskiest_assumption: "<one sentence>"
   evidence_seeds: []     # citation_keys, file_paths, or ev_NNNN ids the user already trusts
   approved_date: null    # filled when status flips to approved
   staleness_until: <today + 14d>
   ---
   ```
   Followed by prose sections defined in the skill (paper or patent canonical lists).
8. **Ask the user to review** the written file. On explicit approval:
   - set `status: approved`,
   - set `approved_date: <today>`,
   - set `staleness_until: <today + scope.staleness_days>` (default 14, from `.evidraft/project.yaml.scope.staleness_days` if present).
9. **Terminal handoff.** Print exactly one recommended next command:
   - paper branch → `workflow:paper.lit`,
   - patent branch → `workflow:patent.scout`.
   Mention that downstream creative commands will refuse to run until the scope file is `approved` and not stale.

## Fast mode

If `mode=fast`, collapse the question set to **3 questions per branch**:

- Paper: (a) one-sentence contribution, (b) one concrete success criterion (metric + baseline + delta), (c) one hard constraint (deadline / page limit / ethics).
- Patent: (a) one-sentence inventive step, (b) claim type, (c) disclosure status.

Skip the Carlini conclusion-first test and the 2–3 approaches step. Still run the self-review pass. Write a minimal scope file with `verdict: pursue` (assumed) but `status: draft` — the user must still approve before the file unlocks downstream commands.

## Constraints

- Never draft method / experiments / claims in this command. Scope only.
- Never invent prior art, citations, or numbers. Unknown answers are recorded as `TODO` in the scope file, not guessed.
- Respect a "stop, enough" cue at any point: write what is collected so far as a `status: draft` file and exit.
- Do **not** modify `.evidraft/project.yaml` or any other artefact outside `.evidraft/scope/`.
- The slug must not collide with an existing scope file; on collision append `-v2`, `-v3`, etc.

## Done criteria

- A single file at `.evidraft/scope/YYYY-MM-DD-<slug>.md` exists.
- Frontmatter validates against the schema in `../../../capabilities/research/brainstorming/spec.md`.
- `status` is either `draft` (user did not approve) or `approved` with `approved_date` and `staleness_until` set.
- Chat output ends with the recommended next command for the chosen branch.
