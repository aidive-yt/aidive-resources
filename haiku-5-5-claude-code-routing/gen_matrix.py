#!/usr/bin/env python3
"""Write the ordered matrix file.

gen_matrix.py [--reps 3] [--passes 2] [--configs haiku-low,haiku-med,sonnet,opus] [--out matrix.txt]

Order: configs run as contiguous BLOCKS (all tasks of one rep set), cheap configs first; tasks are
rotated inside each block so no task always runs first. With --passes 2 the second pass runs the
configs in reverse order (ABBA), which interleaves configs over time without breaking the
contiguous segments that analyze.py needs to beat the 1% meter resolution.
"""
import argparse, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--reps", type=int, default=3, help="reps per config x task per pass")
ap.add_argument("--passes", type=int, default=2)
ap.add_argument("--configs", default="haiku-low,haiku-med,sonnet,opus")
ap.add_argument("--start-rep", type=int, default=1, help="first rep number (use 2 to keep the r1 smoke runs)")
ap.add_argument("--out", default=os.path.join(HERE, "matrix.txt"))
a = ap.parse_args()
tasks = list(json.load(open(os.path.join(HERE, "tasks.json"))))
cfgs = a.configs.split(",")
lines, rep = [], a.start_rep
for p in range(a.passes):
    order = cfgs if p % 2 == 0 else list(reversed(cfgs))
    lines.append(f"# pass {p + 1}: {' -> '.join(order)}")
    for c in order:
        lines.append(f"# block {c}")
        for r in range(a.reps):
            k = rep + r
            rot = (k - 1) % len(tasks)
            for t in tasks[rot:] + tasks[:rot]:
                lines.append(f"{c} {t} {k}")
    rep += a.reps
open(a.out, "w").write("\n".join(lines) + "\n")
n = sum(1 for l in lines if not l.startswith("#"))
print(f"{a.out}: {n} runs ({len(cfgs)} configs x {len(tasks)} tasks x {a.reps} reps x {a.passes} passes)")
