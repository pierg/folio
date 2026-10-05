---
name: guide
format: html
path: content/guides/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  require: [start]
  max_words: 800
on_map: required
parts:
  chapter:
    path: content/guides/{slug}/{nn}-{name}.html
    skeleton: skeleton-chapter.html
    checks:
      require: [h2, check]
      check_each_section: true
      forward_links: marked
    on_map: never
---

# Guide

A guide teaches one subject in order, chapter by chapter, so a reader who starts at the beginning can follow every step.

A guide has two parts, both of this genre. The **front page** is `index.html` in the guide's folder. It says what the guide builds and who it is for. Each **chapter** is a part: a numbered file beside it, `{nn}-{name}.html`, starting at `01`. The number fixes the order. The engine builds the chapter list and the guide's navigation from the files, in number order, so nobody writes the list by hand.

## Reader

The front page: someone deciding whether to start, and where. A chapter: someone who has read the earlier chapters and nothing else. That is the whole contract of a guide.

## Voice

Second person, one idea at a time. Show the idea before naming it. End each section by letting the reader test themselves. The front page orients and does not teach.

> You now have a score for every pair of tokens. Double the sequence, and count the scores again.

## Metadata

No fields beyond the core. On the front page, the `title` is the guide's title, and the `description` says in one sentence what the reader can do at the end. On a chapter, the `title` is the chapter's title without its number, which comes from the file name. Its `description` is the chapter's promise: what the reader leaves with. The generated chapter list shows each chapter's title and description.

## Shape

The shell draws the title and description above the body. On the front page it also draws the chapter list.

The front page:

1. `start`: `<h2 id="start">How to read it</h2>`, who the guide is for and what it assumes.

A chapter:

1. `h2`: sections, each under an `<h2 id="...">`, one idea each.
2. `check`: a `<details class="check"><summary>question</summary><div class="ans">answer</div></details>` at the end of every section.
3. A term the guide defines and other pages need is a concept, linked with `class="defn-link"`. A term only this guide uses may be defined in place.

## Forbidden

- A hand-written chapter list on the front page. The shell draws it from the chapter files. Judged, not checked.
- Teaching on the front page. Its length is capped by `max_words`; the rest is judged, not checked.
- A chapter section without a check-yourself at its end. Caught by `check_each_section`.
- A link to a later chapter. Caught by `forward_links: marked`. A deliberate one carries `data-fwd`, as in `<a data-fwd href="05-merging.html">`.
- Using an idea before the chapter that introduces it. Judged, not checked.
- A chapter listed on a map. Maps list the guide's front page; the shell lists the chapters under it. Caught by the chapter's `on_map: never`.

## Steps

- Plan the chapters first. Each chapter adds one thing the next one needs, and its description says what.
- Write chapters in order. Before each one, reread what the earlier chapters actually said.
- Add a chapter with `folio new guide <slug> --part chapter <name>`, which takes the next number. To insert one, renumber with `folio mv`, which keeps links and comments.
- An invented example gets a flag, because the source did not say it.
- Add the front page to at least one map. Give a reason when the description does not say who should start it.

## Lifecycle

Revised in place. Chapters are added, split and renumbered as the guide grows; the generated chapter list follows. An entry that turned into a teaching sequence becomes a guide. A guide replaced by a better one is `retired` into it with `folio rm --to`.

## Example

```html
<!-- content/guides/attention/index.html; chapters 01-scores.html and 02-softmax.html beside it -->
<meta name="title" content="Attention, from scratch">
<meta name="description" content="By the end you can compute one attention layer by hand and say where its cost comes from.">
<!-- body -->
<h2 id="start">How to read it</h2>
<p>In order. You need to know what a matrix product is, and nothing else.</p>
```
