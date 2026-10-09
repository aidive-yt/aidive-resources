# flow-bench findings (2026-10-09, round 2: isolated work copies, Sonnet 5.5 headless, 19 counted runs)

**F1 (partial payments): quality did not separate.** All 13 F1 runs hidden 5/5, suite and tsc green.
Cost per run: bare $0.27 (bare-r2) to $0.47 (bare-r1); sp, hook-routed, $0.44 (sp-r1) to $0.54 (sp-r2); mp $1.80
(mp-r2) to $2.22 (mp-r1); spd, Superpowers driven, $3.39 (spd-r2) to $4.41 (spd-r3).
Wall: mp 365 to 480 s (mp-r2, mp-r3), spd 520 to 701 s (spd-r2, spd-r3).

**Where the money goes.** mp-r2 (complete flow): grill $0.16, spec $0.11, tickets $0.09, implement $0.96, code-review
$0.45, pr $0.04 (F1 means: implement $1.13, code-review $0.44). spd: brainstorming $0.17, writing-plans $0.27,
executing-plans $3.31 (F1 means). Inside executing-plans the build itself (TDD in session) costs $0.97 on average; the
rest is the one whole-branch reviewer the skill dispatches "on the most capable model", which ran on claude-fable-5-1
in all five spd runs: $2.01 of spd-r1's $3.41, $2.52 of spd-r3's $4.41, $1.57 of f2-spd-r2's $3.00.

**Hook vs driven.** Left to its hook, Superpowers ran brainstorming in sp-r1, sp-r2 and sp-r3 and then coded; writing-
plans ran 0 times in 3. Driven by slash commands, the full loop ran in every spd run and cost 7.4 times more (F1 means: spd $3.74, sp $0.50). The cost is the final review, not the planning.

**F2 (credit notes) separated, barely.** f2-bare-r1 shipped one missing requirement, R3: credit-note numbers are not
gapless. It took the number before validating, like the existing `/issue` route, so rejected requests burned numbers
(CN-0004 where CN-0002 was due; the F2 bare smoke failed the same way). f2-bare-r2, f2-spd-r1, f2-spd-r2, f2-mp-r1 and
f2-mp-r2 scored 5/5. Costs: bare $0.38/$0.45, mp $2.18/$1.95, spd $3.42/$3.00 (r1/r2). Caveat: the first F2 oracle
also required credit notes on open invoices; both bare runs allowed paid invoices only, which the request's wording
permits, so that check was removed and the F2 runs rescored.

**Stacking broke nothing.** both-r1: hook injected, no Superpowers skill invoked, $2.33, inside the mp range.

**Caps.** mp-r1, mp-r3 and f2-mp-r1 hit the 12-driver-turn cap before /pr. spd never needed more than 8 turns.

**Caveats.** Round-1 runs read this repo's CLAUDE.md (parent-directory loading), so they were discarded and rerun outside the repo. A simulated PO answers each round in one message. The SessionStart hook fires on turn 1 only.
/implement covers every ticket in one turn. 5 to 11 compound shell lines per spd run were denied. PO cost is excluded.
