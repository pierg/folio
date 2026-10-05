# The shell's components

This is the vocabulary a page may use. The shell is one stylesheet, `folio.css`, and one script, `folio.js`. Together they draw everything a page does not write: the top bar, the library rail, the header, the banners, the page panel, guide navigation, search and the comment panel. A page writes its metadata and its `<main>`, and nothing else. Read `docs/spec/model.md` §3, §4 and §14 first.

## How a page loads the shell

Every HTML document links the shell in its `<head>`, from the library's root:

```html
<link rel="stylesheet" href="/shell/folio.css">
<script src="/shell/folio.js" defer></script>
```

Every skeleton already carries both lines. `folio serve` and `folio export` serve the shell at `/shell/`, and add whichever line a page lacks, so a frozen page written before the script existed still gets it. `folio export --base /path/` rewrites both, and every link from the root, under that path.

A Markdown record needs nothing: the site renders it as an HTML page at the same path with `.html`, in the same shell.

## What the shell draws, so a page never writes it

- **The library rail**: on the left of every page, links to the home page, the journal and (when served) the Review page; then the charter's home maps, each a group of the documents it lists; then every document other than a journal entry, grouped by genre. The current page is marked. `[` hides or shows it; on a narrow screen it is a drawer opened from the top bar.
- **Topic focus**: the top bar's Focus control narrows the rail, search, the journal, Review and the home page to the documents under the chosen home maps (`model.md` §5). A chip names the focus and clears it; a page outside it says so under its header. It reads `topics` from the catalog, so a page writes nothing for it.
- **The header**: the genre, the record id, the title, the description as a subtitle, the status (unless `live`), the `date` or the dates from git, the tags, "Frozen since <date>" for a document in a frozen state (the date of the commit that froze it), and the genre's fields as a short list, in the order the card declares them. So a body has no `<h1>`, no subtitle and no status line.
- **Banners**: a superseded record links the one that supersedes it; a retracted record links the retraction; a journal entry of kind `correction` shows on the document it is `about`, with its text.
- **The page panel**: the outline (every `<h2>` and `<h3>`), what the page cites (on a map, besides its rows), what cites it, the journal entries about it, and a list for each field of type `id` that names it ("As its protocol"). On a narrow screen the panel follows the page.
- **A guide**: the chapter list on its front page, and on each chapter its place ("Chapter 2 of 5") and links to the previous and next chapter.
- **The home page**: its title is the charter's `name` and its subtitle the page's description (or the charter's `purpose`); the page carries no title of its own. Below, a card for each map the charter lists under `home.maps`, in that order, each showing that map's first rows in its own order ("and N more"), and the latest journal entries.
- **The journal**: one timeline at `/content/journal/`, newest first, filtered by kind, tag, `about` and date. Each entry's `about` chips show the target's genre beside its title, so a source and its reading stay apart. A filter lives in the address (`?kind=decision`), so a filtered view can be linked.
- **Search**: `/`, Ctrl K or Cmd K opens it, over `.folio/search.json`.
- **Previews**: hovering a link to a library document shows its genre, title and description.

## Components a page may write

Each one is plain HTML. Use the class names exactly.

### A definition (concept)

```html
<blockquote class="defn" id="softmax">
<span class="defn-name">Softmax</span><br>
The softmax of a vector of scores is each score's exponential divided by the sum of all the exponentials.
</blockquote>
```

One per concept page. The shell shows its text in the popover on every link to the concept.

### A concept link

```html
<a class="defn-link" href="/content/concepts/softmax/">softmax</a>
```

A dotted underline. Hovering or focusing it shows the definition. Use it for every mention of a term that has a concept page.

### A check-yourself

```html
<details class="check">
<summary>Why does doubling the context quadruple the scores?</summary>
<div class="ans">Every token scores against every token, so n tokens make n squared scores.</div>
</details>
```

Ends a section of an entry or a guide chapter. The shell labels it "Check yourself". The answer stays hidden until the reader opens it.

### A flashcard

```html
<details class="card"><summary>Why subtract the maximum score before the softmax?</summary>It keeps the exponentials from overflowing and leaves the result unchanged.</details>
```

May sit in any HTML document. `folio index` collects every card into `.folio/cards.json`.

### Map rows

```html
<ul class="rows">
<li><a href="/content/concepts/softmax/">Softmax</a> <span class="why">Read first.</span></li>
<li><a href="/content/notes/flashattention-tiling.html">FlashAttention tiling</a></li>
</ul>
```

The reason is optional. Without one, the shell shows the target's description. The shell draws each row's link text from the catalog's title, so a renamed document reads right everywhere; the text in the file is a fallback for reading without the shell, and `folio map add` writes the title there. The shell adds the target's genre, and its status when it is not `live`.

### Text parts

| Markup | Use |
| --- | --- |
| `<p class="thesis">` | An entry's position, at the top. Set larger, with a rule below. |
| `<p class="state">` | A project's state on its reviewed date. Set in a box. |
| `<ul class="identifiers">` with `<a class="identifier">` | A source's identifiers. |
| `<table class="compare">` | A survey's table. |
| `<span class="not-measured">` | A cell or phrase for something not measured. |
| `<mark>` | A highlighted phrase. Use rarely. |

### Figures and tables

```html
<figure>
<img src="/assets/figures/attention-tiling.svg" alt="Queries are scored against one tile of keys at a time">
<figcaption>Each new tile rescales the running sum before adding to it.</figcaption>
</figure>
```

Figures live in `assets/figures/` and are linked from the root. The shell prefixes the caption with "Figure." A table scrolls sideways inside its own box on a narrow screen, never the page. Mark a numeric column with `class="num"` on its cells to right-align it. See `craft/`.

### Code

`<code>` inline and `<pre><code>` for blocks. In a Markdown record, an id in backticks (`R-12`) that names a document becomes a link to it (`<a class="f-cite">`), drawn as a link rather than as code.

## Tokens

Colours, faces and sizes are custom properties on `:root`, redefined for dark mode. A page uses only these, never a hex value, so it reads in both themes.

| Token | For |
| --- | --- |
| `--paper`, `--surface`, `--sunk` | The page, a raised box, a sunk box |
| `--ink`, `--ink-2`, `--ink-3` | Text: main, secondary, quiet |
| `--rule`, `--rule-strong` | Lines and borders |
| `--accent`, `--accent-soft` | The one mark colour: eyebrows, the definition rule |
| `--link`, `--link-line` | Links and their underline |
| `--ok`, `--warn`, `--bad`, `--info` and each `-soft` | States and banners, never decoration |
| `--serif`, `--sans`, `--mono` | Prose, interface, code |
| `--measure`, `--wide` | The reading column, and the most a figure may use |

An inline SVG uses `currentColor` or `var(--ink-2)` and the like for its strokes and fills.

## The comment panel

When a library is served with `folio serve` or `folio up`, every page shows a Comments button, and the top bar links to Review. The panel says who is commenting: the server knows it (`docs/spec/model.md` §12), so there is no name field. Selecting a passage offers to comment on it, and "Comment on the whole page" opens a thread with no quote. A comment is a question or a flag, saved beside the document as `<name>.annotations.json`, the same file `folio annotations` reads, and committed by the server.

The panel lists every thread on the page, with its quote (or "About the whole page"), its messages and its state in plain words: waiting, resting, or closed with how (changed, kept, declined, withdrawn). A resting flag has two buttons, Keep and Change. An addressed thread shows "What changed": the passage before and after, from git. A closed thread takes a reply and can be reopened. Quoted passages are highlighted on the page. A link ending `#comment-<id>` opens the panel at that thread.

Review, at `/content/review/`, lists every waiting question and resting flag in the library, newest first, and the home page shows one line linking to it.

Where the server takes no comments (a public address without `comments.identity_header`, or a request without that header), the panel shows the threads and says why it is read-only. An exported site has no comment button and carries no annotation files, no review page, and no source's kept `original.*`; its page panel says "Comments are open where this library is served with folio serve."


## Theme

The shell follows the reader's system setting. The moon or sun button in the top bar switches theme, and the choice is remembered in that browser. A library can use its own theme: set `theme:` in the charter to a folder in the library holding `folio.css` and `folio.js`.
