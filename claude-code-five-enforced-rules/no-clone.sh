#!/usr/bin/env bash
# PostToolUse hook (matcher: Edit|Write). Rule 1: reuse before you write.
# Runs the copy-paste detector on src/ after every edit. A clone that was not
# there at the baseline blocks with the twin's location (exit 2 -> stderr reaches Claude).
set -u
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
case "$FILE" in *.ts) ;; *) exit 0 ;; esac
cd "$(printf '%s' "$INPUT" | jq -r '.cwd')" || exit 0
BASE=$(cat .claude/jscpd-baseline 2>/dev/null || echo 0)
OUT=$(mktemp -d)
npx --no-install jscpd src --min-lines 4 --min-tokens 30 --reporters json --output "$OUT" --silent >/dev/null 2>&1
COUNT=$(jq '.statistics.total.clones // 0' "$OUT/jscpd-report.json" 2>/dev/null || echo 0)
if [ "$COUNT" -gt "$BASE" ]; then
  echo "Rule 1 (reuse before you write): jscpd found $COUNT clone(s), baseline is $BASE. A helper you just wrote already exists:" 1>&2
  jq -r '.duplicates[] | "  \(.firstFile.name):\(.firstFile.start)-\(.firstFile.end)  ==  \(.secondFile.name):\(.secondFile.start)-\(.secondFile.end)"' "$OUT/jscpd-report.json" 1>&2
  echo "Import and reuse the existing one; do not keep both." 1>&2
  rm -rf "$OUT"; exit 2
fi
rm -rf "$OUT"; exit 0
