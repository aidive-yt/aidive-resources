# Validation (2026-10-08, claude 2.1.293) — raw output in validation.log

1. **Oracle.** `./validate.sh step1`: on upstream every hidden req fails (T5: 1 passing, R3 = regression guard, as designed);
   each reference patch passes its hidden file (T1-T4 5 tests, T5 6 tests = 5 reqs) and the repo's 226 tests. OK.
2. **Hook fires.** `INJECT=$PWD/inject/break.patch RUN_TAG=val2 ./run.sh g1 T1 1` (T1 + an uncommitted `>=` -> `>` break):
   gate.jsonl = 7 calls, 6 `block` (g1, suite red 1 failed / 33 passed under -x) then `give_up`; the stream shows
   `Stop hook feedback:` user messages followed by new assistant turns (the agent continued each time; it kept
   explaining the red test is the user's pre-existing edit and never touched it). `stop_hook_active` false on call 1, true after. OK.
3. **gate.sh by hand** (`./validate.sh step3`, fake stdin): green copy (T1 reference + one new test) -> exit 0, `allow`,
   empty stderr; red copy (break.patch) -> exit 2, `block`, stderr = pytest tail incl. `short test summary info`. OK.
4. **Reviewer by hand** (`./validate.sh step4`, `lib/review.py work/_val3-green T1 indep|adv`): every call returned a
   schema-valid `structured_output`, cost $0.03-0.05 per pair, 10-45 s per call. OK.
5. **Recorded.** `claude --version` 2.1.293. settings.json (gated configs):
   `{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/stop.sh\"","timeout":1500}]}]}}`,
   `.claude/hooks/stop.sh` = `GATE_RUN=<run dir> GATE_CONFIG=<cfg> bash /Users/thomas/dev/gate-bench/gate.sh`.
   Hook input keys seen: background_tasks, cwd, effort, hook_event_name, last_assistant_message, permission_mode, prompt_id,
   session_crons, session_id, stop_hook_active, transcript_path. Stream hook events in the smoke run: exactly one
   `hook_started`/`hook_response` pair, `hook_name: Stop` (no user/global hooks: `--setting-sources project`).

Smoke (`runs/T1-g13adv-r1-smoke`, wrapper hook): hidden 5/5, suite 238/238, 1 hook call, gate 1 green with tests touched,
adv reviewer A approve (0 findings), challenger approve, allow. Worker $0.084 + reviewers $0.034 = $0.117, 12 turns, 66 s.
`runs/T1-g13adv-r1-smoke0` = the first smoke with the inline SPEC command (same outcome, $0.195, 69 s), superseded because the
feedback prefix would leak the command line.

## Gate 1 redesign (2026-10-08, after the coordinator's review): independent test writer
Gate 1 no longer re-runs only the implementer's own tests (it passed by construction: `T2-g1-r1` one allow, hidden R4
missed, suite green). Before the worker starts, `lib/testwriter.py` (headless Sonnet 5.5, reviewer isolation flags,
`--tools Read,Grep,Glob --max-turns 12 --json-schema {file}`, cwd = a pristine temp copy of upstream) gets ONLY
`tasks/<T>.md` and writes `runs/<run>/gate_tests/test_<T>.py` (+ hidden's conftest/pytest.ini) outside the work copy.
Gate 1 = repo suite AND those tests (`TINYDB_TREE` = work copy). `tests_touched` is logged, no longer a rule.

`./validate_writer.sh` (one writer call per task, files in `validation/writer/<T>/`; reference = verify-loops-bench patches):

| task | writer tests | pass on reference | pass on upstream | fail on reference (possible false blocks, kept) | writer $ / wall |
|---|---|---|---|---|---|
| T1 | 52 | 51 | 1 | `test_pull_on_non_list_field_raises_and_leaves_data_unchanged` | 0.099 / 39 s |
| T2 | 42 | 42 | 5 | none | 0.094 / 35 s |
| T3 | 35 | 34 | 11 | `test_rename_table_non_string_target_does_not_corrupt_database` | 0.077 / 34 s |
| T4 | 48 | 47 | 7 | `test_reverse_without_sort_by_reverses_default_order` | 0.092 / 42 s |
| T5 | 26 | 25 | 7 | `test_non_integer_size_is_rejected` | 0.086 / 30 s |

Tests passing on upstream are the "existing behaviour unchanged" guards the instruction asks for (plus a few that
accept "raises" as an outcome); every task's file fails on upstream overall. Each matrix run writes its own file, so
these counts are one sample; per-run counts land in `score.json` (`gate_tests_total`, `gate_tests_fail_final`).

Overlap with the 5 hidden requirements (judgement from test names + spot reads of the assertions):
- T1: 2/5 strict (R1 order, R5 push non-list raises). R2/R4 hedged (`try: ... except (KeyError, AttributeError, TypeError)`: a raise is accepted), R3 hedged (`count('x') < 2`, first-occurrence removal passes).
- T2: 4/5 (R1, R2, R3, R5 cache inclusive vs exclusive and other bounds); R4 hedged (accepts a TypeError).
- T3: 3/5 strict (R1 ids, R2 persistence + `tables()`, R5 stale cache / old name empty / id sequence); R3/R4 use `pytest.raises(Exception)`, not KeyError/ValueError (R4 does check both tables intact).
- T4: 4/5 (R1, R3, R4 limit 0 / negative ValueError, R5 cache not polluted + Document/doc_id); R2 hedged (checks order of docs that have the field and that none are dropped, not "missing last in both directions").
- T5: 5/5 (R1, R2 restart, R3 class/subclass default, R4 non-positive ValueError at construction, R5 close flushes).
The writer hedges exactly where the terse prompt is silent: it encodes "a raise or a no-op are both fine", so gate 1
cannot recover a requirement the prompt never states (T1 R2/R4, T4 R2).

Smoke after the redesign (`runs/T1-g13adv-r1-smoke`, with the deny rules): writer 45 tests ($0.071), first stop gate 1
green (232 suite + 45/45 gate tests), adv A+B approve, allow; hidden 2/5 (R2, R4, R5 missed). Total $0.189, 68 s.
`runs/T1-g13adv-r1-smoke-a` (first redesign smoke): stop 1 blocked by gate 1 (5 gate tests red, reason starts
"The acceptance tests for this change fail:"), the agent fixed push/pull type checks, stop 2 gate 1 green, both reviewers
errored (transient FileNotFoundError on spawn, logged, fail-open allow; one retry added since). The agent also tried
`cat .claude/hooks/stop.sh; find / -name test_T1.py` after the block (denied by the allow-list) -> deny rules added.
`runs/T1-g13adv-r1-smoke-b`: second redesign smoke, clean (reviewers ran, $0.167).
