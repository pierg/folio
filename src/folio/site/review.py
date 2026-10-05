"""What the shell shows about comments: plain words, the review inbox, and what changed.

The file format and the command line keep the five thread states. Readers
see three words: `waiting` (open: the agent owes an answer), `resting`
(noted: a flag the owner may keep or change) and `closed` (addressed,
declined or withdrawn), with how it closed: changed, kept, declined or
withdrawn. A thread addressed straight from rest was kept; one addressed
after it was open was changed.
"""

from __future__ import annotations

import difflib
import html as _html
import json
import re
from typing import TYPE_CHECKING, Any

from .. import annotations as ann
from .. import history
from ..documents import url_of
from ..frontmatter import split

if TYPE_CHECKING:
    from ..library import Library

WORDS = {"open": "waiting", "noted": "resting"}
CONTEXT = 12  # words of unchanged text shown around a change


def _from_state(thread: dict[str, Any], upto: int) -> str:
    """The thread's state just before message `upto`."""
    state = "noted" if thread.get("kind") == "flag" else "open"
    for m in (thread.get("messages") or [])[1:upto]:
        if m.get("state"):
            state = m["state"]
    return state


def _closing(thread: dict[str, Any]) -> int | None:
    """The index of the message that moved the thread to its current, closed state."""
    messages = thread.get("messages") or []
    for i in range(len(messages) - 1, 0, -1):
        if messages[i].get("state") == thread.get("state"):
            return i
    return None


def _opening(thread: dict[str, Any], before: int) -> int:
    """The message that opened the thread, or that last reopened it before message `before`."""
    messages = thread.get("messages") or []
    for i in range(min(before, len(messages)) - 1, 0, -1):
        if messages[i].get("state") == "open":
            return i
    return 0


def plain(thread: dict[str, Any]) -> dict[str, str | None]:
    """A thread's state in a reader's words, and how a closed one closed."""
    state = str(thread.get("state"))
    if state in WORDS:
        return {"word": WORDS[state], "how": None}
    how = state
    if state == "addressed":
        i = _closing(thread)
        how = "kept" if i is not None and _from_state(thread, i) == "noted" else "changed"
    return {"word": "closed", "how": how}


def inbox(lib: "Library") -> dict[str, Any]:
    """Every question waiting on the agent and every flag resting for the owner, newest first."""
    rows = []
    for rel, t in ann.all_threads(lib):
        if t.get("state") not in ann.UNSETTLED:
            continue
        df = lib.by_path.get(rel)
        doc = df.doc if df is not None else None
        messages = t.get("messages") or []
        last = messages[-1] if messages else {}
        rows.append({
            "doc": doc.id if doc is not None else None,
            "title": (doc.title if doc is not None else "") or rel,
            "genre": doc.genre_name if doc is not None else None,
            "path": rel, "url": url_of(rel[:-3] + ".html" if rel.endswith(".md") else rel),
            "id": t.get("id"), "kind": t.get("kind"), "label": t.get("label"),
            "state": t.get("state"), **plain(t), "quote": t.get("quote") or "",
            "author": t.get("author"), "created": t.get("created"),
            "last": {"author": last.get("author"), "date": last.get("date"), "body": last.get("body")},
            "_order": (str(last.get("date") or t.get("created") or ""), int(_num(t.get("id")))),
        })
    rows.sort(key=lambda r: r["_order"], reverse=True)
    for r in rows:
        del r["_order"]
    return {
        "waiting": sum(1 for r in rows if r["state"] == "open"),
        "resting": sum(1 for r in rows if r["state"] == "noted"),
        "threads": rows,
    }


def _num(ident: object) -> int:
    digits = re.sub(r"\D", "", str(ident or ""))
    return int(digits) if digits else 0


# -- what changed -------------------------------------------------------------

