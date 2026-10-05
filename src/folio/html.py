"""A small DOM over the standard library's HTML parser: enough to read pages, not render them."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterator, Union

VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
NOT_PROSE = frozenset({"code", "pre", "script", "style", "head", "template"})

Node = Union["Element", str]


@dataclass(eq=False)
class Element:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    parent: "Element | None" = None

    def get(self, name: str) -> str | None:
        return self.attrs.get(name)

    def has(self, name: str) -> bool:
        return name in self.attrs

    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    @property
    def id(self) -> str | None:
        return self.attrs.get("id")

    def iter(self) -> Iterator["Element"]:
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.iter()

    def find_all(self, tag: str) -> list["Element"]:
        return [e for e in self.iter() if e.tag == tag]

    def first(self, tag: str) -> "Element | None":
        for e in self.iter():
            if e.tag == tag:
                return e
        return None

    def text(self, skip: frozenset[str] = frozenset()) -> str:
        parts: list[str] = []
        _collect(self, parts, skip)
        return "".join(parts)

    def element_children(self) -> list["Element"]:
        return [c for c in self.children if isinstance(c, Element)]

    def inside(self, tag: str) -> bool:
        node = self.parent
        while node is not None:
            if node.tag == tag:
                return True
            node = node.parent
        return False


def _collect(node: Element, parts: list[str], skip: frozenset[str]) -> None:
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.tag not in skip:
            if child.tag in ("br", "p", "li", "div", "td", "th", "tr") or child.tag in HEADINGS:
                parts.append(" ")
            _collect(child, parts, skip)
            if child.tag not in VOID:
                parts.append(" ")


def text_of(nodes: list[Node], skip: frozenset[str] = frozenset()) -> str:
    holder = Element("#group", children=list(nodes))
    return holder.text(skip)


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#root")
        self.stack = [self.root]

    def _add(self, tag: str, attrs: list[tuple[str, str | None]]) -> Element:
        el = Element(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(el)
        return el

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        el = self._add(tag, attrs)
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._add(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse(text: str) -> Element:
    builder = _Builder()
    builder.feed(text)
    builder.close()
    return builder.root


def metas(root: Element) -> dict[str, str]:
    """Every `<meta name content>` in the page, by name; the first one wins."""
    out: dict[str, str] = {}
    for el in root.find_all("meta"):
        name = el.get("name")
        if name and name not in out:
            out[name] = el.get("content") or ""
    return out


def body_of(root: Element) -> Element:
    """The page's content: `<main>` when it has one, else `<body>`, else the whole fragment."""
    return root.first("main") or root.first("body") or root


def heading_level(el: Element) -> int | None:
    if el.tag in HEADINGS:
        return int(el.tag[1])
    return None


def section_of(heading: Element) -> list[Node]:
    """A heading and the siblings that follow it, up to the next heading of its level or higher."""
    level = heading_level(heading)
    parent = heading.parent
    if parent is None or level is None:
        return [heading]
    siblings = parent.children
    start = next(i for i, c in enumerate(siblings) if c is heading)
    out: list[Node] = [heading]
    for node in siblings[start + 1:]:
        if isinstance(node, Element):
            other = heading_level(node)
            if other is not None and other <= level:
                break
        out.append(node)
    return out


def elements_in(nodes: list[Node]) -> Iterator[Element]:
    for node in nodes:
        if isinstance(node, Element):
            yield from node.iter()
