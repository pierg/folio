---
name: organise
description: >-
  Reorganise a folio library without breaking it: move, rename, merge, promote and
  retire documents and maps, keep maps current, tidy tags, and run health passes,
  with every link, comment, id and date kept. Use when the user says "organise",
  "reorganise", "tidy", "clean up", "tidy the maps", "merge these", "merge these topics",
  "split this map", "rebalance the maps", "this heading is too big", "rename this page", "move this", "promote this note", "retire this",
  "this is a duplicate", "fold this into that", "clean up the tags", "what is on no map",
  "is the library healthy?", "health check", "fix what the new pack flagged",
  "audit the library", "does this still earn its page", "review every page against
  the cards", or "bring the library up to the new folio".
---

# organise

Change where documents live and how the maps reach them, with every link, comment and date intact.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`, especially the home maps and packs.
3. List what is available: `folio genres` and `folio workflows`.
4. Look before acting: `folio maps`, `folio tags` and `folio check`.
5. When a document changes genre, read the target card: `folio genre <name>`.

## Rules

1. Move, promote and retire only through `folio mv`, `folio promote` and `folio rm`. A plain file move breaks links, comments and dates.
2. Never move a document with a version-control move command, for the same reason. `folio mv` and `folio promote` stage the rename in git themselves.
3. Settle open questions on a document before you move, merge or retire it. Use the address skill.
4. Prose changes go through the write skill. This skill changes places, not words.
5. A map row links a document. Give it a one-line reason only when this map's reader needs one; without it, the row shows the document's description.
6. Every page has one place: a document whose card says `on_map: placed` is one row on one home map, under one heading. Move a place with `folio map move`, never by adding a second row. A document whose card says `cited` (a source) takes no row; the maps whose pages cite it list it.
7. Tags are facets for filtering, never structure. Structure lives in maps.
8. Structural changes are the owner's call: a new top-level map, a merge, a retirement of their own writing, and any move or rename of an existing page, heading or map. Propose, say why, and act when asked. Placing a new page is not structural: do it.
9. Record every reorganisation as a journal entry of kind `decision`, old names to new, about the documents and maps it touched.
10. An audit proposes and the owner decides. Report every verdict before changing anything, and apply only what the owner approved.

## Steps

Pick the change, then follow its line.

1. **Move or rename a document:** `folio mv <doc> <to>`. Links are rewritten and dates kept. A committed document keeps its id, and its old address redirects. A document never committed takes the new slug as its id, with no redirect, so a move is how to fix a slug before the first commit.
2. **Promote a document** that has outgrown its genre (for example, a short note that grew sections): `folio promote <doc> <genre>`. Then revise it in the new genre's voice through write.
3. **Merge two documents:** pick the one to keep. Fold the other's surviving content into it through write. Then `folio rm <other> --to <kept>`.
4. **Fold a thin definition** into the document that uses it: same as a merge. The concept card's `## Earns its page` says when a term earns its own definition document.
5. **Retire a document:** `folio rm <doc> --to <replacement>`. Its links and address go to the replacement. It prints a `review:` line for every link whose text still names the retired document's title. Review each one, and reword through write any that no longer fits. When the subject has moved to another library the charter names under `libraries`, retire into the document there: `--to <library>:<id>`. Only a genre whose card lists `retired` can be retired. A record that was wrong stays at its address under its own states instead: a result is superseded or retracted through write.
6. **Maps.**
   - A new map: create it through write. Rows go in with `folio map add <map> <doc> --section "<heading>" [--reason ".."] [--after <doc>]`, in the order a newcomer reads them. A page that already has its place elsewhere moves with `folio map move`; it does not get a second row.
   - Move a row to another heading or map: `folio map move <doc> --to <map>#<heading>`. The row keeps its reason, a heading that does not exist is made at the end of the map, and the page itself does not change. `--from <map>` names the row's map when several list the page.
   - Merge two maps: move the other map's rows to the one you keep with `folio map move`, then `folio rm <other> --to <kept>`.
   - Split a map: create the new map through write, then move the rows that go with `folio map move <doc> --to <new map>#<heading>`.
   - Home maps change only through the configure skill.
7. **Rebalance the maps**, after the write skill adds pages (it runs this pass on the maps it touched), when `folio check` warns `heading-size`, or when asked:
   1. For each map, read its headings and their rows (`folio maps`, the map page).
   2. Look for: a heading past about 12 rows, or too mixed to name in a few words (split it); an empty heading (remove it); an existing page that now fits another heading, or a new one, better; a heading that has grown into a topic of its own (a new map, which configure puts on the home page).
   3. Placing a new page needs no approval. Every change to an existing page, heading or map is a proposal: one short table (page, from, to, why), and wait for the owner's yes. New pages land meanwhile.
   4. Apply what the owner approved: `folio map move <doc> --to <map>#<heading>` for each row, a heading renamed through write on the map page.
   5. If the owner does not answer in the session, leave the table as a question on the map page so it shows on the Review page: `folio annotations add <map> --kind question --label "rebalance" --body "<the table>" --author agent:<name>`.
