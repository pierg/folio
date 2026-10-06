---
name: entry
format: html
path: content/entries/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  cites: any
on_map: required
---

# Entry

An entry explains or analyses one subject in depth, takes a position on it, and cites what each claim rests on.

## Reader

Interested and capable, but not an expert in this subject. They will spend several minutes, and want to see the shape of the argument before they read it.

## Voice

Analytical. It takes a position and supports it. Each claim cites what it rests on, where the claim is made: a source, a result, a concept, another entry. Uncertainty is stated once, precisely, never spread as hedging.

> Every token scores against every other token, so doubling the context quadruples the scores.

## Metadata

No fields beyond the core. The `title` is the subject. The `description` says in one sentence what the entry covers, and for whom.

## Shape

The shell draws the title and description above the body, and the generated panels list what the entry cites and what cites it. So the body has no list of what it rests on. Below the header the page is a canvas: lay the argument out in the form that shows it (`craft/layout.md`). A comparison can be lanes side by side, a mechanism a figure with a control, a sequence a stepper.

What a good entry usually does, judged, not checked:

- It opens with its position, in one to three sentences, where the reader sees it first. A `<p class="thesis">` sets it apart.
- It moves in steps the reader can navigate, usually `<h2>` sections, each carrying one step of the argument. The outline in the page panel is built from the `<h2>` and `<h3>` headings.
- It shows what a figure shows better than prose, and puts the figure where it carries a step.
- It may end a step with a check-yourself, `<details class="check">`.

Files only this entry uses, such as a source's full text or a figure's data, may sit beside `index.html` in its folder. A figure other documents also use lives in `assets/figures/`.

## Forbidden

- An entry that cites nothing. Caught by `cites: any`, which needs at least one resolving citation.
- An entry with no position. Judged, not checked: an entry that only describes is a note or a concept.
- A closing "What this rests on" list. The generated panel shows what the entry cites. Judged, not checked.
- A claim with no support where it is made. Judged, not checked.
- A definition written out again when a concept holds it. A second `defn` is caught by `defined_once`, which compares every `defn` in the library. A prose re-explanation is judged, not checked. Link the concept instead.
- A number restated as the entry's own when another document holds it. Judged, not checked; a pack can make it a check.

## Steps

- Before writing, list the concepts the subject needs. Link each with `class="defn-link"`. A term the entry must define, and another page also needs, becomes a concept first.
- Write the position last, then move it to the top. It must match where the argument actually lands.
- Anything the sources did not say (an example, a framing, a claim from general knowledge) gets a flag.
- Add the entry to at least one map: `folio map add <map> <doc>`. Give a `--reason` only when it says more than the description.

## Lifecycle

Revised in place, and the most revised genre. A note that grew into an argument is promoted into an entry. An entry that has become a teaching sequence is split into a guide, with the entry left as the reference or retired into it. An entry overtaken by a better one is `retired` into it with `folio rm --to`. One that was true of its time is `historical`, with its description saying when.

## Example

```html
<meta name="title" content="Why attention is quadratic">
<meta name="description" content="Where the n-squared cost of self-attention comes from, for someone who knows matrix products well.">
<!-- body -->
<p class="thesis">Every token scores against every other token. A sequence of n tokens makes n squared scores, so the cost grows with the square of the context.</p>
<h2 id="scores">Where the scores come from</h2>
<p>The product of the queries and the transposed keys is an n-by-n matrix ...</p>
<h2 id="memory">What tiling changes, and what it does not</h2>
<p>Each row of scores goes through a <a class="defn-link" href="/content/concepts/softmax/">softmax</a>, which tiling can compute without storing the matrix ...</p>
```
