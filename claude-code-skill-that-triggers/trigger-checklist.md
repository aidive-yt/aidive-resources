# Fresh-session trigger checklist

A skill that runs by name can still be invisible to a plain request. Test it the way a teammate will use it.

## Test in a fresh session

1. Open a new session. A skill already used stays in the conversation, so a test in the same session proves nothing.
2. Ask for the task in your own words, without the skill's name. Example: "what did we ship this week?"
3. Watch for the Skill tool call before Claude touches anything else. If Claude runs the commands itself and writes its own summary, the skill was skipped.
4. Repeat in several fresh sessions. A handful of runs is a demo, not a statistic.

## If it was skipped, read why before you edit

1. `/skills`: is it listed, is it switched on, is there a `user-only` badge? A `user-only` badge means Claude will not trigger it on its own.
2. Ask "What skills are available?" and check your skill is in the answer.
3. `claude --debug`, then search the log for the skills line (how many loaded) and for a "Skill listing over budget" warning. Over budget means some descriptions are cut, the least invoked first.
4. `claude plugin validate .claude/skills`: a malformed header still lets `/name` work but leaves Claude with empty metadata to match against.
5. Check the file is `.claude/skills/<name>/SKILL.md`, not a loose `<name>.md`, and that the header starts on the first line.

## Fix, then prove it

1. Rewrite the description with `description-template.md`.
2. Fresh session, same plain request, several runs: does the Skill call come first now?
3. Baseline: set the skill to `"off"` in `skillOverrides` (saved to `.claude/settings.local.json` from `/skills`), ask again, then switch it back on.

## Hold it

1. Write twenty requests: ten that should load the skill, ten near misses (`evals.json` is our set).
2. Run each in its own fresh session and note whether the skill loaded (`trigger_test.py`, `tally.py`).
3. Re-run the list every time you change the description.
4. For a skill that must never miss: call it by name, or add a UserPromptSubmit hook (`hook.json`).
