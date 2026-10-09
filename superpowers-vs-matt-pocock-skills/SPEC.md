# flow-bench - Superpowers loop vs Matt Pocock's Main Flow, same feature, one repo

Question the video must answer: on one small invented repo, for one bounded brownfield feature,
what does each pack cost PER STAGE (tokens, wall-clock, USD) and what does it deliver (hidden
acceptance tests passed, repo suite green, diff size, bugs shipped), against a bare Claude Code run?
Secondary question: does stacking both packs in one project break (hook / slash conflicts)?

## Fixed decisions (2026-10-09)
- Worker model: `claude-sonnet-5-5`, headless (`claude -p`), OAuth from `~/.claude` (see traps below).
- The repo `upstream/`: INVENTED, built here, a small TypeScript project (about 12-20 source files,
  vitest, pnpm or npm, a green suite of ~25-40 tests): a plausible brownfield service, e.g. an
  invoicing API or a booking CLI with a store layer, a domain layer and an HTTP or CLI layer. It is a
  git repo with a clean history (3-6 commits), a short README and a `package.json` with
  `test` and `typecheck` scripts. No framework exotica; plain Node 20 + TS + vitest.
- ONE feature task `tasks/F1.md`: a terse developer request (headline ask + one or two constraints,
  2-4 lines, the way a dev types it), whose honest completion needs 5 requirements that a senior
  would expect (edge cases, a validation, a migration of existing data, an error path, a test).
  `hidden/test_F1.test.ts` is the oracle (5 requirement tests, never visible to the worker, run
  from OUTSIDE the work copy against it). `reference/F1.patch` passes all 5 and the repo suite.
- Configs (`configs.json`):
  - `bare`: no skills, no hooks.
  - `sp`: obra/superpowers installed in the PROJECT (not the user's plugin): clone the repo at the
    latest release tag (record it), expose its skills under `<work>/.claude/skills/` and its
    SessionStart hook + any hooks it ships under `<work>/.claude/settings.json` exactly the way the
    plugin wires them (read its `hooks/` and `plugin.json`; reproduce, don't improvise). Verify in a
    smoke run that the `using-superpowers` text actually appears in the session (stream-json shows
    the hook output) and that `brainstorming` is invoked.
  - `mp`: mattpocock/skills installed in the project via the official installer
    (`npx skills add mattpocock/skills` or the README's exact command, latest release, record the
    version); verify the Main Flow slash commands resolve (`/grill-with-docs`, `/to-spec`,
    `/to-tickets`, `/implement` or `/implement-spec`, `/code-review`, `/pr`, `/retro`; use the names
    the installed version really has).
  - `both`: `sp` + `mp` together (one or two runs only: the stacking question).
- Flows (the driver `run.sh <cfg> <rep>` / `lib/driver.py`):
  - `bare`: one session, the task prompt, "when done, stop and summarise".
  - `sp`: one session; turn 1 = the task prompt (the hook is supposed to route into brainstorming).
    Then the Superpowers loop as it unfolds (brainstorming → writing-plans → executing-plans →
    review); the driver only answers questions and says "go on / proceed with the plan" when the
    assistant ends a turn waiting. Record which skills were invoked and when (Skill tool events).
  - `mp`: one session, one stage per driver turn, in this order: `/grill-with-docs <task>` →
    `/to-spec` → `/to-tickets` → the implement stage (`/implement` or `/implement-spec`, whichever
    v1.3 ships for the loop over tickets) → `/code-review` → `/pr`. (`/retro` optional, one run.)
    The driver answers questions between turns.
  - Every turn is `claude -p … --resume <session_id> --output-format stream-json --verbose
    --include-hook-events`; the first turn creates the session. Per TURN: tokens in/out/cache
    read/cache write, USD (`result.total_cost_usd` deltas), wall-clock, tool calls, Skill
    invocations, files touched. Per STAGE: the sum of its turns. A "stage" for `sp` is the skill in
    force (from the Skill events), for `mp` the slash command of the turn.
  - **Product-owner simulator** (`lib/po.py`): both packs interrogate the user. A headless
    `claude-sonnet-5-5` with NO tools, `--setting-sources ""`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`,
    reads `po/F1-brief.md` (the full intent, the 5 requirements in plain words, preferences and
    constraints; never the tests) and answers the worker's questions tersely, as a busy dev would.
    When the worker ends a turn without a question, the PO replies "go on" (or the next slash
    command for `mp`). Hard caps: 12 driver turns per run, 60 `--max-turns` per claude turn, 40 min
    wall per run. A run that hits a cap is recorded as such, not discarded.
- Reps: 3 per config for `bare`, `sp`, `mp`; 1 for `both`. 10 runs. Parallel 2.
- Scoring (`lib/finalize.py`): hidden 0-5, repo suite pass/fail, typecheck pass/fail, `git diff
  --stat` lines added/removed, files touched, tests added, plus the per-stage table. `analyze.py`
  → `results.json` + `results.md` (per config: mean/median per metric; per stage: tokens, USD, wall).
- Validation BEFORE the matrix (`validate.sh`, logged): (1) `reference/F1.patch` → hidden 5/5 and
  suite green; (2) upstream unchanged → hidden 0/5 (or the honest number, recorded) and suite green;
  (3) one `bare` smoke run end to end with the PO loop exercised; (4) one `sp` smoke proving the
  hook fired and brainstorming ran; (5) one `mp` smoke proving `/grill-with-docs` resolved. A
  smoke run is tagged (`RUN_TAG=smoke`) and ignored by analyze.py.

## Traps already known (from a previous bench of the same kind)
- `claude -p --bare` cannot authenticate on an OAuth (Max plan) account: never use `--bare`. Use
  `--setting-sources project` for workers so the user's own plugins (Superpowers 6.4.1 is installed
  at user scope on this machine) never leak into a `bare` or `mp` run. VERIFY this isolation in the
  smoke: a `bare` run must show no Superpowers hook output and no Skill events.
- Scrub inherited `CLAUDE*` env vars (copy `env.sh` from the previous bench), set
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
- Fresh work copy per run at a unique path; `.claude/` excluded via `.git/info/exclude` so diffs
  stay about the feature.
- A worker may try to read the hidden tests: the hidden dir lives outside the work copy and the
  allow-list has no `find`/`ls` outside cwd.
- Allowed tools: Read,Edit,Write,MultiEdit,Glob,Grep,Skill,TodoWrite,Task,AskUserQuestion is NOT
  available headless (questions come as plain text; the driver detects a turn that ends on a
  question mark or an explicit "?"/options list and routes it to the PO); Bash limited to
  node/npm/pnpm/npx vitest/tsc/git status|diff|log|add|commit|checkout -b/ls/cat/mkdir/head/tail/
  grep/wc. Pocock's `/pr` wants `gh`: allow `Bash(gh:*)` but with no remote the PR step records
  its output text as the artefact (no network push).

## Deliverables
`README.md` (how to run, layout, every trap met), `SPEC.md` (this), `upstream/`, `tasks/F1.md`,
`po/F1-brief.md`, `hidden/`, `reference/`, `configs.json`, `env.sh`, `prep.sh`, `run.sh`,
`validate.sh`, `matrix.sh`, `lib/{driver.py,po.py,finalize.py}`, `analyze.py`, `validation.log`,
`runs/<cfg>-r<rep>/` (stream.jsonl per turn, stages.json, score.json), `results.json`,
`results.md`, and `FINDINGS.md`: the honest reading in 300 words, every number with its run name.
