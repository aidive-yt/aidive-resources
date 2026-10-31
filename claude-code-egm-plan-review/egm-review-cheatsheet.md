# EGM review cheat sheet

## The commands, in order

1. `/egm:egm-brainstorm <the feature in one sentence>` writes `concepts_brief.md`.
2. `/egm:egm-draft` writes the design document, one section at a time. You approve each section.
3. `/egm:egm-review <design>` runs the five review stages (below). Pick the consolidated mode to get one merged list.
4. `/egm:egm-resolve` turns the reports into one table of issues. You answer each one.
5. Open a fresh session and send:

```
Build the feature exactly to the approved design in docs/egm/<file>.md; add tests.
```

## The five review stages and their report files

| Stage | What it asks | Report file |
|---|---|---|
| 1. Initial Zoom Out Review | Does the design solve the right problem? | `zoom_out_report.md` |
| 2. Comprehension Review | Would a newcomer understand it? | `comprehension_report.md` |
| 3. Design Critique | Attacks the design, its structure and its wording | `critic_report.md` |
| 4. Intermediate Zoom Out Review | Zooms out again on the unedited design | `intermediate_zoom_out_report.md` |
| 5. Implementation Readiness | Checks each step against your real code | `implementation_readiness_report.md` |

The consolidated mode also writes `consolidated_review_report.md`. Resolve writes `goldfish_review_report.md`.

## What resolve's suggestions mean

- ESCALATE: the reviewers found a decision only you can make.
- CONTEST: the agent thinks the finding is wrong or the fix is too weak, and says why. You can still overrule it.
- DECLINE: the agent proposes not acting on the finding.
- PROPOSE FIX: the agent proposes an edit to the design.
- "auto accept": reply with these two words to batch-apply every PROPOSE FIX and skip CONTEST items. Decide the escalated issues first.

## Reviewer settings (Claude adapters)

```
tools: [Read, Grep, Glob]
model: inherit
omitClaudeMd: true
```

Read-only tools, the same model as your session, and no CLAUDE.md or other instruction files. This is context and tool isolation, not filesystem isolation: reviewers can read accessible files.

## Before you build

Reviewers read documents. They do not run code. If your design relies on an outside service behaving a certain way, run a check against a copy of the real thing before you ship.
