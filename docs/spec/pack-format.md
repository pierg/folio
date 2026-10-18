# PACK.md and WORKFLOW.md

Read [`model.md`](model.md) first. A pack is data: genres, workflows and rules. It never contains a skill.

## PACK.md

```yaml
---
name: lab
version: 0.1.0
requires: { folio: ">=0.1.0" }
genres: [question, protocol, result, claim, report]
workflows: [record-a-result, write-a-report]
rules: rules.md
journal_kinds: [lock, run, kill, instrument, pivot]   # kinds the journal accepts while the pack is on
---
```

The body says, in plain sentences:

- `# <Name>`: what kind of work this pack is for, in one sentence.
- `## What it adds`: each genre and workflow in one line, each rule, and each journal kind.
- `## When to switch it on`: the kind of library that needs it, and what a library without it loses.
- `## What switching it on changes`: what the rules flag in an existing library, and how the organise skill proposes the fixes.
- `## Working with other packs`: anything a reader of two packs together should know.

## WORKFLOW.md

A workflow is one file, `workflows/<name>.md`.

```yaml
---
name: ingest
pack: knowledge-base
summary: Bring one source into the library as a source, a reading, and any new concepts.
inputs:                       # what the run skill asks for, if the request didn't give it
  - source: a URL, a file, or a citation
  - map: (optional) the map it belongs on
produces: [source, reading, concept, map-row]
---
```

Each input is `name: description`. An input marked `(optional)` is never asked for. The run skill takes every input the request already gives, and asks in one message only for the required ones still missing.

A workflow that produces a record accepts each of the record's fields as an input. It also accepts `from`: a YAML file holding any of those fields under the same names, optionally with `#<key>` to pick one entry in it. A tool built on folio can write such a file. A value given directly wins over the file's.

The body:

- `# <Name>`, then one sentence: what you ask for and what you get.
- `## Steps`: numbered. Each step names the skill or command it uses. Every document is produced through the write skill, never written by hand. A workflow that commits makes the commit its last step, after the map rows, `folio index` and a green `folio check`.
- `## Stops`: when the workflow stops and asks the owner instead of guessing.
- `## Done when`: what is true at the end, including the gate passing.

## rules.md

Each rule is a heading, a sentence saying what it requires, the check name the gate uses, and its default severity. Rule checks are library-wide, and their names are kebab-case. Every name is listed in [`checks.md`](checks.md).

```markdown
## Every number cites a result

A number on a page or in a paper that reports a measurement links to the result that holds it.

- check: `uncited-number`
- default: warning in a new library, error once the charter sets it
```
