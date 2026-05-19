# OpenCode JS-Plugin Spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate via a reversible spike whether OpenCode can read scholar-ip skills directly from `plugins/scholar-ip/skills/` using a runtime path-registration JS plugin — eliminating the need for the ~250-line `packages/adapters/opencode/generate.py` and unlocking native support for skill bundle resources (`references/`, `assets/`, etc.).

**Architecture:** Add a single 50-80 line `.opencode/plugins/scholar.js` modeled on `superpowers.js` (137 lines, already studied). The plugin's `config` hook registers `plugins/scholar-ip/skills/` (and optionally `agents/`) into OpenCode's discovery paths at session start. The existing render pipeline stays untouched so the spike is non-destructive — if the spike fails we delete one JS file and one Makefile target. If it passes, a separate follow-up PR removes the Python adapter.

**Tech Stack:** Node ES modules (no new npm deps; matches superpowers convention), OpenCode 1.3.0 (verified installed), pre-existing pytest test suite (we will NOT add automated JS tests for the spike — validations are explicit manual checks with PASS/FAIL criteria).

**Branch:** `spike/opencode-js-plugin` (do not merge to master; outcome is a decision artefact, not production code).

**Constraints inherited from prior conversation:**
- Path C/D from architecture review: keep Claude Code's render-based adapter, replace OpenCode's with shim. This spike only validates the OpenCode half.
- Source-of-truth remains `plugins/scholar-ip/`. Spike does NOT move files.
- `packages/adapters/opencode/generate.py` is NOT modified or deleted in this spike. Removal is a follow-up PR contingent on spike outcome.

---

## File Structure

**New files:**
- `.opencode/plugins/scholar.js` — the JS plugin under test (~70 lines). Registers `config.skills.paths` (and `config.agents.paths` if Task 6 confirms it exists).
- `docs/spike-results/2026-05-19-opencode-js-plugin.md` — the spike's deliverable. Captures findings, PASS/PARTIAL/FAIL verdict, evidence per validation, and recommended follow-up.
- `plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md` — a single, intentionally-named probe file to test references/ visibility. Reverted in Task 7 if spike fails; promoted to a real reference if it succeeds.

**Modified files:**
- `Makefile` — add one target `install-opencode-spike` that prints the `opencode.json` snippet the user must paste; does not write the user's opencode.json (we never modify user-global config without confirmation).
- `.gitignore` — confirm `node_modules/` already excluded (no change expected, just verify).

**NOT touched in this spike:**
- `packages/adapters/opencode/generate.py` (~250 lines) — left intact. Spike is additive.
- `packages/adapters/_shared/loader.py` — left intact. Spike does not change source discovery.
- The 24 skills other than `using-deep-research` — left intact.
- The 15 source subagents — left intact, used as-is to test Task 6.

---

## Task 0: Spike branch + scaffold

**Files:**
- Create: `docs/spike-results/2026-05-19-opencode-js-plugin.md`
- Create: `.opencode/plugins/scholar.js` (empty placeholder)

- [ ] **Step 1: Create spike branch**

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot
git checkout -b spike/opencode-js-plugin
```

Expected: `Switched to a new branch 'spike/opencode-js-plugin'`.

- [ ] **Step 2: Create spike-results scaffold**

Write `docs/spike-results/2026-05-19-opencode-js-plugin.md`:

```markdown
# Spike: OpenCode JS-plugin path registration

**Date:** 2026-05-19
**Branch:** spike/opencode-js-plugin
**OpenCode version:** 1.3.0
**Status:** IN PROGRESS

## Hypothesis

A 70-line JS plugin at `.opencode/plugins/scholar.js` can replace `packages/adapters/opencode/generate.py` (~250 lines) by registering `plugins/scholar-ip/skills/` as a skills-discovery path at OpenCode startup. References/ subdirectories ride along automatically.

## Validations

- [ ] (Task 1) OpenCode 1.3.0 exposes a `config` plugin hook that accepts a `skills.paths` array.
- [ ] (Task 3) After install, `opencode` discovers all 25 scholar-ip skills from source.
- [ ] (Task 4) OpenCode tolerates source frontmatter fields it doesn't recognise (`subagents`, `triggers`, `outputs`, etc.) without rejecting the skill.
- [ ] (Task 5) A `references/spike-probe.md` file inside a skill is readable by the agent when the skill is loaded.
- [ ] (Task 6) OpenCode exposes an equivalent `agents.paths` registration (or a documented alternative for subagent discovery).

