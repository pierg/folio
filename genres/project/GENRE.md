---
name: project
format: html
path: content/projects/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, paused, done, historical, retired]
fields:
  - { name: reviewed, type: date, required: true }
checks:
  require: [state, next]
  stale_after_days: 90
  max_words: 800
on_map: required
---

# Project

A project page says where a piece of work stands now: what is true, and what is next.

## Reader

Someone who wants the state of the work, not the ideas behind it. Often it is the owner, back after a break.

## Voice

Operational, present tense. Short lines. It says what is true on the date it was last reviewed, and expects to go out of date.

> The forward pass matches the reference, and the backward pass is next.

## Metadata

- `reviewed`: the date the state was last confirmed true, `YYYY-MM-DD`. The shell shows it in the header. It changes on every revision, even when only the next steps changed.
- The `title` is the project's name. The `description` says in one sentence what the project is and what it produces.

## Shape

The shell draws the title, description, status and `reviewed` date above the body. The generated panels show the journal entries about the project, what it cites and what cites it. So the body never lists its decisions or its documents.

1. `state`: a `<p class="state">` that opens the body. It says, in one or two sentences, what is true on the `reviewed` date.
2. `next`: `<h2 id="next">Next</h2>` and a short list of the next steps.
3. Blocked, optional: `<h2 id="blocked">Blocked</h2>`, what is waiting, and on what.
4. Code, optional: `<h2 id="code">Where the code lives</h2>`, links to the repositories and other places outside the library where the work happens.

A page that belongs to this project, such as a plan, is a document of the genre that fits it, in that genre's folder. The state or the next steps link it where it matters.

## Forbidden

- A missing or malformed `reviewed` date. Caught by `fields`.
- A `reviewed` date older than 90 days on a `live` project. Caught by `stale_after_days`, as a warning. Review it, or set the status to `paused` or `done`.
- History and narrative. The journal holds what happened and what was decided. Caught in part by `max_words`; the rest is judged, not checked.
- A list of decisions, lessons or the project's documents. The generated panels show them. Judged, not checked.
- A decision recorded only here. Decisions go in the journal, about this project. Judged, not checked.
- A definition or number restated as this page's own. Link the document that holds it. Judged, not checked.

## Steps

- Every revision sets `reviewed` to today, even when only the next steps changed.
- Record each decision in the journal first, then update this page: `folio journal add --kind decision --about <slug> --title ".." --description ".." --body ".."`. A lesson is an entry of kind `lesson` about the project.
- Keep `next` short. Five items is plenty; the rest belongs in a plan the page links.
- Add the project to at least one map, often a map of the projects.

## Lifecycle

Revised in place, and always reviewed. A project is `live` while work goes on. It is `paused` when work stops for a while, with the state saying why. It is `done` when it shipped or ended, with the state saying what came of it. Later it may become `historical`. A project merged into another is `retired` into it with `folio rm --to`.

## Example

```html
<meta name="title" content="Attention kernel">
<meta name="description" content="A tiled attention kernel for long sequences, checked against a reference implementation.">
<meta name="reviewed" content="2026-10-03">
<!-- body -->
<p class="state">The forward pass matches the reference implementation; the backward pass is not written.</p>
<h2 id="next">Next</h2>
<ul><li>Write the backward pass, and check its gradients against the reference.</li></ul>
```
