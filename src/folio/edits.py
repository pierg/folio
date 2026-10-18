"""Planned edits to library files: find a document, rewrite links to it, write it all at once.

The graph commands (`map`, `tags`, `mv`, `promote`, `rm`) plan every change
first and write only when the whole plan holds, so a refusal changes nothing.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .documents import Document
from .errors import FolioError
from .frontmatter import front_block
from .links import resolve_href

if TYPE_CHECKING:
    from .library import Library


def find_doc(lib: "Library", ref: str, genre: str | None = None) -> Document:
    """A document named by id, by path from the library root, or by its address.

    Ids are unique across the library (the gate's `unique-id`); while two
    documents still share one, `genre` picks among them.
    """
    docs = lib.by_id.get(ref, [])
    if len(docs) > 1 and genre is not None:
        docs = [d for d in docs if d.is_a(genre)] or docs
    if len(docs) == 1:
        return docs[0]
    if len(docs) > 1:
        raise FolioError(f"`{ref}` names {len(docs)} documents: "
                         + ", ".join(d.key for d in docs) + "; give its path instead")
    path = ref.lstrip("/")
    if path in lib.by_path and lib.by_path[path].doc is not None:
        return lib.by_path[path].doc  # type: ignore[return-value]
    target = resolve_href(lib.root, "content/index.html", "/" + path)
    if target is not None and target in lib.by_path and lib.by_path[target].doc is not None:
        return lib.by_path[target].doc  # type: ignore[return-value]
    raise FolioError(f"no document `{ref}`: give its id or its path")


def locked(doc: Document) -> str | None:
    """Why a document's file may not be edited, or None when it may."""
    genre = doc.genre
    if genre is None:
        return None
    if genre.lives == "permanent":
        return "permanent"
    if genre.lives == "frozen" and (doc.status in genre.frozen_in or doc.status in genre.frozen_exits):
        return f"frozen ({doc.status})"
    return None


def href_for(doc: Document) -> str:
    """The href a page uses to link a document: a Markdown record by its source path (model §4)."""
    return "/" + doc.key if doc.key.endswith(".md") else doc.url


def new_href(raw: str, from_path: str, new_target: str) -> str:
    """`raw` rewritten to land on `new_target`, keeping its style (absolute or relative) and fragment."""
    cut = min([i for i in (raw.find("#"), raw.find("?")) if i >= 0], default=len(raw))
    path, tail = raw[:cut], raw[cut:]
    served = new_target
    folder = new_target.endswith("index.html") and (new_target == "index.html" or new_target.endswith("/index.html")) \
        and not path.endswith("index.html")
    if folder:
        served = new_target[: -len("index.html")]
    elif path.endswith(".html") and new_target.endswith(".md"):
        served = new_target[:-3] + ".html"
    if path.startswith("/"):
        return "/" + served + tail
    rel = os.path.relpath(served or ".", os.path.dirname(from_path) or ".")
    if folder:
        rel = rel.rstrip("/") + "/"
    return rel + tail


def _href_patterns(raw: str) -> list[re.Pattern[str]]:
    q = re.escape(raw)
    return [
        re.compile(r"(\bhref\s*=\s*)(\")" + q + r"(\")"),
        re.compile(r"(\bhref\s*=\s*)(')" + q + r"(')"),
        re.compile(r"(\]\()()" + q + r"(\)|\s)"),
        re.compile(r"(^\[[^\]]+\]:\s*)()" + q + r"(\s|$)", re.M),
    ]


def replace_href(text: str, raw: str, new: str, where: str) -> str:
    """Replace every link whose href is exactly `raw`; fail loud when none is found."""
    count = 0
    for pattern in _href_patterns(raw):
        text, n = pattern.subn(lambda m: m.group(1) + m.group(2) + new + m.group(3), text)
        count += n
    if count == 0:
        raise FolioError(f"{where}: cannot find the link `{raw}` in the source to rewrite it")
    return text


def set_front(text: str, key: str, value: Any) -> str:
    """Set one front matter key, replacing a block list under it too."""
    span = front_block(text)
    if span is None:
        raise FolioError(f"cannot set `{key}`: the file has no front matter")
    start, end = span
    lines = text[start:end].splitlines(keepends=True)
    line = f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
    out: list[str] = []
    i, done = 0, False
    while i < len(lines):
        if not done and re.match(re.escape(key) + r":", lines[i]):
            out.append(line)
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t", "-")) and not lines[i].strip() == ""):
                i += 1
            done = True
            continue
        out.append(lines[i])
        i += 1
    if not done:
        out.append(line)
    return text[:start] + "".join(out) + text[end:]


@dataclass
class Plan:
    """Files to write and files to move, applied together."""

    lib: "Library"
    texts: dict[str, str] = field(default_factory=dict)  # path -> new text (path after moves)
    moves: dict[str, str] = field(default_factory=dict)  # old path -> new path, any file
    notes: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    staged: list[tuple[str, str]] = field(default_factory=list)  # renames `git mv` staged
    stage: bool = False  # also `git add` every tracked file the plan writes
    added: list[str] = field(default_factory=list)  # files `git add` staged

    def text(self, path: str) -> str:
        if path in self.texts:
            return self.texts[path]
        old = next((o for o, n in self.moves.items() if n == path), path)
        return (self.lib.root / old).read_text(encoding="utf-8")

    def write(self, path: str, text: str, what: str) -> None:
        if self.text(path) == text:
            return
        self.texts[path] = text
        self.changed.append(f"updated {path}: {what}")

    def apply(self) -> list[str]:
        root = self.lib.root
        for old, new in self.moves.items():
            if (root / new).exists():
                raise FolioError(f"{new} already exists")
        tracked = _git_tracked(root)
        for old, new in self.moves.items():
            (root / new).parent.mkdir(parents=True, exist_ok=True)
            if tracked is not None and old in tracked:
                _git(root, "mv", old, new)
                self.staged.append((old, new))
            else:
                os.replace(root / old, root / new)
            _prune(root / old)
        for path, text in self.texts.items():
            (root / path).write_text(text, encoding="utf-8")
        if self.stage and tracked is not None:
            back = {n: o for o, n in self.moves.items()}
            self.added = [p for p in self.texts if p in tracked or back.get(p, p) in tracked]
            if self.added:
                _git(root, "add", "--", *self.added)
        moved = [f"moved {o} -> {n}" for o, n in self.moves.items()]
        return moved + self.changed + self.notes


def _prune(path: Path) -> None:
    """Remove the folders a move emptied, up to `content/`."""
    folder = path.parent
    while folder.name != "content" and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def _git(root: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise FolioError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _git_tracked(root: Path) -> set[str] | None:
    """The library's files git tracks, relative to the library; None outside a work tree."""
    import shutil
    import subprocess

    if shutil.which("git") is None:
        return None
    result = subprocess.run(["git", "-C", str(root), "ls-files", "--full-name", "-z", "."],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    prefix = Path(os.path.relpath(root.resolve(), Path(top).resolve())).as_posix()
    out = set()
    for name in result.stdout.split("\0"):
        if not name:
            continue
        out.add(name if prefix == "." else os.path.relpath(name, prefix))
    return out
