# The folio model

This is the contract every other spec builds on: the genre cards, the packs, the skills and the engine. When a genre card or a skill disagrees with this file, this file wins and the other is fixed.

## 1. What folio is

folio lets a coding agent build and keep a knowledge library inside any project. A library is a graph of documents. Each document has one genre, and the genre fixes its job, its reader, its voice, its format and its checks. A genre gives structure and voice, never form: how a page looks is the author's, on a free canvas (§14). Every change to a library goes through one of seven skills. The `folio` command exists, but only skills call it, the way an agent calls git.

## 2. The library

A library is a folder holding a `folio.yaml`. It can be a project's `docs/` folder, a `notes/` folder, or a whole repository. One project can hold more than one library.

```
<library>/
  folio.yaml              the charter (written only by skills)
  content/                the documents, one folder per genre
  assets/
    figures/              figure sources and their rendered files
    refs.bib              the library's bibliography
    data/                 datasets that documents cite
  genres/<name>/          this library's genre overrides, variants and custom genres
  workflows/<name>.md     this library's own workflows
  packs/<name>/           this library's own packs
  .folio/                 generated indices (committed; the gate checks they are current)
```

`content/` holds every document, including every journal entry. Nothing outside `content/` is a document.

`.folio/` holds the generated indices: `catalog.json` (every document's metadata, a map's rows and the sections they sit in, and the topics it falls under, §5), `backlinks.json`, `search.json`, `nav.json` (guide navigation), `journal.json` (every journal entry, newest first) and `cards.json` (every flashcard). `folio index` writes them, and nobody edits them by hand. `.folio/redirects.json` is the one file there that is state, not an index: `folio mv`, `promote` and `rm` write it, and it is committed with the rest. `folio init` writes a `.gitignore` for `_site/`, the local server's runtime files and `.folio/build/`, where `folio paper build` compiles papers.

A library can sit inside a larger project. The charter's `root:` names the project root (§10). A path a document gives to something outside the library, such as a result's evidence or its re-derive command, resolves from that root.

## 3. Documents

Three principles shape every document:

- **Metadata holds every fact the engine needs** to render, search, filter or check a document. The body holds prose, and nothing in it is parsed back out.
- **What follows from links is generated, never written.** A list of what a document cites, what cites it, the work on a question, a guide's chapters, a record's current status: the engine derives each one.
- **A record is never edited.** A correction is a new document that points back, and the engine shows it on the one it corrects.

### What earns a page

A document is judged by its content, never by its size. Five questions apply to every genre, and each card's `## Earns its page` says what they mean for that genre:

| Question | When the answer is no |
| --- | --- |
| **Does it earn a page?** It holds knowledge that is not trivial, stays true when a result changes or a system it describes is rewritten, and adds something beyond its sources and the rest of the library. | Its content goes where it is used: a sentence in another document, a map row's reason, a flag, or nowhere. |
| **Is this its one home?** No fact, number or definition is written out again from another document. | Link the home instead. |
| **Is it clear?** A reader of the genre follows it without outside help, and a definition stands alone. | Revise it. |
| **Is it complete, and nothing more?** It says what its reader needs: short where the idea is simple, long where the idea needs the room. Padding and repetition are faults; length is not. | Add the missing step, or cut what is said twice. |
| **Does the form serve the content?** A figure, control, animation or table where it shows what prose cannot; prose where the material is one line of argument. | Redesign it (`craft/layout.md`). |

All five are judged, not checked: no word count or number of links decides them. The write skill asks them before it writes a document, and the organise skill's audit asks them of the documents already written.

### Where a document lives

