"""`folio paper build`, `freeze` and `versions`: compile a paper, and keep snapshots of it.

The source, `main.tex`, is revised for as long as the paper lives. A build
compiles it in `.folio/build/<slug>/`, which git ignores. A freeze builds it,
then copies the source and the PDF into `versions/<name>/`, a part of the
paper the gate keeps permanent once committed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import history, paths
from .commands.create import tex_escape
from .documents import DocFile, Document
from .edits import find_doc
from .errors import FolioError
from .indexer import INDEX_DIR, paper_versions
from .library import Library
from .util import is_slug

BUILD_DIR = f"{INDEX_DIR}/build"
CITES_FILE = "folio-cites.tex"
STY = Path(__file__).resolve().parent / "latex" / "folio.sty"
PDF = "paper.pdf"
_USES_FOLIO_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\bfolio\b[^}]*\}")
_LOG_ERROR_RE = re.compile(r"^(?:!|.*:\d+: )(.*)$")


@dataclass
class Build:
    pdf: Path  # the PDF, absolute
    rel: str  # the PDF, from the library root


def paper(lib: Library, ref: str) -> Document:
    doc = find_doc(lib, ref, genre="paper")
    if not doc.is_a("paper"):
        raise FolioError(f"`{ref}` is a {doc.genre_name}, not a paper")
    if doc.main is None or doc.main.latex is None:
        raise FolioError(f"{doc.key}: the paper has no LaTeX source")
    return doc


def slug_of(doc: Document) -> str:
    """The paper's folder name, which names its build folder."""
    return PurePosixPath(doc.key).parent.name


def build_dir(lib: Library, doc: Document) -> Path:
    return lib.root / BUILD_DIR / slug_of(doc)


def current_pdf(lib: Library, doc: Document) -> Path | None:
    """The PDF of the paper's last build, when there is one."""
    pdf = build_dir(lib, doc) / "main.pdf"
    return pdf if pdf.is_file() else None


def _cites_file(lib: Library, df: DocFile) -> str:
    """One `\\foliocite{id}{title}{address}` per cited id; an id that names no document fails the build."""
    lines = ["% Written by `folio paper build`. Do not edit.\n"]
    seen: set[str] = set()
    missing = []
    for link in lib.links.get(df.path, []):
        if link.kind != "fcite" or link.raw in seen:
            continue
        seen.add(link.raw)
        if not link.docs:
            missing.append(f"\\fcite{{{link.raw}}} names no document")
            continue
        target = link.docs[0]
        address = ""
        if lib.charter.site_url:
            address = lib.charter.site_url + served_url(target)
        lines.append("\\foliocite{%s}{%s}{%s}\n" % (link.raw, tex_escape(target.title), _url_escape(address)))
    if missing:
        raise FolioError(f"{df.path}: " + "; ".join(missing) + "; `folio cite <id>` finds a document's id")
    return "".join(lines)


def served_url(doc: Document) -> str:
    """Where the exported site serves a document: a Markdown record at its `.html` page."""
    path = doc.address_file.path
    if path.endswith(".md"):
        path = path[: -len(".md")] + ".html"
    return "/" + (path[: -len("index.html")] if path.endswith("/index.html") else path)


def _url_escape(url: str) -> str:
    return url.replace("\\", "/").replace("%", "\\%").replace("#", "\\#").replace("{", "%7B").replace("}", "%7D")


def _path_var(name: str, *folders: Path) -> str:
    """A TeX search path: these folders first, then the default (the trailing separator)."""
    parts = [str(f) for f in folders]
    existing = os.environ.get(name)
    return os.pathsep.join(parts + ([existing] if existing else [""]))


def _first_error(log: Path) -> str:
    """The first error in a TeX log, its wrapped lines joined."""
    if not log.is_file():
        return "latexmk wrote no log"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        match = _LOG_ERROR_RE.match(line)
        if not match or not match.group(1).strip():
            continue
        text = match.group(1).strip()
        for more in lines[i + 1:i + 4]:
            if not more.strip() or more.startswith((" ==>", "l.", "!")):
                break
            text += more.strip() if len(line) >= 79 else " " + more.strip()
            line = more
        return text
    return "see the log"


