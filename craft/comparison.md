# Comparison

**When.** The reader must hold two or more things side by side and see where they differ. If they differ on one axis only, that is a sentence, not a comparison.

**The move.** Put the axis of difference in the reader's eye first. Two things: `.cols` with a `.lane` each, coloured by what each thing is (the ROLE register when they are actors, `lane-baseline` for the reference). Three or more things, or more than four axes: a table with the axes as rows and the things as columns, so the eye scans down one axis.

**A verdict, not a list.** When one option wins, say so with a chip in the cell where it wins (`<span class="v v-kept">`), and say why in the prose under it. A comparison that ends without a stance is only a table.

## Two things

```html
<div class="cols">
<div class="lane lane-azure"><h4>A revised document</h4>
<p>Edited in place. Its address always shows the current version.</p></div>
<div class="lane lane-violet"><h4>A permanent record</h4>
<p>Never edited. A correction is a new record that points back.</p></div>
</div>
```

## Before and after

```html
<div class="cols">
<div class="lane lane-baseline"><h4>Before</h4> ... </div>
<div class="lane lane-kept"><h4>After</h4> ... </div>
</div>
```

Only the "after" lane may carry a verdict chip.

## Several things on several axes

```html
<table class="compare">
<thead><tr><th>Axis</th><th>A wiki</th><th>A notes folder</th><th>folio</th></tr></thead>
<tbody>
<tr><td>Broken links found</td><td>by readers</td><td>never</td><td><span class="v v-kept">by the gate</span></td></tr>
<tr><td>History of a decision</td><td>page history</td><td>none</td><td>the journal</td></tr>
</tbody>
</table>
```

Keep cells short. The argument goes in the prose under the table, one line for each axis that matters.

## Do not

- Compare in prose ("A does this whereas B does that, although ...") when a lane or a row would show it at a glance.
- Colour lanes by preference. Colour by kind, and mark preference with a chip.
