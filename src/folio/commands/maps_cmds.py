"""`folio maps` and `folio map add|reason|rm`: the rows of a map, each linking one document."""

from __future__ import annotations

import html as _html
import re
from typing import Any

from ..checks import gate
from ..documents import Document
from ..edits import Plan, find_doc, href_for
from ..errors import FolioError
from ..library import Library
from ..links import resolve_href
from ..util import html_attr, html_text, slugify

_ROWS_RE = re.compile(r"(<ul\b[^>]*\bclass=\"[^\"]*\brows\b[^\"]*\"[^>]*>)(.*?)(</ul>)", re.S)
_ROW_RE = re.compile(r"([ \t]*)<li\b.*?</li>[ \t]*\n?", re.S)
_HREF_RE = re.compile(r"\bhref\s*=\s*[\"']([^\"']*)[\"']")
_WHY_RE = re.compile(r"\s*<span\b[^>]*\bclass=\"[^\"]*\bwhy\b[^\"]*\"[^>]*>.*?</span>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _map(lib: Library, ref: str) -> Document:
    doc = find_doc(lib, ref, "map")
    if not doc.is_a("map"):
        raise FolioError(f"{doc.key} is a `{doc.genre_name}`, not a map")
    return doc


def _rows(lib: Library, m: Document, text: str) -> list[dict[str, Any]]:
    """Every row of a map's source: its span in the text, its href, target and reason."""
    out = []
    for block in _ROWS_RE.finditer(text):
        base = block.start(2)
        for row in _ROW_RE.finditer(block.group(2)):
            h = _HREF_RE.search(row.group(0))
            href = _html.unescape(h.group(1)) if h else None
            target = resolve_href(lib.root, m.key, href) if href else None
            owner = lib.by_path[target].doc if target in lib.by_path else None
            why = _WHY_RE.search(row.group(0))
            reason = " ".join(_html.unescape(_TAG_RE.sub("", why.group(0))).split()) if why else None
            out.append({"start": base + row.start(), "end": base + row.end(), "href": href,
                        "doc": owner, "reason": reason, "text": row.group(0)})
    return out


def listing(lib: Library) -> dict[str, Any]:
    """Each map with its rows, and the documents no map lists."""
    maps = [d for d in lib.documents if d.is_a("map")]
    top = lib.charter.home_maps
    listed: set[Document] = set()
    out_maps = []
    for m in sorted(maps, key=lambda d: (not d.is_home, d.id not in top,
                                         top.index(d.id) if d.id in top else 0, d.id)):
        rows = []
        for row in _rows(lib, m, m.main.text if m.main else ""):
            target: Document | None = row["doc"]
            if target is not None:
                listed.add(target)
            rows.append({"id": target.id if target else None, "path": target.key if target else None,
                         "href": row["href"], "title": target.title if target else None,
                         "reason": row["reason"]})
        out_maps.append({"id": m.id, "path": m.key, "title": m.title, "status": m.status,
                         "top_level": m.id in top, "home": m.is_home, "rows": rows})
    listed.update(d for d in maps if d.id in top)
    orphans = {path for path, _ in gate.orphan(lib)}
    unmapped = [{"id": d.id, "path": d.key, "genre": d.genre_name, "title": d.title,
                 "orphan": d.key in orphans}
                for d in lib.documents
                if d not in listed and not d.is_home and not d.is_a("journal") and d.status != "retired"]
    return {"maps": out_maps, "unmapped": unmapped}


def _row(doc: Document, reason: str | None) -> str:
    link = f'<a href="{html_attr(href_for(doc))}">{html_text(doc.title or doc.id)}</a>'
    why = f' <span class="why">{html_text(reason)}</span>' if reason else ""
    return f"<li>{link}{why}</li>"


def _find_row(lib: Library, m: Document, doc: Document, text: str) -> dict[str, Any] | None:
    return next((r for r in _rows(lib, m, text) if r["doc"] is doc), None)


_HEADING_RE = re.compile(r"<h([23])\b([^>]*)>(.*?)</h\1>", re.S)
_ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']*)[\"']")


