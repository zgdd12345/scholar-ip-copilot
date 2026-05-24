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

# ---------------------------------------------------------------------------
# Per-command hook opt-out
#
# The "active command" is the /scholar:<cmd> currently running in this turn.
# scope-required.sh (UserPromptSubmit) records it; PostToolUse hooks read it
# and consult the command's frontmatter `hooks:` field to decide whether to
# fire. Treats `hooks:` as an explicit allowlist:
#   - field missing  → all hooks fire (backward-compat)
#   - hooks: []      → no hooks fire (lite path: reading-list, using, ...)
#   - hooks: [a, b]  → only a and b fire; others are skipped
#
# State lives OUTSIDE the project tree so commands like /scholar:reading-list
# can keep their "output file is the only artefact" promise. Precedence:
#   $SCHOLAR_IP_STATE_DIR  (explicit override; test fixtures use this)
#   $XDG_STATE_HOME/scholar-ip   (Linux convention)
#   $TMPDIR/scholar-ip           (macOS / fallback)
#   /tmp/scholar-ip              (last resort)
# Keyed by project hash + session id so two concurrent Claude Code sessions
# in the same repo do not trample each other's active-cmd.

_state_root() {
  if [ -n "${SCHOLAR_IP_STATE_DIR:-}" ]; then
    printf '%s' "$SCHOLAR_IP_STATE_DIR"
  elif [ -n "${XDG_STATE_HOME:-}" ]; then
    printf '%s/scholar-ip' "$XDG_STATE_HOME"
  else
    printf '%s/scholar-ip' "${TMPDIR:-/tmp}"
  fi
}

# Short stable digest of the project dir, so /a/b/foo and /c/d/foo don't share.
_project_key() {
  local proj="${CLAUDE_PROJECT_DIR:-$PWD}"
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$proj" | shasum -a 1 | cut -c1-12
  elif command -v sha1sum >/dev/null 2>&1; then
    printf '%s' "$proj" | sha1sum | cut -c1-12
  else
    # No hash tool — collapse the path into a fs-safe basename suffix.
    printf '%s' "$proj" | tr -c '[:alnum:]' '_' | tail -c 24
  fi
}

# Session id from the Claude Code hook envelope; falls back to parent PID so
# single-session runs still get a unique slot. Sanitised to fs-safe chars.
_session_key() {
  local sid
  sid="$(stdin_jq_field '.session_id')"
  [ -n "$sid" ] || sid="pid-${PPID:-0}"
  printf '%s' "$sid" | tr -c '[:alnum:]_-' '_'
}

_state_dir() {
  printf '%s/%s/%s' "$(_state_root)" "$(_project_key)" "$(_session_key)"
}

_state_file() {
  printf '%s/active-cmd' "$(_state_dir)"
}

# Lazy GC of orphan state slots. Each Claude Code session opens a new
# `<project-hash>/<session-key>/` directory under the state root and never
# revisits it once the session ends, so long-running users accumulate orphan
# dirs forever — particularly on Linux where $XDG_STATE_HOME is permanent.
#
# Sweep at most once per 7 days (tracked via a sentinel file at the state
# root). On each sweep, delete `active-cmd` files whose mtime is older than
# 30 days, then prune now-empty session and project directories.
#
# Conservative thresholds: 30 days is well beyond any real session window
# (Claude Code sessions are typically hours, not weeks), and the 7-day
# cooldown keeps the sweep amortised. Failures are silent — GC must never
# make a hook fail. Disable via `SCHOLAR_IP_GC_DISABLE=1` if desired.
_gc_state() {
  [ "${SCHOLAR_IP_GC_DISABLE:-}" = "1" ] && return 0
  local root sentinel
  root="$(_state_root)"
  # First-ever invocation: the state root has never been created (no command
  # has called record_active_command yet). Return without touching the
  # sentinel — nothing to GC. The next invocation will see the root (created
  # by record_active_command's mkdir) and the sentinel can finally land.
  # Net effect: the very first session pays no GC cost, every subsequent
  # session participates in the 7-day cooldown sweep.
  [ -d "$root" ] || return 0
  sentinel="$root/.last-gc"
  # Cooldown: if the sentinel was touched within the last 7 days, skip.
  if [ -f "$sentinel" ] \
     && find "$sentinel" -mtime -7 -print 2>/dev/null | grep -q .; then
    return 0
  fi
  # Delete active-cmd files older than 30 days. -mtime +30 is portable
  # across GNU and BSD find. Errors swallowed (best-effort).
  #
  # Note: the same `active-cmd` mtime is consulted by record_active_command
  # under a 24-h TTL (see SCHOLAR_IP_ACTIVE_CMD_TTL). Those two thresholds
  # are intentionally independent — TTL clears stale command state mid-flow,
  # GC reclaims orphan directories after the session has been dead for a
  # month. A 25-hour idle session sees its slot cleared by TTL but not by
  # GC; that is correct.
  find "$root" -type f -name 'active-cmd' -mtime +30 -delete 2>/dev/null || true
  # Prune now-empty session/project dirs (don't delete root itself).
  find "$root" -mindepth 1 -type d -empty -delete 2>/dev/null || true
  # Touch sentinel even if nothing was deleted — the next sweep cooldown
  # starts from this attempt, not from the last successful delete.
  touch "$sentinel" 2>/dev/null || true
}

