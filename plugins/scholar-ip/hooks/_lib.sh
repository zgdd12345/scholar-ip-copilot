#!/usr/bin/env bash
# Shared helpers for scholar-ip executable hooks (citation-guard, scope-required, ...).
# Sourced via:  . "$(dirname "$0")/_lib.sh"
#
# Why this exists: citation-guard.sh and scope-required.sh used to emit
# block-decision JSON two different ways — one via `jq -Rs`, the other via
# raw `printf '{"reason":%s}' "\"$REASON\""` which fell over on any reason
# containing a double-quote or backslash. This file picks one safe path.

# Capture stdin once into LIB_STDIN; subsequent stdin_jq_field calls reuse it.
read_stdin() {
  LIB_STDIN="$(cat || true)"
  export LIB_STDIN
}

# Print the value at <jq-path> in LIB_STDIN, or empty if jq is missing /
# the field is absent. Caller decides what to do with empty.
stdin_jq_field() {
  local path="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${LIB_STDIN:-}" | jq -r "${path} // empty" 2>/dev/null || true
  fi
}

# Emit a Claude Code "block" decision with the given reason and exit 2.
# Uses jq when available; falls back to a sed/awk JSON escape so the JSON
# stays valid even when reason contains backslashes, quotes, or newlines.
emit_block_decision() {
  local reason="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$reason" | jq -Rs '{decision:"block", reason:.}'
  else
    local esc
    esc="$(printf '%s' "$reason" \
            | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
            | awk 'BEGIN{ORS="\\n"} {print}')"
    printf '{"decision":"block","reason":"%s"}\n' "$esc"
  fi
  exit 2
}
