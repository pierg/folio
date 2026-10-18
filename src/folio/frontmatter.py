"""YAML front matter, and Markdown bodies split by `##` section."""

from __future__ import annotations

import re

import yaml

from .errors import FolioError

_FM_RE = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*\n?", re.S | re.M)
_FENCE_RE = re.compile(r"^(```|~~~)")


def split(text: str, where: str) -> tuple[dict | None, str]:
    """The front matter as a mapping (None when the file has none) and the body."""
    match = _FM_RE.match(text)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise FolioError(f"{where}: front matter is not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FolioError(f"{where}: front matter must be a mapping")
    return data, text[match.end():]


def front_block(text: str) -> tuple[int, int] | None:
    """The character span of the front matter's inner lines, for in-place edits."""
    match = _FM_RE.match(text)
    if not match:
        return None
    return match.start(1), match.end(1)


def sections(body: str) -> list[tuple[str, str]]:
    """The body as (heading, text) pairs; the text before the first `##` has heading ''."""
    out: list[tuple[str, list[str]]] = [("", [])]
    fenced = False
    for line in body.splitlines(keepends=True):
        if _FENCE_RE.match(line):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            out.append((line[3:].strip(), [line]))
        else:
            out[-1][1].append(line)
    return [(heading, "".join(lines)) for heading, lines in out]


def merge_bodies(base: str, over: str) -> str:
    """Merge a card body over another, section by section: a heading replaces, a new one appends."""
    merged = sections(base)
    for heading, text in sections(over):
        if not text.strip():
            continue
        for i, (existing, _) in enumerate(merged):
            if existing == heading:
                merged[i] = (heading, text)
                break
        else:
            merged.append((heading, text))
    parts = [text.rstrip("\n") + "\n" for _, text in merged if text.strip()]
    return "\n".join(parts)


def dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=None, width=1000)
