# What you (the developer who asked) want: partial payments on invoices

You own `ledgerly`, a small invoicing API (Node 20 + TypeScript + vitest, JSON-file store). You typed this request:

> Add partial payments to invoices: `POST /invoices/:id/payments` with `{ "amount": <cents> }`.
> Invoices should expose `amountPaid` and `balance`, and flip to `paid` once the balance hits zero.
> Keep the existing `/pay` endpoint working, and remember we have prod data in the JSON store.

## Why
Customers pay big invoices in instalments. Today finance can only mark an invoice fully paid (`/pay`), so the
outstanding report overstates what we are owed and nobody can see what is left on an invoice.

## What "done" means to you (the five things you will check)
1. **The money math.** Payments accumulate. While something is still owed the invoice stays `open` (no new
   status, please: keep `draft | open | paid | void`). The payment that brings the balance to exactly zero flips it
   to `paid` and sets `paidAt`. Every invoice response (GET, list, and the payment response) shows `amountPaid`
   and `balance` (both integer cents). The outstanding report (`GET /reports/outstanding`) must sum what is still
   owed (the balances), not the invoice totals.
2. **Validation.** `amount` must be a positive integer number of cents. Zero, negatives, decimals, strings,
   missing: 400 validation error, same shape as the rest of the API. Paying more than the balance is rejected
   (we do not do credit or refunds here); 400 is fine. A rejected payment changes nothing.
3. **Existing data.** Production files exist. Invoices already marked `paid` before this change were paid in
   full: after the upgrade they must show `amountPaid = total`, `balance = 0`. Open ones show `amountPaid = 0`.
   The repo has a migrations mechanism (`schemaVersion` + `src/store/migrations.ts`); use it, that is the house
   rule. Payments must persist in the file like everything else. `/pay` keeps working and must leave a paid
   invoice with `balance = 0`.
4. **Error paths.** Unknown invoice: 404. Paying a draft or a void invoice: 409 (same as `/pay` does today).
5. **Tests.** Add tests to the repo suite for the new behaviour (vitest, next to the existing ones). Suite and
   `pnpm typecheck` green at the end.

## Preferences and constraints (answer from these when asked)
- Keep it small and in the existing style: domain functions in `src/domain`, route in the invoices handler,
  money in integer cents, domain errors mapped by the existing error mapping. No new dependencies.
- Store each payment (amount + timestamp) on the invoice; derive `amountPaid`/`balance` from them. A payment id
  or a note field is not needed. Listing payments separately (GET .../payments) is not needed.
- Response of `POST /invoices/:id/payments`: the updated invoice, status 201 (200 is acceptable too).
- Currency: a payment is in the invoice's currency; no currency field on the payment.
- Overdue logic is unchanged (an open invoice past its due date is overdue even if partially paid).
- Work directly in this repo on the current branch. No worktrees, no new branch needed, no remote, no PR to
  open for real (if a tool wants a PR description, writing it is fine). Committing is fine.
- Docs (glossary, ADR, spec files, tickets) are fine if the tool wants them; you do not require them.
- You trust the developer on internal design details: say "your call" for anything not covered here.
- If asked to approve a design, spec, plan or ticket breakdown that matches the above: approve it ("yes, go").
  If it contradicts the above, correct only the contradicting point.
- If asked to choose how to execute a written plan: Native (inline, in this session), not subagent-driven.
  Working on the current branch (main) is fine: you consent to it.
