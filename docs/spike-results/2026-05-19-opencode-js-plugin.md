# Spike: OpenCode JS-plugin path registration

**Date:** 2026-05-19
**Branch:** spike/opencode-js-plugin
**OpenCode version:** 1.3.0
**Status:** RED — Path D-OpenCode not viable on 1.3.0

## Hypothesis

A 70-line JS plugin at `.opencode/plugins/scholar.js` can replace `packages/adapters/opencode/generate.py` (~250 lines) by registering `plugins/scholar-ip/skills/` as a skills-discovery path at OpenCode startup. References/ subdirectories ride along automatically.

## Validations

- [~] (Task 1) OpenCode 1.3.0 exposes a `config` plugin hook that accepts a `skills.paths` array. — **UNCLEAR-but-proceed**: the hook exists and accepts the property (no rejection), but the property is absent from the official `Config` type. Decided empirically.
- [✗] (Task 3) After install, `opencode` discovers all 25 scholar-ip skills from source. — **FAIL**: plugin executed perfectly (all 4 DIAG markers fired) but OpenCode's skill service initialized 60 skills with NONE from the registered source path.
- [skipped] (Task 4) OpenCode tolerates source frontmatter fields it doesn't recognise — blocked by Task 3.
- [skipped] (Task 5) `references/spike-probe.md` readable when skill loads — blocked by Task 3.
- [skipped] (Task 6) `agents.paths` registration — blocked by Task 3.

## Verdict

**Overall:** RED

### What works (evidence-backed)

- JS plugin module loads on OpenCode 1.3.0 startup (`service=plugin path=file://...scholar.js loading plugin`, DIAG-1 fires).
- The exported `ScholarPlugin` factory function is invoked with `{ client, directory }` — `directory` is correctly set to the project root.
- The plugin's `config` async hook is called with a mutable `config` object (initially `config.skills === undefined`).
- Mutating `config.skills.paths` via `.push(...)` succeeds: post-mutation state correctly reflects our absolute path.

### What doesn't (the two independent blockers)

**Blocker A — `config.skills.paths` is type-existent-but-unused on 1.3.0**

OpenCode's skill-discovery service runs at bootstrap and initializes `service=skill count=60` with zero entries from the path we registered. The 60 discovered skills come from hardcoded discovery roots revealed by duplicate-skill WARN logs:

```
WARN service=skill name=agent-browser existing=/Users/fsm/.claude/skills/agent-browser/SKILL.md duplicate=/Users/fsm/.agents/skills/agent-browser/SKILL.md
```

The actual discovery roots on 1.3.0 are `~/.claude/skills/` and `~/.agents/skills/` (user-global), plus project-local equivalents (probably `.claude/skills/`, `.agents/skills/`, `.opencode/skills/`). The 21 `scholar-<cmd>` + 25 `scholar-skill-<id>` entries Alba saw in `opencode` come from the repo's `.agents/skills/` (a `make install-codex` artefact), not from our plugin's pushed path.

This confirms Task 1's UNCLEAR verdict: `config.skills.paths` is in the `Config` interface (or at least not rejected) but is silently ignored by the skill service. Superpowers' production use of this key may rely on a future or fork version; on 1.3.0 it is dead.

**Blocker B — source SKILL.md frontmatter shape is incompatible**

Even if Blocker A were resolved, our source SKILL.md frontmatter would not be accepted by OpenCode's skill loader. Compare:

```yaml
# Our source: plugins/scholar-ip/skills/bib-audit/SKILL.md
id: bib-audit
title: "..."
kind: skill
phase: paper
description: >
  ...
```

```yaml
# What OpenCode discovers (.agents/skills/scholar-skill-bib-audit/SKILL.md, from render):
name: scholar-skill-bib-audit
description: '...'
```

OpenCode's discovery uses the `name:` field as the canonical identifier. Our sources have `id:`, not `name:`. Even with discovery fixed, every source SKILL.md needs frontmatter translation (drop `id/kind/title/phase`, add `name`). That translation is exactly what `packages/adapters/opencode/generate.py` currently does — so we'd be back to a render pipeline. The "zero render" premise of Path D collapses.

