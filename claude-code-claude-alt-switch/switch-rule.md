# The switch rule

Keep this next to the claude-alt alias. Decide before your limit hits, not while you wait.

## Goes to claude-alt (local model)

- A job in one file that you can check at a glance
- Adding an option, explaining a function, testing one function
- Work where a wrong result is visible in one short diff

## Waits for the plan

- Anything that crosses files, such as a rename with callers in other modules
- Anything you cannot check by reading the diff
- Work that depends on your hooks or your project rules (the alias runs with --bare, which skips both)
- Long sessions

## Always

- Read the diff before you commit, whichever model wrote it
- After a rename, import the old names by hand. A green test run only covers what the tests cover

## Why this rule

Two tasks on a 16 GB M1 Pro with qwen3.5:9b:

- One file (add a --prefix option): passed in 93 s with --bare.
- Across files (rename a function, keep the old name as an alias): the model said the tests were green, and an import was broken in both runs.
- On the plan, Claude did the rename in 38 s with both the old and the new imports working.

Two tasks on one small package is a starting point. Widen the rule with your own runs.
