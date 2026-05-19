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
