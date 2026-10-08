# gate-bench

What does each of Shopify's Helix gates catch when rebuilt as a Claude Code **Stop hook**, and what does it
cost? Headless Sonnet 5.5 workers implement five tinydb features (T1..T5); a Stop hook runs gate 1
(behaviour tests) and/or gate 3 (adversarial review by headless Sonnet 5.5 reviewers) every time the worker
tries to stop; hidden tests (the oracle, never visible to the agent) record the ground truth at every stop
and at the end. Built 2026-10-08 from `SPEC.md`; upstream, hidden tests, tasks and reference patches copied
from `../verify-loops-bench` (nothing there or in `../haiku-routing-bench` is modified).

## Commands (from this dir)

```bash
./validate.sh                         # steps 1,3,4 (+ step 2 once its run exists) -> validation.log
INJECT=$PWD/inject/break.patch RUN_TAG=val2 ./run.sh g1 T1 1     # validation step 2 (red start state)
RUN_TAG=smoke ./run.sh g13adv T1 1    # smoke (tagged runs are ignored by analyze.py)
./validate_writer.sh                  # gate-1 test writer on T1..T5: tests on upstream vs reference (REWRITE=1 to redo)
./gen_matrix.py                       # matrix.txt (50 runs, already generated)
nohup ./matrix.sh matrix.txt > matrix.nohup 2>&1 &          # 3 runs in parallel (MATRIX_JOBS=3)
SKIP_DONE=1 nohup ./matrix.sh matrix.txt > matrix.nohup 2>&1 &   # resume
.venv/bin/python analyze.py           # results.json + results.md
.venv/bin/python lib/finalize.py runs/<run>   # rescore one run from its work copy
.venv/bin/python lib/review.py work/<run> T1 adv   # one gate-3 round by hand
```
Single run: `./run.sh <cfg> <task> <rep>` -> `runs/<task>-<cfg>-r<rep>/`, work copy `work/<same name>/`.

## Layout

| path | what |
|---|---|
| `SPEC.md` | the spec this harness implements |
| `upstream/` | tinydb @ 18d73a1 (git repo) |
| `hidden/` | `test_T1..T6.py` (T6 unused), `conftest.py` (`$TINYDB_TREE` or cwd first on sys.path), `pytest.ini` |
| `tasks/T1..T5.md` + `tasks/README.md` | the task prompts (verbatim) and what each hidden req checks |
| `reference/T1..T5.patch` | reference solutions (validation step 1) |
| `inject/break.patch` | `>=` -> `>` in `Query.__ge__` (one repo test red; validation steps 2-3) |
| `inject/test_pushpull.py` | one thin test, makes the T1 reference copy "green with tests touched" (step 3) |
| `configs.json` | `bare` (no hook), `g1`, `g3` (indep), `g13` (g1 then g3 indep), `g13adv` (g1 then g3 adv) |
| `env.sh` | scrubs inherited `CLAUDE*` vars, default `~/.claude` auth, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, venv on PATH |
| `prep.sh <cfg> <work> <run>` | fresh copy of upstream, `.claude/` in `.git/info/exclude`, hook settings for gated configs |
| `run.sh <cfg> <task> <rep>` | one run (worker + hook + `lib/finalize.py`) |
| `gate.sh` | the Stop hook (bash 3.2 wrapper: `exec .venv/bin/python -I lib/hook.py`) |
| `lib/hook.py` | gate dispatch, snapshot, hidden run, gate 1, gate 3, decision, `gate.jsonl` line |
| `lib/review.py` | gate-3 reviewers (indep / adv), schemas, prompts, reason text; CLI for a manual round |
| `lib/testwriter.py` | gate-1 test writer (before the worker) + `run_gate_tests` (path rewritten to `acceptance/`) |
| `validate_writer.sh`, `validation/writer/<T>/` | writer validation files and their runs on upstream / reference |
| `tasks/` (terse prompts, used), `tasks-explicit/` + `runs-explicit/` | the matrix uses terse prompts; see `tasks/README.md` |
| `lib/common.py` | diff incl. untracked files, suite run, hidden run (requirement level) |
| `lib/finalize.py` | post-run diff/suite/hidden, `result.json`, `score.json` |
| `gen_matrix.py`, `matrix.txt`, `matrix.sh`, `matrix-one.sh`, `matrix.log` | 50-run matrix, 3 in parallel (xargs -P), resumable |
| `analyze.py` -> `results.json`, `results.md` | per config, per task, the five questions |
| `validate.sh`, `VALIDATION.md`, `validation.log` | pre-matrix checks |
| `.venv/` | python 3.14.7, pytest 9.1.1, pytest-cov 7.1.0, pyyaml, ruff 0.16.10 (same pins as haiku-routing-bench) |

