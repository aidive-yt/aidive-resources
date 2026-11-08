#!/bin/bash
# One fold-test run: run-one.sh <variant agent|skill> <task> <n>
# Copies ledgerly, sets up the variant, sends the same user prompt, scores the result.
set -u
V=$1; T=$2; N=$3
ROOT=/private/tmp/subagents-bench
W=$ROOT/eval/runs/$V-$T-$N
rm -rf "$W"; mkdir -p "$W"; cp -R "$ROOT/ledgerly/." "$W/"
cd "$W"
if [ "$V" = skill ]; then
  # Fold: the subagent's prompt becomes a skill in the main loop; the agent file moves aside
  mkdir -p .claude/skills/test-writer
  BODY=$(awk 'f>=2{print} /^---$/{f++}' .claude/agents/test-writer.md)
  { printf -- '---\nname: test-writer\ndescription: Write vitest tests for one module of this repo. Use when the user asks to add or improve tests for a file or module.\n---\n'; printf '%s\n' "$BODY"; } > .claude/skills/test-writer/SKILL.md
  git mv .claude/agents/test-writer.md .claude/test-writer.agent.md.aside
  git add -A .claude && git commit -qm "eval: fold test-writer into a skill"
fi
FILE=$(python3 -c "import sys;sys.path.insert(0,'$ROOT/eval');from mutations import MUTATIONS;print(MUTATIONS['$T'][0])")
START=$(date +%s)
claude -p "Add tests for $FILE." --model opus --setting-sources project,local \
  --output-format stream-json --verbose --permission-mode acceptEdits > run.jsonl 2> run.err
END=$(date +%s)
# Score
SRC_CHANGED=$(git status --porcelain -- src | wc -l | tr -d ' ')
npx vitest run > after.txt 2>&1 && GREEN=1 || GREEN=0
TESTS=$(grep -Eo 'Tests +[0-9]+ passed' after.txt | grep -Eo '[0-9]+' | head -1)
python3 - "$W" "$T" <<'PY'
import sys; sys.path.insert(0, "/private/tmp/subagents-bench/eval")
from mutations import MUTATIONS
w, t = sys.argv[1], sys.argv[2]; f, old, new = MUTATIONS[t]
p = f"{w}/{f}"; s = open(p).read(); open(p, "w").write(s.replace(old, new))
PY
npx vitest run > mutant.txt 2>&1 && KILLED=0 || KILLED=1
git checkout -q -- "$FILE"
python3 "$ROOT/eval/score.py" "$W" "$V" "$T" "$N" "$SRC_CHANGED" "$GREEN" "${TESTS:-0}" "$KILLED" "$((END-START))" >> "$ROOT/eval/results.jsonl"
tail -1 "$ROOT/eval/results.jsonl"
