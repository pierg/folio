"""`folio new` and `folio journal add`: new documents from their genre's skeleton."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

from .. import paths
from ..documents import Document
from ..errors import FolioError
from ..frontmatter import dump
from ..genres import FieldSpec, Genre
from ..library import Library
from ..links import RECORD_ID_RE
from ..metaedit import set_meta
from ..util import is_slug, parse_date, slugify, today


def _base_values(when: _dt.date) -> dict[str, str]:
    return {"date": when.isoformat(), "yyyy": f"{when.year:04d}"}


def next_number(lib: Library, prefix: str) -> int:
    """The next free record number: one past the highest ever used by a present file."""
    highest = 0
    for doc in lib.documents:
        if doc.genre is None or doc.genre.prefix != prefix:
            continue
        for candidate in (doc.id, Path(doc.key).stem):
            match = RECORD_ID_RE.match(candidate)
            if match and match.group(1) == prefix:
                highest = max(highest, int(match.group(2)))
    return highest + 1


def _coerce(spec: FieldSpec, raw: str) -> Any:
    if spec.type == "integer":
        if not raw.strip().lstrip("-").isdigit():
            raise FolioError(f"--{spec.name} must be an integer")
        return int(raw)
    if spec.type == "ids":
        return [v.strip() for v in raw.split(",") if v.strip()]
    if spec.type == "date" and parse_date(raw) is None:
        raise FolioError(f"--{spec.name} must be a date, YYYY-MM-DD")
    if spec.type == "enum" and raw not in (spec.values or []):
        raise FolioError(f"--{spec.name} must be one of {', '.join(spec.values or [])}")
    return raw


def _write(lib: Library, rel: str, text: str) -> str:
    target = lib.root / rel
    if target.exists():
        raise FolioError(f"{rel} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return rel


def _skeleton(genre: Genre, name: str, values: dict[str, str]) -> str:
    return paths.fill(genre.skeleton_file(name).read_text(encoding="utf-8"), values)


def _fmt(rel: str) -> str:
    return {".html": "html", ".md": "markdown", ".tex": "latex"}[Path(rel).suffix]


_TEX_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
_TEX_TITLE_RE = re.compile(r"\\title\{[^\n]*\}")


def tex_escape(text: str) -> str:
    return "".join(_TEX_SPECIAL.get(c, c) for c in text)


def _fill_tex_title(text: str, title: str) -> str:
    """Put the title into a LaTeX file's `\\title{..}` line, the one the paper builds from."""
    value = tex_escape(title)
    return _TEX_TITLE_RE.sub(lambda m: "\\title{" + value + "}", text, count=1)


def taken(lib: Library, ident: str) -> Document | None:
    """The document that already holds an id; ids are unique across the whole library."""
    docs = lib.by_id.get(ident)
    return docs[0] if docs else None


def new(lib: Library, genre_name: str, slug: str | None, *, part: tuple[str, str] | None = None,
        title: str | None = None, description: str | None = None, tags: str | None = None,
        fields: dict[str, str] | None = None, status: str | None = None) -> list[str]:
    genre = lib.registry.get(genre_name)
    if not genre.active:
        why = "switched off in the charter" if not genre.enabled else f"in pack `{genre.pack}`, which is off"
        raise FolioError(f"genre `{genre.name}` is {why}")
    fields = fields or {}
    meta: dict[str, Any] = {}
    if title is not None:
        meta["title"] = title
    if description is not None:
        meta["description"] = description
    if tags is not None:
        meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if status is not None:
        if genre.lives == "permanent":
            raise FolioError(f"a `{genre.name}` is permanent and writes no status; the engine derives it")
        if status not in genre.states:
            raise FolioError(f"--status must be one of {', '.join(genre.states)}")
        meta["status"] = status
    for key, raw in fields.items():
        spec = genre.field(key)
        if spec is None:
            known = ", ".join(f.name for f in genre.fields) or "none"
            raise FolioError(f"genre `{genre.name}` has no field `{key}` (its fields: {known})")
        meta[key] = _coerce(spec, raw)
    values = _base_values(today())
    values["genre"] = genre.name
    if part is not None:
        return _new_part(lib, genre, slug, part, values, meta)
    if genre.prefix:
        if slug:
            raise FolioError(f"`{genre.name}` is a record genre and takes the next free id; give no slug")
        values["n"] = str(next_number(lib, genre.prefix))
    else:
        if not slug or not is_slug(slug):
            raise FolioError(f"give a slug of lowercase words joined by hyphens, not `{slug}`")
        holder = taken(lib, slug)
        if holder is not None:
            raise FolioError(f"the id `{slug}` is taken by {holder.key}; ids are unique across the "
                             "library, so pick another slug")
        values["slug"] = slug
    main = paths.fill(genre.path, values)
    left = paths.missing(main, values)
    if left:
        raise FolioError(f"genre `{genre.name}`: its path needs {', '.join(left)}")
    written = [_write(lib, main, _skeleton(genre, genre.skeleton, values))]
    for spec in genre.parts.values():
        if "{nn}" in spec.path or "{name}" in spec.path:
            continue
        written.append(_write(lib, paths.fill(spec.path, values), _skeleton(genre, spec.skeleton, values)))
    holders = [p for p in written if _fmt(p) != "latex"]
    address = genre.address_part()
    meta_home = holders[0] if _fmt(main) != "latex" or address is None else \
        paths.fill(address.path, values)
    for rel in written:
        if _fmt(rel) == "latex" and title is not None:
            target = lib.root / rel
            target.write_text(_fill_tex_title(target.read_text(encoding="utf-8"), title), encoding="utf-8")
    for rel in holders:
        target = lib.root / rel
        text = target.read_text(encoding="utf-8")
        # The genre asked for, even when a variant shares its parent's skeleton.
        text = set_meta(text, _fmt(rel), "genre", genre.name)
        for key, value in meta.items():
            if key in ("title", "description", "tags") or rel == meta_home:
                text = set_meta(text, _fmt(rel), key, value)
        target.write_text(text, encoding="utf-8")
    return written


