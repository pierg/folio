# Knowledge-base rules

These rules hold across the whole library while the knowledge-base pack is on.

## Every identifier in a source is verified

An identifier in a source document is checked against its registry before the source is filed.

Verifying means looking the identifier up and confirming the work at the other end is this work. A DOI resolves at `https://doi.org/`. An arXiv id resolves at `https://arxiv.org/abs/`. An ISBN is found in a library catalogue. A URL loads. In each case the title and the authors match the source's `title` and `authors` fields.

The gate runs offline, so it checks the record of the lookup, not the lookup itself:

- each identifier is an `<a class="identifier">` in the source's `identifiers` list, with a `data-kind` (`doi`, `arxiv`, `isbn`, `handle` or `url`);
- each carries `data-verified` with the date of the lookup, as `YYYY-MM-DD`;
- its link and its text name the same identifier, and the text has the shape its kind requires.

Whether the lookup really happened is judged, not checked. An identifier that cannot be verified is left out of the list, and the source's `about` section says so in words.

- check: `unverified-identifier`
- default: error

## A page stands alone

A page never points into a source's internals. The reader will not open the source, so a section, figure, table, appendix, listing, footnote or equation number of it tells them nothing.

- State the claim itself, and drop the pointer.
- Redraw a figure or table that matters on the page; never "see Figure 3".
- Explain a name the source coins, such as its benchmark's own label, in a clause where it is used, or drop it.
- When the source contradicts itself, say so in words: "the paper gives 47% in one table and 57% in another".
- Quote briefly when the exact words matter, without a location. A verifier searches the kept original beside the source for the words or the number.

What the check reads:

- **Where.** The visible prose of every HTML and Markdown file. Code, scripts, styles, attribute values such as a link's address, and metadata are not read. Journal entries, results and other permanent documents, frozen documents once locked, historical and retired documents, LaTeX files and permanent parts are skipped: they are never rewritten.
- **Which pointers.** A section sign before a number (`§4`), and `Section`, `Table`, `Figure` or `Fig.`, `Listing`, `footnote`, `Eq.` or `Equation`, `Appendix` or `App.` before a number, or for an appendix a capital letter (`Section 5.3`, `Table 7`, `Appendix C`). `Theorem 2`, `Lemma 3` and `Definition 1` are not pointers.
- **The page's own labels.** A page may number its own sections, figures and tables. A label that opens an `h2` to `h4` heading or a caption on the page (`§1 · Setup`, `Figure 3. One tile at a time.`) is the page's own, and a reference to it is not flagged. A guide's chapters share their guide's labels, and a pointer right after `chapter NN` (`chapter 03 §4`) names another chapter, so it is not flagged either.

The shapes are a heuristic. A pointer written in words ("the third table") is missed, which is judged, not checked.

- check: `source-pointer`
- default: warning
