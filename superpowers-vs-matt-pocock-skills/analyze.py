#!/usr/bin/env python3
"""runs/*/score.json (untagged runs only) -> results.json + results.md."""
import json
import os
import statistics as st
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_ORDER = ["bare", "sp", "spd", "mp", "both"]
CFG_LABEL = {"bare": "bare", "sp": "sp (hook-routed)", "spd": "spd (Superpowers driven)", "mp": "mp (Main Flow)", "both": "both (sp+mp, mp flow)"}
TASKS = ["F1", "F2"]
SPD_ORDER = ["/brainstorming", "/writing-plans", "/executing-plans"]
MP_ORDER = ["/grill-with-docs", "/to-spec", "/to-tickets", "/implement", "/code-review", "/pr"]
# Superpowers phases (the raw skill-in-force stages are kept too)
SP_PHASE = {
    "(none)": "before any skill", "using-superpowers": "before any skill",
    "brainstorming": "brainstorming", "writing-plans": "writing-plans",
    "executing-plans": "execution", "subagent-driven-development": "execution",
    "test-driven-development": "execution", "systematic-debugging": "execution",
    "verification-before-completion": "verification", "dispatching-parallel-agents": "execution",
    "requesting-code-review": "review", "receiving-code-review": "review",
    "finishing-a-development-branch": "finishing", "using-git-worktrees": "execution",
    "implementation (no skill)": "implementation (no skill)",
}
PHASE_ORDER = ["before any skill", "brainstorming", "writing-plans", "implementation (no skill)", "execution", "verification", "review", "finishing", "subagents (reviewers, explorers)", "other"]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 3) if xs else None


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 3) if xs else None


def load():
    runs = []
    for d in sorted(os.listdir(os.path.join(HERE, "runs"))):
        p = os.path.join(HERE, "runs", d, "score.json")
        if not os.path.exists(p):
            continue
        s = json.load(open(p))
        if s.get("tag"):
            continue
        runs.append(s)
    return runs


def stage_agg(runs, key_fn, order):
    agg = defaultdict(lambda: defaultdict(list))
    for s in runs:
        per = defaultdict(lambda: {"total": 0, "usd": 0.0, "wall_s": 0.0, "out": 0})
        for name, v in s["stages"].items():
            k = key_fn(name)
            for f in ("total", "usd", "wall_s", "out"):
                per[k][f] += v.get(f, 0)
        for k, v in per.items():
            if not (v["total"] or v["usd"] or v["wall_s"]):
                continue  # empty subagent placeholder segment
            for f in v:
                agg[k][f].append(v[f])
    names = [n for n in order if n in agg] + sorted(n for n in agg if n not in order)
    out = OrderedDict()
    for n in names:
        a = agg[n]
        out[n] = {"runs_with_stage": len(a["total"]), "tokens_mean": mean(a["total"]), "tokens_median": med(a["total"]),
                  "out_tokens_mean": mean(a["out"]), "usd_mean": mean(a["usd"]), "usd_median": med(a["usd"]),
                  "wall_s_mean": mean(a["wall_s"]), "wall_s_median": med(a["wall_s"])}
    return out


def turn_stage_agg(runs, order):
    """Per slash-command stage from the per-turn records (exact turn USD / tokens / wall)."""
    agg = defaultdict(lambda: defaultdict(list))
    for s in runs:
        per = defaultdict(lambda: {"total": 0, "usd": 0.0, "wall_s": 0.0, "out": 0})
        for t in s["per_turn"]:
            per[t["stage"]]["total"] += t.get("tokens") or 0
            per[t["stage"]]["usd"] += t.get("usd") or 0
            per[t["stage"]]["wall_s"] += t.get("wall_s") or 0
        for k, v in per.items():
            for f in v:
                agg[k][f].append(v[f])
    out = OrderedDict()
    for n in [n for n in order if n in agg] + sorted(n for n in agg if n not in order):
        a = agg[n]
        out[n] = {"runs_with_stage": len(a["total"]), "tokens_mean": mean(a["total"]), "tokens_median": med(a["total"]),
                  "out_tokens_mean": None, "usd_mean": mean(a["usd"]), "usd_median": med(a["usd"]),
                  "wall_s_mean": mean(a["wall_s"]), "wall_s_median": med(a["wall_s"])}
    return out


