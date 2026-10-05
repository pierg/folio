"""The comment panel's link to the threads stored beside each document.

The served page reads and writes threads through local endpoints; this
module turns those requests into calls on `folio.annotations`. The
commenter comes from the server (see `identity`), never from the request,
and every write goes through a `Recorder`, which commits it.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .. import annotations
from ..errors import FolioError
from ..library import Library
from . import review
from .identity import Who
from .record import Recorder

KEPT = "Kept."
LIMITS = {"body": 8000, "quote": 2000, "label": 40}


def document_file(lib: Library, rel: str) -> str:
    """A document file under `content/`, from the path a page sends."""
    rel = str(rel or "").lstrip("/")
    parts = PurePosixPath(rel).parts
    if not rel or parts[0] != "content" or ".." in parts:
        raise FolioError(f"no document at {rel or '(none)'}")
    content = (lib.root / "content").resolve()
    if content not in (lib.root / rel).resolve().parents or rel not in lib.by_path:
        raise FolioError(f"no document at {rel}")
    return rel


def threads(lib: Library, rel: str) -> list[dict[str, Any]]:
    """Every thread on a document file, each with its plain words and, once addressed, what changed."""
    rel = document_file(lib, rel)
    out = []
    for t in annotations.load_threads(lib.root, rel):
        shown = {**t, **review.plain(t)}
        change = review.changed(lib, rel, t)
        if change is not None:
            shown["changed"] = change
        out.append(shown)
    return out


def _text(request: dict[str, Any], key: str) -> str:
    value = request.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise FolioError(f"`{key}` must be text")
    if len(value) > LIMITS[key]:
        raise FolioError(f"`{key}` is longer than {LIMITS[key]} characters")
    return value.strip()


def _thread(lib: Library, rel: str, thread_id: str) -> dict[str, Any]:
    for t in annotations.load_threads(lib.root, rel):
        if t.get("id") == thread_id:
            return t
    raise FolioError(f"{rel} has no thread `{thread_id}`")


def act(lib: Library, request: dict[str, Any], who: Who, recorder: Recorder) -> dict[str, Any]:
    """Open a thread, reply to one, or keep or change a resting flag. Returns the thread.

    Actions: `add` (kind, quote, body, label), `reply` (id, body, and
    `reopen` to open a closed thread again), `keep` (id: a resting flag
    closes as kept), `change` (id, body: a resting flag reopens as an open
    question carrying what to change).
    """
    if not isinstance(request, dict):
        raise FolioError("expected a JSON object")
    rel = document_file(lib, str(request.get("doc") or ""))
    df = lib.by_path[rel]
    doc_id = df.doc.id if df.doc is not None else rel
    sidecar = annotations.sidecar_path(rel)
    action = request.get("action")
    body = _text(request, "body")
    thread_id = str(request.get("id") or "")

    def save(write: Any) -> dict[str, Any]:
        return recorder.save(sidecar, who, doc_id, write)

    if action == "add":
        if not body:
            raise FolioError("a comment needs a body")
        kind = request.get("kind") or "question"
        if kind not in annotations.KINDS:
            raise FolioError(f"a thread is a flag or a question, not `{kind}`")
        quote = _text(request, "quote")  # empty: about the whole document
        label = _text(request, "label") or None
        return save(lambda: annotations.add(lib, rel, kind, quote, body, who.name, label=label))
    if action == "reply":
        if not body:
            raise FolioError("a reply needs a body")
        current = _thread(lib, rel, thread_id)
        state = None
        if request.get("reopen"):
            if current.get("state") in annotations.UNSETTLED:
                raise FolioError(f"thread {thread_id} is not closed")
            state = "open"
        return save(lambda: annotations.reply(lib, rel, thread_id, body, who.name, state=state))
    if action in ("keep", "change"):
        current = _thread(lib, rel, thread_id)
        if current.get("kind") != "flag" or current.get("state") != "noted":
            raise FolioError(f"thread {thread_id} is not a resting flag")
        if action == "keep":
            return save(lambda: annotations.reply(lib, rel, thread_id, KEPT, who.name, state="addressed"))
        if not body:
            raise FolioError("say what to change")
        return save(lambda: annotations.reply(lib, rel, thread_id, body, who.name, state="open"))
    raise FolioError(f"unknown comment action `{action}`")
