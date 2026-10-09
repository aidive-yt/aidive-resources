# flow-bench results

Untagged runs only (smoke/validation excluded). Tokens = input + output + cache read + cache write, all models, subagents included. USD = list-price equivalent from `total_cost_usd` deltas (plan quota, not a bill). Wall = sum of worker turn walls (PO time excluded). Diff = lines added+removed vs the base commit, src/ + test/.

## Per config (mean / median)

| task / config | n | hidden /5 (per run) | suite green | tsc green | code diff +/- | all files diff | tests added | tokens | USD | wall s | driver turns | questions | caps hit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 / bare | 3 | 5 / 5 (5,5,5) | 3/3 | 3/3 | 141.667 / 137 | 142.333 | 4.667 | 519,114 / 361,842 | 0.343 / 0.286 | 84.5 / 71.7 | 1.333 | 0.333 | none |
| F1 / sp (hook-routed) | 3 | 5 / 5 (5,5,5) | 3/3 | 3/3 | 235 / 227 | 237 | 12.333 | 724,601 / 765,108 | 0.502 / 0.525 | 118.1 / 119.6 | 2.667 | 1.667 | none |
| F1 / spd (Superpowers driven) | 3 | 5 / 5 (5,5,5) | 3/3 | 3/3 | 386 / 371 | 582 | 27.667 | 4,479,876 / 3,887,015 | 3.738 / 3.412 | 607.367 / 600.8 | 7 | 4 | none |
| F1 / mp (Main Flow) | 3 | 5 / 5 (5,5,5) | 3/3 | 3/3 | 372 / 369 | 578 | 27.667 | 4,476,104 / 4,286,993 | 2.043 / 2.102 | 439.033 / 472.4 | 12 | 7 | mp-r1: driver_turns_12; mp-r3: driver_turns_12 |
| F1 / both (sp+mp, mp flow) | 1 | 5 / 5 (5) | 1/1 | 1/1 | 374 / 374 | 561 | 22 | 5,754,354 / 5,754,354 | 2.326 / 2.326 | 448.2 / 448.2 | 12 | 6 | none |
| F2 / bare | 2 | 4.5 / 4.5 (4,5) | 2/2 | 2/2 | 206.5 / 206.5 | 209.5 | 5 | 651,322 / 651,322 | 0.413 / 0.413 | 103.15 / 103.15 | 2 | 0.5 | none |
| F2 / spd (Superpowers driven) | 2 | 5 / 5.0 (5,5) | 2/2 | 2/2 | 488.5 / 488.5 | 750.5 | 33 | 4,490,365 / 4,490,365 | 3.213 / 3.213 | 511.7 / 511.7 | 6.5 | 3.5 | none |
| F2 / mp (Main Flow) | 2 | 5 / 5.0 (5,5) | 2/2 | 2/2 | 469 / 469.0 | 658 | 31 | 4,520,638 / 4,520,638 | 2.067 / 2.067 | 421.2 / 421.2 | 12 | 6.5 | f2-mp-r1: driver_turns_12 |

Requirement pass counts (runs passing each hidden req):

- **F1 bare**: req1 3/3, req2 3/3, req3 3/3, req4 3/3, req5 3/3
- **F1 sp (hook-routed)**: req1 3/3, req2 3/3, req3 3/3, req4 3/3, req5 3/3
- **F1 spd (Superpowers driven)**: req1 3/3, req2 3/3, req3 3/3, req4 3/3, req5 3/3
- **F1 mp (Main Flow)**: req1 3/3, req2 3/3, req3 3/3, req4 3/3, req5 3/3
- **F1 both (sp+mp, mp flow)**: req1 1/1, req2 1/1, req3 1/1, req4 1/1, req5 1/1
- **F2 bare**: req1 2/2, req2 2/2, req3 1/2, req4 2/2, req5 2/2
- **F2 spd (Superpowers driven)**: req1 2/2, req2 2/2, req3 2/2, req4 2/2, req5 2/2
- **F2 mp (Main Flow)**: req1 2/2, req2 2/2, req3 2/2, req4 2/2, req5 2/2

## F1 spd (Superpowers driven) per slash-command stage (turn level, exact) (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| /brainstorming | 3 | 182,022 | 160,834 | - | 0.166 | 0.156 | 40.283 | 35.44 |
| /writing-plans | 3 | 321,355 | 298,267 | - | 0.266 | 0.274 | 88.133 | 95.82 |
| /executing-plans | 3 | 3,976,500 | 3,427,914 | - | 3.307 | 3.028 | 478.95 | 453.89 |

