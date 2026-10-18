"""Gate checks: they run across the whole library, on every document."""

from __future__ import annotations

import re
from collections import deque
from typing import Any, Callable

from .. import indexer
from .. import links as links_mod
from ..charter import CHARTER
from ..documents import Document
from ..genres import FieldSpec
from ..library import Library
from ..links import RECORD_ID_RE
from .lifecycle import reused_ids
from ..util import PLACEHOLDER_RE, has_placeholder, is_slug, parse_date

Found = list[tuple[str, str]]
GateCheck = Callable[[Library], Found]
LAYOUTS = ("canvas", "column")  # a page's `layout`: the whole canvas (default), or the reading column


def broken_link(lib: Library) -> Found:
    out = []
    for path, links in lib.links.items():
        for link in links:
            if link.resolved:
                continue
            if link.kind == "href":
                out.append((path, f"`{link.raw}` resolves to nothing"))
            elif link.kind == "code":
                out.append((path, f"`{link.raw}` names no document"))
            elif link.kind == "library":
                out.append((path, f"`{link.raw}` resolves to nothing in that library"))
            elif link.kind == "fcite":
                out.append((path, f"\\fcite{{{link.raw}}} names no document"))
            else:
                out.append((path, f"field `{link.field}`: `{link.raw}` names no document"))
    return out


def library_link(lib: Library) -> Found:
    """One warning per library the charter names that is not at its path: its links go unchecked."""
    out = []
    for name, ref in lib.charter.libraries.items():
        if links_mod.library_root(lib, name) is not None:
            continue
        count = sum(1 for links in lib.links.values() for link in links
                    if (link.kind == "library" and link.raw.startswith(name + ":"))
                    or (link.kind == "href" and (link.target or "").startswith(name + ":")))
        out.append((CHARTER, f"library `{name}` is not at `{ref.path}`, so its "
                    f"{count} link{'' if count == 1 else 's'} {'is' if count == 1 else 'are'} not checked"))
    return out


def location(lib: Library) -> Found:
    out = []
    for doc in lib.documents:
        if doc.misplaced:
            if doc.genre is None:
                out.append((doc.key, f"genre `{doc.genre_name}` is not a genre this library knows"))
            else:
                out.append((doc.key, f"a `{doc.genre.name}` document belongs at `{doc.genre.path}`"))
            continue
        if doc.main is None and doc.genre is not None:
            out.append((doc.files[0].path, f"the document's main file `{doc.key}` is missing"))
        for df in doc.files:
            if not df.holds_metadata:
                continue
            declared = df.meta.get("genre")
            if declared and str(declared) != doc.genre_name:
                out.append((df.path, f"says genre `{declared}` but sits at a `{doc.genre_name}` path"))
    return out


def _type_problem(spec: FieldSpec, value: Any) -> str | None:
    if spec.type == "string":
        if isinstance(value, (dict, list)) or isinstance(value, bool):
            return "must be a string"
    elif spec.type == "integer":
        if isinstance(value, bool) or not (isinstance(value, int) or str(value).strip().lstrip("-").isdigit()):
            return f"must be an integer, not `{value}`"
    elif spec.type == "date":
        if parse_date(value) is None:
            return f"must be a date, YYYY-MM-DD, not `{value}`"
    elif spec.type == "enum":
        if str(value) not in (spec.values or []):
            return f"`{value}` is not one of {', '.join(spec.values or [])}"
    elif spec.type == "ids":
        if not isinstance(value, (list, str)):
            return "must be a list of ids"
    elif spec.type == "id":
        if not isinstance(value, str):
            return "must be one id"
    return None


