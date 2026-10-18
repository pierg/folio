---
name: survey
pack: knowledge-base
format: html
path: content/surveys/{slug}.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  cites: any
  min_sources: 2
on_map: required
---

# Survey

A survey compares several works on one question: a neutral table of what each says, and your reading of the table, kept apart.

## Earns its page

A survey earns its place when several works answer one question differently, and setting them side by side shows what no single reading does. A list of works with no question is a map's rows, or a set of sources.

## Reader

Someone deciding which works to read, or which approach to take, on one question. They know the field's basic terms and want the differences laid side by side.

## Voice

The table is neutral: it reports what each work says, in the same terms for every row. The reading after it is yours and takes a position.

> Two of the three works compute exact attention and change only how much memory it takes. The third drops most pairs of tokens, and its savings come from that.

## Metadata

No fields beyond the core.

- `title`: the question's subject.
- `description`: the one question the works are compared on, in one sentence ending in a question mark.

## Shape

The shell draws the title and the question above the body. Below it the page is a canvas: a survey is a comparison, so lay it out as one (`craft/comparison.md`).

What a good survey usually holds, judged, not checked:

- **The works**: which works are in, each linked to its source or reading, and the rule for what was left out.
- **The comparison**: the works against the same criteria, so the eye scans down one criterion. A `<table class="compare">` with a row per work is the plain form; a matrix, lanes or a chart may show it better. Each cell is a short fact from that work.
- **My reading**: what the comparison shows when you read across it, and where you land.
- **Gaps**: what none of the works answers.

## Forbidden

- Fewer than two works cited. Caught by `min_sources`, which counts the distinct sources and readings the survey links.
- An opinion inside the comparison. Judged, not checked; it goes in your reading.
- A cell that states something its work did not. Judged, not checked.
- Two questions in one survey. Judged, not checked; write two surveys.
- A work that is not filed as a source. Judged, not checked; file it first with the ingest workflow.

## Steps

- File every work as a source before it enters the comparison. Ingest any that are missing.
- Fix the columns before filling the rows, and fill every cell. Write "not reported" where a work is silent.
- State the inclusion rule, so a reader can tell a missing work from an excluded one.
- Link each criterion that needs explaining to its concept, with `class="defn-link"`.

## Lifecycle

Revised in place. A new work adds a row, and the reading is revised to match. When the question itself changes, start a new survey and mark the old one `historical`.

## Example

```html
<meta name="title" content="Attention for long sequences">
<meta name="description" content="Which way of computing attention over long sequences keeps the result exact?">
<!-- body -->
<section id="works">
  <h2>The works</h2>
  <p>Works that change how attention is computed for long inputs. Works that replace attention with another operator are left out.</p>
</section>
<table class="compare">
  <thead><tr><th>Work</th><th>Pairs scored</th><th>Exact attention</th></tr></thead>
  <tbody>
    <tr><td><a href="/content/sources/2017-attention-is-all-you-need/">Attention Is All You Need (2017)</a></td><td>all</td><td>yes</td></tr>
    <tr><td><a href="/content/sources/2020-longformer/">Longformer (2020)</a></td><td>a local window, plus a few global tokens</td><td>no</td></tr>
    <tr><td><a href="/content/sources/2022-flashattention/">FlashAttention (2022)</a></td><td>all, one tile at a time</td><td>yes</td></tr>
  </tbody>
</table>
<section id="reading">
  <h2>My reading</h2>
  <p>Only FlashAttention is both exact and lighter on memory. Its compute still grows with the square of the length.</p>
</section>
```
