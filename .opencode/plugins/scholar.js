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

// DIAGNOSTIC #1: fires on ES-module evaluation. If this never appears in
// stderr, OpenCode never imported the plugin file at all.
console.error('[scholar-plugin] DIAG-1 module loaded; __dirname=' + __dirname);

export const ScholarPlugin = async ({ client, directory }) => {
  // .opencode/plugins/scholar.js sits two levels below the repo root:
  // <repo>/.opencode/plugins/scholar.js -> <repo>/plugins/scholar-ip/...
  const repoRoot = path.resolve(__dirname, '../..');
  const sourceSkillsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'skills');
  const sourceAgentsDir = path.join(repoRoot, 'plugins', 'scholar-ip', 'agents');

  // DIAGNOSTIC #2: fires when OpenCode invokes the exported factory function.
  // If DIAG-1 fires but DIAG-2 does not, OpenCode loaded the module but never
  // instantiated the plugin.
  console.error('[scholar-plugin] DIAG-2 ScholarPlugin invoked; sourceSkillsDir=' + sourceSkillsDir + '; directory=' + directory);

  if (!fs.existsSync(sourceSkillsDir)) {
    throw new Error(
      `scholar-ip plugin: source skills directory not found at ${sourceSkillsDir}. ` +
      `This plugin must be loaded from <repo>/.opencode/plugins/scholar.js (project-local install). ` +
      `__dirname was: ${__dirname}.`
    );
  }

  return {
    config: async (config) => {
      // DIAGNOSTIC #3: fires when OpenCode invokes the config hook. If DIAG-2
      // fires but DIAG-3 does not, OpenCode received the plugin object but
      // chose not to call our config hook (wrong key name / wrong contract).
      console.error('[scholar-plugin] DIAG-3 config hook fired; pre-push config.skills=' + JSON.stringify(config.skills));

      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(sourceSkillsDir)) {
        config.skills.paths.push(sourceSkillsDir);
      }

      // DIAGNOSTIC #4 (post-push state): if DIAG-3 fires but the skill list
      // still does not include source skills, the key name `skills.paths` is
      // not the contract OpenCode 1.3.0 reads from.
      console.error('[scholar-plugin] DIAG-4 post-push config.skills.paths=' + JSON.stringify(config.skills.paths));

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
