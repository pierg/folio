# Figures

## When a figure earns its place

Draw a figure when the reader must see a shape: a trend, a comparison of sizes, a structure, the steps of a process. If one sentence says it as well, write the sentence.

Each figure makes one point. Write that point first, as the caption. If you cannot write it in one sentence, the figure is doing two jobs: make two figures.

## Where it lives

- The source and the rendered file go in `assets/figures/`. Link it from the root: `/assets/figures/<name>.svg`.
- Prefer SVG. Use PNG only for photographs or screenshots.
- A paper, a report and a page that show the same result reuse the same file. Never copy it.

## The markup

```html
<figure>
<img src="/assets/figures/attention-tiling.svg" alt="Queries are scored against one tile of keys at a time, and the running softmax is rescaled after each tile">
<figcaption>Each new tile rescales the running sum before adding to it.</figcaption>
</figure>
```

- `alt` says what the figure shows, for a reader who cannot see it.
- The caption says what to look at, not what the figure is. "Each new tile rescales the running sum" beats "Diagram of FlashAttention tiling".
- A number in a caption cites its source, like any number on the page.

## Drawing an inline figure

An inline SVG is drawn for a size, its `viewBox`, and the shell shows it near that size: at most 1.15 times as wide, whatever the window. So draw it at the size it should read at, about 640 to 880 units wide for a page, and size its text for that: 12 units or more for labels, never less than 11. A reader who wants it bigger opens it with the button in its corner. Set `data-fit="wide"` only for a figure that must fill the canvas, such as a wide timeline.

Before it lands, look at it, at a wide canvas and at phone width:

- **Nothing overlaps.** No label sits on another label, a line or a box edge. An arrow never runs through words.
- **Text fits its box.** Every label stays inside its shape with room to spare; a long label wraps onto a second line (two `<text>` or `<tspan>` rows) rather than running out.
- **Nothing is clipped.** Every mark sits inside the `viewBox`, with a margin.
- **Every mark is explained.** A colour, a dash style or a symbol that means something says what in a label, a key or the caption. A line that leads nowhere, or a box that says nothing the reader needs, goes.
- **It makes its one point.** The caption names the point, and a reader who sees only the figure and its caption gets it.
- **It is sized to its content.** No large empty band in the drawing; tighten the `viewBox` to the last mark plus a margin.

## Charts

- Pick the form by the question. Change over time: a line. Comparing a few amounts: bars from zero. Parts of a whole: a single stacked bar, not a pie.
- Label lines and bars directly, at their ends. Avoid a legend the eye must travel to.
- Keep to two or three colours, from the tokens. Grey for context, the accent for the thing the caption names.
- Start a bar's axis at zero. Say when a line's axis does not.
- Remove what does not carry data: heavy grids, borders, shadows, 3D.

## Both themes

An SVG that hard-codes black text vanishes in dark mode. Use `currentColor` for text and lines, or inline the SVG and use the shell's tokens (see `diagrams.md`). A PNG needs a background that reads on both, or a transparent one tested on both.
