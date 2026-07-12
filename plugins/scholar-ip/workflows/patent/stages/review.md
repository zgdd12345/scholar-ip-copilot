# workflow:patent.review

Run a multi-role review pass over `invention_disclosure.md`, `claims.md`, and `claim_chart.md`. Produce `.evidraft/patent/patent_review_report.md`.

The review combines the 5-role panel (engineer / drafter / novelty critic / methodology / examiner) with three **structured audits** built in v0.3: `claim-parser` for structural warnings, `claim-chart-builder` for the chart, and `novelty-heuristics` for per-element overlap scoring. The structured findings feed the panel — novelty-critic and claim-drafter no longer review from prose alone.

## Structured-audit pre-pass

Before the panel runs, refresh the structured audits (idempotent — they read whatever is on disk; if `workflow:patent.claims` already produced fresh artefacts in this run_id, they no-op):

1. **Claim parsing.** Drive `../../../capabilities/patent/claim-parser/spec.md`. Reads `claims.md`; emits `claims_parsed.json` (canonical) + `claim_parse-<ts>.log`. Surfaces structural warnings (`MISSING_TERMINUS`, `UNNUMBERED_ELEMENT`, `FORWARD_DEPENDENCY`, `EMPTY_CLAIM` are `fail`-severity; `ANTECEDENT_MISSING`, `MULTIPLE_DEPENDENCY`, `TRANSITION_UNKNOWN`, `DEPENDENT_NO_NARROW` are `warn`).
2. **Claim chart.** Drive `../../../capabilities/patent/claim-chart-builder/spec.md`. Emits `claim_chart.md` + `claim_chart-<ts>.json`. Populates spec/code support, per-element prior-art overlap, risk roll-up, suggested revisions.
3. **Novelty heuristics.** Drive `../../../capabilities/patent/novelty-heuristics/spec.md`. Reads `claims_parsed.json` + `prior_art_map.md` (+ optional `claim_chart-<ts>.json` to reuse rows). Emits `novelty_audit-<ts>.findings.json` + paired `.log`. Produces `verdict_hint ∈ {novel, narrow, redraft, withdraw}` **advisory only** per claim.

If parser raises `fail`-severity warnings, the panel still runs but the report's overall verdict is forced to `NEEDS_WORK`.

## Reviewer panel

The 5 roles share inputs but have no inter-role dependency — **dispatch them in parallel** and assemble the report at the end. Only the final aggregation is serial. Each role consumes the structured findings from the pre-pass.

1. **Patent engineer** — Use the `patent-engineer` subagent. Are the technical solution, alternatives, examples, and diagrams sufficient to teach the invention to a skilled person? Consults `invention_disclosure.md`.
2. **Claim drafter** — Use the `claim-drafter` subagent. Are claims clear, properly antecedent, with consistent terminology? Are dependent claims actually narrower? Any 112(b)-style indefiniteness risk? **Now consumes `claims_parsed.json`** — antecedent-chain warnings and dependency-graph issues come pre-computed from the parser; this role focuses on the LLM-only judgements (clarity, consistency, breadth-vs-defensibility tradeoffs).
3. **Novelty critic** — Use the `novelty-critic` subagent. For each independent claim element, what is the strongest prior-art overlap? Where is the line of distinction? **Now consumes `novelty_audit-<ts>.findings.json`** — `overlap_score`, `differentiator_hint`, and `verdict_hint` come pre-scored; this role validates the heuristic verdicts against the actual prior-art passages and flags any score the critic disagrees with.
4. **Methodology / technical reviewer** — Use the `methodology-reviewer` subagent. Does the disclosure match the code? Any mismatches against `method_to_code.md`?
5. **Skeptical examiner** — Use the `evidence-auditor` subagent to back the rejection scenarios with verified evidence ids. Imagine you reject this. What is the rejection reasoning, and what amendment closes it? **Reads the per-claim `verdict_hint`** as starting point: `redraft` and `withdraw` verdicts auto-seed this role's rejection scenarios.

Plus the `consistency-checker` agent (carried over from v0.4 wiring) — applies its 9 rules to the TID + claims as cross-document consistency check (terminology drift between disclosure and claims is a common pre-filing defect).

## Output structure

```
# Patent review report

Generated: <iso datetime>
run_id: <id>
Targets:
- disclosure: .evidraft/patent/invention_disclosure.md
- claims:     .evidraft/patent/claims.md
- chart:      .evidraft/patent/claim_chart.md
Structured-audit artefacts (this run):
- claims_parsed:    .evidraft/patent/claims_parsed.json
- claim_chart:      .evidraft/patent/claim_chart-<ts>.json
- novelty_audit:    .evidraft/patent/novelty_audit-<ts>.findings.json

## Structured audits (pre-pass)

### Claim parser
- Fail: <count>; Warn: <count>; Info: <count>
- Top issues: ...

### Claim chart
- Rows total / high risk / medium risk / low risk: ...
- Rows with no spec or no code support: ...

### Novelty heuristics
- Per-claim verdict_hints:
  - c1: <novel|narrow|redraft|withdraw>  (advisory only)
  - c2: ...
- Top overlap findings: ...

## Reviewer panel

### 1. Patent engineer
- Gaps:
- Suggestions:

### 2. Claim drafter
- Beyond parser warnings (clarity / breadth / 112(b)):
- Suggestions:

### 3. Novelty critic
- Heuristic verdicts the critic agrees with:
- Heuristic verdicts the critic OVERRIDES (with reasoning):
- Distinguishing language suggestions:

### 4. Methodology / technical reviewer
- Code vs disclosure mismatches:
- Recommendations:

### 5. Skeptical examiner
- Strongest rejection scenario (seeded from `verdict_hint`):
- Suggested amendments:

### 6. Consistency checker
- Terminology drift between TID and claims:
- Number / symbol consistency:

## Overall verdict
- Verdict: READY_FOR_ATTORNEY / NEEDS_WORK
- Top-3 next actions:
```

## Constraints

- **No legal opinions.** "Verdict" describes maturity for attorney review, not patentability. `verdict_hint` values are advisory.
- Every "mismatch" / "overlap" must point to a file or evidence id.
- Parser `fail`-severity warnings force `Verdict: NEEDS_WORK` regardless of panel consensus.
- Novelty-critic role MUST explicitly state which heuristic verdicts they agree with vs override — the structured findings are starting points, not endpoints.
- Audit artefacts share the same `run_id` as the command invocation so cross-audit dedup works.

## Done criteria

- Report exists.
- Verdict is one of the two enumerated values.
- All three structured audits have run (or no-op'd because fresh artefacts already exist).
- Chat output prints the verdict, the per-claim `verdict_hint`s, and the top-3 next actions.

