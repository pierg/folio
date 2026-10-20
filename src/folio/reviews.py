"""The To review list (model §12): documents that changed after their owner last read them.

Each document keeps its review marks in its address file's annotation file, under `review`:
`changed` marks (a new document, or a substantive revision, with a line saying what changed)
and `reviewed` marks (the owner has read it). Marks are only ever added. A document is to
review while its latest mark is `changed` and it is not retired. The served Review page,
`folio review` and `folio save` (under `save.review: after`) all read and write marks here,
and the marks travel with the document's comments: `folio save` records them, and the server
commits a `reviewed` mark the way it commits a comment.
"""

from __future__ import annotations

from typing import Any

from . import annotations as ann
from .documents import Document, url_of
from .edits import find_doc
from .errors import FolioError
from .library import Library

NEW = "new"  # the note on a new document's first `changed` mark


def reviewable(doc: Document) -> bool:
    """Whether a document goes on the list: any but the home page, a journal entry and a permanent record."""
    genre = doc.genre
    return genre is not None and not doc.is_home and genre.lives != "permanent" and not doc.misplaced


def marks(lib: Library, doc: Document) -> list[dict[str, Any]]:
    return ann.review_marks(lib.root, doc.address_file.path)


def pending(lib: Library, doc: Document) -> dict[str, Any] | None:
    """The `changed` mark that puts a document on the list, or None when it is not to review."""
    found = marks(lib, doc)
    if not found or doc.status == "retired":
        return None
    last = found[-1]
    return last if last.get("mark") == "changed" else None


def _row(doc: Document, mark: dict[str, Any], state: str) -> dict[str, Any]:
    rel = doc.address_file.path
    return {"doc": doc.id, "path": rel, "url": url_of(rel[:-3] + ".html" if rel.endswith(".md") else rel),
            "title": doc.title or doc.id, "genre": doc.genre_name, "status": doc.status, "state": state,
            "date": mark.get("date"), "note": mark.get("note"), "author": mark.get("author")}


def to_review(lib: Library, every: bool = False) -> list[dict[str, Any]]:
    """The documents to review, newest change first. With `every`, also those reviewed since."""
    rows = []
    for order, doc in enumerate(lib.documents):
        found = marks(lib, doc)
        if not found:
            continue
        mark = pending(lib, doc)
        if mark is not None:
            rows.append((str(mark.get("date") or ""), order, _row(doc, mark, "to review")))
        elif every:
            rows.append((str(found[-1].get("date") or ""), order, _row(doc, found[-1], "reviewed")))
    rows.sort(key=lambda r: (r[0], -r[1]), reverse=True)
    return [r[2] for r in rows]


def changed(lib: Library, doc_ref: str, note: str, author: str) -> list[str]:
    """Put a document on the list, with a line saying what changed."""
    doc = find_doc(lib, doc_ref)
    if not reviewable(doc):
        raise FolioError(f"{doc.id} is a {doc.genre_name}{' (the home page)' if doc.is_home else ''}: "
                         "it does not go on the To review list")
    if not note.strip():
        raise FolioError("say what changed, in one line: --note \"..\"")
    ann.add_review_mark(lib.root, doc.address_file.path, "changed", author, note.strip())
    return [f"{doc.id} is on the To review list ({ann.sidecar_path(doc.address_file.path)})"]


def done(lib: Library, doc_ref: str, author: str) -> list[str]:
    """Take a document off the list: a `reviewed` mark, dated today."""
    doc = find_doc(lib, doc_ref)
    if pending(lib, doc) is None:
        raise FolioError(f"{doc.id} is not on the To review list; `folio review list` shows what is")
    ann.add_review_mark(lib.root, doc.address_file.path, "reviewed", author)
    return [f"{doc.id} reviewed ({ann.sidecar_path(doc.address_file.path)})"]


def mark_new(lib: Library, doc: Document, author: str) -> bool:
    """Put a new document on the list once: only when it carries no review mark yet."""
    if not reviewable(doc) or marks(lib, doc):
        return False
    ann.add_review_mark(lib.root, doc.address_file.path, "changed", author, NEW)
    return True
