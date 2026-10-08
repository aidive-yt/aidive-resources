# Sourced by run.sh, gate.sh and validate.sh.
# 1. Scrub every CLAUDE* variable inherited from a launching Claude Code session
#    (CLAUDE_EFFORT, CLAUDE_CODE_SUBAGENT_MODEL, CLAUDE_CODE_SESSION_ID, CLAUDECODE,
#    CLAUDE_CODE_CHILD_SESSION, ...): they would silently change the worker's effort,
#    subagent model and session bookkeeping.
for _v in $(env | sed -n 's/^\(CLAUDE[A-Za-z0-9_]*\)=.*/\1/p'); do unset "$_v"; done
unset _v
# 2. Auth: the user's default config dir (~/.claude, OAuth). See README traps (--bare cannot auth).
unset CLAUDE_CONFIG_DIR
# 3. Fresh work copies at the same path must not share auto-memory across reps.
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
# 4. No bytecode in the shared hidden/ dir when 3 runs execute hidden tests in parallel.
export PYTHONDONTWRITEBYTECODE=1
# 5. The bench venv first: `python -m pytest` inside the work copy uses it.
GATE_BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GATE_BENCH
export PATH="$GATE_BENCH/.venv/bin:$PATH"
