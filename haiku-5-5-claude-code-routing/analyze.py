#!/usr/bin/env python3
"""Aggregate runs/*/score.json into results.json and results.md.

Per config x task: accept rate, mean tokens, mean cost, mean turns, mean wall.
Per config: measured plan-meter deltas (five_hour, seven_day, in percentage points), computed two ways:
  - per_run_sum: sum over the config's runs of (after - before). Quantized at 1% per run, so
    runs far below 1% mostly read 0: a lower-bound-ish, very noisy number.
  - segments:    runs sorted by start time are cut into maximal contiguous segments of the same
    config; each segment contributes (after of its last run - before of its first run). This
    telescopes the quantization: one +-1 pt error per segment instead of per run. PREFERRED.
  Segments/runs whose window resetsAt changed between before and after are excluded for that window.
Plus the /usage-style local heuristic: weighted = cached*1 + uncached*10 + cache_create*12.5 + output*50,
times the model tier (haiku 1 / sonnet 3 / opus 5). The probe's own Haiku tokens after each run are
counted as overhead in the heuristic (they also move the meter).
Usage: analyze.py [--runs-dir runs] [--out-prefix results]
"""
import glob, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, sys.argv[sys.argv.index("--runs-dir") + 1]) if "--runs-dir" in sys.argv else os.path.join(HERE, "runs")
OUTP = sys.argv[sys.argv.index("--out-prefix") + 1] if "--out-prefix" in sys.argv else "results"
CFGS = json.load(open(os.path.join(HERE, "configs.json")))
TASKS = list(json.load(open(os.path.join(HERE, "tasks.json"))).keys())
W = {"cache_read_input_tokens": 1, "input_tokens": 10, "cache_creation_input_tokens": 12.5, "output_tokens": 50}
TIER = {c: v["tier"] for c, v in CFGS.items()}


def weighted(tok, tier):
    raw = sum((tok.get(k) or 0) * w for k, w in W.items())
    return raw, raw * tier


MU = {"cacheReadInputTokens": "cache_read_input_tokens", "inputTokens": "input_tokens",
      "cacheCreationInputTokens": "cache_creation_input_tokens", "outputTokens": "output_tokens"}


def model_tier(name, fallback):
    n = (name or "").lower()
    return 5 if "opus" in n else 3 if "sonnet" in n else 1 if "haiku" in n else fallback


def heuristic_run(s):
    """Tiered heuristic per model actually used (modelUsage), so helper calls on another
    model are weighted with their own tier; falls back to `usage` x config tier."""
    mu = s.get("modelUsage") or {}
    if not mu:
        return weighted(s["tokens"], TIER[s["config"]])[1]
    return sum(weighted({MU[k]: v.get(k) or 0 for k in MU}, model_tier(m, TIER[s["config"]]))[1] for m, v in mu.items())


def probe_tokens(run_dir):
    p = os.path.join(run_dir, "probe.jsonl")
    if not os.path.exists(p):
        return {}
    for line in reversed(open(p, errors="replace").read().strip().split("\n")):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "result":
            u = o.get("usage") or {}
            return {k: u.get(k) or 0 for k in W}
    return {}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def window_delta(b, a, w):
    if not b or not a or b.get(w) is None or a.get(w) is None:
        return None, "missing"
    if b.get(w + "_resets_at") != a.get(w + "_resets_at"):
        return None, "reset"
    return round((a[w] - b[w]) * 100, 2), "ok"


scores = []
for p in sorted(glob.glob(os.path.join(RUNS, "*", "score.json"))):
    s = json.load(open(p))
    if s.get("config") not in CFGS:
        continue
    s["_dir"] = os.path.dirname(p)
    s["_start"] = (s.get("meter_before") or {}).get("ts") or os.path.getmtime(os.path.join(s["_dir"], "stream.jsonl"))
    s["_probe_tok"] = probe_tokens(s["_dir"])
    scores.append(s)
# meter_before.ts is written at extraction time; order by stream file creation instead
for s in scores:
    st = os.stat(os.path.join(s["_dir"], "stream.jsonl"))
    s["_start"] = getattr(st, "st_birthtime", st.st_mtime)
scores.sort(key=lambda s: s["_start"])

cells, per_cfg = {}, {}
for s in scores:
    cells.setdefault((s["config"], s["task"]), []).append(s)
    per_cfg.setdefault(s["config"], []).append(s)

cell_rows = []
for (c, t), ss in sorted(cells.items(), key=lambda kv: (list(CFGS).index(kv[0][0]), TASKS.index(kv[0][1]) if kv[0][1] in TASKS else 99)):
    row = {"config": c, "task": t, "n": len(ss),
           "accept_rate": sum(1 for s in ss if s.get("accepted")) / len(ss),
           "mean_turns": mean([s.get("num_turns") for s in ss]),
           "mean_cost_usd": mean([s.get("total_cost_usd") for s in ss]),
           "mean_wall_s": mean([s.get("wall_s") for s in ss]),
           "mean_tokens": {k: mean([s["tokens"].get(k) for s in ss]) for k in W},
           "mean_weighted_heuristic": mean([heuristic_run(s) for s in ss]),
           "model_ok_all": all(s.get("model_ok") for s in ss)}
    cell_rows.append(row)

