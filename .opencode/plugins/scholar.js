/**
 * scholar-ip-copilot plugin for OpenCode 1.3.0+
 *
 * Registers plugins/scholar-ip/{skills,agents}/ as OpenCode discovery paths
 * at session start. No file copying, no symlinks — OpenCode reads the source
 * tree directly. Lets references/ subdirectories ride along automatically.
 *
 * **Install scope:** project-local only. Loaded via the project's
 * `./opencode.json` `plugin` array as `./.opencode/plugins/scholar.js`. The
 * path math (`path.resolve(__dirname, '../..')`) anchors to the plugin file's
 * own location, so a copy at `~/.config/opencode/plugins/scholar.js`
 * resolves to `~/.config/plugins/scholar-ip/skills` which does not exist.
 * Global-install support is a follow-up; for now we fail loudly (see below)
 * rather than silently load a non-existent skills path.
 *
 * Modeled on superpowers' .opencode/plugins/superpowers.js (135 lines).
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const ScholarPlugin = async ({ client, directory }) => {
  // .opencode/plugins/scholar.js sits two levels below the repo root:
  // <repo>/.opencode/plugins/scholar.js -> <repo>/plugins/scholar-ip/...
  const repoRoot = path.resolve(__dirname, '../..');
  const sourceSkillsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'skills');
  const sourceAgentsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'agents');

  if (!fs.existsSync(sourceSkillsDir)) {
    throw new Error(
      `scholar-ip plugin: source skills directory not found at ${sourceSkillsDir}. ` +
      `This plugin must be loaded from <repo>/.opencode/plugins/scholar.js (project-local install). ` +
      `__dirname was: ${__dirname}.`
    );
  }

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
