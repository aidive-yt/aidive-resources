#!/usr/bin/env bash
# Validation of the gate-1 test writer: one writer call per task (in parallel) into validation/writer/<T>/,
# then its tests on upstream and on the reference patch. Usage: validate_writer.sh [T1 ...]  (reuses an existing
# file unless REWRITE=1). Appends to validation.log.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
. "$HERE/env.sh"
PY="$HERE/.venv/bin/python"
TASKS="${*:-T1 T2 T3 T4 T5}"
for t in $TASKS; do
  D="$HERE/validation/writer/$t"; mkdir -p "$D"
  if [ "${REWRITE:-0}" = 1 ] || [ ! -f "$D/gate_tests/test_$t.py" ]; then "$PY" lib/testwriter.py "$t" "$D" > "$D/writer.out" 2>&1 & fi
done
wait
TMP="$(mktemp -d "${TMPDIR:-/tmp}/gb-vw.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
echo "=== $(date '+%F %T') validate_writer.sh $TASKS" >> validation.log
for t in $TASKS; do
  D="$HERE/validation/writer/$t"
  git clone -q "$HERE/upstream" "$TMP/up-$t"; git clone -q "$HERE/upstream" "$TMP/ref-$t"
  (cd "$TMP/ref-$t" && git apply "$HERE/reference/$t.patch")
  line=$("$PY" - "$D" "$t" "$TMP/up-$t" "$TMP/ref-$t" <<'PY'
import json, os, sys
sys.path.insert(0, "lib")
from testwriter import run_gate_tests
d, t, up, ref = sys.argv[1:5]
w = json.load(open(os.path.join(d, "testwriter.json")))
if not w["ok"]:
    print("%s: writer FAILED %s" % (t, [a["error"] for a in w["attempts"]])); sys.exit()
g = os.path.join(d, "gate_tests")
_, uo, up_p, up_f, _ = run_gate_tests(g, t, up)
_, ro, rp, rf, rnames = run_gate_tests(g, t, ref)
open(os.path.join(d, "on-upstream.txt"), "w").write(uo); open(os.path.join(d, "on-reference.txt"), "w").write(ro)
print("%s: writer tests: %d, pass on reference: %d, pass on upstream: %d | fail on reference: %s | writer $%.3f %ss turns=%s" % (
    t, rp + rf, rp, up_p, rnames, w["cost_usd"], w["wall_s"], [a.get("turns") for a in w["attempts"]]))
PY
)
  echo "$line" | tee -a validation.log
done
