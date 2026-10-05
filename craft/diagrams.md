# Diagrams

A diagram shows how something works: the parts, and what moves between them. It is worth drawing when the reader would otherwise hold four or more parts in their head at once.

## Draw the real mechanism

- Name the parts as the text names them. A box called "Processor" in a page about "the softmax step" is a second vocabulary.
- Show what flows, and which way. Arrows carry one meaning per diagram: data, or control, or time, never a mix.
- Leave out what the point does not need. A diagram of everything shows nothing.
- If the order matters, number the steps and use the same numbers in the text.

## Inline SVG in both themes

Write the SVG inside the page so it can use the shell's tokens:

```html
<figure>
<svg viewBox="0 0 320 80" role="img" aria-label="A row of scores goes through the softmax and comes out as weights">
  <g style="fill: none; stroke: var(--ink-2); stroke-width: 1.5">
    <rect x="10" y="25" width="80" height="30" rx="4"/>
    <rect x="230" y="25" width="80" height="30" rx="4"/>
    <path d="M90 40 H230" marker-end="url(#arrow)"/>
  </g>
  <g style="fill: var(--ink); font: 12px var(--sans)" text-anchor="middle">
    <text x="50" y="44">scores</text>
    <text x="270" y="44">weights</text>
  </g>
  <defs><marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M0 0 L8 4 L0 8 z" style="fill: var(--ink-2)"/></marker></defs>
</svg>
<figcaption>The softmax turns each row of scores into weights that sum to one.</figcaption>
</figure>
```

- Fill and stroke come from tokens (`var(--ink)`, `var(--ink-2)`, `var(--rule)`, `var(--accent)`), set in `style`, never from hex values. A token works in `style`, not in a plain `fill=` attribute.
- Use the accent for the one part the caption names. Everything else is ink or rule.
- Text is at least 12 units at the `viewBox` width, so it stays legible on a phone.
- Give the SVG `role="img"` and an `aria-label` that says what it shows.
- Keep a `viewBox` and no fixed width, so it scales to the column.

## Before you keep it

Look at it at phone width and in dark mode. If a label is too small or a line disappears, fix the drawing, not the page.