# contiguous segments in global start order
segments, cur = [], None
for s in scores:
    if cur and cur["config"] == s["config"]:
        cur["runs"].append(s)
    else:
        cur = {"config": s["config"], "runs": [s]}
        segments.append(cur)

cfg_rows = []
for c, ss in per_cfg.items():
    tok_sum = {k: sum(s["tokens"].get(k) or 0 for s in ss) for k in W}
    probe_sum = {k: sum(s["_probe_tok"].get(k, 0) for s in ss) for k in W}
    raw_w, _ = weighted(tok_sum, TIER[c])
    heur = sum(heuristic_run(s) for s in ss)
    probe_raw, probe_heur = weighted(probe_sum, 1)
    row = {"config": c, "runs": len(ss), "accept_rate": sum(1 for s in ss if s.get("accepted")) / len(ss),
           "tokens_sum": tok_sum, "probe_tokens_sum": probe_sum,
           "cost_sum_usd": round(sum(s.get("total_cost_usd") or 0 for s in ss), 4),
           "weighted_raw_M": raw_w / 1e6, "heuristic_M": (heur + probe_heur) / 1e6}
    for w in ("five_hour", "seven_day"):
        per_run, excl = 0.0, 0
        for s in ss:
            d, why = window_delta(s.get("meter_before"), s.get("meter_after"), w)
            if d is None:
                excl += 1
            else:
                per_run += d
        seg_sum, seg_n, seg_excl = 0.0, 0, 0
        for g in segments:
            if g["config"] != c:
                continue
            d, why = window_delta(g["runs"][0].get("meter_before"), g["runs"][-1].get("meter_after"), w)
            if d is None:
                seg_excl += 1
            else:
                seg_sum += d; seg_n += 1
        row[w] = {"per_run_sum_pts": round(per_run, 2), "per_run_excluded": excl,
                  "segments_sum_pts": round(seg_sum, 2), "segments": seg_n, "segments_excluded": seg_excl,
                  "quantization_error_pts": f"+-{seg_n}",
                  "pts_per_M_heuristic": round(seg_sum / row["heuristic_M"], 4) if row["heuristic_M"] else None,
                  "pts_per_M_weighted_raw": round(seg_sum / row["weighted_raw_M"], 4) if row["weighted_raw_M"] else None}
    cfg_rows.append(row)
cfg_rows.sort(key=lambda r: list(CFGS).index(r["config"]))

out = {"generated_from": len(scores), "cells": cell_rows, "configs": cfg_rows,
       "segments": [{"config": g["config"], "runs": [s["run"] for s in g["runs"]],
                     "before": g["runs"][0].get("meter_before"), "after": g["runs"][-1].get("meter_after")} for g in segments],
       "heuristic_weights": {"tokens": W, "tier": TIER}}
json.dump(out, open(os.path.join(HERE, OUTP + ".json"), "w"), indent=2, default=str)

f = lambda x, d=0: "-" if x is None else (f"{x:,.{d}f}")
md = ["# Results", "", f"{len(scores)} runs. Meter deltas in percentage points of the plan window (1-pt resolution).", "",
      "## Per config x task", "",
      "| config | task | n | accept | turns | input | cache read | cache create | output | cost $ | wall s | heuristic (M) | model ok |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in cell_rows:
    t = r["mean_tokens"]
    md.append(f"| {r['config']} | {r['task']} | {r['n']} | {r['accept_rate']:.0%} | {f(r['mean_turns'],1)} | {f(t['input_tokens'])} | "
              f"{f(t['cache_read_input_tokens'])} | {f(t['cache_creation_input_tokens'])} | {f(t['output_tokens'])} | "
              f"{f(r['mean_cost_usd'],4)} | {f(r['mean_wall_s'],1)} | {f(r['mean_weighted_heuristic']/1e6,2)} | {r['model_ok_all']} |")
md += ["", "## Per config: measured meter vs local heuristic", "",
       "| config | runs | accept | cost $ | heuristic (M units) | 5h pts (segments) | 5h pts (per-run sum) | 7d pts (segments) | segments | 5h pts / M heuristic | 7d pts / M heuristic |",
       "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in cfg_rows:
    fh, sd = r["five_hour"], r["seven_day"]
    md.append(f"| {r['config']} | {r['runs']} | {r['accept_rate']:.0%} | {r['cost_sum_usd']} | {r['heuristic_M']:.2f} | "
              f"{fh['segments_sum_pts']} (excl {fh['segments_excluded']}) | {fh['per_run_sum_pts']} | {sd['segments_sum_pts']} (excl {sd['segments_excluded']}) | "
              f"{fh['segments']} | {fh['pts_per_M_heuristic']} | {sd['pts_per_M_heuristic']} |")
md += ["", "If the /usage heuristic matched the real meter, `pts / M heuristic` would be the same for every config.",
       "Each segment carries up to +-1 pt of quantization error; trust a config's number only when its segment sum is several points.", ""]
open(os.path.join(HERE, OUTP + ".md"), "w").write("\n".join(md))
print("\n".join(md))
