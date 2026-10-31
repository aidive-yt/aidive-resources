<!-- The consolidated review report from our run on a family gift-list app. -->

# Consolidated Review Report

**Target:** `docs/egm/gift-reservations.md` (464 lines; FeatureRange 1-280, DetailedRange 281-464)
**Mode:** Consolidated report, all five stages, no checkpoints. No edits were applied to the document.
**Stage reports:** `zoom_out_report.md` (5), `comprehension_report.md` (6), `critic_report.md` (7), `intermediate_zoom_out_report.md` (8), `implementation_readiness_report.md` (9).

**Overall:** The design fits the problem and keeps Notion as the only store. It is not ready to implement. Five issues need decisions from the author, and the plan has errors a reader can check against the code: a build that breaks mid-sequence, a wrong HTTP status, and a wrong assumption about SDK retries.

## Blockers
Stage 8 raised one item to Blocker (A1). Stages 5, 6, 7 and 9 report none.

## Action items by priority

### 🔴 Blocker

**A1. Decide whether to drop the post-write re-read.** (Stage 5 ZO-2, Stage 6 CO-3/CO-6, Stage 7 CR-1/CR-2/CR-3/CR-8, Stage 8 Z8-1, Stage 9 IR-6)
Lines 28, 132-134, 159, 174, 220, 276, 360, 366, 415.
The re-read does not catch the main race (the document says so at line 174), assumes read-after-write consistency with no evidence, checks only `x`, adds a third Notion call, and leaves the cookie and response behaviour undefined when it fails. Goal 2 and the rejection of Alternative F rest on it. Stage 8 recommends removing it, along with `changed_meanwhile` and the "unverified" branch, rewriting Goal 2 as "reduces duplicate purchases, does not prevent them" and rewriting Alternative F around the real trade-off. If kept, every post-write failure needs a stated cookie and response behaviour. Decide this first: it closes or removes about eight other findings.

### 🟡 Major: design and scope

**A2. Fix the cookie's stated guarantees and the stale-record dead end.** (CR-4, CR-5, Z8-2, Z8-3, ZO-5)
Lines 32, 34, 85, 111, 114, 144-148, 246-250, 355.
A saved copy of the cookie can be replayed to cancel someone else's unit, and clearing the cookie bypasses the one-unit and 80-id limits. After the parents release a unit by hand, the stale cookie makes reserve fail with 409 `already_reserved`. State the real threat model (stops accidental cancels and casual tampering among about 30 relatives), and decide whether to keep the `already_reserved` guard and the 80-id cap.

**A3. Qualify "no identity is stored or logged", and decide on the bespoke log line.** (CR-6, Z8-4, CO-7)
Lines 29, 37, 270-271, 367.
Vercel request logs and Notion edit history, together with timestamped log lines, can let the parents correlate who reserved what. The log line is also specified three different ways.

**A4. Settle where configuration is checked, and the effect on the list route.** (ZO-4, Z8-5, CR-17, CO-12, IR-13)
Lines 36, 115, 117, 168, 394-395, 403.
The proxy 503 for `/api/registry*` changes the existing list GET route, which the plan doesn't list. Configuration is checked in the proxy, the routes and `canReserve`. The 401 versus 503 precedence is unspecified.

**A5. Reuse the existing HMAC helper.** (ZO-1, IR-8)
Lines 111, 324. `src/lib/auth.ts` already has `hmacBase64Url`. The plan writes a second implementation and leaves the crypto details (key import, base64url without `Buffer`, signed text) unspecified.

### 🟡 Major: factual errors and unstated assumptions

**A6. "Each step leaves the project building" is false.** (CO-2, IR-1, Z8-6)
Line 283. The build is red from item 8 through item 16. Group the changes into one landing phase or keep the old exports until the consumers go.

**A7. The deleted `PATCH` route returns 404, not 405.** (CO-5, CR-7, IR-2)
Lines 116, 181, 388, 458. Correct the claim and manual test 7. A 410 stub is an option, but Stage 8 advises against adding code for it.

**A8. Handler signatures ignore Next 16 async APIs.** (IR-3)
Lines 115, 378, 382, 402. `params` is a `Promise`, and `cookies()` is async.

