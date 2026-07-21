PYTHON       ?= .venv/bin/python
PLUGIN_SRC   := plugins/scholar-ip
CC_OUT       := .claude/plugins/scholar-ip
CODEX_OUT    := .codex/plugins/scholar
OPENCODE_OUT := .opencode
DIST_DIR     := dist
SMOKE_VENV   := .release-smoke-venv
# Where Codex auto-discovers skills (cwd walked up to worktree root).
CODEX_SKILLS_INSTALL := .agents/skills

.PHONY: help render _render-all render-claude render-codex render-opencode \
        install _install-all install-claude install-codex install-codex-plugin \
        install-codex-project install-opencode remove-codex-project-skills \
        codex-project-mode-preflight sync-codex-skills package-check \
        test lint plugin-validate wheel wheel-smoke \
        release-check verify clean

help:
	@echo "Render targets (write adapter output):"
	@echo "  render-claude     -> $(CC_OUT)/"
	@echo "  render-codex      -> $(CODEX_OUT)/"
	@echo "  render-opencode   -> $(OPENCODE_OUT)/"
	@echo "  render            -> all three"
	@echo ""
	@echo "Install targets (render + put files where the host actually loads them):"
	@echo "  install-claude    -> render + remind to run 'claude plugin install'"
	@echo "  install-codex     -> validate + install the tracked Codex marketplace plugin"
	@echo "  install-codex-project -> compatibility mode: sync project-local skills"
	@echo "  install-opencode  -> render (opencode auto-discovers .opencode/)"
	@echo "  install           -> all three"
	@echo ""
	@echo "Other:"
	@echo "  sync-codex-skills -> just the compatibility-mode project skill sync"
	@echo "  test              -> full pytest suite"
	@echo "  lint              -> Ruff"
	@echo "  plugin-validate   -> render + official Claude plugin validator"
	@echo "  wheel-smoke       -> clean wheel install + repo-external CLI smoke"
	@echo "  release-check     -> test + lint + plugin validator + wheel smoke"
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

# Marketplace mode is the default. It removes only manifest-owned project skills
# before using the tracked, package-checked repo marketplace.
package-check:
	$(PYTHON) -m evidraft.cli package \
	    --plugin $(PLUGIN_SRC) --out plugins/scholar --check

remove-codex-project-skills:
	$(PYTHON) -m evidraft.cli remove-codex-project-skills \
	    --dest $(CODEX_SKILLS_INSTALL)

install-codex-plugin: package-check remove-codex-project-skills
	$(PYTHON) -m evidraft.cli install-codex-plugin \
	    --repo-root . \
	    --marketplace .agents/plugins/marketplace.json \
	    --plugin plugins/scholar

install-codex: install-codex-plugin

# Compatibility mode is explicit and refuses to run while the marketplace
# plugin is active. It never removes or disables the plugin automatically.
codex-project-mode-preflight:
	$(PYTHON) -m evidraft.cli codex-project-mode-preflight --repo-root .

sync-codex-skills: package-check
	$(PYTHON) -m evidraft.cli sync-codex-skills \
	    --source plugins/scholar --dest $(CODEX_SKILLS_INSTALL)

install-codex-project: package-check codex-project-mode-preflight
	$(PYTHON) -m evidraft.cli sync-codex-skills \
	    --source plugins/scholar --dest .agents/skills

install-claude: render-claude
	@echo ""
	@echo "[install-claude] rendered to $(CC_OUT)/"
	@echo "[install-claude] to (re)install at project scope, run:"
	@echo "    claude plugin marketplace add ./  --scope project  # if not already added"
	@echo "    claude plugin install scholar@scholar-ip-copilot --scope project"

install-opencode: render-opencode
	@echo ""
	@echo "[install-opencode] rendered to $(OPENCODE_OUT)/"
	@echo "[install-opencode] opencode auto-discovers .opencode/{commands,agents,private}/ on next session."

install:
	@$(MAKE) -j3 _install-all

_install-all: install-claude install-codex install-opencode

# ---------------------------------------------------------------------------
# misc

test:
	$(PYTHON) -m pytest tests/

lint:
	$(PYTHON) -m ruff check src packages tests

plugin-validate: render-claude
	@command -v claude >/dev/null || { echo "claude CLI is required" >&2; exit 1; }
	claude plugin validate $(CC_OUT)

