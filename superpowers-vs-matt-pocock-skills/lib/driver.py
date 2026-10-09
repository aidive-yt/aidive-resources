"""One run of the flow bench: drives a headless Sonnet 5.5 session turn by turn, routes questions to the PO.

    driver.py <cfg> <run dir> <work dir> <base sha>

Every worker turn: `claude -p <prompt> [--resume <sid>] --output-format stream-json --verbose --include-hook-events
--include-partial-messages ...` with cwd = the work copy. Per turn it writes turn-NN.stream.jsonl (raw stdout),
turn-NN.times (receive time of every stdout line), turn-NN.stderr, and appends one record to turns.jsonl.
Caps (SPEC): 12 driver turns, --max-turns 60 per claude turn, 40 min wall per run (PO time included).
"""
import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po  # noqa: E402
from accounting import account_turn  # noqa: E402

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "claude-sonnet-5-5"
MAX_DRIVER_TURNS = int(os.environ.get("BENCH_MAX_DRIVER_TURNS", "12"))
MAX_TURNS = os.environ.get("BENCH_MAX_TURNS", "60")
WALL_CAP = float(os.environ.get("BENCH_WALL_CAP_S", str(40 * 60)))

# SPEC allow-list. AskUserQuestion is removed (headless: questions come as plain text); plan mode and worktree
# tools are removed too (a headless session cannot leave plan mode, and a worktree would move the work out of
# the scored copy). Read-only shell commands are auto-approved by Claude Code whatever the list says.
ALLOWED = ",".join([
    "Read", "Edit", "Write", "MultiEdit", "Glob", "Grep", "Skill", "TodoWrite", "Task", "Agent",
    "Bash(node:*)", "Bash(npm:*)", "Bash(pnpm:*)", "Bash(npx vitest:*)", "Bash(npx tsc:*)", "Bash(tsc:*)",
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git add:*)", "Bash(git commit:*)",
    "Bash(git checkout -b:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(mkdir:*)", "Bash(head:*)", "Bash(tail:*)",
    "Bash(grep:*)", "Bash(wc:*)", "Bash(gh:*)",
])
# spd only: the scripts executing-plans / subagent-driven-development call (task-start, task-done, sdd-workspace,
# task-brief, review-package), wherever the model addresses them from.
SPD_EXTRA = ",".join("Bash(*scripts/%s*)" % x for x in ("task-start", "task-done", "sdd-workspace", "task-brief", "review-package"))
DISALLOWED = "AskUserQuestion,EnterPlanMode,ExitPlanMode,EnterWorktree,ExitWorktree,WebFetch,WebSearch"

PRE_IMPLEMENT = ("/grill-with-docs", "/to-spec", "/to-tickets")
SPD_PRE_IMPLEMENT = ("/brainstorming", "/writing-plans")
DONE_SUFFIX = "\n\nWhen you are done, stop and summarise what you changed."


def worker_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


def run_claude(prompt, sid, work, out_prefix, timeout, allowed=ALLOWED):
    cmd = ["claude", "-p", prompt]
    if sid:
        cmd += ["--resume", sid]
    cmd += ["--model", MODEL, "--output-format", "stream-json", "--verbose", "--include-hook-events",
            "--include-partial-messages", "--max-turns", MAX_TURNS, "--permission-mode", "acceptEdits",
            "--allowedTools", allowed, "--disallowedTools", DISALLOWED,
            "--setting-sources", "project", "--strict-mcp-config"]
    t0 = time.time()
    fo = open(out_prefix + ".stream.jsonl", "w")
    ft = open(out_prefix + ".times", "w")
    fe = open(out_prefix + ".stderr", "w")
    p = subprocess.Popen(cmd, cwd=work, env=worker_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=fe, text=True, bufsize=1)
    killed = {"v": False}

    def watchdog():
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            killed["v"] = True
            p.kill()

    th = threading.Thread(target=watchdog, daemon=True)
    th.start()
    for line in p.stdout:
        fo.write(line)
        ft.write("%.3f\n" % (time.time() - t0))
    p.wait()
    th.join(timeout=5)
    for f in (fo, ft, fe):
        f.close()
    return {"exit_code": p.returncode, "wall_s": round(time.time() - t0, 2), "killed_wall_cap": killed["v"], "t0": t0}


def scratch_issues(work):
    root = os.path.join(work, ".scratch")
    if not os.path.isdir(root):
        return None
    for d in sorted(os.listdir(root)):
        if os.path.isdir(os.path.join(root, d, "issues")):
            return ".scratch/%s/issues/" % d
    return None


