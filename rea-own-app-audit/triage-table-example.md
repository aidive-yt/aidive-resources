# REA audit of aidive.dev: what the shipped site gives away

Date: 2026-10-17 (UTC). Tool: REA `rea-agents@6.5.0`, installed from npm.
Targets: `https://aidive.dev/club/` and `https://aidive.dev/club/free-resources/claude-code-limit-cut-levers/`.

The first five columns of the findings table are the outsider view. They were written from REA evidence
and the shipped scripts only, before any source file of this repository was opened
(commit `7e10d79` has that version alone). The last two columns, **Verdict** and **Source**, were added in step 5 after reading the source.

## Summary

- **The email gate does not protect the packs.** Each pack reaches every visitor in three ways without an email:
  the page HTML (F01), a raw markdown copy at `/club/free-resources/<slug>.md` (S1), and the pack files under `/files/` (S2).
  The gate is a client-side overlay over a static export (F02, F03).
- **`/api/subscribe` writes to the real Brevo list with no brake.** It has no rate limit, no CAPTCHA, no Origin check and no double opt-in, and it records no consent (F05, F06).
  Any website can make its visitors' browsers subscribe any address.
- **The whole site config ships to the browser** (F08). This includes values that are not public elsewhere, because this repository is private:
  the Brevo list ID, the YouTube auto-reply limits and the build layout.
- **No response security headers** (U1, now real): no CSP, HSTS, X-Frame-Options, nosniff or Referrer-Policy.
- **Clean:** no source maps, no secrets or API keys in the bundles, no storage, no cookies, and nothing in the console.

## Evidence

| ID | REA operation | Target | Evidence ID |
|----|---------------|--------|-------------|
| E1 | `list_browser_targets` | browser | `ev_bb5764a587b84a36cb11d40f6cd96b2acea26e1e412d0b1d114d2950dd16aab0` |
| E2 | `inspect_web_page` | /club/ | `ev_d84a8cc1436925f002108882c2472e47e744b42097ea8a1c7ff4b03748c329e3` |
| E3 | `inspect_web_page` | free resource | `ev_f08acdc2dba3b837ed1df24b57c80c9528982f9cac80eb5c042963573c743a0b` |
| E4 | `analyze_web_bundle` | /club/ | `ev_ab551792ba284eef2b91e5e43ddc618c92baadcea1050b9bf117bc9bd32ab98a` |
| E5 | `analyze_web_bundle` | free resource | `ev_9e24cc703943623efa2f31750c89ca27ccd5b95a55225bef7be0257a80cfb16f` |
| E6 | `capture_web_screenshot` | /club/ | `ev_c029b86ad2b4a92a0ef45b529691c4bc3f1d1a89b0e340cc0d05f6d51003f65e` |
| E7 | `capture_web_screenshot` | free resource | `ev_72b418d989c042d6320c5473f7d31acd660b242213fea09c97fd33a678bd756e` |
| E8 | `export_web_scripts` | /club/ capture (E2) | `ev_397383a4930fe6fbd9bf7568856f9e9f52d32b4bceba66e348e1738110e421a4` |
| E9 | `export_web_scripts` | free resource capture (E3) | `ev_7b2177f6a302c5971df051a01970d8c63d29286d8a47244fd6c4dacfc59735e3` |
| G1 | not REA: request log of the CDP write guard (see Method) | both pages | `/tmp/rea-audit/guard/requests.jsonl` |
| H1 | not REA, step 5: HEAD requests and anonymous GitHub API reads (see Method) | listed per row | , |

Chunk names below are the shipped file names under `https://aidive.dev/_next/static/chunks/`, as exported by E8 and E9.
Source paths are relative to the repository root. `engine/site/` is shortened to `site/`.

## Findings

Kind: **Observation** = seen directly in the evidence. **Inference** = concluded from what was seen.
**Unknown** = REA could not see it. Severity is "how bad it would be" for the site: High, Medium, Low, Info, None.

Verdict (step 5): **Real leak** = the source confirms it and nothing shows it is intended.
**By design** = the source shows it is intended or unavoidable. **False positive** = the source contradicts the outsider reading.

