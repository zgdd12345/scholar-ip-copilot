# Selective EviDraft 3.0 and Plugin Packaging Design

## Status

Approved in conversation on 2026-07-21. This design supersedes the lightweight
EviDraft 3.0 behavior only where it explicitly restores the structured
`research.explain` workflow. It does not supersede the existing project-data
format, which remains `format_version: 2`.

## Context

The repository currently has two incompatible states:

- tracked `master` source identifies itself as EviDraft 2.0 and contains the
  structured paper-explanation task graph;
- a dirty, isolated `codex/evidraft3-lightweight` worktree contains an
  uncommitted EviDraft 3.0 simplification that is already installed in local
  host caches.

The installed EviDraft 3.0 bundle is valid, but it is not reproducible from a
committed source. It also removes the task graph, dedicated explanation
workers, mandatory related/current-method research, and blocking scope and
evidence policies in one undifferentiated change.

This design makes EviDraft 3.0 reproducible while restoring the paper
explanation guarantees that remain product requirements. It also replaces the
current disposable marketplace targets and duplicate Codex discovery paths
with one deterministic packaging and installation workflow.

## Goals

1. Make EviDraft 3.0 the committed product version without accepting all
   lightweight-worktree behavior unchanged.
2. Retain a validated `research.explain` task graph, dedicated worker modes,
   a dedicated evidence auditor, and mandatory attempts to retrieve similar
   and current methods.
3. Raise the task-graph parallelism ceiling from 4 to 15.
4. Make exhausted task failures produce an explicit partial note instead of
   blocking all output.
5. Make scope and evidence-integrity decisions advisory while retaining hard
   workspace, sensitive-path, overwrite, and user-authority boundaries.
6. Provide a tracked, plugin-creator-compliant `plugins/scholar` release root
   that a clean checkout can install directly.
7. Make marketplace plugin installation the default Codex mode and keep
   project-local `.agents/skills` synchronization as an explicit compatibility
   mode only.
8. Validate source, release, marketplace, and installed-host state from fresh
   command output.

## Non-goals

- Changing `.evidraft/project.yaml` beyond `format_version: 2`.
- Guaranteeing that an external provider or paper source is available.
- Allowing workers to invent missing analysis when retrieval or delegation
  fails.
- Weakening workspace confinement, sensitive-file protection, explicit
  overwrite approval, or the prohibition on filing/submitting without user
  authorization.
- Bundling the canonical plugin content inside the Python wheel.
- Adding placeholder logos, screenshots, privacy policies, or terms URLs.

## Research Guide Compatibility

`research.guide` remains removed in EviDraft 3.0. Guidance and orientation
intents route through `using`; the release does not add a compatibility alias
or restore `workflows/research/stages/guide.md`. The public surface therefore
remains seven workflows and 22 actions, with `research` exposing exactly
`reading-list`, `explain`, and `deep`.

## Authoritative Source and Version

`plugins/scholar-ip/` remains the only hand-authored workflow source.
`plugins/scholar/` is a deterministic, tracked release projection and must not
be edited directly.

`plugins/scholar-ip/plugin.yaml` is the authoritative source for plugin ID,
product name, version, description, license, author, homepage, repository, and
search keywords. Claude and Codex manifests must be derived from this data.
The Python package version remains independently declared by packaging
metadata, but a release test requires it to equal the plugin version.

The base release version is `3.0.0`. A Codex cachebuster is installation state,
not source state. The tracked manifest always returns to `3.0.0` after a local
reinstall.

## Structured Paper Explanation

### Graph contract

The paper-explanation capability retains these resources:

- `task-graph.yaml`;
- `paper-map.schema.json`;
- `analysis-packet.schema.json`;
- the runtime graph and worker-return validator;
- `paper-indexer`, `paper-analysis-worker`, `paper-reasoning-worker`,
  `explanation-evidence-auditor`, and `paper-explainer` mode specifications.

The scheduler contract is:

```yaml
max_parallel: 15
max_attempts: 2
nested_delegation: forbidden
result_order: task_id
```

Effective concurrency is `min(host_capacity, 15, ready_task_count)`. A host may
run fewer tasks concurrently, but no execution path may dispatch more than 15
graph tasks at once.

The existing beginner, graduate, and reviewer dependency shapes remain:

- beginner: index, then method/equation, experiment/limitation, and combined
  related/current-method analysis, then synthesis;
- graduate: index, then method, equations, experiments, limitations, similar
  methods, and current methods, then synthesis;
- reviewer: the graduate analysis wave plus claim-boundary analysis, then the
  dedicated evidence audit, then synthesis.

Only the synthesis task may write the final reading note. Analysis workers and
the auditor return schema-validated packets and never receive output ownership
or overwrite state.

