#!/bin/bash
# For each mutation: apply on a scratch copy of ledgerly, run the suite, report killed/survived
set -u
SRC=/private/tmp/subagents-bench/ledgerly
for t in money customer invoice validation migrations router; do
  W=$(mktemp -d /private/tmp/subagents-bench/eval/mut-XXXX); cp -R "$SRC/." "$W/"
  python3 - "$W" "$t" <<'PY'
import sys; sys.path.insert(0, "/private/tmp/subagents-bench/eval")
from mutations import MUTATIONS
w, t = sys.argv[1], sys.argv[2]
f, old, new = MUTATIONS[t]
p = f"{w}/{f}"; s = open(p).read()
assert s.count(old) == 1, (t, s.count(old)); open(p, "w").write(s.replace(old, new))
PY
  (cd "$W" && npx vitest run >/dev/null 2>&1) && echo "$t survived" || echo "$t killed"
  rm -rf "$W"
done
