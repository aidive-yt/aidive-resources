# The retro checklist

Run it after a session that went wrong, before you clear it, or later on the old session's log.

## The seven gestures

1. Install: `claude plugin marketplace update claude-plugins-official`, then `claude plugin install mattpocock-skills@claude-plugins-official --scope project`. Open a NEW session, type a slash, check that the retro command is listed.
2. Run your real task in a plain session. Let it finish. Keep the session open.
3. Run the retro in that session, then run it again with what failed written after it, as its argument. The retro reads the session log, and a session that never learned it failed will call itself smooth.
4. Trace every candidate. Type this, word for word:

   > For each candidate, quote the moment of this session's transcript that backs it; drop any candidate you cannot trace to a specific moment.

   Zero survivors is a valid retro. Weaker survivors are a judgement call: you decide.
5. Approve one survivor at a time, each into its carrier (below). One change per turn, read the diff after each.
6. Run the prompt audit WITH a path, apply its edits if any, then commit the files yourself. The retro proposes and edits, it does not commit.
7. Re-run the same task in a fresh session and watch what it reads first and whether the failure happens again.

## The four carriers

| What failed | Carrier | Example from our run |
| --- | --- | --- |
| A mechanical failure | A deterministic check: a pre-commit hook, a test, a lint rule, a CI job | `pre-commit.sh` (typecheck, then tests) and `numbering.test.ts` |
| A judgement call | One line in `CODING_STANDARDS.md`, read by the reviewer | `CODING_STANDARDS.md` |
| A navigation gap | A comment at the source, or one CLAUDE.md pointer if a comment cannot do it | A doc comment above `nextId` |
| Nothing the above can hold | Do not write a rule | Both retros declined a CLAUDE.md line |

## Traps

- Commit reminder: the retro can implement what you approve and then leave the files uncommitted. Stage the approved files and commit them yourself.
- A new hook checks the working tree, not the commit. If the tree still holds the bug, the hook refuses the commit. Fix the code first, then commit.
- A cherry-pick does not run the pre-commit hook.
- Prompt-audit path trap: `/doctor prompt-audit` with no path audited the user-level files under `~/.claude`, not the repo, and said nothing about the new files. Give it the path: `/doctor prompt-audit CODING_STANDARDS.md`.
- The retro has no dry-run mode. Try a proposed check against the repo before you let it block merges.
- Do not wire the retro to a session-end hook. Keep a human on the approval.
- Keep the transcript format out of your scripts: it is internal and changes between versions.