def build(lib: Library, ref: str) -> Build:
    """Compile a paper in `.folio/build/<slug>/` and return its PDF."""
    doc = paper(lib, ref)
    main = doc.main
    assert main is not None and main.latex is not None
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        raise FolioError("`folio paper build` needs latexmk, which is not installed; install a TeX "
                         "distribution that includes it, such as TeX Live, and build again")
    if not _USES_FOLIO_RE.search(main.latex):
        raise FolioError(f"{main.path} does not load folio.sty, so its \\fcite would not link; add "
                         "`\\IfFileExists{folio.sty}{\\usepackage{folio}}{\\providecommand{\\fcite}[1]"
                         "{\\texttt{#1}}}` after hyperref, as the paper skeleton does")
    cites = _cites_file(lib, main)
    out = build_dir(lib, doc)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STY, out / STY.name)
    (out / CITES_FILE).write_text(cites, encoding="utf-8")
    assets = lib.assets_dir()
    source = main.abspath.parent
    env = dict(os.environ)
    env["TEXINPUTS"] = _path_var("TEXINPUTS", out, source, assets / "figures")
    env["BIBINPUTS"] = _path_var("BIBINPUTS", assets, source)
    # It runs in the build folder, which sits as deep below the library as the paper's own
    # folder, so the source's relative paths to assets/ resolve the same from either.
    command = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
               "-jobname=main", str(main.abspath)]
    try:
        result = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True, timeout=600,
                                check=False)
    except subprocess.TimeoutExpired as exc:
        raise FolioError(f"{main.path}: latexmk ran for more than ten minutes and was stopped") from exc
    log = out / "main.log"
    pdf = out / "main.pdf"
    if result.returncode != 0 or not pdf.is_file():
        raise FolioError(f"{main.path} did not compile: {_first_error(log)}; the full log is "
                         f"{log.relative_to(lib.root).as_posix()}")
    return Build(pdf, pdf.relative_to(lib.root).as_posix())


def freeze(lib: Library, ref: str, version: str) -> list[str]:
    """Build the paper, then copy its source and PDF into `versions/<version>/`."""
    doc = paper(lib, ref)
    if not version or not is_slug(version):
        raise FolioError(f"a version name is lowercase letters and numbers joined by hyphens, such as "
                         f"`v1` or `camera-ready`, not `{version}`")
    genre = doc.genre
    assert genre is not None and doc.main is not None
    spec = next((p for p in genre.parts.values() if p.lives == "permanent"), None)
    if spec is None:
        raise FolioError(f"genre `{genre.name}` declares no permanent part to hold a version")
    values = dict(doc.main.captures)
    values["name"] = version
    rel = paths.fill(spec.path, values)
    folder = (lib.root / rel).parent
    taken = [v["name"] for v in paper_versions(lib, doc)]
    if version in taken or folder.exists():
        raise FolioError(f"version `{version}` of {doc.id} already exists at "
                         f"{folder.relative_to(lib.root).as_posix()}/; a version is never replaced, "
                         "so freeze under a new name")
    built = build(lib, ref)
    folder.mkdir(parents=True)
    shutil.copyfile(doc.main.abspath, lib.root / rel)
    shutil.copyfile(built.pdf, folder / PDF)
    return [f"built {built.rel}", f"created {rel}", f"created {(folder / PDF).relative_to(lib.root).as_posix()}"]


def versions(lib: Library, ref: str) -> list[dict[str, str]]:
    """A paper's versions: name, the date of the commit that froze it (or `uncommitted`), folder."""
    doc = paper(lib, ref)
    out = []
    for v in paper_versions(lib, doc):
        found = history.commits(lib, [v["path"]]) if history.in_git(lib) else []
        out.append({"name": v["name"], "date": found[0][1].isoformat() if found else "uncommitted",
                    "path": v["path"].rsplit("/", 1)[0] + "/", "pdf": v["pdf"] or ""})
    return out
