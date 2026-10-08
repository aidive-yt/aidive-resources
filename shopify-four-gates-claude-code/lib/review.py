"""Gate 3 reviewers: headless `claude -p` calls returning schema-validated JSON.

CLI (validation step 4):  review.py <work dir> <task id> [indep|adv]   -> prints the gate3 record as JSON
"""
import json
import subprocess
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BENCH, env_clean, sh, work_diff  # noqa: E402

MODEL = "claude-sonnet-5-5"
DIFF_CAP = 60000
CALL_TIMEOUT = 600  # seconds per reviewer call; the hook timeout is 1500

FINDING = {"type": "object",
           "properties": {"severity": {"type": "string", "enum": ["blocking", "minor"]},
                          "file": {"type": "string"}, "line": {"type": "integer"}, "text": {"type": "string"}},
           "required": ["severity", "file", "line", "text"]}
SCHEMA_REVIEW = {"type": "object",
                 "properties": {"approve": {"type": "boolean"}, "findings": {"type": "array", "items": FINDING}},
                 "required": ["approve", "findings"]}
SCHEMA_CHALLENGE = {"type": "object",
                    "properties": {
                        "verdicts": {"type": "array", "items": {
                            "type": "object",
                            "properties": {"id": {"type": "integer"},
                                           "verdict": {"type": "string", "enum": ["upheld", "rejected"]},
                                           "reason": {"type": "string"}},
                            "required": ["id", "verdict", "reason"]}},
                        "added_findings": {"type": "array", "items": FINDING},
                        "approve": {"type": "boolean"}},
                    "required": ["verdicts", "added_findings", "approve"]}

FRAMING = ("You are a senior engineer doing a pre-merge code review of a change to tinydb, a small Python "
           "document database. You can read the repository with Read, Grep and Glob (cwd = the repo with the "
           "change applied). You cannot run code. Below: the task the developer was given, then the full diff "
           "(tracked and new files).")
ASK = ("Find defects: requirements not met, edge cases wrong, behaviour broken, tests that do not test the "
       "requirement. Report only real defects with file and line. approve=true only when nothing blocks.")


def capped_diff(work):
    d = work_diff(work)
    if len(d) > DIFF_CAP:
        d = d[:DIFF_CAP] + "\n[diff truncated at %d chars]\n" % DIFF_CAP
    return d


def call(work, prompt, schema, rid):
    """One headless reviewer. Never raises: an error is recorded and counts as approve (fail open)."""
    # Equivalent of --bare that still authenticates with the user's OAuth login (--bare reads
    # ANTHROPIC_API_KEY only): no settings sources, hooks disabled, no MCP, no CLAUDE.md, no auto-memory.
    args = ["claude", "-p", prompt, "--model", MODEL, "--tools", "Read,Grep,Glob", "--max-turns", "15",
            "--output-format", "json", "--json-schema", json.dumps(schema), "--permission-mode", "dontAsk",
            "--setting-sources", "", "--settings", '{"disableAllHooks":true}', "--strict-mcp-config"]
    env = env_clean({"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"})
    t0 = time.time()
    rec = {"id": rid, "approve": True, "findings": [], "cost_usd": 0.0, "turns": None, "wall_s": None, "error": None}
    try:
        try:
            p = subprocess.run(args, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                               timeout=CALL_TIMEOUT, env=env)
        except OSError as e1:  # seen once in a smoke run: transient FileNotFoundError on spawn -> one retry
            rec["retry_after"] = "%r filename=%s" % (e1, getattr(e1, "filename", None))
            time.sleep(3)
            p = subprocess.run(args, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                           timeout=CALL_TIMEOUT, env=env)
        out = p.stdout.decode("utf-8", "replace")
        try:
            r = json.loads(out)
        except Exception:
            r = None
        if not isinstance(r, dict):
            rec["error"] = "no json (rc=%s): %s %s" % (p.returncode, out[-300:], p.stderr.decode("utf-8", "replace")[-300:])
        else:
            rec["cost_usd"] = r.get("total_cost_usd") or 0.0
            rec["turns"] = r.get("num_turns")
            rec["models"] = sorted((r.get("modelUsage") or {}).keys())
            so = r.get("structured_output")
            if r.get("is_error") or not isinstance(so, dict):
                rec["error"] = "is_error=%s subtype=%s terminal=%s structured_output=%s" % (
                    r.get("is_error"), r.get("subtype"), r.get("terminal_reason"), type(so).__name__)
            else:
                rec["raw"] = so
    except subprocess.TimeoutExpired:
        rec["error"] = "timeout after %ss" % CALL_TIMEOUT
    except Exception as e:  # pragma: no cover
        rec["error"] = "exception: %r filename=%s path_head=%s" % (e, getattr(e, "filename", None), os.environ.get("PATH", "")[:200])
    rec["wall_s"] = round(time.time() - t0, 1)
    return rec


def norm_findings(lst):
    out = []
    for f in lst or []:
        if isinstance(f, dict):
            out.append({"severity": f.get("severity") if f.get("severity") in ("blocking", "minor") else "minor",
                        "file": str(f.get("file", "")), "line": f.get("line"), "text": str(f.get("text", ""))})
    return out