| # | Evidence | Finding | Kind | Severity | Verdict (step 5) | Source |
|---|----------|---------|------|----------|------------------|--------|
| F01 | E3, E7, E9 (inline script `source-1`) | The whole gated pack ships to every visitor. The page HTML carries the article (TL;DR, measurements table, "Do this Monday" checklist, sources, FAQ) in its inline RSC payload. While the email dialog is open, the accessibility tree exposes about 11.6 KB of that text (13 headings, 60 table cells). The screenshot shows it only blurred. View source, reader mode, a screen reader, `curl` or JS turned off all read it without an email. | Observation | High (the email gate protects nothing) | **Real leak.** The site is a static export, and the pack is rendered at build time into the HTML. The gate can only hide it, not withhold it. | `site/next.config.ts` (`output: 'export'`), `site/src/lib/resources.ts` (`renderResourceHtml`), `site/src/components/pages/resource-page.tsx`, `site/src/app/(default)/club/free-resources/[slug]/page.tsx` |
| F02 | E9, chunk `1t27yr-aialmx.js` (`EmailGate`) | The gate is client-side only. It opens 1500 ms after load unless `localStorage[SITE.name.toLowerCase() + ":club:unlocked"] === "1"`. With `SITE.name = "AIDive"` (F08) the key is `aidive:club:unlocked`. One line in the console removes the gate for good. | Observation (key value: Inference) | Medium (the mechanism behind F01) | **Real leak** (same root cause as F01). Key confirmed: `aidive:club:unlocked`. | `site/src/components/email-gate.tsx` (`KEY`, `DELAY_MS`, `readUnlocked`) |
| F03 | E9, `1t27yr-aialmx.js` | The gate fails open. A network error, a 6 s timeout, or any response other than `400 {error: "invalid" or "disposable"}` unlocks the page (`console.warn("subscribe failed, unlocking")`). Blocking `/api/subscribe` in DevTools unlocks without an email. | Observation | Low (F01 already exposes the content) | **By design.** The code comment says: "a broken form must never hide a free page". The Worker's `405`, `502 upstream` and `503 disabled` answers also unlock. | `site/src/components/email-gate.tsx`, `site/worker/index.ts` |
| F04 | E4, E5 (endpoint candidate), E9 | The subscribe contract is readable: `POST /api/subscribe`, JSON `{email, lang, source}`, `source = location.pathname + location.search`. The server answers `invalid` and `disposable`, so a disposable-domain filter exists. | Observation | Low (gives a script writer the exact contract) | **By design** (a public form needs a public endpoint). Note: the disposable list has only 10 domains. | `site/worker/index.ts`, `site/worker/disposable-domains.ts` |
| F05 | E9, `1t27yr-aialmx.js` | The request has no consent field. The "I agree to receive AIDive emails" checkbox is only HTML `required`. A scripted call and a checked box look the same to the server. No consent text version or timestamp comes from the client. | Inference | Medium (proof of consent depends on server logging, see U3) | **Real leak** (a confirmed gap, not a data leak). The Worker sends Brevo only `email`, `listIds`, `LANG` and `SOURCE`. It stores no consent flag, timestamp or consent text version. | `site/worker/index.ts` |
| F06 | E9, `1t27yr-aialmx.js` | No anti-bot or anti-CSRF token goes with the subscribe call: no Turnstile, reCAPTCHA or hCaptcha, no CSRF token. Anyone can script the subscription of third-party addresses into the real mailing list. | Inference (server-side rate limits/double opt-in: U3) | Medium to High without rate limit or double opt-in, Low with them (see U3) | **Real leak; severity High.** No rate limit, no Origin check and no double opt-in: the contact is created directly with `POST /v3/contacts`. `request.json()` parses the body whatever its content type, so a cross-site `text/plain` POST needs no CORS preflight. Any website can make its visitors' browsers subscribe any address. Read from the code only; no POST was sent. | `site/worker/index.ts` |
| F07 | E9, `1t27yr-aialmx.js` | `source` takes the query string as is. Any visitor controls a free-text value stored with their subscription, for example `?x=anything`. | Inference | Low (pollution of list attributes) | **By design.** The query string carries UTM attribution: the `/r/<code>` short links add `utm_*`. The Worker cuts `SOURCE` to 120 characters. Free text is still stored. | `site/scripts/emit-md.mjs` (`_redirects`), `site/worker/index.ts` |
| F08 | E8, E9, chunk `3f4cx_6a3wsgs.js` | The whole site config ships as one `JSON.parse('…')` in a shared chunk loaded on both pages: about 59 KB of JSON, with the copy for 15 locales. Public values in it: name, URL, `email: contact@aidive.dev`, YouTube channel, founding date, timezone `Europe/Paris`. Operational values: F08a to F08d. | Observation | Low (Info for the public values) | **Real leak.** `site.ts` imports all of `generated/site.json`. Two client components, `email-gate.tsx` and `locale-switcher.tsx`, import `SITE`, so the bundler ships every key. They use only `name` and the locales. | `site/src/lib/site.ts`, `site/src/components/email-gate.tsx`, `site/src/components/locale-switcher.tsx`, generated by `site/scripts/channel.mjs` from `channel.config.json` |
| F08a | E8, E9, `3f4cx_6a3wsgs.js` | `club.repo = {owner: "aidive-yt", name: "aidive-resources", commitAs: {name: "AI Dive", email: "339050828+aidive-yt@users.noreply.github.com"}}`. It names the repository where the packs probably live, plus the bot commit identity and its GitHub numeric user ID. | Observation | Medium if the repository is public (all packs readable, see U4). Low if private (reconnaissance only) | **By design.** `aidive-yt/aidive-resources` is public (H1: anonymous GitHub API 200). Pack pages link each file "on GitHub". `commitAs` is not used by the site, but the same noreply address is on every public commit of that repo. | `site/src/lib/resources.ts` (`renderResourceHtml`), `channel.config.json` (`club.repo`) |
| F08b | E8, E9, `3f4cx_6a3wsgs.js` | `club.brevoListId = 3`. It confirms the email provider and the target list. | Observation | Low (useless without the Brevo API key) | **Real leak** (Low). Needed only at build time, to write `BREVO_LIST_ID` into `wrangler.jsonc`. The client never reads it. | `channel.config.json`, `site/scripts/channel.mjs` (`club: site.club ?? null`, verbatim) |
| F08c | E8, E9, `3f4cx_6a3wsgs.js` | `club.autoReply.youtube = {dailyCap: 100, breakerErrors: 5}`. It reveals a YouTube auto-reply bot, its daily cap and its circuit-breaker threshold. | Observation | Low (someone who can cause 5 errors knows how to trip the breaker: Inference) | **Real leak** (Low). No code in `engine/site` reads `autoReply`. It reaches the client only because `channel.mjs` copies the club block verbatim. | `channel.config.json`, `site/scripts/channel.mjs` |
| F08d | E8, E9, `3f4cx_6a3wsgs.js` | `contentDir = "../../channel/site/content"`. It shows the build-time monorepo layout. | Observation | Info | **Real leak** (Info). Used only at build time and on the server. | `site/scripts/channel.mjs`, read by `site/src/lib/content.ts` and `site/src/lib/resources.ts` |
| F08e | E4, E8, `3f4cx_6a3wsgs.js` | Every first load downloads the copy for all 15 locales (78 KB raw chunk), whatever the page language. | Observation | Low (performance, not security) | **Real** (performance, same root cause as F08). | `site/src/lib/site.ts`, `site/scripts/channel.mjs` (`copy`) |
| F09 | E4, E5 | No source maps. None of the 19 (club) and 10 (free resource) analyzed scripts declares a `sourceMappingURL`. `source_maps.requested = 0`. | Observation | None (good) | **By design.** `productionBrowserSourceMaps` is not set, and its default is off. | `site/next.config.ts` |
| F10 | E4, E5 (`vendor_fingerprint`) | Stack fingerprint: Next.js (App Router, Turbopack build, RSC payloads) and React. | Inference (REA confidence high and medium) | Info | **By design** (it cannot be hidden in practice). | `site/package.json` |
| F11 | E2, E3 (storage, workers, console) | No localStorage, sessionStorage, IndexedDB or Cache Storage entry, and no worker, before unlock. The console stayed silent during the observation window. | Observation | None (good) | **By design.** The only storage write is the unlock key, after the form (F02). No cookie code exists, and `/club/` sends no `Set-Cookie` (H1). | `site/src/components/email-gate.tsx` |
| F12 | E3 (`dom_urls`) | The gated page links 14 other locale versions (`/fr/`, `/de/`, …, `/zh-TW/`) and `/videos/<slug>/`. Each locale probably ships the same pack under the same gate. | Observation (links), Inference (same exposure) | Info (multiplies F01) | **By design** (i18n). The same exposure as F01 applies to every locale. | `site/src/app/[lang]/club/free-resources/[slug]/page.tsx` |
| F13 | G1; E2, E3 (1 script excluded as other origin) | Each page view loads `static.cloudflareinsights.com/beacon.min.js` and tries `POST /cdn-cgi/rum` (Cloudflare Web Analytics). The privacy copy shipped in `3f4cx_6a3wsgs.js` covers only the unlock flow and does not name it. | Observation (requests), Inference (privacy gap) | Low | **Real leak** (privacy notice gap), **not from the repo.** The layouts render the beacon only when `SITE.club.analyticsToken` is set, and it is not set. The beacon comes from Cloudflare's automatic Web Analytics injection on the zone (dashboard setting). | `site/src/app/(default)/layout.tsx`, `site/src/app/[lang]/layout.tsx` (tag off); notice in `channel/site/copy/<locale>.json` |
| F14 | G1 | Next.js prefetch exposes the route tree: `HEAD` and `__next._tree.txt` / `__next.!KGRlZmF1bHQp….__PAGE__.txt` requests for `/`, `/club/`, `/about/`, `/contact/`, `/club/free-resources/` and the resource slugs. The dynamic segment is `$d$slug` (`[slug]`). | Observation | Info (public routes only) | **By design** (Next.js `<Link>` prefetch, public routes only). | `site/src/app/` route tree |
| F15 | E9, `3f4cx_6a3wsgs.js` and `1t27yr-aialmx.js` | The privacy copy says it stores "the address of that page". The client sends the path and the query string (UTM tags, referral codes, anything). | Inference | Low | **Real leak** (Low, notice wording). `SOURCE` holds up to 120 characters of path and query string. | `channel/site/copy/en.json` (and the 14 other locales), `site/src/components/email-gate.tsx`, `site/worker/index.ts` |
| U1 | E2, E3 (`metadata.responses` empty, `attach_limited`) | Response headers (CSP, HSTS, X-Frame-Options, cache) were not captured, because REA attaches after the page loads. | Unknown | Not rated | **Resolved: real leak, Low to Medium.** H1 `HEAD /club/` returns only `cache-control: public, max-age=0, must-revalidate` and `server: cloudflare`: no CSP, HSTS, X-Frame-Options, X-Content-Type-Options or Referrer-Policy. The subscribe form can be framed. | No `_headers` file in the repo; `site/wrangler.jsonc` sets none |
| U2 | E3 (`dom_urls`) | `/llms.txt` and `/feed.xml` are linked from the page. REA did not fetch them. If they carry the pack bodies, they are one more way past the gate. | Unknown | High if they carry pack bodies | **Resolved: false positive** for these files. `llms.txt`, `llms-full.txt` and `feed.xml` list articles and link pack pages, but carry no pack bodies. The same build script does publish the bodies elsewhere: see S1. | `site/src/app/llms.txt/route.ts`, `site/src/app/feed.xml/route.ts`, `site/scripts/emit-md.mjs` |
| U3 | E4, E5 (limitation: "server-side behavior may remain unknown") | Server side of `/api/subscribe`: rate limit, double opt-in, consent logging, disposable list, what reaches Brevo. It cannot be tested without a POST, and POSTs to production are not allowed here. | Unknown | Decides F05 and F06 | **Resolved from source:** none of the four protections exist (F05, F06). `updateEnabled: true` lets anyone overwrite `LANG` and `SOURCE` on an existing contact (S3). | `site/worker/index.ts` |
| U4 | F08a | Whether `aidive-yt/aidive-resources` is public. | Unknown | Decides F08a | **Resolved: public**, and linked from the pack pages (F08a). | H1; `site/src/lib/resources.ts` |
| U5 | E2, E3 (limitations) | Traffic before REA attached (first document, cookies) is not in the REA evidence. REA keeps no cookie or header values. | Unknown | Not rated | **Resolved for cookies: none.** There is no cookie code in `site/src` or `site/worker`, and `/club/` sends no `Set-Cookie` (H1). The guard log G1 holds the full request list. | `site/src`, `site/worker` |

