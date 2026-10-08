#!/usr/bin/env python3
"""Write matrix.txt: "<cfg> <task> <rep>" lines. Rep 1: configs bare,g1,g3,g13,g13adv as contiguous blocks,
tasks rotated per block; rep 2: same blocks in reverse config order (ABBA over time)."""
CFGS = ["bare", "g1", "g3", "g13", "g13adv"]
TASKS = ["T1", "T2", "T3", "T4", "T5"]
lines = []
for rep, order in ((1, CFGS), (2, CFGS[::-1])):
    lines.append("# rep %d" % rep)
    for i, c in enumerate(order):
        k = (i + rep - 1) % len(TASKS)
        for t in TASKS[k:] + TASKS[:k]:
            lines.append("%s %s %d" % (c, t, rep))
open("matrix.txt", "w").write("\n".join(lines) + "\n")
print(sum(1 for l in lines if not l.startswith("#")), "runs")
