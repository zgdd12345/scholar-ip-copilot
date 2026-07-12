# Shared adapter entry support

`v2.py` parses the common `--plugin`, `--out`, and `--dry-run` arguments, then invokes
`evidraft.render.render_plugin` with the selected host profile.

This package contains no authoring model. Workflow IR, schema validation, private
resource copying, atomic writes, and ownership cleanup belong to `src/evidraft/`.