def _groups(text: str) -> list[dict[str, Any]]:
    """Each heading of a map with the span up to the next heading of any level."""
    found = list(_HEADING_RE.finditer(text))
    end_main = text.rfind("</main>")
    out = []
    for i, h in enumerate(found):
        stop = found[i + 1].start() if i + 1 < len(found) else (end_main if end_main > h.end() else len(text))
        ident = _ID_RE.search(h.group(2))
        out.append({"title": " ".join(_html.unescape(_TAG_RE.sub("", h.group(3))).split()),
                    "id": ident.group(1) if ident else "", "start": h.start(), "end": h.end(), "stop": stop})
    return out


def _find_group(text: str, name: str) -> dict[str, Any] | None:
    """The group whose heading reads `name` (case does not matter) or has it as its id."""
    want = name.strip().lower()
    return next((g for g in _groups(text) if g["title"].lower() == want or g["id"] == name.strip()), None)


def _new_group(group: str, row: str) -> str:
    return f'<h2 id="{slugify(group)}">{html_text(group.strip())}</h2>\n<ul class="rows">\n{row}\n</ul>\n'


_SLOT = "\x00slot\x00"


def _drop_placeholder(text: str) -> str:
    """A fresh map's skeleton group, rows all placeholders, replaced by a slot mark; else the text as it is."""
    for block in _ROWS_RE.finditer(text):
        rows = list(_ROW_RE.finditer(block.group(2)))
        if not rows or not all("{{" in r.group(0) for r in rows):
            continue
        start, end = block.start(), block.end()
        owner = next((g for g in _groups(text) if g["end"] <= start < g["stop"]), None)
        if owner is not None and "{{" in text[owner["start"]:owner["end"]] \
                and not text[owner["end"]:start].strip():
            start = owner["start"]
        if text[end:end + 1] == "\n":
            end += 1
        return text[:start] + _SLOT + text[end:]
    return text


def _insert_in_group(text: str, group: str, row: str, where: str) -> str:
    match = _find_group(text, group)
    if match is None:
        anchor = text.rfind("</main>")
        if anchor < 0:
            anchor = text.rfind("</body>")
        if anchor < 0:
            raise FolioError(f"{where}: has no </main> or </body> to put a new group in")
        return text[:anchor] + _new_group(group, row) + text[anchor:]
    block = next((b for b in _ROWS_RE.finditer(text) if match["end"] <= b.start() < match["stop"]), None)
    if block is None:
        at = match["end"]
        return text[:at] + f'\n<ul class="rows">\n{row}\n</ul>' + text[at:]
    end = block.start(3)
    lead = "" if text[:end].endswith("\n") else "\n"
    return text[:end] + lead + row + "\n" + text[end:]


def add(lib: Library, map_ref: str, doc_ref: str, reason: str | None, group: str | None = None,
        after: str | None = None) -> list[str]:
    """Add a row: at the end of the last group, at the end of `group` (made at the end of the map
    when missing), or after a row. `after` may name a group heading instead, to put a new `group`
    right after that group. The first row on a fresh map takes the place of the skeleton's
    placeholder group.

    The row's link text is the document's title, a fallback for reading without the shell: the
    shell draws every row's text from the catalog.
    """
    m, doc = _map(lib, map_ref), find_doc(lib, doc_ref)
    if doc is m:
        raise FolioError("a map does not list itself")
    plan = Plan(lib)
    original = plan.text(m.key)
    if _find_row(lib, m, doc, original) is not None:
        raise FolioError(f"{m.id} already lists {doc.id}; `folio map reason` changes its reason")
    row = _row(doc, reason)
    text = _drop_placeholder(original)
    fresh = _SLOT in text
    if fresh and after is None and (group is None or _find_group(text, group) is None):
        text = text.replace(_SLOT, _new_group(group, row) if group else f'<ul class="rows">\n{row}\n</ul>\n')
    else:
        text = text.replace(_SLOT, "")
        text = _place(lib, m, text, row, group, after)
    where = f" after {after}" if after else (f" in `{group}`" if group else "")
    plan.write(m.key, text, f"row added for {doc.id}{where}" + (f" ({reason})" if reason else ""))
    return plan.apply()


