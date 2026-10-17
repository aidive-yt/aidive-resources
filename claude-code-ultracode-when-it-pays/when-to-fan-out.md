# When to fan out: the two-condition checklist

Fan out (use the ultracode keyword in one prompt) only if both answers are yes.

1. Does a test suite or a rule set judge the output?
   - [ ] A suite that already exists and says pass or fail without anyone's opinion.
   - [ ] Or a written rule file the output is reviewed against.
2. Does the job split into independent pieces?
   - [ ] No piece waits on the result of another piece.
   - [ ] Each piece can be checked on its own.

If either answer is no, run plain at high effort. A plain run costs one bill. A
workflow costs one bill per agent.

Jobs that usually pass both tests:
- A port or migration across many files with a test suite as the judge.
- A review of a whole codebase against a rule file.
- A translation of many files with the same prompt.
- A cleanup pass over a pile of similar documents.

Jobs that usually fail one of them:
- A small feature, a bug fix, a refactor of one module.
- Anything where "good" is a matter of taste.
- A chain of steps where each one needs the previous result.

Before you start:
- [ ] Run a slice first (one folder, ten files) and read the token total.
- [ ] Put a budget in the prompt, for example "use 10k tokens".
- [ ] Open /workflows and watch per-agent tokens. Press x to stop.
- [ ] After the run, open /usage and read the share that went to workflows.
