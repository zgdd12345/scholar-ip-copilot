# EviDraft 3.0

EviDraft is an evidence-grounded academic and patent copilot for existing codebases,
experiment results, literature, LaTeX manuscripts, and invention disclosures. It uses
one platform-neutral workflow model and renders equivalent interfaces for Claude Code,
Codex, and OpenCode.

EviDraft does not invent citations, numbers, or code references. Patent material is an
attorney-reviewable draft and **not legal advice**. Paper material remains a draft that
requires author review.

## Public interface

Version 3 exposes exactly seven workflows. `using`, `scope`, `polish`, and `xreview`
run directly; `research`, `paper`, and `patent` take an action as their first argument.

| Workflow | Claude Code | Codex | OpenCode |
|---|---|---|---|
| `using` | `/scholar:using` | `$scholar-using` | `/scholar-using` |
| `scope` | `/scholar:scope` | `$scholar-scope` | `/scholar-scope` |
| `research` | `/scholar:research` | `$scholar-research` | `/scholar-research` |
| `paper` | `/scholar:paper` | `$scholar-paper` | `/scholar-paper` |
| `patent` | `/scholar:patent` | `$scholar-patent` | `/scholar-patent` |
| `polish` | `/scholar:polish` | `$scholar-polish` | `/scholar-polish` |
| `xreview` | `/scholar:xreview` | `$scholar-xreview` | `/scholar-xreview` |

Examples:

```text
/scholar:research deep "retrieval augmented code generation"
$scholar-research explain papers/attention-is-all-you-need.pdf --mode graduate
$scholar-paper draft
/scholar-patent claims
```

The complete action map is:

| Workflow | Actions |
|---|---|
| `using` | direct |
| `scope` | direct |
| `research` | `reading-list`, `explain`, `deep` |
| `paper` | `init`, `lit`, `idea`, `code-audit`, `experiment`, `review`, `draft`, `check`, `venue` |
| `patent` | `init`, `scout`, `prior-art`, `disclosure`, `claims`, `review` |
| `polish` | direct |
| `xreview` | direct |

The v1 command files are not emitted by the v3 renderer. The redundant
`research guide` action was removed; use `using` for orientation.

## Stable output contract

The public interface changed, but project artefact locations did not:

```text
<project>/
├── .evidraft/
│   ├── project.yaml
│   ├── evidence/evidence.jsonl
│   ├── literature/
│   ├── scope/
│   ├── ideas/
│   ├── code/
│   ├── experiments/
│   ├── patent/
│   ├── reviews/
│   └── style/
├── manuscript/
└── submissions/
```

Important outputs include:

| Action | Primary outputs |
|---|---|
| `research reading-list` | `.evidraft/notes/<slug>-<date>.md` |
| `research explain` | `.evidraft/notes/paper-explanations/<paper-slug>.md` |
| `research deep` | `.evidraft/literature/{plan.yaml,candidates.jsonl,screening_log.csv,clusters.yaml,evidence_map.json,related_work.draft.md,citation_audit.json}` |
| `paper init` | `.evidraft/project.yaml`, evidence store, bibliography, `manuscript/main.tex` |
| `paper code-audit` | `.evidraft/code/{repo_summary.md,method_to_code.md,paper_code_audit.md}` |
| `paper experiment` | `.evidraft/experiments/result_analysis.md` and LaTeX tables |
| `paper draft` | `manuscript/main.tex` and `manuscript/sections/` |
| `paper venue` | venue material under `submissions/` |
| `patent disclosure` | `.evidraft/patent/invention_disclosure.md` |
| `patent claims` | `.evidraft/patent/claims.md`, structured claims, and claim chart |
| `polish` | edited target plus `.evidraft/style/` audit logs |
| `xreview` | `.evidraft/reviews/` |

`.evidraft/project.yaml` uses `format_version: 2`. A missing value is interpreted as
v1 and is migrated transactionally before the first write. Evidence remains append-only;
corrections use `supersedes`, and web snapshots are addressed by `sha256(raw_body)`.

See [data model](docs/data-model.md), [project-data migration](docs/migration-v2.md),
and [3.0 workflow migration](docs/migration-v3.md).

## Architecture

The source model has four layers:

1. Seven routers under `plugins/scholar-ip/workflows/`.
2. Six semantic roles under `plugins/scholar-ip/roles/roles.yaml`.
3. Three executable policies under `plugins/scholar-ip/policies/policy.yaml`.
4. Private capabilities and templates loaded only by the workflow stage that needs them.

`src/evidraft/` provides deterministic migration, evidence, snapshot, retention,
policy, and rendering operations. A shared renderer consumes the same workflow IR for
all hosts; host profiles only select paths, invocation syntax, role dispatch, model
tier mapping, and hook projection. More detail is in
[architecture](docs/architecture.md) and [plugin format](docs/plugin-format.md).

## Install and render

Create the project environment and install the package:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Render one host through the shared CLI:

```bash
.venv/bin/evidraft render --host claude --plugin plugins/scholar-ip --out .claude/plugins/scholar-ip
.venv/bin/evidraft render --host codex --plugin plugins/scholar-ip --out .codex/plugins/scholar
.venv/bin/evidraft render --host opencode --plugin plugins/scholar-ip --out .opencode
```

The equivalent thin console adapters are:

```text
evidraft-claude-code
evidraft-codex-cli
evidraft-opencode
```

Every render writes `.evidraft-render-manifest.json`. Re-rendering removes only paths
owned by the previous manifest; adjacent user files are preserved.

## Deterministic core

```bash
.venv/bin/evidraft --root <project> migrate
.venv/bin/evidraft --root <project> workflow preflight paper.draft
.venv/bin/evidraft --root <project> evidence append '{"type":"note",...}'
.venv/bin/evidraft --root <project> evidence resolve ev_0001
.venv/bin/evidraft --root <project> snapshot store <url> <raw-body-file>
```

Only routing, schemas, policy decisions, evidence identity, retention, snapshots, and
atomic persistence are deterministic. Retrieval, critique, and writing remain LLM work.

## Development

```bash
make test
make lint
make render
make plugin-validate
make release-check
```

The release gate runs the full test suite, Ruff, the host plugin validator, wheel build,
and repository-external console-script smoke tests. CI covers Python 3.10-3.12 on Ubuntu
and macOS.

## Safety and legal boundaries

The three shared policies are `workspace-safety`, `scope`, and `evidence-integrity`.
Sensitive paths such as `.env`, private keys, and credentials remain blocked. Scope is
advisory, while evidence integrity is evaluated by final paper and patent audits rather
than blocking ordinary draft generation.

EviDraft never files a patent, gives a patentability or freedom-to-operate opinion,
submits a paper, or guarantees novelty or publication. Patent claims and disclosures
must be reviewed by a registered patent professional. See
[legal and ethics](docs/legal-and-ethics.md).

## License

[MIT](LICENSE)
