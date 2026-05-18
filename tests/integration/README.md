# Integration tests (planned, v0.2)

In v0.1 this directory is a placeholder. The integration surface
below is what the v0.2 pytest harness will cover.

## Planned tests

### 1. Adapter render -> snapshot diff

For each adapter under `packages/adapters/`:

1. Run the adapter generator with `plugins/scholar-ip/` as the
   input and a temporary directory as the output.
2. Compare the generated tree to a committed snapshot in
   `tests/integration/snapshots/<adapter-id>/`.
3. Fail on any diff that is not whitelisted (timestamps, etc.).

Adapters initially in scope: `claude-code`, `codex-cli`.

### 2. Schema validation of templates and fixtures

For every YAML / JSONL / Markdown-with-frontmatter file under:

- `plugins/scholar-ip/templates/`
- `examples/cv-detection-paper/.evidraft/`
- `examples/scholar:patent-disclosure/.evidraft/`

assert validation against the matching schema in
`packages/core/schemas/`:

- `project.schema.json` for `project.yaml`.
- `evidence.schema.json` for each line of `evidence.jsonl`.
- `paper.schema.json` for the paper-side metadata block.
- `patent.schema.json` for the patent-side metadata block.
- `command.schema.json` for every `commands/*.md` frontmatter.

### 3. Hook behavioural tests

Each hook in `plugins/scholar-ip/hooks/` ships a behavioural spec.
The integration suite will:

- Synthesise small inputs (e.g. a paragraph with a strong-claim verb
  but no `citation_key`) and assert that the hook reports the
  expected block / warn outcome.
- For `evidence-consistency`, plant a number with no source row and
  assert the hook fires.
- For `sensitive-file-guard`, attempt a read of a `.env`-style path
  and assert the deny path.

### 4. Patent-specific invariants

- `invention_disclosure.md` must keep the EN/ZH bilingual section
  headers and the "Needs attorney review" footer.
- `claims.md` must keep the "Draft claims. Not filed text..."
  footer.
- `patent_review_report.md` Verdict line must be exactly one of
  `READY_FOR_ATTORNEY` / `NEEDS_WORK`.

## Out of scope (still)

- Real LaTeX compilation (delegated to `latex-build-mcp`).
- Real online scholar / patent retrieval (delegated to MCP stubs).
- Cross-host end-to-end tests against running coding agents.
