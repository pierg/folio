"""`folio journal` (listing) and `folio cite`."""

from __future__ import annotations

from typing import Any

from .. import indexer
from .. import library as library_mod
from .. import links as links_mod
from ..edits import find_doc
from ..errors import FolioError
from ..library import Library
from ..util import html_text, parse_date


def journal(lib: Library, *, kind: str | None = None, about: str | None = None,
            tag: str | None = None, since: str | None = None) -> list[dict[str, Any]]:
    since_date = None
    if since is not None:
        since_date = parse_date(since)
        if since_date is None:
            raise FolioError(f"--since must be YYYY-MM-DD, not `{since}`")
    out = []
    for entry in indexer.journal(lib):
        if kind is not None and entry["kind"] != kind:
            continue
        if about is not None and about.casefold() not in [a.casefold() for a in entry["about"]]:
            continue
        if tag is not None and tag not in entry["tags"]:
            continue
        if since_date is not None:
            when = parse_date(entry["date"])
            if when is None or when < since_date:
                continue
        out.append(entry)
    return out


def cite(lib: Library, ref: str) -> list[dict[str, Any]]:
    """How to cite a document, named by id or by path: one form per format, the same every time.

    `<library>:<id>` names a document in another library the charter names (model §4):
    its markup is a link into that library, and a paper cannot cite it.
    """
    name, sep, ident = ref.partition(":")
    if sep and name in lib.charter.libraries:
        root = links_mod.library_root(lib, name)
        if root is None:
            raise FolioError(f"library `{name}` is not at `{lib.charter.libraries[name].path}`")
        doc = find_doc(library_mod.load_at(root), ident)
        href = f"{name}:" + ("/" + doc.key if doc.key.endswith(".md") else doc.url)
        title = html_text(doc.title or doc.id)
        return [{
            "id": f"{name}:{doc.id}", "library": name, "genre": doc.genre_name, "path": doc.key,
            "url": doc.url, "title": doc.title, "description": doc.description, "status": doc.status,
            "markup": {"html": f'<a href="{href}">{title}</a>', "markdown": f"[{doc.title or doc.id}]({href})",
                       "latex": None},
        }]
    doc = find_doc(lib, ref)
    # An HTML page links a Markdown record by its source path (model §4).
    href = "/" + doc.key if doc.key.endswith(".md") else doc.url
    cls = ' class="defn-link"' if doc.is_a("concept") else ""
    title = html_text(doc.title or doc.id)
    return [{
        "id": doc.id, "genre": doc.genre_name, "path": doc.key, "url": doc.url,
        "title": doc.title, "description": doc.description, "status": doc.status,
        "markup": {"html": f'<a{cls} href="{href}">{title}</a>', "markdown": f"`{doc.id}`",
                   "latex": f"\\fcite{{{doc.id}}}"},
    }]
