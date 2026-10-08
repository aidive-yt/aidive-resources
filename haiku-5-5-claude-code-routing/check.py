#!/usr/bin/env python3
"""Deterministic accept/reject check for one run.

Usage: check.py <task> <workdir> <result.json>
  result.json = the `result` line of the run's stream (only its "result" text is used).
Prints `PASS <reason>` or `FAIL <reason>`; exit 0 on PASS, 1 on FAIL.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, ".venv", "bin", "python")
RUFF = os.path.join(HERE, ".venv", "bin", "ruff")


def final_text(path):
    try:
        r = json.load(open(path))
    except Exception:
        return ""
    return r.get("result") or "" if isinstance(r, dict) else ""


def sh(args, cwd, env=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def suite(wd):
    rc, out = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "tests"], wd)
    m = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    e = re.search(r"(\d+) error", out)
    return rc == 0, f"suite {m.group(1) if m else 0} passed, {f.group(1) if f else 0} failed, {e.group(1) if e else 0} errors"


def git_diff(wd, *paths):
    # tracked changes vs the baseline commit + untracked files under paths
    _, d = sh(["git", "diff", "HEAD", "--", *paths], wd)
    _, u = sh(["git", "ls-files", "--others", "--exclude-standard", "--", *paths], wd)
    return d.strip(), u.strip()


def words(s):
    return re.findall(r"[A-Za-z0-9_']+", s)


def strip_fences(s):
    lines = s.strip().split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def c_explore(wd, txt):
    t = txt.lower()
    miss = []
    if "table.py" not in t:
        miss.append("table.py")
    if "clear_cache" not in t and "_query_cache" not in t:
        miss.append("clear_cache/_query_cache")
    names = ["insert_multiple", "update_multiple", "insert", "update", "upsert", "remove", "truncate"]
    found = {n for n in names if re.search(r"(?<![a-z_])" + n + r"(?![a-z_])", t)}
    if len(found) < 3:
        miss.append(f"only {len(found)} mutating methods {sorted(found)}")
    return (not miss), ("missing " + ", ".join(miss)) if miss else f"table.py + cache method + {len(found)} methods {sorted(found)}"


def c_tests(wd, txt):
    ok, s = suite(wd)
    d, u = git_diff(wd, "tests")
    if d or u:
        return False, f"tests/ modified; {s}"
    return ok, s + "; tests/ untouched"


def c_lint(wd, txt):
    rc, out = sh([RUFF, "check", "tinydb", "--output-format", "concise", "--no-cache"], wd)
    cfg_d, _ = git_diff(wd, "ruff.toml", "pyproject.toml")
    d, _ = git_diff(wd, "tinydb")
    noqa = [l for l in d.split("\n") if l.startswith("+") and "noqa" in l.lower()]
    ok, s = suite(wd)
    why = []
    if rc != 0:
        found = [l for l in out.split("\n") if l.startswith("Found ")]
        why.append("ruff: " + (found[0] if found else out.strip().split("\n")[-1]))
    if cfg_d:
        why.append("lint config changed")
    if noqa:
        why.append(f"{len(noqa)} noqa added")
    if not ok:
        why.append(s)
    return (not why), ("; ".join(why) if why else f"ruff clean; {s}")


DIFF_LINE = re.compile(r"^(diff --git |index [0-9a-f]{6,}\.\.|@@ |\+\+\+ |--- a/|--- /dev/null|[+-] {3,}\S|[+-](def|class|import|from|return) )")


def c_commit(wd, txt):
    msg = strip_fences(txt)
    if not msg:
        return False, "empty answer"
    first = msg.split("\n")[0].strip()
    why = []
    if len(first) > 72:
        why.append(f"first line {len(first)} chars")
    if "push" not in first.lower():
        why.append("no 'push' in first line")
    if "pull" not in first.lower():
        why.append("no 'pull' in first line")
    dl = [l for l in msg.split("\n") if DIFF_LINE.match(l)]
    if dl:
        why.append(f"{len(dl)} diff lines")
    return (not why), ("; ".join(why) if why else f"first line {len(first)} chars: {first!r}")


def c_refactor(wd, txt):
    env = dict(os.environ, TINYDB_TREE=wd)
    rc, out = sh([PY, "-m", "pytest", "-q", "-c", os.path.join(HERE, "hidden", "pytest.ini"),
                  "--rootdir", os.path.join(HERE, "hidden"), os.path.join(HERE, "hidden", "test_T1.py")], wd, env)
    m = re.search(r"(\d+) passed", out)
    hp = int(m.group(1)) if m else 0
    ok, s = suite(wd)
    return (hp == 5 and ok), f"hidden {hp}/5; {s}"


REVIEW_PATTERNS = [
    r"limit\s*=?=\s*0\b",
    r"limit\s+(of\s+)?(0|zero)\b",
    r"\b(0|zero)\s+limit",
    r"zero[- ]limit",
    r"limit.{0,150}\b(falsy|falsey|truthy|truthiness)",
    r"\b(falsy|falsey|truthy|truthiness)\b.{0,150}limit",
    r"if limit:.{0,150}\b(0|zero)\b",
    r"\b(0|zero)\b.{0,150}if limit:",
]


def c_review(wd, txt):
    t = txt.lower().replace("`", "")
    for p in REVIEW_PATTERNS:
        m = re.search(p, t, re.S)
        if m:
            return True, f"matched {p!r}: {m.group(0)[:80]!r}"
    return False, "planted limit=0 defect not mentioned"


def c_summary(wd, txt):
    n = len(words(txt))
    t = txt.lower()
    mods = [m for m in ["database", "table", "queries", "storages", "middlewares", "operations"] if m in t]
    why = []
    if n > 170:
        why.append(f"{n} words > 170")
    if len(mods) < 4:
        why.append(f"only {len(mods)} modules {mods}")
    return (not why), ("; ".join(why) if why else f"{n} words, modules {mods}")


CHECKS = {"explore": c_explore, "tests": c_tests, "lint": c_lint, "commit": c_commit,
          "refactor": c_refactor, "review": c_review, "summary": c_summary}

if __name__ == "__main__":
    task, wd, res = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    ok, why = CHECKS[task](wd, final_text(res))
    print(("PASS " if ok else "FAIL ") + why)
    sys.exit(0 if ok else 1)
