# Changelog

## Unreleased

Pages get a free canvas again. A genre gives structure and voice; the form is the page's.

- Every HTML page is a canvas: all the room between the rail and the page panel, with its own `<style>` and `<script>`, adapting with `@container folio-canvas` queries. The reading column is opt-in with `<meta name="layout" content="column">`; Markdown records always use it. The gate checks `layout` is `canvas` or `column`.
- Genre cards check substance, not form. Word caps are gone from every page genre (they stay on journal entries, results and claims). Gone too: `forbid: [h2]` on concept and note, the `require` parts nothing reads (entry `thesis` and `h2`, project `state` and `next`, guide `start` and chapter sections, reading, source `about`, survey and report sections), and the `check_each_section` check. `forward_links` is judged unless a library sets it. `min_sources` counts the sources a survey cites anywhere. Each card's Shape is now guidance, judged, not checked.
- The shell adds the colour registers (`--teal`, `--indigo`, `--blue`, `--amber`, `--red`; `--azure`, `--violet`, `--orange`; `--kept`, `--discarded`, `--rejected`, `--untested`), a few shared components (`.cols`, `.lane`, `.note`, `.law`, `.chip`, `.v`, `.tbtn`) and KaTeX math, vendored, on a page with `<meta name="math">`.
- `craft/layout.md` holds the canvas contract and the "choosing a form" playbook; new `code.md`, `comparison.md` and `timeline.md` guides. The write skill designs the page, and `folio genre <name>` ends with where the craft guides are installed.
- The documentation library is rebuilt as canvas pages.
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
