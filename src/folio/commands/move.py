"""`folio mv`, `folio promote` and `folio rm --to`: a document changes place, keeping its graph.

Every link to the document is rewritten to its new address, its annotation
sidecars and the files beside it travel with it, its id stays (a renamed
slug-id document writes its old id into its metadata), git keeps its dates
(`git mv` inside a work tree), and the old address is redirected
(`.folio/redirects.json`). A permanent or frozen document that links the old
address is left as it is: the redirect serves it.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from .. import library as library_mod
from .. import history, paths, redirects
from .. import links as links_mod
from ..checks import gate
from ..documents import HOME_PATH, Document
from ..edits import Plan, find_doc, locked, new_href, replace_href, set_front
from ..errors import FolioError
from ..genres import Genre
from ..html import Element
from ..library import Library
from ..metaedit import set_meta
from ..util import is_slug
from .maps_cmds import _HREF_RE, _ROW_RE, _ROWS_RE

SIDECAR = ".annotations.json"


def sidecar(path: str) -> str:
    """The annotation sidecar beside a document file: `<stem>.annotations.json`."""
    p = PurePosixPath(path)
    return str(p.with_name(p.stem + SIDECAR))


def _template(genre: Genre, part: str | None) -> str:
    return genre.path if part is None else genre.parts[part].path


def _is_folder_doc(path: str) -> bool:
    return path.endswith("/index.html")


def _refuse_fixed(doc: Document, verb: str) -> None:
    if doc.is_home:
        raise FolioError(f"the home page stays at {HOME_PATH}; it cannot be {verb}")
    if doc.genre is None or doc.misplaced:
        raise FolioError(f"{doc.key} is not where its genre puts it; fix it before it is {verb}")
    why = locked(doc)
    if why is not None:
        raise FolioError(f"{doc.key} is {why}; it is never {verb}")


def _file_moves(lib: Library, doc: Document, genre: Genre, values: dict[str, str]) -> dict[str, str]:
    """Each of the document's files, its sidecars and the files kept beside it, old path to new."""
    moves: dict[str, str] = {}
    for df in doc.files:
        captures = {**df.captures, **values}
        new = paths.fill(_template(genre, df.part), captures)
        left = paths.placeholders(new)
        if left:
            raise FolioError(f"cannot place {df.path} as a `{genre.name}`: nothing fills "
                             + ", ".join("{" + p + "}" for p in left))
        moves[df.path] = new
    old_main, new_main = doc.key, moves[doc.key]
    for old, new in list(moves.items()):
        if (lib.root / sidecar(old)).is_file():
            moves[sidecar(old)] = sidecar(new)
    if _is_folder_doc(old_main):
        folder = PurePosixPath(old_main).parent
        extra = sorted(str(PurePosixPath(p.relative_to(lib.root).as_posix()))
                       for p in (lib.root / str(folder)).rglob("*") if p.is_file())
        extra = [e for e in extra if e not in moves]
        if extra and not _is_folder_doc(new_main):
            raise FolioError(f"{folder}/ holds files a single-file `{genre.name}` cannot keep beside it: "
                             + ", ".join(extra))
        new_folder = PurePosixPath(new_main).parent
        for e in extra:
            moves[e] = str(new_folder / PurePosixPath(e).relative_to(folder))
    for old, new in moves.items():
        if old != new and (lib.root / new).exists() and new not in moves:
            raise FolioError(f"{new} already exists")
    return {o: n for o, n in moves.items() if o != n}


