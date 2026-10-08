"""After the worker exits: final diff, suite, hidden run, result.json and score.json. Prints one line.
Usage: finalize.py <run dir>   (re-runnable: rescoring an existing run only reads/rewrites files in it)"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PY, env_clean, run_hidden, sh, work_diff  # noqa: E402
from testwriter import run_gate_tests  # noqa: E402

MODEL = "claude-sonnet-5-5"
out = os.path.abspath(sys.argv[1])
meta = json.load(open(os.path.join(out, "meta.json")))
work, task, cfg, rep = meta["work"], meta["task"], meta["cfg"], meta["rep"]


def w(name, txt):
    open(os.path.join(out, name), "w").write(txt)


def rd(name, default=""):
    try:
        return open(os.path.join(out, name)).read().strip()
    except Exception:
        return default


# Final state of the work copy
w("post.diff", work_diff(work))
_, ns = sh(["git", "diff", "HEAD", "--numstat", "--", ".", ":(exclude).coverage"], work)
_, others = sh(["git", "ls-files", "--others", "--exclude-standard"], work)
for f in [l for l in others.splitlines() if l.strip()]:
    try:
        ns += "%d\t0\t%s\n" % (sum(1 for _ in open(os.path.join(work, f), errors="replace")), f)
    except Exception:
        pass
w("numstat.txt", ns)
rc, suite = sh([PY, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "--no-cov"], work,
               timeout=300, env=env_clean())
w("suite.txt", suite)
sp = int((re.findall(r"(\d+) passed", suite) or [0])[-1])
sf = int((re.findall(r"(\d+) failed", suite) or [0])[-1]) + int((re.findall(r"(\d+) errors?\b", suite) or [0])[-1])
if rc != 0 and sf == 0:
    sf = 1
_, hout, hp, hf, hfailed = run_hidden(work, task)
w("hidden.txt", hout)

# Worker result line
lines = []
for raw in open(os.path.join(out, "stream.jsonl"), errors="replace") if os.path.exists(os.path.join(out, "stream.jsonl")) else []:
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            lines.append(json.loads(raw))
        except Exception:
            pass
result = next((o for o in reversed(lines) if o.get("type") == "result"), None) or {}
init = next((o for o in lines if o.get("type") == "system" and o.get("subtype") == "init"), {})
res = {k: result.get(k) for k in ("total_cost_usd", "num_turns", "usage", "modelUsage", "is_error", "subtype",
                                  "stop_reason", "terminal_reason", "duration_ms")}
res["final_text"] = (result.get("result") or "")[-3000:]
res["has_result_line"] = bool(result)
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=2)

# Hook events seen in the stream (which hooks ran)
hook_events = sorted({"%s:%s" % (o.get("hook_event") or o.get("hook_event_name") or "?", o.get("hook_name") or "")
                      for o in lines if o.get("type") == "system" and str(o.get("subtype", "")).startswith("hook")})

# Gate log
gl = [json.loads(l) for l in open(os.path.join(out, "gate.jsonl")) if l.strip()] if os.path.exists(os.path.join(out, "gate.jsonl")) else []
blocks = [g for g in gl if g.get("decision") == "block"]
by_gate = {"g1": sum(1 for g in blocks if g.get("blocked_by") == "g1"),
           "g3": sum(1 for g in blocks if g.get("blocked_by") == "g3")}
right = {k: sum(1 for g in blocks if g.get("blocked_by") == k and g["hidden"]["fail"] > 0) for k in ("g1", "g3")}
false = {k: sum(1 for g in blocks if g.get("blocked_by") == k and g["hidden"]["fail"] == 0) for k in ("g1", "g3")}
rev_cost, rev_findings, rev_errors, rev_models = 0.0, 0, 0, set()
for g in gl:
    for r in (g.get("gate3") or {}).get("reviewers") or []:
        rev_cost += r.get("cost_usd") or 0
        rev_findings += len(r.get("findings") or [])
        rev_errors += 1 if r.get("error") else 0
        rev_models |= set(r.get("models") or [])
# Gate-1 test writer (gated-1 configs only): cost and the final state of its tests on the work copy
tw = {}
try:
    tw = json.load(open(os.path.join(out, "testwriter.json")))
except Exception:
    pass
cost_tw = tw.get("cost_usd") or 0.0
rev_models |= set(tw.get("models") or [])
gt_total = gt_fail = None
gdir = os.path.join(out, "gate_tests")
if os.path.exists(os.path.join(gdir, "test_%s.py" % task)):
    _, gout, gp, gf, _ = run_gate_tests(gdir, task, work)
    w("gatetests-final.txt", gout)
    gt_total, gt_fail = gp + gf, gf
mu = result.get("modelUsage") or {}
cw = result.get("total_cost_usd") or 0.0
s = {
    "task": task, "cfg": cfg, "rep": rep, "run": meta["name"],
    "hidden_pass": hp, "hidden_fail": hf, "failed_reqs": hfailed,
    "suite_pass": sp, "suite_fail": sf,
    "hook_calls": len(gl), "blocks_total": len(blocks), "blocks_by_gate": by_gate,
    "right_blocks": sum(right.values()), "false_blocks": sum(false.values()),
    "right_blocks_by_gate": right, "false_blocks_by_gate": false,
    "give_up": any(g.get("decision") == "give_up" for g in gl),
    "ended_blocked": bool(gl) and gl[-1].get("decision") == "block",
    "cost_worker_usd": round(cw, 6), "cost_reviewers_usd": round(rev_cost, 6), "cost_testwriter_usd": round(cost_tw, 6),
    "cost_total_usd": round(cw + rev_cost + cost_tw, 6),
    "testwriter_ok": tw.get("ok") if tw else None, "gate_tests_total": gt_total, "gate_tests_fail_final": gt_fail,
    "turns": result.get("num_turns"), "wall_s": int(rd("wall_s.txt", "0") or 0),
    "reviewer_findings_total": rev_findings, "reviewer_errors": rev_errors,
    "gate_crashes": rd("gate-errors.txt").count("Traceback"),
    "model_ok": init.get("model") == MODEL and bool(mu) and set(mu) <= {MODEL} and rev_models <= {MODEL},
    "worker_models": sorted(mu), "reviewer_models": sorted(rev_models),
    "is_error": result.get("is_error"), "subtype": result.get("subtype"), "exit_code": rd("exit_code.txt"),
    "has_result_line": bool(result), "claude_code_version": init.get("claude_code_version"),
    "hook_events_in_stream": hook_events,
    "hidden_first_stop": gl[0]["hidden"] if gl else None,
}
json.dump(s, open(os.path.join(out, "score.json"), "w"), indent=2)
print("%s: hidden %d/%d suite %d/%d blocks=%d (g1 %d, g3 %d; right %d, false %d) give_up=%s ended_blocked=%s "
      "gate_tests_fail=%s/%s cost=$%.3f (worker %.3f + rev %.3f + writer %.3f) turns=%s wall=%ss model_ok=%s" % (
          s["run"], hp, hp + hf, sp, sp + sf, len(blocks), by_gate["g1"], by_gate["g3"], s["right_blocks"],
          s["false_blocks"], s["give_up"], s["ended_blocked"], gt_fail, gt_total, s["cost_total_usd"], cw, rev_cost, cost_tw, s["turns"],
          s["wall_s"], s["model_ok"]))
