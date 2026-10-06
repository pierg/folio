# GENRE.md: how a genre is written

A genre is `genres/<name>/GENRE.md` plus one skeleton file. The front matter is what the engine reads. The body is what the agent reads every time it writes or revises a document of this genre. Read [`model.md`](model.md) first.

## Front matter

```yaml
---
name: concept                 # unique across the core and every pack
extends: null                 # another genre's name, for a variant
pack: null                    # set by a pack's genres; null for core
format: html                  # html | markdown | latex
path: content/concepts/{slug}/index.html   # where its documents live
id: slug                      # slug | prefix:R  (numbered records: R-1, R-2, ...)
skeleton: skeleton.html
lives: revised                # revised | permanent | frozen (model.md §3)
states: [draft, live, historical, retired]   # the status words it accepts
frozen_in: []                 # with lives: frozen, the states in which it is never edited
frozen_exits: []              # with lives: frozen, the states it may move to once frozen
fields:                       # genre fields beyond the core metadata
  - { name: rank, type: integer, required: true }
checks:                       # what the gate checks; each a named check with its settings
  require: [defn]             # required parts the machine reads, by the names the card defines
  cites: { defn: none }       # the definition cites nothing
  defined_once: true
on_map: required              # required | optional | never | exempt
parts:                        # only for a genre whose documents have more than one file
  chapter:                    # each part: its own path and skeleton, and checks and on_map if they differ
    path: content/guides/{slug}/{nn}-{name}.html
    skeleton: skeleton-chapter.html
    on_map: never
---
```

- `states`: every status word the genre accepts, `draft` first when the genre has drafts. The model's four (`draft`, `live`, `historical`, `retired`) are common, never required.
- `lives`, `frozen_in` and `frozen_exits`: `revised` documents are edited in place. `permanent` documents are never edited once committed, and write no `status`: the engine derives it (model.md §3). `frozen` documents are never edited once their status first reaches one of `frozen_in`, except that status. The gate compares them with the first commit that set a `frozen_in` state. From then on the status may change only to one of `frozen_exits`, in a commit that changes nothing else (check `frozen`).
- `fields`: each field has a `name`, a `type` and `required` (default `false`). The types are:
  - `string`, `integer`, and `date` (`YYYY-MM-DD`);
  - `enum`, with `values: [...]`;
  - `id`, a document id. An optional `genre:` names the genre it must be, and an optional `status: [...]` the states it must be in;
  - `ids`, a list of ids;
  - `path`, a file or folder that must exist, resolved from the charter's `root`.
  - The core metadata (`title`, `description`, `genre`, `status`, `tags`, and `id` for a record) is never declared again.
- A field is declared only when the engine renders, filters or checks it. Anything else belongs in the body.
- `on_map`: `required` means the document is a row on at least one map. `optional` means a map row, or a link from a document that is on a map. `never` means it is reached only through its parent (a guide's chapter). `exempt` means it is outside the no-orphans rule (a journal entry).
- `parts`: each extra part has a `path` and a `skeleton`, and its own title and description. It takes the genre's checks and `on_map` unless it states its own. A part may set `lives: permanent` (default `revised`): it is a snapshot a command writes, never edited once committed, together with every file in its own folder when its path gives it one (check `permanent`). `folio new` never makes a permanent part. `address: true` marks the part a link to the document lands on. `folio new <genre> <slug> --part <part> <name>` creates one.
- `checks`: the names and settings are listed in [`checks.md`](checks.md), with their defaults. A card uses only names from that list. Card keys are snake_case.
- **A card checks substance, never form.** It checks where a document lives, its metadata and lifecycle, its place on the maps, and its duties to other documents: what it must cite, what it must not restate, what it must link. It does not check markup or size. `require` names only a part the engine or the shell reads (a concept's `defn`, a map's `rows`), or one a tool built on folio parses (a lab record's sections). `max_words` is for short records, such as a journal entry or a result, never for a page. A library's own card may add a form check of its own, with `forbid`, `require` or `max_words`.
- Path templates and skeletons use the placeholders `folio new` fills: `{genre}`, `{slug}`, `{n}`, `{nn}`, `{name}`, `{date}` and `{yyyy}` (model.md §3). A skeleton writes its genre as `{genre}`, never as a fixed name, so a variant's documents carry the variant's name.

- Every setting has a default in the core, so a card states only what differs.
- A library override (`<library>/genres/concept/GENRE.md`) holds front matter keys and body sections it changes, and nothing else. The engine merges it over the card below it: keys by key, body sections by heading.
- A variant sets `extends:` and states only what differs from its parent. A body section it states replaces the parent's section of the same heading whole, so a variant that changes `## Forbidden` restates every item it keeps. Its checks are still inherited key by key.

## Body

The body has these sections, in this order. A section with nothing to say is left out.

- `# <Name>`, then one sentence: the job, the question this genre answers that no other does.
- `## Reader`: who reads it and what they already know.
- `## Voice`: the register, in a few plain sentences, with one short example of a sentence in that voice.
- `## Metadata`: the genre's fields, each with what it is for, and what a good `description` says for this genre.
- `## Shape`: first the parts the machine reads, the ones the front matter's `require` names, with the markup that carries each one. Then what a good document of this genre usually holds, as guidance, judged, not checked. It never prescribes a layout: an HTML page is a canvas the author lays out for what it must show (`craft/layout.md`). A Markdown record's Shape names its `##` sections, since tools read them. The body starts with content: the shell draws the title and description, and the generated link panels (model.md §4). A card never asks for a part that restates metadata or links.
- `## Forbidden`: what this genre never does, each item saying which check catches it or "judged, not checked".
- `## Steps`: what is special about writing or revising this genre, beyond the write skill's own steps (check the term is not already defined; append, never edit; re-derive the number).
- `## Lifecycle`: how it changes over time, what freezes it, and what it is promoted to or from.
- `## Example`: a short, complete example, or the skeleton's filled-in version, in a fenced block.

## Rules for every card

- Plain words, short sentences, one idea per sentence. A card is read by an agent and by a person deciding whether to change it.
- Every rule says what checks it. A rule nothing checks says "judged, not checked".
- No reference to any particular project, person or organisation. Examples are generic or about folio itself.
- The skeleton is a valid document of the genre. It carries `title`, `description`, `genre` (as `{genre}`) and `tags`, and writes no `status`: a new document is `live` unless its author asks to hold it as a `draft`. Its `{{...}}` placeholders are reported by the gate (check `placeholder`) until the author fills them.
