#!/usr/bin/env bash
# Usage: mcp-probe.sh <url> [tools/call json params]  -> initialize + notifications/initialized + tools/list (+ optional tools/call) over streamable HTTP
U="$1"; H=$(mktemp)
curl -s -D "$H" -m 30 -X POST "$U" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
echo; SID=$(grep -i '^mcp-session-id:' "$H" | tr -d '\r' | cut -d' ' -f2); echo "session-id: ${SID:-none}"
HS=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream'); [ -n "$SID" ] && HS+=(-H "Mcp-Session-Id: $SID")
curl -s -m 30 -X POST "$U" "${HS[@]}" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null
curl -s -m 30 -X POST "$U" "${HS[@]}" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'; echo
[ -n "${2:-}" ] && { curl -s -m 90 -X POST "$U" "${HS[@]}" -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":$2}"; echo; }
rm -f "$H"
