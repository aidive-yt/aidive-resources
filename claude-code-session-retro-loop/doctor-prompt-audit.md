# `/doctor prompt-audit` (no path) on the ledgerly copy, session 26612b59-9edd-493b-a397-fb54300fa037

# Prompt audit: Claude Code configuration for ledgerly

**Assumptions**
- **Target model:** Claude Sonnet 5.5, the model running this session. A skill that writes prompts for other models (`prompt-master`) is audited for its Claude-facing text only.
- **Scope:** only the Claude Code configuration that loads into this project, as you specified. I proposed no edits to plugin files.
- **Settings and secrets:** I did not read `.claude/settings.json`, `.mcp.json` or `~/.claude.json`.
- **Edits are not applied.** Every edit below touches `~/.claude/`, so it **affects all projects**.
- **Dependency not verified:** I could not verify that `~/.claude` is under git, so I used no `git blame`. No hunk below relies on history.

**Inventory**
- **Project files:** none. The project root has no `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` or `.claude/` instruction files. The ancestors `/path/to/work` and `/private/tmp` have none either.
- **Managed policy:** no managed-policy `CLAUDE.md` exists.
- **User level:**
  - `~/.claude/CLAUDE.md`, which imports `~/.claude/RTK.md`.
  - `~/.claude/rules/context7.md`.
  - 27 skills under `~/.claude/skills/*/SKILL.md`.
  - There are no `commands/`, `agents/` or `output-styles/` folders.
- **Plugins:** `caveman`, `marketing`, `cowork-plugin-management` and `gleam-reels` are installed. I did not audit them in depth, and they have no findings or edits.
- **Coverage gap:** I read `CLAUDE.md`, `RTK.md`, the rule, `context7-mcp`, most of `prompt-master`, the relevant parts of `graphify`, and the top of `agent-reach`. I covered the other skills (Cloudflare, HyperFrames, browser, media) with signal greps and frontmatter only. I did not read their `references/` subfiles.
- **Possible mismatch:** this session's skill list shows none of the `~/.claude/skills/*` entries. These files may not be loading in this project, so the skill findings may not affect it.


## Findings of the first run

The audit without a path found no project instruction files and went on to audit the user-level files under the home folder instead: six proposed edits and four flags, all about files outside this repository, none applied. That part is left out of this copy because it concerns one developer's personal configuration, not the project.

# Second run: `/doctor prompt-audit CODING_STANDARDS.md` (session 9b5f0cd5-1701-498e-8d05-0355c7f1ece6)

## Prompt audit: `CODING_STANDARDS.md`

**Assumptions**
- **Scope:** only `CODING_STANDARDS.md`, which the request names. The inventory found no `CLAUDE.md`, `AGENTS.md`, rule files, skills, commands or subagents in the repo. `.claude/settings.json` exists but I did not read it, per the audit rules.
- **Target model:** Claude Sonnet 5.5, the model running this audit. The file is read by the coding agent, not by application code.
- **Group 4 (request config and architecture):** not applicable. The file is an agent instruction file and has no request-building code.

**Result: the file is clean.** It has one line, so there is nothing to change and the proposed diff is empty.

**Inventory:** `CODING_STANDARDS.md` has one rule at line 3: "Take a sequence number (`nextId`) only once every validation has passed, so a rejected request leaves the sequence gapless."

**Checks**

| Group | Findings |
|---|---|
| 1 Dated prompt text | 0. The rule has no emphasis, hedging, scaffold or step list. It states a reason, so it is context the model can't know, not a prohibition without provenance. |
| 2 Brittle config files | 0. `git blame` puts the line in `adaa593`, the retro commit that followed the credit-note session. It encodes a failure that actually happened, not a one-off stumble. |
| 3 Tool descriptions | Not applicable. |
| 4 Request config and architecture | Not applicable. |

Group 2 also covers stale facts. `nextId` is still defined (`src/store/json-store.ts:11,52`) and the sequence kinds it names still exist. No other instruction file ranks on the same point, so there is no conflict.

**One thing outside the audit:** the rule is violated in the code. `src/http/handlers/invoices.ts:44` calls `ctx.store.nextId("invoiceNumber")` before `issue()` runs. `issue()` throws `ConflictError` for any non-draft invoice (`src/domain/invoice.ts:42-44`). Issuing an already-issued, paid or void invoice therefore consumes an invoice number and leaves a gap. The fix is to validate first, or to pass an allocator into `issue()` the way `createCreditNote` takes `allocate`. I didn't check `customers.ts:8` or `credit-note.ts`.

This is a code bug, not a prompt problem, and the rule is working as intended. Keep it, and consider an enforcing test: `test/numbering.test.ts` may only cover credit notes. I haven't edited anything.
