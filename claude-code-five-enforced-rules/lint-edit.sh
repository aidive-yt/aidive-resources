#!/usr/bin/env bash
# PostToolUse hook (matcher: Edit|Write). Rule 3: conventions are lint, not prose.
# Runs ESLint on the file that was just edited; a violation is a lint error at the
# exact line, every edit (exit 2 -> stderr reaches Claude). Lint only, never --fix.
set -u
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
case "$FILE" in *.ts) ;; *) exit 0 ;; esac
cd "$(printf '%s' "$INPUT" | jq -r '.cwd')" || exit 0
if ! npx --no-install eslint --no-warn-ignored "$FILE" 1>&2; then
  echo "Rule 3: the conventions above are enforced by eslint.config.js; fix the file, do not change the config." 1>&2
  exit 2
fi
exit 0