def fields(lib: Library) -> Found:
    out: Found = []
    for doc in lib.documents:
        for df in doc.files:
            if df.meta_error:
                out.append((df.path, df.meta_error.split(": ", 1)[-1]))
                continue
            if not df.holds_metadata:
                continue
            for key in ("title", "description", "genre"):
                if not str(df.meta.get(key) or "").strip():
                    out.append((df.path, f"missing `{key}`"))
            for tag in _tags(df.meta.get("tags")):
                if "{{" not in tag and not is_slug(tag):
                    out.append((df.path, f"tag `{tag}` is not a lowercase slug"))
            layout = df.meta.get("layout")
            if df.format == "html" and layout is not None and str(layout).strip() not in LAYOUTS:
                out.append((df.path, f"layout `{layout}` must be one of {', '.join(LAYOUTS)}"))
        genre = doc.genre
        mf = doc.meta_file
        if genre is None or mf is None or doc.is_home or mf.meta_error:
            continue
        if genre.prefix and not str(mf.meta.get("id") or "").strip():
            out.append((mf.path, "missing `id`"))
        if genre.lives == "permanent" and "status" in mf.meta:
            out.append((mf.path, "a permanent document writes no `status`; the engine derives it"))
        field_links = {l.raw: l for l in lib.links.get(mf.path, []) if l.kind == "field"}
        for spec in genre.fields:
            value = mf.meta.get(spec.name)
            if value is None or (isinstance(value, (str, list)) and not value):
                if spec.required:
                    out.append((mf.path, f"missing required field `{spec.name}`"))
                continue
            if has_placeholder(value):
                continue
            problem = _type_problem(spec, value)
            if problem:
                out.append((mf.path, f"field `{spec.name}` {problem}"))
                continue
            if spec.type == "path":
                if not (lib.charter.root_dir / str(value)).exists():
                    out.append((mf.path, f"field `{spec.name}`: `{value}` does not exist under the root"))
            if spec.type in ("id", "ids"):
                values = value if isinstance(value, list) else [v.strip() for v in str(value).split(",")]
                for ident in values:
                    link = field_links.get(str(ident).strip())
                    if link is None or not link.resolved:
                        continue  # broken-link names it
                    out.extend((mf.path, m) for m in _id_limits(spec, str(ident), link.docs))
    return out


def _id_limits(spec: FieldSpec, ident: str, docs: list[Document]) -> list[str]:
    if spec.genre and not any(d.is_a(spec.genre) for d in docs):
        return [f"field `{spec.name}`: `{ident}` is not a {spec.genre}"]
    if spec.status:
        fitting = [d for d in docs if not spec.genre or d.is_a(spec.genre)]
        if not any(d.status in spec.status for d in fitting):
            states = ", ".join(sorted({d.status for d in fitting}))
            return [f"field `{spec.name}`: `{ident}` is `{states}`; it must be {' or '.join(spec.status)}"]
    return []


def _tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def status(lib: Library) -> Found:
    out = []
    for doc in lib.documents:
        genre = doc.genre
        if genre is None or genre.lives == "permanent":
            continue
        for df in doc.files:
            if not df.holds_metadata:
                continue
            value = df.meta.get("status")
            if value is None or str(value) == "":
                if df is doc.meta_file and "live" not in genre.states:
                    out.append((df.path, f"needs a status: one of {', '.join(genre.states)}"))
            elif "{{" not in str(value) and str(value) not in genre.states:
                out.append((df.path, f"status `{value}` is not one of {', '.join(genre.states)}"))
    return out


# A LaTeX command name ending right where the braces start.
_LATEX_COMMAND_END_RE = re.compile(r"\\[A-Za-z@]+\*?$")


def placeholder(lib: Library) -> Found:
    out = []
    for df in lib.files:
        seen: dict[str, int] = {}
        for match in PLACEHOLDER_RE.finditer(df.text):
            if _LATEX_COMMAND_END_RE.search(df.text[max(0, match.start() - 64):match.start()]):
                continue  # `\graphicspath{{figures/}}`: LaTeX braces, not a placeholder
            text = " ".join(match.group(0).split())
            seen[text] = seen.get(text, 0) + 1
        for text, count in seen.items():
            shown = text if len(text) <= 70 else text[:67] + "...}}"
            out.append((df.path, f"placeholder left: {shown}" + (f" ({count} times)" if count > 1 else "")))
    return out


