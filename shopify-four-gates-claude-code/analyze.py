#!/usr/bin/env python3
"""Aggregate runs/*/score.json (matrix runs only: <task>-<cfg>-r<rep>, no tag) -> results.json + results.md."""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CFGS = ["bare", "g1", "g3", "g13", "g13adv"]
TASKS = ["T1", "T2", "T3", "T4", "T5"]
rows = []
for p in sorted(glob.glob(os.path.join(HERE, "runs", "*", "score.json"))):
    if re.fullmatch(r"T\d-[a-z0-9]+-r\d+", os.path.basename(os.path.dirname(p))):
        rows.append(json.load(open(p)))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def agg(rs):
    if not rs:
        return None
    n = len(rs)
    hp = sum(r["hidden_pass"] for r in rs)
    ht = sum(r["hidden_pass"] + r["hidden_fail"] for r in rs)
    rb = {g: sum(r["right_blocks_by_gate"][g] for r in rs) for g in ("g1", "g3")}
    fb = {g: sum(r["false_blocks_by_gate"][g] for r in rs) for g in ("g1", "g3")}
    return {
        "runs": n, "hidden_reqs_passed": hp, "hidden_reqs_total": ht, "hidden_rate": round(hp / ht, 4) if ht else None,
        "runs_fully_passing": sum(1 for r in rs if r["hidden_fail"] == 0),
        "suite_green_runs": sum(1 for r in rs if r["suite_fail"] == 0),
        "mean_cost_total_usd": mean([r["cost_total_usd"] for r in rs]),
        "mean_cost_worker_usd": mean([r["cost_worker_usd"] for r in rs]),
        "mean_cost_reviewers_usd": mean([r["cost_reviewers_usd"] for r in rs]),
        "mean_cost_testwriter_usd": mean([r.get("cost_testwriter_usd") or 0 for r in rs]),
        # per-gate cost: gate 1 = the test writer (its tests then run locally for free), gate 3 = the reviewers
        "mean_cost_gate1_usd": mean([r.get("cost_testwriter_usd") or 0 for r in rs]),
        "mean_cost_gate3_usd": mean([r["cost_reviewers_usd"] for r in rs]),
        "gate_tests_total": sum(r.get("gate_tests_total") or 0 for r in rs),
        "gate_tests_fail_final": sum(r.get("gate_tests_fail_final") or 0 for r in rs),
        "mean_wall_s": mean([r["wall_s"] for r in rs]), "mean_turns": mean([r["turns"] for r in rs]),
        "blocks_per_run": round(sum(r["blocks_total"] for r in rs) / n, 3),
        "blocks_by_gate": {g: sum(r["blocks_by_gate"][g] for r in rs) for g in ("g1", "g3")},
        "right_blocks": rb, "false_blocks": fb,
        "false_block_rate": {g: (round(fb[g] / (rb[g] + fb[g]), 3) if rb[g] + fb[g] else None) for g in ("g1", "g3")},
        "give_ups": sum(1 for r in rs if r["give_up"]), "ended_blocked": sum(1 for r in rs if r["ended_blocked"]),
        "reviewer_findings": sum(r["reviewer_findings_total"] for r in rs),
        "reviewer_errors": sum(r.get("reviewer_errors", 0) for r in rs),
        "model_ok": all(r["model_ok"] for r in rs),
        "missed_reqs": sorted(set("%s:%s" % (r["task"], q) for r in rs for q in r["failed_reqs"])),
    }


by_cfg = {c: agg([r for r in rows if r["cfg"] == c]) for c in CFGS}
by_task = {t: {c: agg([r for r in rows if r["task"] == t and r["cfg"] == c]) for c in CFGS} for t in TASKS}
by_task_all = {t: agg([r for r in rows if r["task"] == t]) for t in TASKS}


def rate(c):
    return (by_cfg.get(c) or {}).get("hidden_rate")


def d(a, b):
    return round(a - b, 4) if a is not None and b is not None else None


