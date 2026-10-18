"""Documents: every file under `content/` that a genre's path claims, with its metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from markdown_it import MarkdownIt

from . import html, paths
from .errors import FolioError
from .frontmatter import split
from .genres import Genre, Registry
from .html import Element

HOME_PATH = "content/index.html"
HOME_ID = "home"
_EXT_FORMAT = {".html": "html", ".md": "markdown", ".tex": "latex"}
_MD = MarkdownIt("commonmark", {"html": True})
_TEX_COMMENT = re.compile(r"(?<!\\)%.*")


@dataclass(eq=False)
class DocFile:
    path: str  # from the library root, with forward slashes
    abspath: Path
    format: str
    part: str | None  # None for the document's main file
    captures: dict[str, str]
    text: str
    meta: dict[str, Any]
    meta_error: str | None = None
    body: Element | None = None  # the page's content; a Markdown body rendered to HTML
    latex: str | None = None  # LaTeX with comments removed
    doc: "Document | None" = None

    @property
    def holds_metadata(self) -> bool:
        return self.format != "latex"


@dataclass(eq=False)
class Document:
    key: str  # the main file's path; unique per document
    genre: Genre | None
    genre_name: str | None
    id: str
    files: list[DocFile]
    is_home: bool = False
    misplaced: bool = False
    status: str = "live"  # the written status, or the derived one for a permanent document
    superseded_by: list["Document"] = field(default_factory=list)
    retracted_by: list["Document"] = field(default_factory=list)

    @property
    def main(self) -> DocFile | None:
        for f in self.files:
            if f.part is None:
                return f
        return None

    @property
    def meta_file(self) -> DocFile | None:
        main = self.main
        if main is not None and main.holds_metadata:
            return main
        if self.genre is not None:
            address = self.genre.address_part()
            if address is not None:
                for f in self.files:
                    if f.part == address.name:
                        return f
        for f in self.files:
            if f.holds_metadata:
                return f
        return None

    @property
    def meta(self) -> dict[str, Any]:
        mf = self.meta_file
        return mf.meta if mf is not None else {}

    @property
    def title(self) -> str:
        return str(self.meta.get("title") or "")

    @property
    def description(self) -> str:
        return str(self.meta.get("description") or "")

    @property
    def tags(self) -> list[str]:
        return tags_of(self.meta)

    @property
    def address_file(self) -> DocFile:
        if self.genre is not None:
            address = self.genre.address_part()
            if address is not None:
                for f in self.files:
                    if f.part == address.name:
                        return f
        return self.main or self.files[0]

    @property
    def url(self) -> str:
        return url_of(self.address_file.path)

    def is_a(self, genre: str) -> bool:
        return self.genre is not None and self.genre.is_a(genre)

    def parts(self, name: str) -> list[DocFile]:
        return sorted((f for f in self.files if f.part == name), key=lambda f: f.path)


def url_of(path: str) -> str:
    url = "/" + path
    if url.endswith("/index.html"):
        url = url[: -len("index.html")]
    return url


def tags_of(meta: dict[str, Any]) -> list[str]:
    raw = meta.get("tags")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def read_file(library: Path, rel: str, part: str | None, captures: dict[str, str]) -> DocFile:
    abspath = library / rel
    fmt = _EXT_FORMAT[abspath.suffix]
    text = abspath.read_text(encoding="utf-8")
    df = DocFile(rel, abspath, fmt, part, captures, text, {})
    if fmt == "html":
        root = html.parse(text)
        df.meta = dict(html.metas(root))
        df.body = html.body_of(root)
    elif fmt == "markdown":
        try:
            front, body = split(text, rel)
        except FolioError as exc:
            df.meta_error = str(exc)
            front, body = None, text
        if front is None and df.meta_error is None:
            df.meta_error = f"{rel}: has no YAML front matter"
        df.meta = front or {}
        df.body = html.parse(_MD.render(body))
    else:
        df.latex = _TEX_COMMENT.sub("", text)
    return df


def _templates(registry: Registry) -> list[tuple[Genre, str | None, str]]:
    out: list[tuple[Genre, str | None, str]] = []
    for genre in registry.genres.values():
        out.append((genre, None, genre.path))
        for part in genre.parts.values():
            out.append((genre, part.name, part.path))
    return out


def _main_key(genre: Genre, part: str | None, rel: str, captures: dict[str, str]) -> str:
    if part is None:
        return rel
    return paths.fill(genre.path, captures)


def _slug_id(genre: Genre, key: str, captures: dict[str, str]) -> str:
    last = genre.path.rsplit("/", 1)[-1]
    if "{slug}" in last:
        return PurePosixPath(key).stem
    return captures.get("slug", PurePosixPath(key).stem)


def discover(library: Path, registry: Registry) -> list[Document]:
    content = library / "content"
    if not content.is_dir():
        return []
    templates = _templates(registry)
    docs: dict[str, Document] = {}
    deferred: list[tuple[DocFile, list[tuple[Genre, str | None, dict[str, str]]]]] = []

    def attach(genre: Genre, part: str | None, df: DocFile, captures: dict[str, str]) -> None:
        key = _main_key(genre, part, df.path, captures)
        df.part = part
        df.captures = captures
        doc = docs.get(key)
        if doc is None:
            doc = Document(key=key, genre=genre, genre_name=genre.name, id="", files=[])
            docs[key] = doc
        doc.files.append(df)
        df.doc = doc

    for abspath in sorted(content.rglob("*")):
        rel_parts = abspath.relative_to(library).parts
        if not abspath.is_file() or abspath.suffix not in _EXT_FORMAT:
            continue
        if any(p.startswith(".") for p in rel_parts):
            continue
        rel = "/".join(rel_parts)
        if rel == HOME_PATH:
            df = read_file(library, rel, None, {})
            map_genre = registry.genres.get("map")
            doc = Document(key=rel, genre=map_genre, genre_name="map", id=HOME_ID, files=[df], is_home=True)
            df.doc = doc
            docs[rel] = doc
            continue
        candidates = []
        for genre, part, template in templates:
            captures = paths.match(template, rel)
            if captures is not None:
                candidates.append((genre, part, captures))
        probe = read_file(library, rel, None, {})
        declared = probe.meta.get("genre") if probe.holds_metadata else None
        if declared:
            chosen = [c for c in candidates if c[0].name == declared]
            if chosen:
                attach(chosen[0][0], chosen[0][1], probe, chosen[0][2])
            else:
                genre = registry.genres.get(str(declared))
                df = probe
                stem = PurePosixPath(rel).stem
                doc_id = str(df.meta.get("id") or (PurePosixPath(rel).parent.name if stem == "index" else stem))
                doc = Document(key=rel, genre=genre, genre_name=str(declared), id=doc_id,
                               files=[df], misplaced=True)
                df.doc = doc
                docs[rel] = doc
        elif len(candidates) == 1:
            attach(candidates[0][0], candidates[0][1], probe, candidates[0][2])
        elif candidates:
            deferred.append((probe, candidates))

    for probe, candidates in deferred:
        # Variants share their parent's path; the file that holds the metadata names the genre.
        pick = None
        for genre, part, captures in candidates:
            key = _main_key(genre, part, probe.path, captures)
            if key in docs and docs[key].genre is genre:
                pick = (genre, part, captures)
                break
        if pick is None:
            pick = next((c for c in candidates if c[0].extends is None), candidates[0])
        attach(pick[0], pick[1], probe, pick[2])

    for doc in docs.values():
        doc.files.sort(key=lambda f: (f.part is not None, f.part or "", f.path))
        if doc.is_home or doc.misplaced:
            continue
        genre = doc.genre
        assert genre is not None
        captures = doc.files[0].captures
        if genre.prefix is not None:
            mf = doc.meta_file
            written = mf.meta.get("id") if mf is not None else None
            doc.id = str(written) if written else PurePosixPath(doc.key).stem
        else:
            # A document renamed by `folio mv` keeps its id in its metadata.
            mf = doc.meta_file
            written = mf.meta.get("id") if mf is not None else None
            doc.id = str(written) if written else _slug_id(genre, doc.key, captures)
    return sorted(docs.values(), key=lambda d: d.key)
