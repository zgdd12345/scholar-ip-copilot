# tests/

This directory ships **fixtures and stubs** for v0.1. Real pytest
integration is on the v0.2 roadmap.

## Why no executable tests in v0.1

The MVP focuses on workflow correctness over breadth. We ship
manifests, prompts, schemas, and adapters; the LLM-driven outputs are
exercised through the worked `examples/` and reviewed by hand. A
pytest harness is planned for v0.2 once the schemas and adapters
stabilise.

## Current layout

```
tests/
├── README.md                  this file
├── fixtures/
│   ├── cv-detection-paper.md  pointer to examples/cv-detection-paper/
│   └── patent-disclosure.md   pointer to examples/scholar:patent-disclosure/
└── integration/
    └── README.md              planned integration-test surface
```

## How fixtures are used today

In v0.1 the worked examples *are* the fixtures. The pointer files
under `fixtures/` say which example to use as the regression input
and what aspect of the workflow it covers.

## What v0.2 adds

- `tests/unit/` -- schema validation for project / evidence / paper /
  patent / command schemas.
- `tests/integration/` -- adapter render against snapshot, fixture
  evidence consistency checks, citation-guard hook tests.
- `tests/conftest.py` -- pytest fixtures pointing at the examples.
- `pyproject.toml` entries for `pytest`, `jsonschema`, `pyyaml`.
