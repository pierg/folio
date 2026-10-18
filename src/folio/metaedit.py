"""Write metadata into a document: `<meta>` tags in HTML, front matter keys in Markdown."""

from __future__ import annotations

import json
import re
from typing import Any

from .errors import FolioError
from .frontmatter import front_block
from .util import html_attr, html_text


def _html_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def set_html(text: str, name: str, value: Any) -> str:
    content = html_attr(_html_value(value))
    pattern = re.compile(r'(<meta\s+name="' + re.escape(name) + r'"\s+content=")[^"]*(")')
    if pattern.search(text):
        text = pattern.sub(lambda m: m.group(1) + content + m.group(2), text, count=1)
    else:
        tag = f'<meta name="{name}" content="{content}">\n'
        anchor = text.find("</head>")
        if anchor < 0:
            raise FolioError(f"cannot add <meta name=\"{name}\">: the page has no </head>")
        text = text[:anchor] + tag + text[anchor:]
    if name == "title":
        text = re.sub(r"<title>.*?</title>", lambda m: f"<title>{html_text(str(value))}</title>",
                      text, count=1, flags=re.S)
    return text


def _yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def set_markdown(text: str, key: str, value: Any) -> str:
    span = front_block(text)
    if span is None:
        raise FolioError(f"cannot set `{key}`: the file has no front matter")
    start, end = span
    block = text[start:end]
    line = f"{key}: {_yaml_value(value)}"
    pattern = re.compile(r"^" + re.escape(key) + r":.*$", re.M)
    if pattern.search(block):
        block = pattern.sub(lambda m: line, block, count=1)
    else:
        block = block + line + "\n"
    return text[:start] + block + text[end:]


def set_meta(text: str, fmt: str, key: str, value: Any) -> str:
    if fmt == "html":
        return set_html(text, key, value)
    if fmt == "markdown":
        return set_markdown(text, key, value)
    raise FolioError(f"a {fmt} file holds no metadata")
