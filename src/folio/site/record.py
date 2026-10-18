"""Saving a comment: write the page's annotation file, then commit it, and push when asked.

Each new thread, reply or deletion is one commit on the current branch
holding only that page's annotation file, authored as the commenter. With `push`, the
server pulls with rebase before it writes and pushes after it commits. When
any step fails, the local write is rolled back and the comment is refused:
a comment is saved and recorded, or the reader sees why it was not. Outside
git the file is written and nothing else.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, TypeVar

from ..errors import FolioError
from .identity import Who

T = TypeVar("T")


def in_git(root: Path) -> bool:
    if shutil.which("git") is None:
        return False
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"


class Recorder:
    """Writes and commits comments one at a time for one library."""

    def __init__(self, root: Path, push: bool = False) -> None:
        self.root = root
        self.git = in_git(root)
        if push and not self.git:
            raise FolioError("--push needs the library in a git repository; it is not in one")
        self.push = push
        self._lock = threading.Lock()

    def describe(self) -> str:
        """How comments are kept, for the server's startup line."""
        if not self.git:
            return "comments are saved to annotation files only: the library is not in git"
        if self.push:
            return "each comment is committed on the current branch and pushed"
        return "each comment is committed on the current branch"

    def _run(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True,
                              env=env, stdin=subprocess.DEVNULL)

    def _must(self, what: str, *args: str, env: dict[str, str] | None = None) -> str:
        result = self._run(*args, env=env)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise FolioError(f"{what} failed: {detail[-1] if detail else 'git exited ' + str(result.returncode)}")
        return result.stdout.strip()

    def _head(self) -> str | None:
        result = self._run("rev-parse", "--verify", "-q", "HEAD")
        return result.stdout.strip() if result.returncode == 0 else None

    def _env(self, who: Who) -> dict[str, str]:
        env = dict(os.environ)
        env.update({"GIT_AUTHOR_NAME": who.name, "GIT_AUTHOR_EMAIL": who.email})
        if not self._run("config", "user.name").stdout.strip():
            env.update({"GIT_COMMITTER_NAME": who.name, "GIT_COMMITTER_EMAIL": who.email})
        return env

    def _pull(self) -> None:
        result = self._run("pull", "--rebase", "--autostash", "--quiet")
        if result.returncode != 0:
            if (self.root / self._must("git rev-parse", "rev-parse", "--git-path", "rebase-merge")).exists() or \
                    (self.root / self._must("git rev-parse", "rev-parse", "--git-path", "rebase-apply")).exists():
                self._run("rebase", "--abort")
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise FolioError("the comment was not saved: pulling the latest version failed"
                             + (f" ({detail[-1]})" if detail else ""))

    def save(self, sidecar: str, who: Who, doc_id: str, write: Callable[[], T], message: str | None = None) -> T:
        """Run `write` (which writes `sidecar`) and record the result; undo it all on any failure."""
        with self._lock:
            if not self.git:
                return write()
            if self.push:
                self._pull()
            path = self.root / sidecar
            before = path.read_bytes() if path.is_file() else None
            head = self._head()
            committed = False
            try:
                result = write()
                self._must("git add", "add", "--", sidecar)
                self._must("git commit", "commit", "--quiet", "--only", "-m", message or f"Comment on {doc_id}",
                           "--", sidecar, env=self._env(who))
                committed = True
                if self.push:
                    self._must("git push", "push", "--quiet")
                return result
            except Exception as exc:
                self._undo(sidecar, before, head, committed)
                raise FolioError(f"the comment was not saved: {exc}") from exc

    def _undo(self, sidecar: str, before: bytes | None, head: str | None, committed: bool) -> None:
        """Put the branch, the index entry and the annotation file back as they were."""
        if committed:
            if head is not None:
                self._run("reset", "--soft", "--quiet", head)
            else:
                self._run("update-ref", "-d", "HEAD")
        if head is not None:
            self._run("reset", "--quiet", head, "--", sidecar)
        else:
            self._run("rm", "--cached", "--quiet", "--ignore-unmatch", "--", sidecar)
        path = self.root / sidecar
        if before is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(before)