wheel:
	@rm -rf $(DIST_DIR) build *.egg-info src/*.egg-info packages/*.egg-info
	$(PYTHON) -m build --wheel --outdir $(DIST_DIR)
	$(PYTHON) -c 'import pathlib,zipfile; p=next(pathlib.Path("$(DIST_DIR)").glob("*.whl")); n=set(zipfile.ZipFile(p).namelist()); required={"evidraft/schemas/workflow.schema.json"}; forbidden={"packages/adapters/_shared/loader.py","packages/adapters/_shared/bundle.py","packages/core/src/__init__.py","packages/core/src/migrate.py"}; assert required <= n, required-n; assert not forbidden & n, forbidden & n'

wheel-smoke: wheel
	@rm -rf $(SMOKE_VENV)
	$(PYTHON) -m venv $(SMOKE_VENV)
	$(SMOKE_VENV)/bin/python -m pip install --quiet $(DIST_DIR)/*.whl
	@cd /tmp && $(CURDIR)/$(SMOKE_VENV)/bin/evidraft --help >/dev/null
	@cd /tmp && $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-claude-code --help >/dev/null
	@cd /tmp && $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-codex-cli --help >/dev/null
	@cd /tmp && $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-opencode --help >/dev/null
	@set -eu; root=$$(mktemp -d /tmp/evidraft-wheel-smoke.XXXXXX); trap 'rm -rf "$$root"' EXIT; \
	  cp -R $(PLUGIN_SRC) "$$root/plugin"; \
	  cd /tmp; \
	  $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-claude-code --plugin "$$root/plugin" --out "$$root/claude"; \
	  $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-codex-cli --plugin "$$root/plugin" --out "$$root/codex"; \
	  $(CURDIR)/$(SMOKE_VENV)/bin/evidraft-opencode --plugin "$$root/plugin" --out "$$root/opencode"; \
	  $(CURDIR)/$(SMOKE_VENV)/bin/python -c 'import pathlib; r=pathlib.Path("'"$$root"'"); assert len(list((r/"claude/commands").glob("*.md"))) == 7; assert len(list((r/"codex/skills").glob("scholar-*/SKILL.md"))) == 7; assert len(list((r/"opencode/commands").glob("scholar-*.md"))) == 7'

release-check: test lint plugin-validate wheel-smoke

verify: install test
	@echo ""
	@echo "[verify] host CLI detection:"
	@command -v claude >/dev/null   && echo "  ✓ claude   $$(claude --version 2>&1 | head -1)" || echo "  ✗ claude   (not on PATH)"
	@command -v codex >/dev/null    && echo "  ✓ codex    $$(codex --version 2>&1 | head -1)" || echo "  ✗ codex    (not on PATH)"
	@command -v opencode >/dev/null && echo "  ✓ opencode $$(opencode --version 2>&1 | head -1)" || echo "  ✗ opencode (not on PATH)"
	@echo ""
	@echo "[verify] rendered output:"
	@test -f $(CC_OUT)/.claude-plugin/plugin.json   && echo "  ✓ $(CC_OUT)/.claude-plugin/plugin.json" || echo "  ✗ $(CC_OUT)/.claude-plugin/plugin.json (missing)"
	@test -f $(CC_OUT)/private/policies/policy.yaml  && echo "  ✓ $(CC_OUT)/private/policies/policy.yaml" || echo "  ✗ $(CC_OUT)/private/policies/policy.yaml (missing)"
	@test -f $(CODEX_OUT)/.codex-plugin/plugin.json && echo "  ✓ $(CODEX_OUT)/.codex-plugin/plugin.json" || echo "  ✗ $(CODEX_OUT)/.codex-plugin/plugin.json (missing)"
	@test -d $(OPENCODE_OUT)/private                && echo "  ✓ $(OPENCODE_OUT)/private"              || echo "  ✗ $(OPENCODE_OUT)/private (missing)"
	@n=$$($(PYTHON) -c 'import json, pathlib; p=pathlib.Path("$(CODEX_SKILLS_INSTALL)/.evidraft-ownership.json"); print(len(json.loads(p.read_text())["owned_paths"]) if p.is_file() else 0)'); \
	  [ "$$n" -eq 7 ] && echo "  ✓ $(CODEX_SKILLS_INSTALL) (7 owned entries)" || echo "  ✗ $(CODEX_SKILLS_INSTALL) (expected 7 owned entries; run 'make install-codex')"
	@echo ""
	@echo "[verify] next step per host:"
	@echo "  claude:   claude plugin marketplace add ./ --scope project &&"
	@echo "            claude plugin install scholar@scholar-ip-copilot --scope project"
	@echo "  codex:    codex plugin marketplace add ./ &&"
	@echo "            codex -c 'model_reasoning_effort=\"xhigh\"' plugin add scholar@scholar-ip-copilot"
	@echo "  opencode: open opencode in this repo (auto-discovery), or install the rendered .opencode tree"

clean:
	$(PYTHON) -m evidraft.cli clean-rendered --out $(CC_OUT)
	$(PYTHON) -m evidraft.cli clean-rendered --out $(CODEX_OUT)
	$(PYTHON) -m evidraft.cli clean-rendered --out $(OPENCODE_OUT)
	rm -rf $(DIST_DIR) $(SMOKE_VENV)
	@echo "[clean] removed rendered output (marketplace files preserved)"
