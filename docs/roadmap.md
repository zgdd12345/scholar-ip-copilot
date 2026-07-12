# Roadmap

## 2.0.0

- Seven public workflows across Claude Code, Codex, and OpenCode.
- One action-based workflow contract with lazy stage loading.
- Six semantic roles with mode overlays and three semantic model tiers.
- Three executable shared policies.
- Deterministic project migration, evidence identity, snapshot, retention, and policy
  core under `src/evidraft/`.
- Shared IR renderer with ownership manifests and three thin host adapters.
- Project `format_version: 2`, transactional v1 migration, quarantine, and
  content-addressed snapshots.
- Release gates for Python 3.10-3.12 on Ubuntu and macOS.

## Non-goals

- No MCP dependency for the v2 workflow or deterministic core.
- No automatic paper submission or patent filing.
- No patentability or freedom-to-operate opinion.
- No fabricated citations, experimental results, or code provenance.
- No web UI; generated artefacts remain inspectable files.

Future work should add a public workflow only when it cannot be represented as an action
of one of the seven existing routers. New host support should be another renderer profile,
not a fork of workflow behavior.
