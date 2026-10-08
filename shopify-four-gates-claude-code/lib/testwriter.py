"""Gate 1 test writer: an independent headless Sonnet 5.5 that sees ONLY the task prompt (plus read-only access to a
pristine upstream copy) and writes integration-style pytest cases. The file lives OUTSIDE the work copy, in
<out dir>/gate_tests/ next to a copy of hidden/conftest.py (TINYDB_TREE) and hidden/pytest.ini.

CLI: testwriter.py <task id> <out dir>   -> writes <out dir>/gate_tests/test_<T>.py and <out dir>/testwriter.json
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BENCH, HIDDEN, PY, counts, env_clean, sh  # noqa: E402

MODEL = "claude-sonnet-5-5"
CALL_TIMEOUT = 600
SCHEMA = {"type": "object", "properties": {"file": {"type": "string"}}, "required": ["file"]}
FRAMING = ("You are a senior engineer writing acceptance tests for a change request to tinydb, a small Python document "
           "database. You can read the CURRENT repository (before the change) with Read, Grep and Glob to learn the API; "
           "you cannot run code. The change is not implemented yet: your tests must describe the requested behaviour.")
ASK = ("Write integration-style pytest cases for this request against the tinydb API, one test per behaviour a careful "
       "senior would expect, pushing for edge cases beyond the happy path (missing fields, wrong types, boundaries, "
       "persistence, cache, existing behaviour unchanged). Tests only, no implementation. Return the file content.\n"
       "Constraints: one self-contained pytest module (field `file`); `tinydb` is importable (the tree under test is put "
       "first on sys.path); do not import anything from the repo's tests/ directory or its fixtures; use "
       "tinydb.storages.MemoryStorage or pytest's tmp_path for files; import the new API inside each test, not at module "
       "level, so one missing name fails its tests instead of the whole module; give every test a descriptive name.")


def write(task, out_dir, attempts=2):
    gt = os.path.join(out_dir, "gate_tests")
    os.makedirs(gt, exist_ok=True)
    shutil.copy(os.path.join(HIDDEN, "conftest.py"), gt)
    shutil.copy(os.path.join(HIDDEN, "pytest.ini"), gt)
    task_prompt = open(os.path.join(BENCH, "tasks", task + ".md")).read().strip()
    prompt = "%s\n\n## The request (as the developer typed it)\n%s\n\n%s" % (FRAMING, task_prompt, ASK)
    rec = {"task": task, "attempts": [], "cost_usd": 0.0, "ok": False, "file": None}
    pristine = tempfile.mkdtemp(prefix="gb-writer-")
    try:
        shutil.copytree(os.path.join(BENCH, "upstream"), os.path.join(pristine, "tinydb-repo"), symlinks=True)
        cwd = os.path.join(pristine, "tinydb-repo")
        for i in range(attempts):
            t0 = time.time()
            a = {"error": None}
            args = ["claude", "-p", prompt, "--model", MODEL, "--tools", "Read,Grep,Glob", "--max-turns", "12",
                    "--output-format", "json", "--json-schema", json.dumps(SCHEMA), "--permission-mode", "dontAsk",
                    "--setting-sources", "", "--settings", '{"disableAllHooks":true}', "--strict-mcp-config"]
            env = env_clean({"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"})
            try:
                p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, timeout=CALL_TIMEOUT, env=env)
                r = json.loads(p.stdout.decode("utf-8", "replace"))
                a.update(cost_usd=r.get("total_cost_usd") or 0.0, turns=r.get("num_turns"),
                         models=sorted((r.get("modelUsage") or {}).keys()), subtype=r.get("subtype"))
                so = r.get("structured_output")
                src = so.get("file") if isinstance(so, dict) else None
                if r.get("is_error") or not src:
                    a["error"] = "is_error=%s subtype=%s terminal=%s" % (r.get("is_error"), r.get("subtype"),
                                                                       r.get("terminal_reason"))
                else:
                    compile(src, "test_%s.py" % task, "exec")
                    if "def test_" not in src:
                        raise ValueError("no test functions")
                    open(os.path.join(gt, "test_%s.py" % task), "w").write(src)
                    rec["ok"], rec["file"] = True, os.path.join(gt, "test_%s.py" % task)
            except subprocess.TimeoutExpired:
                a["error"] = "timeout after %ss" % CALL_TIMEOUT
            except Exception as e:
                a["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
            a["wall_s"] = round(time.time() - t0, 1)
            rec["attempts"].append(a)
            rec["cost_usd"] += a.get("cost_usd") or 0.0
            if rec["ok"]:
                break
    finally:
        shutil.rmtree(pristine, ignore_errors=True)
    rec["cost_usd"] = round(rec["cost_usd"], 6)
    rec["wall_s"] = round(sum(a["wall_s"] for a in rec["attempts"]), 1)
    rec["models"] = sorted({m for a in rec["attempts"] for m in a.get("models") or []})
    json.dump(rec, open(os.path.join(out_dir, "testwriter.json"), "w"), indent=2)
    return rec


def run_gate_tests(gate_dir, task, tree, timeout=300):
    """Generated tests on `tree` (TINYDB_TREE = tree, cwd = tree). Returns (rc, out, passed, failed, failed_names).
    Paths to the gate_tests dir are rewritten to `acceptance/` so the agent never learns where the file is."""
    f = os.path.join(gate_dir, "test_%s.py" % task)
    rc, out = sh([PY, "-m", "pytest", "-q", "--tb=short", "-rfE", "--no-header", "-c", os.path.join(gate_dir, "pytest.ini"),
                  "--rootdir", gate_dir, f], tree, timeout=timeout, env=env_clean({"TINYDB_TREE": tree}))
    out = out.replace(os.path.realpath(gate_dir), "acceptance").replace(gate_dir, "acceptance")
    rel = os.path.relpath(gate_dir, tree)
    out = out.replace(rel, "acceptance")
    import re
    names = sorted(set(re.findall(r"(?:FAILED|ERROR) \S*::(test_\w+)", out)))
    p, fl = counts(out)
    if rc != 0 and fl == 0:
        fl = max(1, len(names))
    return rc, out, p, fl, names


if __name__ == "__main__":
    r = write(sys.argv[1], os.path.abspath(sys.argv[2]))
    print(json.dumps({k: r[k] for k in ("task", "ok", "cost_usd", "wall_s", "file")}))
