#!/usr/bin/env python3
"""Extract one run's numbers from runs/<name>/stream.jsonl.

extract.py <outdir> <config> <task> <rep>          -> prints the stream's `result` line (result.json)
extract.py <outdir> <config> <task> <rep> --score  -> writes score.json, prints a one-line summary
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from meter import meter  # noqa: E402

out, cfg, task, rep = sys.argv[1:5]
score_mode = "--score" in sys.argv
stream = os.path.join(out, "stream.jsonl")

lines = []
for raw in open(stream, errors="replace") if os.path.exists(stream) else []:
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            lines.append(json.loads(raw))
        except Exception:
            pass
result = next((o for o in reversed(lines) if o.get("type") == "result"), None)
init = next((o for o in lines if o.get("type") == "system" and o.get("subtype") == "init"), {})

if not score_mode:
    print(json.dumps(result or {"type": "result", "result": "", "missing": True}))
    sys.exit(0)

def rd(name, default=None):
    p = os.path.join(out, name)
    try:
        return open(p).read().strip()
    except Exception:
        return default

def jl(name):
    try:
        return json.loads(rd(name) or "null")
    except Exception:
        return None

cfgs = json.load(open(os.path.join(HERE, "configs.json")))
before = meter(stream, "first") if os.path.exists(stream) else None
after = jl("after.json")
r = result or {}
usage = r.get("usage") or {}
tok = {k: usage.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")}
mu = r.get("modelUsage") or {}
assistant_models = sorted({(o.get("message") or {}).get("model") for o in lines
                           if o.get("type") == "assistant" and (o.get("message") or {}).get("model") not in (None, "<synthetic>")})
check_txt = (rd("check.txt", "") or "").split("\n")
verdict_line = check_txt[0] if check_txt else ""
numstat = [l.split("\t") for l in (rd("numstat.txt", "") or "").split("\n") if l.strip()]
added = sum(int(a) for a, d, f in numstat if a.isdigit())
deleted = sum(int(d) for a, d, f in numstat if d.isdigit())
changed_by_agent = (rd("pre.diff", "") or "") != (rd("post.diff", "") or "")

def strip_raw(m):
    if not m:
        return m
    return {k: v for k, v in m.items() if not k.startswith("raw_")}

s = {
    "run": os.path.basename(out), "config": cfg, "task": task, "rep": int(rep),
    "expected_model": cfgs[cfg]["model"], "config_args": cfgs[cfg]["args"],
    "init_model": init.get("model"), "assistant_models": assistant_models,
    "model_usage_keys": sorted(mu.keys()),
    "model_ok": init.get("model") == cfgs[cfg]["model"] and set(mu.keys()) <= {cfgs[cfg]["model"]} and bool(mu),
    "claude_code_version": init.get("claude_code_version"),
    "meter_before": strip_raw(before), "meter_after": strip_raw(after),
    "n_rate_limit_events": (before or {}).get("n_events", 0),
    "has_result_line": result is not None,
    "subtype": r.get("subtype"), "is_error": r.get("is_error"), "stop_reason": r.get("stop_reason"),
    "num_turns": r.get("num_turns"), "duration_ms": r.get("duration_ms"), "duration_api_ms": r.get("duration_api_ms"),
    "total_cost_usd": r.get("total_cost_usd"), "usage": usage, "tokens": tok, "modelUsage": mu,
    "wall_s": int(rd("wall_s.txt", "0") or 0), "exit_code": rd("exit_code.txt"),
    "final_text": (r.get("result") or "")[-2000:],
    "diff": {"files": len(numstat), "added": added, "deleted": deleted, "changed_by_agent": changed_by_agent},
    "check": {"verdict": verdict_line.split(" ")[0] if verdict_line else None, "reason": verdict_line[5:] if verdict_line else None},
}
s["accepted"] = s["check"]["verdict"] == "PASS"
json.dump(s, open(os.path.join(out, "score.json"), "w"), indent=2)
mb, ma = s["meter_before"] or {}, s["meter_after"] or {}
print(f"{s['run']}: {s['check']['verdict']} turns={s['num_turns']} cost=${(s['total_cost_usd'] or 0):.3f} "
      f"in={tok['input_tokens']} cr={tok['cache_read_input_tokens']} cc={tok['cache_creation_input_tokens']} out={tok['output_tokens']} "
      f"wall={s['wall_s']}s 5h {mb.get('five_hour')}->{ma.get('five_hour')} 7d {mb.get('seven_day')}->{ma.get('seven_day')} "
      f"model_ok={s['model_ok']} | {s['check']['reason']}")