## Verdict

(filled in at Task 7)

## Evidence

(filled in per task)
```

- [ ] **Step 3: Create empty plugin file**

Write `.opencode/plugins/scholar.js`:

```javascript
// Spike: replaces .opencode/{commands,agents,skills}/ rendered output by
// pointing OpenCode at plugins/scholar-ip/ source directly. Will be filled in
// at Task 2 after API research completes. Do NOT load this plugin yet.
```

- [ ] **Step 4: Commit scaffold**

```bash
git add docs/spike-results/2026-05-19-opencode-js-plugin.md .opencode/plugins/scholar.js
git commit -m "spike(opencode): scaffold JS-plugin spike branch"
```

Expected: one commit, two new files.

---

## Task 1: Research OpenCode 1.3.0 plugin API

**Goal:** Confirm the `config` plugin hook signature and `skills.paths` registration are real on the installed version.

**Files:**
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md` (append findings)

- [ ] **Step 1: Locate OpenCode plugin docs**

Run:
```bash
opencode --help 2>&1 | head -40
opencode docs plugins 2>&1 | head -40 || echo "(no docs subcommand)"
```

If `opencode docs plugins` is not a real subcommand, find the canonical docs and source repo first:
```bash
# Find any pointer to docs/source from the installed binary's package metadata
which opencode | xargs -I{} dirname {} | xargs -I{} ls {}/.. 2>/dev/null
brew info opencode 2>/dev/null | head -10        # if installed via Homebrew
npm info opencode 2>/dev/null | head -20         # if available on npm
```

Goal: surface the **authoritative** docs URL and source-repo URL from package metadata. Do NOT guess URLs — only follow ones the metadata or local files actually provide. Once you have the real docs/source pointer, read the plugin-hook documentation there.

Expected: one of these surfaces — local CLI help, package metadata pointing at official docs, or the source repo URL — describes plugin hooks.

- [ ] **Step 2: Find the actual `config` hook signature**

Search for the hook in OpenCode's installed source on disk:
```bash
which opencode | xargs ls -l
brew --prefix opencode 2>/dev/null
find /opt/homebrew/Cellar/opencode 2>/dev/null -name "*.js" -path "*plugin*" | head -5
find /opt/homebrew/lib/node_modules 2>/dev/null -name "*.d.ts" -path "*opencode*" | head -10
# Also check the npm global root in case it's installed via npm:
npm root -g 2>/dev/null
```

If you find the source repo URL via Step 1, use `gh api repos/<owner>/<repo>/...` to drill into the plugin contract. **Do not type a repo slug you have not confirmed** — the Step 1 metadata is the source of truth for the repo location.

Goal: find the file that defines the `Plugin` type or the `experimental.chat.messages.transform` / `config` hook contract.

- [ ] **Step 3: Confirm `skills.paths` is a real config field**

Once the plugin contract is located (either on local disk via the find/brew commands above, or in the confirmed source repo via gh), grep for `skills.paths` and `skills?.paths` and read the surrounding code to confirm the key name is exact. Reference: `superpowers.js:103-109` uses `config.skills.paths` against the same OpenCode version family and works in production — that is supporting evidence but not a substitute for confirming against OpenCode 1.3.0 specifically.

Acceptance: either find `config.skills.paths` (or equivalent like `config.skill.paths` — note exact key) in OpenCode source, OR confirm via docs that adding to `config.skills` mutates the discovery set.

- [ ] **Step 4: Document findings in spike-results**

Append to `docs/spike-results/2026-05-19-opencode-js-plugin.md` under `## Evidence`:

```markdown
### Task 1: Plugin API research

- **Plugin hook contract:** <paste the type signature / quote the docs>
- **Skills discovery key (exact):** `config.skills.paths` | `config.skill.paths` | <other>
- **Source:** <URL or local path to the file that proves it>
- **Verdict:** REAL | MISSING | UNCLEAR
- **If MISSING:** stop the spike here, document why, fall back to render-pipeline extension (Path A from the architecture review).
```

- [ ] **Step 5: Decision gate**

If Task 1 finds the API is MISSING or UNCLEAR after 20 minutes of research: STOP. Commit the spike-results file with verdict `BLOCKED — API not confirmed`, post findings to the user, and request direction. Do not proceed to Task 2 on a guessed API.

- [ ] **Step 6: Commit research findings**

