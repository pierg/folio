---
name: map
format: html
path: content/maps/{slug}.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks:
  require: [rows]
on_map: required
---

# Map

A map is a front door over part of the library: it lists the documents worth following, in the order to read them.

## Reader

Someone arriving cold. They need to know what is here, where to start, and what to skip.

## Voice

Opinionated and brief. A row's reason, when it has one, says why to follow the link from this map, not what the document is. A short stance can open the map.

> Start here: the shortest argument for why attention costs what it does.

## Metadata

No fields beyond the core. The `title` is the scope of the map, such as a topic, a question or a reading path. The `description` says in one sentence what the map covers.

## Shape

The shell draws the title and description above the body.

One part is required, because the machine reads it:

- `rows`: one or more `<ul class="rows">`, each under an optional `<h2>` that names a group. Each row is `<li><a href="...">Title</a></li>`, with an optional `<span class="why">reason</span>` after the link. The catalog, the rail and topic focus read these rows. The shell draws the link text from the catalog's title, so the title in the file is only a fallback for reading without the shell, and the gate's number rules never read it. Without a reason, the shell shows the target's description. A row can point to any document, including another map.

Around the rows the page is a canvas. What a good map usually does, judged, not checked:

- It says in a few sentences what the library holds here now, and what is still unsettled.
- It groups the rows the way a newcomer should read them, each group under its heading, each row with a reason when the description does not give one.
- It may draw the territory: a figure of how the documents relate, placed above or beside the rows. The rows still list every document the map holds.
- It ends with the questions this part of the library has not answered yet.

**The home page is a map.** It is the map with the id `home`, and it lives at `content/index.html`, not under `content/maps/`. It has no title of its own: the shell and the indices use the charter's `name`, so `folio config set name` renames it. The shell draws the top-level maps the charter names under `home.maps`, in that order, so the home page never lists them by hand. It may still hold an intro, a figure and rows of its own. It is the root: nothing needs to list it. It never lists a `draft` document.

## Forbidden

- A reason that only repeats the title or the description. Leave the reason out instead. Judged, not checked.
- A map that explains. Its stance is a few sentences; the explaining belongs in an entry it lists. Judged, not checked.
- A top-level map listed by hand on the home page. The shell draws them from the charter. Judged, not checked.
- A top-level map in the charter that does not exist, or is a `draft`. Caught by the gate check `home-maps`.
- A `draft` document in the home page's own rows. Judged, not checked.
- A map listed nowhere. Every map except `home` and the top-level maps in the charter is a row on another map. Caught by `orphan`, because the card says `on_map: required`.
- Declaring a document's topic on the document itself. A document is on every map that lists it. Judged, not checked; the genre's metadata has no topic field.

## Steps

- Delete the optional parts you do not use. A placeholder left in the page is reported by the gate.
- Add rows with `folio map add <map> <doc>`. Add `--reason ".."` when this map has a reason to follow the link that the description does not give. Place the row with `--group "<heading>"` (under that `<h2>`; a new group is made at the end of the map) and `--after <doc>` (after that row); without them it goes at the end. To put a new group right after an existing one, give `--group "<new heading>" --after "<heading>"`. The first row added to a fresh map takes the place of the skeleton's placeholder group.
- Write a reason for a reader deciding whether to click: what they gain, or when to read it.
- Order rows the way a newcomer should read them, or by importance. Never alphabetically by default.
- A map past about forty rows is split into smaller maps, and listed from the larger one. Judged, not checked.
- Adding a top-level map is a charter change, made by the configure skill. It updates `home.maps`, and the home page follows. Set the map `live` first: a `draft` map cannot be a home map.

## Lifecycle

Revised in place, every time a document joins or leaves its scope. The write skill adds the row in the same change as the document. Maps are merged, split and renamed by the organise skill, with every link kept. A map whose scope the library dropped is `retired` into the map that absorbed it.

## Example

```html
<meta name="title" content="Attention">
<meta name="description" content="What this library knows about attention in transformers, and where to start.">
<!-- body -->
<ul class="rows">
<li><a href="/content/concepts/softmax/">Softmax</a> <span class="why">Read first: every other page leans on it.</span></li>
<li><a href="/content/entries/attention-is-quadratic/">Why attention is quadratic</a></li>
</ul>
```
