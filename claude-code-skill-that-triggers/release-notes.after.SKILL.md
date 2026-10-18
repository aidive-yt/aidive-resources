---
name: release-notes
description: Writes this week's release notes from git log, grouped by scope (router, css, jsx). Use when the user asks what we shipped, what changed this week, for release notes, a changelog, or a summary of recent commits.
---

# Release notes

1. Find the range: commits since last Monday (`git log --since="last monday" --no-merges --pretty="%h %s"`).
2. Drop `chore` and `docs` commits.
3. Group what is left by the conventional-commit scope (router, css, jsx, serve-static...), fixes and features apart.
4. Write one line per change, in plain English, present tense, no commit hashes, with the PR number at the end.
5. Output a markdown block titled "Release notes, week of <date>", with a two-line summary on top.