### Mandatory attempt semantics

`mandatory: true` means that a task must be scheduled or explicitly recorded
as unavailable. It no longer means that the task must succeed before synthesis
may run.

The similar-method and current-method scopes are mandatory attempts in every
profile:

- beginner uses its combined external-research task;
- graduate and reviewer use separate similar-method and current-method tasks.

Each external-research attempt records its queries, providers, cutoff date,
opened canonical sources, rejected candidates, and failure reason. A section
cannot claim coverage when no source was successfully verified.

### Retry and degradation

A timeout, execution failure, or invalid packet consumes an attempt. Attempt
two uses a fresh worker with the same immutable scope and budget. The
coordinator does not repair an invalid packet, broaden the task, or silently
replace a failed external search with unsupported prose.

After attempt two fails, the task becomes terminal with a recorded failure.
Synthesis still runs and writes a note with `status: partial`, an explicit gap
for the failed scope, and both attempt reasons.

When the host cannot create independent workers, affected tasks are recorded
as unavailable. The coordinator may execute the synthesis contract locally to
write the partial status and gap report, but it must not merge missing worker
scopes into an unstructured monolithic analysis.

If indexing fails, the partial artifact is limited to verified source identity,
content-availability facts, task status, and recovery instructions. It does not
invent method, equation, experiment, or related-work content.

### Auditor semantics

The reviewer profile retains the dedicated evidence auditor. The auditor checks
packet/source consistency, claim boundaries, and external-source labeling.
Valid auditor findings are written into the note as warnings and correction
guidance. `blocking: true` is removed from the orchestration decision: an audit
finding cannot suppress synthesis or delete an otherwise valid note.

### Final status

- `complete`: every selected analysis task returned a valid packet.
- `partial`: any selected task failed, was unavailable, or returned incomplete
  externally verified coverage.
- `error`: workspace safety rejected the output target, overwrite permission
  was absent, or the final artifact could not be written atomically.

Audit severity does not change `complete` to `partial` by itself when all task
packets are valid. Audit warnings remain prominent in the final note.

## Policy Model

`scope` and `evidence-integrity` remain named policies so workflows can report
their decisions consistently, but they are advisory:

- missing or stale scope emits a warning and suggested next action;
- missing evidence, unresolved citations, unsupported claims, or incomplete
  related-work coverage emits `WARN` or `FAIL` in the audit artifact;
- neither policy prevents drafting, review, synthesis, or final-note writing.

The following constraints remain hard failures:

- output paths outside the selected workspace;
- sensitive files, credentials, private keys, and `.env` files;
- writes through unsafe symlink ancestors;
- overwrite without explicit approval;
- patent filing, paper submission, or other external publication without
  explicit user authorization.

## Tracked Release Package

The repository contains one tracked local release package:

```text
plugins/scholar/
|-- .codex-plugin/plugin.json
|-- .claude-plugin/plugin.json
|-- skills/
|-- commands/
|-- agents/
|-- private/
`-- .evidraft-release-manifest.json
```

Codex and Claude files may coexist because their public entry paths are
disjoint. Host-private resources may be duplicated where their relative-link
contracts differ. OpenCode remains an untracked `.opencode/` projection because
its command and agent paths can collide with Claude formats.

The release manifest records:

- release-manifest format version;
- product version;
- renderer version;
- SHA-256 digest of sorted canonical source paths and bytes;
- owned release paths for each host projection.

Packaging stages both host projections in a temporary directory, rejects path
collisions with different bytes, validates both manifests, and atomically
replaces the owned release package. Unknown files inside the dedicated release
root are errors rather than silently preserved adjacent content.

CI regenerates the base release package in a temporary directory and compares
it byte-for-byte with `plugins/scholar/`. A mismatch fails the release gate.

## Marketplace Layout

The tracked Codex marketplace remains at `.agents/plugins/marketplace.json` and
uses this source:

```json
{
  "source": "local",
  "path": "./plugins/scholar"
}
```

Its installation and authentication policies remain `AVAILABLE` and
`ON_INSTALL`, and its category remains `Productivity`.

The root `.claude-plugin/marketplace.json` becomes tracked and points its
`scholar` entry to `./plugins/scholar`. A clean checkout therefore contains
both marketplace descriptors and the referenced release package before any
render command runs.

Marketplace JSON and user Codex configuration are never hand-edited during an
update/reinstall loop.

## Codex Installation Modes

### Marketplace plugin mode

`install-codex` aliases the default `install-codex-plugin` mode. This mode:

1. verifies the tracked release package and provenance;
2. removes only EviDraft-owned project skills recorded in
   `.agents/skills/.evidraft-ownership.json`;
3. confirms or installs the repo-local marketplace;
4. reads the marketplace name from its JSON through the plugin-creator helper;
5. applies exactly one transient Codex cachebuster through the plugin-creator
   helper;
6. runs `codex plugin add scholar@scholar-ip-copilot`;
7. restores the tracked base manifest even when installation fails;
8. validates the installed cache and confirms the expected seven public skills.

The workflow never edits `~/.codex/config.toml`.

### Project-skill compatibility mode

`install-codex-project` renders and transactionally synchronizes the seven
project-local skills. It is not part of the default aggregate install. It
refuses to claim success when the marketplace plugin is also active and reports
the exact non-destructive host command needed to select one mode.

Verification requires exactly one active Codex discovery source.

## Claude and OpenCode Installation

Claude installs or updates `scholar@scholar-ip-copilot` at project scope from
the tracked repo marketplace and validates both the source package and installed
cache.

OpenCode renders from the canonical source into `.opencode/` and verifies seven
public commands plus required private resources. Host sessions must be
restarted, and Codex must start a new task, after installation so host caches
load the new release.

## Python Wheel Boundary

The Python wheel remains a renderer and deterministic CLI toolchain. It does
not include `plugins/scholar-ip` or `plugins/scholar`. Documentation and smoke
tests state that rendering requires an explicit external `--plugin` path. The
wheel smoke test must not imply that the wheel alone is a complete plugin
distribution.

## Metadata

Generated manifests use the configured repository URL
`https://github.com/zgdd12345/scholar-ip-copilot` and the same value for the
public website until a separate documentation site exists. Interface prompts
remain limited to three entries of at most 128 characters.

