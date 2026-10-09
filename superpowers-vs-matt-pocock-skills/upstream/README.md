# ledgerly

Small invoicing API used by the back office: customers, invoices, an outstanding-balance report.
Plain Node 20 + TypeScript, no framework. Data lives in one JSON file (`LEDGERLY_DATA`, default `data/ledgerly.json`).

```bash
pnpm install
pnpm test        # vitest
pnpm typecheck   # tsc --noEmit
```

## Layout

- `src/domain/` - invoices, customers, money, validation, domain errors. No I/O.
- `src/store/` - the JSON-file store, repositories, and the schema migrations applied on load.
- `src/http/` - a tiny router, request handlers, error-to-status mapping. `createApp()` returns a
  `handle(method, path, body)` function that the tests call directly; `src/server.ts` binds it to `node:http`.

## Conventions

- Money is always an integer number of cents. Never floats.
- Domain functions return new objects; they never mutate their input.
- Validation failures throw `ValidationError` (HTTP 400), missing records `NotFoundError` (404),
  illegal state transitions `ConflictError` (409).
- The stored file carries a `schemaVersion`. Any change to the stored shape bumps it and adds a
  migration in `src/store/migrations.ts`: production files are migrated on load, never by hand.

## Invoice lifecycle

`draft` → (`issue`) → `open` → (`pay`) → `paid`; `draft`/`open` → (`void`) → `void`.
