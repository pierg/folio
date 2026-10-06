# Changelog

## Unreleased

Pages get a free canvas again. A genre gives structure and voice; the form is the page's.

- Every HTML page is a canvas: all the room between the rail and the page panel, with its own `<style>` and `<script>`, adapting with `@container folio-canvas` queries. The reading column is opt-in with `<meta name="layout" content="column">`; Markdown records always use it. The gate checks `layout` is `canvas` or `column`.
- Genre cards check substance, not form. Word caps are gone from every page genre (they stay on journal entries, results and claims). Gone too: `forbid: [h2]` on concept and note, the `require` parts nothing reads (entry `thesis` and `h2`, project `state` and `next`, guide `start` and chapter sections, reading, source `about`, survey and report sections), and the `check_each_section` check. `forward_links` is judged unless a library sets it. `min_sources` counts the sources a survey cites anywhere. Each card's Shape is now guidance, judged, not checked.
- The shell adds the colour registers (`--teal`, `--indigo`, `--blue`, `--amber`, `--red`; `--azure`, `--violet`, `--orange`; `--kept`, `--discarded`, `--rejected`, `--untested`), a few shared components (`.cols`, `.lane`, `.note`, `.law`, `.chip`, `.v`, `.tbtn`) and KaTeX math, vendored, on a page with `<meta name="math">`.
- `craft/layout.md` holds the canvas contract and the "choosing a form" playbook; new `code.md`, `comparison.md` and `timeline.md` guides. The write skill designs the page, and `folio genre <name>` ends with where the craft guides are installed.
- The documentation library is rebuilt as canvas pages.
- A document is judged by its content, never its size. Five questions, judged, not checked, apply to every genre: does it earn a page (not trivial, durable, adding something), is this its one home, is it clear, is it complete and nothing more, does the form serve the content (model.md §3, the write skill's rule 23). Each card gains `## Earns its page`, with examples rather than thresholds. A concept no longer needs two documents linking it, and a well-known part of a larger system can be one; an implementation detail of one system as built stays in its document. The write skill asks the questions before it writes, and no longer makes a concept of every term explained twice.
- `craft/layout.md` adds restraint (a figure, control or animation earns its place by showing what prose cannot) and says length follows the content. The concept skeleton drops its fixed "Why it matters / The trap / Related" sections.
- The organise skill audits a library against the current cards: a verdict per document, a report to the owner, then batches the owner approves. `folio skills [update]` compares a library's copy of the skills with the engine's and refreshes the stale ones.
- The rail keeps each map's own sections: `folio index` records, for a map, the heading each list of rows sits under (`sections` in `catalog.json`, beside the flat `rows`), and the rail shows them as sub-groups that count their genres while closed. A map without sections lists a long run of documents by genre, in reading order. Every document in a map's group carries its genre's mark, with a key at the foot of the rail, and the map's first document is marked Start. The rail is a little wider.
- `folio serve` loads the library once and again only when a file, the shell or the last commit changes; it used to load it on every request. Pages and files carry an ETag and are answered with 304 when unchanged.
- The shell keeps a page hidden until it has drawn the top bar, rail and panel, and set any math, so no page shows half drawn; it shows anyway after 1.5 s should the script fail, and at once without scripting. KaTeX and its common fonts load beside the indices instead of after them. Where the browser supports speculation rules, a linked page is prerendered while the pointer rests on its link.

## 0.1.0 (2026-10-04)

The first release.

- The `folio` command: create a library, write documents from genre skeletons, keep maps, the journal and comment threads, move and retire documents with links kept, search, serve and export a static site, and build and freeze papers.
- The gate, `folio check`: links, genre cards, fields, placeholders, lifecycles checked against git, orphans, unique ids, current indices and stale quotes, with severities set in the charter.
- Eight core genres: concept, note, entry, map, guide, project, journal, paper.
- Two packs: knowledge-base (source, reading, survey; ingest and quiz) and lab (question, protocol, result, claim, report; record-a-result and write-a-report).
- Seven skills: set-up, configure, write, organise, address, publish, run.
- The shell: one stylesheet and one script for every page, in light and dark, with the library rail and a focus on one or more topics.
- The documentation in `docs/`, itself a folio library, and the specification in `docs/spec/`.