def review_prompt(task_prompt, diff):
    return "%s\n\n## Task given to the developer\n%s\n\n## Diff (git diff HEAD, new files included)\n```diff\n%s\n```\n\n%s" % (
        FRAMING, task_prompt.strip(), diff, ASK)


def challenge_prompt(task_prompt, diff, a_findings):
    listing = "\n".join("[%d] (%s) %s:%s %s" % (i + 1, f["severity"], f["file"], f["line"], f["text"])
                        for i, f in enumerate(a_findings)) or "(reviewer A reported no findings)"
    return ("%s\n\nA first reviewer (A) already reviewed this diff. You are the challenger: for EACH of A's findings "
            "decide whether it is a real defect (upheld) or not (rejected: wrong, not required by the task, already "
            "handled, or speculative), with a one-sentence reason grounded in the code; check the code before you "
            "decide. Then add any real blocking defect A missed in added_findings (file and line). approve=true only "
            "when no upheld or added finding blocks.\n\n## Task given to the developer\n%s\n\n## Diff (git diff HEAD, "
            "new files included)\n```diff\n%s\n```\n\n## Reviewer A's findings (id in brackets)\n%s\n\n%s" % (
                FRAMING, task_prompt.strip(), diff, listing,
                "Answer every id in verdicts. Report only real defects."))


def gate3(work, task_prompt, variant):
    diff = capped_diff(work)
    reviewers, blocking = [], []
    if variant == "indep":
        prompt = review_prompt(task_prompt, diff)
        with ThreadPoolExecutor(max_workers=2) as ex:
            recs = list(ex.map(lambda rid: call(work, prompt, SCHEMA_REVIEW, rid), ["A", "B"]))
        for rec in recs:
            raw = rec.pop("raw", None) or {}
            rec["findings"] = norm_findings(raw.get("findings"))
            rec["approve_raw"] = raw.get("approve", True) if not rec["error"] else None
            rb = [f for f in rec["findings"] if f["severity"] == "blocking"]
            rec["approve"] = not rb  # effective verdict = no blocking finding (an errored call approves)
            blocking += [dict(f, by=rec["id"]) for f in rb]
            reviewers.append(rec)
    elif variant == "adv":
        a = call(work, review_prompt(task_prompt, diff), SCHEMA_REVIEW, "A")
        raw = a.pop("raw", None) or {}
        a["findings"] = norm_findings(raw.get("findings"))
        a["approve_raw"] = raw.get("approve", True) if not a["error"] else None
        a["approve"] = not [f for f in a["findings"] if f["severity"] == "blocking"]
        b = call(work, challenge_prompt(task_prompt, diff, a["findings"]), SCHEMA_CHALLENGE, "B")
        rawb = b.pop("raw", None) or {}
        verdicts = {}
        for v in rawb.get("verdicts") or []:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                verdicts[v["id"]] = {"verdict": v.get("verdict"), "reason": str(v.get("reason", ""))}
        b["verdicts"] = [dict(id=k, **verdicts[k]) for k in sorted(verdicts)]
        b["findings"] = norm_findings(rawb.get("added_findings"))
        b["approve_raw"] = rawb.get("approve", True) if not b["error"] else None
        # Only upheld findings of A block. An errored challenger upholds nothing (fail open, logged).
        for i, f in enumerate(a["findings"]):
            v = verdicts.get(i + 1)
            f["challenge"] = v["verdict"] if v else ("error" if b["error"] else "unanswered")
            if f["severity"] == "blocking" and v and v["verdict"] == "upheld":
                blocking.append(dict(f, by="A", upheld_by="B"))
        blocking += [dict(f, by="B") for f in b["findings"] if f["severity"] == "blocking"]
        b["approve"] = not blocking
        reviewers = [a, b]
    else:
        raise ValueError(variant)
    return {"ran": True, "variant": variant, "reviewers": reviewers, "blocking_findings": len(blocking),
            "blocking": blocking, "pass": not blocking,
            "cost_usd": round(sum(r.get("cost_usd") or 0 for r in reviewers), 6), "diff_chars": len(diff)}


def reason_text(g3):
    lines = ["Code review found %d blocking defect(s):" % g3["blocking_findings"]]
    for i, f in enumerate(g3["blocking"]):
        lines.append("%d. %s:%s %s" % (i + 1, f["file"], f["line"], " ".join(f["text"].split())))
    tail = "Fix every finding, re-run the tests, then stop."
    body = "\n".join(lines)
    room = 1500 - len(tail) - 2
    if len(body) > room:
        body = body[:room - 4] + " ..."
    return body + "\n" + tail


if __name__ == "__main__":
    work, task = sys.argv[1], sys.argv[2]
    variant = sys.argv[3] if len(sys.argv) > 3 else "indep"
    tp = open(os.path.join(BENCH, "tasks", task + ".md")).read()
    g3 = gate3(os.path.abspath(work), tp, variant)
    print(json.dumps(g3, indent=2))
    if not g3["pass"]:
        print("--- reason ---\n" + reason_text(g3))
