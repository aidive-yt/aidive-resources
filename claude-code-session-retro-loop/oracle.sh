#!/usr/bin/env bash
# Usage: oracle.sh <workdir> <out.json>  -- the hidden finance test for the credit-note task, run from OUTSIDE the work copy.
H=/path/to/hidden-tests
W="$1"; OUT="$2"
cd "$H" && env -u CLAUDECODE WORK="$W" BASE="$(git -C "$W" rev-list --max-parents=0 HEAD | head -1)" TASK=F2 \
  "$H/node_modules/.bin/vitest" run --reporter=json --outputFile="$OUT" > "$OUT.log" 2>&1
python3 - "$OUT" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]))
for tr in j["testResults"]:
    for a in tr["assertionResults"]:
        print(a["status"].upper(), a["title"]); 
        if a["status"]!="passed": print("   ", " ".join(a.get("failureMessages") or [])[:500].replace("\n"," | "))
PY