### Recommended follow-up

- **Abandon Path D for OpenCode on 1.3.0.** The runtime-path-registration approach does not work; the source-frontmatter shape is incompatible.
- **Path A is the surviving option for unlocking `references/`**: extend the existing render pipeline (`packages/adapters/{claude_code,codex_cli,opencode}/generate.py` + `_shared/loader.py`) to (a) treat each skill as a directory bundle and (b) copy sibling files like `references/`, `assets/`, `scripts/` into each rendered output. Estimated ~125 lines of Python per the architecture review on 2026-05-19.
- **Codex-only carve-out worth re-evaluating later**: superpowers ships to Codex via pure `rsync` to the `prime-radiant-inc/openai-codex-plugins` fork repo. That pattern *could* still work for our Codex output, because Codex's plugin layout is permissive about extra frontmatter. But Codex is a separate adapter from OpenCode — that decision is orthogonal to this spike's verdict.
- **OpenCode upgrade is not a fix on its own.** The remote `oh-my-openagent`'s reliance on `config.skills.paths` *might* indicate a future OpenCode version wires it up, but until empirically verified on a newer release with our source-frontmatter shape, that's speculation. Tracking issue is appropriate; reliance is not.

### Disposition of spike files

- `.opencode/plugins/scholar.js`: **DELETE** (git rm). The plugin works but does nothing useful on 1.3.0; keeping it in the repo would mislead future maintainers.
- `./opencode.json`: **DELETE** (was created by Task 3 Step 2; not committed; uncommitted-rm). Alba's home-global `~/.config/opencode/opencode.json` was never touched.
- `plugins/scholar-ip/skills/.../references/spike-probe.md`: **N/A** — Task 5 was skipped so the probe file was never created.
- `.gitignore` narrow (commit b93d9c2): **KEEP**. It correctly distinguishes `.opencode/plugins/` (source) from `.opencode/{commands,agents,skills,README.md}` (render output). The narrow is a tiny correctness improvement that stands on its own regardless of spike outcome.
- `docs/superpowers/plans/2026-05-19-opencode-js-plugin-spike.md`: **KEEP** on this branch as the spike's executed plan; it will be merged to master in a documentation-only follow-up if Alba wants the institutional memory.

## Evidence

### Task 1: Plugin API research

- **Canonical repo:** `anomalyco/opencode` (github.com/sst/opencode redirects here; 162k stars, "The open source coding agent", maintainer `thdxr` = SST/Dax Raad). The Explore agent's research target was correct.
- **Local version:** 1.3.0 (Homebrew). Latest on npm `opencode-ai`: 1.15.5 (12 minor versions ahead).
- **Plugin hook contract:** `config?: (input: Config) => Promise<void>` — defined in `packages/plugin/src/index.ts` on dev branch of `anomalyco/opencode`. Hook receives a `Config` object and mutates it in place.
- **Skills discovery key (exact):** `config.skills.paths` (array of absolute directory paths).
- **Production evidence:** superpowers 5.0.7 uses this key in `.opencode/plugins/superpowers.js:89-95` (the `config` hook body; `config.skills.paths.push(...)` is on line 93). Works on the same OpenCode release family our local 1.3.0 belongs to. 14 published skills are discovered via this mechanism in real installs.
- **Type-definition gap:** the `Config` interface in `packages/sdk/js/src/gen/types.gen.ts` (dev branch) does NOT declare a `skills` field. Either the runtime loader reads it via dynamic property access (JS allows this) or the type definitions haven't caught up to a runtime-supported API.
- **Verdict:** UNCLEAR — empirically supported by a production plugin in a 162k-star repo (anomalyco/opencode), but absent from the official type contract.
- **Decision (controller, not the agent):** PROCEED to Task 2 with the empirical evidence as basis. Task 3 (skill discovery on local 1.3.0) is the real validation; if it fails, we learn the truth in ~10 min. The type-definition gap is recorded as a long-term maintenance risk to be surfaced in the Task 7 final verdict.
- **Risk surface (for Task 7):** if OpenCode formalises a different skill-path registration API in a future minor release, our plugin breaks silently. Mitigation if spike succeeds: pin to a tested OpenCode version range in the install docs and add a smoke test that exercises `config.skills.paths` registration.

