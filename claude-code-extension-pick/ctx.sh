#!/usr/bin/env bash
# Usage: ctx.sh <step>  -> runs "/context" through run-session.sh, writes context-<step>.txt (honours STRICT_MCP / EXTRA_ALLOW)
C="$(cd "$(dirname "$0")" && pwd)"
"$C/run-session.sh" "$C/out/context-$1.json" "/context" >/dev/null
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['result'])" "$C/out/context-$1.json" > "$C/context-$1.txt"
grep -E '^\*\*Tokens|^\| (System prompt|System tools|MCP tools|Memory files|Skills|Custom agents|Messages) ' "$C/context-$1.txt"
