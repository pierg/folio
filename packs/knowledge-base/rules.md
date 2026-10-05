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
