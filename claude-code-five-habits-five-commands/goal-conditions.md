# /goal conditions

The /goal judge reads only the conversation. It does not run commands or read files, so write the condition as something Claude's own output can demonstrate. Name one end state and the proof you want printed on screen.

## 1. The one we used (overdue invoices endpoint)

```
/goal GET /invoices/overdue returns the overdue invoices with page and pageSize query params, new tests cover it, and the full pnpm test output showing every test passing is printed in this conversation
```

Result on our run: the reply printed the full vitest output, then the goal was marked achieved.

## 2. Template: a bug fix

```
/goal <the failing behaviour> no longer happens, a new test reproduces it and passes, and the full <your test command> output showing every test passing is printed in this conversation
```

## 3. Template: a refactor

```
/goal <the old name or pattern> no longer appears in the code, the output of <your search command> showing no matches is printed in this conversation, and the full <your test command> output showing every test passing is printed too
```

## Rules for all three

- One end state, not a list of wishes.
- The proof is output Claude prints (test results, a search result), never "it works".
- Do not write a condition Claude cannot meet; an unsatisfiable goal loops.
- Check it with `/goal` alone; remove it with `/goal clear`.