def main():
    cfg, run_dir, work, base = sys.argv[1:5]
    conf = json.load(open(os.path.join(BENCH, "configs.json")))[cfg]
    flow = conf["flow"]
    task_id = os.environ.get("TASK", "F1")
    task = open(os.path.join(BENCH, "tasks", task_id + ".md")).read().strip()
    allowed = ALLOWED + ("," + SPD_EXTRA if flow == "spd" else "")
    spd_stages = ["/brainstorming", "/writing-plans", "/executing-plans"]
    spd_i = 0
    t_run = time.time()
    sid = None
    prev = None  # cumulative modelUsage / cost of the session so far
    stage_in_force = "(none)"
    caps = []
    turns_log = open(os.path.join(run_dir, "turns.jsonl"), "a")

    # mp flow: the slash commands in SPEC order; the implement stage is built when it is reached.
    mp_stages = ["/grill-with-docs", "/to-spec", "/to-tickets", "/implement", "/code-review", "/pr"]
    mp_i = 0

    def mp_prompt(i):
        s = mp_stages[i]
        if s == "/grill-with-docs":
            return "/grill-with-docs " + task
        if s == "/implement":
            issues = scratch_issues(work)
            return "/implement " + ("the tickets in %s, all of them, blockers first" % issues if issues
                                    else "the spec and tickets above")
        if s == "/code-review":
            return "/code-review since %s" % base
        return s

    if flow == "bare":
        prompt, stage = task + DONE_SUFFIX, "bare"
    elif flow == "spd":
        prompt, stage = "/brainstorming " + task, spd_stages[0]
        stage_in_force = "brainstorming"
    elif flow == "sp":
        prompt, stage = task, None
    else:
        prompt, stage = mp_prompt(0), mp_stages[0]
    source = "driver"
    end_reason = None

    for n in range(1, MAX_DRIVER_TURNS + 1):
        remaining = WALL_CAP - (time.time() - t_run)
        if remaining <= 5:
            caps.append("wall_40min")
            end_reason = "cap_wall"
            break
        prefix = os.path.join(run_dir, "turn-%02d" % n)
        r = run_claude(prompt, sid, work, prefix, remaining, allowed)
        seg_mode = flow in ("sp", "spd")  # stage split by skill in force inside the turn
        acc = account_turn(prefix + ".stream.jsonl", prefix + ".times", prev,
                           None if seg_mode else stage, stage_in_force)
        if acc.get("session_id"):
            sid = acc["session_id"]
        if acc.get("cumulative"):
            prev = acc["cumulative"]
        if seg_mode:
            stage_in_force = acc["stage_at_end"]
        rec = {"n": n, "flow": flow, "task": task_id, "stage": acc["stage_at_end"] if flow == "sp" else stage,
               "prompt": prompt,
               "prompt_source": source, **{k: v for k, v in r.items() if k != "t0"}, **{k: v for k, v in acc.items() if k != "cumulative"}}
        if r["killed_wall_cap"]:
            caps.append("wall_40min")
        if acc.get("subtype") == "error_max_turns":
            caps.append("max_turns_60@turn%d" % n)
        last = acc.get("result_text") or acc.get("last_assistant_text") or ""
        open(prefix + ".last.txt", "w").write(last)
        if r["killed_wall_cap"]:
            rec["po"] = None
            turns_log.write(json.dumps(rec) + "\n")
            turns_log.flush()
            end_reason = "cap_wall"
            break
        po_stage = stage if flow != "sp" else acc["stage_at_end"]
        ans = po.ask(run_dir, n, flow, po_stage, last, task_id)
        rec["po"] = ans
        turns_log.write(json.dumps(rec) + "\n")
        turns_log.flush()

        # Next prompt
        if flow in ("bare", "sp"):
            if ans["kind"] == "done":
                end_reason = "done"
                break
            prompt = ans["reply"] if ans["kind"] == "question" else (
                "go on" if flow == "bare" else "go on, proceed with the plan")
            source = "po" if ans["kind"] == "question" else "driver"
        elif flow == "spd":
            if ans["kind"] == "question":
                prompt, source = ans["reply"], "po"
                if stage in SPD_PRE_IMPLEMENT and "implementing yet" not in prompt:
                    prompt += "\n\nDon't start implementing yet."
            elif ans["kind"] == "waiting" or acc.get("subtype") == "error_max_turns":
                prompt, source = "go on", "driver"
            else:
                spd_i += 1
                if spd_i >= len(spd_stages):
                    end_reason = "done"
                    break
                stage, prompt, source = spd_stages[spd_i], spd_stages[spd_i], "driver"
                stage_in_force = stage.lstrip("/")  # a typed slash command expands inline: no Skill event
        else:
            if ans["kind"] == "question":
                prompt, source = ans["reply"], "po"
                # A user following the Main Flow builds only at /implement. Without this line the worker took the
                # answers to its last grilling questions as a go and coded inside /grill-with-docs (both-r1, twice).
                if stage in PRE_IMPLEMENT and "implementing yet" not in prompt:
                    prompt += "\n\nDon't start implementing yet."
            elif ans["kind"] == "waiting" or acc.get("subtype") == "error_max_turns":
                prompt, source = "go on", "driver"  # stage not finished: stay in it
            else:
                mp_i += 1
                if mp_i >= len(mp_stages):
                    end_reason = "done"
                    break
                stage, prompt, source = mp_stages[mp_i], mp_prompt(mp_i), "driver"
        if n == MAX_DRIVER_TURNS:
            caps.append("driver_turns_12")
            end_reason = "cap_driver_turns"
    meta = {"end_reason": end_reason, "caps": sorted(set(caps)), "session_id": sid,
            "run_wall_s": round(time.time() - t_run, 1), "mp_stage_reached": mp_stages[min(mp_i, 5)] if flow == "mp" else None,
            "spd_stage_reached": spd_stages[min(spd_i, 2)] if flow == "spd" else None, "task": task_id}
    json.dump(meta, open(os.path.join(run_dir, "driver.json"), "w"), indent=2)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
