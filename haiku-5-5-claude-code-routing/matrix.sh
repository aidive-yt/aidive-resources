#!/usr/bin/env bash
# Run an ordered list of "<config> <task> <rep>" lines SEQUENTIALLY (the plan meter is shared:
# never run two cells at once). Blank lines and #comments are skipped. Appends to matrix.log.
# Usage: matrix.sh [matrix-file]   (default: matrix.txt)
#   SKIP_DONE=1 matrix.sh ...      skip cells whose runs/<task>-<config>-r<rep>/score.json exists (resume)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
LIST="${1:-matrix.txt}"
# one matrix at a time: the meter is shared
mkdir "$HERE/.matrix.lock" 2>/dev/null || { echo "another matrix.sh is running (remove .matrix.lock if stale)" >&2; exit 1; }
trap 'rmdir "$HERE/.matrix.lock"' EXIT
echo "=== $(date '+%F %T') start $LIST" >> matrix.log
grep -vE '^\s*(#|$)' "$LIST" | while read -r CFG TASK REP; do
  if [ "${SKIP_DONE:-0}" = 1 ] && [ -f "runs/${TASK}-${CFG}-r${REP}/score.json" ]; then
    echo "$(date '+%F %T') skip ${TASK}-${CFG}-r${REP}" >> matrix.log; continue
  fi
  line=$(./run.sh "$CFG" "$TASK" "$REP" < /dev/null 2>&1 | tail -1)
  echo "$(date '+%F %T') $line" | tee -a matrix.log
done
echo "=== $(date '+%F %T') done $LIST" >> matrix.log
