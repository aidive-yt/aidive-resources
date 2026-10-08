#!/usr/bin/env bash
# Interactive demo of the gate for a screen recording: a gated tinydb work copy (config g13: acceptance
# tests, then two reviewers) with T1's acceptance tests already written. Usage: ./demo.sh [T1..T5]
# Then:  cd work/demo && claude --setting-sources project --permission-mode acceptEdits
# and paste the request printed below. When Claude stops, the Stop hook runs; a red acceptance test shows
# as "Stop hook feedback: ... The acceptance tests for this change fail:" and Claude keeps working.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; TASK="${1:-T1}"
. "$HERE/env.sh"
RUN="$HERE/runs/demo"; W="$HERE/work/demo"
rm -rf "$RUN"; mkdir -p "$RUN"
"$HERE/prep.sh" g13 "$W" "$RUN" > "$RUN/prep.txt" 2>&1
printf '{"task":"%s","cfg":"g13","rep":0,"work":"%s","name":"demo"}\n' "$TASK" "$W" > "$RUN/meta.json"
cp "$HERE/tasks/$TASK.md" "$RUN/task.md"
printf '%s\n\nWhen you are done, stop and summarise what you changed.\n' "$(cat "$HERE/tasks/$TASK.md")" > "$RUN/prompt.txt"
# Reuse the acceptance tests of a matrix run of the same task (no new writer call).
SRC=$(ls -d "$HERE"/runs/"$TASK"-g13-r1/gate_tests 2>/dev/null | head -1)
cp -R "$SRC" "$RUN/gate_tests"
echo "ready: cd $W && claude --setting-sources project --permission-mode acceptEdits"
echo "--- paste this request ---"; cat "$RUN/prompt.txt"
