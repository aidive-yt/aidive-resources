#!/bin/sh
# Block edits to the append-only migrations file
path=$(jq -r '.tool_input.file_path // empty')
case "$path" in
  *src/store/migrations.ts)
    echo "migrations.ts is append-only: add a new migration file instead" >&2
    exit 2 ;;
esac
exit 0
