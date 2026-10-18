---
name: knowledge-base
version: 0.1.0
requires: { folio: ">=0.1.0" }
genres: [source, reading, survey]
workflows: [ingest, quiz]
rules: rules.md
---

# Knowledge base

This pack is for reading and learning: keeping the works you read, what you made of them, and what you still remember.

## What it adds

- **source**: a work you keep, such as a paper, an article, a book or a talk. Its citation is metadata (authors, year, the kept original), its identifiers are verified, and the original file sits beside it, kept out of the exported site.
- **reading**: your close reading of one source, named in its `source` field. Its slug is the source's with `-reading` added, since ids are unique across the library. What the work claims comes first, and your take comes after, kept apart.
- **survey**: several works compared on one question. A neutral table comes first, and your reading of it comes after.
- **ingest** (workflow): one source in. A source, a reading, any new concepts and a map row come out.
- **quiz** (workflow): asks you the flashcards in one part of the library, one at a time. It grades each answer and ends with one journal entry of kind `lesson`.
- **Every identifier in a source is verified** (rule, check `unverified-identifier`). A DOI, an arXiv id or an ISBN is checked against its registry before the source is filed.
- **A page stands alone** (rule, check `source-pointer`). A page states what a source says, never where in it: no section, figure, table or appendix number of the source.
- **Journal kinds**: none of its own. The quiz writes the core's `lesson`.

## When to switch it on

Switch it on when the library keeps other people's work. A personal knowledge base needs it. So does a lab that keeps its literature, or a project that tracks the papers behind its design.

Without it, the core still has notes, entries and concepts. You lose a fixed home for each work's citation and original. You lose the line between what a work says and what you think of it. You lose the ingest and quiz procedures.

## What switching it on changes

Nothing is rewritten. The pack adds three genres and two workflows.

The identifier rule looks only at source documents. A library that had the pack off has none, so that rule flags nothing at first. The `source-pointer` rule reads every page, so it may warn about pointers already written; the organise skill can rewrite them.

Older notes or entries may already describe works you read. The organise skill can propose promoting each one to a source and a reading. You approve each move, and promotion keeps ids, links, comments and dates.

## Working with other packs

- **With the lab pack.** A reading may quote a number from its source. That number cites the source, and the lab pack's `uncited-number` rule accepts a source citation for it. Your own measurements never go in a source or a reading. They are results.
- **Flashcards live anywhere.** A card is a core component, not a genre: `<details class="card"><summary>question</summary>answer</details>`. Any HTML page can carry cards, including a lab report. `folio cards` lists them wherever they are, and the quiz asks them.
- **One graph.** Sources and readings cite concepts like any other page. A term a source introduces becomes a core concept, not a section of the reading.