```bash
git add docs/spike-results/2026-05-19-opencode-js-plugin.md
git commit -m "spike(opencode): document OpenCode 1.3.0 plugin API findings"
```

Expected: one commit, spike-results file updated with the Task 1 evidence block.

---

## Task 2: Write the minimal JS plugin

**Files:**
- Modify: `.opencode/plugins/scholar.js` (fill in the body)

- [ ] **Step 1: Write the plugin body**

Replace the placeholder in `.opencode/plugins/scholar.js` with the following (adjust `skills.paths` key name based on Task 1 evidence if it differs):

```javascript
/**
 * scholar-ip-copilot plugin for OpenCode 1.3.0+
 *
 * Registers plugins/scholar-ip/{skills,agents}/ as OpenCode discovery paths
 * at session start. No file copying, no symlinks — OpenCode reads the source
 * tree directly. Lets references/ subdirectories ride along automatically.
 *
 * Modeled on superpowers' .opencode/plugins/superpowers.js (135 lines).
 */

import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const ScholarPlugin = async ({ client, directory }) => {
  // .opencode/plugins/scholar.js sits two levels below the repo root:
  // <repo>/.opencode/plugins/scholar.js -> <repo>/plugins/scholar-ip/...
  const repoRoot = path.resolve(__dirname, '../..');
  const sourceSkillsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'skills');
  const sourceAgentsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'agents');

  return {
    config: async (config) => {
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(sourceSkillsDir)) {
        config.skills.paths.push(sourceSkillsDir);
      }

      // Only add agents path if Task 6 confirmed the agents.paths key exists.
      // Until then, leave this commented so a misnamed key doesn't silently
      // shadow a real config field on future OpenCode versions.
      // config.agents = config.agents || {};
      // config.agents.paths = config.agents.paths || [];
      // if (!config.agents.paths.includes(sourceAgentsDir)) {
      //   config.agents.paths.push(sourceAgentsDir);
      // }
    },
  };
};
```

- [ ] **Step 2: Sanity-check the path math**

Run:
```bash
node --eval "import('./.opencode/plugins/scholar.js').then(m => console.log(typeof m.ScholarPlugin))"
```

Expected output: `function`.

If you see `SyntaxError` or `Cannot find module`, fix the import / export shape before continuing.

- [ ] **Step 3: Verify path resolution lands on the source tree**

Run:
```bash
node --input-type=module --eval "
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(new URL('file://$(pwd)/.opencode/plugins/scholar.js')));
const repoRoot = path.resolve(__dirname, '../..');
console.log(path.join(repoRoot, 'plugins', 'scholar-ip', 'skills'));
"
```

Expected output: `/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/plugins/scholar-ip/skills`.

If the path is wrong (e.g., resolves to `.opencode/plugins/scholar-ip/skills`), the `path.resolve(__dirname, '../..')` is off — adjust the `'../..' ` segment count to match the actual depth.

- [ ] **Step 4: Commit the plugin**

```bash
git add .opencode/plugins/scholar.js
git commit -m "spike(opencode): minimal JS plugin registers source skills dir"
```

Expected: one commit, one file modified.

---

## Task 3: Verify OpenCode discovers all 25 skills via the plugin

**Goal:** Empirical end-to-end: install the plugin into the user's OpenCode and confirm every source skill appears.

**Files:**
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md`

- [ ] **Step 1: Locate the OpenCode config file**

Run:
```bash
ls -la ~/.config/opencode/opencode.json 2>&1
ls -la ./opencode.json 2>&1
```

Expected: at least one of these exists, or both are missing (in which case you'll create the project-local `./opencode.json` in Step 2).

- [ ] **Step 2: Wire the plugin into project-local opencode.json**

If `./opencode.json` does not exist, create it:

```bash
cat > ./opencode.json <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["./.opencode/plugins/scholar.js"]
}
EOF
```

If it already exists, **do not overwrite** — instead, print its contents and ASK the user to add `"./.opencode/plugins/scholar.js"` to the `plugin` array. Never modify a config file the user owns without confirmation.

- [ ] **Step 3: Snapshot the baseline (skills available BEFORE spike)**

Run OpenCode in this directory and ask it:
```
list all available skills, one per line
```

Save the output (manually copy or `opencode > /tmp/baseline.txt` if non-interactive mode supports it). This is the "before" set — we need to know what would have appeared from `.opencode/skills/` (rendered output) so we can detect double-counting in Step 5.

- [ ] **Step 4: Restart OpenCode and re-list skills**

Quit OpenCode. Re-open it in the same directory. The plugin should now be loaded (look for any startup log message from `scholar.js`).

Ask again:
```
list all available skills, one per line
```

- [ ] **Step 5: Compare**

Acceptance criteria:
- All 25 source skill IDs appear (compare against `ls plugins/scholar-ip/skills` — should produce a list of 25 directory names).
- No skill is listed twice (if rendered `.opencode/skills/` is still present, OpenCode might discover both copies — note this and continue; the duplicate is a known consequence of the spike being additive, will resolve when the render pipeline is removed in follow-up).

- [ ] **Step 6: Record evidence**

Append to `docs/spike-results/2026-05-19-opencode-js-plugin.md`:

```markdown
### Task 3: Skill discovery via JS plugin

