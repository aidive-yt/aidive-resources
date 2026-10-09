# What you (the developer who asked) want: credit notes

You own `ledgerly`, a small invoicing API (Node 20 + TypeScript + vitest, JSON-file store). You typed this request:

> Paid invoices can't be voided, so finance needs credit notes: `POST /invoices/:id/credit-notes` with
> `{ "amount": <cents> }`, numbered `CN-0001`, `CN-0002`..., and `GET /invoices/:id/credit-notes` to list them.
> Voiding a paid invoice should then work, by crediting whatever is left on it.

## Why
A credit note is a legal accounting document: it reduces what a customer owes on an issued invoice. Auditors check
that credit note numbers form one unbroken sequence and that no invoice is credited for more than it was worth.

## What "done" means to you (the five things you will check)
1. **Never over-credit, and the report knows.** The sum of all credit notes on an invoice never exceeds its total (a
   new one that would push past the total is rejected, 400 like the discount rule). The outstanding report
   (`GET /reports/outstanding`) counts, for each open invoice, its total minus what was credited on it.
2. **Production files.** Files written before this change have no credit notes and no credit-note counter. After the
   upgrade the first credit note is `CN-0001` (id well formed), and credit notes persist in the file across a restart.
   Use the repo's migration mechanism (`schemaVersion` + `src/store/migrations.ts`), that is the house rule.
3. **Numbering.** One gapless sequence `CN-0001`, `CN-0002`... across all invoices, in creation order. A request that is
   rejected (bad amount, over the total, draft, void, unknown invoice) must not consume a number: auditors flag gaps.
4. **Errors.** Credit notes only on `open` or `paid` invoices: a draft or a void invoice is 409 (as `/pay` does for
   illegal states). Unknown invoice: 404, on POST and GET. `amount` must be a positive integer number of cents:
   anything else is 400. A rejected request records nothing.
5. **Voiding a paid invoice** now works: it issues one credit note for whatever is left (total minus earlier credit
   notes; none if nothing is left) and sets the invoice `void`. Voiding a void invoice stays 409. The existing test
   that says paid invoices can never be voided must be updated to the new rule, not deleted or skipped; all other
   existing tests stay. Add tests for the new behaviour. Suite and `pnpm typecheck` green.

## Preferences and constraints (answer from these when asked)
- A credit note: `{ id, number, invoiceId, amount, createdAt }`. No reason field needed, no currency field (it is in
  the invoice's currency). POST returns the credit note with 201; GET returns the list (oldest first), 200.
- Credit notes on open invoices are allowed (they reduce what is owed); they do not change the invoice's status.
- Keep it small and in the existing style: domain functions in `src/domain`, routes in the handlers, domain errors
  mapped by the existing error mapping. No new dependencies.
- If asked to choose how to execute a written plan: Native (inline, in this session), not subagent-driven.
  Working on the current branch (main) is fine: you consent to it.
- Work directly in this repo on the current branch. No worktrees, no new branch needed, no remote, no PR to open for
  real (if a tool wants a PR description, writing it is fine). Committing is fine.
- Docs (glossary, ADR, spec files, tickets) are fine if the tool wants them; you do not require them.
- You trust the developer on internal design details: say "your call" for anything not covered here.
- If asked to approve a design, spec, plan or ticket breakdown that matches the above: approve it ("yes, go").
  If it contradicts the above, correct only the contradicting point.
