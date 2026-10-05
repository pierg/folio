"""The packs' rule checks: `uncited-number` and `cites-superseded` (lab), `unverified-identifier` (knowledge-base)."""

from __future__ import annotations

import re

from ..documents import DocFile, Document
from ..html import Element, Node
from ..library import Library
from ..links import Link
from ..util import parse_date, today

Found = list[tuple[str, str]]

# ---------------------------------------------------------------- uncited-number

_UNITS = (
    r"ns|µs|μs|us|ms|s|sec|secs|seconds?|min|mins|minutes?|h|hr|hrs|hours?"
    r"|[kKMGT]i?B|B|bytes?|[kKMG]?Hz|[kM]?W|mW|V|mV|mA|A|[kM]?J|°C|°F|K"
    r"|nm|mm|cm|m|km|mg|g|kg|t"
)
_NUM = r"\d+(?:[.,]\d+)?"
_MEASURE_RE = re.compile(
    rf"{_NUM}\s?%"                                      # a percentage
    rf"|\b{_NUM}\s?(?:×|x\b)"                           # a multiplier: 3×, 2.5x
    rf"|\b\d+\s+of\s+\d+\b"                             # a of b
    rf"|\b{_NUM}\s?/\s?{_NUM}\b"                        # a ratio a/b
    rf"|\b{_NUM}\s?(?:{_UNITS})(?![\w/])"               # a number with a unit
    r"|\b\d+\.\d+\b"                                    # a number with a decimal point
)
# Removed before the shapes are matched: they hold digits but measure nothing.
_SKIP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"                            # a date
    r"|\b[A-Z][A-Za-z]*-\d+\b"                          # an id: R-12, C-3
    r"|\bv?\d+\.\d+\.\d+(?:[.-]\w+)*\b|\bv\d+(?:\.\d+)*\b"   # a version: 0.1.0, v2.1
    r"|(?:§|\b(?:[Ss]ections?|[Cc]hapters?|[Ff]ig(?:ure)?s?\.?|[Tt]ables?|[Ee]q(?:uation)?s?\.?"
    r"|[Ss]teps?|[Pp]arts?|[Aa]ppendix|[Vv]ersion|[Ll]ines?|[Pp]ages?|pp?\.)\s?)\d+(?:\.\d+)*"
    r"|https?://\S+"                                    # a URL
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'“])")
_CITE = "\x00"
_ITEM_TAGS = {"li", "tr", "dd", "dt"}
_BLOCK_TAGS = {"p", "figcaption", "caption", "summary", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6",
               "td", "th", "div", "section", "main", "body", "article", "aside", "details", "figure",
               "ul", "ol", "dl", "table", "thead", "tbody", "header", "footer", "nav", "#root", "#group"}
_INLINE_TAGS = {"a", "span", "em", "strong", "b", "i", "sub", "sup", "abbr", "cite", "q", "small",
                "mark", "s", "u", "time", "data", "dfn"}
_SKIP_TAGS = {"code", "pre", "script", "style", "kbd", "samp", "var", "math", "svg", "head", "template"}


def measurements(text: str) -> list[str]:
    """The numbers in a stretch of prose that are shaped like measurements.

    The heuristic: a percentage (`12%`), a multiplier (`3×`, `2.5x`),
    `a of b`, a ratio `a/b`, a number with a unit of measure (`45 ms`,
    `2 GB`) and any number with a decimal point (`0.93`). Dates, record ids
    (`R-12`), version numbers (`0.1.0`, `v2`), section, figure, table and
    page numbers, and URLs are removed first. A plain integer (`1000 items`,
    `2019`) is never a measurement. Numbers written in words are missed;
    that is judged, not checked.
    """
    return [m.group(0).strip() for m in _MEASURE_RE.finditer(_SKIP_RE.sub(" ", text))]


def _is_row_link(node: Element) -> bool:
    """The first link of a map row (`ul.rows > li > a`): the shell draws its text from the catalog."""
    li = node.parent
    if node.tag != "a" or li is None or li.tag != "li" or li.parent is None:
        return False
    if li.parent.tag != "ul" or "rows" not in li.parent.classes:
        return False
    return li.first("a") is node


def _units(nodes: list[Node], cite_els: set[int] | dict[int, str]) -> list[tuple[bool, str]]:
    """Split HTML into checking units: (is an item, text with cites marked).

    A list item, a table row, a `dd` or `dt` is one unit; any other block is
    split into sentences later. Code and `.not-measured` spans are dropped,
    and a citing link or code element becomes a cite mark (its own mark when
    `cite_els` maps elements to marks). A map row's link text is dropped too.
    """
    units: list[tuple[bool, list[str]]] = [(False, [])]

    def walk(node: Node, in_item: bool) -> None:
        if isinstance(node, str):
            units[-1][1].append(node)
            return
        if id(node) in cite_els:
            mark = cite_els[id(node)] if isinstance(cite_els, dict) else _CITE
            units[-1][1].append(f" {mark} ")
            return
        if _is_row_link(node):
            return
        if node.tag in _SKIP_TAGS or "not-measured" in node.classes or "identifier" in node.classes:
            return
        opens = node.tag in _ITEM_TAGS or (not in_item and node.tag in _BLOCK_TAGS)
        if opens:
            units.append((node.tag in _ITEM_TAGS, []))
        for child in node.children:
            walk(child, in_item or node.tag in _ITEM_TAGS)
        if opens:
            units.append((in_item, []))  # what follows belongs to the enclosing unit's level
        elif node.tag not in _INLINE_TAGS:
            units[-1][1].append(" ")

    for n in nodes:
        walk(n, False)
    return [(item, " ".join("".join(parts).split())) for item, parts in units if "".join(parts).strip()]