### Step 5 additions: outsider-reachable, found by reading the source

REA did not observe these. Each was confirmed on production with a HEAD request only (H1).

| # | Finding | Severity | Verdict | Source |
|---|---------|----------|---------|--------|
| S1 | `/club/free-resources/<slug>.md` serves each published pack as markdown, with every `{{file:…}}` inlined, and no gate. `HEAD /club/free-resources/claude-code-limit-cut-levers.md` returns `200 text/markdown`. The path follows the same pattern as the `/videos/<slug>.md` alternates that `llms.txt` advertises, so it is easy to guess. | High (the whole pack in machine-readable form) | **Real leak** | `site/scripts/emit-md.mjs` (writes `out/club/free-resources/<rslug>.md`) |
| S2 | Pack files are static assets at `/club/free-resources/<pack>/files/<name>`, with no gate. The gated page lists their download links in its DOM. `HEAD …/haiku-5-5-claude-code-routing/files/README.md` returns `200`. | Medium (the same files are public on GitHub, F08a) | **Real leak** (consistent with the public repo, but it defeats the gate) | `site/scripts/sync-assets.mjs`, `site/src/components/pages/resource-page.tsx` |
| S3 | The Worker sends Brevo `updateEnabled: true`. Resubmitting someone's address overwrites their `LANG` and `SOURCE` attributes. | Low | **Real leak** | `site/worker/index.ts` |

