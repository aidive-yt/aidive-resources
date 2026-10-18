# Skill description template

The description is the one line Claude reads before it decides to load your skill. Write it for the moment you ask, not for the file.

## Template

```
<Verb in third person> <what the skill produces>, <how it is shaped>. Use when the user asks <phrase 1>, <phrase 2>, <phrase 3>, or <phrase 4>.
```

Three parts, in this order:

1. What it does. Third person ("Writes", never "I can" or "You can use this"). Name the output.
2. When to use it. Start with "Use when the user asks".
3. Your words. The exact phrases you or your team type, copied from your own history, not synonyms you invented.

Put the key use case first. The description and `when_to_use` are cut together at 1,536 characters in the skill listing.

## Worked example (the real one from our run)

Before, a summary of the skill:

```
Generates changelog documents from repository history.
```

After, what + when + the words we type:

```
Writes this week's release notes from git log, grouped by scope (router, css, jsx). Use when the user asks what we shipped, what changed this week, for release notes, a changelog, or a summary of recent commits.
```

What changed:

- What: "Writes this week's release notes from git log, grouped by scope".
- When: "Use when the user asks ...".
- Your words: "what we shipped", "what changed this week", "release notes", "a changelog", "a summary of recent commits".

## Fill-in sheet

- Skill name:
- The prompt I keep retyping (copy it from your history):
- The output I want from it:
- Verb + output (what it does):
- Four phrases I really type (when):
- Phrases that sound close but are a different job (for your near misses):

## Check before you save

- Third person, no "I" and no "you".
- At least three phrases you really type.
- Under 1,536 characters in total.
- Not so wide that it matches a neighbour job. Add the near misses to your trigger test.
