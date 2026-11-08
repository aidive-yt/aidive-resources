---
paths:
  - "src/domain/**"
---
# src/domain: pure functions, nothing else

- No I/O here: no `node:fs`, no `node:http`, nothing from `src/store/` or `src/http/`.
- `type`, never `interface`; const objects or union types, never `enum`; no `any`.
- Money is an integer number of cents; reuse `money.ts` (`assertCents`, `formatCents`, `sum`) instead of writing a new helper.
- One new file needs a reason the task gives. No class, factory or generic helper for one caller.
These conventions are checked by ESLint on every edit (`.claude/hooks/lint-edit.sh`).
