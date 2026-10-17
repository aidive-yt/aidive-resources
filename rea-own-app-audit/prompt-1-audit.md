We own aidive.dev and this repo is its source (the Next.js site in engine/site, the Cloudflare Worker in engine/site/worker). Audit what the SHIPPED site gives away to an outsider, with REA (Reverse Engineer Anything, github.com/morluto/rea). Install it only from the official npm package, rea-agents.

1. Install: npm i -g rea-agents@6.5.0, then rea setup --skill-client claude_code --yes --json, with REA_MCP_INPUT_SCHEMA_PROFILE=compact. If REA's MCP tools do not load in this session, use the rea CLI equivalent of each tool.
2. Start headless Chromium with --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir=/tmp/rea-chrome, and open https://aidive.dev/club/ then one free resource page under https://aidive.dev/club/free-resources/.
3. Run REA on those pages: list_browser_targets, inspect_web_page, analyze_web_bundle, capture_web_screenshot. Export the scripts to a new directory outside the repo.
4. Write audit/rea-before.md: one row per finding with its Evidence ID, what it is, whether it is an observation, an inference or an unknown, and how bad it would be. Do not open the source before this step is done: the report is what a stranger sees.
5. Only then read the source and add a column per finding: real leak, by design, or false positive, with the file it comes from.

Rules: never send a POST or any write request to aidive.dev (it is production and the form writes to a real mailing list). Change no app code in this chat yet. Note how long each step took at the end of the report. Commit audit/rea-before.md.
