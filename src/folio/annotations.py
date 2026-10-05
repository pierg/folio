"""Comment threads on a document: flags an agent leaves and questions a reader asks.

Threads live in a sidecar file beside the document file they were left on,
`<stem>.annotations.json` (`content/notes/x.html` keeps its threads in
`content/notes/x.annotations.json`). Each file of a document, such as a
guide's chapter, has its own sidecar. The format:

    {
      "version": 1,
      "threads": [
        {
          "id": "a1",                      # unique within the sidecar, never reused
          "kind": "flag" | "question",
          "label": "example" | null,       # a flag's kind of addition; optional
          "quote": "the passage",          # the text the thread is anchored on; "" for the whole document
          "state": "open" | "noted" | "addressed" | "declined" | "withdrawn",
          "author": "who opened it",
          "created": "YYYY-MM-DD",
          "messages": [                    # the first is the opening body
            {"author": "..", "date": "YYYY-MM-DD", "body": "..", "state": null | "<state>"}
          ]
        }
      ]
    }

A message's `state` is the state it moved the thread to. A flag starts
`noted`, a question `open`. Nothing is deleted: threads and messages are
only added, and a thread only changes state.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from .errors import FolioError
from .util import today

if TYPE_CHECKING:
    from .documents import DocFile
    from .library import Library

SUFFIX = ".annotations.json"
STATES = ("open", "noted", "addressed", "declined", "withdrawn")
KINDS = ("flag", "question")
UNSETTLED = ("open", "noted")


def sidecar_path(rel: str) -> str:
    """The sidecar beside a document file, both relative to the library root."""
    p = PurePosixPath(rel)
    return str(p.with_name(p.stem + SUFFIX))


def sidecars(root: Path) -> list[str]:
    """Every sidecar under `content/`, relative to the library root."""
    content = root / "content"
    if not content.is_dir():
        return []
    return sorted(p.relative_to(root).as_posix() for p in content.rglob("*" + SUFFIX) if p.is_file())


def load_threads(root: Path, rel: str) -> list[dict[str, Any]]:
    """The threads on one document file; empty when it has no sidecar."""
    return _read(root, sidecar_path(rel))


def _read(root: Path, sidecar: str) -> list[dict[str, Any]]:
    path = root / sidecar
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FolioError(f"{sidecar}: not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("threads"), list):
        raise FolioError(f"{sidecar}: expected an object with a `threads` list")
    return data["threads"]


def _write(root: Path, rel: str, threads: list[dict[str, Any]]) -> str:
    sidecar = sidecar_path(rel)
    text = json.dumps({"version": 1, "threads": threads}, indent=2, ensure_ascii=False) + "\n"
    (root / sidecar).write_text(text, encoding="utf-8")
    return sidecar


def normalise(text: str) -> str:
    return " ".join(text.split())


def page_text(df: "DocFile") -> str:
    """The text a reader sees on the page, whitespace collapsed: title, description and body."""
    parts = [str(df.meta.get("title") or ""), str(df.meta.get("description") or "")]
    if df.body is not None:
        parts.append(df.body.text())
    elif df.latex is not None:
        parts.append(df.latex)
    else:
        parts.append(df.text)
    return normalise(" ".join(parts))


def resolve_file(lib: "Library", ref: str) -> "DocFile":
    """A document file from a path, an address, or a document's id (its address file)."""
    clean = ref.strip().lstrip("/")
    for candidate in (clean, clean.rstrip("/") + "/index.html", clean[:-5] + ".md" if clean.endswith(".html") else ""):
        if candidate in lib.by_path:
            return lib.by_path[candidate]
    docs = lib.find(ref.strip())
    if len(docs) == 1:
        return docs[0].address_file
    if len(docs) > 1:
        raise FolioError(f"`{ref}` names {len(docs)} documents; give its path")
    raise FolioError(f"`{ref}` names no document")


def _check_state(state: str) -> None:
    if state not in STATES:
        raise FolioError(f"state `{state}` is not one of {', '.join(STATES)}")


