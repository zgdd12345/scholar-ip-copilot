# Carlini conclusion-first test + approaches with tradeoffs

Two interview-stage techniques applied *after* the question schema and *before* the verdict matrix.

## Carlini conclusion-first test (full mode only)

Ask the user to draft the abstract (paper) or 技术交底书 summary (patent) **as if the work were complete**. Mirror it back. Surface, line by line:

- numbers without a source,
- comparatives ("better than", "faster than") without a named baseline,
- novelty claims without a contrasted reference,
- promised artefacts (datasets, code, ablations) that have no evidence seed yet.

Each gap becomes an explicit `TODO` in the scope file or is acknowledged as accepted risk.

## Approaches with tradeoffs

Offer 2–3 candidate approaches to the stated contribution. For each:

- **Scope** — what is in / out.
- **Evidence cost** — how much literature / experimentation / coding effort it implies.
- **Riskiest assumption** — one falsifiable sentence.
- **Fallback** — what to do if that assumption breaks.

Let the user pick one or request another round.
