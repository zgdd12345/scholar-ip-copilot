PYTHON       ?= .venv/bin/python
PLUGIN_SRC   := plugins/scholar-ip
PLUGIN_OUT   := plugins/scholar
PLUGIN_CREATOR_ROOT ?= $(HOME)/.codex/skills/.system/plugin-creator
CC_OUT       := .claude/plugins/scholar-ip
CODEX_OUT    := .codex/plugins/scholar
OPENCODE_OUT := .opencode
DIST_DIR     := dist
SMOKE_VENV   := .release-smoke-venv
READ_ONLY_PYTHON := env PYTHONDONTWRITEBYTECODE=1
SMOKE_ENV    := env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1
# Where Codex auto-discovers skills (cwd walked up to worktree root).
CODEX_SKILLS_INSTALL := .agents/skills

.PHONY: help render _render-all render-claude render-codex render-opencode \
        install _install-all install-claude install-codex install-codex-plugin \
        install-codex-project install-opencode remove-codex-project-skills \
        codex-project-mode-preflight sync-codex-skills package package-check \
        test lint plugin-validate plugin-validate-codex plugin-validate-claude \
        opencode-inventory wheel wheel-smoke \
        release-check verify clean

help:
	@echo "Render targets (write adapter output):"
	@echo "  render-claude     -> $(CC_OUT)/"
	@echo "  render-codex      -> $(CODEX_OUT)/"
	@echo "  render-opencode   -> $(OPENCODE_OUT)/"
	@echo "  render            -> all three"
	@echo ""
	@echo "Install targets (render + put files where the host actually loads them):"
	@echo "  install-claude    -> validate + update the tracked project marketplace plugin"
	@echo "  install-codex     -> validate + install the tracked Codex marketplace plugin"
	@echo "  install-codex-project -> compatibility mode: sync project-local skills"
	@echo "  install-opencode  -> render (opencode auto-discovers .opencode/)"
	@echo "  install           -> all three"
	@echo ""
	@echo "Other:"
	@echo "  package           -> regenerate the tracked Codex/Claude release package"
	@echo "  package-check     -> verify the tracked release package without writing"
	@echo "  sync-codex-skills -> just the compatibility-mode project skill sync"
	@echo "  test              -> full pytest suite"
	@echo "  lint              -> Ruff"
	@echo "  plugin-validate   -> Codex and Claude validation of the tracked package"
	@echo "  opencode-inventory -> temporary OpenCode render and inventory check"
	@echo "  wheel-smoke       -> clean wheel install + repo-external CLI smoke"
	@echo "  release-check     -> non-mutating verification + temporary host inventory"
	@echo "  verify            -> package drift + tests + lint + validators + wheel smoke"
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
package:
	$(PYTHON) -m evidraft.cli package \
	    --plugin $(PLUGIN_SRC) --out $(PLUGIN_OUT)

package-check:
	$(READ_ONLY_PYTHON) $(PYTHON) -m evidraft.cli package \
	    --plugin $(PLUGIN_SRC) --out plugins/scholar --check

remove-codex-project-skills:
	$(PYTHON) -m evidraft.cli remove-codex-project-skills \
	    --dest $(CODEX_SKILLS_INSTALL)

install-codex-plugin: package-check remove-codex-project-skills
	$(PYTHON) -m evidraft.cli install-codex-plugin \
	    --repo-root . \
	    --marketplace .agents/plugins/marketplace.json \
	    --plugin $(PLUGIN_OUT)

install-codex: install-codex-plugin

# Compatibility mode is explicit and refuses to run while the marketplace
# plugin is active. It never removes or disables the plugin automatically.
codex-project-mode-preflight:
	$(PYTHON) -m evidraft.cli codex-project-mode-preflight --repo-root .

sync-codex-skills: package-check codex-project-mode-preflight
	$(PYTHON) -m evidraft.cli sync-codex-skills \
	    --source plugins/scholar --dest $(CODEX_SKILLS_INSTALL)

install-codex-project: sync-codex-skills

install-claude: package-check plugin-validate-claude
	$(PYTHON) -m evidraft.cli install-claude-plugin --repo-root .

install-opencode: package-check
	$(PYTHON) -m packages.adapters.opencode.generate \
	    --plugin $(PLUGIN_SRC) --out $(OPENCODE_OUT)
	@echo ""
	@echo "[install-opencode] rendered to $(OPENCODE_OUT)/"
	@echo "[install-opencode] opencode auto-discovers .opencode/{commands,agents,private}/ on next session."

install:
	@$(MAKE) -j3 _install-all

_install-all: install-claude install-codex install-opencode

# ---------------------------------------------------------------------------
# misc

test:
	$(READ_ONLY_PYTHON) $(PYTHON) -m pytest -p no:cacheprovider tests/

lint:
	$(PYTHON) -m ruff check --no-cache src packages tests

plugin-validate-codex:
	@test -f "$(PLUGIN_CREATOR_ROOT)/scripts/validate_plugin.py" || { \
	  echo "Codex plugin validator not found; set PLUGIN_CREATOR_ROOT" >&2; exit 1; }
	$(READ_ONLY_PYTHON) $(PYTHON) $(PLUGIN_CREATOR_ROOT)/scripts/validate_plugin.py plugins/scholar