## Method

1. `npm i -g rea-agents@6.5.0`. The npm metadata points at `github.com/morluto/rea` and has no install hooks.
   `REA_MCP_INPUT_SCHEMA_PROFILE=compact rea setup --skill-client claude_code --yes --json` installed only the
   `reverse-engineer-anything` skill. It registers no MCP server, so REA's MCP tools did not load in this session.
   Every tool ran as its CLI equivalent: `rea list-browser-targets`, `rea inspect-web-page`, `rea analyze-web-bundle`,
   `rea capture-web-screenshot` and `rea export-web-scripts`.
2. Headless Chromium 156 ran with `--remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir=/tmp/rea-chrome`.
3. **No write reached aidive.dev.** A small CDP guard attached to every tab before it navigated.
   It let only GET, HEAD and OPTIONS through and failed every other method. It blocked 6 `POST /cdn-cgi/rum`
   attempts (the Cloudflare beacon) over two browser runs. No request to `/api/subscribe` was made,
   and no non-GET/HEAD/OPTIONS request reached aidive.dev.
   The first run had a guard bug and opened `/club/` three times (GET only). Chromium was restarted from a clean profile for the evidence above.
4. REA runs: `inspect-web-page` with `--observation-ms 3000 --include-accessibility-text --include-console-text --include-json-body-shapes --include-script-sources --include-storage-keys`.
   `analyze-web-bundle` with `--observation-ms 5000 --fetch-source-maps`. All runs were limited to `--allowed-origins https://aidive.dev`.
