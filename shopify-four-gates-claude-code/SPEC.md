# gate-bench — SPEC (written 2026-10-08 by the /plan stage of the AIDive pipeline)

Goal: measure, on a real repo, what each of Shopify's Helix gates catches when rebuilt as a Claude Code
Stop hook, and what it costs. Output feeds a YouTube video; every number must be reproducible from this dir.

## Reuse (read-only, never modify)
- `/Users/thomas/dev/verify-loops-bench/upstream/` : tinydb @ 18d73a1 (git repo). Copy it as `upstream/` here.
- `/Users/thomas/dev/verify-loops-bench/hidden/` : `test_T1.py..test_T6.py`, `conftest.py`, `pytest.ini`. Copy as `hidden/`.
  Hidden tests are the ORACLE: one `test_reqN` per requirement of the task prompt. They live OUTSIDE every work copy
  and the agent never sees them. Run: `cd <tree> && python -m pytest -c <bench>/hidden/pytest.ini --rootdir <bench>/hidden <bench>/hidden/test_Tn.py -q`
  (conftest puts cwd or `$TINYDB_TREE` first on sys.path). Check `tasks/README.md` there for the exact invocation and validate with `validate.sh`.
- `/Users/thomas/dev/verify-loops-bench/tasks/T1.md..T5.md` : the five task prompts, typed as a developer would. Copy as `tasks/`. T6 is NOT used.
- `/Users/thomas/dev/haiku-routing-bench/{env.sh,run.sh,extract.py,prep.sh,matrix.sh}` : patterns to copy (auth via the
  user's default config dir, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `.venv` with pytest, stream-json extraction of
  `total_cost_usd`, `num_turns`, `usage`, `modelUsage`, fresh work copy per run, `--setting-sources project --strict-mcp-config`).
