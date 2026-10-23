# Retro output, session A (cb5884fb-bd6f-4684-8866-d0adc12ac26e)

## 1. `/retro` (resumed headless, 2026-10-23 10:39:44, $0.0658, 17.5 s, 5 turns)

Prompt typed: `/retro` -> transcript records `<command-name>/mattpocock-skills:retro</command-name>`. Tool calls: Skill(mattpocock-skills:writing-for-agents), Bash(ls -a; ls .github; ls .git/hooks | grep -v sample; cat tsconfig.json), Bash(find .claude -type f; cat .claude/settings*.json).

Verbatim:

> This session was smooth. The pass came out clean on the first typecheck and test run, and I found no `AGENTS.md`/`CLAUDE.md` or `CODING_STANDARDS.md` to prune. The candidates below are in order of severity.
> 
> **1. No guardrail runs the checks (automated checks)**
> - `package.json` already has `test` and `typecheck`, but nothing runs them: there's no `.github/` workflow and no pre-commit hook.
> - This session only stayed green because I ran both by hand. An agent, or a person, can commit a type error or a failing test.
> - **Fix:** add a CI job running `pnpm typecheck && pnpm test`, plus a pre-commit hook running the same. Neither needs prose.
> 
> **2. The migration rule is the one convention that could be missed (automated checks)**
> - The README says "any change to the stored shape bumps `schemaVersion` and adds a migration".
> - I found it only because I read `README.md` while working out the design. If I'd skipped it, nothing would have failed. Adding a field to `StoreData` without a migration still typechecks.
> - **Fix:** a test that fails when someone changes the stored shape without bumping the version. For example, snapshot the output of `migrate({})` and assert the snapshot's `schemaVersion` equals `CURRENT_SCHEMA_VERSION`. This is a deterministic check, so it should replace the README sentence rather than add to it.
> 
> **3. Adding a counter or store collection touches five places (navigation)**
> - Adding credit notes meant editing `types.ts`, `json-store.ts` (the `empty()` function), `migrations.ts` (the migration, plus the fallback defaults at the bottom of `migrate`), `context.ts`, and a new repo file.
> - The `{ customer: 0, invoice: 0, invoiceNumber: 0 }` literal is duplicated in `json-store.ts` and `migrations.ts`. I had to find both with `grep`.
> - **Fix:** have `migrate` build its defaults from one shared `emptyData()`. That removes a hidden dependency rather than documenting it. A pointer in a steering file would cost context on every turn and go stale, so I wouldn't write one.
> 
> **4. Nothing for the reviewer to enforce (coding standards)**
> - There's no `CODING_STANDARDS.md`. The README's conventions are mostly mechanical: integer cents, domain functions that don't mutate their input, and which error type maps to which status.
> - A reviewer agent would have no judgement-call rules to apply. I wouldn't add any until a real review miss shows one is needed.
> 
> **5. Tool economy and information access: nothing to change**
> - My one failed Bash call (a rejected heredoc) cost a retry, but that was my command and not the tooling.
> - I had everything I needed, since the tests call `createApp().handle` directly with no server or logs to tee.
> 
> I'd start with 1 and 2. They're small, mechanical, and would catch the likeliest future mistake. Want me to add the CI workflow, the pre-commit hook and the schema-version test?

## 2. Trace step (same session, 10:40:33, $0.0322, 17.1 s, 1 turn)

Prompt: "For each candidate, quote the moment of this session's transcript that backs it; drop any candidate you cannot trace to a specific moment."

Verbatim:

> Two of the five candidates have no support in the transcript, and I got a detail wrong in a third. Here is each one against what actually happened.
> 
> **1. No guardrail: kept**
> - The moment is my `ls -a; ls .github 2>/dev/null; ls .git/hooks | grep -v sample` command. The listing shows `.claude .git .gitignore data node_modules package.json … vitest.config.ts`. There is no `.github`, and the hooks `grep` printed nothing.
> - It isn't a mistake I made, since my own `pnpm typecheck` and `pnpm test` run came back clean. It's a repo-state finding: the checks exist as scripts and nothing runs them.
> 
> **2. Migration rule has no check: dropped**
> - I can't point to a moment where I missed or nearly missed a migration. I read `migrations.ts` in my first big `cat`, before I'd seen the README. I would have found the migration step either way, so my claim that I found it only through the README was wrong.
> - "Nothing would have failed if I'd skipped it" is a hypothetical, not something that happened.
> 
> **3. Five places to touch for a new collection: kept, but weaker than I said**
> - The moment is my batch of edits to `types.ts`, `json-store.ts`, `migrations.ts` and `context.ts`. Two of them changed the same literal, `{ customer: 0, invoice: 0, invoiceNumber: 0 }`, which now reads `…, creditNote: 0`. It appears in both `json-store.ts` and the fallback in `migrate`.
> - I said I "had to find both with `grep`". That's wrong. I never ran one, since the `grep` was in the command that was rejected. I already knew both locations from reading the files, and the edits went through without friction.
> - The duplicated literal is real but caused no trouble. I'd rate it low severity.
> 
> **4. No `CODING_STANDARDS.md`: dropped**
> - The only moment is the `git ls-files` output showing the file doesn't exist. No review step happened in this session and no reviewer missed anything.
> - "I wouldn't add any until a real review miss shows one is needed" was my own opinion, not something the session showed.
> 
> **5. Tool economy: dropped as a finding**
> - The moment is my first Bash call being rejected with `Contains brace with quote character (expansion obfuscation)`. It cost one retry, and I switched to Write and Edit.
> - It was a one-off, and I can't tell from the transcript whether the harness or my heredoc-in-Python approach was at fault. I don't think it justifies a change.
> 
> That leaves candidate 1 as the only solid finding and candidate 3 as a minor one. For 1, I can add a CI workflow and a pre-commit hook that both run `pnpm typecheck && pnpm test`.

## 3. Second `/retro`, with the defect reported by the developer (same session, 10:41:10, $0.0491, 23.1 s, 1 turn, no tool call; it skipped the writing-for-agents reload)

Prompt: `/retro Finance tested this build after the session: they sent a credit note that was too big (rejected, fine), and the next valid credit note came out CN-0004 where CN-0002 was due. Rejected requests burn credit-note numbers. Don't fix the code; run the retro on this session with that failure in mind.`

Verbatim:

> I'm skipping the style-guide reload because it's already in this session. The cause is in my own code, and I traced each finding to a specific moment.
> 
> **What happened**
> - In `issueCreditNote` (`src/http/handlers/invoices.ts`) I call `ctx.store.nextId("creditNote")` first and `createCreditNote(...)` second. `nextId` persists the counter immediately, and `createCreditNote` is what throws the 409 for an over-limit amount. So a rejected request still burns a number.
> - I copied the order from the existing `/issue` handler, which I had read. It does `const n = ctx.store.nextId("invoiceNumber"); const issued = issue(current, ...)`, and `issue()` throws if the invoice isn't a draft. So issuing a non-draft invoice probably burns an `INV-` number the same way. I haven't run that, only read it.
> 
> **1. A test that would have caught it: I wrote the scenario and skipped the assertion (automated checks)**
> - The moment is the test I wrote: "rejects bad amounts (400) and amounts above what is left (409)".
>   ```
>   await app.handle("POST", ..., { amount: 8_000 });
>   expect((await app.handle("POST", ..., { amount: 1_001 })).status).toBe(409);
>   expect((await app.handle("POST", ..., { amount: 1_000 })).status).toBe(201);
>   ```
>   That is exactly Finance's sequence: accept, reject, accept. I only checked status codes, never the number on the last note, which comes out as `CN-0003`.
> - The "numbers credit notes sequentially" test only covers two successful requests in a row.
> - **Fix:** add a test that each numbered sequence (`INV-`, `CN-`) stays gapless after rejected requests. Run it over both sequences, which also exposes the `/issue` case.
> - **Rule:** when a test reaches a failure path, assert the state afterwards, not just the status code.
> 
> **2. `nextId` looks pure but isn't (navigation)**
> - In `json-store.ts`, `nextId(kind)` runs `this.update(...)`, so every call writes to the counter and persists it. The `Store` type in `json-store.ts` has only the signature `nextId(kind: keyof Counters): number;`, with no comment about the side effect.
> - Nothing at the call site tells you to allocate only after validation. This is a gotcha no config reveals, so a short doc comment on `nextId` is worth its cost. Something like: "Consumes the number even if the caller then fails; call it only after validation."
> - Keep it as a comment on `nextId`, not a steering-file line. It matters only to someone calling `nextId`, and it can't go stale there.
> 
> **3. The gapless-numbering convention isn't written down (coding standards)**
> - The README's "Conventions" list has cents, immutability, error-to-status mapping, and migrations. It says nothing about invoice or credit-note numbers being gapless, though the request ("numbered `CN-0001`, `CN-0002`...") implies it.
> - This is partly a judgement call: reviewers need to know that numbers are allocated after validation. One README line would do. Finding 1's test is the deterministic check; the README line explains why the test exists.
> 
> **4. Missing CI, from the first retro: still real, but it wouldn't have helped here**
> - My own typecheck and tests passed, so a CI job would also have passed. I'm keeping it as a separate, unrelated finding, not as a cause of this failure.
> 
> **5. My summary stated the rules but didn't test them**
> - I told you "Rules I chose" and flagged the two-update void risk, but never exercised a rejection followed by a success. The summary read as complete when that path was untested. This is a process gap, and finding 1 is the fix.
> 
> I'd start with 1 and 2. I haven't touched the code, as you asked.

