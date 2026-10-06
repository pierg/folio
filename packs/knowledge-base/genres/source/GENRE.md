---
name: source
pack: knowledge-base
format: html
path: content/sources/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, retired]
fields:
  - { name: authors, type: string, required: true }
  - { name: year, type: integer, required: true }
  - { name: original, type: string, required: true }
checks:
  require: [identifiers]
  cites: none
  original_beside: true
on_map: optional
---

# Source

A source is one work you keep, such as a paper, an article, a book or a talk: its verified citation, a few words on what it is, and the original beside it.

## Earns its page

A source earns its place when a document cites the work. A work nothing cites is not kept yet.

## Reader

Anyone in the library who needs to know exactly which work a page means, and where to find it. They want the facts of the work, not an opinion of it.

## Voice

Bibliographic. Describe the work in its own terms, in the present tense, and judge nothing. Opinion belongs in a reading.

> A paper that introduces the Transformer, a sequence model built on attention alone, and evaluates it on machine translation.

## Metadata

The citation is metadata, so the shell can render it and search can filter by it.

- `title`: the work's own title, as published.
- `description`: one line on what the work is, in its own terms.
- `authors` (required): the authors, as the work lists them.
- `year` (required): the year the work appeared.
- `original` (required): the name of the kept file beside the page, `original.<ext>`. When the file cannot be kept, it starts with `Not kept:` and gives the reason.

## Shape

The shell draws the title, the description and the citation fields above the body. Readings and surveys of this source are not listed by hand: the generated panels show them.

One part is required, because the pack's rule reads it:

- `identifiers`: a `<ul class="identifiers">`, one `<li>` per identifier, each an `<a class="identifier">` as the pack's rule describes. A DOI, an arXiv id, an ISBN, a handle or a URL.

What a good source page usually adds, judged, not checked: a few sentences on what the work is, where it appeared and what it covers.

## Forbidden

- An identifier with no verification record. Caught by `unverified-identifier`.
- An `original` that names no file beside the page and gives no `Not kept:` reason. Caught by `original_beside`.
- An opinion, a rating or a summary of the argument. Judged, not checked; it belongs in a reading.
- Links to other library documents. Caught by `cites: none`; a source points out to its work, and other pages point in to it.
- A copy of the abstract. Judged, not checked; the original is beside the page.

## Steps

- Look up every identifier before writing it down, and record the date (rule `unverified-identifier`).
- Search the library for the work first (`folio search`, by title and by identifier). A work is filed once.
- The slug is `{year}-{short-title}`, lowercase, for example `2017-attention-is-all-you-need`.
- Name the kept file `original.<ext>`: `original.pdf`, `original.html` for a saved web page, `original.md` for a transcript.
- Keep the original only when its licence allows a private copy. Otherwise write `Not kept:` and why. `folio export` never publishes it; `folio serve` shows it locally.

## Lifecycle

A source's citation is fixed once filed. Verify every identifier and put the original beside it before the first commit, so it is `live` from the start; hold it as `draft` only when the owner asks.

After that, its tags may change (`folio tags rename` edits them), and only a wrong citation field is corrected, in place, with a journal entry of kind `correction` about the source. That limit is judged, not checked. A duplicate source is retired into the other one by the organise skill (`folio rm --to`). A source is never promoted; its reading grows instead.

## Example

```html
<meta name="title" content="Attention Is All You Need">
<meta name="description" content="The paper that introduces the Transformer, a sequence model built on attention alone.">
<meta name="authors" content="Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin">
<meta name="year" content="2017">
<meta name="original" content="original.pdf">
<!-- body -->
<ul class="identifiers">
  <li><a class="identifier" data-kind="arxiv" data-verified="2026-10-03"
      href="https://arxiv.org/abs/1706.03762">1706.03762</a></li>
</ul>
<section id="about">
  <h2>About</h2>
  <p>A paper from NIPS 2017. It replaces recurrence with self-attention in an encoder-decoder model, and evaluates it on machine translation.</p>
</section>
```
