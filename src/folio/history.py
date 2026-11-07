"""Read a library's git history: the versions of a file, its dates, and deleted record ids.

Every function takes paths relative to the library root. The working tree
counts as the newest version: an uncommitted change is a change. A library
outside a git work tree, or on a machine without git, has no history; callers
ask `in_git` first.
"""

from __future__ import annotations

import datetime as _dt
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


def baseline(lib: "Library") -> str:
    """The charter's `baseline` commit, checked to be in this history; empty when the charter names none.

    The lifecycle checks read history from it on: its tree is every file's first version.
    """
    commit = lib.charter.baseline
    if not commit or not _has_head(lib):
        return ""
    if "history.baseline" not in lib.cache:
        if _git(lib, "merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode != 0:
            raise FolioError(f"folio.yaml: `baseline` {commit[:7]} is not a commit in this branch's history "
                             "(a shallow clone needs the full history: fetch-depth 0)")
        lib.cache["history.baseline"] = _dt.date.fromisoformat(
            _git(lib, "show", "-s", "--format=%cs", commit).stdout.strip())
    return commit


def commits(lib: "Library", paths: list[str], checked: bool = False) -> list[tuple[str, _dt.date]]:
    """The commits that touched any of these paths, oldest first, with their dates.

    `checked`: as the lifecycle checks read history. With a charter `baseline`, the baseline commit comes
    first when any of the paths exists in its tree, then only the commits after it.
    """
    if not _has_head(lib):
        return []
    base = baseline(lib) if checked else ""
    span = [f"{base}..HEAD"] if base else []
    out = _git(lib, "log", "--format=%H %cs", *span, "--", *paths).stdout.split()
    pairs = list(reversed([(out[i], _dt.date.fromisoformat(out[i + 1])) for i in range(0, len(out), 2)]))
    if base and any(_git(lib, "cat-file", "-e", f"{base}:./{p}", check=False).returncode == 0 for p in paths):
        pairs.insert(0, (base, lib.cache["history.baseline"]))
    return pairs


def show(lib: "Library", commit: str, path: str) -> str | None:
    """A file's text at a commit, or None when it did not exist there."""
    result = _git(lib, "show", f"{commit}:./{path}", check=False)
    return result.stdout if result.returncode == 0 else None


def _working(lib: "Library", path: str) -> str | None:
    target = lib.root / path
    return target.read_text(encoding="utf-8") if target.is_file() else None


def versions(lib: "Library", paths: list[str], checked: bool = False) -> list[Version]:
    """Every committed version of these files, oldest first, then the working tree if it differs.

    `checked`: from the charter's `baseline` on, as `commits` reads it.
    """
    out = [Version(sha, day, {p: show(lib, sha, p) for p in paths})
           for sha, day in commits(lib, paths, checked)]
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


def deleted(lib: "Library", under: str = "content", checked: bool = False) -> list[tuple[str, str]]:
    """Files deleted from history under a folder, as (path, deleting commit), oldest first.

    `checked`: only deletions after the charter's `baseline`.
    """
    if not in_git(lib) or not _has_head(lib):
        return []
    base = baseline(lib) if checked else ""
    span = [f"{base}..HEAD"] if base else []
    text = _git(lib, "log", "--diff-filter=D", "--name-only", "--relative", "--format=@%H",
                *span, "--", under).stdout
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
