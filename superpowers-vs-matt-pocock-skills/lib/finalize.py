"""After the driver: final diff, suite, typecheck, hidden oracle, per-stage table -> score.json, stages.json.

    finalize.py <run dir>      (re-runnable; reads meta.json, turns.jsonl, driver.json)
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIDDEN = os.path.join(BENCH, "hidden")
MODEL = "claude-sonnet-5-5"
UPSTREAM_TESTS = 34


def sh(args, cwd, env=None, timeout=600):
    try:
        p = subprocess.run(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or b"").decode("utf-8", "replace") + "\n[timeout]"


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update(extra or {})
    return env


def work_diff(work, base):
    """Working tree vs the base commit (commits made by the worker included) + untracked files. Index untouched."""
    _, d = sh(["git", "diff", base, "--no-color", "--", "."], work)
    _, others = sh(["git", "ls-files", "--others", "--exclude-standard"], work)
    for f in [l for l in others.splitlines() if l.strip()]:
        _, nd = sh(["git", "diff", "--no-color", "--no-index", "--", "/dev/null", f], work)
        d += nd
    return d


def numstat(work, base):
    rows = []
    _, ns = sh(["git", "diff", base, "--numstat", "--", "."], work)
    for l in ns.splitlines():
        p = l.split("\t")
        if len(p) == 3:
            rows.append((int(p[0]) if p[0] != "-" else 0, int(p[1]) if p[1] != "-" else 0, p[2]))
    _, others = sh(["git", "ls-files", "--others", "--exclude-standard"], work)
    for f in [l for l in others.splitlines() if l.strip()]:
        try:
            rows.append((sum(1 for _ in open(os.path.join(work, f), errors="replace")), 0, f))
        except Exception:
            pass
    return rows


def run_hidden(work, base, task="F1"):
    rep = os.path.join(os.path.dirname(work), ".hidden-%s.json" % os.path.basename(work))
    rc, txt = sh([os.path.join(HIDDEN, "node_modules", ".bin", "vitest"), "run", "--reporter=json",
                  "--outputFile=" + rep], HIDDEN, env=clean_env({"WORK": work, "BASE": base, "TASK": task}), timeout=300)
    reqs = OrderedDict(("test_req%d" % i, False) for i in range(1, 6))
    fails = {}
    try:
        j = json.load(open(rep))
        for tr in j.get("testResults", []):
            for a in tr.get("assertionResults", []):
                m = re.match(r"(test_req\d)", a.get("title", ""))
                if m:
                    reqs[m.group(1)] = a.get("status") == "passed"
                    if a.get("status") != "passed":
                        fails[m.group(1)] = (" ".join(a.get("failureMessages") or []))[:600]
            if tr.get("status") == "failed" and not tr.get("assertionResults"):
                fails["collect"] = (tr.get("message") or "")[:800]
        os.remove(rep)
    except Exception as e:  # noqa: BLE001
        fails["runner"] = "%s: %s" % (type(e).__name__, txt[-800:])
    return reqs, fails, txt


def main():
    out = os.path.abspath(sys.argv[1])
    meta = json.load(open(os.path.join(out, "meta.json")))
    work, base, cfg = meta["work"], meta["base"], meta["cfg"]
    if not os.path.isdir(work):  # tmp work copy gone: rescore the archived copy
        work = os.path.join(BENCH, "work", meta["name"])
    drv = json.load(open(os.path.join(out, "driver.json"))) if os.path.exists(os.path.join(out, "driver.json")) else {}
    turns = [json.loads(l) for l in open(os.path.join(out, "turns.jsonl"))] if os.path.exists(
        os.path.join(out, "turns.jsonl")) else []

    have_nm = os.path.isdir(os.path.join(work, "node_modules"))
    if not have_nm:  # rescoring after cleanup: restore deps from upstream
        shutil.copytree(os.path.join(BENCH, "upstream", "node_modules"), os.path.join(work, "node_modules"), symlinks=True)

    diff = work_diff(work, base)
    open(os.path.join(out, "post.diff"), "w").write(diff)
    rows = numstat(work, base)
    open(os.path.join(out, "numstat.txt"), "w").write("".join("%d\t%d\t%s\n" % r for r in rows))
    code = [r for r in rows if r[2].startswith(("src/", "test/"))]
    tests_files = [r for r in rows if r[2].endswith(".test.ts")]

    rc_s, suite = sh([os.path.join(work, "node_modules", ".bin", "vitest"), "run"], work, env=clean_env(), timeout=300)
    open(os.path.join(out, "suite.txt"), "w").write(suite)
    clean = re.sub(r"\x1b\[[0-9;]*m", "", suite)
    m = re.search(r"Tests\s+(?:(\d+) failed \| )?(\d+) passed(?: \| \d+ \w+)? \((\d+)\)", clean)
    s_fail = int(m.group(1) or 0) if m else None
    s_pass = int(m.group(2)) if m else 0
    s_total = int(m.group(3)) if m else 0
    if m is None:
        mf = re.search(r"Tests\s+(\d+) failed \((\d+)\)", clean)
        s_fail, s_total = (int(mf.group(1)), int(mf.group(2))) if mf else (None, 0)
    rc_t, tc = sh([os.path.join(work, "node_modules", ".bin", "tsc"), "--noEmit"], work, env=clean_env(), timeout=300)
    open(os.path.join(out, "typecheck.txt"), "w").write(tc)
    task = meta.get("task", "F1")
    reqs, fails, htxt = run_hidden(work, base, task)
    open(os.path.join(out, "hidden.txt"), "w").write(htxt + "\n" + json.dumps(fails, indent=2))

    _, commits = sh(["git", "log", "--oneline", "%s..HEAD" % base], work)
    _, branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], work)
    _, branches = sh(["git", "branch", "--format=%(refname:short)"], work)
    added_its = 0
    for l in diff.splitlines():
        if re.match(r"^\+\s*(it|test)(\.each\([^)]*\))?\s*\(", l):
            added_its += 1

    # Per-stage table (sum of turn segments; for mp/bare/both a segment = the turn's stage)
    stages = OrderedDict()
    for t in turns:
        for sgm in t.get("segments") or []:
            st = sgm["stage"] if cfg in ("sp", "spd") else t["stage"]
            s = stages.setdefault(st, {"turns": set(), "in": 0, "out": 0, "cr": 0, "cw": 0, "total": 0, "usd": 0.0,
                                       "wall_s": 0.0, "api_calls": 0})
            s["turns"].add(t["n"])
            for k in ("in", "out", "cr", "cw", "total", "api_calls"):
                s[k] += sgm.get(k, 0)
            s["usd"] += sgm.get("usd", 0.0)
            s["wall_s"] += sgm.get("wall_s", 0.0)
        if cfg not in ("sp", "spd") and not t.get("segments"):
            stages.setdefault(t["stage"], {"turns": {t["n"]}, "in": 0, "out": 0, "cr": 0, "cw": 0, "total": 0,
                                           "usd": 0.0, "wall_s": t.get("wall_s", 0), "api_calls": 0})
    # Turn-level wall/usd are exact; mp/bare stage wall = turn wall (segments only cover stdout gaps)
    if cfg not in ("sp", "spd"):
        for st, s in stages.items():
            s["wall_s"] = sum(t.get("wall_s", 0) for t in turns if t["stage"] == st)
            s["usd"] = sum(t.get("usd", 0) for t in turns if t["stage"] == st)
    for s in stages.values():
        s["turns"] = sorted(s["turns"])
        s["usd"] = round(s["usd"], 4)
        s["wall_s"] = round(s["wall_s"], 1)
    json.dump(stages, open(os.path.join(out, "stages.json"), "w"), indent=2)

    tok = {k: sum(t.get("tokens", {}).get(k, 0) for t in turns) for k in ("in", "out", "cr", "cw", "total")}
    models = sorted({m for t in turns for m in (t.get("models") or {})})
    skills = [dict(s, turn=t["n"]) for t in turns for s in t.get("skills") or []]
    hooks = [dict(h, turn=t["n"]) for t in turns for h in t.get("hooks") or []]
    po_cost = sum((t.get("po") or {}).get("cost_usd", 0) for t in turns)
    files = sorted({f.replace(work + "/", "") for t in turns for f in t.get("files_touched") or []})
    score = {
        "run": meta["name"], "task": meta.get("task", "F1"), "cfg": cfg, "rep": meta["rep"], "tag": meta.get("tag"),
        "hidden_pass": sum(reqs.values()), "hidden_reqs": reqs, "hidden_fail_msgs": fails,
        "suite_green": rc_s == 0 and (s_fail or 0) == 0 and s_total > 0, "suite_pass": s_pass, "suite_total": s_total,
        "tests_added_suite": max(0, s_total - UPSTREAM_TESTS), "tests_added_diff": added_its,
        "typecheck_green": rc_t == 0,
        "diff_files": len(rows), "diff_added": sum(r[0] for r in rows), "diff_removed": sum(r[1] for r in rows),
        "code_diff_added": sum(r[0] for r in code), "code_diff_removed": sum(r[1] for r in code),
        "code_files": len(code), "test_files_touched": len(tests_files),
        "non_code_files": sorted(r[2] for r in rows if not r[2].startswith(("src/", "test/"))),
        "files_touched_by_tools": files,
        "commits": len([l for l in commits.splitlines() if l.strip()]), "branch_at_end": branch.strip(),
        "branches": branches.split(),
        "driver_turns": len(turns), "claude_turns_total": sum(t.get("num_turns") or 0 for t in turns),
        "tool_calls": sum(t.get("tool_calls", 0) for t in turns),
        "tokens": tok, "usd": round(sum(t.get("usd", 0) for t in turns), 4),
        "usd_po": round(po_cost, 4),
        "wall_s": round(sum(t.get("wall_s", 0) for t in turns), 1), "run_wall_s": drv.get("run_wall_s"),
        "end_reason": drv.get("end_reason"), "caps": drv.get("caps", []),
        "questions_routed_to_po": sum(1 for t in turns if (t.get("po") or {}).get("kind") == "question"),
        "skills_invoked": [s["skill"] for s in skills],
        "skills_failed": [s["skill"] for s in skills if s.get("ok") is False],
        "skill_events": skills,
        "hook_events": hooks,
        "superpowers_injected": any(h.get("superpowers_injected") for h in hooks),
        "init_plugins": (turns[0].get("init_plugins") if turns else None),
        "models": models, "model_ok": bool(models) and set(models) <= {MODEL},
        "permission_denials": sum(len(t.get("permission_denials") or []) for t in turns),
        "estimated_turns": [t["n"] for t in turns if t.get("estimated")],
        "spd_slash_stage_per_turn": [t["stage"] for t in turns] if cfg == "spd" else None,
        "per_turn": [{"n": t["n"], "stage": t["stage"], "source": t.get("prompt_source"), "usd": t.get("usd"),
                      "tokens": t.get("tokens", {}).get("total"), "wall_s": t.get("wall_s"),
                      "num_turns": t.get("num_turns"), "subtype": t.get("subtype"),
                      "skills": [s["skill"] for s in t.get("skills") or []],
                      "po_kind": (t.get("po") or {}).get("kind")} for t in turns],
        "stages": stages,
    }
    json.dump(score, open(os.path.join(out, "score.json"), "w"), indent=2)
    if os.environ.get("KEEP_NODE_MODULES") != "1":
        shutil.rmtree(os.path.join(work, "node_modules"), ignore_errors=True)
    print("%s: hidden %d/5 suite %s (%d/%d) tsc %s diff +%d/-%d (code +%d/-%d) tokens %d usd %.2f wall %ss turns %d "
          "end=%s caps=%s skills=%s" % (
              meta["name"], score["hidden_pass"], "green" if score["suite_green"] else "RED", s_pass, s_total,
              "ok" if score["typecheck_green"] else "FAIL", score["diff_added"], score["diff_removed"],
              score["code_diff_added"], score["code_diff_removed"], tok["total"], score["usd"], score["wall_s"],
              len(turns), score["end_reason"], ",".join(score["caps"]) or "-",
              ",".join(OrderedDict.fromkeys(score["skills_invoked"])) or "-"))


if __name__ == "__main__":
    main()
