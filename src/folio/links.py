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
_LIBRARY_RE = re.compile(r"^([a-z][a-z0-9-]*):(.*)$", re.S)
_FCITE_RE = re.compile(r"\\fcite\{([^}]*)\}")
RECORD_ID_RE = re.compile(r"^([A-Za-z]+)-([0-9]+)$")


@dataclass(eq=False)
class Link:
    file: DocFile
    kind: str  # "href" | "code" | "fcite" | "field" | "library" (a link into another library, model §4)
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


def library_ref(lib: "Library", href: str) -> tuple[str, str] | None:
    """`(name, address)` when an href links into a library the charter names, else None."""
    match = _LIBRARY_RE.match(href)
    if match is None or match.group(1) not in lib.charter.libraries:
        return None
    return match.group(1), match.group(2)


def library_root(lib: "Library", name: str) -> Path | None:
    """Where a library the charter names is on this machine, or None when it is not there."""
    roots = lib.cache.setdefault("library_roots", {})
    if name not in roots:
        root = (lib.root / lib.charter.libraries[name].path).resolve()
        roots[name] = root if (root / "folio.yaml").is_file() else None
    return roots[name]


def resolve_library(lib: "Library", href: str) -> tuple[bool | None, str | None]:
    """Whether a link into another library lands on a file there, and which one.

    `(None, None)` when the library is not at its path, so the link cannot be checked.
    """
    ref = library_ref(lib, href)
    if ref is None:
        return False, None
    name, address = ref
    root = library_root(lib, name)
    if root is None:
        return None, None
    path = address.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return False, None
    found = resolve_href(root, "", path if path.startswith("/") else "/" + path)
    return (found is not None), found


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
        if moved is not None and (_LIBRARY_RE.match(moved) or (library / moved).is_file()):
            return moved  # a document retired into another library leads there (model §3)
    return None


def _href_links(lib: "Library", df: DocFile, nodes: list[Node]) -> list[Link]:
    out = []
    for el in elements_in(nodes):
        if el.tag != "a" or not el.has("href") or el.has("data-unchecked"):
            continue
        href = (el.get("href") or "").strip()
        if library_ref(lib, href) is not None:
            found, _ = resolve_library(lib, href)
            out.append(Link(df, "library", href, found is not False, href, [],
                            defn="defn-link" in el.classes, element=el))
            continue
        if not href or href.startswith("#") or is_external(href) or "{{" in href:
            continue
        target = resolve_href(lib.root, df.path, href)
        if target is not None and library_ref(lib, target) is not None:
            # An old address redirected into another library: checked there like a link into it.
            found, _ = resolve_library(lib, target)
            out.append(Link(df, "href", href, found is not False, target, [],
                            defn="defn-link" in el.classes, element=el))
            continue
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
