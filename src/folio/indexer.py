"""The generated indices in `.folio/`: written by `folio index`, compared by the gate."""

from __future__ import annotations

import datetime as _dt
import html as _html
import json
import re
from pathlib import Path
from typing import Any

from .documents import DocFile, Document, url_of
from .html import NOT_PROSE, text_of
from .library import Library

INDEX_DIR = ".folio"
FILES = ("catalog.json", "backlinks.json", "search.json", "nav.json", "journal.json", "cards.json")


def _plain(value: Any) -> Any:
    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return value


def _squash(text: str) -> str:
    return " ".join(text.split())


def _fields(doc: Document) -> dict[str, Any]:
    if doc.genre is None:
        return {}
    meta = doc.meta
    return {f.name: _plain(meta[f.name]) for f in doc.genre.fields if f.name in meta}


def _part_entry(df: DocFile) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "part": df.part, "path": df.path, "url": url_of(df.path),
        "title": str(df.meta.get("title") or ""), "description": str(df.meta.get("description") or ""),
    }
    if "nn" in df.captures:
        entry["number"] = int(df.captures["nn"])
    if "name" in df.captures:
        entry["name"] = df.captures["name"]
    return entry


def _field_order(doc: Document) -> list[str]:
    """The fields the document holds, in the order its card declares them."""
    if doc.genre is None:
        return []
    return [f.name for f in doc.genre.fields if f.name in doc.meta]


def _map_rows(lib: Library, doc: Document) -> list[str]:
    """A map's rows, in the map's own order: the path of each document listed."""
    from .commands.maps_cmds import _rows

    out: list[str] = []
    for row in _rows(lib, doc, doc.main.text if doc.main else ""):
        target = row["doc"]
        if target is not None and target.key not in out:
            out.append(target.key)
    return out


_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", re.S | re.I)


def _map_sections(lib: Library, doc: Document) -> list[dict[str, Any]]:
    """A map's rows as the map groups them: each list of rows under the heading nearest above it.

    Consecutive lists under the same heading are one section. A list with no heading
    above it has no title. A row already listed earlier is not listed again.
    """
    from .commands.maps_cmds import _ROWS_RE, _rows

    text = doc.main.text if doc.main else ""
    headings = [(m.start(), " ".join(_html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).split()))
                for m in _HEADING_RE.finditer(text)]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    rows = _rows(lib, doc, text)
    for block in _ROWS_RE.finditer(text):
        above = [title for at, title in headings if at < block.start()]
        title = above[-1] if above and above[-1] else None
        paths = []
        for row in rows:
            target = row["doc"]
            if block.start(2) <= row["start"] < block.end(2) and target is not None and target.key not in seen:
                seen.add(target.key)
                paths.append(target.key)
        if not paths:
            continue
        if out and out[-1]["title"] == title:
            out[-1]["rows"].extend(paths)
        else:
            out.append({"title": title, "rows": paths})
    return out


_ABSTRACT_RE = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)
_TEX_ARG_RE = re.compile(r"\\([A-Za-z]+)\*?(?:\[[^\]]*\])?\{([^{}]*)\}")
_TEX_DROP = {"cite", "citep", "citet", "label", "ref", "eqref", "footnote"}


def latex_abstract(latex: str | None) -> str:
    """A paper's abstract as plain text, read from its source: paragraphs split by a blank line."""
    match = _ABSTRACT_RE.search(latex or "")
    if not match:
        return ""
    text = match.group(1)

    def arg(m: re.Match[str]) -> str:
        name, value = m.group(1), m.group(2)
        if name in _TEX_DROP:
            return ""
        if name == "fcite":
            return ", ".join(v.strip() for v in value.split(","))
        return value

    for _ in range(10):  # nested commands unwrap from the inside out
        text, n = _TEX_ARG_RE.subn(arg, text)
        if not n:
            break
    escaped: list[str] = []

    def keep(m: re.Match[str]) -> str:
        escaped.append(m.group(1))
        return f"\x00{len(escaped) - 1}\x00"

    text = re.sub(r"\\([%&$#_{}])", keep, text)
    text = re.sub(r"\\[A-Za-z]+\*?|[{}$]", "", text).replace("~", " ")
    text = text.replace("---", "\u2014").replace("--", "\u2013")
    text = re.sub(r"\x00(\d+)\x00", lambda m: escaped[int(m.group(1))], text)
    paras = [_squash(p) for p in re.split(r"\n\s*\n", text)]
    text = "\n\n".join(p for p in paras if p)
    return re.sub(r"\s+([,.;:])", r"\1", text)


