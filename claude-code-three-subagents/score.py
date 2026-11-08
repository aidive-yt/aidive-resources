# Parse one run's stream-json and write a result row
import json, sys
w, v, t, n, src_changed, green, tests, killed, wall = sys.argv[1:]
delegated = skill = False
result = {}
for line in open(f"{w}/run.jsonl"):
    try: e = json.loads(line)
    except Exception: continue
    if e.get("type") == "assistant":
        for b in e["message"].get("content", []):
            if b.get("type") == "tool_use":
                i = b.get("input", {})
                if b["name"] in ("Agent", "Task") and i.get("subagent_type") == "test-writer": delegated = True
                if b["name"] == "Skill" and "test-writer" in json.dumps(i): skill = True
    if e.get("type") == "result": result = e
passed = int(src_changed) == 0 and green == "1" and killed == "1"
print(json.dumps({
    "variant": v, "task": t, "run": int(n),
    "invoked": delegated if v == "agent" else skill,
    "pass": passed, "green": green == "1", "srcChanged": int(src_changed), "killed": killed == "1",
    "tests": int(tests), "wallSec": int(wall),
    "costUsd": result.get("total_cost_usd"), "durationMs": result.get("duration_ms"), "turns": result.get("num_turns"),
    "usage": result.get("usage"), "modelUsage": result.get("modelUsage"), "isError": result.get("is_error"),
}))
