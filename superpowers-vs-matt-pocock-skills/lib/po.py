"""Product-owner simulator: a headless Sonnet 5.5 with NO tools that read po/F1-brief.md and answers the worker.

    po.py <run dir> <turn n> <flow> <stage> <last message file>   -> prints one JSON line, writes po-<n>.json

Output: {"kind": "question" | "waiting" | "done", "reply": str, "cost_usd", "wall_s", "error", "heuristic_question"}
- question: the worker asks the user something (a question, options, an approval request) -> reply answers it
- waiting:  it stopped without asking (announced a next step, paused between phases)      -> driver sends "go on"
- done:     it reports the whole change finished                                          -> driver stops (bare/sp)
Isolation (same as the previous benches' reviewers): --setting-sources "", disableAllHooks, --strict-mcp-config,
--tools "", CLAUDE_CODE_DISABLE_CLAUDE_MDS=1, CLAUDE_CODE_DISABLE_AUTO_MEMORY=1, scrubbed CLAUDE* env,
cwd = an empty temp dir (never the work copy).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "claude-sonnet-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["question", "waiting", "done"]},
        "reply": {"type": "string"},
    },
    "required": ["kind", "reply"],
    "additionalProperties": False,
}

FLOW_NOTE = {
    "bare": "The assistant was asked to implement the request and stop with a summary when done.",
    "sp": "The assistant runs a process (brainstorm -> design -> written plan -> execution -> review -> finish). "
          "It often stops to ask for approval of a design, a spec or a plan, or to ask how to finish the branch.",
    "spd": "You are driving the assistant through the Superpowers stages by slash command, one stage at a time "
           "(brainstorming -> writing-plans -> executing-plans); the current stage is shown below and YOU send the "
           "next command once a stage is over. RULE FOR THIS FLOW: when the stage's output is delivered (a design "
           "approved and written, a plan saved) and the assistant only asks you to approve it or whether to proceed, "
           "answer what is open (approve it; if asked for an execution approach, choose Native / inline in this "
           "session; consent to working on the current branch) and classify it kind=question only if something "
           "beyond approval is open, otherwise kind=done. Never tell it to start implementing yourself before the "
           "executing-plans stage. During executing-plans, approve its rulings and ask it to finish.",
    "mp": "You are driving the assistant through slash commands, one stage at a time (grill -> spec -> tickets -> "
          "implement -> code review -> PR); the current stage is shown below and YOU send the next command once "
          "a stage is over. Interviews (grilling) come in rounds of numbered questions with a recommended answer "
          "each. RULE FOR THIS FLOW: when the stage's output is delivered and the assistant only asks whether to "
          "proceed, start building, move on, or confirms its own summary ('Ready to write the spec?', 'Shall I "
          "start?', 'Does this capture it?' after a full recap), that is kind=done with an empty reply: the next "
          "slash command will follow. Never tell it to start implementing or to move to another phase yourself; "
          "answer only the open design questions. Before the /implement stage, if the assistant offers to build "
          "next, end your reply with: \"Don't start implementing yet.\"",
}


def heuristic_question(text):
    """SPEC's driver rule: a turn that ends on a question mark or an explicit options list."""
    tail = (text or "").strip()[-600:]
    if tail.rstrip("*_` \n").endswith("?"):
        return True
    lines = [l.strip() for l in tail.splitlines() if l.strip()]
    opts = [l for l in lines[-8:] if re.match(r"^(\(?[A-Da-d1-4][\).:]|[-*] \*\*Option)", l)]
    return len(opts) >= 2 or "?" in "\n".join(lines[-3:])


def ask(run_dir, n, flow, stage, last_text, task="F1"):
    brief = open(os.path.join(BENCH, "po", "%s-brief.md" % task)).read()
    prompt = (
        "You play the developer who asked a coding assistant for a change in your repo. You are busy: you answer "
        "tersely (1 to 6 short sentences or a short numbered list), the way a dev types in a chat. You never write "
        "code, never mention how you will check the work, never invent requirements beyond your brief. You answer "
        "ONLY what the assistant asked: never volunteer a requirement, an edge case or a constraint it did not ask "
        "about (a question it asked is fair game, even a broad one like 'anything else I should know?').\n\n"
        "=== YOUR BRIEF (private, the assistant has not seen it) ===\n" + brief + "\n=== END BRIEF ===\n\n"
        + FLOW_NOTE.get(flow, "") + "\nCurrent stage: " + stage + "\n\n"
        "=== THE ASSISTANT'S LAST MESSAGE (it is now waiting for you) ===\n" + (last_text or "(empty message)")[-12000:]
        + "\n=== END MESSAGE ===\n\n"
        "Classify the message and write your reply:\n"
        "- kind=question when it asks you anything or waits for a decision or an approval (numbered questions, "
        "options, 'does this look right?', 'shall I proceed?'). Reply by answering EVERY open question in one go, "
        "from your brief; where your brief is silent, accept the assistant's recommendation or say 'your call'. "
        "Approve designs, specs, plans and ticket breakdowns that match your brief; correct only what contradicts it. "
        "If it asks how to finish a branch (merge, PR, keep), say: keep it on the current branch, no PR, done. "
        "If a code review it ran lists real defects, tell it to fix them.\n"
        "- kind=waiting when it stopped without asking anything but the work is not finished (it announced a next "
        "step, or paused between phases). Reply: 'go on'.\n"
        "- kind=done when it reports the change finished (implemented, tests run) or, for a slash-command stage, "
        "when that stage's output is delivered and nothing is asked. Reply: ''.\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update({"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--tools", "", "--max-turns", "4", "--permission-mode", "dontAsk", "--setting-sources", "",
           "--settings", '{"disableAllHooks":true}', "--strict-mcp-config"]
    out = {"kind": None, "reply": "", "cost_usd": 0.0, "wall_s": 0.0, "error": None,
           "heuristic_question": heuristic_question(last_text)}
    t0 = time.time()
    for attempt in range(2):
        try:
            with tempfile.TemporaryDirectory(prefix="po-") as cwd:
                p = subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                   text=True, timeout=300)
            res = json.loads(p.stdout.strip().splitlines()[-1])
            out["cost_usd"] += res.get("total_cost_usd") or 0.0
            out["models"] = sorted((res.get("modelUsage") or {}).keys())
            so = res.get("structured_output")
            if isinstance(so, str):
                so = json.loads(so)
            if not so or so.get("kind") not in ("question", "waiting", "done"):
                raise ValueError("no structured_output: %s" % (res.get("result") or "")[:300])
            out["kind"], out["reply"], out["error"] = so["kind"], so["reply"].strip(), None
            break
        except Exception as e:  # noqa: BLE001
            out["error"] = "%s: %s" % (type(e).__name__, e)
            time.sleep(3)
    if out["kind"] is None:  # PO failed twice: fall back on the SPEC heuristic
        out["kind"] = "question" if out["heuristic_question"] else "waiting"
        out["reply"] = "Your call on all of these; go on." if out["kind"] == "question" else "go on"
        out["fallback"] = True
    if out["kind"] == "waiting" and not out["reply"]:
        out["reply"] = "go on"
    out["wall_s"] = round(time.time() - t0, 2)
    json.dump(dict(out, n=n, stage=stage, prompt_chars=len(prompt)), open(os.path.join(run_dir, "po-%02d.json" % n), "w"),
              indent=2)
    return out


if __name__ == "__main__":
    rd, n, flow, stage, f = sys.argv[1:6]
    print(json.dumps(ask(rd, int(n), flow, stage, open(f).read(), os.environ.get("TASK", "F1"))))
