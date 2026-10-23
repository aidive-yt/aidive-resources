#!/usr/bin/env bash
# Usage: run-session.sh <workdir> <out.json> <prompt> [resume-session-id]
# One headless Claude Code turn with an isolated project-only setup and an allow-list.
set -uo pipefail
W="$1"; OUT="$2"; PROMPT="$3"; SID="${4:-}"
source ./env.sh  # your own env: unset CLAUDE* variables, optionally CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
ALLOWED="Read,Edit,Write,MultiEdit,Glob,Grep,Skill,TodoWrite,Task,Agent,Bash(node:*),Bash(npm:*),Bash(pnpm:*),Bash(npx vitest:*),Bash(npx tsc:*),Bash(tsc:*),Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git add:*),Bash(git commit:*),Bash(git checkout -b:*),Bash(ls:*),Bash(cat:*),Bash(mkdir:*),Bash(head:*),Bash(tail:*),Bash(grep:*),Bash(wc:*),Bash(gh:*)"
DIS="AskUserQuestion,EnterPlanMode,ExitPlanMode,EnterWorktree,ExitWorktree,WebFetch,WebSearch"
ARGS=(-p "$PROMPT")
[ -n "$SID" ] && ARGS+=(--resume "$SID")
cd "$W" || exit 1
T0=$(date +%s)
claude "${ARGS[@]}" --model claude-sonnet-5-5 --permission-mode acceptEdits --output-format json \
  --allowedTools "$ALLOWED" --disallowedTools "$DIS" --setting-sources project --strict-mcp-config \
  > "$OUT" 2> "$OUT.stderr" < /dev/null
RC=$?
echo "rc=$RC wall=$(( $(date +%s) - T0 ))s" | tee "$OUT.wall"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print({k:d.get(k) for k in ('session_id','total_cost_usd','duration_ms','num_turns','is_error','subtype')})" "$OUT"
