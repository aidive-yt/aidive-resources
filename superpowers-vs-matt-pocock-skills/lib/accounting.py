"""Per-turn and per-stage accounting from one claude -p stream-json (with --include-partial-messages).

Sources of truth (checked on 2.1.294, see README traps):
- result.total_cost_usd and result.modelUsage are CUMULATIVE over a resumed session and include subagents:
  per-turn USD and tokens = delta against the previous turn's result.
- result.usage covers the main thread of this invocation only (no subagents): not used for totals.
- assistant events carry a usage SNAPSHOT taken when the message started (output_tokens partial);
  stream_event message_start/message_delta (main thread only) carry the exact per-API-call usage.
- Subagent API calls emit only assistant snapshots (parent_tool_use_id = the Task/Agent tool_use id).
Stage split inside a turn (sp: the skill in force): main-thread calls are priced exactly from their own usage
(Sonnet 5.5 list prices, verified against total_cost_usd); the subagent remainder (turn delta - main calls) is
split over the Task calls that spawned them, weighted by their snapshot tokens. Wall per stage = the receive-time
gaps of the stdout lines, attributed to the stage in force.
"""
import json
from collections import Counter, defaultdict

# USD per token, claude-sonnet-5-5 list prices (derived from two probe turns: exact match to total_cost_usd).
PRICE = {"in": 2e-6, "out": 10e-6, "cr": 0.2e-6, "cw1h": 4e-6, "cw5m": 2.5e-6}
SP_INJECT_MARK = "You have superpowers"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DESIGN_STAGES = {"(none)", "using-superpowers", "brainstorming", "writing-plans"}
NO_SKILL_IMPL = "implementation (no skill)"


def _tok(u):
    """Normalise an API usage dict to in/out/cr/cw (+ cw split)."""
    u = u or {}
    cc = u.get("cache_creation") or {}
    cw = u.get("cache_creation_input_tokens") or 0
    cw1h = cc.get("ephemeral_1h_input_tokens")
    cw5m = cc.get("ephemeral_5m_input_tokens")
    if cw1h is None and cw5m is None:
        cw1h, cw5m = cw, 0
    return {"in": u.get("input_tokens") or 0, "out": u.get("output_tokens") or 0,
            "cr": u.get("cache_read_input_tokens") or 0, "cw": cw, "cw1h": cw1h or 0, "cw5m": cw5m or 0}


def _usd(t):
    return t["in"] * PRICE["in"] + t["out"] * PRICE["out"] + t["cr"] * PRICE["cr"] + \
        t["cw1h"] * PRICE["cw1h"] + t["cw5m"] * PRICE["cw5m"]


def _mu_tokens(mu):
    out = {}
    for m, v in (mu or {}).items():
        out[m] = {"in": v.get("inputTokens") or 0, "out": v.get("outputTokens") or 0,
                  "cr": v.get("cacheReadInputTokens") or 0, "cw": v.get("cacheCreationInputTokens") or 0,
                  "usd": v.get("costUSD") or 0.0}
    return out


def _sub(a, b):
    keys = set(a) | set(b)
    return {m: {k: (a.get(m, {}).get(k, 0) - b.get(m, {}).get(k, 0)) for k in ("in", "out", "cr", "cw", "usd")}
            for m in keys}


def _sum_models(per_model):
    t = {k: 0 for k in ("in", "out", "cr", "cw", "usd")}
    for v in per_model.values():
        for k in t:
            t[k] += v.get(k, 0)
    return t


