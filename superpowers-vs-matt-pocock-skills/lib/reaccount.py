"""Recompute the accounting fields of runs/<run>/turns.jsonl from the saved turn streams (after a change to
lib/accounting.py), keeping what the driver recorded (prompt, source, wall, exit code, PO answer). Then run finalize.py.
    reaccount.py <run dir>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from accounting import account_turn  # noqa: E402

KEEP = ("n", "flow", "prompt", "prompt_source", "exit_code", "wall_s", "killed_wall_cap", "po")

run = os.path.abspath(sys.argv[1])
turns = [json.loads(l) for l in open(os.path.join(run, "turns.jsonl"))]
prev, stage_in_force, out = None, "(none)", []
prev_slash = None
for t in turns:
    prefix = os.path.join(run, "turn-%02d" % t["n"])
    if t["flow"] == "spd" and t["stage"] != prev_slash:  # a typed slash command starts its skill (no Skill event)
        stage_in_force, prev_slash = t["stage"].lstrip("/"), t["stage"]
    sp = t["flow"] in ("sp", "spd")
    acc = account_turn(prefix + ".stream.jsonl", prefix + ".times", prev, None if sp else t["stage"], stage_in_force)
    if acc.get("cumulative"):
        prev = acc["cumulative"]
    if sp:
        stage_in_force = acc["stage_at_end"]
    rec = {k: t[k] for k in KEEP if k in t}
    rec["stage"] = acc["stage_at_end"] if t["flow"] == "sp" else t["stage"]
    rec.update({k: v for k, v in acc.items() if k != "cumulative"})
    out.append(rec)
with open(os.path.join(run, "turns.jsonl"), "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print("%s: %d turns reaccounted" % (os.path.basename(run), len(out)))