_BLOCK = re.compile(r"</?(?:p|div|li|ul|ol|h[1-6]|br|hr|blockquote|pre|table|tr|td|th|details|summary|section|"
                    r"figure|figcaption|dl|dt|dd|main|article|aside)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
_DROP = re.compile(r"<(script|style|head)\b.*?</\1>", re.S | re.I)


def plain_text(path: str, text: str) -> list[str]:
    """A document file's reading text as words: the body of a page, without markup."""
    if path.endswith(".md"):
        _, body = split(text, path)
        return body.split()
    main = re.search(r"<main\b[^>]*>(.*)</main>", text, re.S | re.I)
    body = main.group(1) if main else _DROP.sub(" ", text)
    return _html.unescape(_TAG.sub("", _BLOCK.sub(" ", body))).split()


def _sidecar_states(lib: "Library", sidecar: str) -> list[tuple[str, list[dict[str, Any]]]]:
    """Each commit that touched the annotation file, oldest first, with its threads then."""
    out = []
    for commit, _ in history.commits(lib, [sidecar]):
        text = history.show(lib, commit, sidecar)
        try:
            threads = json.loads(text)["threads"] if text else []
        except (ValueError, KeyError, TypeError):
            threads = []
        out.append((commit, threads))
    return out


def _first_with(states: list[tuple[str, list[dict[str, Any]]]], thread_id: str, count: int) -> str | None:
    """The first commit where the thread holds at least `count` messages."""
    for commit, threads in states:
        for t in threads:
            if t.get("id") == thread_id and len(t.get("messages") or []) >= count:
                return commit
    return None


def _window(words: list[str], start: int, end: int) -> dict[str, str]:
    """The changed words, with a few unchanged words on each side."""
    a, b = max(0, start - CONTEXT), min(len(words), end + CONTEXT)
    return {"lead": ("… " if a > 0 else "") + " ".join(words[a:start]),
            "text": " ".join(words[start:end]),
            "tail": " ".join(words[end:b]) + (" …" if b < len(words) else "")}


def changed(lib: "Library", rel: str, thread: dict[str, Any]) -> dict[str, Any] | None:
    """The passage before and after the agent addressed a thread, from git; None when not known.

    Before is the document as of the commit that opened (or last reopened)
    the thread; after is the document as of the commit that recorded the
    addressing reply. Without that history, or without a change, None.
    Each side holds the changed words (`text`) and a few unchanged words
    around them (`lead`, `tail`), from the change nearest the quote.
    """
    if thread.get("state") != "addressed" or not history.in_git(lib):
        return None
    closing = _closing(thread)
    if closing is None:
        return None
    opening = _opening(thread, closing)
    states = _sidecar_states(lib, ann.sidecar_path(rel))
    thread_id = str(thread.get("id"))
    start = _first_with(states, thread_id, opening + 1)
    end = _first_with(states, thread_id, closing + 1)
    if start is None or end is None or start == end:
        return None
    old_text, new_text = history.show(lib, start, rel), history.show(lib, end, rel)
    if old_text is None or new_text is None:
        return None
    old, new = plain_text(rel, old_text), plain_text(rel, new_text)
    hunks = _hunks(old, new)
    if not hunks:
        return None
    quote = str(thread.get("quote") or "").split()
    at = _find(old, quote)
    near = min(hunks, key=lambda h: 0 if at is None else _distance(h[1], h[2], at, at + len(quote)))
    i1, i2, j1, j2 = near[1], near[2], near[3], near[4]
    return {"before": _window(old, i1, i2), "after": _window(new, j1, j2),
            "from": start[:7], "to": end[:7]}


def _hunks(old: list[str], new: list[str]) -> list[tuple[str, int, int, int, int]]:
    """The changed spans, with spans fewer than four unchanged words apart joined into one."""
    out: list[tuple[str, int, int, int, int]] = []
    for op in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if op[0] == "equal":
            continue
        if out and op[1] - out[-1][2] < 4:
            out[-1] = ("replace", out[-1][1], op[2], out[-1][3], op[4])
        else:
            out.append(op)
    return out


def _bare(word: str) -> str:
    return word.strip(".,;:!?\"'()[]“”‘’").lower()


def _find(words: list[str], quote: list[str]) -> int | None:
    """Where the quoted words start, punctuation at word edges aside."""
    if not quote:
        return None
    n = len(quote)
    want = [_bare(w) for w in quote]
    for i in range(len(words) - n + 1):
        if [_bare(w) for w in words[i:i + n]] == want:
            return i
    return None


def _distance(a1: int, a2: int, b1: int, b2: int) -> int:
    if a2 < b1:
        return b1 - a2
    if b2 < a1:
        return a1 - b2
    return 0
