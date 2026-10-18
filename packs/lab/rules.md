# Lab rules

These rules hold across the whole library while the lab pack is on.

## Every number cites a result

A number on a page or in a paper that reports a measurement links to the result that holds it.

The value lives once, in the result. Every other document cites the result by id, so a correction reaches every page through one new result.

What the check reads:

- **Where.** HTML pages, papers, and the body of claims. Journal entries, questions, protocols and results are records: the journal is where a number is first written down, a protocol's numbers are predictions, and a result is the number's home. None is flagged.
- **Which numbers.** Numbers shaped like measurements: percentages, ratios, `a of b`, `a/b`, multipliers such as `3×`, numbers with a decimal point, and numbers with a unit of measure. Dates, ids, section numbers, version numbers and numbers inside code are skipped.
- **What counts as cited.** A link to a result (`R-n`) in the same sentence, list item or table row. A link to a protocol there counts too: its number is a pre-registered threshold, not a measurement. In a paper, `\fcite{R-n}` in the same sentence. With the knowledge-base pack on, a link to the source that reported the number also counts.
- **Map rows.** The link text of a map row is not read. The shell draws it from the catalog's title, so the text in the file is only a fallback.
- **Not a measurement.** A number that only looks like one, such as "a 2/3 majority", is wrapped to say so. In HTML or Markdown that is `<span class="not-measured">`; in LaTeX, `\notmeasured{}`. Whether that is honest is judged, not checked.

The shapes are a heuristic. It can miss a measurement written in words, which is judged, not checked.

- check: `uncited-number`
- default: warning in a new library, error once the charter sets it

## A citation names a current result

A revised document that cites a result cites one whose derived status is `live`.

A result's status is derived: `superseded` once a newer result names it in `supersedes`, `retracted` once a journal entry of kind `retraction` names it in `about`. When that happens, every revised document citing it is named, with the result that replaces it, if any. The fix is to cite the replacement, or to mark the citing document `historical`.

Permanent and frozen documents are not flagged: journal entries, results, locked protocols and published reports are never rewritten, and the banner on the superseded or retracted result says what changed. Documents with status `historical` or `retired` are not flagged either. A citation whose sentence, list item or table row contains the word "retracted" or "superseded" is not flagged: it is an honest mention, such as "R-3, since retracted, had claimed 12%".

- check: `cites-superseded`
- default: warning
