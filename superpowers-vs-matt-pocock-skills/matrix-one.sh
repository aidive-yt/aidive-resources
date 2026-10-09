#!/usr/bin/env bash
# One matrix cell (called by matrix.sh through xargs). Args: <cfg> <rep>
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
CFG="$1"; REP="$2"; export TASK="${3:-F1}"
PFX=""; [ "$TASK" != "F1" ] && PFX="$(echo "$TASK" | tr "A-Z" "a-z")-"
if [ "${SKIP_DONE:-0}" = 1 ] && [ -f "runs/${PFX}${CFG}-r${REP}/score.json" ]; then
  echo "$(date '+%F %T') skip ${PFX}${CFG}-r${REP}" >> matrix.log; exit 0
fi
echo "$(date '+%F %T') start ${PFX}${CFG}-r${REP}" >> matrix.log
line=$(./run.sh "$CFG" "$REP" < /dev/null 2>&1 | tail -1)
echo "$(date '+%F %T') $line" >> matrix.log
echo "$line"