## F1 spd per skill in force (within-turn split) (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| brainstorming | 3 | 182,022 | 160,834 | 4,161 | 0.166 | 0.156 | 38.8 | 33.6 |
| writing-plans | 3 | 321,355 | 298,267 | 11,827 | 0.266 | 0.274 | 86.733 | 95.1 |
| executing-plans | 3 | 66,938 | 68,739 | 505 | 0.047 | 0.047 | 4.6 | 4.6 |
| test-driven-development | 3 | 2,927,098 | 2,854,967 | 22,508 | 0.974 | 0.936 | 457.033 | 448.9 |
| finishing-a-development-branch | 1 | 976,505 | 976,505 | 5,297 | 0.282 | 0.282 | 50.7 | 50.7 |
| test-driven-development [subagent] | 3 | 656,962 | 565,811 | 20,918 | 2.192 | 2.047 | 0.0 | 0.0 |

## F1 sp (hook-routed) per phase (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| before any skill | 3 | 19,549 | 19,538 | 238 | 0.03 | 0.03 | 5.333 | 5.4 |
| brainstorming | 3 | 249,260 | 247,900 | 8,037 | 0.219 | 0.244 | 40.533 | 40.1 |
| implementation (no skill) | 2 | 386,028 | 386,028 | 5,080 | 0.176 | 0.176 | 60.3 | 60.3 |
| execution | 1 | 595,318 | 595,318 | 15,622 | 0.405 | 0.405 | 93.0 | 93.0 |

## F1 sp (hook-routed) per skill in force (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| (none) | 3 | 19,549 | 19,538 | 238 | 0.03 | 0.03 | 5.333 | 5.4 |
| brainstorming | 3 | 249,260 | 247,900 | 8,037 | 0.219 | 0.244 | 40.533 | 40.1 |
| test-driven-development | 1 | 595,318 | 595,318 | 15,622 | 0.405 | 0.405 | 93.0 | 93.0 |
| implementation (no skill) | 2 | 386,028 | 386,028 | 5,080 | 0.176 | 0.176 | 60.3 | 60.3 |

## F1 mp per slash-command stage (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| /grill-with-docs | 3 | 316,507 | 348,862 | 5,999 | 0.204 | 0.215 | 59.933 | 59.9 |
| /to-spec | 3 | 163,344 | 167,578 | 5,135 | 0.118 | 0.113 | 42.1 | 40.8 |
| /to-tickets | 3 | 257,955 | 268,062 | 5,867 | 0.143 | 0.151 | 44.4 | 47.8 |
| /implement | 3 | 2,655,565 | 2,613,062 | 30,215 | 1.125 | 1.195 | 224.567 | 245.4 |
| /code-review | 3 | 1,047,586 | 1,107,555 | 9,294 | 0.439 | 0.445 | 64.2 | 65.8 |
| /pr | 1 | 105,440 | 105,440 | 1,349 | 0.041 | 0.041 | 11.6 | 11.6 |

## F1 both per slash-command stage (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| /grill-with-docs | 1 | 344,391 | 344,391 | 6,193 | 0.225 | 0.225 | 61.8 | 61.8 |
| /to-spec | 1 | 217,572 | 217,572 | 4,835 | 0.123 | 0.123 | 42.9 | 42.9 |
| /to-tickets | 1 | 382,953 | 382,953 | 7,115 | 0.196 | 0.196 | 49.4 | 49.4 |
| /implement | 1 | 3,070,579 | 3,070,579 | 24,618 | 1.112 | 1.112 | 194.2 | 194.2 |
| /code-review | 1 | 1,615,265 | 1,615,265 | 13,410 | 0.625 | 0.625 | 86.8 | 86.8 |
| /pr | 1 | 123,594 | 123,594 | 1,461 | 0.045 | 0.045 | 13.1 | 13.1 |

## F2 spd (Superpowers driven) per slash-command stage (turn level, exact) (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| /brainstorming | 2 | 485,364 | 485,364 | - | 0.354 | 0.354 | 96.815 | 96.815 |
| /writing-plans | 2 | 166,012 | 166,012 | - | 0.159 | 0.159 | 49.755 | 49.755 |
| /executing-plans | 2 | 3,838,988 | 3,838,988 | - | 2.7 | 2.7 | 365.1 | 365.1 |

## F2 spd per skill in force (within-turn split) (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| brainstorming | 2 | 253,890 | 253,890 | 6,038 | 0.207 | 0.207 | 53.05 | 53.05 |
| writing-plans | 2 | 397,486 | 397,486 | 14,060 | 0.307 | 0.307 | 90.75 | 90.75 |
| executing-plans | 2 | 69,973 | 69,973 | 286 | 0.046 | 0.046 | 3.5 | 3.5 |
| test-driven-development | 2 | 3,304,676 | 3,304,676 | 23,244 | 1.052 | 1.052 | 361.25 | 361.25 |
| test-driven-development [subagent] | 2 | 464,339 | 464,339 | 13,017 | 1.602 | 1.602 | 0.0 | 0.0 |

