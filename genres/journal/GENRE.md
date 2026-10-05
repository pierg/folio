---
name: journal
format: markdown
path: content/journal/{yyyy}/{date}-{slug}.md
id: slug
skeleton: skeleton.md
lives: permanent
states: [live]
fields:
  - { name: date, type: date, required: true }
  - { name: kind, type: string }
  - { name: about, type: ids }
checks:
  kinds: [decision, lesson, correction, retraction]
  max_words: 150
on_map: exempt
---

# Journal

A journal entry records one thing that happened or was decided, on its date, and is never edited.

## Reader

The owner, or a collaborator, later. They want to know when something changed and why. They read it to reconstruct a decision, not for pleasure.

## Voice

Terse. Past tense for what happened, present tense for what holds from now on. One entry, one event. Cite documents by link or id; never restate their content.

> The masked softmax overflowed in half precision. The kernel now subtracts the row maximum first.

## Metadata

- `date`: the day of the event, `YYYY-MM-DD`. Required. It is the day the event happened, which can differ from the day of the commit.
- `kind`: optional. The shell filters the timeline by it, and a `correction` or `retraction` shows as a banner on what it names. The core has four kinds. A `decision` is a choice that binds later work. A `lesson` is something learned the hard way. A `correction` says a document or an earlier entry was wrong, and what is true instead. A `retraction` withdraws a record. A pack adds its own kinds while it is on, and the charter adds more under `journal.kinds`. An entry with no kind is a plain event.
- `about`: the ids of the documents the entry concerns. The entry shows on each of them.
- The `title` is the event in a few words. The `description` says in one line what happened.
- No `status`: the entry is permanent, so the engine derives it.

## Shape

The file is Markdown: the front matter, then a body of one to five short lines. The body says what happened, why, and what it changes. It links the documents involved. It has no headings.

A library has one journal: every entry is its own file under `content/journal/{yyyy}/`. The shell renders them as one timeline, newest first, filtered by kind, tag, date or `about`. The set-up skill writes the first entry. The configure and organise skills record their decisions as entries.

## Forbidden

- Editing or deleting an entry once it is committed. Caught by `permanent`, which compares the file with its first commit.
- A missing or malformed `date`, or an `about` that names no document. Caught by `fields`.
- A `status` field. Caught by `fields`: a permanent document writes none.
- A kind the library does not accept. Caught by `kinds`, which accepts the core's four, the kinds of every pack switched on, and the charter's `journal.kinds`. A library adds a kind through the configure skill.
- A body longer than 150 words. Caught by `max_words`. A long story belongs in a document the entry links to.
- More than one event in an entry. Write two entries. Judged, not checked.
- A definition, number or argument written out in full. Judged, not checked. Link the document that holds it.

## Steps

- Write an entry with `folio journal add --title ".." --description ".." --body ".." [--kind <kind>] [--about <id>,..] [--date <date>] [--tags ..]`. It writes one new file, named from the date and the title's first six words, and never edits an existing one.
- Give `--date` when the event happened on another day than today.
- Name in `--about` every document the entry concerns, so it shows on each.
- To correct a document or an earlier entry, add a new entry of kind `correction`, with `about` naming it, and say what is true instead. To withdraw a record, add one of kind `retraction`. Never edit the original.

## Lifecycle

Permanent. An entry is written once and never changed. Its status is derived, and is always `live`. A later correction about it shows as a banner on it. It is exempt from the no-orphans rule, so no map lists it. Links from the journal do not count toward the no-orphans rule.

## Example

```markdown
---
title: The softmax overflowed in half precision
description: Long rows of large scores overflowed, so the kernel now subtracts the row maximum first.
genre: journal
date: 2026-10-03
kind: lesson
about: [attention-kernel, softmax]
tags: [attention, numerics]
---

Rows of large attention scores overflowed to infinity in half precision.
The kernel now subtracts each row's maximum before the exponential; see [softmax](/content/concepts/softmax/).
```
