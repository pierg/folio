# SKILL.md: how a skill is written

Read [`model.md`](model.md) first. folio has seven skills, and the set is fixed: set-up, configure, write, organise, address, publish, run. A skill holds how to act. What is specific to a genre lives in its GENRE.md, and what is specific to a procedure lives in its WORKFLOW.md.

## Front matter

```yaml
---
name: write
description: >-
  Add or revise any document in a folio library, in its genre's voice and format.
  Use when the user asks to add, write, log, record, draft or revise a page, a note,
  a concept, a journal entry, a paper section, or any document a genre in this library covers.
---
```

The description says when to use the skill, with the user's own words for it, so an agent picks the right one. It is under 1024 characters.

## Body

- `# <name>`, then one sentence: what the skill does.
- `## Start`: always the same first steps: find the library (the nearest `folio.yaml`), read the charter, list the genres and workflows available (`folio genres`, `folio workflows`), and read the card for the genre in hand.
- `## Rules`: numbered, each one line with its reason. These bind every time.
- `## Steps`: the procedure, numbered, naming each `folio` command it runs.
- `## Stops`: when to stop and ask the owner instead of guessing, kept few.
- `## Done when`: what is true at the end. Always includes `folio check` passing.
- `## Commands`: the `folio` commands this skill uses, one line each.

## Rules for every skill

- A skill never names a particular genre except as an example. It reads genres from the library.
- A skill never edits the charter, except set-up and configure.
- A skill never writes a document directly. It goes through write, and write goes through the genre's card and the gate.
- A skill records a decision (a pack switched on, a topic merged, a genre added) as a new journal entry: `folio journal add --title .. --description .. --body .. --kind decision --about ..`. It never edits an existing entry.
- A skill that changes the library ends each change with a commit, after `folio index` and a green `folio check`. The commit holds exactly the documents touched, their annotation files (`<stem>.annotations.json`), `.folio/` (the indices and redirects are committed), the charter if it changed, and any assets or evidence the documents cite. Never `git add -A`. Lifecycles are checked against git, so an uncommitted record is not yet permanent.
- A skill is written for any coding agent that reads `.agents/skills/`, not for one product.
- Plain words, short sentences. No reference to any particular project, person or organisation.
