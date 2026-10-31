# claude-alt: one-file jobs I can check in a glance
# plan: anything across files, or that I can't check by reading the diff
# always: read the diff before committing
alias claude-alt='CLAUDE_CODE_ATTRIBUTION_HEADER=0 ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY=ollama ANTHROPIC_BASE_URL=http://localhost:11434 claude --bare --model qwen3.5:9b'