def main():
    runs = load()
    for s in runs:
        s.setdefault("task", "F1")
    by = OrderedDict(("%s/%s" % (t, c), [s for s in runs if s["cfg"] == c and s["task"] == t]) for t in TASKS for c in CFG_ORDER)
    res = {"configs": OrderedDict(), "stages": OrderedDict(), "runs": []}
    for key, rs in by.items():
        if not rs:
            continue
        task, c = key.split("/")
        m = lambda f: [f(s) for s in rs]  # noqa: E731
        res["configs"][key] = {
            "task": task, "cfg": c, "label": CFG_LABEL[c],
            "n": len(rs),
            "hidden_mean": mean(m(lambda s: s["hidden_pass"])), "hidden_median": med(m(lambda s: s["hidden_pass"])),
            "hidden_per_run": m(lambda s: s["hidden_pass"]),
            "req_pass_rate": {r: sum(1 for s in rs if s["hidden_reqs"].get(r)) for r in ["test_req%d" % i for i in range(1, 6)]},
            "suite_green": sum(1 for s in rs if s["suite_green"]), "typecheck_green": sum(1 for s in rs if s["typecheck_green"]),
            "tests_added_mean": mean(m(lambda s: s["tests_added_suite"])),
            "code_diff_mean": mean(m(lambda s: s["code_diff_added"] + s["code_diff_removed"])),
            "code_diff_median": med(m(lambda s: s["code_diff_added"] + s["code_diff_removed"])),
            "all_diff_mean": mean(m(lambda s: s["diff_added"] + s["diff_removed"])),
            "non_code_files_mean": mean(m(lambda s: len(s["non_code_files"]))),
            "tokens_mean": mean(m(lambda s: s["tokens"]["total"])), "tokens_median": med(m(lambda s: s["tokens"]["total"])),
            "out_tokens_mean": mean(m(lambda s: s["tokens"]["out"])),
            "usd_mean": mean(m(lambda s: s["usd"])), "usd_median": med(m(lambda s: s["usd"])),
            "usd_po_mean": mean(m(lambda s: s["usd_po"])),
            "wall_s_mean": mean(m(lambda s: s["wall_s"])), "wall_s_median": med(m(lambda s: s["wall_s"])),
            "driver_turns_mean": mean(m(lambda s: s["driver_turns"])),
            "questions_mean": mean(m(lambda s: s["questions_routed_to_po"])),
            "caps": {s["run"]: s["caps"] for s in rs if s["caps"]},
            "end_reasons": m(lambda s: s["end_reason"]),
            "models": sorted({x for s in rs for x in s["models"]}),
            "superpowers_injected": m(lambda s: s["superpowers_injected"]),
            "skills_per_run": {s["run"]: list(OrderedDict.fromkeys(s["skills_invoked"])) for s in rs},
            "skills_failed": {s["run"]: s["skills_failed"] for s in rs if s["skills_failed"]},
        }
        if c in ("sp", "spd"):
            res["stages"]["%s/%s_skill" % (task, c)] = stage_agg(rs, lambda n: n, list(SP_PHASE))
            res["stages"]["%s/%s_phase" % (task, c)] = stage_agg(rs, lambda n: "subagents (reviewers, explorers)" if n.endswith("[subagent]") else SP_PHASE.get(n, "other"), PHASE_ORDER)
        if c == "spd":
            res["stages"]["%s/spd_slash" % task] = turn_stage_agg(rs, SPD_ORDER)
        if c in ("mp", "both"):
            res["stages"]["%s/%s" % (task, c)] = stage_agg(rs, lambda n: n, MP_ORDER)
    for s in runs:
        res["runs"].append({k: s[k] for k in ("run", "task", "cfg", "hidden_pass", "hidden_reqs", "suite_green", "typecheck_green",
                                               "code_diff_added", "code_diff_removed", "diff_added", "diff_removed",
                                               "tests_added_suite", "tokens", "usd", "usd_po", "wall_s", "driver_turns",
                                               "questions_routed_to_po", "end_reason", "caps", "skills_invoked",
                                               "superpowers_injected", "commits", "models", "stages")})
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=2)

    L = ["# flow-bench results", "",
         "Untagged runs only (smoke/validation excluded). Tokens = input + output + cache read + cache write, all models, "
         "subagents included. USD = list-price equivalent from `total_cost_usd` deltas (plan quota, not a bill). "
         "Wall = sum of worker turn walls (PO time excluded). Diff = lines added+removed vs the base commit, src/ + test/.", "",
         "## Per config (mean / median)", "",
         "| task / config | n | hidden /5 (per run) | suite green | tsc green | code diff +/- | all files diff | tests added | tokens | USD | wall s | driver turns | questions | caps hit |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c, v in res["configs"].items():
        L.append("| %s | %d | %s / %s (%s) | %d/%d | %d/%d | %s / %s | %s | %s | %s / %s | %s / %s | %s / %s | %s | %s | %s |" % (
            "%s / %s" % (v["task"], v["label"]), v["n"], v["hidden_mean"], v["hidden_median"], ",".join(map(str, v["hidden_per_run"])), v["suite_green"], v["n"],
            v["typecheck_green"], v["n"], v["code_diff_mean"], v["code_diff_median"], v["all_diff_mean"], v["tests_added_mean"],
            fmt(v["tokens_mean"]), fmt(v["tokens_median"]), v["usd_mean"], v["usd_median"], v["wall_s_mean"], v["wall_s_median"],
            v["driver_turns_mean"], v["questions_mean"], "; ".join("%s: %s" % (k, ",".join(x)) for k, x in v["caps"].items()) or "none"))
    L += ["", "Requirement pass counts (runs passing each hidden req):", ""]
    for c, v in res["configs"].items():
        L.append("- **%s %s**: %s" % (v["task"], v["label"], ", ".join("%s %d/%d" % (k.replace("test_", ""), n, v["n"]) for k, n in v["req_pass_rate"].items())))
    titles = []
    for t in TASKS:
        titles += [("%s/spd_slash" % t, "%s spd (Superpowers driven) per slash-command stage (turn level, exact)" % t),
                   ("%s/spd_skill" % t, "%s spd per skill in force (within-turn split)" % t),
                   ("%s/sp_phase" % t, "%s sp (hook-routed) per phase" % t),
                   ("%s/sp_skill" % t, "%s sp (hook-routed) per skill in force" % t),
                   ("%s/mp" % t, "%s mp per slash-command stage" % t), ("%s/both" % t, "%s both per slash-command stage" % t)]
    for key, title in titles:
        if key not in res["stages"]:
            continue
        L += ["", "## %s (mean over the runs that had the stage)" % title, "",
              "| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |",
              "|---|---|---|---|---|---|---|---|---|"]
        for n, v in res["stages"][key].items():
            L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (n, v["runs_with_stage"], fmt(v["tokens_mean"]),
                     fmt(v["tokens_median"]), fmt(v["out_tokens_mean"]), v["usd_mean"], v["usd_median"], v["wall_s_mean"], v["wall_s_median"]))
    L += ["", "## Per run", "",
          "| run | task | hidden | reqs failed | suite | tsc | code +/- | tests added | tokens | USD | wall s | turns | end | skills (first use order) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(runs, key=lambda s: (s["task"], CFG_ORDER.index(s["cfg"]), s["run"])):
        L.append("| %s | %s | %d/5 | %s | %s | %s | +%d/-%d | %d | %s | %.2f | %.0f | %d | %s%s | %s |" % (
            s["run"], s["task"], s["hidden_pass"], ",".join(k.replace("test_", "") for k, v in s["hidden_reqs"].items() if not v) or "-",
            "green" if s["suite_green"] else "RED", "ok" if s["typecheck_green"] else "FAIL", s["code_diff_added"],
            s["code_diff_removed"], s["tests_added_suite"], fmt(s["tokens"]["total"]), s["usd"], s["wall_s"], s["driver_turns"],
            s["end_reason"], (" (" + ",".join(s["caps"]) + ")") if s["caps"] else "",
            " > ".join(OrderedDict.fromkeys(x.split(":")[-1] for x in s["skills_invoked"])) or "-"))
    open(os.path.join(HERE, "results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def fmt(x):
    if x is None:
        return "-"
    return "{:,.0f}".format(x)


if __name__ == "__main__":
    main()
