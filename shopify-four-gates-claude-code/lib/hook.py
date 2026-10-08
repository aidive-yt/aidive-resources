"""Stop hook: gate 1 (behaviour tests) and/or gate 3 (adversarial review), per GATE_CONFIG.

Env: GATE_RUN (abs run dir, holds meta.json + prompt.txt), GATE_CONFIG (key of configs.json).
stdin: the Stop hook input JSON. Block = exit 2 with the reason on stderr. Allow = exit 0, no output.
Every invocation appends ONE line to $GATE_RUN/gate.jsonl. Nothing but the reason ever reaches the agent.
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BENCH, run_hidden, run_suite, tests_touched, work_diff  # noqa: E402
from testwriter import run_gate_tests  # noqa: E402

GIVE_UP_AFTER = 6


def tail40(out, room=1400):
    t = "\n".join(out.rstrip().splitlines()[-40:])
    if len(t) > room:
        t = "...\n" + t[-room:]
    return t


def main():
    t0 = time.time()
    run = os.environ["GATE_RUN"]
    cfg_name = os.environ["GATE_CONFIG"]
    cfg = json.load(open(os.path.join(BENCH, "configs.json")))[cfg_name]
    meta = json.load(open(os.path.join(run, "meta.json")))
    work, task = meta["work"], meta["task"]
    raw = sys.stdin.read()
    try:
        hin = json.loads(raw) if raw.strip() else {}
    except Exception:
        hin = {"_unparsed": raw[:500]}
    log_path = os.path.join(run, "gate.jsonl")
    prev = []
    if os.path.exists(log_path):
        prev = [json.loads(l) for l in open(log_path) if l.strip()]
    n = len(prev) + 1
    blocks_before = sum(1 for p in prev if p.get("decision") == "block")

    # Snapshot of the work at this stop, before gate 1 runs.
    open(os.path.join(run, "snap-%d.diff" % n), "w").write(work_diff(work))
    # Ground truth at this moment (silent).
    _, hout, hp, hf, hfailed = run_hidden(work, task)
    open(os.path.join(run, "hidden-%d.txt" % n), "w").write(hout)

    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n, "stop_hook_active": hin.get("stop_hook_active"),
           "hook_input_keys": sorted(hin.keys()),
           "gate1": {"ran": False}, "gate3": {"ran": False},
           "hidden": {"pass": hp, "fail": hf, "failed_reqs": hfailed}}
    reason, blocked_by = None, None

    if cfg["gate1"]:
        # Gate 1 = the repo suite AND the acceptance tests written before the run by the independent test writer
        # (run dir gate_tests/, outside the work copy). A writer failure leaves the suite alone (logged).
        rc, out, sp, sf = run_suite(work)
        open(os.path.join(run, "gate1-%d.txt" % n), "w").write(out)
        suite_ok = rc == 0 and sf == 0
        gdir = os.path.join(run, "gate_tests")
        has_gt = os.path.exists(os.path.join(gdir, "test_%s.py" % task))
        g = {"ran": True, "suite_pass": sp, "suite_fail": sf, "tests_touched": tests_touched(work),
             "gate_tests_present": has_gt}
        gt_ok, gout = True, ""
        if has_gt:
            grc, gout, gp, gf, gnames = run_gate_tests(gdir, task, work)
            open(os.path.join(run, "gatetests-%d.txt" % n), "w").write(gout)
            gt_ok = grc == 0 and gf == 0
            g.update(gate_tests_pass=gp, gate_tests_fail=gf, gate_tests_failed=gnames)
        g["pass"] = suite_ok and gt_ok
        rec["gate1"] = g
        if not g["pass"]:
            blocked_by = "g1"
            parts = []
            if not gt_ok:
                parts.append("The acceptance tests for this change fail:\n" + tail40(gout, 1400 if suite_ok else 800))
            if not suite_ok:
                parts.append("The repo's test suite is red (python -m pytest -q -x):\n" + tail40(out, 1400 if gt_ok else 550))
            reason = "\n\n".join(parts)

    if cfg["gate3"] and blocked_by is None:
        from review import gate3, reason_text
        g3 = gate3(work, open(os.path.join(run, "task.md")).read(), cfg["gate3"])
        rec["gate3"] = g3
        if not g3["pass"]:
            blocked_by = "g3"
            reason = reason_text(g3)

    if blocked_by is None:
        decision = "allow"
    elif blocks_before >= GIVE_UP_AFTER:
        decision = "give_up"
    else:
        decision = "block"
    rec["blocked_by"] = blocked_by
    rec["decision"] = decision
    rec["reason"] = (reason or "")[:500]
    rec["reason_chars"] = len(reason or "")
    rec["wall_s"] = round(time.time() - t0, 1)
    with open(log_path, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    if n == 1:
        json.dump(hin, open(os.path.join(run, "hook-input-1.json"), "w"), indent=2)
    if decision == "block":
        sys.stderr.write(reason)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # A crashed gate must never deadlock a run: log and allow.
        run = os.environ.get("GATE_RUN", "/tmp")
        with open(os.path.join(run, "gate-errors.txt"), "a") as fh:
            fh.write(traceback.format_exc() + "\n")
        sys.exit(0)