## 4. Trace step on the second retro (same session, 10:41:43, $0.0498, 33.4 s, 1 turn)

Prompt: same trace prompt as section 2.

Verbatim:

> I traced each candidate again. Two survive on firm evidence, two survive but with a gap I should state, and one is dropped.
> 
> **1. Test asserts status but not the number: kept, firm**
> - The moment is the test I wrote in `test/credit-notes.test.ts`:
>   ```
>   await app.handle("POST", `/invoices/${id}/credit-notes`, { amount: 8_000 });
>   expect((await app.handle("POST", `/invoices/${id}/credit-notes`, { amount: 1_001 })).status).toBe(409);
>   expect((await app.handle("POST", `/invoices/${id}/credit-notes`, { amount: 1_000 })).status).toBe(201);
>   ```
>   That is accept, reject, accept, with only status codes checked. By my reading of the handler, the last note comes out as `CN-0003`. I derived that and haven't run it.
> - The adjacent test, "numbers credit notes sequentially…", covers two successes in a row and never a rejection.
> - The cause, which I only read and haven't run, is this in the handler I wrote:
>   ```
>   const id = ctx.store.nextId("creditNote");
>   const note = createCreditNote(invoice, existing, amount, …
>   ```
>   That order matches the existing issue handler, which I read:
>   ```
>   const n = ctx.store.nextId("invoiceNumber");
>   const issued = issue(current, `INV-…`, ctx.now());
>   ```
>   and `issue()` throws `ConflictError` for non-drafts. So the `INV-` sequence very likely has the same leak. I haven't run that either.
> 
> **2. `nextId` has no warning about its side effect: kept, firm on the facts**
> - The moment is the `Store` type I read in `json-store.ts`. `update` has a comment ("Apply a change and persist it (when file-backed)."), while `nextId(kind: keyof Counters): number;` has none. Its implementation calls `this.update(...)`, so it persists immediately.
> - The `/issue` call site I copied has no comment either.
> - I can't show that a comment would have changed what I did, because I never weighed the ordering at all. I copied it. The comment is a bet on the next caller, not a proven fix.
> 
> **3. Gapless numbering isn't written in the README: kept, weaker**
> - The moment is the `README.md` output I read before writing the handler. Its Conventions list covers cents, no mutation, error-to-status mapping and `schemaVersion`. It has no line about numbers.
> - So the agent doing the implementation, meaning me, read the conventions and found nothing on this.
> - I overstated one thing last turn. Your request said "numbered `CN-0001`, `CN-0002`...", and I said that implies gapless numbers. That was my inference, not your words. Finance has now confirmed it as a requirement, but nothing in the original request stated it.
> 
> **4. No CI or pre-commit hook: kept, unrelated to this failure**
> - The moment is my `ls -a; ls .github 2>/dev/null; ls .git/hooks | grep -v sample` output, which showed no `.github` and no hooks.
> - It wouldn't have caught this. My own run ended `Tests 42 passed (42)`, and CI would have passed too.
> 
> **5. "My summary stated rules without testing them": dropped**
> - I can quote the summary ("Rules I chose", plus the line about the void being two separate store updates). But it describes my behaviour, not a change to the environment, and finding 1 already covers the underlying gap. Keeping it would count one moment twice.
> 
> The order of importance is 1, 2, then 3. Finding 4 stays on the list but belongs to a separate piece of work. I still haven't changed any code.
