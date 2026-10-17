#!/usr/bin/env bash
# Source this file before you launch Claude Code: `source ultracode-caps.sh && claude`.
# These two lines are caps 2 and 3 of the five. Caps 1, 4 and 5 live in settings.json.

# Cap 2: at most 4 workflow agents run at once. The default is 16 (fewer on a machine
# with few CPUs). Accepted values are 1 to 256. Needs Claude Code v2.1.269 or later.
export CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS=4

# Cap 3: run every workflow agent on one cheaper model, while your other subagents
# keep theirs. Replace the placeholder with the full model id you want to pay for.
# Needs Claude Code v2.1.296 or later.
export CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL="<your-cheaper-model-id>"

# Optional kill switch for a shared machine: no workflows at all.
# export CLAUDE_CODE_DISABLE_WORKFLOWS=1
