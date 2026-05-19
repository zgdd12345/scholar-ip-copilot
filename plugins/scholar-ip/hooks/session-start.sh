#!/usr/bin/env bash
# session-start SessionStart hook for scholar-ip (EviDraft).
# Emits the using-scholar-ip-copilot SKILL.md body as additionalContext so
# Claude Code knows the workflow on every fresh session.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL_PATH="$PLUGIN_ROOT/skills/using-scholar-ip-copilot/SKILL.md"

if [ ! -f "$SKILL_PATH" ]; then
  # Nothing to inject; succeed silently.
  exit 0
fi

CONTENT="$(cat "$SKILL_PATH")"

if command -v jq >/dev/null 2>&1; then
  jq -n --arg c "$CONTENT" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: $c
    }
  }'
else
  # Crude JSON fallback: escape only the bare minimum (backslash + quote + newline).
  ESC="$(printf '%s' "$CONTENT" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS="\\n"} {print}')"
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ESC"
fi
exit 0
