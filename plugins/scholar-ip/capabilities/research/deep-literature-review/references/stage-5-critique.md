# Stage 5 - Critique

Mode fast skips Stage 5 Critique entirely. Do not dispatch `paper-critic`, do not create
placeholder critique files, and hand `clusters.yaml` directly to Stage 6.

Mode full requires critique for papers selected for full review:

1. Select papers whose methodological or evidentiary risk warrants full-text critique.
2. Dispatch according to task independence, with no fixed cardinality, waves, or retry
   count. Keep each worker's write ownership disjoint or aggregate its returned findings.
3. For each selected paper, record Strengths, Weaknesses, Opportunities, Threats, and
   `Delta vs our angle` in `critique/<cluster-id>.md`.
4. Trace every paper claim to a readable section, figure, table, or equation. If only an
   abstract is available, tag the limited observation `[abstract-only]`, omit unseen
   detail, and record a full-text gap.

Full mode may finish `complete_with_gaps` when a selected PDF cannot be read, provided
the critique file names the evidence boundary and recovery action. Never invent a
locator or silently replace full-text critique with abstract paraphrase.
