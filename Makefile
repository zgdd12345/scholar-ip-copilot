PYTHON       ?= .venv/bin/python
PLUGIN_SRC   := plugins/scholar-ip
CC_OUT       := .claude/plugins/scholar-ip
CODEX_OUT    := .codex/plugins/scholar
OPENCODE_OUT := .opencode
# Where Codex auto-discovers skills (cwd walked up to worktree root).
CODEX_SKILLS_INSTALL := .agents/skills

.PHONY: help render _render-all render-claude render-codex render-opencode \
        install _install-all install-claude install-codex install-opencode \
        sync-codex-skills test verify clean

help:
	@echo "Render targets (write adapter output):"
	@echo "  render-claude     -> $(CC_OUT)/"
	@echo "  render-codex      -> $(CODEX_OUT)/"
	@echo "  render-opencode   -> $(OPENCODE_OUT)/"
	@echo "  render            -> all three"
	@echo ""
	@echo "Install targets (render + put files where the host actually loads them):"
	@echo "  install-claude    -> render + remind to run 'claude plugin install'"
	@echo "  install-codex     -> render + sync scholar-* skills into $(CODEX_SKILLS_INSTALL)/"
	@echo "  install-opencode  -> render (opencode auto-discovers .opencode/)"
	@echo "  install           -> all three"
	@echo ""
	@echo "Other:"
	@echo "  sync-codex-skills -> just the .agents/skills/scholar-* sync step"
	@echo "  test              -> pytest tests/test_adapter_conformance.py"
	@echo "  verify            -> render + test + report which host CLIs are detected"
	@echo "  clean             -> remove rendered output (keeps marketplace files)"

# ---------------------------------------------------------------------------
# render

# `render` and `install` aggregate the three host adapters. Each writes to a
# disjoint tree, so we recurse with -j3 to run them concurrently. Override the
# parallel degree via `make MAKEFLAGS='-j1' render` if needed.
render:
	@$(MAKE) -j3 _render-all

_render-all: render-claude render-codex render-opencode

render-claude:
	$(PYTHON) -m packages.adapters.claude_code.generate \
	    --plugin $(PLUGIN_SRC) --out $(CC_OUT)

render-codex:
	$(PYTHON) -m packages.adapters.codex_cli.generate \
	    --plugin $(PLUGIN_SRC) --out $(CODEX_OUT)

render-opencode:
	$(PYTHON) -m packages.adapters.opencode.generate \
	    --plugin $(PLUGIN_SRC) --out $(OPENCODE_OUT)

# ---------------------------------------------------------------------------
# install

# Codex 0.130.0 does not sync plugins from local marketplaces, so we install
# by copying the rendered skill bundles into <repo>/.agents/skills/, which
# Codex auto-discovers by walking up from cwd. We delete existing scholar-*
# entries first so renamed/removed source skills don't linger.
sync-codex-skills: render-codex
	@mkdir -p $(CODEX_SKILLS_INSTALL)
	@find $(CODEX_SKILLS_INSTALL) -mindepth 1 -maxdepth 1 -type d -name 'scholar-*' -exec rm -rf {} +
	@cp -R $(CODEX_OUT)/skills/scholar-* $(CODEX_SKILLS_INSTALL)/
	@n=$$(find $(CODEX_SKILLS_INSTALL) -mindepth 1 -maxdepth 1 -type d -name 'scholar-*' | wc -l | tr -d ' '); \
	  echo "[install-codex] synced $$n skill(s) to $(CODEX_SKILLS_INSTALL)/"

install-codex: sync-codex-skills

install-claude: render-claude
	@echo ""
	@echo "[install-claude] rendered to $(CC_OUT)/"
	@echo "[install-claude] to (re)install at project scope, run:"
	@echo "    claude plugin marketplace add ./  --scope project  # if not already added"
	@echo "    claude plugin install scholar@scholar-ip-copilot --scope project"

install-opencode: render-opencode
	@echo ""
	@echo "[install-opencode] rendered to $(OPENCODE_OUT)/"
	@echo "[install-opencode] opencode auto-discovers .opencode/{commands,agents,skills}/ on next session."

install:
	@$(MAKE) -j3 _install-all

_install-all: install-claude install-codex install-opencode

# ---------------------------------------------------------------------------
# misc

test:
	$(PYTHON) -m pytest tests/test_adapter_conformance.py

verify: install test
	@echo ""
	@echo "[verify] host CLI detection:"
	@command -v claude >/dev/null   && echo "  ✓ claude   $$(claude --version 2>&1 | head -1)" || echo "  ✗ claude   (not on PATH)"
	@command -v codex >/dev/null    && echo "  ✓ codex    $$(codex --version 2>&1 | head -1)" || echo "  ✗ codex    (not on PATH)"
	@command -v opencode >/dev/null && echo "  ✓ opencode $$(opencode --version 2>&1 | head -1)" || echo "  ✗ opencode (not on PATH)"
	@echo ""
	@echo "[verify] rendered output:"
	@test -f $(CC_OUT)/.claude-plugin/plugin.json   && echo "  ✓ $(CC_OUT)/.claude-plugin/plugin.json" || echo "  ✗ $(CC_OUT)/.claude-plugin/plugin.json (missing)"
	@test -f $(CC_OUT)/hooks/hooks.json             && echo "  ✓ $(CC_OUT)/hooks/hooks.json"           || echo "  ✗ $(CC_OUT)/hooks/hooks.json (missing)"
	@test -f $(CODEX_OUT)/.codex-plugin/plugin.json && echo "  ✓ $(CODEX_OUT)/.codex-plugin/plugin.json" || echo "  ✗ $(CODEX_OUT)/.codex-plugin/plugin.json (missing)"
	@test -d $(OPENCODE_OUT)/skills                 && echo "  ✓ $(OPENCODE_OUT)/skills"               || echo "  ✗ $(OPENCODE_OUT)/skills (missing)"
	@n=$$(find $(CODEX_SKILLS_INSTALL) -mindepth 1 -maxdepth 1 -type d -name 'scholar-*' 2>/dev/null | wc -l | tr -d ' '); \
	  [ "$$n" -gt 0 ] && echo "  ✓ $(CODEX_SKILLS_INSTALL)/scholar-* ($$n entries)" || echo "  ✗ $(CODEX_SKILLS_INSTALL)/scholar-* (run 'make install-codex')"
	@echo ""
	@echo "[verify] next step per host:"
	@echo "  claude:   claude plugin marketplace add ./ --scope project &&"
	@echo "            claude plugin install scholar@scholar-ip-copilot --scope project"
	@echo "  codex:    codex plugin marketplace add ./ &&"
	@echo "            append '[plugins.\"scholar@scholar-ip-copilot\"] enabled = true' to ~/.codex/config.toml"
	@echo "  opencode: open opencode in this repo (auto-discovery), or copy .opencode/{commands,agents,skills}/ to ~/.config/opencode/"

clean:
	rm -rf $(CC_OUT) $(CODEX_OUT)
	find $(OPENCODE_OUT) -mindepth 1 -maxdepth 1 \
	    \( -name commands -o -name agents -o -name skills -o -name README.md \) \
	    -exec rm -rf {} +
	@echo "[clean] removed rendered output (marketplace files preserved)"
