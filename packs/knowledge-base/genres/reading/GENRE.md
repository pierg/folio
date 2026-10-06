---
name: reading
pack: knowledge-base
format: html
path: content/readings/{slug}.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
fields:
  - { name: source, type: id, genre: source, required: true }
checks:
  cites: any
on_map: required
---

# Reading

A reading is your close reading of one source: what it claims, faithfully, and then your take on it, kept apart.

## Earns its page

A reading earns its place when the library rests on the work or argues with it: documents cite it, or will. A work mentioned once needs only a source.

## Reader

The owner, coming back months later, and anyone the library is shared with. They have not read the work, or have forgotten it. They want to know what it says without opening it, and what you made of it.

## Voice

Neutral in what the work claims, then opinionated in your take. In the claims, report the work's position with its own hedges intact. In the take, say plainly what you think and why.

> The work claims that self-attention links any two positions in a constant number of steps, at a cost per layer that grows with the square of the sequence length (section 4). My take: the comparison favours attention only while sequences are shorter than the model width, which long contexts break.

## Metadata

- `title`: the work's short title.
- `description`: one line on what you made of the work.
- `source` (required): the id of the one source this reading is of. The shell links it under the title, and the source's page lists this reading.

## Shape

The shell draws the title, the description and the source above the body. Below it the page is a canvas.

What a good reading usually holds, judged, not checked:

- **What it claims**: the work's main claims, each with where it is made (a section, a page, a timestamp). A reading often leads with the work's own central figure or argument, redrawn so the claim is obvious.
- **What it rests on**: the evidence and method behind the claims, as the work presents them.
- **My take**: what holds, what does not, what it changes for you. Set apart from the claims, so a reader never mistakes the one for the other.
- **What it leaves open**: questions the work raises and does not answer.
- **Cards**: flashcards, `<details class="card"><summary>question</summary>answer</details>`, for what is worth remembering a month from now.

## Forbidden

- A reading of two works. The `source` field names one; a second work discussed as an equal is judged, not checked. Compare works in a survey.
- Your opinion mixed into the work's claims. Judged, not checked.
- A claim the work did not make, in the part that reports the work. Judged, not checked.
- A term defined here that another page needs. Caught by `defined_once` once a concept defines it; make it a concept and link it with `class="defn-link"`.
- A take that passes off a claim the work did not make. Judged, not checked. The take is the library's reading and an agent may draft it; it is set apart from the work's claims, so it needs no flag. A point in it the owner must decide gets one (the write skill's rule 11).

## Steps

- Read the whole work before writing. A reading of an abstract is not a reading.
- Name the reading `<source-slug>-reading`, so the pair is easy to find. Ids are unique across the library, so the reading never takes the source's own slug.
- Keep each claim to what the work states. Quote briefly when the exact words matter, with the location.
- Write cards only for what is worth remembering a month from now. One fact per card, answerable in a sentence.

## Lifecycle

Revised in place: a reread adds to the take, and the take may change its mind. To keep an old view on record, mark the reading `historical`. Then start a new reading with a new slug. A reading that grows into an argument across several works is promoted to an entry. A reading that grows into a comparison moves into a survey. The organise skill does both.

## Example

```html
<meta name="title" content="Attention Is All You Need">
<meta name="description" content="A strong case for attention alone, whose cost argument holds only for short sequences.">
<meta name="source" content="2017-attention-is-all-you-need">
<!-- body -->
<section id="claims">
  <h2>What it claims</h2>
  <ul>
    <li>Self-attention links any two positions in a constant number of sequential steps, where a recurrent layer needs as many steps as the sequence is long (section 4).</li>
    <li>Its cost per layer grows with the square of the sequence length (section 4, table 1).</li>
  </ul>
</section>
<section id="take">
  <h2>My take</h2>
  <p>The cost comparison favours attention while sequences are shorter than the model width. Long contexts break that assumption, and the paper does not test them.</p>
  <details class="card"><summary>Why does the paper scale the dot products by one over the square root of the key width?</summary>Large dot products push the softmax into regions where its gradients are tiny; the scaling keeps them in range.</details>
</section>
```
