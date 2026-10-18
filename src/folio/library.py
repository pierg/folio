"""A loaded library: its charter, genres, documents and the graph of their links."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import charter as charter_mod
from . import genres as genres_mod
from . import packs as packs_mod
from .charter import Charter
from .checks.registry import card_check_names, check_names
from .documents import DocFile, Document, discover
from .errors import FolioError
from .genres import Registry
from .links import Link, field_links, file_links


class IdIndex(dict):  # type: ignore[type-arg]
    """Documents by id. Ids compare without regard to case: `r-12` finds `R-12`."""

    @staticmethod
    def _key(key: object) -> object:
        return key.casefold() if isinstance(key, str) else key

    def __getitem__(self, key: object) -> list[Document]:
        return super().__getitem__(self._key(key))

    def __setitem__(self, key: object, value: list[Document]) -> None:
        super().__setitem__(self._key(key), value)

    def __contains__(self, key: object) -> bool:
        return super().__contains__(self._key(key))

    def get(self, key: object, default: Any = None) -> Any:
        return super().get(self._key(key), default)

    def setdefault(self, key: object, default: Any = None) -> Any:
        return super().setdefault(self._key(key), default)


@dataclass
class Library:
    root: Path
    charter: Charter
    registry: Registry
    documents: list[Document]
    by_path: dict[str, DocFile] = field(default_factory=dict)
    by_id: dict[str, list[Document]] = field(default_factory=IdIndex)
    prefixes: set[str] = field(default_factory=set)
    links: dict[str, list[Link]] = field(default_factory=dict)  # by file path
    cache: dict[str, Any] = field(default_factory=dict)

    @property
    def files(self) -> list[DocFile]:
        return [f for d in self.documents for f in d.files]

    def doc_links(self, doc: Document) -> list[Link]:
        return [link for f in doc.files for link in self.links.get(f.path, [])]

    def journal_kinds(self) -> list[str]:
        """The kinds the journal accepts: the core's, every pack switched on, and the charter's."""
        kinds: list[str] = []
        journal = self.registry.genres.get("journal")
        if journal is not None:
            kinds.extend(journal.checks.get("kinds") or [])
        for pack in self.registry.packs.values():
            if pack.on:
                kinds.extend(pack.journal_kinds)
        kinds.extend(self.charter.journal_kinds)
        return list(dict.fromkeys(kinds))

    def find(self, ident: str, genre: str | None = None) -> list[Document]:
        docs = self.by_id.get(ident, [])
        if genre is not None:
            docs = [d for d in docs if d.is_a(genre)]
        return docs

    def assets_dir(self) -> Path:
        return self.root / self.charter.assets


def load(start: Path) -> Library:
    root = charter_mod.find_library(start)
    return load_at(root)


def load_or_shipped(start: Path) -> tuple[Library, bool]:
    """The library at or above `start`, or, outside any library, one that holds only what folio ships.

    The second value says whether a library was found. The shipped-only one
    has no documents and no packs switched on; `folio genres` and `folio pack
    list` use it to answer before `folio init`.
    """
    try:
        root = charter_mod.find_library(start)
    except FolioError:
        here = start.resolve()
        charter = charter_mod.parse({}, here / charter_mod.CHARTER)
        packs = packs_mod.available(here / ".folio-none", charter)
        registry = genres_mod.load(here / ".folio-none", charter, packs, card_check_names())
        return Library(here, charter, registry, []), False
    return load_at(root), True


def load_at(root: Path) -> Library:
    charter = charter_mod.load(root)
    names = check_names()
    for name in charter.checks:
        if name not in names:
            raise FolioError(f"folio.yaml: `checks.{name}` names no check; checks.md lists them")
    packs = packs_mod.available(root, charter)
    registry = genres_mod.load(root, charter, packs, card_check_names())
    documents = discover(root, registry)
    for doc in documents:
        if doc.is_home and doc.main is not None:
            # The home page's title is the charter's name; the page carries none of its own.
            doc.main.meta["title"] = charter.name
    lib = Library(root, charter, registry, documents)
    for genre in registry.genres.values():
        if genre.prefix:
            lib.prefixes.add(genre.prefix)
    for doc in documents:
        lib.by_id.setdefault(doc.id, []).append(doc)
        for df in doc.files:
            lib.by_path[df.path] = df
    for df in lib.files:
        lib.links[df.path] = file_links(lib, df)
    for doc in documents:
        mf = doc.meta_file
        if mf is not None:
            lib.links[mf.path].extend(field_links(lib, doc))
    _derive_status(lib)
    return lib


def _derive_status(lib: Library) -> None:
    """A permanent document's status follows from what supersedes or retracts it."""
    for doc in lib.documents:
        written = doc.meta.get("status")
        doc.status = str(written) if written else "live"
    for doc in lib.documents:
        mf = doc.meta_file
        if mf is None:
            continue
        for link in lib.links.get(mf.path, []):
            if link.kind != "field":
                continue
            if link.field == "supersedes":
                for target in link.docs:
                    if target.genre is not None and doc.genre is not None and \
                            target.genre.lineage[-1] == doc.genre.lineage[-1]:
                        target.superseded_by.append(doc)
            if link.field == "about" and doc.is_a("journal") and doc.meta.get("kind") == "retraction":
                for target in link.docs:
                    target.retracted_by.append(doc)
    for doc in lib.documents:
        if doc.genre is not None and doc.genre.lives == "permanent":
            if doc.retracted_by:
                doc.status = "retracted"
            elif doc.superseded_by:
                doc.status = "superseded"
            else:
                doc.status = "live"
