#!/usr/bin/env bash
# Validation before the matrix (SPEC § Validation). Steps 1, 3, 4 here; step 2 = the g1 red-start smoke run:
#   INJECT=$PWD/inject/break.patch RUN_TAG=val2 ./run.sh g1 T1 1     (then: ./validate.sh step2)
# Usage: validate.sh [all|step1|step2|step3|step4]   -> appends to validation.log
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
. "$HERE/env.sh"
PY="$HERE/.venv/bin/python"
STEP="${1:-all}"
status=0
count() { grep -Eo "[0-9]+ $2" <<<"$1" | tail -1 | awk '{print $1}'; }
log() { echo "$*" | tee -a validation.log; }
log "=== $(date '+%F %T') validate.sh $STEP  ($(claude --version))"

if [ "$STEP" = all ] || [ "$STEP" = step1 ]; then
  # 1. upstream fails the hidden tests (<= 1 req passing: T5 R3 is a regression guard); reference passes hidden + suite
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/gb-validate.XXXXXX")"
  for t in T1 T2 T3 T4 T5; do
    tree="$TMP/$t"; git clone -q "$HERE/upstream" "$tree"
    v=$(cd "$tree" && TINYDB_TREE="$tree" "$PY" -m pytest -v -c "$HERE/hidden/pytest.ini" --rootdir "$HERE/hidden" "$HERE/hidden/test_$t.py" 2>&1)
    up_pass=$(grep -Eo "test_req[0-9]+[^ ]* PASSED" <<<"$v" | wc -l | tr -d ' ')
    (cd "$tree" && git apply "$HERE/reference/$t.patch") || { log "$t: reference patch does not apply"; status=1; continue; }
    h=$(cd "$tree" && TINYDB_TREE="$tree" "$PY" -m pytest -q -c "$HERE/hidden/pytest.ini" --rootdir "$HERE/hidden" "$HERE/hidden/test_$t.py" 2>&1); hrc=$?
    s=$(cd "$tree" && "$PY" -m pytest -q -p no:cacheprovider --no-cov 2>&1); src=$?
    ok=OK; { [ "$up_pass" -gt 1 ] || [ $hrc -ne 0 ] || [ $src -ne 0 ]; } && { ok=FAIL; status=1; }
    log "step1 $t: upstream reqs passing=$up_pass  reference hidden rc=$hrc ($(count "$h" passed) passed)  suite rc=$src ($(count "$s" passed) passed)  [$ok]"
  done
  rm -rf "$TMP"
fi

if [ "$STEP" = all ] || [ "$STEP" = step3 ]; then
  # 3. gate.sh by hand, fake stdin. green = T1 reference + one new test (g1 passes) -> exit 0 allow;
  #    red = break.patch (one repo test fails) -> exit 2, pytest tail on stderr.
  FAKE='{"session_id":"validate","transcript_path":"/dev/null","cwd":"x","hook_event_name":"Stop","stop_hook_active":false}'
  for k in green red; do
    R="$HERE/runs/_val3-$k"; W="$HERE/work/_val3-$k"; rm -rf "$R"; mkdir -p "$R"
    ./prep.sh g1 "$W" "$R" > /dev/null
    if [ $k = green ]; then
      (cd "$W" && git apply "$HERE/reference/T1.patch" && cp "$HERE/inject/test_pushpull.py" tests/)
    else
      (cd "$W" && git apply "$HERE/inject/break.patch")
    fi
    printf '{"task":"T1","cfg":"g1","rep":0,"work":"%s","name":"_val3-%s"}\n' "$W" "$k" > "$R/meta.json"; cp tasks/T1.md "$R/task.md"
    echo "$FAKE" | GATE_RUN="$R" GATE_CONFIG=g1 bash gate.sh > "$R/stdout.txt" 2> "$R/stderr.txt"; rc=$?
    dec=$("$PY" -c "import json;print(json.loads(open('$R/gate.jsonl').readline())['decision'])")
    want=0; [ $k = red ] && want=2
    ok=OK; [ $rc -ne $want ] && { ok=FAIL; status=1; }
    [ $k = red ] && ! grep -q "short test summary" "$R/stderr.txt" && { ok=FAIL; status=1; }
    [ $k = green ] && [ -s "$R/stderr.txt" ] && { ok=FAIL; status=1; }
    log "step3 $k: exit=$rc decision=$dec stderr_bytes=$(wc -c < "$R/stderr.txt" | tr -d ' ') [$ok]"
  done
fi

if [ "$STEP" = all ] || [ "$STEP" = step4 ]; then
  # 4. one reviewer pair by hand on the green copy (needs step3's work/_val3-green): structured_output valid
  W="$HERE/work/_val3-green"
  [ -d "$W" ] || { log "step4: run step3 first"; exit 1; }
  for v in indep adv; do
    "$PY" lib/review.py "$W" T1 $v > "runs/_val3-green/review-$v.txt" 2>&1
    s=$("$PY" - "runs/_val3-green/review-$v.txt" <<'PY'
import json, sys
t = open(sys.argv[1]).read(); i = t.find("--- reason"); d = json.loads(t[:i] if i > 0 else t)
ok = all(r["error"] is None and isinstance(r["approve_raw"], bool) for r in d["reviewers"])
ok = ok and all(f["severity"] in ("blocking", "minor") and isinstance(f["line"], int) for r in d["reviewers"] for f in r["findings"])
print("%s pass=%s blocking=%d findings=%s cost=$%.4f wall=%s" % ("OK" if ok else "FAIL", d["pass"], d["blocking_findings"],
      [len(r["findings"]) for r in d["reviewers"]], d["cost_usd"], [r["wall_s"] for r in d["reviewers"]]))
PY
)
    case "$s" in OK*) ;; *) status=1 ;; esac
    log "step4 $v: $s"
  done
fi

if [ "$STEP" = all ] || [ "$STEP" = step2 ]; then
  # 2. hook fires on a red start: runs/T1-g1-r1-val2 must log a block and the stream must show the agent continuing
  R="$HERE/runs/T1-g1-r1-val2"
  if [ -f "$R/gate.jsonl" ]; then
    s=$("$PY" - "$R" <<'PY'
import json, sys, os
r = sys.argv[1]
g = [json.loads(l) for l in open(os.path.join(r, "gate.jsonl")) if l.strip()]
st = [json.loads(l) for l in open(os.path.join(r, "stream.jsonl")) if l.startswith("{")]
blocks = [x for x in g if x["decision"] == "block"]
# index in the stream of the first hook response that blocked, then any assistant tool_use after it
txt = [json.dumps(o) for o in st]
fb = next((i for i, t in enumerate(txt) if "Stop hook feedback" in t or ('"hook_event": "Stop"' in t and '"exit_code": 2' in t)), None)
after = fb is not None and any(o.get("type") == "assistant" for o in st[fb + 1:])
print("%s blocks=%d hook_calls=%d feedback_idx=%s assistant_after=%s last=%s" % (
    "OK" if blocks and after else "FAIL", len(blocks), len(g), fb, after, g[-1]["decision"] if g else None))
PY
)
    case "$s" in OK*) ;; *) status=1 ;; esac
    log "step2: $s"
  else
    log "step2: not run yet (INJECT=\$PWD/inject/break.patch RUN_TAG=val2 ./run.sh g1 T1 1)"
  fi
fi
[ $status -eq 0 ] && log "VALIDATION OK" || log "VALIDATION FAILED"
exit $status
