"""`folio search` and `folio cards`: index the files in memory, change nothing."""

from __future__ import annotations

import re
from typing import Any

from .. import charter as charter_mod
from .. import indexer
from .. import library as library_mod
from .. import links as links_mod
from ..edits import find_doc
from ..errors import FolioError
from ..library import Library
from .maps_cmds import listing as map_listing

_WORD_RE = re.compile(r"[^\W_]+(?:[-'’._][^\W_]+)*", re.U)
MIN_TERM = 2  # shorter terms are ignored


def _tokens(text: str) -> list[str]:
    """The words of a text, lowercased; a joined word (`self-attention`) also counts as its parts."""
    out = []
    for word in _WORD_RE.findall(text.casefold()):
        out.append(word)
        parts = re.split(r"[-'’._]", word)
        if len(parts) > 1:
            out.extend(p for p in parts if p)
    return out


def _hit(tokens: list[str], term: str) -> bool:
    return any(t.startswith(term) for t in tokens)


def _score(entry: dict[str, Any], words: list[str]) -> int:
    """How well an entry matches: every term must start a word somewhere, or the score is 0."""
    title = _tokens(str(entry.get("title", ""))) + _tokens(str(entry.get("id", "")))
    desc = _tokens(str(entry.get("description", "")))
    tags = _tokens(" ".join(entry.get("tags") or []))
    text = _tokens(str(entry.get("text", "")))
    score = 0
    for word in words:
        hits = 10 * _hit(title, word) + 5 * _hit(tags, word) + 3 * _hit(desc, word)
        body = sum(1 for t in text if t.startswith(word))
        if not hits and not body:
            return 0
        score += hits + min(body, 5)
    return score


def search(lib: Library, query: str, everywhere: bool) -> list[dict[str, Any]]:
    """Documents matching every word of the query, best first, retired documents last.

    A term matches a whole word or the start of one (`soft` finds `softmax`);
    terms under two characters are ignored. The search index is rebuilt in
    memory from the files as they are now, so a document made a moment ago is
    found before `folio index` runs.
    """
    words = [w for w in dict.fromkeys(_WORD_RE.findall(query.casefold())) if len(w) >= MIN_TERM]
    if not words:
        raise FolioError(f"give at least one word of {MIN_TERM} characters or more to search for")
    libraries: list[tuple[str, Library]] = [(".", lib)]
    if everywhere:
        for rel in lib.charter.search:
            other = (lib.root / rel).resolve()
            if not (other / charter_mod.CHARTER).is_file():
                raise FolioError(f"folio.yaml: search library `{rel}` has no {charter_mod.CHARTER}")
            libraries.append((rel, library_mod.load_at(other)))
        listed = {(lib.root / rel).resolve() for rel in lib.charter.search}
        for name in lib.charter.libraries:
            other = links_mod.library_root(lib, name)
            if other is not None and other not in listed:
                libraries.append((name, library_mod.load_at(other)))
    hits = []
    for label, one in libraries:
        for entry in indexer.search(one):
            score = _score(entry, words)
            if score:
                hits.append({"library": label, "score": score, "id": entry["id"], "genre": entry["genre"],
                             "part": entry.get("part"), "path": entry["path"], "url": entry["url"],
                             "title": entry["title"], "description": entry["description"],
                             "status": entry.get("status")})
    hits.sort(key=lambda h: (h["status"] == "retired", -h["score"], h["library"], h["path"]))
    return hits


def cards(lib: Library, *, map_ref: str | None = None, tag: str | None = None,
          doc_ref: str | None = None) -> list[dict[str, Any]]:
    out = indexer.cards(lib)  # the files as they are now, not the last `folio index`
    if doc_ref is not None:
        files = {f.path for f in find_doc(lib, doc_ref).files}
        out = [c for c in out if c["path"] in files]
    if tag is not None:
        out = [c for c in out if tag in (c.get("tags") or [])]
    if map_ref is not None:
        m = find_doc(lib, map_ref, "map")
        if not m.is_a("map"):
            raise FolioError(f"{m.key} is not a map")
        rows = next(x for x in map_listing(lib)["maps"] if x["path"] == m.key)["rows"]
        files = {f.path for r in rows if r["path"] for f in lib.by_path[r["path"]].doc.files}  # type: ignore[union-attr]
        out = [c for c in out if c["path"] in files]
    return out
