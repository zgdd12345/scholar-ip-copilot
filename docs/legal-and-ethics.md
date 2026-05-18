# Legal & Ethics

EviDraft assists, it does not replace. Two areas need explicit framing.

## 1. Patent outputs are attorney-reviewable, not legal advice

The `/patent-*` commands produce:

- an **invention disclosure** suitable for handing to a registered patent agent or attorney;
- **draft claims** with a `claim_chart.md` that traces each element to specification text and source code;
- a **multi-role review report** flagging novelty, clarity, support, and prior-art risks.

What they explicitly **do not** produce:

- a patentability opinion,
- a freedom-to-operate analysis,
- a filing-ready application without human review,
- any guarantee that the invention is novel or non-obvious in any jurisdiction.

Every patent artefact ends with a "Needs attorney review" checklist. The plugin will refuse to remove it.

## 2. Paper outputs are draft material, not guaranteed publishable

The `/paper-*` commands produce:

- a LaTeX draft built from the evidence store,
- a `paper_code_audit.md` that classifies each claim as `CONFIRMED` / `PARTIAL` / `MISSING` / `MISMATCH` / `NOT_AUDITABLE`,
- a `paper_check_report.md` covering citations, LaTeX, figure/table refs, and number provenance.

What they explicitly **do not** do:

- fabricate citations or experiment numbers (evidence consistency hook),
- claim novelty without evidence (citation guard),
- submit anywhere on the user's behalf.

## 3. Evidence discipline

The plugin treats the following as **hard rules**, not preferences:

1. **No strong claim without citation.** Verbs like *novel*, *first*, *outperform*, *significant*, *state-of-the-art* require a `citation_key` or `evidence_id` (`hooks/citation-guard.md`).
2. **No number without source.** A figure in the draft must trace to a row in `experiments/` (`hooks/evidence-consistency.md`).
3. **No code claim without trace.** Statements about what the code does must point to `file_path` + line range (`hooks/evidence-consistency.md`).

Hooks default to **block**. Users can downgrade to **warn** in `.evidraft/project.yaml` under `rules`, but the plugin records the downgrade in `paper_check_report.md`.

## 4. Sensitive files

By default the plugin refuses to read:

- `.env`, `.env.*`
- `secrets/`
- `credentials.json`
- `*.pem`, `*.key`

If a workflow truly needs one of these, the user must explicitly approve a single, scoped read. See `hooks/sensitive-file-guard.md`.

## 5. Data handling

- EviDraft processes everything locally unless a user explicitly enables an MCP server that calls an external service.
- MCP servers under `packages/mcp/` are stubs in MVP and must declare their data flows in their own README.
- No telemetry is shipped from this plugin.

## 6. Third-party references

This project draws design ideas from many upstream plugins (see `reference-analysis.md`). It does **not** vendor their source unless:

- the upstream license permits redistribution under MIT-compatible terms, and
- the file is placed under a `THIRD_PARTY/` directory with the original license file alongside.

At v0.1, no third-party source is vendored.

## 7. Authorship and IP

- The user owns their code, papers, and disclosures. EviDraft is a tool; it does not claim co-authorship of generated output.
- Generated drafts are starting points. Users must review and edit before publishing or filing.

## 8. Compliance disclaimers (jurisdictional)

- US patent law (35 USC, 37 CFR, MPEP) is the reference for the patent module's terminology. Other jurisdictions (EPO, CNIPA, JPO) may treat claim scope, novelty, and inventive step differently.
- EviDraft is jurisdiction-aware where possible (`patent.schema.json` includes a `jurisdiction` field) but does not localise legal substance.

When in doubt, consult counsel.
