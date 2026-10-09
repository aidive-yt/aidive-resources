#!/usr/bin/env bash
# One run: fresh work copy + pack fixtures, the driver (worker turns + PO), then finalize.
# Usage: [TASK=F1|F2] run.sh <cfg> <rep>        cfg: bare|sp|spd|mp|both
#   RUN_TAG=x -> runs/<name>-x (smoke runs; analyze.py ignores tagged runs)
# The work copy lives OUTSIDE the repo tree ($FLOW_BENCH_WORK, default /private/tmp/flow-bench/<name>): Claude Code
# loads every CLAUDE.md of the parent directories, so a work copy under this repo read the repo's CLAUDE.md (and the
# instructions it pulls in) in every session. After finalize the copy (without node_modules) is archived to work/<name>.
set -uo pipefail
CFG="$1"; REP="${2:-1}"
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
TASK="${TASK:-F1}"; export TASK
PFX=""; [ "$TASK" != "F1" ] && PFX="$(echo "$TASK" | tr "A-Z" "a-z")-"
NAME="${PFX}${CFG}-r${REP}${RUN_TAG:+-$RUN_TAG}"
WROOT="${FLOW_BENCH_WORK:-/private/tmp/flow-bench}"
OUT="$HERE/runs/$NAME"; W="$WROOT/$NAME"
rm -rf "$OUT"; mkdir -p "$OUT"
"$HERE/prep.sh" "$CFG" "$W" > "$OUT/prep.txt" 2>&1 || { echo "$NAME: prep failed"; cat "$OUT/prep.txt"; exit 2; }
BASE=$(tail -1 "$OUT/prep.txt")
cp "$W/.claude/settings.json" "$OUT/settings.json"
printf '{"task":"%s","cfg":"%s","rep":%s,"tag":"%s","work":"%s","name":"%s","base":"%s","started":"%s","claude_version":"%s"}\n' \
  "$TASK" "$CFG" "$REP" "${RUN_TAG:-}" "$W" "$NAME" "$BASE" "$(date '+%F %T')" "$(claude --version | head -1)" > "$OUT/meta.json"
python3 "$HERE/lib/driver.py" "$CFG" "$OUT" "$W" "$BASE" > "$OUT/driver.out" 2> "$OUT/driver.err"
python3 "$HERE/lib/finalize.py" "$OUT"
rm -rf "$HERE/work/$NAME"; mkdir -p "$HERE/work"
rsync -a --exclude node_modules "$W/" "$HERE/work/$NAME/"