- **Source skill count:** 25 (verified: `ls plugins/scholar-ip/skills | wc -l`)
- **OpenCode discovered count:** <number>
- **Discovered IDs:** <paste list>
- **Missing IDs:** <list any that didn't appear>
- **Duplicates:** <count if rendered .opencode/skills/ was also discovered>
- **Verdict:** PASS | PARTIAL | FAIL
```

- [ ] **Step 7: Commit**

```bash
git add docs/spike-results/2026-05-19-opencode-js-plugin.md opencode.json
git commit -m "spike(opencode): verify 25-skill discovery via JS plugin"
```

Expected: one commit. (If `opencode.json` was pre-existing and you did not modify it, omit it from the `git add`.)

---

## Task 4: Frontmatter tolerance — does OpenCode reject unknown fields?

**Goal:** Source SKILL.md files declare frontmatter fields like `subagents`, `triggers`, `outputs`, `allowed_tools` that the render pipeline currently translates away. The spike asks: does OpenCode just ignore unknown keys?

**Files:**
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md`

- [ ] **Step 1: Pick a "rich frontmatter" skill**

Run:
```bash
head -20 plugins/scholar-ip/skills/deep-literature-review/SKILL.md
```

Inspect the frontmatter. Confirm it has multiple fields beyond `name` + `description` (e.g., `triggers`, `provides`, `id`, `kind`, `title`).

- [ ] **Step 2: Load the skill in OpenCode**

In OpenCode (with the plugin active), prompt:
```
load the deep-literature-review skill and tell me its first heading
```

Acceptance:
- OpenCode loads the skill without error.
- The agent reports the first heading from `plugins/scholar-ip/skills/deep-literature-review/SKILL.md` (which is `# deep-literature-review`).
- No warning about "unknown frontmatter field" or "schema validation failed".

- [ ] **Step 3: Try a skill with `kind: command` (cross-purpose) frontmatter**

Pick any of the 25 source skills that has `kind:` in frontmatter:
```bash
grep -l "^kind:" plugins/scholar-ip/skills/*/SKILL.md | head -3
```

Load one of them in OpenCode the same way. Acceptance: same — loads cleanly.

- [ ] **Step 4: Record evidence**

Append to spike-results:

```markdown
### Task 4: Frontmatter tolerance

- **Tested skills:** deep-literature-review, <second skill>, <third skill>
- **OpenCode reaction to unknown fields:** SILENT IGNORE | WARNING | REJECTION
- **Quote any error / warning text:** <verbatim>
- **Verdict:** PASS (silently ignored) | PARTIAL (warnings but loads) | FAIL (rejection)
```

- [ ] **Step 5: Commit**

```bash
git add docs/spike-results/2026-05-19-opencode-js-plugin.md
git commit -m "spike(opencode): frontmatter tolerance test (3 skills)"
```

Expected: one commit.

---

## Task 5: References/ subdirectory visibility

**Goal:** Confirm a `references/spike-probe.md` inside a skill is readable when that skill is loaded.

**Files:**
- Create: `plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md`
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md`

- [ ] **Step 1: Add the probe file**

Run:
```bash
mkdir -p plugins/scholar-ip/skills/using-deep-research/references
```

Write `plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md`:

```markdown
# Spike probe

This file exists to verify OpenCode can read `references/` subdirectories of a
skill when that skill is loaded via the JS-plugin path-registration mechanism.

