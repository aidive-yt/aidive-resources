#!/usr/bin/env bash
# One matrix cell (called by matrix.sh through xargs). Args: <cfg> <task> <rep>
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
CFG="$1"; TASK="$2"; REP="$3"
if [ "${SKIP_DONE:-0}" = 1 ] && [ -f "runs/${TASK}-${CFG}-r${REP}/score.json" ]; then
  echo "$(date '+%F %T') skip ${TASK}-${CFG}-r${REP}" >> matrix.log; exit 0
fi
echo "$(date '+%F %T') start ${TASK}-${CFG}-r${REP}" >> matrix.log
line=$(./run.sh "$CFG" "$TASK" "$REP" < /dev/null 2>&1 | tail -1)
echo "$(date '+%F %T') $line" >> matrix.log
echo "$line"
