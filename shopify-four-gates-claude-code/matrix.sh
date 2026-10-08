#!/usr/bin/env bash
# Run an ordered list of "<cfg> <task> <rep>" lines, up to MATRIX_JOBS (default 3) at a time, each run in
# its own work copy. Blank lines and #comments skipped. Appends to matrix.log. Resumable: SKIP_DONE=1.
# Usage: nohup ./matrix.sh matrix.txt > matrix.nohup 2>&1 &
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
LIST="${1:-matrix.txt}"; JOBS="${MATRIX_JOBS:-3}"
mkdir "$HERE/.matrix.lock" 2>/dev/null || { echo "another matrix.sh is running (remove .matrix.lock if stale)" >&2; exit 1; }
trap 'rmdir "$HERE/.matrix.lock"' EXIT
echo "=== $(date '+%F %T') start $LIST jobs=$JOBS pid=$$" >> matrix.log
grep -vE '^[[:space:]]*(#|$)' "$LIST" | xargs -P "$JOBS" -L 1 ./matrix-one.sh
echo "=== $(date '+%F %T') done $LIST" >> matrix.log