# Parse the user prompt; if it begins with "/scholar:<cmd>", write <cmd> to
# the state file (just the bare cmd name, no leading slash) and refresh its
# mtime — a fresh /scholar:<cmd> always wins.
#
# If the prompt does NOT carry a /scholar: prefix (e.g. a clarifying answer
# inside a multi-turn workflow), preserve the existing state file as long as
# it was written within TTL. Past TTL, clear it so a stale command name
# from a prior session does not leak through. Default TTL = 86400 s (24 h);
# override via env SCHOLAR_IP_ACTIVE_CMD_TTL (seconds).
#
# Rationale: the previous "clear on any non-/scholar prompt" rule broke
# downstream PostToolUse opt-out for every multi-turn /scholar:<cmd> flow
# (the user's clarifying reply has no slash prefix → state wiped → hooks
# see empty state → opt-out fails). The TTL window is measured from the
# last /scholar:<cmd> write; non-slash preserves do NOT bump the mtime, so
# the TTL truly bounds "how long since the user last named a command".
#
# Triggers a lazy GC sweep after the write — at most once per 7 days; see
# `_gc_state`.
record_active_command() {
  local prompt="$1"
  local sdir sfile tmp cmd ttl now mtime
  sdir="$(_state_dir)"
  sfile="$(_state_file)"
  mkdir -p "$sdir" 2>/dev/null || return 0
  cmd="$(printf '%s' "$prompt" | awk '
    match($0, /^\/scholar:[a-zA-Z0-9_-]+/) {
      print substr($0, RSTART+9, RLENGTH-9); exit
    }')"
  if [ -n "$cmd" ]; then
    # Atomic replace: write to a sibling then mv. Avoids exposing a truncated
    # file to PostToolUse readers racing against UserPromptSubmit.
    tmp="$sfile.tmp.$$"
    printf '%s\n' "$cmd" > "$tmp" && mv -f "$tmp" "$sfile"
  else
    ttl="${SCHOLAR_IP_ACTIVE_CMD_TTL:-86400}"
    # Refuse non-integer TTL: bash `$((...))` on a non-numeric string aborts
    # under `set -euo pipefail` (scope-required.sh:6) — silently fall back
    # to default rather than killing the hook.
    case "$ttl" in
      ''|*[!0-9]*) ttl=86400 ;;
    esac
    if [ -f "$sfile" ]; then
      now="$(date +%s)"
      # GNU stat first (Linux); BSD stat second (macOS / *BSD). The reverse
      # order is broken: GNU `stat -f %m` is valid but returns mount point,
      # not mtime, so a BSD-first chain short-circuits with garbage on Linux
      # and the arithmetic below aborts under set -e.
      mtime="$(stat -c %Y "$sfile" 2>/dev/null \
               || stat -f %m "$sfile" 2>/dev/null \
               || printf '0')"
      # Future mtime (NFS / clock skew / restored backup) → treat as corrupt
      # and clear, else `now - mtime` is negative and the slot is preserved
      # indefinitely.
      if [ "$now" -lt "$mtime" ] || [ "$((now - mtime))" -ge "$ttl" ]; then
        tmp="$sfile.tmp.$$"
        : > "$tmp" && mv -f "$tmp" "$sfile"
      fi
      # else: preserve untouched (do NOT bump mtime — TTL window is from the
      # last /scholar:<cmd> write, not from the last preserve).
    fi
  fi
  _gc_state
}

# Return 0 if the named hook is DISABLED for the currently active command,
# 1 otherwise. Defaults to "active" on every uncertain path so we never
# silently weaken a hook for a command that has no opt-out declared.
#
# Source of truth: hooks/command-hooks.json, emitted by the claude_code
# adapter alongside hooks.json. The rendered command frontmatter no longer
# carries the source `hooks:` field (CC only recognises description /
# argument-hint / allowed-tools), so the adapter projects each command's
# allowlist into this sidecar.
#
# DEPENDENCY: jq is required to parse the sidecar (see line below). If jq is
# not on PATH, this function returns 1 ("not disabled"), which re-enables
# every hook for every command — including the lite-mode ones that declared
# `hooks: []`. This is fail-closed (a hook firing where it shouldn't is
# noisier than silent miscompliance) but it means `/scholar:reading-list` on
# a no-jq box would suddenly see citation-guard fire. The hard-exclude path
# globs inside each hook (e.g. citation-guard.sh's manuscript-section
# pattern) are the runtime backstop. Document any new lite-mode command's
# expected paths there as well, not only here.
hook_disabled_by_command() {
  local hook_name="$1"
  local sfile cmd plugin_root map_file allow
  sfile="$(_state_file)"
  [ -s "$sfile" ] || return 1
  cmd="$(head -n1 "$sfile" | tr -d '\n\r ' )"
  [ -n "$cmd" ] || return 1
  plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
  map_file="$plugin_root/hooks/command-hooks.json"
  [ -f "$map_file" ] || return 1
  command -v jq >/dev/null 2>&1 || return 1
  # `null` ← command absent from sidecar (no opt-out declared, all hooks fire).
  # `""`   ← empty allowlist (commands[cmd] == [], all hooks skip).
  # `"a b c"` ← space-joined allowlist; the hook fires only if hook_name is in it.
  allow="$(jq -r --arg c "$cmd" '
    if (.commands | has($c)) then
      (.commands[$c] | join(" "))
    else
      "null"
    end
  ' "$map_file" 2>/dev/null || printf 'null')"
  case "$allow" in
    null) return 1 ;;
    "")   return 0 ;;
  esac
  # Word-bounded match against the space-joined allowlist.
  for h in $allow; do
    [ "$h" = "$hook_name" ] && return 1
  done
  return 0
}
