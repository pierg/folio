# The checks

This is the one list of every check `folio check` runs. A genre card, a pack card and a pack's `rules.md` use only names from this list. Read [`model.md`](model.md) first.

## Names

- **Card checks** are keys under a card's `checks:`, so their names are snake_case (`max_words`). Each applies to the documents of that genre.
- **Gate checks and rule checks** run across the whole library, so their names are kebab-case (`uncited-number`). A gate check always runs. A rule check runs while its pack is on.
- **Lifecycle checks** (`permanent`, `frozen`) are turned on by the card's `lives:`. A card lists one under `checks:` only to give it settings.

The charter sets any check's severity by its name: `checks: { uncited-number: error, max_words: warning }`. The values are `error`, `warning` and `off`. An error fails the gate; a warning is reported and does not.

## Gate checks

These run on every document. No card needs to name them.

| Check | What it checks | Default |
| --- | --- | --- |
| `broken-link` | Every link and citation resolves, the way the exported site serves it: an `href`, an id in backticks, a field of type `id`, a `\fcite`, and a link into another library the charter names, where that library is at its path. | error |
| `library-link` | A library the charter names under `libraries` is at its path, so links into it are checked. Reported once per library that is not, with the number of its links left unchecked. | warning |
| `location` | A document sits at its genre's `path`, and its `genre` metadata matches. | error |
| `fields` | The core metadata is present (`title`, `description`, `genre`, and `id` for a record), a page's `layout`, when present, is `canvas` or `column`, a permanent document writes no `status`, and every field the card declares under `fields:` is present when required and has its type. An `id` field resolves, and meets its `genre` and `status` limits. A `path` field exists, resolved from the charter's `root`. | error |
| `status` | The status is one of the card's `states`, or absent when the card has `live`. | error |
| `placeholder` | No `{{...}}` placeholder is left in a document. | error |
| `orphan` | The no-orphans rule: a document is on a map, or linked from a map or from a document on a map, as its card's `on_map` asks. A field of type `id` counts as a link both ways, so a document named by a reachable document's field, or naming one, is reachable. Links from journal entries do not count. | error |
| `home-maps` | Every map the charter lists under `home.maps` exists and is not a `draft`. | error |
| `unique-id` | Every id is unique across the library, whatever the genre, compared without regard to case: slugs, record ids, and journal entry ids (their file stems). A record id is in its genre's prefix and is never reused, even after its document is retired. | error |
| `index-current` | The generated indices in `.folio/` match what `folio index` would write. | error |
| `stale-quote` | An open question still quotes text that is on its document. | error |

## Card checks

A retired document is held only to its lifecycle checks (`permanent`, `frozen`): its address redirects to its replacement, so what its body cites or links no longer matters.

| Check | Settings | What it checks | Default | Used by |
| --- | --- | --- | --- | --- |
| `require` | a list of part names | Each named part of the body is present. In LaTeX, a part is an environment or command of that name (`abstract`, `bibliography`). Order is judged, not checked. The card's Shape defines each name. `h2` is at least one `<h2>` section. In Markdown, a part is a `##` section. A document has no `<h1>` of its own: the shell draws the title. A core or pack card requires only a part the engine or the shell reads, or that a tool built on folio parses. | error | concept (`defn`), map (`rows`), source (`identifiers`), paper, question, protocol, result, claim |
| `forbid` | a list of elements or part names | None of them appears. | error | none in the core; a library's own cards |
| `max_words` | a number | The body has at most this many words. Metadata, code and markup are not counted. Pages carry no cap: it is for short records. | error | journal, result, claim |
| `cites` | `none`, `any` or `results`, or a map from a part name to one of those | `none`: the document (or the part) cites no library document; links to concepts with `class="defn-link"` do not count. `any`: it cites at least one document. `results`: it cites at least one result. | error | concept (`{ defn: none }`), note, entry, paper, source, reading, survey, claim, report |
| `defined_once` | `true` | No other document holds a `defn` with the same `defn-name`. | error | concept |
| `min_links` | a number | The document links to at least this many other documents. | error | note |
| `forward_links` | `marked` | A link to a later chapter carries `data-fwd`. | error | none in the core; a library may set it on a guide's chapters |
| `stale_after_days` | a number | A `live` document's `reviewed` date is no older than this. | warning | project |
| `permanent` | `true` | Compared with git history: the file is unchanged since its first commit. Turned on by `lives: permanent`. A part marked `lives: permanent` is checked the same way, and when its path gives it a folder of its own, so is every file in that folder: none may change, appear or disappear (annotation files aside). | error | journal, result, paper (`version` part) |
| `frozen` | `true` | Once the status has reached one of the card's `frozen_in` states, the file matches the first commit that set such a state, except its `status` field. The status may then change only to one of the card's `frozen_exits`. Turned on by `lives: frozen`. | error | report, protocol |
| `kinds` | a list of kinds | A journal entry's `kind`, when present, is one the library accepts: this list, plus the `journal_kinds` of every pack switched on, plus the charter's `journal.kinds`. | error | journal |
| `bib` | a path | Every `\cite` key is in this file, and the paper has no bibliography of its own. | error | paper |
| `figures` | a path | Every `\includegraphics` names a file in this folder. | error | paper |
| `original_beside` | `true` | The `original` field names a file `original.<ext>` in the document's folder, or starts with `Not kept:` and a reason. | error | source |
| `min_sources` | a number | The document cites at least this many distinct sources or readings, wherever in the page. | error | survey |
| `answer_cites` | a list of genres | When the status is `answered` or `narrowed`, the `answer` part cites at least one document of these genres. | error | question |
| `prediction_ids` | `true` | Every item in the `predictions` part opens with its id, `P1:`, `P2:` and so on, numbered from 1 without gaps, and ends with `Confidence: <n>%`. | error | protocol |
| `rule_ids` | `true` | Every item in the `rules` part opens with its id, `D1:`, `D2:` and so on, numbered from 1 without gaps. Exactly one item is marked `(kill)` after its id. | error | protocol |
| `pinned_config` | `true` | The `configuration` part holds one fenced `yaml` block that parses. | error | protocol |

## Rule checks

These come with a pack's `rules.md` and run while the pack is on.

| Check | Pack | What it checks | Default |
| --- | --- | --- | --- |
| `uncited-number` | lab | A number shaped like a measurement, on a page, in a paper or in a claim's body, cites a result in the same sentence, list item or table row. A citation of a protocol there also counts (a pre-registered threshold), and with the knowledge-base pack on, so does a citation of the source that reported it. A map row's link text is not read: the shell draws it from the catalog. | warning in a new library; the charter makes it an error |
| `cites-superseded` | lab | A revised document cites only results whose derived status is `live`. Permanent and frozen documents are not flagged: the banner on the superseded result says so. Historical and retired documents are not flagged either. Nor is a citation whose sentence, list item or table row says "retracted" or "superseded": that is an honest mention. | warning |
| `unverified-identifier` | knowledge-base | Every identifier in a source is an `<a class="identifier">` with a `data-kind`, a `data-verified` date, and a link and text that name the same identifier. | error |

## Adding a check

A check is added to the engine and to this list in the same change. A library's own pack can only combine the checks listed here; it cannot invent one.