5. Scripts were exported to `/tmp/rea-audit/scripts-club/` and `/tmp/rea-audit/scripts-free/`, outside the repository.
   They were read with `grep` and a parser only, never executed.
6. Repository contact before step 5: one directory listing at the start of the session showed file names
   in `engine/site/` and `engine/site/worker/` (`disposable-domains.ts`, `index.ts`). No file content was opened.
7. H1 checks in step 5, all read-only: `HEAD` on `/club/`, `/club/free-resources/claude-code-limit-cut-levers.md`,
   `/club/free-resources/haiku-5-5-claude-code-routing/files/README.md` and `/llms-full.txt`.
   Anonymous `GET` on `api.github.com/repos/aidive-yt/aidive-resources` returned 200 (public).
   Anonymous `GET` on `api.github.com/repos/aidive-yt/aidive-site` returned 404 (private to outsiders).
   Because this repository is private, the F08 values are not public anywhere else.
8. No application code was changed.

## Timings

| Step | What | Time |
|------|------|------|
| 1 | Check the npm package, install REA, `rea setup` | 36 s |
| 2 | Write the CDP write guard, start Chromium, open both pages (includes one restart after the guard bug) | 1 min 47 s |
| 3 | REA: targets, inspect ×2, bundle ×2, screenshot ×2, export ×2, plus reading the evidence | 4 min 16 s |
| 4 | Write the outsider report | 1 min 32 s |
| 5 | Read the source, H1 checks, add the Verdict and Source columns | 4 min 30 s |
| | **Total** | **12 min 41 s** |
