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