def _uncited(text: str, item: bool) -> list[str]:
    pieces = [text] if item else _SENTENCE_RE.split(text)
    out = []
    for piece in pieces:
        if _CITE in piece:
            continue
        out.extend(measurements(piece))
    return out


_LATEX_DROP_RE = re.compile(
    r"\\(?:notmeasured|ref|eqref|autoref|cref|Cref|label|cite[a-z]*|includegraphics|input|include"
    r"|graphicspath|usepackage|documentclass|bibliography|bibliographystyle|url|texttt|verb\S"
    r"|hspace|vspace|setlength|addtolength|newcommand|renewcommand|def)\*?(?:\[[^\]]*\])*(?:\{(?:[^{}]|\{[^{}]*\})*\})*"
)
_LATEX_ENV_RE = re.compile(r"\\begin\{(verbatim|lstlisting|minted|equation\*?|align\*?|math)\}.*?\\end\{\1\}", re.S)
_FCITE_RE = re.compile(r"\\fcite\{([^}]*)\}")
_OPTS_RE = re.compile(r"(\\[A-Za-z]+\*?)\[[^\]]*\]")


def _latex_units(lib: Library, latex: str, cites: set[str]) -> list[tuple[bool, str]]:
    if "\\begin{document}" in latex:
        latex = latex.split("\\begin{document}", 1)[1]
    latex = _LATEX_ENV_RE.sub(" ", latex)
    latex = re.sub(r"\$[^$]*\$", " ", latex)
    latex = _FCITE_RE.sub(lambda m: f" {_CITE} " if any(i.strip() in cites for i in m.group(1).split(","))
                          else " ", latex)
    latex = _LATEX_DROP_RE.sub(" ", latex)
    latex = _OPTS_RE.sub(r"\1", latex).replace("\\%", "%").replace("~", " ")
    out = []
    for para in re.split(r"\n\s*\n|\\item\b", latex):
        text = " ".join(para.split())
        if text:
            out.append((False, text))
    return out


def _counts_as_cite(lib: Library, doc: Document, kb_on: bool) -> bool:
    """A result, a protocol (its numbers are pre-registered thresholds), or with kb on a source."""
    return doc.is_a("result") or doc.is_a("protocol") or (kb_on and doc.is_a("source"))


_RECORDS = ("journal", "question", "protocol", "result")


def uncited_number(lib: Library) -> Found:
    """A measured number on a page, in a paper or in a claim's body cites a result in the same unit.

    The unit is the sentence, list item or table row (`measurements` says
    which numbers count). A link to a protocol also counts, and with the
    knowledge-base pack on, a link to a source. A map row's link text is
    not read: the shell replaces it with the catalog's title.
    """
    kb_on = any(p.on and p.name == "knowledge-base" for p in lib.registry.packs.values())
    out: Found = []
    for doc in lib.documents:
        if any(doc.is_a(g) for g in _RECORDS):
            continue
        for df in doc.files:
            if df.format == "markdown" and not doc.is_a("claim"):
                continue
            links = lib.links.get(df.path, [])
            if df.format == "latex":
                ids = {link.raw for link in links if any(_counts_as_cite(lib, d, kb_on) for d in link.docs)}
                units = _latex_units(lib, df.latex or "", ids)
            elif df.body is not None:
                cite_els = {id(link.element) for link in links if link.element is not None
                            and any(_counts_as_cite(lib, d, kb_on) for d in link.docs)}
                units = _units([df.body], cite_els)
            else:
                continue
            seen: list[str] = []
            for item, text in units:
                seen.extend(_uncited(text, item))
            for number in dict.fromkeys(seen):
                out.append((df.path, f"`{number}` looks like a measurement and cites no result in its"
                                     " sentence, item or row; cite the result, or wrap it as not measured"))
    return out


# ---------------------------------------------------------------- cites-superseded


_HONEST_RE = re.compile(r"\b(?:retracted|superseded)\b", re.I)


def _unit_of(units: list[tuple[bool, str]], mark: str) -> str | None:
    for item, text in units:
        if mark not in text:
            continue
        if item:
            return text
        return next((s for s in _SENTENCE_RE.split(text) if mark in s), text)
    return None


