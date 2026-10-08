#!/usr/bin/env bash
# Build a fresh work copy for one task: upstream tinydb, baseline commit, task injection.
# Usage: prep.sh <task> <workdir>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TASK="$1"; W="$2"
read -r INJ MODE < <("$HERE/.venv/bin/python" -c "
import json,sys; t=json.load(open('$HERE/tasks.json'))['$TASK']; print(t['inject'] or '-', t['mode'] or '-')")
rm -rf "$W"; mkdir -p "$(dirname "$W")"
cp -R "$HERE/upstream" "$W"
cd "$W"
/usr/bin/find . -name __pycache__ -type d -prune -exec rm -rf {} +
rm -f .coverage
git update-index -q --refresh || true
G() { git -c user.email=dev@example.com -c user.name=dev "$@"; }
# Injections that belong to the baseline are folded into the top upstream commit
# (amend, same message/author/date), so `git log` shows no extra "bug" commit.
if [ "$MODE" = "commit" ]; then
  git apply "$HERE/$INJ"
  git add -A
  G commit -q --amend --no-edit --no-verify
fi
case "$MODE" in
  stage)    git apply --index "$HERE/$INJ" ;;
  worktree) git apply "$HERE/$INJ" ;;
esac
