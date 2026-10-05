# Layout

## The reading column

Prose sits in one column about 68 characters wide (`--measure`). That width is easy to read and is the same on every page. Do not set widths on paragraphs, and do not put prose side by side.

On a wide screen the page panel sits to the right of the column. On a narrow screen it follows the page. Nothing a page writes goes in the panel.

## Order

- The body starts with content. The shell has already drawn the title, the description and the metadata.
- Use `<h2>` for the parts of the argument and `<h3>` for small labelled parts inside one. Never skip to `<h4>` for size. The outline is built from `<h2>` and `<h3>`.
- One idea per section. If a section needs two headings inside it, it is two sections.
- Put a check-yourself at the end of the section it tests, not at the end of the page.

## Going wider

A table, a figure or a code block may need more than the column. It keeps to the column, and scrolls sideways inside its own box on a small screen. The page itself never scrolls sideways.

If a figure only reads at a larger size, link the full-size file from the caption rather than stretching the page.

## Phones

Check every page at phone width. Watch for:

- long words or paths that do not wrap (wrap them in `<code>`; the shell lets code break);
- tables with more than four columns (split them, or turn them around so rows are the long side);
- figures with small text (redraw them with fewer, larger labels).

## Space

Leave space to the shell. Do not add `<br>` or empty paragraphs to push things apart, and do not set margins inline. If something looks cramped, the structure is usually wrong: a list written as a paragraph, or two ideas in one section.
