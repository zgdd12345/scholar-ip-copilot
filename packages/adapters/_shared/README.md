# `_shared/` — adapter cross-cutting helpers

Code that every host adapter needs lives here. Keep adapter-specific logic in `claude_code/`, `codex_cli/`, `opencode/` — only put things in `_shared/` when two or more adapters use the same code.

## Modules

### `loader.py`

Parses the platform-neutral plugin at `plugins/scholar-ip/` into in-memory `Plugin` + `FrontmatterDoc` records that each adapter then renders.

Key exports:

- `FrontmatterDoc` — dataclass with `path`, `meta`, `body`, and `bundle_dir`. The `bundle_dir` field (Path | None) is set ONLY for skills; for commands / agents / hooks it stays `None`.
- `Plugin` — `manifest` + lists of `commands`, `agents`, `skills`, `hooks`.
- `load_plugin(plugin_dir)` — entrypoint. Reads `plugin.yaml` and walks the four entrypoint directories.
- `validate(plugin, schema_path)` — runs every `FrontmatterDoc.meta` against `command.schema.json`.
- `split_frontmatter(text)` — exposed for tests.
- `dump_frontmatter(fm, body)` — render a frontmatter+body markdown file (stable YAML sort order).
- `render_retention_section(meta)` — emits the `## Pre-run cleanup` block when a command declares a `retention:` rule.

**Skill discovery is bundle-aware.** Skills are discovered by `_load_skill_dir(skills_dir)`: each top-level subdirectory `<skill_id>/` whose `SKILL.md` exists is loaded as a single skill, with `bundle_dir` set to the parent directory. Files under `<skill_id>/references/`, `<skill_id>/assets/`, `<skill_id>/scripts/` etc. are NEVER treated as separate skills — they are part of the bundle that `bundle.py` propagates.

(Commands / agents / hooks still use the older `_load_md_dir()` which expects one `.md` per resource at the top level.)

### `bundle.py`

`copy_skill_bundle(doc, dest_skill_dir) -> list[Path]` is the per-skill bundle propagator. Every adapter calls it after writing its `SKILL.md`:

```python
target = sk_dir / "SKILL.md"
target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
written.append(target)
written.extend(copy_skill_bundle(d, sk_dir))   # propagate references/ assets/ scripts/ …
```

What it does:
- Walks `doc.bundle_dir` recursively (`rglob("*")`).
- Skips the top-level `SKILL.md` itself (already written by the adapter).
- Copies every other file via `shutil.copyfile`, preserving the relative path under `dest_skill_dir`.
- Returns `[]` when the doc has no bundle (commands / agents / hooks) or when the bundle is empty.

**Trust model.** Symlinks are followed (their targets are copied, not the links). Cyclic directory symlinks would loop. Bundles are author-controlled in-tree content, so this is acceptable; do not feed untrusted source trees in.

**Permission model.** `shutil.copyfile` does NOT preserve file modes. If a future `scripts/run.sh` lands in a bundle and needs `+x`, switch to `shutil.copy2` (or `os.chmod` after copy). Today no source skill ships executable resources.

## Why a shared module

Three adapters had byte-identical `_copy_skill_bundle` helpers before this extraction. The extraction (`refactor(adapters): extract copy_skill_bundle to _shared/bundle.py`) removed ~45 lines of duplication and gave the bundle-copy logic a single canonical home. If a fourth adapter lands (Gemini / Cursor / etc.), it imports from here and gets the behaviour for free.

## Conformance

The shared modules are exercised by:
- `tests/test_loader_skill_bundles.py` — unit tests for `_load_skill_dir`, bundle propagation per adapter.
- `tests/test_adapter_conformance.py` invariant I (`test_invariant_i_bundle_resources_propagated`) — asserts every source skill's non-`SKILL.md` siblings appear in both claude_code and codex_cli rendered output.
