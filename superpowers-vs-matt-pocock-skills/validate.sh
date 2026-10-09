#!/usr/bin/env bash
# The 5 validation steps of SPEC.md, appended to validation.log.
# Usage: ./validate.sh [steps]      default "1 2 3 4 5"; steps 3-5 (smoke runs, RUN_TAG=smoke) run in parallel.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
. "$HERE/env.sh"
STEPS="${*:-1 2 3 4 5}"
LOG="$HERE/validation.log"
log(){ echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

static_run(){  # <name> <patch or ""> [task] : prep a bare copy, optionally apply a patch, score it with finalize.py
  local name="$1" patch="$2" task="${3:-F1}" out="$HERE/runs/$1" w="$HERE/work/$1"
  rm -rf "$out"; mkdir -p "$out"
  local base; base=$("$HERE/prep.sh" bare "$w" | tail -1)
  if [ -n "$patch" ]; then ( cd "$w" && git apply "$patch" ) || { log "FAIL $name: git apply"; return 1; }; fi
  printf '{"task":"%s","cfg":"bare","rep":0,"tag":"validation","work":"%s","name":"%s","base":"%s"}\n' "$task" "$w" "$name" "$base" > "$out/meta.json"
  : > "$out/turns.jsonl"; echo '{"end_reason":"static"}' > "$out/driver.json"
  python3 "$HERE/lib/finalize.py" "$out"
}
check(){  # <run dir> <python expr over s (score.json)> <label>
  python3 - "$1" "$2" "$3" <<'PY'
import json, sys
s = json.load(open(sys.argv[1] + "/score.json"))
ok = eval(sys.argv[2], {"s": s})
print(("PASS " if ok else "FAIL ") + sys.argv[3])
sys.exit(0 if ok else 1)
PY
}

log "=== validate.sh steps: $STEPS (claude $(claude --version | head -1))"
for st in $STEPS; do case $st in
1) log "step 1: reference/F1.patch -> hidden 5/5, suite green, typecheck green"
   static_run val1-reference "$HERE/reference/F1.patch" | tee -a "$LOG"
   check runs/val1-reference 's["hidden_pass"]==5 and s["suite_green"] and s["typecheck_green"]' "step 1" | tee -a "$LOG" ;;
2) log "step 2: upstream unchanged -> hidden 0/5 (honest number recorded), suite green"
   static_run val2-upstream "" | tee -a "$LOG"
   check runs/val2-upstream 's["hidden_pass"]==0 and s["suite_green"] and s["suite_total"]==34' "step 2" | tee -a "$LOG" ;;
f2-1) log "F2 step 1: reference/F2.patch -> hidden 5/5, suite green, typecheck green"
   static_run val1-f2-reference "$HERE/reference/F2.patch" F2 | tee -a "$LOG"
   check runs/val1-f2-reference 's["hidden_pass"]==5 and s["suite_green"] and s["typecheck_green"]' "F2 step 1" | tee -a "$LOG" ;;
f2-2) log "F2 step 2: upstream unchanged -> hidden 0/5, suite green"
   static_run val2-f2-upstream "" F2 | tee -a "$LOG"
   check runs/val2-f2-upstream 's["hidden_pass"]==0 and s["suite_green"]' "F2 step 2" | tee -a "$LOG" ;;
esac; done

pids=""
for st in $STEPS; do case $st in
3) log "step 3: bare smoke (RUN_TAG=smoke) started"; ( RUN_TAG=smoke ./run.sh bare 1 > runs/.smoke-bare.out 2>&1 ) & pids="$pids $!" ;;
4) log "step 4: sp smoke (RUN_TAG=smoke) started"; ( RUN_TAG=smoke ./run.sh sp 1 > runs/.smoke-sp.out 2>&1 ) & pids="$pids $!" ;;
5) log "step 5: mp smoke (RUN_TAG=smoke) started"; ( RUN_TAG=smoke ./run.sh mp 1 > runs/.smoke-mp.out 2>&1 ) & pids="$pids $!" ;;
f2-3) log "F2 step 3: bare smoke on F2 (RUN_TAG=smoke): bare must score < 5"; ( TASK=F2 RUN_TAG=smoke ./run.sh bare 1 > runs/.smoke-f2-bare.out 2>&1 ) & pids="$pids $!" ;;
spd) log "spd smoke on F1 (RUN_TAG=smoke)"; ( RUN_TAG=smoke ./run.sh spd 1 > runs/.smoke-spd.out 2>&1 ) & pids="$pids $!" ;;
esac; done
[ -n "$pids" ] && wait $pids
for st in $STEPS; do case $st in
3) tail -1 runs/.smoke-bare.out | tee -a "$LOG"
   check runs/bare-r1-smoke 's["end_reason"] in ("done","cap_driver_turns") and len(s["per_turn"])>=1 and all(t["po_kind"] for t in s["per_turn"])' "step 3a: bare ran end to end, the PO classified every turn" | tee -a "$LOG"
   check runs/bare-r1-smoke 'not s["superpowers_injected"] and not s["skill_events"] and "superpowers" not in (s["init_plugins"] or [])' "step 3b: isolation: no Superpowers hook output, no Skill events, user plugin not loaded" | tee -a "$LOG" ;;
4) tail -1 runs/.smoke-sp.out | tee -a "$LOG"
   check runs/sp-r1-smoke 's["superpowers_injected"] and any(h["event"]=="SessionStart" for h in s["hook_events"])' "step 4a: SessionStart hook fired and injected using-superpowers" | tee -a "$LOG"
   check runs/sp-r1-smoke '"brainstorming" in [x.split(":")[-1] for x in s["skills_invoked"]]' "step 4b: brainstorming invoked (Skill event)" | tee -a "$LOG" ;;
5) tail -1 runs/.smoke-mp.out | tee -a "$LOG"
   check runs/mp-r1-smoke 's["per_turn"][0]["stage"]=="/grill-with-docs" and {"grilling","domain-modeling"} <= set(s["per_turn"][0]["skills"])' "step 5: /grill-with-docs resolved (turn 1 loads grilling + domain-modeling, as its SKILL.md instructs)" | tee -a "$LOG" ;;
f2-3) tail -1 runs/.smoke-f2-bare.out | tee -a "$LOG"
   check runs/f2-bare-r1-smoke 's["hidden_pass"] < 5' "F2 step 3: bare scores < 5 on F2" | tee -a "$LOG" ;;
spd) tail -1 runs/.smoke-spd.out | tee -a "$LOG"
   check runs/spd-r1-smoke '{"/brainstorming","/writing-plans","/executing-plans"} <= set(s["spd_slash_stage_per_turn"] or [])' "spd: the three slash stages were all reached" | tee -a "$LOG" ;;
esac; done
log "=== validate.sh done"