def _home_maps(lib: Library) -> list[Document]:
    out = []
    for name in lib.charter.home_maps:
        out.extend(lib.find(name, "map"))
    return out


def orphan(lib: Library) -> Found:
    """The no-orphans rule: every document is on a map, or reachable from one."""
    home = [d for d in lib.documents if d.is_home]
    roots = home + _home_maps(lib)
    forward: dict[Document, set[Document]] = {d: set() for d in lib.documents}
    on_map: set[Document] = set(_home_maps(lib))
    files_on_map: set[str] = set()
    for doc in lib.documents:
        if doc.is_a("journal"):
            continue
        for link in lib.doc_links(doc):
            for target in link.docs:
                if target is doc:
                    continue
                forward[doc].add(target)
                if link.kind == "field":
                    forward[target].add(doc)
                elif doc.is_a("map"):
                    on_map.add(target)
                    if link.target is not None:
                        files_on_map.add(link.target)
    # `optional` asks for a map row or a link from a document on a map: any map, home or not.
    starts = roots + [d for d in lib.documents if d in on_map]
    reached: set[Document] = set(starts)
    queue = deque(starts)
    while queue:
        doc = queue.popleft()
        for nxt in forward[doc]:
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    out = []
    for doc in lib.documents:
        genre = doc.genre
        if genre is None or doc.is_home or doc.status == "retired":
            continue
        if genre.on_map == "required" and doc not in on_map:
            out.append((doc.key, "is on no map; add it with `folio map add <map> <doc>`"))
        elif genre.on_map == "optional" and doc not in reached:
            out.append((doc.key, "is on no map and linked from nothing on one"))
        for df in doc.files:
            if df.part is not None and genre.parts[df.part].on_map == "never" and df.path in files_on_map:
                out.append((df.path, f"a `{df.part}` is never listed on a map; list its document instead"))
    return out


def home_maps(lib: Library) -> Found:
    out = []
    for name in lib.charter.home_maps:
        maps = lib.find(name, "map")
        if not maps:
            out.append((CHARTER, f"home map `{name}` does not exist"))
        elif all(m.status == "draft" for m in maps):
            out.append((CHARTER, f"home map `{name}` is a draft"))
    return out


def unique_id(lib: Library) -> Found:
    """Every id names one document across the whole library; a record id has its form and is never reused."""
    out = []
    seen: dict[str, Document] = {}
    for doc in lib.documents:
        key = doc.id.casefold()  # ids compare without regard to case
        if key in seen:
            out.append((doc.key, f"id `{doc.id}` is also the id of {seen[key].key};"
                                 " ids are unique across the library, whatever their case"))
        else:
            seen[key] = doc
        genre = doc.genre
        if genre is None or genre.prefix is None or doc.misplaced:
            continue
        mf = doc.meta_file
        written = str(mf.meta.get("id") or "") if mf is not None else ""
        if not written or "{{" in written:
            continue
        match = RECORD_ID_RE.match(written)
        if not match or match.group(1) != genre.prefix or match.group(2).startswith("0"):
            out.append((doc.key, f"id `{written}` is not of the form {genre.prefix}-<n>"))
            continue
        stem = doc.key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if stem != written:
            out.append((doc.key, f"id `{written}` does not match its file name `{stem}`"))
    out.extend(reused_ids(lib))
    return out


def index_current(lib: Library) -> Found:
    return indexer.stale(lib)


GATE_CHECKS: dict[str, GateCheck] = {
    "broken-link": broken_link,
    "library-link": library_link,
    "location": location,
    "fields": fields,
    "status": status,
    "placeholder": placeholder,
    "orphan": orphan,
    "home-maps": home_maps,
    "unique-id": unique_id,
    "index-current": index_current,
}
