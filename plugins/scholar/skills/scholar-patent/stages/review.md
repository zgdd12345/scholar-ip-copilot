# workflow:patent.review

Review every available patent artifact and produce one consolidated readiness report
at `.evidraft/patent/patent_review_report.md`. This is technical drafting review,
not a patentability opinion or legal advice.

## Input reuse

Build an `Input summary` from the fingerprints of available disclosure, claims,
structured claims, claim charts, prior-art map, code mapping, and evidence. If the
existing report's `Input summary` matches the current normalized inputs and source
fingerprints, reuse the report and state that no reviewed input changed. Otherwise,
reuse still-current audit results and refresh only changed or missing areas.

## Steps

1. **Inventory and gaps.** Missing optional artifacts become review findings. Only a
   workspace-safety violation can block report creation.
2. **Structured audits when possible.** Use
   `../../.evidraft-private/capabilities/patent/claim-parser/spec.md`,
   `../../.evidraft-private/capabilities/patent/claim-chart-builder/spec.md`, and
   `../../.evidraft-private/capabilities/patent/novelty-heuristics/spec.md` for the inputs they can
   consume. Parser failure is a `FAIL` finding for structure but does not block
   review of `claims.md` or the disclosure.
3. **Adaptive review.** Dispatch review roles adaptively according to the available
   artifacts and uncovered risk. Use no fixed panel size, waves, or retry count.
   Cover technical enablement, claim clarity/support, prior-art overlap,
   code/disclosure consistency, and filing-review gaps when relevant. Every mismatch
   or overlap finding cites a file, passage, or evidence id.
4. **Consolidate once.** De-duplicate all deterministic and delegated findings into
   a single consolidated summary and assign severities:
   - `FAIL`: claims cannot be safely interpreted, required human-readable artifacts
     are absent, or material support/consistency defects exist;
   - `WARN`: attorney input, verification, optional structured output, or narrower
     support remains incomplete;
   - `PASS`: no material drafting-readiness gaps were found in supplied inputs.

## Output

Write the report with this shape:

```
# Patent review report

Generated: <iso datetime>
Input summary: <normalized inputs and source fingerprints>

## Available and missing inputs
...

## Consolidated findings
| Severity | Artifact / claim | Finding | Evidence | Next action |

## Structured audit status
- Claim parser: PASS | WARN | FAIL | SKIPPED
- Claim chart: PASS | WARN | FAIL | SKIPPED
- Novelty heuristics: PASS | WARN | FAIL | SKIPPED

## Attorney-review risks
...

Overall verdict: PASS | WARN | FAIL
```

The report contains exactly one overall verdict. `PASS` means ready for attorney
review, not patentable or ready to file.

## Done criteria

- The report exists with the current `Input summary`, consolidated findings, and one
  enumerated verdict.
- Chat output prints the verdict, finding counts by severity, missing inputs, and
  highest-priority next actions.