def _natural(name: str) -> list[Any]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def paper_versions(lib: Library, doc: Document) -> list[dict[str, Any]]:
    """A paper's frozen versions, from its permanent parts, in their names' natural order."""
    if doc.genre is None:
        return []
    out = []
    for df in doc.files:
        spec = doc.genre.parts.get(df.part) if df.part is not None else None
        if spec is None or spec.lives != "permanent":
            continue
        folder = df.path.rsplit("/", 1)[0]
        pdf = f"{folder}/paper.pdf"
        out.append({"name": df.captures.get("name", folder.rsplit("/", 1)[-1]), "path": df.path,
                    "pdf": pdf if (lib.root / pdf).is_file() else None})
    return sorted(out, key=lambda v: _natural(v["name"]))


def topics(lib: Library) -> dict[str, list[str]]:
    """The topics each document falls under, by path: the ids of the charter's home maps, in its order.

    A document is under a home map when the map reaches it through map rows (a map's
    rows can list maps, and their rows count too), or when it is a concept linked from
    a document under the map. A journal entry is under every topic of a document in
    its `about`. The home page is under every topic. Nothing on a document declares one.
    """
    home_maps: list[Document] = []
    for name in lib.charter.home_maps:
        home_maps.extend(d for d in lib.find(name, "map") if d not in home_maps)
    rows = {d: [lib.by_path[k].doc for k in _map_rows(lib, d)] for d in lib.documents if d.is_a("map")}
    out: dict[str, list[str]] = {d.key: [] for d in lib.documents}
    for top in home_maps:
        reached: set[Document] = set()
        todo = [top]
        while todo:
            doc = todo.pop()
            if doc in reached or doc.is_home or doc.is_a("journal"):
                continue
            reached.add(doc)
            todo.extend(rows.get(doc, []))
            for link in lib.doc_links(doc):
                todo.extend(t for t in link.docs if t.is_a("concept"))
        for doc in lib.documents:
            if doc in reached and top.id not in out[doc.key]:
                out[doc.key].append(top.id)
    ids = [m.id for m in home_maps]
    for doc in lib.documents:
        if doc.is_home:
            out[doc.key] = list(ids)
    for doc in lib.documents:
        if doc.is_a("journal"):
            under = {t for link in lib.doc_links(doc) if link.kind == "field" and link.field == "about"
                     for target in link.docs for t in out[target.key]}
            out[doc.key] = [i for i in ids if i in under]
    return out


def catalog(lib: Library) -> dict[str, Any]:
    docs = []
    under = topics(lib)
    for doc in lib.documents:
        entry = {
            "id": doc.id, "genre": doc.genre_name, "path": doc.key, "url": doc.url,
            "title": doc.title, "description": doc.description, "status": doc.status,
            "tags": doc.tags, "fields": _fields(doc), "field_order": _field_order(doc),
            "parts": [_part_entry(f) for f in doc.files if f.part is not None],
            "topics": under[doc.key],
        }
        if doc.is_a("map"):
            entry["rows"] = _map_rows(lib, doc)
            entry["sections"] = _map_sections(lib, doc)
        if doc.is_a("paper"):
            entry["abstract"] = latex_abstract(doc.main.latex if doc.main else None)
            entry["versions"] = paper_versions(lib, doc)
        docs.append(entry)
    return {"documents": docs}


def backlinks(lib: Library) -> dict[str, Any]:
    out: dict[str, dict[str, Any]] = {}
    for doc in lib.documents:
        out[doc.key] = {"id": doc.id, "cites": set(), "cited_by": set(), "about": [], "fields": {},
                        "superseded_by": sorted(d.key for d in doc.superseded_by),
                        "retracted_by": sorted(d.key for d in doc.retracted_by)}
    for doc in lib.documents:
        for link in lib.doc_links(doc):
            for target in link.docs:
                if target is doc:
                    continue
                out[doc.key]["cites"].add(target.key)
                out[target.key]["cited_by"].add(doc.key)
                if link.kind != "field":
                    continue
                if link.field == "about" and doc.is_a("journal"):
                    out[target.key]["about"].append({
                        "path": doc.key, "id": doc.id, "kind": doc.meta.get("kind"),
                        "date": _plain(doc.meta.get("date")),
                    })
                else:
                    out[target.key]["fields"].setdefault(link.field, set()).add(doc.key)
    for entry in out.values():
        entry["cites"] = sorted(entry["cites"])
        entry["cited_by"] = sorted(entry["cited_by"])
        entry["about"] = sorted(entry["about"], key=lambda a: (str(a["date"]), a["path"]), reverse=True)
        entry["fields"] = {k: sorted(v) for k, v in sorted(entry["fields"].items())}
    return out


