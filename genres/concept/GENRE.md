---
name: concept
format: html
path: content/concepts/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  require: [defn]
  cites: { defn: none }
  defined_once: true
on_map: optional
---

# Concept

A concept defines one term, once, so that every other document can link to it instead of explaining it again.

## Earns its page

A term gets a concept when a reader would want it pinned down on its own: the idea is not trivial, and it stays true and worth looking up beyond the page where it first came up. A well-known part of a larger system can be a concept, such as the KV cache of a transformer. An implementation detail of one system as built, which would change if that system were rewritten, stays prose in the document about that system.

Use the field's name for the term when it has one. A name the library coins earns a concept only when it is clear, does not read as a better-known meaning in another field, and the page says the name is the library's (a flag, `framing`). A partition or taxonomy the library made up to organise a topic, such as its own list of categories, is not a set of concepts: it lives in the entry that frames the topic, until the field has a name for it.

How many documents link a concept is a signal, not a rule. A concept nothing links yet asks a question: should a page link it, or is the term thin enough to fold into the document that uses it? Several small terms that only make sense together are one concept, not several.

## Reader

Someone who met the term on another page and wants it pinned down. Often they read only the definition, in the popover that shows when they hover a link. They have no context beyond that definition.

## Voice

Impersonal, present tense, timeless. No "we", no "I", no story of how the term came about. The definition stays true when any result or number changes.

> The softmax turns a row of scores into weights that are positive and sum to one.

## Metadata

No fields beyond the core. The `title` is the term, as a reader would search for it. The `description` says in one sentence what the concept is for. It is not the definition: the definition lives in the `defn`.

## Shape

The shell draws the term and the description above the body. Below it the page is a canvas: lay it out around what makes the idea obvious (`craft/layout.md`).

One part is required, because the machine reads it:

- `defn`: a `<blockquote class="defn" id="{slug}">`. It opens with `<span class="defn-name">` holding the term alone. Then one to three sentences follow. This is the text other pages cite and the popover shows, so it stands alone: every symbol in it is named in it or is a `defn-link`.

What a good concept usually does, judged, not checked:

- It puts the definition beside the one figure, control or contrast that makes the idea obvious: the definition next to a diagram of the mechanism, a dial that shows the effect of a setting, a matrix that shows the rule at several scales.
- It gives a worked example the reader can follow step by step.
- It names the usual misreading, precisely.
- It says what the idea buys and where it is used, and links the neighbouring concepts.
- It is as long as the idea needs. A simple idea is its definition and one figure; a deep one adds the steps it takes to understand it. Nothing on the page says the same thing twice, and the page takes no fixed run of sections.

## Forbidden

- A citation inside the definition. Caught by `cites: { defn: none }`, which applies to the `defn` only. Sources and results may be cited anywhere below it.
- A second definition of the same term. Caught by `defined_once`: no other document carries a `defn` with the same `defn-name`.
- A prose re-explanation of the term on another page. Judged, not checked.
- A label after the term in `defn-name`, such as "Softmax, definition". Judged, not checked.
- A concept for an implementation detail of one system as built, which would change if the system were rewritten. It stays in the document about that system. Judged, not checked.
- A number that belongs to a result, stated as the concept's own. The definition stays true when any result changes. Judged, not checked.

## Steps

- Search before writing: `folio search <term>`. If the term is defined, link to it or revise it. Never add a second one.
- Ask whether the term earns its page (above). If not, explain it in a clause where it is used. The organise skill folds a thin concept into the document that uses it with `folio rm --to`.
- After writing it, replace every other explanation of the term with `<a class="defn-link" href="/content/concepts/{slug}/">`. The write skill does this sweep.
- Delete what the skeleton offers and you do not use. A placeholder left in the page is reported by the gate.
- An invented example or figure gets a flag, because the source did not say it.

## Lifecycle

Revised in place. The slug is the id and never changes; a move uses `folio mv`. A concept is born when a term earns its own page, often out of a note or an entry's section. It becomes `historical` when the library stops using the term. It becomes `retired` when merged into another concept with `folio rm --to`. When the page has become an argument about the term rather than a definition of it, the argument moves into an entry and the concept links it.

## Example

```html
<meta name="title" content="Softmax">
<meta name="description" content="The function that turns attention scores into weights.">
<style>
.sm-hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 2rem; align-items: start; }
.sm-hero > * { min-width: 0; }
@container folio-canvas (max-width: 44rem) { .sm-hero { grid-template-columns: minmax(0, 1fr); } }
</style>
<!-- body -->
<section class="sm-hero">
<blockquote class="defn" id="softmax">
<span class="defn-name">Softmax</span><br>
The softmax of a vector of scores is the exponential of each score divided by the sum of the exponentials of all of them.
</blockquote>
<figure>
<svg viewBox="0 0 320 120" role="img" aria-label="Four scores become four weights that sum to one; the largest score takes most of the weight">...</svg>
<figcaption>The largest score takes most of the weight, and every weight stays positive.</figcaption>
</figure>
</section>
<h2>The trap</h2>
<p>Computed as written, the exponentials overflow for large scores. Adding the same constant to every score leaves the result unchanged, so implementations subtract the maximum first.</p>
```
