#!/usr/bin/env python3
"""Read a stream-json file and print the plan meter carried by its rate_limit_event lines.

Output (one JSON line): {"ts", "five_hour", "five_hour_resets_at", "seven_day",
"seven_day_resets_at", "n_events", "raw_first", "raw_last"}: utilizations are the
values of the FIRST event (the meter as the run began). `--last` uses the last event.
"""
import json, sys, time

def events(path):
    out = []
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "rate_limit_event":
            out.append(o)
    return out

def windows(ev):
    info = ev.get("rate_limit_info") or {}
    uw = info.get("unifiedWindows") or {}
    def w(name):
        x = uw.get(name) or {}
        return x.get("utilization"), x.get("resetsAt")
    fh, fhr = w("five_hour")
    sd, sdr = w("seven_day")
    return {"five_hour": fh, "five_hour_resets_at": fhr, "seven_day": sd, "seven_day_resets_at": sdr}

def meter(path, which="first"):
    evs = events(path)
    if not evs:
        return {"ts": int(time.time()), "n_events": 0, "five_hour": None, "seven_day": None}
    ev = evs[0] if which == "first" else evs[-1]
    d = {"ts": int(time.time()), "n_events": len(evs)}
    d.update(windows(ev))
    d["raw_first"] = evs[0].get("rate_limit_info")
    d["raw_last"] = evs[-1].get("rate_limit_info")
    return d

if __name__ == "__main__":
    which = "last" if "--last" in sys.argv else "first"
    path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    print(json.dumps(meter(path, which)))
