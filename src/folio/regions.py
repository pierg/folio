"""Named parts of a document's body, as a card's `require`, `forbid` and `cites` name them.

In HTML a part is an element whose tag, id or class is the name; when that
element is a heading, the part runs to the next heading of its level. In
Markdown a part is a `##` section: the card's Shape names its heading as
"`## Heading` (`name`)", and otherwise the heading's slug is the name. In
LaTeX a part is an environment or a command of that name.
"""

from __future__ import annotations

import re

from .documents import DocFile
from .genres import Genre
from .html import Element, Node, heading_level, section_of
from .util import slugify

_SHAPE_RE = re.compile(r"`##\s+([^`]+?)`\s*\(`([A-Za-z0-9_-]+)`\)")


def markdown_headings(genre: Genre) -> dict[str, str]:
    """Heading text (lowercased) to part name, from the card's Shape."""
    return {h.strip().lower(): name for h, name in _SHAPE_RE.findall(genre.body)}


def _md_name(heading: str, mapping: dict[str, str]) -> str:
    return mapping.get(heading.strip().lower(), slugify(heading))


def find(df: DocFile, genre: Genre, name: str) -> list[list[Node]]:
    """Every occurrence of the part in the file, each as a list of nodes; empty when absent."""
    if df.format == "latex":
        latex = df.latex or ""
        pattern = r"\\begin\{" + re.escape(name) + r"\}|\\" + re.escape(name) + r"(?![A-Za-z])"
        return [[]] if re.search(pattern, latex) else []
    if df.body is None:
        return []
    if df.format == "markdown":
        mapping = markdown_headings(genre)
        return [section_of(h) for h in df.body.element_children()
                if h.tag == "h2" and _md_name(h.text(), mapping) == name]
    out: list[list[Node]] = []
    for el in df.body.iter():
        if el is df.body:
            continue
        if el.tag == name or el.id == name or name in el.classes:
            out.append(section_of(el) if heading_level(el) else [el])
    return out


def list_items(nodes: list[Node]) -> list[Element]:
    """The items of the lists directly inside a part (nested lists belong to their item)."""
    items: list[Element] = []
    for node in nodes:
        if not isinstance(node, Element):
            continue
        lists = [node] if node.tag in ("ul", "ol") else [
            e for e in node.iter() if e.tag in ("ul", "ol") and not e.inside("li")
        ]
        for lst in lists:
            items.extend(c for c in lst.element_children() if c.tag == "li")
    return items
