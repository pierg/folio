"""`folio tags [rename <old> <new>]`: the tags in use, and one renamed everywhere."""

from __future__ import annotations

from typing import Any

from ..documents import tags_of
from ..edits import Plan, locked, set_front
from ..errors import FolioError
from ..library import Library
from ..metaedit import set_html
from ..util import is_slug


def listing(lib: Library) -> list[dict[str, Any]]:
    counts: dict[str, list[str]] = {}
    for doc in lib.documents:
        for tag in dict.fromkeys(doc.tags):
            counts.setdefault(tag, []).append(doc.id)
    return [{"tag": t, "count": len(ids), "documents": sorted(ids)}
            for t, ids in sorted(counts.items(), key=lambda kv: (-len(kv[1]), kv[0]))]


def rename(lib: Library, old: str, new: str) -> list[str]:
    if not is_slug(new):
        raise FolioError(f"a tag is a lowercase slug, not `{new}`")
    if old == new:
        raise FolioError("the old and new tag are the same")
    plan = Plan(lib)
    found = False
    for doc in lib.documents:
        for df in doc.files:
            if not df.holds_metadata:
                continue
            tags = tags_of(df.meta)
            if old not in tags:
                continue
            found = True
            why = locked(doc)
            if why:
                plan.notes.append(f"left {df.path} ({why}): it keeps the tag `{old}`")
                continue
            renamed = list(dict.fromkeys(new if t == old else t for t in tags))
            text = plan.text(df.path)
            text = set_html(text, "tags", renamed) if df.format == "html" else set_front(text, "tags", renamed)
            plan.write(df.path, text, f"tag {old} -> {new}")
    if not found:
        raise FolioError(f"no document has the tag `{old}`; `folio tags` lists them")
    return plan.apply()
