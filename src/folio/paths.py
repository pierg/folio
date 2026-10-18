"""Path templates: `content/results/R-{n}.md` and the like."""

from __future__ import annotations

import re

_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERNS = {
    "slug": _SLUG,
    "n": r"[1-9][0-9]*",
    "nn": r"[0-9]{2}",
    "name": _SLUG,
    "date": r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
    "yyyy": r"[0-9]{4}",
    "genre": _SLUG,
}
# A single-brace token; `{{...}}` is text for the author and is never filled.
_TOKEN_RE = re.compile(r"(?<!\{)\{(" + "|".join(PATTERNS) + r")\}(?!\})")


def placeholders(template: str) -> list[str]:
    return _TOKEN_RE.findall(template)


def regex(template: str) -> re.Pattern[str]:
    out: list[str] = []
    seen: set[str] = set()
    pos = 0
    for match in _TOKEN_RE.finditer(template):
        out.append(re.escape(template[pos:match.start()]))
        name = match.group(1)
        if name in seen:
            out.append(f"(?P={name})")
        else:
            out.append(f"(?P<{name}>{PATTERNS[name]})")
            seen.add(name)
        pos = match.end()
    out.append(re.escape(template[pos:]))
    return re.compile("^" + "".join(out) + "$")


def match(template: str, path: str) -> dict[str, str] | None:
    found = regex(template).match(path)
    return found.groupdict() if found else None


def fill(template: str, values: dict[str, str]) -> str:
    """Fill the placeholders it has values for; leave the rest as written."""
    return _TOKEN_RE.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def missing(template: str, values: dict[str, str]) -> list[str]:
    return [p for p in placeholders(template) if p not in values]