### Task 2: Minimal JS plugin

- **Implementation:** `.opencode/plugins/scholar.js` (commits `8ab03c68` initial → `0c70749` defensive guard → `f263b66` diagnostic instrumentation).
- **Runtime sanity (Node 22):** `node --eval "import('./.opencode/plugins/scholar.js').then(m => console.log(typeof m.ScholarPlugin))"` prints `function`. Path resolution lands at `/Users/fsm/.../plugins/scholar-ip/skills`.
- **Fail-loud guard:** if `sourceSkillsDir` does not exist (e.g., plugin copied to `~/.config/opencode/plugins/`), the factory throws with the resolved path AND `__dirname` for diagnosis. Empirically verified by relocating to `/tmp/fake/opencode/plugins/scholar.js` and observing `CAUGHT: scholar-ip plugin: source skills directory not found at /private/tmp/fake/plugins/scholar-ip/skills. ... __dirname was: /private/tmp/fake/opencode/plugins.`
- **File length:** 58 lines pre-diagnostic, 77 lines after the 4-stage diagnostic added at f263b66.
- **Verdict:** plugin code is correct; the failure mode in Task 3 is downstream of the plugin's job.

### Task 3: Skill-discovery verification

- **Test setup:** `.opencode/{commands,agents,skills,README.md}` stashed to `/tmp/scholar-ip-spike-stash/` (so OpenCode could not discover via rendered output). Project-local `./opencode.json` created with `{ "plugin": ["./.opencode/plugins/scholar.js"] }`. Alba's home-global `~/.config/opencode/opencode.json` was NOT modified.
- **Interactive run output (Alba's session):** OpenCode listed 60 skills total — 14 generic skills bundled by `oh-my-openagent`, 21 `scholar-<cmd>` and 25 `scholar-skill-<id>` entries from the repo's `.agents/skills/` (a `make install-codex` artefact unrelated to this spike). **Zero entries used bare source skill IDs** (`bib-audit`, `brainstorming`, etc.) that would have indicated our plugin's pushed path was being walked.
- **Diagnostic re-run (`opencode run --print-logs --log-level INFO`, 12s):** all four DIAG markers fired in order:
  - `INFO service=plugin path=file://.../.opencode/plugins/scholar.js loading plugin`
  - `[scholar-plugin] DIAG-1 module loaded; __dirname=/Users/fsm/.../scholar-ip-copilot/.opencode/plugins`
  - `[scholar-plugin] DIAG-2 ScholarPlugin invoked; sourceSkillsDir=/Users/fsm/.../plugins/scholar-ip/skills; directory=/Users/fsm/.../scholar-ip-copilot`
  - `[scholar-plugin] DIAG-3 config hook fired; pre-push config.skills=undefined`
  - `[scholar-plugin] DIAG-4 post-push config.skills.paths=["/Users/fsm/.../plugins/scholar-ip/skills"]`
- **Key system log line:** `INFO service=skill count=60 init` — confirms 60 skills discovered, none from our path.
- **Discovery-roots evidence:** duplicate-skill WARNs reveal hardcoded roots:
  - `~/.claude/skills/`
  - `~/.agents/skills/`
  - (project-local equivalents likely included by similar walk)
- **Verdict:** FAIL. Plugin works; OpenCode 1.3.0's skill service does not consume `config.skills.paths`.

### Tasks 4, 5, 6: SKIPPED

All three validations are downstream of Task 3 (frontmatter tolerance, references/ visibility, agents.paths registration). Task 3's failure short-circuits all three — there is no skill-list outcome to verify tolerance against, no references/ to walk because the parent skills were never discovered, and no point researching `agents.paths` if the analogous `skills.paths` is unused.

Markers updated in the Validations checklist above to `[skipped]`.