plugin-validate-claude:
	@command -v claude >/dev/null || { echo "claude CLI is required" >&2; exit 1; }
	claude plugin validate plugins/scholar

plugin-validate: plugin-validate-codex plugin-validate-claude

opencode-inventory:
	@set -eu; root=$$(mktemp -d /tmp/evidraft-opencode.XXXXXX); \
	  trap 'rm -rf "$$root"' EXIT; \
	  $(READ_ONLY_PYTHON) $(PYTHON) -m packages.adapters.opencode.generate \
	    --plugin $(PLUGIN_SRC) --out "$$root/opencode"; \
	  $(READ_ONLY_PYTHON) $(PYTHON) -c 'import pathlib; r=pathlib.Path("'"$$root"'")/"opencode"; assert len(list((r/"commands").glob("scholar-*.md"))) == 7; assert (r/"private/policies/policy.yaml").is_file(); assert (r/"private/capabilities/index.yaml").is_file()'

wheel:
	@rm -rf $(DIST_DIR) build *.egg-info src/*.egg-info packages/*.egg-info
	$(PYTHON) -m build --wheel --outdir $(DIST_DIR)
	$(PYTHON) -c 'import pathlib,zipfile; p=next(pathlib.Path("$(DIST_DIR)").glob("*.whl")); n=set(zipfile.ZipFile(p).namelist()); required={"evidraft/schemas/workflow.schema.json"}; forbidden={"packages/adapters/_shared/loader.py","packages/adapters/_shared/bundle.py","packages/core/src/__init__.py","packages/core/src/migrate.py"}; prefixes=("plugins/",".codex-plugin/",".claude-plugin/","skills/"); leaked=sorted(x for x in n if x.startswith(prefixes)); assert required <= n, required-n; assert not forbidden & n, forbidden & n; assert not leaked, leaked'

wheel-smoke:
	@set -eu; python=$$($(SMOKE_ENV) $(PYTHON) -c 'import os,sys; print(os.path.abspath(sys.executable))'); \
	  root=$$(mktemp -d /tmp/evidraft-wheel-smoke.XXXXXX); \
	  trap 'rm -rf "$$root"' EXIT; \
	  $(READ_ONLY_PYTHON) "$$python" -c 'import sys; from pathlib import Path; from evidraft.release import stage_wheel_source; stage_wheel_source(Path(sys.argv[1]), Path(sys.argv[2]))' "$(CURDIR)" "$$root/source"; \
	  cp -R "$(PLUGIN_SRC)" "$$root/plugin"; \
	  cd "$$root"; \
	  $(SMOKE_ENV) "$$python" -m build --wheel --outdir "$$root/dist" "$$root/source"; \
	  $(SMOKE_ENV) "$$python" -c 'import pathlib,sys,zipfile; p=next(pathlib.Path(sys.argv[1]).glob("*.whl")); n=set(zipfile.ZipFile(p).namelist()); required={"evidraft/schemas/workflow.schema.json"}; forbidden={"packages/adapters/_shared/loader.py","packages/adapters/_shared/bundle.py","packages/core/src/__init__.py","packages/core/src/migrate.py"}; prefixes=("plugins/",".codex-plugin/",".claude-plugin/","skills/"); leaked=sorted(x for x in n if x.startswith(prefixes)); assert required <= n, required-n; assert not forbidden & n, forbidden & n; assert not leaked, leaked' "$$root/dist"; \
	  $(SMOKE_ENV) "$$python" -m venv "$$root/venv"; \
	  $(SMOKE_ENV) "$$root/venv/bin/python" -m pip install --quiet "$$root"/dist/*.whl; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft" --help >/dev/null; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-claude-code" --help >/dev/null; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-codex-cli" --help >/dev/null; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-opencode" --help >/dev/null; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-claude-code" --plugin "$$root/plugin" --out "$$root/claude"; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-codex-cli" --plugin "$$root/plugin" --out "$$root/codex"; \
	  $(SMOKE_ENV) "$$root/venv/bin/evidraft-opencode" --plugin "$$root/plugin" --out "$$root/opencode"; \
	  $(SMOKE_ENV) "$$root/venv/bin/python" -c 'import pathlib; r=pathlib.Path("'"$$root"'"); assert len(list((r/"claude/commands").glob("*.md"))) == 7; assert len(list((r/"codex/skills").glob("scholar-*/SKILL.md"))) == 7; assert len(list((r/"opencode/commands").glob("scholar-*.md"))) == 7'

verify: package-check test lint plugin-validate wheel-smoke

release-check: verify opencode-inventory
	git diff --exit-code

clean:
	$(PYTHON) -m evidraft.cli clean-rendered --out $(CC_OUT)
	$(PYTHON) -m evidraft.cli clean-rendered --out $(CODEX_OUT)
	$(PYTHON) -m evidraft.cli clean-rendered --out $(OPENCODE_OUT)
	rm -rf $(DIST_DIR) $(SMOKE_VENV)
	@echo "[clean] removed rendered output (marketplace files preserved)"
