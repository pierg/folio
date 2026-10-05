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
  forbid: [h2]
  max_words: 250
  cites: { defn: none }
  defined_once: true
on_map: optional
---

# Concept

A concept defines one term, once, so that every other document can link to it instead of explaining it again.

## Reader

Someone who met the term on another page and wants it pinned down. Often they read only the definition, in the popover that shows when they hover a link. They have no context beyond that definition.

## Voice

Impersonal, present tense, timeless. No "we", no "I", no story of how the term came about. The definition stays true when any result or number changes.

> The softmax turns a row of scores into weights that are positive and sum to one.

## Metadata

No fields beyond the core. The `title` is the term, as a reader would search for it. The `description` says in one sentence what the concept is for. It is not the definition: the definition lives in the `defn`.

## Shape

The shell draws the term and the description above the body. The body starts with the definition.

1. `defn`: a `<blockquote class="defn" id="{slug}">`. It opens with `<span class="defn-name">` holding the term alone. Then one to three sentences follow. This is the sentence other pages cite and the popover shows. Every symbol in it is named in it or is a `defn-link`.
2. A figure, optional. One `<figure>` that makes the idea obvious, with a `<figcaption>` that says what to see. A figure other documents also use comes from `assets/figures/`.
3. Short sections, optional, each under an `<h3>`. "Why it matters" takes two to four sentences. "The trap" names the usual misreading. "Related" links neighbouring concepts in a sentence or two.

## Forbidden

- An `<h2>` section. A concept that needs sections is an entry. Caught by `forbid: [h2]`.
- More than 250 words. Caught by `max_words`.
- A citation inside the definition. Caught by `cites: { defn: none }`, which applies to the `defn` only. Sources and results may be cited below it.
- A second definition of the same term. Caught by `defined_once`: no other document carries a `defn` with the same `defn-name`.
- A prose re-explanation of the term on another page. Judged, not checked.
- A label after the term in `defn-name`, such as "Softmax, definition". Judged, not checked.
- A concept for a part of one particular system. That stays as prose in its entry. Judged, not checked.

## Steps

- Search before writing: `folio search <term>`. If the term is defined, link to it or revise it. Never add a second one.
- A concept earns its page when the idea is transferable, not trivial, and needed on at least two documents. Judged, not checked. The organise skill folds a thin concept into its entry with `folio rm --to`.
- After writing it, replace every other explanation of the term with `<a class="defn-link" href="/content/concepts/{slug}/">`. The write skill does this sweep.
- Delete the optional parts you do not use. A placeholder left in the page is reported by the gate.
- An invented example or figure gets a flag, because the source did not say it.

## Lifecycle

Revised in place. The slug is the id and never changes; a move uses `folio mv`. A concept is born when a term needs explaining a second time, often out of a note or an entry's section. It becomes `historical` when the library stops using the term. It becomes `retired` when merged into another concept with `folio rm --to`. If it outgrows 250 words, the long form moves into an entry and the concept stays short.

## Example

```html
<meta name="title" content="Softmax">
<meta name="description" content="The function that turns attention scores into weights.">
<!-- body -->
<blockquote class="defn" id="softmax">
<span class="defn-name">Softmax</span><br>
The softmax of a vector of scores is the exponential of each score divided by the sum of the exponentials of all of them.
</blockquote>
<h3>The trap</h3>
<p>Computed as written, the exponentials overflow for large scores. Adding the same constant to every score leaves the result unchanged, so implementations subtract the maximum first.</p>
```
