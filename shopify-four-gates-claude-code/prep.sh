#!/usr/bin/env bash
# Fresh work copy of upstream tinydb (git clean at HEAD) + the Stop hook settings for gated configs.
# Usage: prep.sh <cfg> <work dir> <run dir>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="$1"; W="$2"; RUN="$3"
rm -rf "$W"; mkdir -p "$(dirname "$W")"
cp -R "$HERE/upstream" "$W"
cd "$W"
/usr/bin/find . -name __pycache__ -type d -prune -exec rm -rf {} +
rm -f .coverage
# .claude/ is excluded locally (not committed, not in .gitignore): `git status` stays clean,
# the hook config never shows up in the diffs the reviewers and the scorer read.
echo ".claude/" >> .git/info/exclude
git update-index -q --refresh || true
if [ "$CFG" != "bare" ]; then
  # The settings command is a neutral wrapper: Claude Code prefixes every "Stop hook feedback" with the
  # hook's command line, so the SPEC command (GATE_RUN=... GATE_CONFIG=<cfg> bash <bench>/gate.sh) would
  # show the agent the config name and the bench path. The wrapper holds that exact command instead.
  mkdir -p .claude/hooks
  printf '#!/bin/bash\nGATE_RUN=%s GATE_CONFIG=%s bash %s/gate.sh\n' "$RUN" "$CFG" "$HERE" > .claude/hooks/stop.sh
  "$HERE/.venv/bin/python" - "$HERE" > .claude/settings.json <<'PY'
import json
import sys
bench = sys.argv[1]
cmd = 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/stop.sh"'
# Once a gate blocks, the agent hunts for the tests behind it (seen in a smoke: `cat .claude/hooks/stop.sh;
# find / -name test_T1.py`). The oracle and the gate tests live under the bench: deny the usual forms.
# Read rules cover Read/Grep/Glob; Bash rules match the command text (not a security boundary).
deny = ["Read(./.claude/**)", "Read(/%s/hidden/**)" % bench, "Read(/%s/runs/**)" % bench,
        "Read(/%s/validation/**)" % bench, "Read(/%s/reference/**)" % bench,
        "Read(//Users/thomas/dev/verify-loops-bench/**)", "Read(//Users/thomas/dev/haiku-routing-bench/**)",
        "Bash(*.claude/hooks*)", "Bash(*.claude/settings*)", "Bash(*gate-bench/hidden*)", "Bash(*../hidden*)",
        "Bash(*gate-bench/runs*)", "Bash(*../runs*)", "Bash(*gate_tests*)", "Bash(*gate-bench/reference*)",
        "Bash(*gate-bench/validation*)", "Bash(*verify-loops-bench*)", "Bash(*haiku-routing-bench*)", "Bash(find *)"]
print(json.dumps({"permissions": {"deny": deny},
                  "hooks": {"Stop": [{"hooks": [{"type": "command", "command": cmd, "timeout": 1500}]}]}}, indent=2))
PY
fi
test -z "$(git status --porcelain)" || { echo "work copy not clean"; git status --porcelain; exit 1; }