def _rewrite_links(lib: Library, plan: Plan, doc: Document, mapping: dict[str, str],
                   new_from: dict[str, str]) -> None:
    """Point every link to the document's files at their new paths, and rebase its own relative links."""
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        own = owner is doc
        edits: dict[str, str] = {}
        for link in links:
            if link.kind != "href" or link.target is None:
                continue
            moved = link.target in mapping
            if not moved and not (own and not link.raw.startswith("/")):
                continue
            target = mapping.get(link.target, link.target)
            here = new_from.get(path, path)
            new = new_href(link.raw, here, target)
            if new != link.raw:
                edits[link.raw] = new
        if not edits:
            continue
        if owner is not None and not own and locked(owner):
            plan.notes.append(f"left {path} ({locked(owner)}): its links to the old address follow the redirect")
            continue
        here = new_from.get(path, path)
        text = plan.text(here)
        for raw, new in edits.items():
            text = replace_href(text, raw, new, path)
        plan.write(here, text, "links to " + doc.id + " rewritten" if not own else "relative links rebased")


def committed(lib: Library, doc: Document) -> bool:
    """True when any of the document's files was ever committed, so its address may be known."""
    return history.in_git(lib) and bool(history.commits(lib, [f.path for f in doc.files]))


def _relocate(lib: Library, doc: Document, genre: Genre, values: dict[str, str], *,
              meta: dict[str, str], redirect: bool = True) -> list[str]:
    plan = Plan(lib, stage=True)
    file_moves = _file_moves(lib, doc, genre, values)
    if not file_moves:
        raise FolioError(f"{doc.key} is already there")
    doc_paths = {df.path for df in doc.files}
    mapping = {o: n for o, n in file_moves.items() if o in doc_paths}
    plan.moves.update(file_moves)
    _rewrite_links(lib, plan, doc, mapping, mapping)
    mf = doc.meta_file
    if mf is not None:
        here = mapping.get(mf.path, mf.path)
        text = plan.text(here)
        for key, value in meta.items():
            text = set_meta(text, mf.format, key, value) if mf.format == "html" else set_front(text, key, value)
        plan.write(here, text, ", ".join(f"{k}: {v}" for k, v in meta.items()))
    changes = plan.apply()
    return changes + _staged_note(plan) + redirects.add(lib.root, mapping, record=redirect)


def _staged_note(plan: Plan) -> list[str]:
    """What the plan staged in git, so the commit step only commits."""
    out = []
    if plan.staged:
        out.append(f"staged the rename of {len(plan.staged)} file{'s' if len(plan.staged) != 1 else ''}"
                   " in git (git mv)")
    if plan.added:
        out.append(f"staged {len(plan.added)} changed file{'s' if len(plan.added) != 1 else ''} in git"
                   " (git add)")
    if out:
        out[-1] += "; add the journal entry and .folio/, then commit"
    return out


def mv(lib: Library, ref: str, to: str) -> list[str]:
    doc = find_doc(lib, ref)
    _refuse_fixed(doc, "moved")
    genre = doc.genre
    assert genre is not None
    if genre.prefix is not None:
        raise FolioError(f"{doc.key} is a record; its path follows its id `{doc.id}` and never changes")
    if "/" in to or "." in to:
        captures = paths.match(genre.path, to.lstrip("/"))
        if captures is None:
            raise FolioError(f"`{to}` is not a `{genre.name}` path ({genre.path}); "
                             "`folio promote` changes a document's genre")
    else:
        if not is_slug(to):
            raise FolioError(f"a slug is lowercase words joined by hyphens, not `{to}`")
        captures = {"slug": to}
    meta: dict[str, str] = {}
    slug = captures.get("slug")
    known = committed(lib, doc) or "id" in doc.meta
    if not known:
        # Never committed, so nothing outside the working tree knows its address or id:
        # the new slug becomes its id and no redirect is kept.
        holder = next((d for d in lib.by_id.get(slug, []) if d is not doc), None) if slug else None
        if holder is not None:
            raise FolioError(f"the id `{slug}` is taken by {holder.key}")
        changes = _relocate(lib, doc, genre, captures, meta=meta, redirect=False)
        if slug is not None and slug != doc.id:
            changes.append(f"{doc.key} was never committed, so its id is now `{slug}` and no redirect is kept")
            for path, links in lib.links.items():
                if lib.by_path[path].doc is not doc and any(lk.kind != "href" and doc in lk.docs for lk in links):
                    changes.append(f"note: {path} cites `{doc.id}` by id; change it to `{slug}`")
        return changes
    if slug is not None and slug != doc.id:
        meta["id"] = doc.id  # the id never changes, even when the slug does
    return _relocate(lib, doc, genre, captures, meta=meta)


