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

## Charts

- Pick the form by the question. Change over time: a line. Comparing a few amounts: bars from zero. Parts of a whole: a single stacked bar, not a pie.
- Label lines and bars directly, at their ends. Avoid a legend the eye must travel to.
- Keep to two or three colours, from the tokens. Grey for context, the accent for the thing the caption names.
- Start a bar's axis at zero. Say when a line's axis does not.
- Remove what does not carry data: heavy grids, borders, shadows, 3D.

## Both themes

An SVG that hard-codes black text vanishes in dark mode. Use `currentColor` for text and lines, or inline the SVG and use the shell's tokens (see `diagrams.md`). A PNG needs a background that reads on both, or a transparent one tested on both.
