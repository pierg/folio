---
name: note
format: html
path: content/notes/{slug}.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  cites: any
  min_links: 1
on_map: optional
---

# Note

A note states one idea or claim, with its reason, as a node other documents can link to.

## Earns its page

A note holds one lesson worth keeping: a claim that would change a decision or how something is read, and that the library does not already state. A remark that restates a concept's definition, or a fact with no consequence, stays a sentence in the document that needs it.

## Reader

Someone who already knows the domain. They want the thought, not the background.

## Voice

Assertive and plain. State the claim as if it is true, and give the reason in the same breath. No hedging, no warm-up.

> Keep a running maximum and a running sum per row, and the softmax comes out exact one tile at a time.

## Metadata

No fields beyond the core. The `title` is a short name for the idea. The `description` states the claim itself, in one sentence, as true. Search results and map rows show it, so it must stand alone.

## Shape

The shell draws the title and the claim above the body. Below it the page is a canvas, and a note usually needs little of it.

What a good note usually does, judged, not checked:

- It gives the reason and the consequence in a few paragraphs, or shows them in one figure or contrast with a sentence or two beside it.
- It links at least one other document. Terms link to their concepts with `class="defn-link"`.

## Forbidden

- A note that links to nothing. Caught by `min_links`.
- More than one claim. Judged, not checked. Split it into two notes.
- A note that has grown into an argument in several steps. Judged, not checked: promote it into an entry.
- Scaffolding such as "In this note I will". Judged, not checked.
- Hedging the claim into a question. Judged, not checked. An open question belongs on a map or a project.

## Steps

- Check the claim is not already a note: `folio search <words>`. If it is, revise that note.
- Link out generously. A note is useful through its links, and its backlinks are generated.
- A term the note explains in passing, and some other page also explains, becomes a concept.

## Lifecycle

Revised in place. A note that grows sections is promoted to an entry with `folio promote <doc> entry`. A note whose claim turned out wrong is marked `historical`, with a sentence saying why, or `retired` into the note that replaced it.

## Example

```html
<meta name="title" content="FlashAttention tiling">
<meta name="description" content="Attention computed one tile of keys at a time is exact, because the softmax can be rescaled as it goes.">
<!-- body -->
<p>Each tile of keys updates a running maximum and a running sum per query row. When the maximum grows, the partial <a class="defn-link" href="/content/concepts/softmax/">softmax</a> is rescaled, so the result is exact and the full matrix of scores is never stored.</p>
```