### Worker (run.sh)
`claude -p "<T-file verbatim>\n\nWhen you are done, stop and summarise what you changed." --model claude-sonnet-5-5
--output-format stream-json --verbose --include-hook-events --max-turns 60 --permission-mode acceptEdits
--allowedTools <haiku-routing-bench list> --setting-sources project --strict-mcp-config`, cwd = `work/<run>/`, stdin /dev/null.
Gated configs get `work/<run>/.claude/settings.json`:
`{"permissions":{"deny":[...see traps...]},"hooks":{"Stop":[{"hooks":[{"type":"command","command":"bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/stop.sh\"","timeout":1500}]}]}}`
and `.claude/hooks/stop.sh` = `GATE_RUN=<abs run dir> GATE_CONFIG=<cfg> bash <bench>/gate.sh` (the SPEC command, one level down: see traps).
Copies of both land in the run dir (`settings.json`, `stop.sh`).

### Hook (lib/hook.py), one invocation
1. read stdin JSON; n = lines already in `gate.jsonl` + 1; blocks so far from the same file
2. `snap-<n>.diff` = `git diff HEAD` + untracked files (index never touched)
3. hidden tests on the work copy (`TINYDB_TREE` = work copy, cwd = work copy) -> `hidden-<n>.txt`; never shown to the agent
4. gate 1 (if configured) = the repo suite `python -m pytest -q -x --no-header -p no:cacheprovider --no-cov` (300 s)
   -> `gate1-<n>.txt` AND the writer's acceptance tests `runs/<run>/gate_tests/test_<T>.py` run with `TINYDB_TREE` = work
   copy -> `gatetests-<n>.txt`. Block when either is red. Reason: "The acceptance tests for this change fail:" + last 40
   lines (failing test names + assertion output, the gate_tests path rewritten to `acceptance/`), then the suite tail if the
   suite is red too; <= 1500 chars. `tests_touched` is still logged but no longer blocks. No writer file (writer failed
   twice) -> suite only, logged as `gate_tests_present: false`.
5. gate 3 (if configured and gate 1 passed or absent): see below
6. decision: allow / block / give_up (a would-be block when 6 blocks already happened -> allow, logged `give_up`).
   `stop_hook_active` is logged, never used. Block = exit 2 + reason on stderr. A crash of the hook itself is
   logged to `gate-errors.txt` and allows (counted as `gate_crashes` in score.json).

### Gate 1 test writer (lib/testwriter.py, run.sh before the worker, configs g1/g13/g13adv)
`claude -p` Sonnet 5.5 with the reviewer isolation flags, `--tools Read,Grep,Glob --max-turns 12 --json-schema
{"file": string}`, cwd = a pristine temp copy of upstream (deleted after). Prompt = framing + `tasks/<T>.md` + the
coordinator's instruction ("Write integration-style pytest cases for this request against the tinydb API, one test per
behaviour a careful senior would expect, pushing for edge cases beyond the happy path (missing fields, wrong types,
boundaries, persistence, cache, existing behaviour unchanged). Tests only, no implementation. Return the file content.")
+ mechanics (self-contained module, imports of the new API inside each test, MemoryStorage/tmp_path). The file must
compile and contain `def test_`, else one retry. Output `runs/<run>/gate_tests/` (+ hidden's conftest.py with
`TINYDB_TREE`, pytest.ini) and `testwriter.json` (cost, turns, attempts). Fixed per-run cost, outside the worker's wall.

