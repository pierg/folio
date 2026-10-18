# Tables

## When to use one

Use a table when the reader compares the same few facts across several things. Each row is a thing; each column is one fact about it. If there is one fact per thing, use a list. If there are two things, write a sentence.

## Shape

- Put the things down the side and the facts across the top. A table with many rows and few columns reads on a phone; the reverse does not.
- Keep to about five columns. Split a wider table into two that each answer one question.
- Order the rows by what matters most to the reader, not alphabetically, unless the reader will look a row up by name.
- The first column names the row. In a survey, it links the source.

## Cells

- Numbers: same unit and precision down a column, unit in the header, not in each cell. Right-align them with `class="num"`.
- Empty is not the same as zero. Write "not reported" or use `<span class="not-measured">` for what was not measured.
- Keep cells short: a fact, not a sentence. A cell that needs a sentence is a footnote under the table.
- Every number cites its source in the same row, as the gate asks.

## Markup

```html
<table class="compare">
<thead>
<tr><th>Work</th><th class="num">Year</th><th>Exact attention</th></tr>
</thead>
<tbody>
<tr><td><a href="/content/sources/2017-attention-is-all-you-need/">Attention Is All You Need</a></td><td class="num">2017</td><td>yes</td></tr>
</tbody>
</table>
```

Use `<thead>` and `<th>`. A `<caption>` may say what to read across. Do not style a table inline: the shell sets the rules, the spacing and the scrolling on a small screen.
