#!/usr/bin/env bash
# session_key_contract_test.sh — pin _session_key() behaviour against a
# realistic Claude Code hook envelope.
#
# Why this exists: hooks/_lib.sh:_session_key() reads `.session_id` from the
# envelope JSON. If Claude Code ever renames the field, the function silently
# returns `pid-<PPID>` and the per-session state directory shifts, which
# breaks the per-command hook opt-out with NO visible error. This test pins
# the contract so a rename surfaces as a failed CI run rather than a silent
# regression.
#
# Runnable directly: `bash hooks/tests/session_key_contract_test.sh`.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="$HERE/../_lib.sh"

if [ ! -f "$LIB" ]; then
  printf 'FAIL cannot locate _lib.sh at %s\n' "$LIB"
  exit 1
fi

# Positive case: envelope with a session_id should round-trip through
# _session_key without taking the pid-<PPID> fallback. Run the source +
# call in a subshell so any `set -e` from _lib.sh doesn't infect the test.
POS_JSON='{"session_id":"abc123-test-session-xyz","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}'
POS_OUT="$(printf '%s' "$POS_JSON" | bash -c ". '$LIB' && read_stdin && _session_key" 2>/dev/null)"

if [ -z "$POS_OUT" ]; then
  printf 'FAIL positive case produced empty output\n'
  exit 1
fi

case "$POS_OUT" in
  pid-*)
    printf 'FAIL positive case fell back to pid-* fallback: %s\n' "$POS_OUT"
    exit 1
    ;;
esac

# fs-safe character set: alnum, underscore, hyphen only (matches the tr
# class inside _session_key itself).
if ! printf '%s' "$POS_OUT" | grep -Eq '^[A-Za-z0-9_-]+$'; then
  printf 'FAIL positive case contains non-fs-safe characters: %s\n' "$POS_OUT"
  exit 1
fi

# Negative case: envelope WITHOUT session_id must take the documented
# pid-<PPID> fallback so callers can detect "no session id" by prefix.
NEG_JSON='{"tool_name":"Write"}'
NEG_OUT="$(printf '%s' "$NEG_JSON" | bash -c ". '$LIB' && read_stdin && _session_key" 2>/dev/null)"

case "$NEG_OUT" in
  pid-*) ;;
  *)
    printf 'FAIL negative case did not take pid-* fallback: %s\n' "$NEG_OUT"
    exit 1
    ;;
esac

printf 'OK session_key_contract_test passed\n'
exit 0
