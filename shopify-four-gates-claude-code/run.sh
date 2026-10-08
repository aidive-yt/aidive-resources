#!/usr/bin/env bash
# One run: fresh work copy, headless Sonnet 5.5 worker, Stop hook per config, final scoring.
# Usage: run.sh <cfg> <task> <rep>      cfg: bare|g1|g3|g13|g13adv   task: T1..T5
#   RUN_TAG=x      -> runs/<task>-<cfg>-r<rep>-x (smoke runs stay out of the matrix)
#   INJECT=<patch> -> git apply it to the work copy before the worker starts (validation: red start state)
set -uo pipefail
CFG="$1"; TASK="$2"; REP="${3:-1}"
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
PY="$HERE/.venv/bin/python"
MAX_TURNS="${BENCH_MAX_TURNS:-60}"
NAME="${TASK}-${CFG}-r${REP}${RUN_TAG:+-$RUN_TAG}"
OUT="$HERE/runs/$NAME"; W="$HERE/work/$NAME"
rm -rf "$OUT"; mkdir -p "$OUT"
"$HERE/prep.sh" "$CFG" "$W" "$OUT" > "$OUT/prep.txt" 2>&1 || { echo "$NAME: prep failed"; cat "$OUT/prep.txt"; exit 2; }
if [ -n "${INJECT:-}" ]; then ( cd "$W" && git apply "$INJECT" ) || { echo "$NAME: inject failed"; exit 2; }; fi
cp "$HERE/tasks/$TASK.md" "$OUT/task.md"
printf '%s\n\nWhen you are done, stop and summarise what you changed.\n' "$(cat "$HERE/tasks/$TASK.md")" > "$OUT/prompt.txt"
printf '{"task":"%s","cfg":"%s","rep":%s,"work":"%s","name":"%s"}\n' "$TASK" "$CFG" "$REP" "$W" "$NAME" > "$OUT/meta.json"
# Gate 1 configs: the independent test writer runs BEFORE the worker (fixed per-run cost), sees only tasks/<T>.md,
# writes $OUT/gate_tests/test_<T>.py outside the work copy.
if "$PY" -c "import json,sys; sys.exit(0 if json.load(open('$HERE/configs.json'))['$CFG']['gate1'] else 1)"; then
  "$PY" "$HERE/lib/testwriter.py" "$TASK" "$OUT" > "$OUT/testwriter.out" 2>&1
fi
[ -f "$W/.claude/settings.json" ] && cp "$W/.claude/settings.json" "$OUT/settings.json" && cp "$W/.claude/hooks/stop.sh" "$OUT/stop.sh"

# Same allow-list as haiku-routing-bench/run.sh (verify-loops-bench's + Bash(ruff:*)).
TOOLS="Read,Edit,Write,MultiEdit,Glob,Grep,Skill,TodoWrite,Bash(uv:*),Bash(python:*),Bash(python3:*),Bash(pytest:*),Bash(ruff:*),Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(ls:*),Bash(cat:*),Bash(mkdir:*),Bash(mktemp:*),Bash(head:*),Bash(tail:*),Bash(grep:*),Bash(wc:*)"

cd "$W"
START=$(date +%s)
claude -p "$(cat "$OUT/prompt.txt")" --model claude-sonnet-5-5 \
  --output-format stream-json --verbose --include-hook-events --max-turns "$MAX_TURNS" \
  --permission-mode acceptEdits --allowedTools "$TOOLS" \
  --setting-sources project --strict-mcp-config \
  < /dev/null > "$OUT/stream.jsonl" 2> "$OUT/stderr.txt"
echo "$?" > "$OUT/exit_code.txt"
END=$(date +%s)
echo "$((END-START))" > "$OUT/wall_s.txt"

"$PY" "$HERE/lib/finalize.py" "$OUT"