## F2 mp per slash-command stage (mean over the runs that had the stage)

| stage | runs | tokens mean | tokens median | out tokens | USD mean | USD median | wall s mean | wall s median |
|---|---|---|---|---|---|---|---|---|
| /grill-with-docs | 2 | 232,965 | 232,965 | 5,946 | 0.182 | 0.182 | 56.7 | 56.7 |
| /to-spec | 2 | 180,084 | 180,084 | 4,452 | 0.115 | 0.115 | 37.6 | 37.6 |
| /to-tickets | 2 | 253,688 | 253,688 | 5,152 | 0.131 | 0.131 | 38.5 | 38.5 |
| /implement | 2 | 2,689,071 | 2,689,071 | 31,452 | 1.159 | 1.159 | 218.35 | 218.35 |
| /code-review | 2 | 1,107,122 | 1,107,122 | 9,454 | 0.458 | 0.458 | 63.85 | 63.85 |
| /pr | 1 | 115,414 | 115,414 | 1,372 | 0.043 | 0.043 | 12.4 | 12.4 |

## Per run

| run | task | hidden | reqs failed | suite | tsc | code +/- | tests added | tokens | USD | wall s | turns | end | skills (first use order) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bare-r1 | F1 | 5/5 | - | green | ok | +149/-11 | 6 | 840,751 | 0.47 | 119 | 2 | done | - |
| bare-r2 | F1 | 5/5 | - | green | ok | +118/-10 | 4 | 354,748 | 0.27 | 63 | 1 | done | - |
| bare-r3 | F1 | 5/5 | - | green | ok | +125/-12 | 4 | 361,842 | 0.29 | 72 | 1 | done | - |
| sp-r1 | F1 | 5/5 | - | green | ok | +182/-15 | 10 | 613,434 | 0.44 | 99 | 3 | done | brainstorming |
| sp-r2 | F1 | 5/5 | - | green | ok | +212/-15 | 13 | 765,108 | 0.54 | 120 | 2 | done | brainstorming > test-driven-development |
| sp-r3 | F1 | 5/5 | - | green | ok | +267/-14 | 14 | 795,260 | 0.52 | 135 | 3 | done | brainstorming |
| spd-r1 | F1 | 5/5 | - | green | ok | +350/-21 | 21 | 3,667,286 | 3.41 | 601 | 6 | done | test-driven-development |
| spd-r2 | F1 | 5/5 | - | green | ok | +317/-16 | 36 | 3,887,015 | 3.39 | 520 | 7 | done | test-driven-development |
| spd-r3 | F1 | 5/5 | - | green | ok | +434/-20 | 26 | 5,885,328 | 4.41 | 701 | 8 | done | test-driven-development > finishing-a-development-branch |
| mp-r1 | F1 | 5/5 | - | green | ok | +349/-20 | 29 | 5,098,503 | 2.22 | 472 | 12 | cap_driver_turns (driver_turns_12) | grilling > domain-modeling > tdd > code-review |
| mp-r2 | F1 | 5/5 | - | green | ok | +314/-15 | 25 | 4,042,815 | 1.80 | 365 | 12 | done | grilling > domain-modeling > tdd > code-review |
| mp-r3 | F1 | 5/5 | - | green | ok | +395/-23 | 29 | 4,286,993 | 2.10 | 480 | 12 | cap_driver_turns (driver_turns_12) | grilling > domain-modeling > tdd > code-review |
| both-r1 | F1 | 5/5 | - | green | ok | +356/-18 | 22 | 5,754,354 | 2.33 | 448 | 12 | done | grilling > domain-modeling > tdd > code-review |
| f2-bare-r1 | F2 | 4/5 | req3 | green | ok | +204/-10 | 5 | 494,231 | 0.38 | 92 | 1 | done | - |
| f2-bare-r2 | F2 | 5/5 | - | green | ok | +189/-10 | 5 | 808,413 | 0.45 | 115 | 3 | done | - |
| f2-spd-r1 | F2 | 5/5 | - | green | ok | +546/-14 | 46 | 5,310,616 | 3.42 | 506 | 6 | done | writing-plans > test-driven-development |
| f2-spd-r2 | F2 | 5/5 | - | green | ok | +401/-16 | 20 | 3,670,114 | 3.00 | 517 | 7 | done | test-driven-development |
| f2-mp-r1 | F2 | 5/5 | - | green | ok | +460/-23 | 31 | 4,823,516 | 2.18 | 443 | 12 | cap_driver_turns (driver_turns_12) | grilling > domain-modeling > tdd > code-review |
| f2-mp-r2 | F2 | 5/5 | - | green | ok | +440/-15 | 31 | 4,217,761 | 1.95 | 399 | 12 | done | grilling > domain-modeling > tdd > code-review |
