"""Pages as the site serves them: links rewritten, Markdown records rendered in the shell."""

from __future__ import annotations

import html as _html
import re
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

from ..frontmatter import split
from ..links import is_external, resolve_href
from ..util import html_attr, html_text

if TYPE_CHECKING:
    from ..library import Library

SHELL_CSS = "/shell/folio.css"
SHELL_JS = "/shell/folio.js"
_MD = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
_ATTR_RE = re.compile(r"""(\s(?:href|src)\s*=\s*)(["'])(.*?)\2""", re.S | re.I)
_CODE_RE = re.compile(r"(?<!<pre>)<code>([^<]+)</code>")


def site_href(lib: "Library", from_path: str, href: str, base: str) -> str:
    """An href as the exported site serves it.

    A link to a Markdown record lands on its rendered `.html` page, and a link
    from the library root gains the site's base path.
    """
    if not href or href.startswith("#") or is_external(href) or href.startswith("//"):
        return href
    path, sep, rest = _split_suffix(href)
    target = resolve_href(lib.root, from_path, path) if path else None
    if target is not None and target.endswith(".md") and path.endswith(".md"):
        path = path[: -len(".md")] + ".html"
    if path.startswith("/") and base != "/":
        path = base.rstrip("/") + path
    return path + sep + rest


def _split_suffix(href: str) -> tuple[str, str, str]:
    cut = min((i for i in (href.find("#"), href.find("?")) if i >= 0), default=-1)
    if cut < 0:
        return href, "", ""
    return href[:cut], href[cut], href[cut + 1:]


def rewrite(lib: "Library", from_path: str, text: str, base: str) -> str:
    """Every href and src in a page, rewritten with `site_href`."""
    def one(match: re.Match[str]) -> str:
        value = _html.unescape(match.group(3))
        new = site_href(lib, from_path, value, base)
        if new == value:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}{_html.escape(new, quote=True)}{match.group(2)}"
    return _ATTR_RE.sub(one, text)


def with_shell(text: str) -> str:
    """A page that predates the shell's script, or never linked the shell, still gets it.

    A frozen or permanent page cannot be edited to add a line, so the site adds
    whatever of the two shell links the page lacks, just before `</head>`.
    """
    missing = []
    if SHELL_CSS not in text:
        missing.append(f'<link rel="stylesheet" href="{SHELL_CSS}">')
    if SHELL_JS not in text:
        missing.append(f'<script src="{SHELL_JS}" defer></script>')
    if not missing:
        return text
    at = text.lower().find("</head>")
    if at < 0:
        return "\n".join(missing) + "\n" + text
    return text[:at] + "\n".join(missing) + "\n" + text[at:]


def with_title(text: str, title: str) -> str:
    """The home page's `<title>`, from the charter's name: the page carries no title of its own."""
    tag = f"<title>{html_text(title)}</title>"
    if re.search(r"<title>.*?</title>", text, re.S):
        return re.sub(r"<title>.*?</title>", lambda m: tag, text, count=1, flags=re.S)
    at = text.lower().find("</head>")
    return text if at < 0 else text[:at] + tag + "\n" + text[at:]


def _link_ids(lib: "Library", body: str) -> str:
    """An id in backticks cites the document it names, so it becomes a link to it."""
    def one(match: re.Match[str]) -> str:
        ident = _html.unescape(match.group(1)).strip()
        docs = lib.by_id.get(ident)
        if not docs:
            return match.group(0)
        return f'<a class="f-cite" href="/{docs[0].address_file.path}" title="{html_attr(docs[0].title)}">{match.group(0)}</a>'
    return _CODE_RE.sub(one, body)


def _meta(name: str, value: object) -> str:
    return f'<meta name="{name}" content="{html_attr(str(value))}">'


def page(title: str, metas: dict[str, object], main: str, *, extra_head: str = "") -> str:
    """A page in the shell. The shell draws everything above and beside `main`."""
    head = "\n".join(_meta(k, v) for k, v in metas.items() if v not in (None, "", []))
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html_text(title)}</title>\n{head}\n{extra_head}"
        f"<link rel=\"stylesheet\" href=\"{SHELL_CSS}\">\n<script src=\"{SHELL_JS}\" defer></script>\n"
        f"</head>\n<body>\n<main>\n{main}\n</main>\n</body>\n</html>\n"
    )


def record(lib: "Library", rel: str) -> str:
    """A Markdown record rendered as an HTML page, before links are rewritten for the site."""
    df = lib.by_path[rel]
    doc = df.doc
    text = df.abspath.read_text(encoding="utf-8")
    front, body = split(text, rel)
    front = front or {}
    tags = front.get("tags") or []
    metas: dict[str, object] = {
        "genre": front.get("genre"),
        "title": front.get("title"),
        "description": front.get("description"),
        "status": doc.status if doc is not None else front.get("status"),
        "tags": ", ".join(str(t) for t in tags) if isinstance(tags, list) else tags,
        "folio-source": rel,
    }
    if front.get("id") is not None:
        metas["id"] = front["id"]
    main = _link_ids(lib, _MD.render(body))
    return page(str(front.get("title") or rel), metas, main)


def view(title: str, name: str, description: str) -> str:
    """A page the shell builds entirely from the indices, such as the journal timeline."""
    return page(title, {"title": title, "description": description, "folio-view": name}, "")


def redirect(to: str) -> str:
    safe = _html.escape(to, quote=True)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<meta http-equiv=\"refresh\" content=\"0; url={safe}\">\n<link rel=\"canonical\" href=\"{safe}\">\n"
        f"<title>Moved</title>\n</head>\n<body>\n<p>This page moved to <a href=\"{safe}\">{safe}</a>.</p>\n"
        "</body>\n</html>\n"
    )
