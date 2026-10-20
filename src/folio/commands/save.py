"""`folio save`: record the library's content on its branch, checked, and push it.

Content is what the library holds: its documents and their annotation files under `content/`,
its assets, and the indices in `.folio/` regenerated from them. Everything else in the
repository (the charter, genres, workflows, skills, code) is a change to the library or the
project, made another way, and `save` leaves it alone and says so.

One save is one commit. It pulls the latest version first, so the commit sits on top of what
others pushed; it regenerates the indices and runs the gate, so nothing unchecked is recorded;
and when the push is refused because the branch moved meanwhile, it takes its commit back,
pulls, and tries again. Indices are regenerated, never merged: before each pull the local copy
of `.folio/` is put back as committed, and `folio index` writes it again afterwards.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .. import indexer
from .. import library as library_mod
from ..checks.run import run as run_checks
from ..errors import FolioError
from ..indexer import INDEX_DIR

ATTEMPTS = 4


@dataclass
class Saved:
    commit: str | None = None  # the commit's short id; None when there was nothing to save
    pushed: bool = False
    files: list[str] = field(default_factory=list)  # paths from the repository's root
    pages: list[tuple[str, str, str]] = field(default_factory=list)  # (id, status, address) of saved documents
    left: list[str] = field(default_factory=list)  # changed paths outside the library's content


class Git:
    def __init__(self, where: Path) -> None:
        self.where = where

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.where, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)

    def must(self, what: str, *args: str) -> str:
        result = self.run(*args)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise FolioError(f"{what} failed: {detail[-1] if detail else 'git exited ' + str(result.returncode)}")
        return result.stdout.strip()

    def ok(self, *args: str) -> bool:
        return self.run(*args).returncode == 0


def _scope(lib: library_mod.Library, top: Path) -> list[str]:
    """The library's content folders, as paths from the repository's root."""
    folders = [lib.root / "content", lib.assets_dir(), lib.root / INDEX_DIR]
    out = []
    for folder in folders:
        try:
            out.append(folder.resolve().relative_to(top).as_posix() or ".")
        except ValueError as exc:
            raise FolioError(f"{folder} is outside the repository at {top}") from exc
    return out


def _changed(git: Git, paths: list[str] | None = None) -> list[str]:
    """Paths with changes, staged or not, tracked or new."""
    args = ["status", "--porcelain", "-z", "--untracked-files=all"]
    if paths is not None:
        args += ["--", *paths]
    out = git.run(*args).stdout
    entries = [e for e in out.split("\0") if e]
    files: list[str] = []
    skip = False
    for entry in entries:
        if skip:
            skip = False
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            skip = True  # the next entry is the rename's old path
        files.append(path)
    return files


def _gate(lib: library_mod.Library) -> None:
    """The library's gate: its own command when the charter names one, else folio's checks."""
    command = lib.charter.save.gate
    if command:
        result = subprocess.run(shlex.split(command), cwd=lib.root, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            tail = (result.stdout + result.stderr).strip().splitlines()[-15:]
            raise FolioError(f"the gate `{command}` failed; nothing was saved:\n" + "\n".join(tail))
        return
    problems = [p for p in run_checks(lib) if p.severity == "error"]
    if problems:
        lines = "\n".join(p.line() for p in problems[:15])
        raise FolioError(f"folio check found {len(problems)} error(s); nothing was saved:\n{lines}")


def _pull(git: Git, index: str) -> None:
    """Bring the branch up to date with its upstream, keeping local edits; indices are rebuilt after."""
    git.run("checkout", "--", index)  # the local indices are regenerated, never merged
    git.run("clean", "-fdq", "--", index)
    result = git.run("pull", "--rebase", "--autostash", "--quiet")
    if result.returncode != 0:
        for marker in ("rebase-merge", "rebase-apply"):
            if (git.where / git.must("git rev-parse", "rev-parse", "--git-path", marker)).exists():
                git.run("rebase", "--abort")
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise FolioError("pulling the latest version failed; nothing was saved"
                         + (f" ({detail[-1]})" if detail else "")
                         + ". If a page you changed was also changed upstream, settle it by hand and save again.")
    if git.run("diff", "--name-only", "--diff-filter=U").stdout.strip():
        raise FolioError("your changes and the latest version touch the same lines; settle them by hand "
                         "(git status shows where) and save again")


def save(start: Path, message: str | None = None, push: bool = True) -> Saved:
    lib = library_mod.load(start)
    git = Git(lib.root)
    if not git.ok("rev-parse", "--is-inside-work-tree"):
        raise FolioError("folio save needs the library in a git repository; it is not in one")
    top = Path(git.must("git rev-parse", "rev-parse", "--show-toplevel")).resolve()
    git = Git(top)
    branch = git.run("symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if not branch:
        raise FolioError("folio save records on a branch; this checkout is not on one")
    upstream = git.run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip()
    if push and not upstream:
        raise FolioError(f"branch `{branch}` has no upstream to push to; use --no-push to commit only")
    scope = _scope(lib, top)
    index = scope[2]
    left = sorted(set(_changed(git)) - set(_changed(git, scope)))

    for attempt in range(1, ATTEMPTS + 1):
        if upstream:
            _pull(git, index)
        lib = library_mod.load(start)
        if lib.charter.save.review == "after":
            _mark_new(lib, git, top)
        indexer.write(lib)
        lib = library_mod.load(start)
        files = _changed(git, scope)
        if not files:
            return Saved(left=left)
        _gate(lib)
        git.must("git add", "add", "--all", "--", *scope)
        staged = [f for f in git.must("git diff", "diff", "--cached", "--name-only").splitlines() if f]
        if not staged:
            return Saved(left=left)
        pages = _pages(lib, top, staged)
        # Only the library's content: anything else staged in the repository stays staged, uncommitted.
        git.must("git commit", "commit", "--quiet", "-m", message or _message(pages, staged), "--", *scope)
        commit = git.must("git rev-parse", "rev-parse", "--short", "HEAD")
        if not push:
            return Saved(commit, False, staged, pages, left)
        if git.ok("push", "--quiet"):
            return Saved(commit, True, staged, pages, left)
        # The branch moved since the pull: take the commit back, keep the edits, and go again.
        git.must("git reset", "reset", "--soft", "--quiet", "HEAD~1")
        git.must("git reset", "reset", "--quiet", "--", *scope)
    raise FolioError(f"the branch kept moving: {ATTEMPTS} attempts to push were refused; nothing was pushed")


def _mark_new(lib: library_mod.Library, git: Git, top: Path) -> None:
    """Under `save.review: after`, put on the To review list each document recorded for the first time."""
    from .. import reviews
    from ..site.identity import local

    head = git.run("ls-tree", "-r", "-z", "--name-only", "HEAD")
    tracked = {p for p in head.stdout.split("\0") if p} if head.returncode == 0 else set()
    author = local(lib.root).name or "agent"
    for doc in lib.documents:
        try:
            rel = (lib.root / doc.key).resolve().relative_to(top).as_posix()
        except ValueError:
            continue
        if rel not in tracked:
            reviews.mark_new(lib, doc, author)


def _pages(lib: library_mod.Library, top: Path, staged: list[str]) -> list[tuple[str, str, str]]:
    """The documents a save touches: id, status and address (under the charter's `save.url`)."""
    base = lib.charter.save.url
    seen: dict[str, tuple[str, str, str]] = {}
    for path in staged:
        rel = (top / path).resolve()
        try:
            key = rel.relative_to(lib.root.resolve()).as_posix()
        except ValueError:
            continue
        if key.endswith(".annotations.json"):
            key = key[: -len(".annotations.json")]
            key = next((p for p in lib.by_path if p.rsplit(".", 1)[0] == key), key)
        df = lib.by_path.get(key)
        if df is None or df.doc is None or df.doc.id in seen:
            continue
        doc = df.doc
        seen[doc.id] = (doc.id, doc.status, (base + doc.url) if base else doc.url)
    return list(seen.values())


def _message(pages: list[tuple[str, str, str]], staged: list[str]) -> str:
    ids = [p[0] for p in pages]
    if not ids:
        return f"Update {len(staged)} file(s) in the library"
    if len(ids) <= 3:
        return "Update " + ", ".join(ids)
    return "Update " + ", ".join(ids[:3]) + f" and {len(ids) - 3} more"
