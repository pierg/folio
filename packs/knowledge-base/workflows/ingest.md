---
name: ingest
pack: knowledge-base
summary: Bring one source into the library as a source, a reading, and any new concepts.
inputs:
  - source: a URL, a file, or a citation
  - map: the map it belongs on, if the request does not make it clear
produces: [source, reading, concept, map-row, journal-entry]
---

# Ingest

You hand over one work to keep; you get a verified source with the original beside it, a reading of it, any new concepts, and a row on a map.

## Steps

1. **Read the work whole.** Fetch the URL or open the file. Note the title, authors, year, venue and every identifier it shows. If the request gave only a citation, find the work first.
2. **Check it is not filed already.** Run `folio search` with the title, then with each identifier. Search reads the files as they are now, and several words must all match. If it is filed, stop and offer to revise its reading instead.
3. **Verify every identifier.** Look each one up in its registry and confirm the title and authors match (rule `unverified-identifier`). Record the date of each lookup. Drop any identifier that cannot be verified, and say so in the source's `about` section.
4. **File the source.** Through the write skill, which runs `folio new source <slug> --authors ".." --year <year> --original original.<ext>`. Use the slug `{year}-{short-title}`. Save the original beside it as `original.<ext>`, or set `original` to `Not kept:` and the reason. The original stays private: `folio export` leaves it out of the site.
5. **Write the reading.** Through the write skill, which runs `folio new reading <source-slug>-reading --source <source-slug>`. Ids are unique across the library, so the reading never takes the source's slug. What it claims first, then the take, set apart. Flag only a point in it the owner must decide.
6. **Add concepts.** For each term the reading needs that the library does not define, run `folio search` for it first. If it is missing and other pages will need it, write a concept through the write skill. Link every use with `class="defn-link"`.
7. **Add cards.** Where the work holds something worth remembering, the write skill adds flashcards to the reading: `<details class="card"><summary>question</summary>answer</details>`.
8. **Put it on a map.** Run `folio map add <map> <reading> [--group "<heading>"] [--after <doc>]`, placed where a newcomer would read it. Add `--reason "..."` only when one line on why to follow it says more than the reading's description. The source needs no row: the reading's `source` field links it.
9. **Record it.** Through the write skill, which runs `folio journal add --title "Ingested <title>" --description "<one line on the work>" --body ".." --about <source>,<reading>`. The entry has no kind; it shows on both documents.
10. **Run the gate.** `folio index`, then `folio check` passes.
11. **Commit.** Add exactly: the documents written, their annotation files (`<stem>.annotations.json`), `.folio/`, and the kept original. Never `git add -A`.

## Stops

- An identifier resolves to a different work, or the work's own pages disagree on its title or authors. Ask which is right.
- The work cannot be read whole: it is behind a paywall, or the file is damaged. Ask for a copy.
- The licence does not allow a private copy, or the owner may not want one kept. Ask before writing `Not kept:`.
- No map fits, and the request names none. Ask which map, or whether to start one through the configure skill.
- The work is already filed. Ask whether to revise its reading.

## Done when

- The source is `live`, with its authors and year set, every identifier verified and dated, and the original beside it or a reason it is not.
- The reading names the source in its `source` field, and is on a map.
- Every new term has a concept, and every use links it.
- The journal has one entry about the source and the reading.
- `folio check` passes, and everything is committed.
