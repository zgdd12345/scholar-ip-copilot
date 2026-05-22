#!/usr/bin/env bash
# citation-guard PostToolUse hook for scholar-ip (EviDraft).
# Blocks edits to manuscript/** or .evidraft/** that introduce strong-claim
# verbs without a nearby \cite{...} or ev_NNNN evidence id (~same-line window).
set -euo pipefail
. "$(dirname "$0")/_lib.sh"

read_stdin
# Per-command opt-out: if the currently active /scholar:<cmd> does not list
# `citation-guard` in its frontmatter `hooks:` allowlist (or declares `hooks:
# []`), skip the check entirely. This is the runtime side of the contract
# that lite-mode commands like /scholar:reading-list rely on.
if hook_disabled_by_command "citation-guard"; then
  exit 0
fi

# Need jq to find the edited file path inside the tool-call envelope; without
# it we cannot scope the check, so skip rather than block.
command -v jq >/dev/null 2>&1 || exit 0
FILE_PATH="$(stdin_jq_field '.tool_input.file_path')"
if [ -z "${FILE_PATH:-}" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Scope: only enforce on manuscript/** and .evidraft/** paths.
case "$FILE_PATH" in
  *manuscript/*|*.evidraft/*) ;;
  *) exit 0 ;;
esac

# Word-boundary regex via [^[:alnum:]_] because POSIX awk has no \b. The
# verb list is the canonical strong-claim set from docs/legal-and-ethics.md.
VERBS='(SOTA|state-of-the-art|novel|novelty|first|outperform|outperforms|outperformed|significant|significantly|superior|unprecedented|breakthrough)'
BOUNDED="(^|[^[:alnum:]_])${VERBS}([^[:alnum:]_]|$)"

OFFENDER=""
while IFS= read -r hit; do
  lineno="${hit%%:*}"
  text="${hit#*:}"
  # Within the same line (proxy for ~120 chars), require a \cite{...} or ev_NNNN.
  if ! printf '%s' "$text" | grep -Eq '\\cite[a-z]*\{[^}]+\}|ev_[0-9]{4}'; then
    OFFENDER="line $lineno: $text"
    break
  fi
done < <(grep -n -E "$BOUNDED" "$FILE_PATH" || true)

[ -z "$OFFENDER" ] && exit 0
emit_block_decision "citation-guard: strong-claim verb without nearby citation ($OFFENDER)"