- **The home page** is the map named `home`, at `content/index.html`. It is the one document outside its genre's folder, and the root of the no-orphans rule. It has no title of its own: the shell and the indices use the charter's `name`, so renaming the library renames its home page.
- **One document, one file, one genre.** The genre card names the path: `content/<folder>/<slug>.<ext>`, or `content/<folder>/<slug>/index.html` for a genre whose documents keep files beside them.
- **Formats.** HTML for pages, Markdown for records (a journal entry, and the lab pack's question, protocol, result and claim), LaTeX for the paper. Each genre has exactly one format.
- **The id.** Every document has an id: its slug for most genres, or a numbered id for record genres that declare a prefix (`R-12` for a result, `C-3` for a claim, `Q-4` for a question). A journal entry's id is its file's stem. Ids are unique across the whole library, whatever the genre, and compare without regard to case: `folio new` refuses a taken id (check `unique-id`), and every lookup finds `r-12` as `R-12`. A record id is never reused, even after its document is retired. Every command that takes a document accepts its id or its path.
- **An id never changes once committed.** When a move changes the slug of a committed document, `folio mv` writes the old id into its metadata as `id` and redirects the old address (redirects are state, kept in `.folio/redirects.json`). A document that was never committed takes its new slug as its id, with no redirect.

### Metadata

HTML documents carry metadata in `<meta>` tags in `<head>`, Markdown documents in YAML front matter, and a paper in its landing page. Every document has five fields:

| Field | Meaning | Required |
| --- | --- | --- |
| `title` | The document's title | yes |
| `description` | One line saying what it is, in its genre's voice. In HTML it is the standard `<meta name="description">`. | yes |
| `genre` | Its genre; must match its folder | yes |
| `status` | One of the states its card declares; absent means `live` | when the card's states do not include `live` |
| `tags` | Lowercase slugs: a YAML list, or comma-separated in HTML | no |
| `layout` | An HTML page's layout: `canvas`, the whole room between the rail and the page panel (the default), or `column`, the reading column (§14) | no |

A record genre adds `id`. The engine adds `created` and `updated` from git, and nobody writes them.

- **The shell renders the header from metadata.** The title, the description as its subtitle, the status, the dates (with "Frozen since" for a frozen document) and the tags are drawn by the shell, and the card's fields in the card's order. A document's body starts with its content, never with its own `<h1>` or subtitle. Search results, link previews and map rows use the same description.
- **Genre fields.** A card can declare more fields with `fields:` (format in `genre-format.md`). A field is declared only when the engine renders, filters or checks it: a result's `number`, a question's `rank`, a journal entry's `kind`. The gate checks each one is present when required and has its type (check `fields`). A field of type `id` is a citation, like a link.
- **Dates.** `created` and `updated` come from git. A genre declares a `date` field only when the date of the event can differ from the date of the commit: a journal entry and a result do. A project declares `reviewed`, the date its state was last confirmed.

### Parts and placeholders

- **Multi-part genres.** A guide has a front page and chapters. A paper has its LaTeX source, an HTML landing page, and its versions. The card declares each extra part under `parts:` (`genre-format.md`). The parts share the document's id, genre, status and tags; a part has its own title and description. A link to the document lands on its main file, or on the part the card marks `address: true` (a paper's landing page).
- **Placeholders.** `folio new` fills `{genre}` (the genre asked for, so a variant writes its own name), `{slug}`, `{n}` (the next free record number), `{nn}` (the next free two-digit part number), `{name}` (a part's name), `{date}` (today, `YYYY-MM-DD`) and `{yyyy}` (this year), and writes `--title`, `--description`, `--tags` and any `--<field>` into the metadata. Text in double braces, `{{like this}}`, is for the author to replace. The gate reports every one left in a document (check `placeholder`).

### Status and lifecycle

Each card declares its `states`, the status words its documents accept, and the gate rejects any other word (check `status`). Most cards use some of these four:

- `draft`: unfinished, and kept off the home page. A new document is `live`, because skeletons write no status; it is `draft` only when the author asks to hold it;
- `live`: current;
- `historical`: true of its time, and kept for the record;
- `retired`: replaced. It names its replacement in `replaced_by`, and the engine redirects its address there. The replacement may be a document in another library the charter names (`replaced_by: pier-folio:cti`, §4), when a library hands a subject to another.

A card can add states of its own: a project is `paused` or `done`, a protocol `locked`.

Each card says how its documents change over time (`lives:`), and the gate checks it against git:

- `revised`: edited in place.
- `permanent`: never edited once committed (check `permanent`). A journal entry and a result are permanent. A part can be permanent on its own, with its folder: a paper's source is revised, and each of its versions is a permanent snapshot. A permanent document writes no `status`: the engine derives it (below).
- `frozen`: edited freely until its status first reaches one of the card's `frozen_in` states, then never again, except its `status` field (check `frozen`). A report is frozen when it is `live`, a protocol when it is `locked`. The gate compares the file with the first commit that set a `frozen_in` state, so going back to `draft` does not unfreeze it. After that the status may move only forward, to one of the card's `frozen_exits` (a protocol to `abandoned`, a report to `historical`), in a commit that changes the status and nothing else.

### Corrections and derived status

Nothing that is permanent or frozen is edited to say it was wrong. Instead:

- **A newer record supersedes an older one** by naming it: `supersedes: R-1`. The engine marks R-1 `superseded`, shows a banner linking the newer one, and keeps R-1 at its address so old citations still show what they cited.
- **A journal entry retracts or corrects a document** by naming it in `about`, with kind `retraction` or `correction`. A retraction marks a record `retracted`. A correction shows as a banner on the document it names, with the entry's text.
- So a permanent document's status is derived: `superseded` if a document of its genre supersedes it, `retracted` if a retraction names it, `live` otherwise. A frozen document keeps the status it was frozen with, and shows its corrections the same way.

## 4. Links and citations

- **A citation is a link to the cited document.** In HTML, an `<a href>` to its path from the library's root, such as `/content/concepts/softmax/`. In Markdown, a link, or an id in backticks that matches a document (`R-12`, which the site renders as a link), or a field of type `id`. In LaTeX, `\fcite{<id>}`. The gate resolves every one, the way the exported site serves it (check `broken-link`).
- **Links to Markdown records.** An HTML page links a Markdown record by its source path, such as `/content/results/R-1.md`. The exported site renders each Markdown record as a page at the same path with `.html`, and rewrites the links to match. `folio cite <id>` prints the right markup for each format, always in the same form, so nobody works this out by hand.
- **One fact has one home.** A fact (a definition, a measured number, a decision) lives in exactly one document. Everything else cites that document by id and never restates its value as its own.
- **Links to another library.** A library can link documents in other folio libraries on the same machine, which the charter names under `libraries` (§10), each with its `path` and, optionally, the `url` where it is served. A link names the library as its scheme and the document's address in it: `<a href="pier-folio:/content/concepts/cti/">`, or `[CTI](pier-folio:/content/concepts/cti/)` in Markdown; `folio cite pier-folio:cti` prints it. The gate resolves the link against that library's files and redirects, as it would its own (check `broken-link`). Where the library is not at its path, as in a checkout without it, its links are not checked, and the gate says so once per library (check `library-link`, a warning). `folio serve` and `folio export` rewrite the link to the library's `url`, mark it with `data-library` and give it the target's title, and the shell shows which library it leads to; without a `url` the link is served as written. A link to another library is not a citation: it shows in no link panel, counts toward no card's `cites`, makes no document reachable, and has no hover definition.
- **Concepts are linked, not explained twice.** The second time a term needs explaining, it becomes a concept, and every mention links to it with `class="defn-link"`. Hovering the link shows the definition.
- **Link panels are generated.** The shell shows, beside every document, what it cites, what cites it, and the journal entries `about` it. A field of type `id` also shows on the document it names, under the field's name: a question lists the protocols whose `question` names it, and a protocol the results whose `protocol` names it. Nobody writes these lists by hand, so a genre never has a "rests on", "referenced in" or "work so far" section.
- **Siblings share ids and assets, never sentences.** A journal entry, a report and a paper about the same result each cite the result and reuse its figure from `assets/figures/`. None is generated from another.

## 5. Maps

- **A map is a document of the map genre:** a front door over part of the library. Each row links a document; the shell draws the link's text from the document's title, so the text in the file is only a fallback. A row may say, in one line, why to follow it from this map; without one, the shell shows the document's description. Rows keep the order and the group headings the map gives them (`folio map add --group --after`).
- **A library has as many maps as it needs,** at any scope: a topic, a question, a reading path, a project. Maps can list other maps.
- **Topics are the top-level maps:** the ones the charter lists under `home.maps`. The shell draws them on the home page, in that order, so the home page never lists them by hand. A home map is never a `draft` (check `home-maps`). A document is on every map that lists it. Nothing declares a topic on the document itself.
- **What falls under a topic** follows from the maps. A document is under a home map when the map reaches it through map rows (a row can list another map, whose rows count too), or when it is a concept linked from a document under it. A journal entry is under every topic of a document in its `about`. The home page is under every topic. `folio index` writes each document's topics, as home-map ids in the charter's order, into `catalog.json` under `topics`.
- **Concepts are filed under no topic.** They are listed on whatever maps use them, their backlinks show where, and they fall under every topic whose documents link them.
- **Tags are facets for filtering,** never structure.
- **No orphans.** Every document except a journal entry is listed on at least one map, or linked from a document that is (check `orphan`). A card with `on_map: required` needs a map row; `optional` is met by either. Links from maps and from documents on maps count, and so does a field of type `id` on such a document (a result whose `protocol` names a protocol on a map is reachable through it); links from journal entries do not. Every top-level map is reachable from the home page.

## 6. The journal

The journal is the dated record of what happened and what was decided. Each entry is its own document of the journal genre: a short Markdown file at `content/journal/{yyyy}/{date}-{slug}.md`, permanent once committed.

```yaml
---
title: The attention kernel subtracts the row maximum first
description: Half-precision scores overflowed in the softmax, so the kernel now subtracts each row's maximum.
genre: journal
date: 2026-10-03
kind: decision
about: [attention-kernel, softmax]
tags: [attention]
---
```

- `date` is the day of the event. `kind` is optional. `about` names the documents the entry concerns, and the entry shows on each of them.
- A library has one journal. The shell renders it as a timeline, filtered by kind, tag, date or `about`; a project page shows the entries about it.
- Two agents writing at once never touch the same file, and every entry can be linked and searched on its own.
- **Kinds** are an open set. The core has `decision`, `lesson`, `correction` and `retraction`. A pack adds its own (the lab pack adds `lock`, `run`, `kill`, `instrument` and `pivot`), and the charter adds more under `journal.kinds`. The gate accepts the union (check `kinds`).

## 7. Genres

A genre is a folder, `genres/<name>/`, holding:

- `GENRE.md`: front matter with the settings the engine reads, then the card the agent reads every time it writes one (format in `genre-format.md`);
- a skeleton: `skeleton.html`, `skeleton.md` or `skeleton.tex`, the file a new document starts from.

Where genres come from, in lookup order:

1. the library's own `genres/<name>/`;
2. a pack switched on in the charter;
3. folio's core.

The first one found wins, but an override in the library holds only what it changes: the card underneath still applies, so folio's upgrades flow in. Genre names are unique across the core and every pack. A pack never redefines a core genre.

- **Core genres (8):** concept, note, entry, map, guide, project, journal, paper.
- **Knowledge-base pack (3):** source, reading, survey.
- **Lab pack (5):** question, protocol, result, claim, report.

**What a card checks.** A card checks substance: where a document lives, its metadata and lifecycle, its place on the maps, and its duties to other documents (what it cites, what it must not restate, what it links). It never checks markup or size, except the few parts the machine reads: a concept's definition, a map's rows, a guide's chapters as parts, and the sections of Markdown records that tools parse. Word limits are for short records only (a journal entry, a result, a claim). Everything else in a card is guidance on what a good document of the genre holds, judged, not checked (`genre-format.md`).

**Variants.** A genre can `extend` another (`paper-workshop` extends `paper`). It inherits everything and overrides only what it states: usually the voice, the reader and the limits. A variant is for a second audience. Voice is never set per document.

**Promotion.** A document changes genre only by promotion (a note that grew sections becomes an entry), done by the organise skill, which keeps its id, links, comments and dates.

## 8. Packs

A pack is data, never a skill:

```
packs/<name>/
  PACK.md                 name, purpose, what it adds (format in pack-format.md)
  genres/<name>/          GENRE.md + skeleton each
  workflows/<name>.md     WORKFLOW.md files the run skill follows
  rules.md                optional library-wide rules the gate enforces
```

- A pack is switched on for the whole library, in the charter. Switching it on adds its genres, workflows, rules and journal kinds, and rewrites nothing. Its rules can flag existing documents; the organise skill proposes the fixes.
- Switching a pack off hides its genres and workflows from new work. Existing documents stay valid.
- folio ships two packs: `knowledge-base` and `lab`. A library's own packs live in its `packs/`, or in a git repository the charter pins by URL and commit.
- Several packs make one library and one graph: one set of concepts, one search.

## 9. Workflows

A workflow is a multi-step procedure about documents that no single genre card holds: ingesting a source, quizzing the reader, recording a result. It is a Markdown file with front matter (format in `pack-format.md`). The run skill follows it step by step, and every document it produces goes through the write skill. Lookup order is the same as for genres.

## 10. The charter

`folio.yaml` says what this library is. Only the set-up and configure skills write it, and every change is shown as a diff and recorded in the journal.

```yaml
folio: 0.1.0                 # the engine version this library is checked with
name: Proof repair notes
purpose: My notes on proof repair, for me and my co-authors.
reader: One reader, the owner, who knows the field.
voice: Plain and precise. No hedging. British spelling.
packs:
  - lab
  - knowledge-base
  - name: my-pack
    git: https://github.com/<owner>/<repo>
    ref: <commit>
home:
  maps: [proof-repair, solvers]   # the top-level maps, in order
genres:                            # optional per-genre settings
  journal: { max_words: 120 }
  survey: { enabled: false }
checks:                            # which checks fail the gate and which only warn
  uncited-number: error
assets: assets/
root: ..                           # the project root; paths outside the library resolve from here
theme: folio                       # or a theme folder in the library
journal:
  kinds: [meeting]                 # kinds this library adds to the core's and the packs'
search:                            # other libraries to search alongside this one
  - ../lab/docs
libraries:                         # other libraries this one links to (§4)
  pier-folio:
    path: ../../pier-folio           # where the library is on this machine
    url: http://localhost:5180       # where it is served; links are rewritten to it
site_url: https://example.org/notes   # where the exported site is published; a paper's \fcite links resolve from it
comments:
  identity_header: X-Forwarded-User   # the header a sign-in proxy names the reader in, for a deployed server
```

Defaults: no packs, the folio theme, `assets/`, `root` is the folder holding `folio.yaml`, the reader is the owner, the voice is plain and precise, no `site_url` (a paper's `\fcite` then prints the id as plain text), and no `comments.identity_header` (comments are then taken only on 127.0.0.1, as the git user). `comments.identity_header` must be a header name: letters, digits and hyphens.

Under `libraries:`, each name is a lowercase slug, used as the scheme of a link (§4), and may not be a scheme the web already uses (`http`, `https`, `mailto` and the like). `path` is required, relative to the folder holding `folio.yaml`; `url` is optional and must be an http(s) address. `folio search --all` searches these libraries too, where their path holds one.

Under `genres:`, a genre takes `enabled` and any setting of its card's checks. Under `checks:`, a check takes `error`, `warning` or `off`. Check names are listed in `checks.md`.


## 11. The seven skills

| Skill | Does |
| --- | --- |
| set-up | Installs folio in a project or a new repository, asks what the library is for, writes the charter, creates the home page, records the setup in the journal, runs the gate. |
| configure | Changes the charter: packs, maps on the home page, a genre's limits, a new genre, a variant, a workflow, a pack made from existing genres. |
| write | Adds or revises any document, in its genre's voice and format, links its concepts, flags only what needs the owner's judgement, updates the maps, runs the gate. |
| organise | Moves, merges, promotes and retires documents and maps, with every link, comment and date intact. Runs health passes, and audits documents against the current cards: whether each still earns its page (§3), and in what form. |
| address | Answers the comments readers left on rendered pages, on the page they were left on. |
| publish | Exports the static site, and builds a paper and freezes versions of it. Freezing copies the paper's source and built PDF into a permanent `versions/<name>/` folder and adds a journal entry; the source stays revised, and a later change is frozen as a new version. |
| run | Follows a workflow from a pack or the library, step by step; every document it produces goes through write. |

Every skill starts the same way: it reads the charter, the genres available (library, packs, core) and the workflows. So a new genre, workflow or pack never needs a new skill. Skill contracts follow `skill-format.md`. A library keeps its own copy of the skills; after folio is upgraded, `folio skills update` refreshes it.

## 12. The review loop

- **Flags.** A flag marks only what needs the owner's judgement: a claim stated as fact that its sources do not support and the owner may know better (an inference about someone else's result, a claim from general knowledge the argument rests on), a number or name not verified against its source, or a passage the agent could not settle (text it may not rewrite, a source to find). The flag's body says what there is to decide. Routine work raises none: the agent's own framing, layout, wording and captions, an example that illustrates without asserting a new fact, the library's synthesis that is the page's job, and corrections of plain errors (the commit records those). A flag rests until the owner keeps it or asks for a change.
- **Questions.** A reader selects a passage on the rendered page and asks a question. It is saved in a file beside the document. The address skill answers it, edits the document and replies.
- A document whose quoted passage changed under an open question fails the gate.
- **Thread states:** `open` (waits for an answer), `noted` (a flag at rest), `addressed` (answered or kept), `declined` (not acted on, with a reason), `withdrawn` (taken back by its author). Nothing is deleted.
- **Plain words.** The file and the command line keep the five states. A reader sees three words: *waiting* (`open`), *resting* (`noted`) and *closed* (the other three), with how it closed: *changed*, *kept*, *declined* or *withdrawn*. A thread moved to `addressed` from `noted` was kept; one moved to `addressed` from `open` was changed.
- **Keep or change.** A resting flag shows two buttons. Keep closes it as kept: a reply "Kept." that moves it to `addressed`. Change asks what to change; that text is a reply that moves the flag to `open`, and the address skill picks it up as a question.
- **What changed.** An addressed thread shows the agent's reply and the passage before and after. The server computes it from git: the document as of the commit that opened the thread (or last reopened it) against the document as of the commit that recorded the addressing reply. Without that history, as on an exported site or before the reply is committed, nothing is shown.
- **Review.** `/content/review/` lists every waiting question and every resting flag across the library, newest first, each linking to its passage. The home page shows one line, such as "3 questions waiting on the agent, 5 flags for you", linking to it.

### Who comments, and where a comment goes

- **No name field.** The server knows who is writing. Locally it is the library repository's `git config user.name` (the operating-system user outside git). On a deployed server it is the request header the host's sign-in proxy sets, named in the charter as `comments.identity_header`.
- **Refused, never anonymous.** When `folio serve` listens on an address other than this machine's and no identity header is configured, or a request lacks the header, comments are read-only and the panel says why.
- **One commit per comment.** Each new thread or reply is committed on the current branch by the server, in a commit holding only that page's annotation file, with the message "Comment on <id>", authored as the commenter. Outside git the file is written and nothing else, and the server's startup line says so.
- **Pushed when deployed.** With `folio serve --push`, the server pulls with rebase before it writes and pushes after it commits. On a conflict or a failed push, it rolls the local write back, refuses the comment and shows the reader the error. A comment is never lost or dropped in silence.
- **Safe defaults.** `folio serve` listens on 127.0.0.1 unless `--host` is given. A comment request is JSON, at most 64 KB, sent from a page the same server served, about a document file under `content/`. On 127.0.0.1, a request whose Host is not this machine's gets nothing.
- **An exported site has no comments.** It leaves the annotation files out, hides the comment buttons, and its page panel says: "Comments are open where this library is served with folio serve."

## 13. The gate

`folio check` runs offline, names every problem in one pass and never changes a file. CI runs the same command. It checks:

- every link and citation resolves, the way the exported site serves it;
- every document meets its genre's card: location, metadata and fields, status words, the parts the machine reads, word limits on short records and the card's other checks;
- no placeholder is left in a document;
- each document keeps its lifecycle: permanent and frozen documents against git history;
- no orphans; every top-level map in the charter exists;
- one fact, one home: a concept's definition is not restated, and pack rules hold (for the lab pack, every number cites a result);
- ids are unique across the library, and record ids are never reused;
- the generated indices in `.folio/` are current;
- open questions still quote text that is on the page;
- papers: every `\fcite` resolves, every figure comes from `assets/figures/`.

Every check has a name, listed with its settings and default severity in `checks.md`. A card or a pack uses only names from that list. The charter can make any check an error, a warning, or off.

## 14. The shell

Every HTML document uses the shared shell: one stylesheet, light and dark themes, the library rail, the header drawn from metadata, the search palette, link previews, concept popovers, the page panel (outline, metadata, the generated link panels), the comment panel and the Review page (§12). Markdown records are rendered in the same shell.

**The canvas.** Below the header, an HTML page is a free canvas: it has all the room between the library rail and the page panel, with no measure, and it lays itself out for what it must show, with figures, diagrams, interactive controls and its own grid. A page may carry its own `<style>` and `<script>` in its `<head>` or body. The canvas is a size container named `folio-canvas`, so a page adapts to its room with `@container folio-canvas (...)` queries, since the panels share the window with it. Five things stay fixed, because the library reads them:

- **The words are in the markup.** A script may arrange, reveal, highlight and animate the page's words, never write them: comments are anchored, and search and the gate read the text, from the file.
- **The genre's hooks stay:** a concept's `defn`, a map's `rows`, and the rest its card names.
- **The voice stays:** the genre's register, every claim supported where it is made, every number cited, a flag only where the owner has something to decide.
- **Colours come from the shell's tokens,** never a hex value, so a page reads in both themes.
- **The header is the shell's:** a page writes no `<h1>` and no subtitle of its own.

A page that is one line of argument may opt into the reading column with `<meta name="layout" content="column">`; a Markdown record is always rendered in it. The shell offers colour registers, a few shared components and KaTeX math (`$…$`, `\[…\]`, on a page carrying `<meta name="math" content="katex">`), all described in `shell/COMPONENTS.md`. How to choose a page's form is in `craft/layout.md`. A figure, control or animation earns its place by showing what prose cannot; a page uses one where it carries the idea, never to decorate. The shell shows an inline SVG near the size it was drawn for, so its labels do not grow with the window, and lets the reader open any figure larger in a dialog.

The library rail is on the left of every page, the home page, the journal and the Review page included. It links home, the journal and, when served, the Review page. Then it lists the charter's home maps in order, each a group of the documents it lists, and then every document other than a journal entry, grouped by genre. Inside a map's group the documents keep the map's own sections: each list of rows sits under the heading nearest above it on the map page, and consecutive lists under one heading are one section. A map with two or more such sections shows them as sub-groups, each counting its genres while closed; a long map (more than twelve rows) opens only its first section and the one being read. A map with fewer sections lists its documents by genre in reading order (guide, entry, concept, note, survey, reading, source) when it has more than six, and as one list otherwise. Each document in a map's group carries its genre's mark, a letter or two with the genre's name on hover, and a key at the foot of the rail names the marks shown. The map's first document is marked Start. It is drawn from the indices alone (`catalog.json`, `nav.json`) and the site data, so no page lists the library by hand. The current page is marked and scrolled into view, and a guide being read shows its chapters. A group the reader opens or closes stays so in that browser. On a wide screen the rail sits beside the page and the page panel; the `[` key or the top bar's library button hides or shows it, and that choice is remembered. On a narrow screen it is a drawer that the same button or key opens and Escape, a click outside or a link closes.

**Topic focus.** A reader can focus the library on one or more topics, chosen from the Focus control in the top bar. A document is in focus when it falls under a chosen topic (§5). While a focus is on, the rail (its maps, genre groups and counts), search, the journal view, the Review page, the home page's inbox line, its map cards and its recent entries show only what is in focus, and a chip in the top bar names the focus and clears it in one click. Search can still widen to the whole library for one search. Maps, genres and tags still filter inside the focus. A page outside the focus still opens by its address and says, under its header, that it is outside the focus. While it is read, the rail keeps it in its genre group, marked. The focus is remembered in that browser. It is computed from the catalog alone, so it works the same on an exported site.

A page loads the shell from the library's root, with `<link rel="stylesheet" href="/shell/folio.css">` and `<script src="/shell/folio.js" defer></script>` in its `<head>`. Every skeleton carries both lines. `folio serve` and `folio export` serve the shell at `/shell/` and add either line a page lacks, so a frozen page never needs an edit to get it.

Two components ask the reader something:

- **A check-yourself**, `<details class="check"><summary>question</summary><div class="ans">answer</div></details>`, ends a section of an entry or a guide chapter. It tests that section.
- **A flashcard**, `<details class="card"><summary>question</summary>answer</details>`, can sit in any HTML document. The summary is the question; the rest is the answer. `folio index` collects every card into `.folio/cards.json`, and `folio cards` lists them. A card is a component, not a genre. Pages are plain HTML in git and need no build step to read. `folio serve` serves the library, with comments (§12); `folio export` writes a static site. Export leaves out kept originals (`original.*` in a source's folder), annotation files and the review page; `folio serve` still shows them. The shell's components are described in `shell/COMPONENTS.md`, and the craft of figures, tables and diagrams in `craft/`. Both ship with folio, and `folio genre` and the write skill point to them.

## 15. What folio does not do

- It does not judge whether a result counts. A tool built on folio decides that (lab-kit for a lab) and then writes the documents through folio.
- It does not host anything. Publishing writes static files.
- It does not let a skill skip the gate.
