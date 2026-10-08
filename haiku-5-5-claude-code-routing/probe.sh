#!/usr/bin/env bash
# Cheapest possible call: one Haiku turn answering "ok". Prints the current plan
# meter read from its rate_limit_event as one JSON line. The probe itself costs a
# few hundred tokens of Haiku (well under the 1% meter resolution).
# Usage: probe.sh [raw-stream-out-file]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/env.sh" ] && . "$HERE/env.sh"
RAW="${1:-$(mktemp -t hrb-probe)}"; case "$RAW" in /*) ;; *) RAW="$PWD/$RAW";; esac
cd "$(mktemp -d -t hrb-probe-cwd)"
claude --model claude-haiku-5-5 -p "ok" --max-turns 1 --output-format stream-json --verbose \
  --setting-sources project --strict-mcp-config > "$RAW" 2>/dev/null
"$HERE/.venv/bin/python" "$HERE/meter.py" "$RAW"
