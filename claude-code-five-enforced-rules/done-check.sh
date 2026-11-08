#!/usr/bin/env bash
# Stop hook. Rule 4: done means the checks passed.
# Refuses the end of the turn while typecheck or tests are red, or while the test
# count dropped under the baseline (a suite made green by deleting tests is red).
set -u
INPUT=$(cat)
# Guard: when Claude Code is already continuing because of this hook, let it stop.
[ "$(printf '%s' "$INPUT" | jq -r '.stop_hook_active')" = "true" ] && exit 0
cd "$(printf '%s' "$INPUT" | jq -r '.cwd')" || exit 0
# Nothing changed since the last commit: nothing to check.
[ -z "$(git status --porcelain -- src test 2>/dev/null)" ] && exit 0
LOG=$(mktemp)
if ! pnpm --silent typecheck > "$LOG" 2>&1; then
  echo "Rule 4: typecheck fails. Not done yet." 1>&2; tail -30 "$LOG" 1>&2; rm -f "$LOG"; exit 2
fi
if ! pnpm --silent test > "$LOG" 2>&1; then
  echo "Rule 4: tests fail. Not done yet." 1>&2; grep -v '^\s*$' "$LOG" | tail -30 1>&2; rm -f "$LOG"; exit 2
fi
BASE=$(cat .claude/test-baseline 2>/dev/null || echo 0)
COUNT=$(grep -oE 'Tests +[0-9]+ passed' "$LOG" | grep -oE '[0-9]+' | head -1)
rm -f "$LOG"
if [ -n "$COUNT" ] && [ "$COUNT" -lt "$BASE" ]; then
  echo "Rule 4: $COUNT tests passed, the baseline is $BASE. A test disappeared; restore it." 1>&2; exit 2
fi
exit 0