def _honest_mention(lib: Library, link: Link) -> bool:
    """True when the citation's sentence, list item or table row says `retracted` or `superseded`."""
    df = link.file
    mark = "\x01cite\x01"
    if link.element is not None and df.body is not None:
        unit = _unit_of(_units([df.body], {id(link.element): mark}), mark)
    elif link.kind == "fcite" and df.latex is not None:
        units = []
        for item, text in _latex_units(lib, _mark_fcite(df.latex, link.raw, mark), set()):
            units.append((item, text))
        unit = _unit_of(units, mark)
    else:
        return False
    return bool(unit and _HONEST_RE.search(unit))


def _mark_fcite(latex: str, ident: str, mark: str) -> str:
    """The LaTeX with each `\\fcite{..}` naming `ident` replaced by a mark the unit split keeps."""
    def one(m: re.Match[str]) -> str:
        ids = [i.strip() for i in m.group(1).split(",")]
        return f" {mark} " if ident in ids else m.group(0)
    return _FCITE_RE.sub(one, latex)


def cites_superseded(lib: Library) -> Found:
    """A revised document cites only results whose derived status is `live`."""
    out: Found = []
    for doc in lib.documents:
        genre = doc.genre
        if genre is None or genre.lives == "permanent" or doc.status in ("historical", "retired"):
            continue
        if genre.lives == "frozen" and doc.status in genre.frozen_in:
            continue
        named: dict[str, tuple[str, Document]] = {}
        for link in lib.doc_links(doc):
            for target in link.docs:
                if target.is_a("result") and target.status != "live" and target is not doc \
                        and not _honest_mention(lib, link):
                    named.setdefault(target.id, (link.file.path, target))
        for ident, (path, target) in sorted(named.items()):
            if target.superseded_by:
                newer = ", ".join(sorted(d.id for d in target.superseded_by))
                out.append((path, f"cites `{ident}`, which is {target.status}; cite {newer} instead,"
                                  " or mark this document historical"))
            else:
                out.append((path, f"cites `{ident}`, which is {target.status}; cite a live result,"
                                  " or mark this document historical"))
    return out


# ---------------------------------------------------------------- unverified-identifier

_SHAPES = {
    "doi": re.compile(r"^10\.\d{4,9}/\S+$"),
    "arxiv": re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$"),
    "isbn": re.compile(r"^(?:\d[- ]?){9}[\dXx]$|^(?:\d[- ]?){12}\d$"),
    "handle": re.compile(r"^\d+(?:\.\d+)*/\S+$"),
    "url": re.compile(r"^https?://\S+$"),
}
_RESOLVERS = {"doi": "https://doi.org/", "arxiv": "https://arxiv.org/abs/", "handle": "https://hdl.handle.net/"}


def _identifier_problem(el: Element) -> str | None:
    kind = el.get("data-kind") or ""
    text = el.text().strip()
    href = (el.get("href") or "").strip()
    if "identifier" not in el.classes:
        return f"`{text}` in the identifiers list is not an <a class=\"identifier\">"
    if kind not in _SHAPES:
        return f"identifier `{text}` has data-kind `{kind}`; use one of {', '.join(_SHAPES)}"
    verified = el.get("data-verified") or ""
    date = parse_date(verified)
    if date is None:
        return f"identifier `{text}` has no data-verified date (YYYY-MM-DD) of its lookup"
    if date > today():
        return f"identifier `{text}` was verified on {verified}, which is in the future"
    if not _SHAPES[kind].match(text):
        return f"identifier `{text}` is not shaped like a {kind}"
    if kind in _RESOLVERS:
        same = href.lower() == (_RESOLVERS[kind] + text).lower()
    elif kind == "isbn":
        digits = re.sub(r"[- ]", "", text).lower()
        same = digits in re.sub(r"[- ]", "", href).lower()
    else:
        same = href.rstrip("/") == text.rstrip("/")
    if not same:
        return f"identifier `{text}` links to `{href}`, which names a different identifier"
    return None


def unverified_identifier(lib: Library) -> Found:
    """Every identifier in a source is an `<a class="identifier">` with its kind, its lookup date, and a matching link."""
    out: Found = []
    for doc in lib.documents:
        if not doc.is_a("source"):
            continue
        for df in doc.files:
            out.extend((df.path, m) for m in _identifier_problems(df))
    return out


def _identifier_problems(df: DocFile) -> list[str]:
    if df.body is None:
        return []
    out = []
    lists = [el for el in df.body.iter() if "identifiers" in el.classes or el.id == "identifiers"]
    inside: set[int] = set()
    for lst in lists:
        for el in lst.iter():
            if el.tag == "a":
                inside.add(id(el))
                problem = _identifier_problem(el)
                if problem:
                    out.append(problem)
            elif el.tag == "li" and el.first("a") is None and el.text().strip():
                out.append(f"`{el.text().strip()}` in the identifiers list is not an <a class=\"identifier\">")
    for el in df.body.iter():
        if el.tag == "a" and "identifier" in el.classes and id(el) not in inside:
            out.append(f"identifier `{el.text().strip()}` sits outside the identifiers list")
    return out
