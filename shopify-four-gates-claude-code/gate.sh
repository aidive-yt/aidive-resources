#!/usr/bin/env bash
# Stop hook entry point (bash 3.2 OK). All logic lives in lib/hook.py.
# Called as: GATE_RUN=<abs run dir> GATE_CONFIG=<cfg> bash <bench>/gate.sh  (stdin = hook input JSON)
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$HERE/.venv/bin/python" -I "$HERE/lib/hook.py"
