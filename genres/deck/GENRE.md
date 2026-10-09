---
name: deck
format: html
path: content/decks/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  require: [deck, slide]
  cites: any
on_map: optional
---

# Deck

A deck carries a talk: the slides a speaker shows, in order, with what the speaker says under each.

## Earns its page

A deck exists when a talk is given, or will be, from the library's knowledge. Its slides show; the documents it rests on explain. A talk that has not been planned yet is a note or an entry first. A deck that would only restate one page as bullets is that page, presented from its own canvas.

## Reader

Two readers. The audience sees one slide at a time, for a minute or less, while someone talks. The speaker reads the notes, rehearses from them, and presents from the page.

## Voice

On a slide, as few words as carry the point: a claim as a short line, labels on a figure, a name. The notes are the talk itself, in the speaker's spoken register, plain and direct.

> The model proposes. The engine decides.

## Metadata

No fields beyond the core. The `title` is the talk's title. The `description` says in one sentence what the talk argues, for whom, and how long it runs.

## Shape

The machine reads two parts:

- `deck`: one `<div class="deck">` in `<main>`. `data-theme="dark"` or `"light"` fixes the slides' theme whatever the reader's; without it they follow the page.
- `slide`: each `<section class="slide">` directly inside it, in order. A slide is drawn at 1600 by 900 pixels and scaled to fit, so its own styles lay it out in pixels, absolutely or in a grid.

Inside a slide, by convention, judged, not checked:

- One `<h2>` names the slide. The page's outline lists them, so the outline is the talk's running order.
- `<aside class="notes">` holds what the speaker says. The page shows it under the slide; Present hides it, and the presenter's window shows it beside the slide. Notes may be structured: `<ul class="points">`, the talking points to cover, beside `<div class="script">`, the words to say. H, or the bar's button, hides every script, to rehearse from the points alone. `<span class="cue">click</span>` in a script marks where the next build comes.
- `data-step="n"` on an element makes it appear at the nth build of its slide; `data-until="n"` makes it leave after the nth. The slide carries `data-at`, its current build, for styles that change with it. The page shows each slide complete.

What a good deck usually does, judged, not checked:

- One idea per slide, and the slide shows it: a figure, a contrast, a sequence that builds.
- A visual vocabulary held across slides: the same mark for the same thing, a colour per part of the talk (`craft/figures.md`).
- Every claim a slide makes rests on a library document the deck links, from the notes or the slide.

## Forbidden

- A deck that cites nothing. Caught by `cites: any`: the talk rests on the library's documents.
- A slide that is a page of text. Judged, not checked: the notes carry the words, the slide carries the point.
- Words written by a script. The shell's rule, judged, not checked (`shell/COMPONENTS.md`): every word is in the markup, so comments, search and the gate read it.
- A number on a slide that no document holds. Judged, not checked; cite the document that holds it.

## Steps

- Start from the talk's outline: one line per slide saying what the audience should keep. Write the notes before the slide: the points first, three to five, then the script that says them.
- Design the slides as a set: decide the recurring marks and colours first, then draw each slide with them.
- Present it once from the page (P), and once with the presenter's window (S), before calling it done.

## Lifecycle

Revised in place until the talk is given. A talk given and kept as it was becomes `historical`, with its description saying when and where. A later talk on the same subject is a new deck; the old one may be `retired` into it with `folio rm --to`.

## Example

```html
<meta name="title" content="Why the gate sits below the model">
<meta name="description" content="A five-minute talk for engineers: why an agent's actions are decided in code, not by the model.">
<!-- body -->
<div class="deck" data-theme="dark">
  <section class="slide">
    <h2>A prompt is a request</h2>
    <p class="kx-line" data-step="1">A gate is not.</p>
    <aside class="notes"><p>A model that has been fooled stops honouring requests. A gate in code does not care who asked.</p></aside>
  </section>
</div>
```
