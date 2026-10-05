"""The site a library serves: every path, and what is at it.

`folio serve` and `folio export` share this, so the local site and the
exported one are the same pages.
"""

from __future__ import annotations

import json
import mimetypes
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .. import library as library_mod
from .. import redirects as redirects_mod
from ..data import shipped
from ..documents import url_of
from ..errors import FolioError
from ..indexer import INDEX_DIR
from ..library import Library
from . import dates, render

JOURNAL_VIEW = "content/journal/index.html"
REVIEW_VIEW = "content/review/index.html"
SITE_DATA = f"{INDEX_DIR}/site.json"
COPIED = ("content", "assets")  # library folders served as they are, besides the documents


@dataclass
class Response:
    body: bytes
    content_type: str
    status: int = 200
    location: str | None = None


def shell_dir(lib: Library) -> Path:
    """The shell: a theme folder in the library when the charter names one, else folio's own."""
    if lib.charter.theme != "folio":
        theme = lib.root / lib.charter.theme
        if not (theme / "folio.css").is_file() or not (theme / "folio.js").is_file():
            raise FolioError(f"folio.yaml: theme `{lib.charter.theme}` must hold folio.css and folio.js")
        return theme
    return shipped("shell")


def redirects(lib: Library) -> dict[str, str]:
    return {k.lstrip("/"): v.lstrip("/") for k, v in redirects_mod.load(lib.root).items()}


def _served(path: str) -> str:
    """Where a source file is served: a Markdown record at its `.html` page."""
    return path[: -len(".md")] + ".html" if path.endswith(".md") else path


def _type(path: str) -> str:
    kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return kind + "; charset=utf-8" if kind.startswith("text/") or kind.endswith("json") or \
        kind.endswith("javascript") else kind


