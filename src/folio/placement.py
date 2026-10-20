"""One place per document (model §5): which home map row, under which heading, holds each document.

A document whose card says `on_map: placed` has exactly one place: one row on one of the
charter's home maps, under a heading of that map. The place is read from the maps, never
from the document. A document whose card says `on_map: cited` (a source) is never a row: it
belongs to every home map whose rows cite it. The gate (`placement`, `heading-size`), the
indices (`place`, `used_by`) and `folio map` all read the maps through this module, so they
agree.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass

from .documents import Document
from .library import Library

HEADING_ROWS = 12  # past this many rows, a heading asks for a split (check `heading-size`)

_HEADING_RE = re.compile(r"<h([1-6])\b([^>]*)>(.*?)</h\1\s*>", re.S | re.I)
_ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']*)[\"']")
_TAG_RE = re.compile(r"<[^>]+>")


def slug(text: str) -> str:
    """A heading's anchor from its text, as the shell names a heading that has no id."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


@dataclass(frozen=True)
class Heading:
    title: str
    anchor: str
    start: int


@dataclass(frozen=True)
class Row:
    """One row of a map: the document it lists, and the heading nearest above it (None: under none)."""

    map: Document
    doc: Document
    heading: Heading | None


def headings(text: str) -> list[Heading]:
    """A map source's headings, in order, each with its anchor: its id, else its text as a slug."""
    out = []
    for m in _HEADING_RE.finditer(text):
        title = " ".join(_html.unescape(_TAG_RE.sub("", m.group(3))).split())
        ident = _ID_RE.search(m.group(2))
        anchor = ident.group(1).strip() if ident and ident.group(1).strip() else slug(title)
        out.append(Heading(title, anchor, m.start()))
    return out


def rows_in(lib: Library, m: Document, text: str | None = None) -> list[Row]:
    """Every row of a map that lists a document, in order, with its heading. Rows above the
    first heading, or under a heading with no text, are under none."""
    from .commands.maps_cmds import _rows

    if text is None:
        text = m.main.text if m.main else ""
    heads = headings(text)
    out = []
    for row in _rows(lib, m, text):
        target = row["doc"]
        if target is None or target is m:
            continue
        above = [h for h in heads if h.start < row["start"]]
        heading = above[-1] if above and above[-1].title else None
        out.append(Row(m, target, heading))
    return out


def home_maps(lib: Library) -> list[Document]:
    """The charter's home maps, in its order."""
    out: list[Document] = []
    for name in lib.charter.home_maps:
        out.extend(d for d in lib.find(name, "map") if d not in out)
    return out


def all_rows(lib: Library) -> dict[Document, list[Row]]:
    """Every map's rows, by map, read once per loaded library."""
    cached = lib.cache.get("placement.rows")
    if cached is None:
        cached = {d: rows_in(lib, d) for d in lib.documents if d.is_a("map")}
        lib.cache["placement.rows"] = cached
    return cached


def home_rows(lib: Library) -> dict[Document, list[Row]]:
    """Each document's rows on the home maps: its places, one when it is placed well."""
    out: dict[Document, list[Row]] = {}
    rows = all_rows(lib)
    for m in home_maps(lib):
        for row in rows.get(m, []):
            out.setdefault(row.doc, []).append(row)
    return out


def on_map(doc: Document) -> str | None:
    return doc.genre.on_map if doc.genre is not None else None


def is_placed(doc: Document) -> bool:
    return on_map(doc) == "placed" and not doc.is_home


def is_cited(doc: Document) -> bool:
    return on_map(doc) == "cited"


def place(lib: Library, doc: Document) -> dict[str, str | None] | None:
    """A placed document's place, `{map, section, anchor}`; None while it has no single place."""
    found = home_rows(lib).get(doc, [])
    if len(found) != 1:
        return None
    row = found[0]
    return {"map": row.map.id, "section": row.heading.title if row.heading else None,
            "anchor": row.heading.anchor if row.heading else None}


def used_by(lib: Library) -> dict[Document, list[str]]:
    """Each cited document's home maps, in the charter's order: those that link it, or whose rows cite it."""
    out: dict[Document, list[str]] = {}
    rows = all_rows(lib)
    for m in home_maps(lib):
        readers = [m] + [r.doc for r in rows.get(m, [])]
        for reader in readers:
            for link in lib.doc_links(reader):
                for target in link.docs:
                    if is_cited(target) and target is not reader:
                        ids = out.setdefault(target, [])
                        if m.id not in ids:
                            ids.append(m.id)
    return out