8. **Tags:** `folio tags` lists them. Merge spellings that look alike with `folio tags rename <old> <new>`. A tag on one document earns a second or goes.
9. **Pack fixes:** after a pack is switched on, `folio check` names what its rules flag. Propose one fix per document, and apply each the owner approves through this skill or write.
10. **Health pass**, when asked or after a large change:
   1. `folio check` passes.
   2. Orphans: `folio maps` lists documents on no map. Add each to a map, or link it from one.
   3. Places: `folio check` names each placed page on no home map, on two, or outside every heading (check `placement`), and each source that is a row. Propose one place for each in a table and apply it with `folio map move` and `folio map rm` once approved. Headings past 12 rows get the rebalance pass (step 7).
   4. Thin documents: fold them into the document they belong to.
   5. Duplicates: `folio search` for each key term. Two homes for one fact become one.
   6. Stale maps: a map whose opening take predates most of its rows gets a revision through write.
   7. Drafts left for weeks: finish them through write, or propose retiring them.
   8. Open comments: `folio annotations list`. Hand them to the address skill. Under `save.review: after`, `folio review list` shows the pages waiting for the owner's review: report how many, never mark them reviewed.
   9. Report what you found, what you changed, and what is left for the owner.
11. **Audit against the cards**, when asked or after folio is upgraded:
   1. If folio was upgraded, refresh the library's skills first: `folio skills update`, then commit `.agents/skills/`.
   2. Take one map at a time (`folio maps`): its rows, and the concepts they link.
   3. Read each document in full, with its card (`folio genre <name>`) and `craft/layout.md`. Ask the five questions of the write skill's rule 24, and the card's `## Earns its page`. For a definition document, also ask whether its term is the field's name, or the library's own framing presented as one; the card says what follows.
   4. Give each document one verdict: keep; revise (the words); redesign (the form); promote to another genre; merge into a named document; retire. Add one line on why, and whether you would write it today, and in what form.
   5. Report to the owner: a table per map with every verdict, then what repeats across documents. Change nothing yet.
   6. Apply what the owner approves, in batches, least risk first: fixes that change no meaning, then merges and retirements (steps 3 to 5), then revisions and redesigns through write. Each batch ends with the gate and a commit, and each merge or retirement is recorded (step 12).
12. **Record it.** `folio journal add --title "<change>" --description "<one line: what moved and why>" --body "<old names and new>" --kind decision --about <id>,..`.
13. **Run the gate.** `folio index`, then `folio check`.
14. **Save.** `folio mv`, `folio promote` and `folio rm` stage every file they moved or changed, annotation files included; `folio save -m "<what moved>"` records them with the journal entry and `.folio/` (which holds the redirects). If it lists files it left alone (the charter, genres, code), those are a change to the library, not content: make them the way the repository takes changes. Where the repository takes every change by pull request, or has no upstream, use `folio save --no-push` on your branch.

## Stops

- A retirement or merge would remove the owner's own writing. Ask first.
- A move would change a top-level map. Hand it to configure.
- A rebalance would move or rename an existing page, heading or map, and the owner has not said yes. Propose it and wait; leave it as a question on the map when the session ends.
- Two documents look like duplicates but disagree on a fact. Show both and ask which holds.
- A document has an open question you cannot answer. Leave it in place and report it.

## Done when

- Every moved, promoted or retired document keeps its id, comments and dates, and its old address redirects.
- Every document except a journal entry is on a map, or linked from one that is, and every placed document has its one place.
- Every row links a document that exists, and every top-level map is reachable from home.
- The journal records each reorganisation.
- `folio check` passes, and the change is saved with `folio save`.

## Commands

- `folio maps` lists the maps, their rows, and documents on none.
- `folio map add <map> <doc> --section ".." [--reason ".."] [--after <doc>|<heading>]` adds a map row (`--after <heading>` with a new `--section` puts the heading after that one); `folio map rm <map> <doc>` removes one.
- `folio map move <doc> --to <map>[#<heading>] [--from <map>]` moves a row in one step.
- `folio review list` shows the pages waiting for the owner's review.
- `folio annotations add <map> --kind question --body ".." --author <who>` leaves an unanswered proposal on the map.
- `folio mv <doc> <to>` moves a document and rewrites its links.
- `folio promote <doc> <genre>` changes a document's genre.
- `folio rm <doc> --to <doc>` retires a document into another, and names the links whose text to review.
- `folio tags [rename <old> <new>]` lists or renames tags.
- `folio search <words>` finds duplicates.
- `folio annotations list` shows open comments.
- `folio journal add --title ".." --description ".." --body ".." --kind decision --about <id>,..` records the change.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
- `folio skills update` refreshes the library's copy of the skills after folio is upgraded.