class Site:
    def __init__(self, lib: Library, base: str = "/", live: bool = False) -> None:
        if not base.startswith("/") or not base.endswith("/"):
            raise FolioError(f"--base must start and end with `/`, not `{base}`")
        self.lib = lib
        self.base = base
        self.live = live  # served by `folio serve`, so the comment panel talks to the server
        self.comments: dict | None = None  # the server's answer on commenting; None on an exported site
        self._dates: dict[str, dict[str, str]] | None = None

    @classmethod
    def load(cls, root: Path, base: str = "/", live: bool = False) -> "Site":
        return cls(library_mod.load_at(root), base, live)

    # -- data --------------------------------------------------------------

    def dates(self) -> dict[str, dict[str, str]]:
        if self._dates is None:
            self._dates = dates.from_git(self.lib.root)
        return self._dates

    def frozen(self) -> dict[str, str]:
        """Each document now in a frozen state, by path, with the date of the commit that froze it."""
        from ..checks.lifecycle import frozen_since

        out = {}
        for doc in self.lib.documents:
            since = frozen_since(self.lib, doc)
            if since is not None:
                out[doc.key] = since
        return out

    def paper_builds(self) -> dict[str, tuple[str, Path]]:
        """Each built paper, by its key: the site path its current PDF is published at, and the PDF.

        The site path is `paper.pdf` in the paper's folder; the PDF is the last
        `folio paper build`, which stays out of git.
        """
        from ..paper import PDF, current_pdf

        out = {}
        for doc in self.lib.documents:
            if doc.is_a("paper"):
                pdf = current_pdf(self.lib, doc)
                if pdf is not None:
                    out[doc.key] = (doc.key.rsplit("/", 1)[0] + "/" + PDF, pdf)
        return out

    def builds(self) -> dict[str, Path]:
        """Each paper's current PDF, by the site path it is published at."""
        return dict(self.paper_builds().values())

    def site_data(self) -> dict:
        """What the shell needs beyond `.folio/`: the charter's home maps, kinds and dates."""
        lib = self.lib
        known = {f.path for f in lib.files}
        return {
            "name": lib.charter.name,
            "purpose": lib.charter.purpose,
            "home": {"maps": list(lib.charter.home_maps)},
            "journal": {"kinds": lib.journal_kinds(), "url": url_of(JOURNAL_VIEW)},
            "dates": {p: d for p, d in sorted(self.dates().items()) if p in known},
            "frozen": self.frozen(),
            "builds": {key: url_of(path) for key, (path, _) in sorted(self.paper_builds().items())},
            "live": self.live,
            "review": {"url": url_of(REVIEW_VIEW)},
            "comments": self.comments,
        }

    # -- paths -------------------------------------------------------------

    def paths(self) -> Iterator[str]:
        """Every path the exported site holds, from its root."""
        lib = self.lib
        moved = redirects(lib)
        builds = self.builds()
        yield "index.html"
        yield ".nojekyll"
        for folder in COPIED:
            top = lib.root / folder
            if not top.is_dir():
                continue
            for path in sorted(top.rglob("*")):
                rel = path.relative_to(lib.root).as_posix()
                if not path.is_file() or any(p.startswith(".") for p in path.relative_to(lib.root).parts):
                    continue
                if rel.endswith(".annotations.json"):
                    continue  # comments stay in the library, never on a published site
                if rel.startswith("content/") and path.name.startswith("original."):
                    continue  # a source's kept original is a private copy: `folio serve` shows it, export never
                if rel in moved or rel in builds:
                    continue
                yield _served(rel) if rel in lib.by_path else rel
        yield from sorted(builds)
        yield JOURNAL_VIEW  # the review page is not exported: an exported site carries no comments
        for name in sorted(p.name for p in (lib.root / INDEX_DIR).glob("*.json")):
            if name != "redirects.json":
                yield f"{INDEX_DIR}/{name}"
        yield SITE_DATA
        for path in sorted(shell_dir(lib).rglob("*")):
            if path.is_file() and path.suffix != ".md":
                yield "shell/" + path.relative_to(shell_dir(lib)).as_posix()
        for old in sorted(moved):
            yield _served(old)

    def get(self, path: str) -> Response | None:
        """The content at a site path (no leading `/`), or None when nothing is there."""
        lib = self.lib
        path = path.lstrip("/")
        if path in ("", "index.html"):
            return self._html(render.redirect(self.base + "content/"))
        if path == ".nojekyll":
            return Response(b"", "text/plain")
        if path.endswith("/"):
            path += "index.html"
        elif path.split("/", 1)[0] in COPIED and (lib.root / path).is_dir():
            return Response(b"", "text/html", 301, self.base + path + "/")
        moved = self._moved(path)
        if moved is not None:
            return moved
        if path == JOURNAL_VIEW and JOURNAL_VIEW not in lib.by_path:
            return self._page(JOURNAL_VIEW, render.view(
                "Journal", "journal", "What happened and what was decided, newest first."))
        if path == REVIEW_VIEW and REVIEW_VIEW not in lib.by_path:
            return self._page(REVIEW_VIEW, render.view(
                "Review", "review", "Questions waiting on the agent and flags resting for you, newest first."))
        if path == SITE_DATA:
            return Response(json.dumps(self.site_data(), indent=1).encode(), _type(path))
        if path.startswith("shell/"):
            return self._file(shell_dir(lib) / path[len("shell/"):], path)
        if path.startswith(INDEX_DIR + "/") and path.endswith(".json") and path != redirects_mod.FILE:
            return self._file(lib.root / path, path)
        if path.split("/", 1)[0] not in COPIED or path.endswith(".annotations.json"):
            return None
        if path.endswith(".html"):
            record = path[: -len(".html")] + ".md"
            df = lib.by_path.get(record)
            if df is not None and df.format == "markdown":
                return self._page(record, render.record(lib, record))
            df = lib.by_path.get(path)
            if df is not None and df.format == "html":
                text = render.with_shell(df.abspath.read_text(encoding="utf-8"))
                if df.doc is not None and df.doc.is_home:
                    text = render.with_title(text, lib.charter.name)
                return self._page(path, text)
        if path.endswith(".md") and path in lib.by_path:
            return Response(b"", "text/html", 301, self.base + _served(path))
        build = self.builds().get(path)
        if build is not None:
            return self._file(build, path)
        return self._file(lib.root / path, path)

    def _moved(self, path: str) -> Response | None:
        for old, new in redirects(self.lib).items():
            if _served(old) == path:
                target = url_of(_served(new))
                return self._html(render.redirect(self.base.rstrip("/") + target))
        return None

    def _page(self, source: str, text: str) -> Response:
        return self._html(render.rewrite(self.lib, source, text, self.base))

    def _html(self, text: str) -> Response:
        return Response(text.encode("utf-8"), "text/html; charset=utf-8")

    def _file(self, abspath: Path, path: str) -> Response | None:
        if not abspath.is_file():
            return None
        return Response(abspath.read_bytes(), _type(path))


def export(root: Path, out: Path, base: str = "/") -> list[str]:
    """Write the static site into `out`; return the paths written."""
    return export_site(root, out, base)[0]


def export_site(root: Path, out: Path, base: str = "/") -> tuple[list[str], list[str]]:
    """Write the static site into `out`; return the paths written and, of them, the pages.

    A page is a document's file rendered as HTML, or a view such as the journal;
    the shell, the indices, assets and redirect stubs are not pages.
    """
    site = Site.load(root, base)
    out = out.resolve()
    lib_root = root.resolve()
    guarded = [lib_root / name for name in (*COPIED, INDEX_DIR)]
    if out == lib_root or any(out == g or g in out.parents for g in guarded):
        raise FolioError(f"--out {out} would write over the library; pick another folder, such as _site/")
    if out.exists() and any(out.iterdir()):
        if not (out / ".nojekyll").is_file():
            raise FolioError(f"--out {out} is not empty and holds no earlier export; pick an empty folder")
        shutil.rmtree(out)
    written: list[str] = []
    pages: list[str] = []
    documents = {_served(f.path) for f in site.lib.files if f.format != "latex"}
    for path in site.paths():
        response = site.get(path)
        if response is None:
            raise FolioError(f"export: nothing to write at {path}")
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.body)
        written.append(path)
        if path in documents or path == JOURNAL_VIEW:
            pages.append(path)
    return written, pages