def promote(lib: Library, ref: str, genre_name: str) -> list[str]:
    doc = find_doc(lib, ref)
    _refuse_fixed(doc, "promoted")
    source = doc.genre
    assert source is not None
    target = lib.registry.get(genre_name)
    if target is source:
        raise FolioError(f"{doc.key} is already a `{genre_name}`")
    if not target.active:
        raise FolioError(f"genre `{genre_name}` is switched off")
    if source.format != "html" or target.format != "html":
        raise FolioError(f"promotion converts only between HTML genres: `{source.name}` is {source.format} "
                         f"and `{target.name}` is {target.format}; write the new document through the "
                         "write skill and retire this one with `folio rm --to`")
    if target.prefix is not None:
        raise FolioError(f"`{genre_name}` is a record genre with numbered ids; a promoted document keeps its id")
    if target.lives != "revised":
        raise FolioError(f"`{genre_name}` documents are {target.lives}; only a revised genre takes a promotion")
    if len(doc.files) > 1:
        raise FolioError(f"{doc.key} has parts; only a single-file document is promoted")
    if doc.status not in target.states and not (doc.status == "live" and "status" not in doc.meta):
        raise FolioError(f"status `{doc.status}` is not one of `{genre_name}`'s states: {', '.join(target.states)}")
    slug = doc.files[0].captures.get("slug") or PurePosixPath(doc.key).stem
    values = {**doc.files[0].captures, "slug": slug}
    changes = _relocate(lib, doc, target, values, meta={"genre": genre_name},
                        redirect=committed(lib, doc))
    return changes + [f"{doc.id} now has genre `{genre_name}`: `folio genre {genre_name}` gives its shape, "
                      "and `folio check` names what it still lacks"]


def dedupe_rows(text: str) -> tuple[str, int]:
    """Drop a row whose link repeats an earlier row's on the same map."""
    seen: set[str] = set()
    dropped = 0

    def block(m: re.Match[str]) -> str:
        nonlocal dropped

        def row(r: re.Match[str]) -> str:
            nonlocal dropped
            h = _HREF_RE.search(r.group(0))
            if h is None:
                return r.group(0)
            if h.group(1) in seen:
                dropped += 1
                return ""
            seen.add(h.group(1))
            return r.group(0)

        return m.group(1) + _ROW_RE.sub(row, m.group(2)) + m.group(3)

    return _ROWS_RE.sub(block, text), dropped


def _is_row_link(el: Element) -> bool:
    li = el.parent
    return (el.tag == "a" and li is not None and li.tag == "li" and li.parent is not None
            and li.parent.tag == "ul" and "rows" in li.parent.classes and li.first("a") is el)


def _stale_link_text(lib: Library, doc: Document, replacement: Document, mapping: dict[str, str]) -> list[str]:
    """Each link to the retired document whose text still names its title, to review by hand.

    A map row is left out: the shell draws its text from the catalog.
    """
    title = " ".join((doc.title or "").split()).casefold()
    if not title:
        return []
    out = []
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        if owner is doc or owner is None or locked(owner):
            continue
        for lk in links:
            if lk.kind != "href" or lk.target not in mapping or lk.element is None or _is_row_link(lk.element):
                continue
            text = " ".join(lk.element.text().split())
            if title in text.casefold():
                out.append(f"review: {path} links to {replacement.id} with the text \"{text}\", which names"
                           f" the retired {doc.id}; reword it if it no longer fits")
    return out


