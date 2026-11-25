"""Redirects: where a moved or retired document's old address now leads.

`.folio/redirects.json` holds `{"redirects": {"<old file>": "<new file>"}}`,
both library-relative source paths (`content/notes/x.html`,
`content/results/R-1.md`), and `"ids": {"<old id>": "<new id>"}` for documents
`folio rm` deleted, so a citation of a deleted document's id leads to what
replaced it. `folio mv`, `folio promote` and `folio rm --to`
write it; `folio index` never touches it. Chains are collapsed on write, so
every value is the file the address leads to now. The exported site serves
each old address as a redirect to the new one, and the gate resolves a link
through it the same way.
"""

from __future__ import annotations

import json
from pathlib import Path

from .errors import FolioError

FILE = ".folio/redirects.json"
_cache: dict[Path, tuple[float, dict[str, str]]] = {}
_ids: dict[Path, dict[str, str]] = {}


def load(root: Path) -> dict[str, str]:
    path = root / FILE
    if not path.is_file():
        return {}
    mtime = path.stat().st_mtime
    cached = _cache.get(path)
    if cached is not None and cached[0] == mtime:
        return dict(cached[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FolioError(f"{FILE}: not valid JSON: {exc}") from exc
    table = data.get("redirects") if isinstance(data, dict) else None
    ids = data.get("ids", {}) if isinstance(data, dict) else {}
    if not isinstance(table, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                              for k, v in table.items()):
        raise FolioError(f'{FILE}: must be {{"redirects": {{"<old file>": "<new file>"}}}}')
    if not isinstance(ids, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in ids.items()):
        raise FolioError(f'{FILE}: `ids` must be {{"<old id>": "<new id>"}}')
    _cache[path] = (mtime, dict(table))
    _ids[path] = dict(ids)
    return dict(table)


def ids(root: Path) -> dict[str, str]:
    """The ids of deleted documents, each with the id of the document that replaced it."""
    load(root)
    return dict(_ids.get(root / FILE, {}))


def add_id(root: Path, old: str, new: str) -> None:
    """Record that a deleted document's id now leads to another document's."""
    table, known = load(root), ids(root)
    for k, v in list(known.items()):
        if v == old:
            known[k] = new
    known[old] = new
    _write(root, table, known)


def target(root: Path, path: str) -> str | None:
    """The file an old address leads to now, or None when it is not redirected."""
    return load(root).get(path)


def add(root: Path, moves: dict[str, str], record: bool = True) -> list[str]:
    """Record old -> new for each move, collapsing chains; return what changed, for printing.

    With `record` false (an address that was never committed), only earlier
    redirects that led to a moved file are carried along; none is added.
    """
    if not moves:
        return []
    table = load(root)
    before = dict(table)
    for old, new in list(table.items()):
        if new in moves:
            table[old] = moves[new]
    if record:
        for old, new in moves.items():
            if old == new:
                continue
            table[old] = new
    for new in moves.values():
        table.pop(new, None)  # an address that serves a document again is no longer redirected
    if not record and table == before:
        return []
    _write(root, table, ids(root))
    if not record:
        return [f"redirected {old} -> {new}" for old, new in table.items() if before.get(old) != new]
    return [f"redirected {old} -> {new}" for old, new in moves.items() if old != new]


def _write(root: Path, table: dict[str, str], known: dict[str, str]) -> None:
    path = root / FILE
    path.parent.mkdir(exist_ok=True)
    data: dict = {"redirects": dict(sorted(table.items()))}
    if known:
        data["ids"] = dict(sorted(known.items()))
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _cache.pop(path, None)
    _ids.pop(path, None)
