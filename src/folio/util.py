"""Small helpers shared across the engine."""

from __future__ import annotations

import datetime as _dt
import os
import re

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER_RE = re.compile(r"\{\{(.*?)\}\}", re.S)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def html_text(text: str) -> str:
    """Text for an HTML text node: only `&`, `<` and `>` escaped, so quotes stay readable in the source."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_attr(text: str) -> str:
    """Text for a double-quoted HTML attribute: `html_text` plus `"`; an apostrophe stays as it is."""
    return html_text(text).replace('"', "&quot;")


def today() -> _dt.date:
    """Today, or FOLIO_TODAY (YYYY-MM-DD) so tests and reruns are reproducible."""
    fixed = os.environ.get("FOLIO_TODAY")
    if fixed:
        return _dt.date.fromisoformat(fixed)
    return _dt.date.today()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "untitled"


def is_slug(text: str) -> bool:
    return bool(SLUG_RE.match(text))


def parse_date(value: object) -> _dt.date | None:
    """A date from a YAML date or a `YYYY-MM-DD` string; None when it is neither."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and DATE_RE.match(value):
        try:
            return _dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def has_placeholder(value: object) -> bool:
    if isinstance(value, str):
        return "{{" in value
    if isinstance(value, list):
        return any(has_placeholder(v) for v in value)
    return False


def as_list(value: object) -> list[str]:
    """A list of strings from a YAML list, a comma-separated string, or nothing."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(",") if p.strip()]


def deep_merge(base: dict, over: dict) -> dict:
    """Merge `over` onto `base` key by key; nested mappings merge, everything else replaces."""
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out