Asset fields, privacy-policy URLs, and terms-of-service URLs are omitted until
real project-owned assets and policies exist. The release process must not
invent placeholder metadata to make the manifest look more complete.

## Test-Driven Implementation

Every production change follows Red, Green, Refactor. The implementation plan
must establish failing tests for at least these behaviors before modifying
production code:

1. the EviDraft 3.0 source still contains and validates the paper-explanation
   graph, schemas, and dedicated modes;
2. the scheduler ceiling is 15 and dispatch uses the host-capacity minimum;
3. external-research tasks are always attempted and exhausted failures produce
   a partial note rather than a blocked workflow;
4. auditor findings are advisory;
5. scope and evidence-integrity cannot block generation while workspace safety
   still can;
6. host manifests derive version and metadata from canonical `plugin.yaml`;
7. a clean checkout contains valid Codex and Claude marketplace targets;
8. regenerated release output is byte-identical to the tracked package;
9. marketplace mode and project-skill mode cannot both report active success;
10. cachebuster installation restores the tracked base manifest on success and
    failure;
11. Codex plugin-creator validation and Claude validation pass for the release
    root;
12. the wheel is explicitly tested as renderer-only.

Focused tests run first for each Red/Green cycle. The final gate runs the full
test suite, Ruff, package drift verification, both host validators, wheel smoke,
and clean-checkout installation preflight.

## Integration Safety

The existing dirty v3 worktree is preserved before restructuring. Its complete
non-ignored state is committed as a checkpoint on
`codex/evidraft3-lightweight`; ignored installed host trees are not included.
Selective-v3 work then proceeds through small TDD commits on the isolated
branch. No reset, stash, history rewrite, or edits to the locked Claude
worktrees are permitted.

The branch can integrate into `master` only after:

- all approved behavior is represented by tests;
- the tracked release package is reproducible;
- the full release gate passes from committed source;
- a final diff review finds no unresolved critical or important issue.

Real host reinstall happens only from that integrated, verified commit. Any
required system-level Codex CLI or configuration change requires separate user
approval.

## Acceptance Criteria

The work is complete when all of the following are true:

- committed EviDraft source and all generated manifests report base version
  `3.0.0`;
- `research.explain` uses the validated task graph with `max_parallel: 15`;
- similar-method and current-method research are always attempted;
- exhausted failures yield an explicit partial note rather than suppressing
  output;
- the dedicated auditor runs without blocking synthesis;
- scope and evidence-integrity are advisory, while workspace safety remains
  enforced;
- `.agents/plugins/marketplace.json` and the tracked Claude marketplace both
  resolve to `plugins/scholar` in a clean checkout;
- Codex uses exactly one active discovery mode;
- cachebusted installation leaves the tracked source manifest unchanged;
- Codex, Claude, OpenCode, Python, lint, package-drift, and clean-checkout gates
  pass from fresh command output;
- installed host caches report the integrated version and expose exactly seven
  public Scholar entrypoints;
- the final handoff instructs the user to start a new Codex task and restart
  other host sessions.