def _text(df: DocFile) -> str:
    if df.latex is not None:
        return _squash(re.sub(r"\\[A-Za-z]+\*?|[{}\[\]]", " ", df.latex))
    if df.body is None:
        return ""
    return _squash(df.body.text(NOT_PROSE))


def search(lib: Library) -> list[dict[str, Any]]:
    out = []
    for doc in lib.documents:
        for df in doc.files:
            spec = doc.genre.parts.get(df.part) if doc.genre is not None and df.part is not None else None
            if spec is not None and spec.lives == "permanent":
                continue  # a snapshot of the source: the source is searched already
            out.append({
                "id": doc.id, "genre": doc.genre_name, "part": df.part, "path": df.path,
                "url": url_of(df.path), "title": str(df.meta.get("title") or doc.title),
                "description": str(df.meta.get("description") or doc.description),
                "tags": doc.tags, "status": doc.status, "text": _text(df),
            })
    return out


def nav(lib: Library) -> dict[str, Any]:
    """Each document with numbered parts (a guide's chapters), in number order."""
    out: dict[str, Any] = {}
    for doc in lib.documents:
        numbered = [f for f in doc.files if f.part is not None and "nn" in f.captures]
        if not numbered:
            continue
        numbered.sort(key=lambda f: (int(f.captures["nn"]), f.path))
        out[doc.key] = {"id": doc.id, "title": doc.title, "url": doc.url,
                        "chapters": [_part_entry(f) for f in numbered]}
    return out


def journal(lib: Library) -> list[dict[str, Any]]:
    entries = []
    for doc in lib.documents:
        if not doc.is_a("journal"):
            continue
        meta = doc.meta
        about = meta.get("about") or []
        entries.append({
            "id": doc.id, "path": doc.key, "url": doc.url, "date": _plain(meta.get("date")),
            "title": doc.title, "description": doc.description, "kind": meta.get("kind"),
            "about": [str(a) for a in (about if isinstance(about, list) else [about])],
            "tags": doc.tags,
        })
    entries.sort(key=lambda e: (str(e["date"]), e["path"]), reverse=True)
    return entries


def cards(lib: Library) -> list[dict[str, Any]]:
    out = []
    for doc in lib.documents:
        for df in doc.files:
            if df.format != "html" or df.body is None:
                continue
            for el in df.body.iter():
                if el.tag != "details" or "card" not in el.classes:
                    continue
                summary = el.first("summary")
                question = _squash(summary.text()) if summary is not None else ""
                answer_nodes = [c for c in el.children if c is not summary]
                out.append({"doc": doc.id, "genre": doc.genre_name, "path": df.path,
                            "url": url_of(df.path), "question": question,
                            "answer": _squash(text_of(answer_nodes)), "tags": doc.tags})
    return out


def build(lib: Library) -> dict[str, str]:
    """What `folio index` writes, file name to text."""
    data = {
        "catalog.json": catalog(lib), "backlinks.json": backlinks(lib), "search.json": search(lib),
        "nav.json": nav(lib), "journal.json": journal(lib), "cards.json": cards(lib),
    }
    return {name: json.dumps(_plain(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
            for name, value in data.items()}


def write(lib: Library) -> list[str]:
    """Write the indices; return the paths that changed."""
    folder = lib.root / INDEX_DIR
    folder.mkdir(exist_ok=True)
    changed = []
    for name, text in build(lib).items():
        path = folder / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(f"{INDEX_DIR}/{name}")
    return changed


def stale(lib: Library) -> list[tuple[str, str]]:
    folder = lib.root / INDEX_DIR
    out = []
    for name, text in build(lib).items():
        path: Path = folder / name
        rel = f"{INDEX_DIR}/{name}"
        if not path.is_file():
            out.append((rel, "missing; run `folio index`"))
        elif path.read_text(encoding="utf-8") != text:
            out.append((rel, "out of date; run `folio index`"))
    return out
