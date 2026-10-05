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
  require: [works, table, reading]
  cites: any
  min_sources: 2
on_map: required
---

# Survey

A survey compares several works on one question: a neutral table of what each says, and your reading of the table, kept apart.

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

The shell draws the title and the question above the body. The body starts with the works.

1. **The works** (`works`): `<section id="works">`. Which works are in, each linked to its source, and the rule for what was left out.
2. **The table** (`table`): `<table class="compare">`. One row per work, its first cell linking the work's source or reading. One column per criterion. Each cell is a short fact from that work.
3. **My reading** (`reading`): `<section id="reading">`, `<h2>My reading</h2>`. What the table shows when you read across it, and where you land.
4. **Gaps** (optional): `<section id="gaps">`. What none of the works answers.

## Forbidden

- Fewer than two works, or a table row that links no source. Caught by `min_sources`.
- An opinion inside the table. Judged, not checked; it goes in "My reading".
- A cell that states something its work did not. Judged, not checked; the write skill flags it.
- Two questions in one survey. Judged, not checked; write two surveys.
- A work that is not filed as a source. Caught by `min_sources`, which counts only rows linking a source, or a reading of one; file it first with the ingest workflow.

## Steps

- File every work as a source before it enters the table. Ingest any that are missing.
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
