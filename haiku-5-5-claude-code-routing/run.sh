#!/usr/bin/env bash
# One run: fresh tinydb work copy + task injection, headless claude -p, extract tokens/meter, check.
# Usage: run.sh <config> <task> <rep>
#   config: a key of configs.json (haiku-med | haiku-low | sonnet | opus)
#   task:   a key of tasks.json   (explore | tests | lint | commit | refactor | review | summary)
set -uo pipefail
CFG="$1"; TASK="$2"; REP="${3:-1}"
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
PY="$HERE/.venv/bin/python"
MAX_TURNS="${BENCH_MAX_TURNS:-40}"
NAME="${TASK}-${CFG}-r${REP}"
OUT="$HERE/runs/$NAME"; W="$HERE/work/$NAME"
rm -rf "$OUT"; mkdir -p "$OUT"
"$HERE/prep.sh" "$TASK" "$W" > "$OUT/prep.txt" 2>&1 || { echo "$NAME: prep failed"; cat "$OUT/prep.txt"; exit 2; }
( cd "$W" && git diff HEAD > "$OUT/pre.diff" )

# Config args (model pinned by full id, optional --effort)
CARGS=()
while IFS= read -r a; do CARGS+=("$a"); done < <("$PY" -c "
import json; [print(a) for a in json.load(open('$HERE/configs.json'))['$CFG']['args']]")
[ ${#CARGS[@]} -gt 0 ] || { echo "bad config $CFG" >&2; exit 2; }

# Fixed allow-list for every cell, including Bash(ruff:*) for the lint task.
TOOLS="Read,Edit,Write,MultiEdit,Glob,Grep,Skill,TodoWrite,Bash(uv:*),Bash(python:*),Bash(python3:*),Bash(pytest:*),Bash(ruff:*),Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(ls:*),Bash(cat:*),Bash(mkdir:*),Bash(mktemp:*),Bash(head:*),Bash(tail:*),Bash(grep:*),Bash(wc:*)"

cd "$W"
START=$(date +%s)
claude -p "$(cat "$HERE/tasks/$TASK.md")" "${CARGS[@]}" \
  --output-format stream-json --verbose --max-turns "$MAX_TURNS" \
  --permission-mode acceptEdits --allowedTools "$TOOLS" \
  --setting-sources project --strict-mcp-config \
  > "$OUT/stream.jsonl" 2> "$OUT/stderr.txt"
echo "$?" > "$OUT/exit_code.txt"
END=$(date +%s)
echo "$((END-START))" > "$OUT/wall_s.txt"

# After-meter: one cheap Haiku probe (its own stream is kept for audit).
"$HERE/probe.sh" "$OUT/probe.jsonl" > "$OUT/after.json" 2>/dev/null

# Diff of the agent's work (tracked + untracked) vs the post-injection state
# (index left untouched: the commit task's staged changes stay staged for the check)
git diff HEAD -- . ':(exclude).coverage' > "$OUT/post.diff"
git diff HEAD --numstat -- . ':(exclude).coverage' > "$OUT/numstat.txt"
git ls-files --others --exclude-standard | while IFS= read -r f; do
  git diff --no-index -- /dev/null "$f" >> "$OUT/post.diff"
  echo "$(wc -l < "$f" | tr -d ' ')	0	$f" >> "$OUT/numstat.txt"
done

"$PY" "$HERE/extract.py" "$OUT" "$CFG" "$TASK" "$REP" > "$OUT/result.json"
"$PY" "$HERE/check.py" "$TASK" "$W" "$OUT/result.json" > "$OUT/check.txt"; echo "$?" >> "$OUT/check.txt"
"$PY" "$HERE/extract.py" "$OUT" "$CFG" "$TASK" "$REP" --score
