"""Read a library's git history: the versions of a file, its dates, and deleted record ids.

Every function takes paths relative to the library root. The working tree
counts as the newest version: an uncommitted change is a change. A library
outside a git work tree, or on a machine without git, has no history; callers
ask `in_git` first.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import FolioError

if TYPE_CHECKING:
    from .library import Library

WORKING = "working tree"


@dataclass(frozen=True)
class Version:
    commit: str  # a commit hash, or WORKING
    date: _dt.date | None
    files: dict[str, str | None]  # path -> text at this version; None when absent

    @property
    def short(self) -> str:
        return self.commit if self.commit == WORKING else self.commit[:7]


def _git(lib: "Library", *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(lib.root), *args], capture_output=True, text=True,
                            check=False)
    if check and result.returncode != 0:
        raise FolioError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def in_git(lib: "Library") -> bool:
    """True when the library sits in a git work tree and git is installed."""
    if "history.in_git" not in lib.cache:
        ok = shutil.which("git") is not None and \
            _git(lib, "rev-parse", "--is-inside-work-tree", check=False).stdout.strip() == "true"
        lib.cache["history.in_git"] = ok
    return bool(lib.cache["history.in_git"])


def _has_head(lib: "Library") -> bool:
    if "history.head" not in lib.cache:
        lib.cache["history.head"] = _git(lib, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
    return bool(lib.cache["history.head"])


def commits(lib: "Library", paths: list[str]) -> list[tuple[str, _dt.date]]:
    """The commits that touched any of these paths, oldest first, with their dates."""
    if not _has_head(lib):
        return []
    out = _git(lib, "log", "--format=%H %cs", "--", *paths).stdout.split()
    pairs = [(out[i], _dt.date.fromisoformat(out[i + 1])) for i in range(0, len(out), 2)]
    return list(reversed(pairs))


def show(lib: "Library", commit: str, path: str) -> str | None:
    """A file's text at a commit, or None when it did not exist there."""
    result = _git(lib, "show", f"{commit}:./{path}", check=False)
    return result.stdout if result.returncode == 0 else None


def _working(lib: "Library", path: str) -> str | None:
    target = lib.root / path
    return target.read_text(encoding="utf-8") if target.is_file() else None


def versions(lib: "Library", paths: list[str]) -> list[Version]:
    """Every committed version of these files, oldest first, then the working tree if it differs."""
    out = [Version(sha, day, {p: show(lib, sha, p) for p in paths}) for sha, day in commits(lib, paths)]
    now = {p: _working(lib, p) for p in paths}
    if not out or out[-1].files != now:
        if out or any(v is not None for v in now.values()):
            out.append(Version(WORKING, None, now))
    return out


def dates(lib: "Library", path: str) -> tuple[_dt.date | None, _dt.date | None]:
    """(created, updated): the first and last commits that touched the file; None outside git."""
    if not in_git(lib):
        return None, None
    found = commits(lib, [path])
    if not found:
        return None, None
    return found[0][1], found[-1][1]


def deleted(lib: "Library", under: str = "content") -> list[tuple[str, str]]:
    """Files deleted from history under a folder, as (path, deleting commit), oldest first."""
    if not in_git(lib) or not _has_head(lib):
        return []
    text = _git(lib, "log", "--diff-filter=D", "--name-only", "--relative", "--format=@%H",
                "--", under).stdout
    out: list[tuple[str, str]] = []
    commit = ""
    for line in text.splitlines():
        if line.startswith("@"):
            commit = line[1:]
        elif line.strip():
            out.append((line.strip(), commit))
    return list(reversed(out))


def show_bytes(lib: "Library", commit: str, path: str) -> bytes | None:
    """A file's bytes at a commit, or None when it did not exist there. For files that are not text."""
    result = subprocess.run(["git", "-C", str(lib.root), "show", f"{commit}:./{path}"], capture_output=True,
                            check=False)
    return result.stdout if result.returncode == 0 else None


def tree(lib: "Library", commit: str, folder: str) -> list[str]:
    """The files under a folder at a commit, from the library root."""
    result = _git(lib, "ls-tree", "-r", "--name-only", "--full-name", commit, "--", folder, check=False)
    if result.returncode != 0:
        return []
    prefix = _git(lib, "rev-parse", "--show-prefix").stdout.strip()
    return sorted(p[len(prefix):] for p in result.stdout.splitlines() if p.startswith(prefix))


def _digest(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def baseline(lib: "Library") -> dict[str, str]:
    """The files the charter's `baseline` lists, each with the sha256 of the bytes it was last rewritten to
    on the record; empty when the charter names none (model §10).

    The file's lines are only ever added: a line changed or removed since any committed version of the file
    is an error, so a listed text cannot be swapped silently for a later edit. A path listed twice takes the
    later line, a second rewrite on the record.
    """
    if "history.baseline" in lib.cache:
        return lib.cache["history.baseline"]
    found: dict[str, str] = {}
    name = lib.charter.baseline
    if name:
        path = lib.charter.library / name
        rel = path.relative_to(lib.root).as_posix()
        if not path.is_file():
            raise FolioError(f"folio.yaml: `baseline` names {name}, which does not exist")
        text = path.read_text(encoding="utf-8")
        lines = _baseline_lines(text, name)
        if in_git(lib):
            charter = lib.charter.path.relative_to(lib.root).as_posix()
            for sha, _ in commits(lib, [charter]):
                named = re.search(r"(?m)^baseline:\s*(\S+)", show(lib, sha, charter) or "")
                if named and named.group(1).strip("'\"") != name:
                    raise FolioError(f"folio.yaml: `baseline` named {named.group(1)} in {sha[:7]}; once set, it "
                                     "names the same file for good")
            for sha, _ in commits(lib, [rel]):
                before = show(lib, sha, rel)
                if before is not None and lines[:len(_baseline_lines(before, name))] != _baseline_lines(before, name):
                    raise FolioError(f"{name}: a line committed in {sha[:7]} was changed or removed; "
                                     "its lines are only ever added")
        for digest, listed in lines:
            found[listed] = digest
    lib.cache["history.baseline"] = found
    return found


def _baseline_lines(text: str, name: str) -> list[tuple[str, str]]:
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        digest, sep, rel = line.partition("  ")
        if not sep or not rel or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise FolioError(f"{name}:{number}: expected `<sha256 in lowercase hex>  <path from the library>`")
        out.append((digest, rel))
    return out


def listed_now(lib: "Library", path: str) -> bool | None:
    """For a file the baseline lists: whether its bytes now are the listed ones. None when it is not listed."""
    digest = baseline(lib).get(path)
    if digest is None:
        return None
    target = lib.root / path
    return _digest(target.read_bytes() if target.is_file() else None) == digest


def baseline_version(lib: "Library", found: list[Version], paths: list[str]) -> int | None:
    """The index of the newest version whose files all hold the bytes the baseline lists, when every one of
    the document's files is listed; None otherwise."""
    listed = baseline(lib)
    if not paths or any(p not in listed for p in paths):
        return None
    for i in range(len(found) - 1, -1, -1):
        version = found[i]
        ok = True
        for p in paths:
            if version.commit == WORKING:
                target = lib.root / p
                data = target.read_bytes() if target.is_file() else None
            else:
                data = show_bytes(lib, version.commit, p)
            if _digest(data) != listed[p]:
                ok = False
                break
        if ok:
            return i
    return None
