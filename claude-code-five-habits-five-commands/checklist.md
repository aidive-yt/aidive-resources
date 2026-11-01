# Clear and skill-doctor checklist

After every finished task
1. Run `/context` and read what the session carries.
2. Run `/clear` before the next unrelated task.
3. Run `/context` again; the conversation should be near empty while instructions, tools and skills stay.
4. In the middle of a task, do not clear: use `/compact` with a focus instead.

Once a month
1. Run `/skill-doctor` (needs a recent Claude Code release).
2. Skills loaded but never invoked: turn them off in `/skills` (space bar cycles).
3. Skills synced from claude.ai: switch them off on the web side, deleting them locally brings them back.
4. Plugin skills: disable the plugin in the Installed tab.
5. Keep what you use rarely but still need.