answers = {
    "q1_gate1_vs_bare": {"bare": rate("bare"), "g1": rate("g1"), "delta": d(rate("g1"), rate("bare"))},
    "q2_gate3_over_g1": {"g1": rate("g1"), "g13": rate("g13"), "delta": d(rate("g13"), rate("g1")),
                         "g3_alone": rate("g3"), "g3_vs_bare": d(rate("g3"), rate("bare"))},
    "q3_adv_vs_indep": {"g13": rate("g13"), "g13adv": rate("g13adv"), "delta": d(rate("g13adv"), rate("g13")),
                        "false_blocks_g3": {c: (by_cfg.get(c) or {}).get("false_blocks", {}).get("g3") for c in ("g13", "g13adv")}},
    "q4_false_block_rate": {c: (by_cfg.get(c) or {}).get("false_block_rate") for c in CFGS},
    "q4_gate1_false_blocks": {c: {"false": (by_cfg.get(c) or {}).get("false_blocks", {}).get("g1"),
                                  "right": (by_cfg.get(c) or {}).get("right_blocks", {}).get("g1")}
                              for c in ("g1", "g13", "g13adv")},
    "q5_cost": {c: {k: (by_cfg.get(c) or {}).get(k) for k in ("mean_cost_total_usd", "mean_cost_worker_usd",
                                                               "mean_cost_gate1_usd", "mean_cost_gate3_usd", "mean_wall_s")} for c in CFGS},
}
json.dump({"n_runs": len(rows), "by_cfg": by_cfg, "by_task": by_task, "by_task_all": by_task_all,
           "answers": answers, "runs": rows}, open(os.path.join(HERE, "results.json"), "w"), indent=2)

L = ["# gate-bench results", "", "%d runs scored (matrix runs only)." % len(rows), "",
     "## Per config", "",
     "| cfg | runs | hidden reqs | fully passing | suite green | mean $ total (worker + g1 writer + g3 reviewers) | mean wall s | blocks/run | g1 right/false | g3 right/false | give-ups | ended blocked | model ok |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for c in CFGS:
    a = by_cfg[c]
    if not a:
        L.append("| %s | 0 |" % c); continue
    L.append("| %s | %d | %d/%d (%.0f%%) | %d | %d | %.3f (%.3f + %.3f + %.3f) | %.0f | %.2f | %d/%d | %d/%d | %d | %d | %s |" % (
        c, a["runs"], a["hidden_reqs_passed"], a["hidden_reqs_total"], 100 * (a["hidden_rate"] or 0),
        a["runs_fully_passing"], a["suite_green_runs"], a["mean_cost_total_usd"] or 0, a["mean_cost_worker_usd"] or 0,
        a["mean_cost_testwriter_usd"] or 0, a["mean_cost_reviewers_usd"] or 0, a["mean_wall_s"] or 0, a["blocks_per_run"], a["right_blocks"]["g1"],
        a["false_blocks"]["g1"], a["right_blocks"]["g3"], a["false_blocks"]["g3"], a["give_ups"], a["ended_blocked"],
        a["model_ok"]))
L += ["", "## Per task (hidden reqs passed / total, per config)", "", "| task | " + " | ".join(CFGS) + " | missed reqs (all configs) |",
      "|---|" + "---|" * (len(CFGS) + 1)]
for t in TASKS:
    cells = []
    for c in CFGS:
        a = by_task[t][c]
        cells.append("%d/%d, $%.2f, %.1f blk" % (a["hidden_reqs_passed"], a["hidden_reqs_total"], a["mean_cost_total_usd"] or 0,
                                                a["blocks_per_run"]) if a else "-")
    L.append("| %s | %s | %s |" % (t, " | ".join(cells), ", ".join((by_task_all[t] or {}).get("missed_reqs", []))))
L += ["", "## The video's questions", ""]
for k, v in answers.items():
    L.append("- **%s**: `%s`" % (k, json.dumps(v)))
L += ["", "Gate 1 false blocks (gate 1 blocked while the hidden oracle was fully green): " + ", ".join(
    "%s %s/%s" % (c, (by_cfg.get(c) or {}).get("false_blocks", {}).get("g1"),
                  ((by_cfg.get(c) or {}).get("false_blocks", {}).get("g1") or 0) + ((by_cfg.get(c) or {}).get("right_blocks", {}).get("g1") or 0))
    for c in ("g1", "g13", "g13adv")) + " (false / all g1 blocks)."]
L += ["", "Right block = the hidden oracle had at least one failing requirement at that stop; false block = the oracle "
      "was fully green at that stop (the gate sent the agent back for nothing the user asked for)."]
open(os.path.join(HERE, "results.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
