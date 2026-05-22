#!/usr/bin/env bash
# scope-required UserPromptSubmit hook for scholar-ip (EviDraft).
# Refuses gated /scholar:* commands when the latest .evidraft/scope/*.md is
# missing, not status:approved, or stale (today > approved_date + staleness_days).
# Mirrors the three rules in scope-required.md §Rules.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
read_stdin
PROMPT="$(stdin_jq_field '.prompt // .user_prompt')"
[ -n "${PROMPT:-}" ] || PROMPT="${LIB_STDIN:-}"

# Record the active /scholar:<cmd> for downstream PostToolUse hooks to consult
# against the command's frontmatter `hooks:` allowlist. Always runs, even on
# non-gated prompts (then it just clears stale state).
record_active_command "$PROMPT"

# Only enforce when the prompt starts with one of the gated slash commands.
GATED_RE='^/scholar:(paper-idea|paper-draft|patent-scout|patent-claims|deepresearch|polish)\b'
printf '%s' "$PROMPT" | grep -Eq "$GATED_RE" || exit 0

CMD="$(printf '%s' "$PROMPT" | awk '{print $1; exit}')"
TODAY="$(date +%Y-%m-%d)"
PROJECT_YAML="$PROJECT_DIR/.evidraft/project.yaml"
SCOPE_DIR="$PROJECT_DIR/.evidraft/scope"

# --- Per-command default failure mode (overridden by project.yaml below).
# Writers (paper-draft / patent-claims / polish) emit publishable artefacts
# under manuscript/, so an unscoped run can corrupt material that ends up
# in a submission — default `block`. Analysis / retrieval commands
# (paper-idea / patent-scout / deepresearch) only write scratch under
# .evidraft/, so a missing scope is informational, not corrupting — default
# `warn`. The user can still flip either via project.yaml.hooks.scope_required.
case "$CMD" in
  /scholar:paper-draft|/scholar:patent-claims|/scholar:polish)
    DOWNGRADE="block" ;;
  /scholar:paper-idea|/scholar:patent-scout|/scholar:deepresearch)
    DOWNGRADE="warn" ;;
  *)
    DOWNGRADE="block" ;;  # safe default for any future gated command