def _new_part(lib: Library, genre: Genre, slug: str | None, part: tuple[str, str],
              values: dict[str, str], meta: dict[str, Any]) -> list[str]:
    part_name, name = part
    spec = genre.parts.get(part_name)
    if spec is None:
        known = ", ".join(genre.parts) or "none"
        raise FolioError(f"genre `{genre.name}` has no part `{part_name}` (its parts: {known})")
    if spec.lives == "permanent":
        hint = " `folio paper freeze` writes a paper's versions." if genre.is_a("paper") else ""
        raise FolioError(f"a `{part_name}` part is permanent: it is a snapshot a command writes, never "
                         f"one started from a skeleton.{hint}")
    if not slug:
        raise FolioError("give the slug of the document the part belongs to")
    values["slug"] = slug
    main = paths.fill(genre.path, values)
    doc: Document | None = next((d for d in lib.documents if d.key == main), None)
    if doc is None:
        raise FolioError(f"no `{genre.name}` document at {main}; create it first")
    if "{name}" in spec.path:
        if not is_slug(name):
            raise FolioError(f"a part name is lowercase words joined by hyphens, not `{name}`")
        values["name"] = name
    if "{nn}" in spec.path:
        used = [int(f.captures["nn"]) for f in doc.files if f.part == part_name and "nn" in f.captures]
        number = max(used, default=0) + 1
        if number > 99:
            raise FolioError(f"{doc.key} already has 99 `{part_name}` parts")
        values["nn"] = f"{number:02d}"
    rel = paths.fill(spec.path, values)
    left = paths.missing(rel, values)
    if left:
        raise FolioError(f"part `{part_name}`: its path needs {', '.join(left)}")
    _write(lib, rel, _skeleton(genre, spec.skeleton, values))
    if _fmt(rel) != "latex":
        target = lib.root / rel
        text = set_meta(target.read_text(encoding="utf-8"), _fmt(rel), "genre", genre.name)
        for key in ("title", "description", "tags"):
            if key in meta:
                text = set_meta(text, _fmt(rel), key, meta[key])
        target.write_text(text, encoding="utf-8")
    return [rel]


def journal_add(lib: Library, *, title: str, description: str, body: str, kind: str | None = None,
                about: str | None = None, date: str | None = None, tags: str | None = None) -> str:
    genre = lib.registry.get("journal")
    if kind:
        accepted = lib.journal_kinds()
        if kind not in accepted:
            raise FolioError(f"kind `{kind}` is not one this library accepts: {', '.join(accepted)}")
    about_ids = [a.strip() for a in (about or "").split(",") if a.strip()]
    for ident in about_ids:
        if ident not in lib.by_id:
            raise FolioError(f"--about `{ident}` names no document")
    when = parse_date(date) if date else today()
    if when is None:
        raise FolioError(f"--date must be YYYY-MM-DD, not `{date}`")
    values = _base_values(when)
    base = slugify(" ".join(title.split()[:6]))  # the file slug: the title's first six words
    for attempt in range(1, 1000):
        values["slug"] = base if attempt == 1 else f"{base}-{attempt}"
        rel = paths.fill(genre.path, values)
        if not (lib.root / rel).exists() and taken(lib, Path(rel).stem) is None:
            break
    front: dict[str, Any] = {"title": title, "description": description, "genre": genre.name, "date": when}
    if kind:
        front["kind"] = kind
    if about_ids:
        front["about"] = about_ids
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    if tag_list:
        front["tags"] = tag_list
    return _write(lib, rel, "---\n" + dump(front) + "---\n\n" + body.strip() + "\n")
