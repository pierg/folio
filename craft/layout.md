# Layout

## A page designs itself around what it shows

Every HTML page is a free canvas: all the room between the library rail and the page panel, below the header the shell draws. Lead with the one figure, control or contrast that carries the idea, when one does, and lay the page out around it. The prose is the definition, the caption, and what the figure cannot show: the reasons, the trade-offs, the open questions. This holds for every genre, concepts and notes included. A definition is often clearer beside a diagram or a control than as three paragraphs, and a note's one claim is often clearer as a contrast than as a paragraph.

Vary the form. A system with parts, a flow, a set to compare, a mechanism with a setting, a progression: each has a form that shows it (below). Do not reach for the same layout twice in a row. A library reads as one system when each page's form fits its own material, not when pages share a template.

**Restraint.** A figure, control or animation earns its place by showing what prose cannot: a structure, a flow, the effect of a setting, a comparison. Use the fewest that carry the idea, and make each one complete. One added to decorate costs the reader time and teaches nothing.

**Length follows the content.** No page has a word limit. Say what the reader needs: briefly where the idea is simple, at length where it needs the room. What is wrong is saying a thing twice, on the page or across the library, and words that carry nothing.

**The reading column is the exception.** A page that is one line of argument, a narrative, or a reading that is itself a line of prose may read best in the column: `<meta name="layout" content="column">`. Reach for it when the material is a line of thought, not a structure, and know why a figure would not serve. A page left in the column because it was quicker to write is the thing to avoid.

## The contract

The page's layout is the author's: grids, columns, widths, type scale, sections, interaction, motion. Five things stay fixed, because the library reads them:

1. **The words are in the markup.** Write every sentence, label and caption in the HTML. A script may arrange, reveal, highlight and animate them, and must not write them. Comments are anchored by quoting the page file, and search and the gate read the same file, so text a script generates is invisible to all three. The one exception is a label that repeats words already in the markup, such as a dial's tick names or a chart's axis.
2. **The genre's hooks stay.** A concept keeps its `defn`; a map keeps its `ul.rows`; a guide's chapters stay parts. The card names them.
3. **The voice stays.** Take a position where the genre does, support every claim where it is made, cite every number, state a null as plainly as a win, and flag only what needs the owner's judgement.
4. **Colours come from the shell's tokens.** Use `var(--teal)`, `var(--surface)`, `var(--ink-2)` and the rest (`shell/COMPONENTS.md`), never a hex value, so the page works in both themes. One register per figure.
5. **The page adapts to the canvas, not the window.** The rail and the panel share the window with the page, and a reader opens and closes them without resizing it. Write `@container folio-canvas (max-width: 44rem) { ... }`, never `@media (max-width: ...)`, for anything about the page's own layout.

The header is the shell's too: no `<h1>` and no subtitle in the body.

## Choosing a form

Start from what the reader must come away with, then pick the form that shows it:

| The material is | A form that shows it |
| --- | --- |
| a system with parts | a map: the parts drawn in place, each opening its own panel or card |
| a sequence or a flow | a stepper, or a sticky figure beside prose that advances it |
| rounds of work over time | a swimlane: lanes for the actors, columns for the rounds |
| options, tiers or cases | columns side by side, or a matrix the reader scans down one axis |
| one rule at several scales | a matrix: a row per scale, the same columns, so the pattern repeats down the page |
| a mechanism with a setting | a control (a dial, a toggle) whose effect the page shows at once |
| two states of the same thing | a contrast: the two side by side, or a picker that swaps one readout |
| a ceiling, a share, a frontier | a chart drawn inline: bars, a band, a region inside a region; say so when the numbers are illustrative |
| what counts against what only looks like it | a ladder: the near misses greyed as rungs, the real thing set apart at the top |
| a change to a fact over time | two lanes, overwrite against supersede, or a record with a replay control |
| a progression across levels | a descent: one card per level, arrows labelled with what changes |
| a map of a topic | cards grouped the way a newcomer should read them, each with its reason |

Keep the page's words in the order a reader would read them without the layout. A screen reader, a reader with scripts off, and anyone reading the page file get that order.

**The figure carries the page, so make it explain itself.** Its `aria-label` describes the whole thing (the parts, how they relate, what to conclude), not "a diagram". The caption says what to see. A reader who only looks at the figure and its caption should get the idea.

## Mechanics

- **Only the page's own classes, behind one short prefix.** Give the page a prefix (`.kx-`, `.sm-`) and keep its CSS in one `<style>` block in the `<head>`. Never restyle the shell's `.f-` classes.
- **Nothing overflows.** Use `minmax(0, 1fr)` tracks and `min-width: 0` on grid and flex children. A wide figure sits in an `overflow-x: auto` wrapper with a `min-width` in `rem`, so it scrolls sideways on a phone instead of pushing the page. Size the figure's own SVG (`.xx-scroll > svg`), never every `svg` inside the figure: the shell puts an icon button in the figure's corner, and a rule that reaches it stretches it.
- **Keep the drawing inside the viewBox.** Anything past an SVG's `viewBox` is clipped without a warning, the commonest way a designed page ships broken. Size the `viewBox` to the last element plus a margin, and check again after adding a row or a label.
- **One small script, and only to toggle.** A control's script sets a class or an attribute on a wrapper and nothing more: it never writes text and never builds the figure. Everything shows with the script off; the toggle only changes which pre-written state is visible. Reach for a control only where a setting or a state is the point.
- **Controls are buttons.** A control is a `<button class="tbtn">`, a picked state is `aria-pressed`, and a readout that changes is `aria-live="polite"`. Test it from the keyboard.
- **Motion is optional.** Respect `prefers-reduced-motion`, and make sure the page reads fully without it.
- **Prose still needs a line length.** On a wide canvas, set a paragraph's `max-width` (about `44rem`) where it is not inside a narrower track.
- **The shell draws the chrome.** Do not add a table of contents or a list of links: the page panel shows the outline from the `<h2>` and `<h3>` headings, and what the page cites and what cites it.
- **Leave space to the structure.** Do not add `<br>` or empty paragraphs to push things apart. If something looks cramped, the structure is usually wrong.

## Check two widths before it lands

Look at the page with the rail and the panel open at about 1440 pixels wide (a canvas near 820 pixels), and at phone width. There is no sideways scroll of the page, no clipped figure, and every control can be reached. Long words and paths wrap (put them in `<code>`, which may break). A table with more than four columns is turned around or split.