**A9. The Notion SDK already retries 429s, and error classification is unspecified.** (IR-4, IR-5)
Lines 276, 339-345. "No automatic retry" is false unless `getClient` sets `retry: false`. Name how `rate_limited`, `not_found` and `retry-after` are detected, state the `pages.update` payloads, and reconcile the two signatures of `writeReservationState`. A missing `Acheté ?` returns 502 before the 422 check.

**A10. Undefined terms and sources.** (CO-1, CR-12, CO-4, CO-10, CO-14)
`concepts_brief.md`, "the owner", "reconciliation", "Public only" filter, `x` and `y`, and the data-source id are used without definition or link. Five places justify choices by process history a new reader cannot verify.

**A11. Required sections and rationale.** (CR-9, CR-10, CR-11)
There is no Risks & Mitigations section (the content is scattered). Alternatives A, J and M are rejected only on "the parents decided"; C and F lack the decisive trade-off. The Open Question at line 57 points to intro wording that is not in the plan.

**A12. Unresolved decisions in the plan.** (IR-6, IR-7, IR-9, IR-10, IR-11, IR-12)
Cancel error mapping, the cookie-change rule, response bodies, final French copy, the client rewrite details and automated test coverage for the Notion layer, routes, proxy and table.

### 🟢 Nit

*   **Simplicity.** Single `[action]` route instead of two files; delete the unused `checkbox.tsx` and `input.tsx`; remove the "Optional extras" question; revert to strict `x/y` parsing or fix the Goal wording; fold Alternatives G, H and I into Goals and Non-Goals. (ZO-6, ZO-8, Z8-7, Z8-8, Z8-9, CR-19)
*   **Structure.** Reorder Open Questions; split CUJ 4; add one error-path CUJ; fix the ambiguous state table and the packed response table; fix the "two new calls" list. (CR-13 to CR-16)
*   **Wording and terminology.** Unify `acheté`/`achete`/`Acheté ?` and `x/y` versus `acquise/totale`; remove filler and duplicated statements; fix French copy and apostrophes; pin `vitest`; split the dense reserve step 7 and `act` handler sentences. (CR-18, CR-20 to CR-24, IR-14 to IR-20)

## Traceability matrix

| Action item | Stage 5 | Stage 6 | Stage 7 | Stage 8 | Stage 9 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 re-read | ZO-2 | CO-3, CO-6 | CR-1, CR-2, CR-3, CR-8 | Z8-1 | IR-6 |
| A2 cookie guarantees, stale record | ZO-5 | | CR-4, CR-5 | Z8-2, Z8-3 | |
| A3 identity and logging | | CO-7 | CR-6 | Z8-4 | IR-17 |
| A4 config checks, list route | ZO-4 | CO-12 | CR-17 | Z8-5 | IR-13 |
| A5 HMAC reuse | ZO-1 | | | | IR-8 |
| A6 build order claim | | CO-2 | | Z8-6 | IR-1 |
| A7 405 vs 404 | | CO-5 | CR-7 | Z8-7 | IR-2 |
| A8 async handler APIs | | | | | IR-3 |
| A9 SDK retry, error mapping | | | | | IR-4, IR-5 |
| A10 undefined terms | | CO-1, CO-4, CO-10, CO-14 | CR-12 | | |
| A11 risks section, rationale | | | CR-9, CR-10, CR-11 | | |
| A12 unresolved plan decisions | ZO-3 | CO-13 | | | IR-6 to IR-12 |
| Nits | ZO-6 to ZO-8 | CO-8, CO-9, CO-11, CO-15, CO-16 | CR-13 to CR-24 | Z8-7 to Z8-9 | IR-14 to IR-20 |

## Coverage and limits
- Stage 7 critics reviewed lines 1-280 only. Stage 9 reviewers audited lines 281-464 against the real code under `src/`.
- No stage reviewed any file outside the target document and the existing source files named above.
- Stage 8 ran on the unedited document, so its recommendations (drop the re-read, drop `already_reserved`, remove the proxy 503) are proposals for the author to decide, not settled findings.
- Reviewers cannot run the app. The claims about Next.js (404 versus 405) and the Notion SDK (retry defaults) come from the reviewers reading the code and type definitions in the repo and should be confirmed during the fix.