### Gate 3 (lib/review.py)
Each reviewer: `claude -p "<prompt>" --model claude-sonnet-5-5 --tools Read,Grep,Glob --max-turns 15 --output-format json
--json-schema <schema> --permission-mode dontAsk --setting-sources "" --settings '{"disableAllHooks":true}' --strict-mcp-config`
with `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, all inherited `CLAUDE*` vars dropped, cwd = work copy,
600 s timeout. Prompt = framing + task prompt (T-file) + diff (tracked + untracked, cap 60k chars) + the SPEC's "Find defects..."
sentence. `structured_output` is read from the JSON result; `total_cost_usd`, `num_turns`, wall and models are recorded.
- `indep`: reviewers A and B, same prompt, run in parallel, no shared context. Blocking findings = union. Pass when both approve.
- `adv`: A as above; challenger B gets A's numbered findings + the diff, answers `upheld|rejected` + reason per id, may add
  findings (`added_findings`). Blocking = A's blocking findings B upheld + B's added blocking findings. B always runs (same
  2-call budget as indep).
- Effective `approve` = "no blocking finding" (the raw `approve` is logged as `approve_raw`; a reviewer saying approve=false with
  only minor findings does not block). A reviewer call that errors approves (fail open) with `error` recorded; an errored
  challenger upholds nothing.
- Reason = "Code review found N blocking defect(s):" + numbered `file:line text` + "Fix every finding, re-run the tests, then stop.", <= 1500 chars.

### Per run (`runs/<task>-<cfg>-r<rep>/`)
`stream.jsonl`, `stderr.txt`, `exit_code.txt`, `wall_s.txt` (includes hook time: the hook runs inside the session),
`gate.jsonl`, `snap-<n>.diff`, `hidden-<n>.txt`, `gate1-<n>.txt`, `hook-input-1.json`, `post.diff`, `numstat.txt`,
`suite.txt` (full suite, no -x), `hidden.txt`, `gate_tests/`, `testwriter.json`, `gatetests-<n>.txt`, `gatetests-final.txt`, `result.json`, `score.json`, `meta.json`, `task.md`, `prompt.txt`,
`settings.json` + `stop.sh` (gated configs).
`score.json`: task, cfg, rep, hidden_pass/hidden_fail/failed_reqs (**requirement level**: 5 reqs per task), suite_pass/fail,
hook_calls, blocks_total, blocks_by_gate {g1,g3}, right_blocks / false_blocks (+ `_by_gate`), give_up, ended_blocked,
cost_worker_usd, cost_reviewers_usd, cost_testwriter_usd, cost_total_usd (all three), testwriter_ok, gate_tests_total,
gate_tests_fail_final, turns, wall_s, reviewer_findings_total, reviewer_errors, gate_crashes,
model_ok (worker init model + every modelUsage key + every reviewer model == claude-sonnet-5-5), hook_events_in_stream,
hidden_first_stop.

## Matrix
5 tasks x 5 configs x 2 reps = 50 runs. Rep 1 config blocks bare, g1, g3, g13, g13adv (tasks rotated per block), rep 2 the
reverse block order. Up to 3 runs at once, each in its own work copy (`matrix-one.sh` via `xargs -P 3`, bash 3.2 has no
`wait -n`). `matrix.log`: one `start` and one result line per run.

## Traps found
- **Gate 1 as first built passed by construction** (it only re-ran the implementer's own tests: `T2-g1-r1` one allow, hidden
  R4 missed). Redesigned around an independent test writer (above). The writer hedges where the terse prompt is silent
  (accepts "raises or no-op"), so it cannot recover unstated requirements; per-task overlap is in VALIDATION.md.
- **A blocked agent hunts for the tests.** After a gate-1 block the smoke agent ran `cat .claude/hooks/stop.sh; find / -name
  test_T1.py` (denied only because `find` is not on the allow-list; `cat` is, and `stop.sh` names the bench dir, from where
  `hidden/` is one `cat` away). Gated configs' `.claude/settings.json` now carries `permissions.deny`: Read of `./.claude/**`,
  the bench's `hidden/ runs/ validation/ reference/`, the two sibling benches; Bash patterns containing `.claude/hooks`,
  `.claude/settings`, `../hidden`, `../runs`, `gate_tests`, the bench sub-paths, `find *`. Probed with a Haiku session: all
  five escape attempts (cat, Read, ls, python open) denied, in-tree reads fine. Bash rules match command text, not a security
  boundary. Bare runs have no settings file (bare r1 ran before this change; bare has no motive to hunt).
  Reviewers and the writer run with `--setting-sources ""`, so these rules do not apply to them.
- **Transient `FileNotFoundError` spawning a reviewer** inside the hook (once, both reviewers of one call, wall 0.0 s;
  never reproduced by hand). Reviewer calls now retry once after 3 s; the error message records `filename`.
- **`--bare` cannot authenticate here.** It reads `ANTHROPIC_API_KEY` / `apiKeyHelper` only, never OAuth or the keychain;
  this account is OAuth (`~/.claude`), so a `--bare` reviewer returns `terminal_reason: api_error`, cost 0. Used the
  documented equivalents instead: `--setting-sources ""` + `--settings '{"disableAllHooks":true}'` + `--strict-mcp-config` +
  `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` + `--tools Read,Grep,Glob`. The reviewers' cwd is the
  work copy, whose `.claude/settings.json` carries the Stop hook: without `--setting-sources ""`/`disableAllHooks` a reviewer
  would run the gate recursively. Verified: a dummy Stop hook in the probe copy never fired.
- **Inherited session env.** A matrix launched from inside Claude Code inherits `CLAUDE_EFFORT=medium`,
  `CLAUDE_CODE_SUBAGENT_MODEL=opus`, `CLAUDE_CODE_SESSION_ID`, `CLAUDECODE`, `CLAUDE_CODE_CHILD_SESSION`, messaging tokens.
  `env.sh` unsets every `CLAUDE*` var before setting its own; reviewers get a scrubbed env too (the hook process itself
  inherits the worker's `CLAUDE_*` vars, e.g. the worker's session id).
- **The feedback line leaks the hook command.** Claude Code prefixes each block with the command line:
  `Stop hook feedback:\n[<command>]: <reason>`. With the SPEC command inline the agent would read `GATE_CONFIG=g13adv` and
  `gate-bench/gate.sh`. The settings command is therefore `bash "$CLAUDE_PROJECT_DIR/.claude/hooks/stop.sh"`, a one-line
  wrapper holding the SPEC command. The agent can still `cat` it (it lives in the work copy) but it is not pushed at it.
- **Stop hook input keys (2.1.293):** `background_tasks, cwd, effort ({"level":"medium"}), hook_event_name,
  last_assistant_message, permission_mode, prompt_id, session_crons, session_id, stop_hook_active, transcript_path`.
- **8-cap resets on tool calls.** Per the docs the consecutive-continuation count resets each time Claude calls a tool, so the
  built-in cap only bites an agent that answers blocks with text alone. Our give-up (6 blocks per run, counted from
  `gate.jsonl`, tool calls or not) fires first in every case.
- **Red start state: the agent refuses to fix code it did not write.** Validation step 2 (T1 + an uncommitted `>=` -> `>`
  edit) shows Sonnet 5.5 implementing T1, then answering 6 consecutive gate-1 blocks with "the red test is your pre-existing
  uncommitted edit, not my change" without touching it, until give_up. The hook mechanics are validated; the behaviour is a
  finding in itself (gate 1 cannot force a fix the agent considers out of scope).
- **pytest-cov.** The repo's `pytest.ini` adds `--cov tinydb`; gate 1 adds `--no-cov` so the 40-line tail holds the failure,
  not the coverage table (and no `.coverage` file is written). `.coverage` is gitignored anyway.
- **T5 R4 is parametrized** (several test ids, one requirement). hidden counts are per requirement (5 per task), a req
  passes only when all its ids pass. `validate.sh` step 1: T5 upstream passes 1 req (R3, the regression guard) as designed.
- **Diff without touching the index.** `git add -N` would change what the agent sees in `git status`; untracked files are
  diffed with `git diff --no-index /dev/null <f>` instead. `.claude/` is in `.git/info/exclude`, so the hook config never
  shows in any diff or in `git status`.
- **Worker Bash denials.** The 2.1.293 permission layer denies some agent commands with "Contains brace with quote character
  (expansion obfuscation)" even under acceptEdits + allow-list; agents route around it (visible as `permission_denied` events).
- **Reviewers on a correct solution still flag "blocking".** On the T1 reference patch, reviewer A marked "pull does not check
  the field is a list" (not required by the task) as blocking; indep therefore blocks, the adv challenger rejected it. This is
  exactly what false_blocks measures (hidden all green at that stop).
- **Shared plan meter.** Workers and reviewers bill the user's plan quota; `total_cost_usd` is the list-price equivalent the
  CLI reports, not a bill. Nothing else heavy should run on the account during the matrix.
- **rtk rewrites interactive `grep`/`diff`** in the launching Claude session only; scripts here call binaries directly
  (`/usr/bin/diff`/`cmp` for verification diffs).
- **CLI version:** `claude --version` = 2.1.293 (Claude Code); flags checked in `claude --help`: `--json-schema`, `--bare`, `--tools`,
  `--permission-mode` (choices acceptEdits, auto, bypassPermissions, manual, dontAsk, plan), `--setting-sources`,
  `--include-hook-events`. `--max-turns` is accepted though not listed in `--help`.

## Matrix launch (2026-10-08 16:33:54, after the gate-1 redesign)
`cd /Users/thomas/dev/gate-bench && SKIP_DONE=1 nohup ./matrix.sh matrix.txt > matrix.nohup 2>&1 &` -> PID 71317, 3 lanes.
The 5 bare r1 runs (terse prompts) are kept and skipped; 45 runs to go. Expected wall ~40-70 min: gated runs so far take
~30-70 s of worker wall + ~35-40 s of test writer (before the worker) + 1-35 s per hook call, more with blocks.
Then `.venv/bin/python analyze.py`.
