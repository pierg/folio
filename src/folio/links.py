"""Links and citations: where each one points, resolved the way the exported site serves it."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from . import redirects
from .documents import DocFile, Document
from .html import Element, Node, elements_in
from .util import has_placeholder

if TYPE_CHECKING:
    from .library import Library

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_FCITE_RE = re.compile(r"\\fcite\{([^}]*)\}")
RECORD_ID_RE = re.compile(r"^([A-Za-z]+)-([0-9]+)$")


@dataclass(eq=False)
class Link:
    file: DocFile
    kind: str  # "href" | "code" | "fcite" | "field"
    raw: str
    resolved: bool
    target: str | None = None  # the file an href lands on, from the library root
    docs: list[Document] = field(default_factory=list)
    defn: bool = False  # an href with class="defn-link"
    field: str | None = None
    element: Element | None = None

    def cites(self, doc: Document) -> bool:
        return doc in self.docs


def is_external(href: str) -> bool:
    return bool(_SCHEME_RE.match(href)) or href.startswith("//")


def resolve_href(library: Path, from_path: str, href: str) -> str | None:
    """The file an href lands on, from the library root, or None when nothing is there.

    A folder serves its `index.html`, and a Markdown record is served at its
    path with `.html`, so `/content/results/R-1.html` lands on `R-1.md`.
    """
    clean = unquote(href.split("#", 1)[0].split("?", 1)[0])
    if not clean:
        return from_path
    if clean.startswith("/"):
        target = library / clean.lstrip("/")
    else:
        target = (library / from_path).parent / clean
    target = Path(os.path.normpath(target))
    candidates: list[Path] = []
    if clean.endswith("/") or target.is_dir():
        candidates.append(target / "index.html")
    else:
        candidates.append(target)
        if target.suffix == ".html":
            candidates.append(target.with_suffix(".md"))
    for candidate in candidates:
        if candidate.is_file():
            return Path(os.path.relpath(candidate, library)).as_posix()
    # An old address of a moved document serves a redirect (`.folio/redirects.json`).
    olds = [Path(os.path.relpath(c, library)).as_posix() for c in candidates]
    if not target.suffix and not clean.endswith("/"):
        olds.append(Path(os.path.relpath(target / "index.html", library)).as_posix())
    for old in olds:
        moved = redirects.target(library, old)
        if moved is not None and (library / moved).is_file():
            return moved
    return None


def _href_links(lib: "Library", df: DocFile, nodes: list[Node]) -> list[Link]:
    out = []
    for el in elements_in(nodes):
        if el.tag != "a" or not el.has("href") or el.has("data-unchecked"):
            continue
        href = (el.get("href") or "").strip()
        if not href or href.startswith("#") or is_external(href) or "{{" in href:
            continue
        target = resolve_href(lib.root, df.path, href)
        docs = []
        if target is not None and target in lib.by_path:
            owner = lib.by_path[target].doc
            if owner is not None:
                docs = [owner]
        out.append(Link(df, "href", href, target is not None, target, docs,
                        defn="defn-link" in el.classes, element=el))
    return out


def _code_links(lib: "Library", df: DocFile, nodes: list[Node]) -> list[Link]:
    """An id in backticks cites the document it names; one shaped like a record id must resolve."""
    out = []
    for el in elements_in(nodes):
        if el.tag != "code" or el.inside("pre"):
            continue
        text = el.text().strip()
        if text in lib.by_id:
            out.append(Link(df, "code", text, True, docs=list(lib.by_id[text]), element=el))
            continue
        match = RECORD_ID_RE.match(text)
        if match and match.group(1) in lib.prefixes:
            out.append(Link(df, "code", text, False, element=el))
    return out


def links_in(lib: "Library", df: DocFile, nodes: list[Node]) -> list[Link]:
    """The links and citations inside some nodes of a page or a Markdown body."""
    out = _href_links(lib, df, nodes)
    if df.format == "markdown":
        out.extend(_code_links(lib, df, nodes))
    return out


def fcites(lib: "Library", df: DocFile, latex: str) -> list[Link]:
    out = []
    for match in _FCITE_RE.finditer(latex):
        for raw in match.group(1).split(","):
            ident = raw.strip()
            if not ident or "{{" in ident:
                continue
            docs = list(lib.by_id.get(ident, []))
            out.append(Link(df, "fcite", ident, bool(docs), docs=docs))
    return out


def field_links(lib: "Library", doc: Document) -> list[Link]:
    """A field of type `id` or `ids` is a citation of the documents it names."""
    mf = doc.meta_file
    if mf is None or doc.genre is None:
        return []
    out = []
    for spec in doc.genre.fields:
        if spec.type not in ("id", "ids"):
            continue
        value = mf.meta.get(spec.name)
        if value is None or has_placeholder(value):
            continue
        values = value if isinstance(value, list) else (
            [value] if spec.type == "id" else [v.strip() for v in str(value).split(",")]
        )
        for raw in values:
            ident = str(raw).strip()
            if not ident:
                continue
            docs = list(lib.by_id.get(ident, []))
            if spec.genre:
                fitting = [d for d in docs if d.is_a(spec.genre)]
                docs = fitting or docs
            out.append(Link(mf, "field", ident, bool(docs), docs=docs, field=spec.name))
    return out


def file_links(lib: "Library", df: DocFile) -> list[Link]:
    if df.latex is not None:
        return fcites(lib, df, df.latex)
    if df.body is None:
        return []
    return links_in(lib, df, [df.body])
