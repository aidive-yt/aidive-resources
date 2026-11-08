#!/usr/bin/env bash
# PreToolUse hook (matcher: Write). Rule 2: no module nobody asked for.
# Creating a file that does not exist yet under src/ becomes a permission prompt:
# the human says yes or no, the model does not decide alone.
set -u
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd')
case "$FILE" in "$CWD"/src/*) ;; *) exit 0 ;; esac
[ -e "$FILE" ] && exit 0
REL=${FILE#"$CWD"/}
jq -cn --arg r "Rule 2: new module under src/ ($REL). One new file needs a reason: approve only if the task asked for it, otherwise put the code in the module it belongs to." \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
