# review: planted defect and matching rule

The uncommitted change is the reference T4 patch (`Table.search(cond, *, sort_by, reverse, limit)`)
with one defect: the truncation guard is `if limit:` instead of `if limit is not None:`, so
`search(cond, limit=0)` returns ALL matching documents instead of `[]` (0 is falsy).
Everything else in the change is correct (missing-field docs last in both directions,
negative limit -> ValueError, cache keeps the plain result).

## Check rule (check.py review)
PASS iff the final answer (case-insensitive) matches at least one of:
- `limit\s*=?=\s*0` (e.g. "limit=0", "limit == 0")
- `limit\s+(of\s+)?(0|zero)\b` (e.g. "limit of 0", "limit zero")
- `\b(0|zero)\s+limit` / `zero[- ]limit`
- `limit` within 150 characters of `falsy|falsey|truthy|truthiness` (either order)
- `if limit:` together with `0` or `zero` within 150 characters
Decoy answers (generic review, or only the sort order) must FAIL.