esac
STALENESS_DAYS=14
if [ -f "$PROJECT_YAML" ]; then
  v="$(awk '
    /^hooks:[[:space:]]*$/ { in_hooks=1; next }
    in_hooks && /^[^[:space:]]/ { in_hooks=0 }
    in_hooks && /^[[:space:]]+scope_required:/ {
      sub(/^[[:space:]]+scope_required:[[:space:]]*/,"")
      sub(/[[:space:]]*#.*$/,""); gsub(/["'"'"']/,""); gsub(/[[:space:]]/,"")
      print; exit
    }' "$PROJECT_YAML" 2>/dev/null || true)"
  [ -n "$v" ] && DOWNGRADE="$v"

  d="$(awk '
    /^scope:[[:space:]]*$/ { in_scope=1; next }
    in_scope && /^[^[:space:]]/ { in_scope=0 }
    in_scope && /^[[:space:]]+staleness_days:/ {
      sub(/^[[:space:]]+staleness_days:[[:space:]]*/,"")
      sub(/[[:space:]]*#.*$/,""); gsub(/["'"'"']/,""); gsub(/[[:space:]]/,"")
      print; exit
    }' "$PROJECT_YAML" 2>/dev/null || true)"
  [ -n "$d" ] && STALENESS_DAYS="$d"
fi

# disabled → unconditionally pass. Audit-append happens at /scholar:paper-check.
[ "$DOWNGRADE" = "disabled" ] && exit 0

# --- Distinguish "project not initialised" from "project but no scope".
PROJECT_INIT=true
[ -f "$PROJECT_YAML" ] || PROJECT_INIT=false

# --- Pick the latest scope file: date-prefixed name (YYYY-MM-DD-*) first, then mtime.
LATEST=""
if [ -d "$SCOPE_DIR" ]; then
  cand="$(ls -1 "$SCOPE_DIR"/*.md 2>/dev/null \
          | grep -E '/[0-9]{4}-[0-9]{2}-[0-9]{2}-' \
          | sort -r | head -n1 || true)"
  if [ -z "$cand" ]; then
    cand="$(ls -1t "$SCOPE_DIR"/*.md 2>/dev/null | head -n1 || true)"
  fi
  LATEST="$cand"
fi

REASON=""
STATUS=""
APPROVED_DATE=""
STALENESS_UNTIL=""

if [ -z "$LATEST" ]; then
  REASON="missing"
else
  # Parse YAML frontmatter (enter on first `---`, exit on second).
  STATUS="$(awk '
    /^---[[:space:]]*$/ { if (!in_fm) { in_fm=1; next } else { exit } }
    in_fm && /^status:/ {
      sub(/^status:[[:space:]]*/,"")
      sub(/[[:space:]]*#.*$/,""); gsub(/["'"'"']/,""); gsub(/[[:space:]]/,"")
      print; exit
    }' "$LATEST" 2>/dev/null || true)"
  APPROVED_DATE="$(awk '
    /^---[[:space:]]*$/ { if (!in_fm) { in_fm=1; next } else { exit } }
    in_fm && /^approved_date:/ {
      sub(/^approved_date:[[:space:]]*/,"")
      sub(/[[:space:]]*#.*$/,""); gsub(/["'"'"']/,""); gsub(/[[:space:]]/,"")
      print; exit
    }' "$LATEST" 2>/dev/null || true)"

  if [ "$STATUS" != "approved" ]; then
    REASON="draft-only"
  elif [ -z "$APPROVED_DATE" ]; then
    REASON="stale"   # approved with no date → treat as stale per scope-required.md §Rules.3
  else
    # Compute staleness_until = approved_date + staleness_days (BSD then GNU date).
    until=""
    if until="$(date -j -v+"${STALENESS_DAYS}"d -f "%Y-%m-%d" "$APPROVED_DATE" "+%Y-%m-%d" 2>/dev/null)"; then
      :
    elif until="$(date -d "${APPROVED_DATE} + ${STALENESS_DAYS} days" "+%Y-%m-%d" 2>/dev/null)"; then
      :
    else
      until=""
    fi
    STALENESS_UNTIL="$until"
    # ISO-8601 dates compare lexicographically.
    if [ -n "$until" ] && [ "$TODAY" \> "$until" ]; then
      REASON="stale"
    fi
  fi
fi

# Pass.
[ -z "$REASON" ] && exit 0

# --- Build a copy-pasteable suggestion block keyed off the failure mode.
if [ "$PROJECT_INIT" = "false" ]; then
  SUGGEST="$(cat <<'EOS'
project not initialised — first run:
  /scholar:paper-init
then either:
  /scholar:brainstorming "<topic>"          # full path (~5 min)
  /scholar:using-deep-research "<topic>"    # fast path: scope-stub
EOS
)"
elif [ "$REASON" = "missing" ]; then
  SUGGEST="$(cat <<'EOS'
Full path (recommended):
  /scholar:brainstorming "<topic>"

Fast path (ad-hoc scope-stub):
  /scholar:using-deep-research "<topic>"
EOS
)"
elif [ "$REASON" = "draft-only" ]; then
  SUGGEST="$(cat <<EOS
the latest scope file is status: draft. Approve it:
  \$EDITOR "$LATEST"
set status: approved and approved_date: $TODAY in its frontmatter.
EOS
)"
else  # stale
  SUGGEST="$(cat <<EOS
the latest scope file is stale (approved $APPROVED_DATE, expires $STALENESS_UNTIL, today $TODAY). Either:
  /scholar:brainstorming "<topic>"          # re-scope
or refresh approved_date to $TODAY in:
  $LATEST
EOS
)"
fi

LATEST_DISPLAY="${LATEST:-(none)}"
LATEST_DISPLAY="${LATEST_DISPLAY#$PROJECT_DIR/}"
SUGGEST_INDENTED="$(printf '%s\n' "$SUGGEST" | sed 's/^/    /')"

MSG="$(cat <<EOS
scope-required: BLOCKED
  command: $CMD
  reason: $REASON
  detail:
    scope_dir: .evidraft/scope/
    latest_file: $LATEST_DISPLAY
    status: ${STATUS:-(missing)}
    approved_date: ${APPROVED_DATE:-(unset)}
    staleness_until: ${STALENESS_UNTIL:-(unset)}
    today: $TODAY
  suggestion: |
$SUGGEST_INDENTED
EOS
)"

if [ "$DOWNGRADE" = "warn" ]; then
  # warn mode passes; the audit-append to paper_check_report.md is owned by
  # /scholar:paper-check (the check report doesn't exist yet on most runs).
  printf '%s\n' "$MSG" >&2
  exit 0
fi

emit_block_decision "$MSG"
