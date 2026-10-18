"""The lifecycle checks, `permanent` and `frozen`, and record-id reuse (check `unique-id`), against git history.

The working tree is the newest version, so an uncommitted edit is an edit.
A file that was never committed has no history yet and is not flagged.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from .. import history, html
from ..documents import Document
from ..errors import FolioError
from ..frontmatter import split
from ..library import Library
from ..links import RECORD_ID_RE

Found = list[tuple[str, str]]

_META_STATUS_RE = re.compile(r"""[ \t]*<meta\s+name=["']status["'][^>]*>[ \t]*\n?""", re.I)
_MD_STATUS_RE = re.compile(r"^status:.*\n?", re.M)
_FRONT_RE = re.compile(r"\A(---\n.*?\n---\n)", re.S)


def status_of(text: str | None, path: str) -> str | None:
    """The status a version of a file writes; `live` when it writes none; None when absent."""
    if text is None:
        return None
    if path.endswith(".html"):
        value = html.metas(html.parse(text)).get("status")
    elif path.endswith(".md"):
        try:
            front, _ = split(text, path)
        except FolioError:  # a version with broken front matter writes no readable status
            front = None
        value = (front or {}).get("status")
    else:
        return None
    return str(value) if value else "live"


def without_status(text: str | None, path: str) -> str | None:
    """The file's text with its status field taken out, to compare the rest."""
    if text is None:
        return None
    if path.endswith(".html"):
        return _META_STATUS_RE.sub("", text)
    if path.endswith(".md"):
        match = _FRONT_RE.match(text)
        if match:
            return _MD_STATUS_RE.sub("", match.group(1)) + text[match.end():]
    return text


def permanent(lib: Library, doc: Document) -> Found:
    """Every file of the document matches its first committed version."""
    if not history.in_git(lib):
        return []
    out: Found = []
    for df in doc.files:
        found = history.commits(lib, [df.path])
        if not found:
            continue  # never committed: nothing is fixed yet
        first = found[0][0]
        if history.show(lib, first, df.path) != (df.abspath.read_text(encoding="utf-8")
                                                   if df.abspath.is_file() else None):
            out.append((df.path, f"a permanent document has changed since its first commit {first[:7]};"
                                 " restore it and record the change in a new document"))
    return out


def _part_folder(template: str, path: str) -> str | None:
    """The folder a part owns: its file's folder when the template names it per part (`.../{name}/x`)."""
    folder = template.rsplit("/", 1)[0]
    if "{name}" in folder or "{nn}" in folder:
        return path.rsplit("/", 1)[0]
    return None


def permanent_parts(lib: Library, doc: Document) -> Found:
    """Every part the card marks `lives: permanent` matches its first commit, and so does its folder.

    A part whose path gives it a folder of its own (a paper's `versions/<name>/`)
    owns every file there: none may change, appear or disappear after the
    commit that first added the part. Annotation files may change.
    """
    genre = doc.genre
    if genre is None or not history.in_git(lib):
        return []
    out: Found = []
    for df in doc.files:
        spec = genre.parts.get(df.part) if df.part is not None else None
        if spec is None or spec.lives != "permanent":
            continue
        found = history.commits(lib, [df.path])
        if not found:
            continue  # never committed: nothing is fixed yet
        first = found[0][0]
        folder = _part_folder(spec.path, df.path)
        if folder is None:
            files = [df.path]
        else:
            here = lib.root / folder
            now = [p.relative_to(lib.root).as_posix() for p in here.rglob("*") if p.is_file()] \
                if here.is_dir() else []
            files = sorted(set(history.tree(lib, first, folder)) | set(now))
        changed = []
        for path in files:
            if path.endswith(".annotations.json"):
                continue
            target = lib.root / path
            current = target.read_bytes() if target.is_file() else None
            if history.show_bytes(lib, first, path) != current:
                changed.append(path)
        if changed:
            where = f"{folder}/" if folder else df.path
            out.append((df.path, f"the permanent `{df.part}` part {where} has changed since its commit "
                                 f"{first[:7]} ({', '.join(changed)}); restore it, and make any change "
                                 "in the source or in a new part"))
    return out


def frozen(lib: Library, doc: Document) -> Found:
    """Once frozen, the document keeps the text of the first version that froze it, except its status.

    The versions are every commit touching any of its files, then the working
    tree. The first version whose status is in the card's `frozen_in` fixes
    the document for good: every later version must match it with the status
    field taken out. Its status may then only stay frozen or move forward to
    one of the card's `frozen_exits`, and an exit is never taken back.
    """
    genre = doc.genre
    mf = doc.meta_file
    if genre is None or mf is None or not history.in_git(lib):
        return []
    paths = [f.path for f in doc.files]
    found = history.versions(lib, paths)
    first = next((i for i, v in enumerate(found)
                  if status_of(v.files.get(mf.path), mf.path) in genre.frozen_in), None)
    if first is None:
        return []
    base_version = found[first]
    base_status = str(status_of(base_version.files.get(mf.path), mf.path))
    base = {p: without_status(t, p) for p, t in base_version.files.items()}
    out: Found = []
    allowed = [*genre.frozen_in, *genre.frozen_exits]
    exited: str | None = None
    for version in found[first + 1:]:
        state = status_of(version.files.get(mf.path), mf.path)
        if state in genre.frozen_exits and state not in genre.frozen_in and exited is None:
            exited = state
    now = found[-1]
    state = status_of(now.files.get(mf.path), mf.path)
    rest = {p: without_status(t, p) for p, t in now.files.items()}
    changed = sorted(p for p in paths if rest.get(p) != base.get(p))
    if changed:
        out.append((mf.path, f"changed since it was frozen (`{base_status}` in {base_version.short}): "
                             f"{', '.join(changed)}; only the status may change, so restore the text "
                             "and record the change in a new document"))
    if state not in allowed:
        exits = ", ".join(genre.frozen_exits) or "none"
        out.append((mf.path, f"status `{state}` after being frozen (`{base_status}` in "
                             f"{base_version.short}); a frozen document stays "
                             f"{' or '.join(genre.frozen_in)} or moves on to {exits}"))
    elif exited is not None and state not in genre.frozen_exits:
        out.append((mf.path, f"status went back to `{state}` after `{exited}`; leaving a frozen state "
                             "is never undone"))
    return out


def frozen_since(lib: Library, doc: Document) -> str | None:
    """The date (YYYY-MM-DD) of the commit that froze a document now in a `frozen_in` state, or None.

    None when the document is not frozen now, or its freezing is not committed yet.
    """
    genre = doc.genre
    mf = doc.meta_file
    if genre is None or mf is None or genre.lives != "frozen" or doc.status not in genre.frozen_in \
            or not history.in_git(lib):
        return None
    for version in history.versions(lib, [f.path for f in doc.files]):
        if version.commit == history.WORKING or version.date is None:
            continue
        if status_of(version.files.get(mf.path), mf.path) in genre.frozen_in:
            return version.date.isoformat()
    return None


def reused_ids(lib: Library) -> Found:
    """A record id held now by a document once held by a file that was deleted."""
    by_prefix = {g.prefix: g for g in lib.registry.genres.values() if g.prefix}
    out: Found = []
    for path, commit in history.deleted(lib):
        stem = PurePosixPath(path).stem
        match = RECORD_ID_RE.match(stem)
        if not match or match.group(1) not in by_prefix:
            continue
        for doc in lib.find(stem):
            if doc.genre is not None and doc.genre.prefix == match.group(1):
                out.append((doc.key, f"id `{stem}` was used by {path}, deleted in {commit[:7]};"
                                     " a record id is never reused"))
    return out