def _elsewhere(lib: Library, to: str) -> tuple[Document, str, str] | None:
    """A replacement in another library the charter names, `<library>:<id>` (model §4).

    Returns the document there, the redirect target (`<library>:<file>`) and the
    href a link takes to reach it; None when `to` names no other library.
    """
    name, sep, ident = to.partition(":")
    if not sep or name not in lib.charter.libraries:
        return None
    root = links_mod.library_root(lib, name)
    if root is None:
        raise FolioError(f"library `{name}` is not at `{lib.charter.libraries[name].path}`; "
                         "it must be there to retire a document into it")
    other = library_mod.load_at(root)
    found = find_doc(other, ident)
    if found.status == "retired":
        raise FolioError(f"{name}:{found.id} is retired itself; retire into what replaced it")
    landing = found.address_file.path
    href = "/" + found.key if found.key.endswith(".md") else found.url
    return found, f"{name}:{landing}", f"{name}:{href}"


def rm(lib: Library, ref: str, to: str) -> list[str]:
    doc = find_doc(lib, ref)
    _refuse_fixed(doc, "retired")
    elsewhere = _elsewhere(lib, to)
    if elsewhere is not None:
        return _rm_elsewhere(lib, doc, to.partition(":")[0], *elsewhere)
    replacement = find_doc(lib, to)
    genre = doc.genre
    assert genre is not None
    if replacement is doc:
        raise FolioError("a document is retired into another document, not into itself")
    if "retired" not in genre.states:
        raise FolioError(f"a `{genre.name}` is never retired: its states are {', '.join(genre.states)}")
    if doc.status == "retired":
        raise FolioError(f"{doc.key} is already retired")
    if replacement.status == "retired":
        raise FolioError(f"{replacement.key} is retired itself; retire into what replaced it")
    plan = Plan(lib, stage=True)
    landing = replacement.address_file.path
    mapping = {df.path: landing for df in doc.files}
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        if owner is doc or owner is None:
            continue
        edits = {lk.raw: new_href(lk.raw, path, landing) for lk in links
                 if lk.kind == "href" and lk.target in mapping}
        edits = {r: n for r, n in edits.items() if r != n}
        if not edits:
            continue
        if locked(owner):
            plan.notes.append(f"left {path} ({locked(owner)}): its links to {doc.id} follow the redirect")
            continue
        text = plan.text(path)
        for raw, new in edits.items():
            text = replace_href(text, raw, new, path)
        what = f"links to {doc.id} now go to {replacement.id}"
        if owner.is_a("map"):
            text, dropped = dedupe_rows(text)
            if dropped:
                what += f" ({dropped} duplicate row{'s' if dropped > 1 else ''} dropped)"
        plan.write(path, text, what)
    mf = doc.meta_file
    if mf is None:
        raise FolioError(f"{doc.key} holds no metadata to mark retired")
    text = plan.text(mf.path)
    for key, value in (("status", "retired"), ("replaced_by", replacement.id)):
        text = set_meta(text, mf.format, key, value) if mf.format == "html" else set_front(text, key, value)
    plan.write(mf.path, text, f"status: retired, replaced_by: {replacement.id}")
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        if owner is not doc and any(lk.kind != "href" and doc in lk.docs for lk in links):
            plan.notes.append(f"note: {path} still cites `{doc.id}` by id; it resolves to the retired document")
    plan.notes.extend(_stale_link_text(lib, doc, replacement, mapping))
    before = {path for path, _ in gate.orphan(lib)}
    changes = plan.apply() + _staged_note(plan) + redirects.add(lib.root, mapping)
    after = library_mod.load_at(lib.root)
    for path, _ in gate.orphan(after):
        if path not in before:
            changes.append(f"note: {path} was reachable only through {doc.id}; it is on no map now")
    return changes


