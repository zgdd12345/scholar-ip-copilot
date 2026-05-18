# Fixture: patent-disclosure

This fixture is the worked example at
[`examples/scholar:patent-disclosure/`](../../examples/scholar:patent-disclosure/).
It is used as a regression input for the patent workflow:

- `/scholar:patent-init` template render
- `/scholar:patent-scout` candidate enumeration
- `/scholar:patent-prior-art` map structure
- `/scholar:patent-disclosure` -- 13-section bilingual TID structure and the
  mandatory "Needs attorney review" footer
- `/scholar:patent-claims` claims + claim-chart traceability
- `/scholar:patent-review` multi-role report with a binary Verdict

## What it exercises

- A `project_type: patent` project with `jurisdiction: US`.
- A bilingual (EN / ZH) TID with all 13 required sections.
- A claim chart whose every row points to both specification (TID
  section) and code (`src/optim/scheduler.py` line ranges).
- The mandatory `Needs attorney review` footer block (must not be
  removed by any command).
- The `Draft claims. Not filed text...` footer on `claims.md`.
- A patent-review report whose Verdict is one of the two enumerated
  values (`READY_FOR_ATTORNEY`, `NEEDS_WORK`) -- this fixture uses
  `NEEDS_WORK`.

## Planned use in v0.2

- `pytest` will assert that every command output still contains the
  attorney-review footer after re-rendering.
- A bilingual-headers check will scan `invention_disclosure.md` for
  the EN/ZH heading pairs (technical solution / 技术方案, etc.).
- The claim chart will be cross-checked against the line ranges in
  `src/optim/scheduler.py` to guarantee no dangling references.
