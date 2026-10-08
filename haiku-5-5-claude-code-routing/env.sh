# Sourced by run.sh and probe.sh.
# Auth: an isolated CLAUDE_CONFIG_DIR is not logged in
# (`claude auth status` -> loggedIn false), so runs use the user's default config dir:
# CLAUDE_CONFIG_DIR is deliberately left unset.
unset CLAUDE_CONFIG_DIR
# Fresh work copies at the same path must not inherit memory written by an earlier rep.
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
# The bench venv (pytest, ruff, mypy) comes first, so `python -m pytest` and `ruff` just work.
export PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.venv/bin:$PATH"