def _rm_elsewhere(lib: Library, doc: Document, name: str, replacement: Document, landing: str,
                  href: str) -> list[str]:
    """Retire a document into one in another library: links go there, and so does the address."""
    genre = doc.genre
    assert genre is not None
    if "retired" not in genre.states:
        raise FolioError(f"a `{genre.name}` is never retired: its states are {', '.join(genre.states)}")
    if doc.status == "retired":
        raise FolioError(f"{doc.key} is already retired")
    label = f"{name}:{replacement.id}"
    plan = Plan(lib, stage=True)
    mapping = {df.path: landing for df in doc.files}
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        if owner is doc or owner is None:
            continue
        cut = lambda raw: min([i for i in (raw.find("#"), raw.find("?")) if i >= 0], default=len(raw))
        edits = {lk.raw: href + lk.raw[cut(lk.raw):] for lk in links
                 if lk.kind == "href" and lk.target in mapping}
        if not edits:
            continue
        if locked(owner):
            plan.notes.append(f"left {path} ({locked(owner)}): its links to {doc.id} follow the redirect")
            continue
        text = plan.text(path)
        what = f"links to {doc.id} now go to {label}"
        if owner.is_a("map"):
            # A map lists this library's documents: its row for the retired one goes.
            text, dropped = _drop_rows(text, set(edits))
            if dropped:
                what += f" ({dropped} row{'s' if dropped > 1 else ''} dropped)"
            edits = {raw: new for raw, new in edits.items() if _has_href(text, raw)}
        for raw, new in edits.items():
            text = _undefine(replace_href(text, raw, new, path), new)
        plan.write(path, text, what)
    mf = doc.meta_file
    if mf is None:
        raise FolioError(f"{doc.key} holds no metadata to mark retired")
    text = plan.text(mf.path)
    for key, value in (("status", "retired"), ("replaced_by", label)):
        text = set_meta(text, mf.format, key, value) if mf.format == "html" else set_front(text, key, value)
    plan.write(mf.path, text, f"status: retired, replaced_by: {label}")
    for path, links in lib.links.items():
        owner = lib.by_path[path].doc
        if owner is not doc and any(lk.kind != "href" and doc in lk.docs for lk in links):
            plan.notes.append(f"note: {path} still cites `{doc.id}` by id; it resolves to the retired document")
    plan.notes.extend(_stale_link_text(lib, doc, replacement, mapping))
    before = {path for path, _ in gate.orphan(lib)}
    changes = plan.apply() + _staged_note(plan) + redirects.add(lib.root, mapping)
    after = library_mod.load_at(lib.root)
    for path, _ in gate.orphan(after):
        if path not in before:
            changes.append(f"note: {path} was reachable only through {doc.id}; it is on no map now")
    return changes


def _drop_rows(text: str, hrefs: set[str]) -> tuple[str, int]:
    """A map's text without the rows that link one of `hrefs`, and how many went."""
    dropped = 0

    def block(m: re.Match[str]) -> str:
        nonlocal dropped

        def row(r: re.Match[str]) -> str:
            nonlocal dropped
            h = _HREF_RE.search(r.group(0))
            if h is not None and h.group(1) in hrefs:
                dropped += 1
                return ""
            return r.group(0)

        return m.group(1) + _ROW_RE.sub(row, m.group(2)) + m.group(3)

    return _ROWS_RE.sub(block, text), dropped


def _has_href(text: str, href: str) -> bool:
    return any(h.group(1) == href for h in _HREF_RE.finditer(text))


def _undefine(text: str, href: str) -> str:
    """Drop `defn-link` from the links to `href`: a link into another library has no hover definition."""
    tag_re = re.compile(r"<a\b[^>]*\bhref\s*=\s*[\"']" + re.escape(href) + r"[\"'][^>]*>")

    def fix(m: re.Match[str]) -> str:
        def classes(c: re.Match[str]) -> str:
            kept = " ".join(x for x in c.group(1).split() if x != "defn-link")
            return f' class="{kept}"' if kept else ""
        return re.sub(r'\s+class="([^"]*)"', classes, m.group(0))

    return tag_re.sub(fix, text)