def add(lib: "Library", rel: str, kind: str, quote: str | None, body: str, author: str,
        label: str | None = None) -> dict[str, Any]:
    """Open a thread on a passage of a document file, or with no quote on the whole document.

    A quote must be on the page.
    """
    if kind not in KINDS:
        raise FolioError(f"kind `{kind}` is not one of {', '.join(KINDS)}")
    quote = quote or ""
    if not body.strip() or not author.strip():
        raise FolioError("a thread needs a body and an author")
    df = lib.by_path.get(rel)
    if df is None:
        raise FolioError(f"`{rel}` is not a document file")
    if normalise(quote) not in page_text(df):
        raise FolioError(f"the quote is not on {rel}: `{quote}`")
    threads = load_threads(lib.root, rel)
    used = {str(t.get("id")) for t in threads}
    n = len(threads) + 1
    while f"a{n}" in used:
        n += 1
    date = today().isoformat()
    thread = {
        "id": f"a{n}", "kind": kind, "label": label, "quote": normalise(quote),
        "state": "noted" if kind == "flag" else "open", "author": author, "created": date,
        "messages": [{"author": author, "date": date, "body": body, "state": None}],
    }
    threads.append(thread)
    _write(lib.root, rel, threads)
    return thread


def reply(lib: "Library", rel: str, thread_id: str, body: str, author: str,
          state: str | None = None) -> dict[str, Any]:
    """Add a reply to a thread, and move it to a new state when one is given."""
    if state is not None:
        _check_state(state)
    if not body.strip() or not author.strip():
        raise FolioError("a reply needs a body and an author")
    threads = load_threads(lib.root, rel)
    for thread in threads:
        if thread.get("id") == thread_id:
            thread.setdefault("messages", []).append(
                {"author": author, "date": today().isoformat(), "body": body, "state": state})
            if state is not None:
                thread["state"] = state
            _write(lib.root, rel, threads)
            return thread
    raise FolioError(f"{rel} has no thread `{thread_id}`")


def all_threads(lib: "Library") -> list[tuple[str, dict[str, Any]]]:
    """Every thread in the library, as (document file, thread)."""
    out = []
    for sidecar in sidecars(lib.root):
        p = PurePosixPath(sidecar)
        stem = p.name[: -len(SUFFIX)]
        owner = next((f.path for f in lib.files if PurePosixPath(f.path).parent == p.parent
                      and PurePosixPath(f.path).stem == stem), str(p.with_name(stem)))
        out.extend((owner, t) for t in _read(lib.root, sidecar))
    return out


def row(lib: "Library", rel: str, thread: dict[str, Any]) -> dict[str, Any]:
    """One thread as the stable `--json` row."""
    df = lib.by_path.get(rel)
    doc = df.doc if df is not None else None
    messages = thread.get("messages") or []
    last = messages[-1] if messages else {}
    return {
        "doc": doc.id if doc is not None else None, "path": rel, "id": thread.get("id"),
        "kind": thread.get("kind"), "label": thread.get("label"), "state": thread.get("state"),
        "quote": thread.get("quote"), "author": thread.get("author"), "created": thread.get("created"),
        "messages": len(messages), "last_author": last.get("author"), "last_date": last.get("date"),
    }


def resolve(lib: "Library", state: str, body: str, author: str, doc: str | None = None,
            label: str | None = None) -> list[tuple[str, dict[str, Any]]]:
    """Move every unsettled thread (open or noted) the filters select to one state, one reply each."""
    _check_state(state)
    rel = resolve_file(lib, doc).path if doc else None
    picked = [(r, t) for r, t in all_threads(lib)
              if t.get("state") in UNSETTLED and t.get("state") != state
              and (rel is None or r == rel) and (label is None or t.get("label") == label)]
    return [(r, reply(lib, r, str(t["id"]), body, author, state)) for r, t in picked]


def stale_quotes(lib: "Library") -> list[tuple[str, str]]:
    """Open questions whose quote is no longer on their document, and sidecars with no document."""
    out = []
    for sidecar in sidecars(lib.root):
        p = PurePosixPath(sidecar)
        stem = p.name[: -len(SUFFIX)]
        owner = next((f for f in lib.files if PurePosixPath(f.path).parent == p.parent
                      and PurePosixPath(f.path).stem == stem), None)
        threads = _read(lib.root, sidecar)
        if owner is None:
            if any(t.get("state") == "open" for t in threads):
                out.append((sidecar, "open threads on a document file that does not exist"))
            continue
        text = page_text(owner)
        for t in threads:
            quote = normalise(str(t.get("quote") or ""))
            if t.get("state") == "open" and quote and quote not in text:
                out.append((owner.path, f"open thread {t.get('id')} quotes text no longer on the page:"
                                        f" `{t.get('quote')}`"))
    return out
