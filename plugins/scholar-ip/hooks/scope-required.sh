#!/usr/bin/env bash
# scope-required UserPromptSubmit hook for scholar-ip (EviDraft).
# Blocks gated /scholar:* commands if no scope file exists.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
read_stdin
PROMPT="$(stdin_jq_field '.prompt // .user_prompt')"
# Fallback: if jq missing or no prompt field, treat raw stdin as the prompt.
[ -n "${PROMPT:-}" ] || PROMPT="${LIB_STDIN:-}"

# Only enforce when the prompt starts with one of the gated slash commands.
GATED='^/scholar:(paper-idea|paper-draft|patent-scout|patent-claims|deepresearch|polish)\b'
printf '%s' "$PROMPT" | grep -Eq "$GATED" || exit 0

# Pass if at least one scope file exists.
shopt -s nullglob 2>/dev/null || true
matches=( "$PROJECT_DIR"/.evidraft/scope/*.md )
if [ "${#matches[@]}" -gt 0 ] && [ -e "${matches[0]}" ]; then
  exit 0
fi

emit_block_decision "scope file missing — run /scholar:brainstorming first"
