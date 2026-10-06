# Timeline

**When.** The reader must see order or duration. There are two kinds: a **record** (dated events: a project's milestones, a run of decisions) and a **sequence** (steps that always run in the same order: a procedure, a pipeline).

## A record: dated events

A table, date first, oldest first so it reads top to bottom, with a state chip on each row and a link for anything that rests on a document.

```html
<table>
<thead><tr><th>When</th><th>What</th><th>State</th></tr></thead>
<tbody>
<tr><td><code>2026-10-03</code></td><td>One journal entry per file.</td><td><span class="v v-kept">decided</span></td></tr>
<tr><td><code>2026-10-04</code></td><td>Comments are committed by the server.</td><td><span class="v v-kept">decided</span></td></tr>
</tbody>
</table>
```

Do not hand-copy the journal: the journal page already lists every entry. A timeline on a page is for a selection the page argues from.

## A sequence: ordered steps

Chips, one per step, with the current one marked, and a stepper when the reader should walk it.

```html
<ol class="kx-steps" aria-label="What the write skill does">
<li>pick the genre</li><li>search</li><li class="kx-on">write</li><li>map it</li><li>gate</li>
</ol>
```

Lay the list out as a row with the page's own CSS, and mark the current step with a register hue. The words stay in the list, so the sequence reads the same with the styles off.

## Durations

When the length of things matters, draw it: an inline SVG with a time axis, one bar per phase, in one register, each bar labelled with its duration inside it (`diagrams.md`).

## Do not

- Draw a record as a horizontal line with dots. It hides the text and breaks on a narrow screen.
- Write a sequence as prose with "then ... then ... then".
- Leave the dates off a record.