def account_turn(stream_path, times_path, prev, fixed_stage, stage_in_force):
    lines, times = [], []
    try:
        raw = open(stream_path, errors="replace").read().splitlines()
        tms = [float(x) for x in open(times_path).read().split()]
    except FileNotFoundError:
        raw, tms = [], []
    for i, l in enumerate(raw):
        l = l.strip()
        if l.startswith("{"):
            try:
                lines.append(json.loads(l))
                times.append(tms[i] if i < len(tms) else (times[-1] if times else 0.0))
            except Exception:
                pass

    stage = fixed_stage or stage_in_force
    out = {"session_id": None, "subtype": None, "is_error": None, "num_turns": None, "result_text": None,
           "last_assistant_text": "", "stage_at_start": stage}
    tools_main, tools_sub = Counter(), Counter()
    skills, hooks, files = [], [], set()
    skill_ids = {}
    task_stage = {}  # Task/Agent tool_use id -> stage when spawned
    main_calls = {}  # msg id -> {"stage", "tok"}
    sub_snap = {}  # msg id -> (parent id, tokens)
    seg_wall = defaultdict(float)
    order = [stage]
    last_t = 0.0
    result = None
    denials = []
    for o, t in zip(lines, times):
        seg_wall[stage] += max(0.0, t - last_t)
        last_t = t
        typ = o.get("type")
        if typ == "system" and o.get("subtype") == "init":
            out["session_id"] = o.get("session_id")
            out["init_model"] = o.get("model")
            out["init_skills"] = o.get("skills")
            out["init_plugins"] = [p.get("name") for p in o.get("plugins") or []]
        elif typ == "system" and str(o.get("subtype", "")).startswith("hook"):
            if o.get("subtype") == "hook_response":
                outp = o.get("output") or ""
                hooks.append({"event": o.get("hook_event"), "name": o.get("hook_name"),
                              "superpowers_injected": SP_INJECT_MARK in outp, "output_chars": len(outp),
                              "exit_code": o.get("exit_code"), "outcome": o.get("outcome")})
        elif typ == "stream_event" and not o.get("parent_tool_use_id"):
            ev = o.get("event") or {}
            if ev.get("type") == "message_start":
                m = ev.get("message") or {}
                main_calls[m.get("id")] = {"stage": stage, "tok": _tok(m.get("usage")), "model": m.get("model")}
                main_calls["__last__"] = m.get("id")
            elif ev.get("type") == "message_delta":
                mid = main_calls.get("__last__")
                if mid in main_calls:
                    u = ev.get("usage") or {}
                    tk = main_calls[mid]["tok"]
                    tk["out"] = u.get("output_tokens", tk["out"]) or tk["out"]
        elif typ == "assistant":
            m = o.get("message") or {}
            parent = o.get("parent_tool_use_id")
            if parent:
                sub_snap[m.get("id")] = (parent, _tok(m.get("usage")))
            for c in m.get("content") or []:
                if c.get("type") == "text" and not parent:
                    out["last_assistant_text"] = c.get("text") or out["last_assistant_text"]
                if c.get("type") != "tool_use":
                    continue
                name = c.get("name")
                inp = c.get("input") or {}
                (tools_sub if parent else tools_main)[name] += 1
                if name in EDIT_TOOLS and inp.get("file_path"):
                    files.add(inp["file_path"])
                    # sp: code written while only a design skill is in force = implementation with no skill
                    if (not parent and not fixed_stage and stage in DESIGN_STAGES
                            and ("/src/" in inp["file_path"] or "/test/" in inp["file_path"])):
                        stage = NO_SKILL_IMPL
                        order.append(stage)
                if name in ("Task", "Agent") and not parent:
                    task_stage[c.get("id")] = stage
                if name == "Skill":
                    sk = inp.get("skill") or inp.get("command") or "?"
                    rec = {"skill": sk, "t": round(t, 2), "thread": "sub" if parent else "main", "ok": None,
                           "args": (inp.get("args") or "")[:200]}
                    skills.append(rec)
                    skill_ids[c.get("id")] = rec
                    if not parent and not fixed_stage:
                        stage = sk.split(":")[-1]
                        order.append(stage)
        elif typ == "user":
            for c in (o.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in skill_ids:
                    txt = c.get("content")
                    txt = txt if isinstance(txt, str) else json.dumps(txt)
                    skill_ids[c["tool_use_id"]]["ok"] = not c.get("is_error") and "Launching skill" in txt
                    skill_ids[c["tool_use_id"]]["result"] = txt[:200]
        elif typ == "result":
            result = o
    main_calls.pop("__last__", None)

    if result:
        out.update({"subtype": result.get("subtype"), "is_error": result.get("is_error"),
                    "num_turns": result.get("num_turns"), "result_text": result.get("result"),
                    "terminal_reason": result.get("terminal_reason"), "stop_reason": result.get("stop_reason")})
        denials = result.get("permission_denials") or []
        cum = {"cost": result.get("total_cost_usd") or 0.0, "models": _mu_tokens(result.get("modelUsage"))}
        pm = prev["models"] if prev else {}
        delta_models = _sub(cum["models"], pm)
        delta_cost = cum["cost"] - (prev["cost"] if prev else 0.0)
        out["cumulative"] = cum
        out["estimated"] = False
    else:  # killed or crashed: best effort from the stream itself
        delta_models = {}
        for c in main_calls.values():
            d = delta_models.setdefault(c.get("model") or "?", {"in": 0, "out": 0, "cr": 0, "cw": 0, "usd": 0.0})
            for k in ("in", "out", "cr", "cw"):
                d[k] += c["tok"][k]
            d["usd"] += _usd(c["tok"])
        for _, (parent, tk) in sub_snap.items():
            d = delta_models.setdefault("?sub", {"in": 0, "out": 0, "cr": 0, "cw": 0, "usd": 0.0})
            for k in ("in", "out", "cr", "cw"):
                d[k] += tk[k]
            d["usd"] += _usd(tk)
        delta_cost = sum(v["usd"] for v in delta_models.values())
        out["cumulative"] = None
        out["estimated"] = True
    tot = _sum_models(delta_models)
    out["usd"] = round(delta_cost, 6)
    out["tokens"] = {k: tot[k] for k in ("in", "out", "cr", "cw")}
    out["tokens"]["total"] = sum(out["tokens"].values())
    out["models"] = {m: v for m, v in delta_models.items() if any(v[k] for k in ("in", "out", "cr", "cw"))}

    # Stage segments
    segs = defaultdict(lambda: {"in": 0, "out": 0, "cr": 0, "cw": 0, "usd": 0.0, "api_calls": 0, "wall_s": 0.0})
    main_tok = {"in": 0, "out": 0, "cr": 0, "cw": 0}
    main_usd = 0.0
    for c in main_calls.values():
        s = segs[c["stage"]]
        for k in ("in", "out", "cr", "cw"):
            s[k] += c["tok"][k]
            main_tok[k] += c["tok"][k]
        u = _usd(c["tok"])
        s["usd"] += u
        s["api_calls"] += 1
        main_usd += u
    rem = {k: max(0, out["tokens"][k] - main_tok[k]) for k in ("in", "out", "cr", "cw")}
    rem_usd = max(0.0, delta_cost - main_usd) if result else 0.0
    weights = defaultdict(float)
    for _, (parent, tk) in sub_snap.items():
        # subagent spend is its own segment, labelled with the stage that dispatched it
        weights[task_stage.get(parent, stage) + " [subagent]"] += tk["in"] + tk["cr"] + tk["cw"] + tk["out"]
    wsum = sum(weights.values())
    if result and (wsum > 0 or rem_usd > 0):
        if wsum == 0:
            weights = {stage + " [subagent]": 1.0}
            wsum = 1.0
        for st, w in weights.items():
            s = segs[st]
            f = w / wsum
            for k in ("in", "out", "cr", "cw"):
                s[k] += int(round(rem[k] * f))
            s["usd"] += rem_usd * f
    for st, w in seg_wall.items():
        segs[st]["wall_s"] += w
    seen = []
    for st in order:
        if st not in seen:
            seen.append(st)
    for st in segs:
        if st not in seen:
            seen.append(st)
    out["segments"] = [dict(stage=st, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in segs[st].items()},
                            total=segs[st]["in"] + segs[st]["out"] + segs[st]["cr"] + segs[st]["cw"])
                       for st in seen if st in segs]
    out["pricing_check"] = {"main_calls_usd": round(main_usd, 6), "turn_usd": round(delta_cost, 6),
                            "subagent_usd": round(rem_usd, 6), "main_calls": len(main_calls),
                            "subagent_msgs": len(sub_snap)}
    out["stage_at_end"] = stage
    out["tools_main"] = dict(tools_main)
    out["tools_sub"] = dict(tools_sub)
    out["tool_calls"] = sum(tools_main.values()) + sum(tools_sub.values())
    out["skills"] = skills
    out["hooks"] = hooks
    out["files_touched"] = sorted(files)
    out["permission_denials"] = [{"tool": d.get("tool_name"), "input": json.dumps(d.get("tool_input"))[:200]}
                                 for d in denials]
    out["stream_lines"] = len(lines)
    return out
