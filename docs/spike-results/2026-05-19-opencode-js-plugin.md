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