Sentinel string: `OPENCODE-REFERENCES-SPIKE-OK-2026-05-19`
```

- [ ] **Step 2: Verify the file is on disk**

```bash
cat plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md | head -5
```

Expected: prints the heading and sentinel string.

- [ ] **Step 3: Confirm OpenCode does NOT misclassify it as a separate skill**

In OpenCode (plugin active), list skills again:
```
list all available skills
```

Acceptance: the list still has 25 entries. `spike-probe` is NOT in the list (because `references/*.md` should not be picked up as standalone skills). If it IS in the list, OpenCode's discovery is doing rglob-like behaviour and the entire reference/ pattern is incompatible — record FAIL and stop.

- [ ] **Step 4: Verify the file is readable from within the loaded skill**

In OpenCode:
```
load the using-deep-research skill, then read the file references/spike-probe.md relative to the skill and tell me the sentinel string
```

Acceptance: the agent reports `OPENCODE-REFERENCES-SPIKE-OK-2026-05-19`.

If the agent reports the file is not found, try with the absolute path:
```
read /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md
```

If that works but the relative path didn't, document this — it means progressive disclosure via relative links requires absolute paths in skill bodies, which is a real authoring constraint.

- [ ] **Step 5: Record evidence**

Append to spike-results:

```markdown
### Task 5: References/ visibility

- **Probe file path:** plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md
- **Misclassified as separate skill:** YES | NO
- **Sentinel readable via relative path:** YES | NO
- **Sentinel readable via absolute path:** YES | NO
- **Verdict:** PASS (relative path works) | PARTIAL (abs path only) | FAIL
```

- [ ] **Step 6: Commit**

```bash
git add plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md docs/spike-results/2026-05-19-opencode-js-plugin.md
git commit -m "spike(opencode): references/ visibility probe"
```

Expected: one commit, two files.

---

## Task 6: Subagents discovery — does `agents.paths` exist?

**Goal:** Source has 15 subagents in `plugins/scholar-ip/agents/`. The render pipeline currently translates these to OpenCode `mode: subagent` files at `.opencode/agents/`. Find out whether OpenCode 1.3.0 has a runtime hook to register additional agent search paths.

**Files:**
- Modify: `.opencode/plugins/scholar.js` (uncomment the agents block IF the key is confirmed)
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md`

- [ ] **Step 1: Research the agents.paths key**

Search the same way as Task 1:
```bash
gh api repos/sst/opencode/contents/packages/opencode/src --jq '.[].name' 2>&1
# Drill into config/discovery code; grep for "agents" + "paths"
```

Or check OpenCode docs for "subagent discovery" / "agents config".

- [ ] **Step 2: Three possible outcomes**

  - **(a) `config.agents.paths` exists:** uncomment the block in `.opencode/plugins/scholar.js` (Task 2 left this as a commented stub) and proceed to Step 3.
  - **(b) A different key exists** (e.g., `config.agent.paths`, `config.subagents.paths`): update the JS plugin with the correct key, proceed to Step 3.
  - **(c) No runtime agent path registration exists:** OpenCode requires agents to live in `.opencode/agents/` only. Document this limitation. The render pipeline for agents would still be needed — only skills can be sourced directly. Skip to Step 5.

- [ ] **Step 3: (If a or b) Enable agent registration in the plugin**

Edit `.opencode/plugins/scholar.js` and uncomment the agents block:

```javascript
config.agents = config.agents || {};
config.agents.paths = config.agents.paths || [];
if (!config.agents.paths.includes(sourceAgentsDir)) {
  config.agents.paths.push(sourceAgentsDir);
}
```

- [ ] **Step 4: Verify in OpenCode**

Restart OpenCode. Prompt:
```
list all available subagents
```

Acceptance: 15 source subagents appear (compare: `ls plugins/scholar-ip/agents | wc -l` = 15).

- [ ] **Step 5: Record evidence**

Append to spike-results:

```markdown
### Task 6: Subagent discovery

- **Key found in OpenCode source:** `config.agents.paths` | other: <name> | NONE
- **Source/doc reference:** <URL or path>
- **(if applicable) Discovered subagent count:** <N> out of 15
- **Verdict:** PASS | PARTIAL (skills work but agents need render) | FAIL
```

- [ ] **Step 6: Commit**

```bash
git add .opencode/plugins/scholar.js docs/spike-results/2026-05-19-opencode-js-plugin.md
git commit -m "spike(opencode): subagent path registration check"
```

Expected: one commit. (Plugin file may have no changes if outcome was (c); commit the doc anyway.)

---

## Task 7: Decision document + spike disposition

**Goal:** Capture a final verdict, recommend the follow-up PR scope, and decide what to do with the probe/plugin files.

**Files:**
- Modify: `docs/spike-results/2026-05-19-opencode-js-plugin.md`

- [ ] **Step 1: Aggregate the per-task verdicts**

From Tasks 1, 3, 4, 5, 6 — collect each `Verdict: ...` line. Compute the overall:
- All PASS → **GREEN** (recommend follow-up PR to remove `opencode/generate.py`)
- Mix of PASS + PARTIAL → **AMBER** (recommend follow-up PR with documented carve-out, e.g., "skills via plugin, agents still rendered")
- Any FAIL → **RED** (do not pursue Path D for OpenCode; fall back to Path A — extend render pipeline to copy references/)

- [ ] **Step 2: Write the verdict section**

Replace `**Status:** IN PROGRESS` with `**Status:** <GREEN|AMBER|RED>` and append at the bottom of spike-results:

```markdown
## Verdict

**Overall:** GREEN | AMBER | RED

### What works (evidence-backed)
- <bullet per validated capability>

### What doesn't (with workaround if AMBER)
- <bullet per limitation>

### Recommended follow-up

(If GREEN)
- Open PR: remove `packages/adapters/opencode/generate.py`, remove `render-opencode` Makefile target, delete `.opencode/{skills,agents,commands}/` rendered output, keep `.opencode/plugins/scholar.js` + `opencode.json`.
- Risk: Claude Code and Codex adapters untouched, so they remain on the render pipeline. References/ progressive disclosure for the deepresearch split (the original motivating problem) becomes feasible for OpenCode users but still blocked for Claude Code and Codex until those adapters are upgraded separately.

(If AMBER)
- Open PR with documented carve-out: <state which capability stays rendered>
- Open follow-up issue: <state what to research next>

(If RED)
- Abandon Path D for OpenCode.
- Open issue: extend render pipeline per Path A — propagate `references/` from source to all three rendered trees. ~125 lines of Python per prior estimate.

### Disposition of spike files

- `.opencode/plugins/scholar.js`: KEEP (becomes the OpenCode entrypoint) | DELETE (RED outcome).
- `opencode.json`: KEEP if user did not pre-own; otherwise leave as user's file.
- `plugins/.../using-deep-research/references/spike-probe.md`: DELETE (probe-only) regardless of outcome — real references/ files come in the deepresearch split PR.
```

- [ ] **Step 3: Clean up the probe file (always)**

```bash
rm plugins/scholar-ip/skills/using-deep-research/references/spike-probe.md
# Remove the references/ directory if it's now empty.
rmdir plugins/scholar-ip/skills/using-deep-research/references 2>/dev/null || true
```

- [ ] **Step 4: If RED, also clean up the plugin and config**

```bash
# Only if Step 1 produced a RED verdict:
rm .opencode/plugins/scholar.js
# If you created ./opencode.json fresh in Task 3 Step 2, remove it.
# If you only edited an existing one, ask the user to revert their edit; do not undo it for them.
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "spike(opencode): final verdict and cleanup — <GREEN|AMBER|RED>"
```

Expected: one commit, no stray files.

- [ ] **Step 6: Push the branch**

```bash
git push -u origin spike/opencode-js-plugin
```

Expected: branch published, remote URL printed.

- [ ] **Step 7: Surface the verdict**

Print the final summary to the user with these three lines:
- `Spike outcome: <GREEN|AMBER|RED>`
- `Spike branch: spike/opencode-js-plugin (pushed)`
- `Recommended next step: <one-sentence pointer to the follow-up>`

Do NOT auto-open a follow-up PR or merge. The user decides whether to proceed based on the verdict.

---

## Rollback

The spike branch is isolated. To abandon:

```bash
git checkout master
git branch -D spike/opencode-js-plugin
# Optionally also: git push origin --delete spike/opencode-js-plugin
```

If the user already pasted the plugin reference into their global `~/.config/opencode/opencode.json`, ask them to remove the line manually — do not edit their global config for them.

---

## Out of scope (explicitly excluded)

- Modifying `packages/adapters/opencode/generate.py`. Spike is additive; removal is a follow-up.
- Touching the Claude Code or Codex adapters.
- The deepresearch split. The spike unlocks the prerequisite (references/ on OpenCode) but does not perform the split.
- Performance benchmarking of cold-start time with the plugin. Functional validation only.
- Adding automated tests for the JS plugin. Spike validations are manual with explicit acceptance criteria; investing in CI for spike code is premature.