def _place(lib: Library, m: Document, text: str, row: str, group: str | None, after: str | None) -> str:
    if after is not None:
        try:
            prev = _find_row(lib, m, find_doc(lib, after), text)
        except FolioError:
            prev = None
        heading = _find_group(text, after) if prev is None else None
        if heading is not None:
            if group is None:
                raise FolioError(f"--after `{after}` names a group; give --group <new heading> to put a "
                                 "new group after it, or name a document to put the row after its row")
            if _find_group(text, group) is not None:
                raise FolioError(f"{m.id} already has the group `{group}`; --after <group> places only a "
                                 "new group")
            at = heading["stop"]
            lead = "" if text[:at].endswith("\n") else "\n"
            gap = "\n" if text[at:].startswith("<h") else ""
            return text[:at] + lead + _new_group(group, row) + gap + text[at:]
        if prev is None:
            raise FolioError(f"{m.id} has no row for `{after}` and no group of that name to put the new "
                             "row after")
        if group is not None:
            g = _find_group(text, group)
            if g is None or not g["end"] <= prev["start"] < g["stop"]:
                raise FolioError(f"the row for {after} is not in the group `{group}`")
        indent = re.match(r"[ \t]*", prev["text"]).group(0)  # type: ignore[union-attr]
        tail = "" if prev["text"].endswith("\n") else "\n"
        return text[: prev["end"]] + tail + indent + row + ("\n" if tail == "" else "") + text[prev["end"]:]
    if group is not None:
        return _insert_in_group(text, group, row, m.key)
    blocks = list(_ROWS_RE.finditer(text))
    if blocks:
        end = blocks[-1].start(3)
        lead = "" if text[:end].endswith("\n") else "\n"
        return text[:end] + lead + row + "\n" + text[end:]
    anchor = text.rfind("</main>")
    if anchor < 0:
        anchor = text.rfind("</body>")
    if anchor < 0:
        raise FolioError(f"{m.key}: has no </main> or </body> to put a list of rows in")
    return text[:anchor] + f'<ul class="rows">\n{row}\n</ul>\n' + text[anchor:]


def reason(lib: Library, map_ref: str, doc_ref: str, why: str) -> list[str]:
    m, doc = _map(lib, map_ref), find_doc(lib, doc_ref)
    plan = Plan(lib)
    text = plan.text(m.key)
    row = _find_row(lib, m, doc, text)
    if row is None:
        raise FolioError(f"{m.id} has no row for {doc.id}; `folio map add` adds one")
    old = row["text"]
    stripped = _WHY_RE.sub("", old)
    new_why = f' <span class="why">{html_text(why)}</span>' if why.strip() else ""
    new = re.sub(r"(</a>)", lambda mm: mm.group(1) + new_why, stripped, count=1)
    text = text[: row["start"]] + new + text[row["end"]:]
    what = f"reason for {doc.id}: {why}" if why.strip() else f"reason for {doc.id} removed"
    plan.write(m.key, text, what)
    return plan.apply()


def remove(lib: Library, map_ref: str, doc_ref: str) -> list[str]:
    m, doc = _map(lib, map_ref), find_doc(lib, doc_ref)
    plan = Plan(lib)
    text = plan.text(m.key)
    row = _find_row(lib, m, doc, text)
    if row is None:
        raise FolioError(f"{m.id} has no row for {doc.id}")
    text = text[: row["start"]] + text[row["end"]:]
    plan.write(m.key, text, f"row for {doc.id} removed")
    out = plan.apply()
    others = [mm for mm in lib.documents if mm.is_a("map") and mm is not m
              and _find_row(lib, mm, doc, mm.main.text if mm.main else "") is not None]
    if not others and doc.genre is not None and doc.genre.on_map == "required":
        out.append(f"note: {doc.id} is now on no map; `folio check` will say so until a map lists it")
    return out
