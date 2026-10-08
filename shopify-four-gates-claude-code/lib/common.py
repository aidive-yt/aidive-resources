"""Shared helpers: work-copy diff, pytest runs and parsing. Used by hook.py, review.py, finalize.py."""
import os
import re
import subprocess

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(BENCH, ".venv", "bin", "python")
HIDDEN = os.path.join(BENCH, "hidden")


def sh(args, cwd, timeout=None, env=None):
    """Run a command, capture stdout+stderr together. Returns (rc, text). rc=124 on timeout."""
    try:
        p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, timeout=timeout, env=env)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace")
        return 124, out + "\n[timed out after %ss]" % timeout


def work_diff(work):
    """`git diff HEAD` of tracked files plus every untracked (non-ignored) file as a new-file diff.
    Never touches the index (no `git add -N`), so the agent's `git status` is unaffected."""
    _, d = sh(["git", "diff", "HEAD", "--no-color", "--", ".", ":(exclude).coverage"], work)
    _, others = sh(["git", "ls-files", "--others", "--exclude-standard"], work)
    for f in [l for l in others.splitlines() if l.strip()]:
        _, nd = sh(["git", "diff", "--no-color", "--no-index", "--", "/dev/null", f], work)
        d += nd
    return d


def tests_touched(work):
    _, mod = sh(["git", "diff", "HEAD", "--name-only", "--", "tests"], work)
    _, new = sh(["git", "ls-files", "--others", "--exclude-standard", "--", "tests"], work)
    return bool(mod.strip() or new.strip())


def counts(txt):
    """(passed, failed+errors) from a pytest summary line."""
    p = re.findall(r"(\d+) passed", txt)
    f = re.findall(r"(\d+) failed", txt)
    e = re.findall(r"(\d+) errors?\b", txt)
    return (int(p[-1]) if p else 0), (int(f[-1]) if f else 0) + (int(e[-1]) if e else 0)


def env_clean(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and not k.startswith("GATE_")}
    env["PATH"] = os.path.join(BENCH, ".venv", "bin") + os.pathsep + env.get("PATH", "/usr/bin:/bin")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


def run_suite(work, timeout=300):
    """Gate 1 / final suite: the repo's own pytest run (226 tests + whatever the agent wrote).
    --no-cov: the repo's pytest.ini adds --cov; the coverage table would fill the 40-line tail."""
    rc, out = sh([PY, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider", "--no-cov"],
                 work, timeout=timeout, env=env_clean())
    p, f = counts(out)
    if rc != 0 and f == 0:
        f = 1  # collection error, timeout, crash: count as red
    return rc, out, p, f


def run_hidden(work, task, timeout=300):
    """Ground truth: hidden tests on the work copy (cwd = work copy, TINYDB_TREE set). Output never reaches the agent."""
    rc, out = sh([PY, "-m", "pytest", "-q", "-rA", "-c", os.path.join(HIDDEN, "pytest.ini"), "--rootdir", HIDDEN,
                  os.path.join(HIDDEN, "test_%s.py" % task)],
                 work, timeout=timeout, env=env_clean({"TINYDB_TREE": work}))
    # Requirement level (T5 R4 is parametrized: one req = several test ids). A req passes iff none of its
    # test ids failed or errored; a run that collected nothing counts every req as failed.
    reqs = sorted(set(re.findall(r"^def (test_req\d+)", open(os.path.join(HIDDEN, "test_%s.py" % task)).read(), re.M)))
    failed = sorted(set(re.findall(r"(?:FAILED|ERROR) \S+::(test_req\d+)", out)))
    p_tests, f_tests = counts(out)
    if rc != 0 and not failed:
        failed = list(reqs)
    if p_tests == 0 and f_tests == 0:
        failed = list(reqs)
    return rc, out, len(reqs) - len(failed), len(failed), failed
