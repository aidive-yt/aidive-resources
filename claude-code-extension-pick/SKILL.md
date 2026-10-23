---
name: release
description: Cut a patch release of ledgerly (typecheck, tests, version bump, changelog line, commit, tag).
disable-model-invocation: true
---

Run these steps in order and stop at the first failure:

1. `pnpm typecheck` must exit 0.
2. `pnpm test` must pass.
3. Bump the patch version in `package.json` (e.g. 0.4.0 -> 0.4.1).
4. Add one line at the top of `CHANGELOG.md` (create it if missing): `## vX.Y.Z - YYYY-MM-DD` followed by a one-line summary of the commits since the last tag.
5. `git commit -am "release vX.Y.Z"`
6. `git tag vX.Y.Z`. Never push.
