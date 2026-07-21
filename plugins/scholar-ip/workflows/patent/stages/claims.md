# workflow:patent.claims

Always produce an attorney-reviewable `.evidraft/patent/claims.md` from the material
available. Missing disclosure sections, evidence, code support, or prior art increase
risk and create explicit gaps; they do not suppress the human-readable draft.

## Steps

1. **Inventory support.** Read any available disclosure, candidate list, prior-art
   map, code mapping, evidence, and existing claims. Summarize what is present and
   missing. Do not refuse to proceed when `Technical solution` or `Implementation
   details` is incomplete.
   - If `claims.md` already exists, treat it as protected human input. Preserve
     attorney edits verbatim, show the proposed replacement as a diff, and continue
     using the existing file unless the user accepts the replacement. Never overwrite
     existing claims without explicit confirmation.
2. **Draft claims adaptively.** Use claim drafting, patent engineering, novelty, and
   evidence roles only where they materially improve the requested claims. Use no
   fixed delegation cardinality, waves, or retry count. Draft supported independent
   and dependent claims up to the requested counts; preserve terminology from the
   disclosure and label unsupported elements for attorney attention.
3. **Always write `claims.md` safely.** Create the file when it is absent; when it
   exists, follow the protected-input rule above. Include:
   - `# Draft claims (for attorney review)`;
   - numbered independent and dependent claims;
   - `## Drafting risks and gaps`, with a table
     `Claim/element | Missing support or prior-art gap | Risk | Attorney action`;
   - the required attorney footer below.
4. **Attempt structured parsing.** Drive
   `../../../capabilities/patent/claim-parser/spec.md` against the completed
   `claims.md`. The claim-parser is the sole writer of `claims_parsed.json`.
   Surface every parser finding. A parser failure blocks only structured parsing and
   chart generation; it never removes or invalidates `claims.md`.
5. **Build structured chart when parsing succeeds.** Drive
   `../../../capabilities/patent/claim-chart-builder/spec.md`. The
   claim-chart-builder consumes `claims_parsed.json` and writes only `claim_chart.md`
   and `claim_chart-<ts>.json`. If parsing or required chart inputs fail, skip these
   optional chart artifacts and add the reason, impact, and recovery action to
   `Drafting risks and gaps`.

## Required footer

Append this footer on every run and never remove it:

```
> Draft claims. Not filed text. These claims include AI-assisted drafting risks and
> support gaps identified above. They must be reviewed and adapted by a registered patent agent / attorney before any filing decision.
```

## Constraints

- Never invent specification, code, evidence, or prior-art support.
- Keep strong novelty assertions out of claim text.
- Unsupported elements must carry `high` risk and a concrete attorney action.
- Workspace safety is the only hard blocker.

## Done criteria

- `claims.md` always exists, contains claims or clearly labelled claim placeholders,
  includes `Drafting risks and gaps`, and ends with the required footer.
- Structured artifacts are produced only after successful parsing and validation.
- Status is `complete` when claims and structured artifacts validate,
  `complete_with_gaps` when claims exist but support or optional structured artifacts
  are incomplete, or `blocked` only when workspace safety prevents writing
  `claims.md`.
- Chat output reports claim count, risk counts, parser/chart status, and next actions.
