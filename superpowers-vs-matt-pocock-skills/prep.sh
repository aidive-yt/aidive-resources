#!/usr/bin/env bash
# Fresh work copy of upstream (node_modules included) + the pack fixtures of <cfg>.
# Usage: prep.sh <cfg> <work dir>      Prints the base commit (the oracle's BASE) on its last line.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="$1"; W="$2"
SP=$(python3 -c "import json;print(int(json.load(open('$HERE/configs.json'))['$CFG']['superpowers']))")
MP=$(python3 -c "import json;print(int(json.load(open('$HERE/configs.json'))['$CFG']['mattpocock']))")
rm -rf "$W"; mkdir -p "$(dirname "$W")"
cp -R "$HERE/upstream" "$W"
cd "$W"
# .claude/ never shows in git status or in any diff (hook config, installed skills).
echo ".claude/" >> .git/info/exclude
mkdir -p .claude/skills

if [ "$MP" = 1 ]; then
  cp -R "$HERE/packs/mattpocock-skills/.claude/skills/." .claude/skills/
  # One-time per-repo precondition of the pack (/setup-matt-pocock-skills), answered once with the defaults it
  # recommends for a repo with no remote: local-markdown tracker, single-context domain docs, no triage labels
  # (triage is installed, so Section B would ask; default labels kept). Committed so it never shows in the diff.
  S="$HERE/packs/mattpocock-skills/.claude/skills/setup-matt-pocock-skills"
  mkdir -p docs/agents
  cp "$S/issue-tracker-local.md" docs/agents/issue-tracker.md
  cp "$S/domain.md" docs/agents/domain.md
  cp "$S/triage-labels.md" docs/agents/triage-labels.md
  cat > CLAUDE.md <<'MD'
## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
MD
  git add CLAUDE.md docs/agents
  GIT_AUTHOR_DATE="2026-03-09T18:00:00" GIT_COMMITTER_DATE="2026-03-09T18:00:00" \
    git -c user.name="Dana Whitfield" -c user.email="dana@ledgerly.dev" commit -q -m "chore: configure agent skills (local tracker)"
fi

if [ "$SP" = 1 ]; then
  # The plugin root as Claude Code would hold it, so the hook script finds ../skills/using-superpowers.
  mkdir -p .claude/plugins
  cp -R "$HERE/packs/superpowers" .claude/plugins/superpowers
  cp -R "$HERE/packs/superpowers/skills/." .claude/skills/
fi

python3 - "$HERE" "$SP" "$CFG" > .claude/settings.json <<'PY'
import json, sys
bench, sp, cfg = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
# Oracle, reference, PO brief, other runs: denied by path (Read/Grep/Glob) and by command text (Bash).
deny = ["Read(/%s/hidden/**)" % bench, "Read(/%s/reference/**)" % bench, "Read(/%s/runs/**)" % bench,
        "Read(/%s/po/**)" % bench, "Read(/%s/validation/**)" % bench,
        "Bash(*hidden*)", "Bash(*reference/F*)", "Bash(*-brief.md*)", "Bash(*/runs/*)", "Bash(*../*)", "Bash(find *)"]
if cfg == "spd":
    # executing-plans runs its sibling scripts as ../subagent-driven-development/scripts/...: a "../" deny would block the
    # pack's own loop. The oracle stays protected by the Read denies and Bash(*hidden*).
    deny.remove("Bash(*../*)")
settings = {"permissions": {"deny": deny}}
if sp:
    # = packs/superpowers/hooks/hooks.json, with ${CLAUDE_PLUGIN_ROOT} provided the way the plugin loader provides it
    # (the script also picks its JSON output shape from CLAUDE_PLUGIN_ROOT being set).
    root = '$CLAUDE_PROJECT_DIR/.claude/plugins/superpowers'
    hooks = json.load(open("%s/packs/superpowers/hooks/hooks.json" % bench))["hooks"]
    for groups in hooks.values():
        for g in groups:
            for h in g["hooks"]:
                h["command"] = 'CLAUDE_PLUGIN_ROOT="%s" %s' % (root, h["command"].replace("${CLAUDE_PLUGIN_ROOT}", root))
    settings["hooks"] = hooks
print(json.dumps(settings, indent=2))
PY
[ "$(ls .claude/skills | wc -l)" -eq 0 ] && rmdir .claude/skills
test -z "$(git status --porcelain)" || { echo "work copy not clean"; git status --porcelain; exit 1; }
git rev-parse HEAD