- Claude Code CLI 2.1.293 is installed. Docs that define the hook contract: https://code.claude.com/docs/en/hooks
  (fetch with `curl -s https://r.jina.ai/https://code.claude.com/docs/en/hooks`): a Stop hook that exits 2 blocks the
  stop and its stderr is fed back; `{"decision":"block","reason":"..."}` on stdout does the same; input JSON on stdin
  carries `stop_hook_active`, `session_id`, `transcript_path`; after 8 consecutive continuations Claude Code overrides
  the next block (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` raises it); a hook past `timeout` (seconds, default 600) renders no decision.

## Worker
`claude -p "<task prompt>" --model claude-sonnet-5-5 --output-format stream-json --verbose --max-turns 60
--permission-mode acceptEdits --allowedTools "<same list as haiku-routing-bench/run.sh>" --setting-sources project
--strict-mcp-config`, cwd = fresh work copy `work/<run>/` (copy of upstream, `git` clean at HEAD). The task prompt is the
T-file verbatim plus one line appended for every config (bare included): "When you are done, stop and summarise what
you changed." No mention of gates in the prompt: the gate is the hook, not the instruction.
Work copy carries `.claude/settings.json` with the Stop hook for gated configs (none for `bare`):
`{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"GATE_RUN=<abs run dir> GATE_CONFIG=<cfg> bash <bench>/gate.sh","timeout":1500}]}]}}`
(check the exact settings shape in the hooks doc; `timeout` is in seconds; verify the hook fires with a smoke run before the matrix).

## Gates (gate.sh, one script, dispatches on GATE_CONFIG)
Reads stdin JSON. Logs ONE line per invocation to `$GATE_RUN/gate.jsonl`: {ts, n (invocation index), stop_hook_active,
gate1:{ran, suite_pass, suite_fail, tests_touched (bool: any file under tests/ added or modified vs HEAD), pass},
gate3:{ran, variant, reviewers:[{id, approve, findings:[{severity, file, line, text}], cost_usd, turns, wall_s}], blocking_findings, pass},
hidden:{pass, fail, failed_reqs} (ground truth at this moment, run SILENTLY on the work copy; never shown to the agent),
decision ("block"|"allow"|"give_up"), reason (the text sent back, truncated 500), wall_s}.
Give-up: after 6 blocks in one run the hook allows and logs decision "give_up" (the video needs to count it; Claude
Code's own 8-cap would otherwise hide it). Never use stop_hook_active to allow: log it only.
Order inside one invocation: gate 1 (when the config has it) first; gate 3 only when gate 1 passed or is absent.
- Gate 1 (behaviour tests): `python -m pytest -q -x --no-header -p no:cacheprovider` on the work copy (the repo's own 226 tests plus
  whatever the agent wrote). Block when red (reason = last 40 lines of pytest), OR when `tests_touched` is false
  (reason: "No test covers the new behaviour. Add tests for every requirement in the task, run them, then stop.").
- Gate 3 (adversarial reviews): headless reviewers, each `claude -p --bare --model claude-sonnet-5-5 --tools "Read,Grep,Glob"
  --max-turns 15 --output-format json --json-schema '<schema>' --permission-mode dontAsk` (confirm each flag exists in
  `claude --help`; drop `--permission-mode dontAsk` if it errors), cwd = work copy, prompt = system framing + the task
  prompt + `git diff HEAD` (tracked + untracked files, cap 60k chars) + "Find defects: requirements not met, edge cases
  wrong, behaviour broken, tests that do not test the requirement. Report only real defects with file and line. approve=true
  only when nothing blocks." Schema: {approve: boolean, findings: [{severity: "blocking"|"minor", file, line, text}]}.
  Read `structured_output` from the JSON result; record `total_cost_usd`. Set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
  - variant `indep` (Shopify as written): two reviewers, same prompt, independent, no shared context; union of findings;
    block if any blocking finding from either; reason = the blocking findings, numbered, "Fix every finding, re-run the
    tests, then stop." Pass when BOTH approve.
  - variant `adv` (reviewer + challenger, arXiv 2608.18167 shape): reviewer A as above; then challenger B gets A's
    findings plus the diff and must, per finding, answer upheld|rejected with a reason, and may add findings A missed;
    only upheld (or B-added) blocking findings block. Pass when nothing upheld blocks.
- Reason text is what the worker sees next turn: keep it factual, under 1500 chars.

## Configs (configs.json)
- `bare`: no hook.
- `g1`: gate 1 only.
- `g3`: gate 3 indep only.
- `g13`: gate 1 then gate 3 indep (Shopify's order).
- `g13adv`: gate 1 then gate 3 adv.
Gate 2 (UI) and gate 4 (engineer) are out of scope by design: tinydb is a library, Shopify allows skipping UI review for
logic-only changes; gate 4 is the human, measured as "what reached the human": the hidden failures left at the end.

## Per run outputs (runs/<task>-<cfg>-r<rep>/)
stream.jsonl, stderr.txt, exit_code.txt, wall_s.txt, gate.jsonl, post.diff, numstat.txt, suite.txt (final repo suite),
hidden.txt (final hidden run), result.json (worker: total_cost_usd, num_turns, usage, modelUsage, is_error, subtype,
final text), score.json: {task, cfg, rep, hidden_pass, hidden_fail, failed_reqs, suite_pass, suite_fail, blocks_total,
blocks_by_gate {g1, g3}, right_blocks (hidden failing at that moment), false_blocks (hidden all passing at that moment),
give_up, ended_blocked (the LAST gate.jsonl line is a block, i.e. Claude Code's cap or the agent ended anyway),
cost_worker_usd, cost_reviewers_usd, cost_total_usd, turns, wall_s, reviewer_findings_total, model_ok}.
Snapshot at every hook call: before gate 1 runs, `git diff HEAD` of the work copy to `$GATE_RUN/snap-<n>.diff`.

## Matrix
5 tasks (T1..T5) × 5 configs × 2 reps = 50 runs. `matrix.txt` ordered: rep 1 of everything first (config-contiguous:
bare, g1, g3, g13, g13adv, tasks rotated), then rep 2 in reverse config order. `matrix.sh` runs up to 3 runs in parallel
(each in its own work copy), appends one line per run to `matrix.log`, resumable (`SKIP_DONE=1` skips runs with score.json).
`analyze.py` → `results.json` + `results.md`: per config: hidden requirements passed / total, runs fully passing, mean
cost, mean wall, blocks per run, right vs false blocks per gate, give-ups, ended_blocked; per task the same; and the
answer to the video's questions: (1) does gate 1 alone move hidden pass rate vs bare, (2) does gate 3 indep add anything
over g1, (3) does adv beat indep, (4) false-block rate per gate, (5) cost per gate.

## Validation before the matrix (VALIDATION.md + validate.sh)
1. upstream fails every hidden test file; the reference patches in `/Users/thomas/dev/verify-loops-bench/reference/`
   pass hidden + suite (reuse their validate.sh logic).
2. The hook fires: one smoke run of T1 on `g1` with a deliberately failing state (apply a patch that breaks one test)
   must show a block in gate.jsonl, and the stream must show the agent continuing after "Stop hook feedback".
3. gate.sh called by hand with a fake stdin on a clean work copy returns allow, on a red copy returns exit 2 with the
   pytest tail on stderr.
4. One reviewer call by hand returns valid structured_output against the schema.
5. Record the exact `claude --version`, the settings.json used, and the hook input keys seen.

## Deliverables
Everything under /Users/thomas/dev/gate-bench with README.md (layout, commands, traps found). When the matrix is launched,
run it with `nohup ./matrix.sh matrix.txt > matrix.nohup 2>&1 &` and report the PID; do not wait for it to finish.
Copy the scripts (not runs/, not work/) to /Users/thomas/dev/faceless-video-pipeline/jobs/shopify-four-gates-claude-code-20261008-1529/research/code/
with a one-line README. Report: what was validated, the smoke run's gate.jsonl, the matrix PID, expected duration.
