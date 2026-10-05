"""The charter, `folio.yaml`: what a library is, with the model's defaults."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .errors import FolioError
from .frontmatter import dump

CHARTER = "folio.yaml"

KEYS = (
    "folio", "name", "purpose", "reader", "voice", "packs", "home", "genres",
    "checks", "assets", "root", "theme", "journal", "search", "site_url", "comments",
)
_HOME_KEYS = ("maps",)
_JOURNAL_KEYS = ("kinds",)
_COMMENTS_KEYS = ("identity_header",)
_PACK_KEYS = ("name", "git", "ref")
SEVERITIES = ("error", "warning", "off")
# Keys whose value is a list, so `config set` splits a comma-separated value.
LIST_KEYS = ("packs", "home.maps", "journal.kinds", "search")

DEFAULT_READER = "One reader, the owner."
DEFAULT_VOICE = "Plain and precise."


@dataclass
class PackRef:
    name: str
    git: str | None = None
    ref: str | None = None


@dataclass
class Charter:
    path: Path
    raw: dict[str, Any]
    folio: str
    name: str
    purpose: str
    reader: str
    voice: str
    packs: list[PackRef]
    home_maps: list[str]
    genres: dict[str, dict[str, Any]]
    checks: dict[str, str]
    assets: str
    root: str
    theme: str
    journal_kinds: list[str]
    search: list[str] = field(default_factory=list)
    site_url: str = ""  # where the exported site is published; a paper's \fcite links resolve from it
    identity_header: str = ""  # the request header a sign-in proxy names the reader in; empty: none

    @property
    def library(self) -> Path:
        return self.path.parent

    @property
    def root_dir(self) -> Path:
        return (self.library / self.root).resolve()

    @property
    def pack_names(self) -> list[str]:
        return [p.name for p in self.packs]

    def effective(self) -> dict[str, Any]:
        """Every key with its value, defaults filled in."""
        packs: list[Any] = []
        for p in self.packs:
            packs.append(p.name if p.git is None else {"name": p.name, "git": p.git, "ref": p.ref})
        return {
            "folio": self.folio, "name": self.name, "purpose": self.purpose,
            "reader": self.reader, "voice": self.voice, "packs": packs,
            "home": {"maps": list(self.home_maps)}, "genres": self.genres,
            "checks": self.checks, "assets": self.assets, "root": self.root,
            "theme": self.theme, "journal": {"kinds": list(self.journal_kinds)},
            "search": list(self.search), "site_url": self.site_url,
            "comments": {"identity_header": self.identity_header},
        }


def find_library(start: Path) -> Path:
    """The nearest folder at or above `start` holding a `folio.yaml`."""
    here = start.resolve()
    for folder in (here, *here.parents):
        if (folder / CHARTER).is_file():
            return folder
    raise FolioError(f"no {CHARTER} found at or above {here}; run `folio init` first")


def _str(raw: dict, key: str, default: str, where: str) -> str:
    value = raw.get(key, default)
    if value is None:
        return default
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise FolioError(f"{where}: `{key}` must be a string")
    return str(value)


def _str_list(value: Any, key: str, where: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise FolioError(f"{where}: `{key}` must be a list of strings")
    return list(value)


def _only(mapping: Any, allowed: tuple[str, ...], key: str, where: str) -> dict:
    if mapping is None:
        return {}
    if not isinstance(mapping, dict):
        raise FolioError(f"{where}: `{key}` must be a mapping")
    for k in mapping:
        if k not in allowed:
            raise FolioError(f"{where}: unknown key `{key}.{k}`")
    return mapping


def parse(raw: dict[str, Any], path: Path) -> Charter:
    where = str(path)
    for key in raw:
        if key not in KEYS:
            raise FolioError(f"{where}: unknown key `{key}`")
    packs: list[PackRef] = []
    raw_packs = raw.get("packs") or []
    if not isinstance(raw_packs, list):
        raise FolioError(f"{where}: `packs` must be a list")
    for entry in raw_packs:
        if isinstance(entry, str):
            packs.append(PackRef(entry))
        elif isinstance(entry, dict):
            _only(entry, _PACK_KEYS, "packs[]", where)
            if not isinstance(entry.get("name"), str):
                raise FolioError(f"{where}: a pack given as a mapping needs a `name`")
            packs.append(PackRef(entry["name"], entry.get("git"), entry.get("ref")))
        else:
            raise FolioError(f"{where}: each pack is a name or a mapping with name, git and ref")
    names = [p.name for p in packs]
    if len(set(names)) != len(names):
        raise FolioError(f"{where}: a pack is listed twice in `packs`")
    home = _only(raw.get("home"), _HOME_KEYS, "home", where)
    journal = _only(raw.get("journal"), _JOURNAL_KEYS, "journal", where)
    genres = raw.get("genres") or {}
    if not isinstance(genres, dict) or not all(isinstance(v, dict) for v in genres.values()):
        raise FolioError(f"{where}: `genres` maps each genre name to its settings")
    checks = raw.get("checks") or {}
    if not isinstance(checks, dict):
        raise FolioError(f"{where}: `checks` maps each check name to a severity")
    for name, severity in list(checks.items()):
        if severity is False:
            # YAML 1.1 reads a bare `off` as false.
            checks[name] = severity = "off"
        if severity not in SEVERITIES:
            raise FolioError(
                f"{where}: check `{name}` has severity `{severity}`; use error, warning or off"
            )
    return Charter(
        path=path,
        raw=raw,
        folio=_str(raw, "folio", __version__, where),
        name=_str(raw, "name", path.parent.name, where),
        purpose=_str(raw, "purpose", "", where),
        reader=_str(raw, "reader", DEFAULT_READER, where),
        voice=_str(raw, "voice", DEFAULT_VOICE, where),
        packs=packs,
        home_maps=_str_list(home.get("maps"), "home.maps", where),
        genres={str(k): dict(v) for k, v in genres.items()},
        checks={str(k): str(v) for k, v in checks.items()},
        assets=_str(raw, "assets", "assets/", where),
        root=_str(raw, "root", ".", where),
        theme=_str(raw, "theme", "folio", where),
        journal_kinds=_str_list(journal.get("kinds"), "journal.kinds", where),
        search=_str_list(raw.get("search"), "search", where),
        site_url=_site_url(raw, where),
        identity_header=_identity_header(raw, where),
    )


def _identity_header(raw: dict[str, Any], where: str) -> str:
    """The header naming the signed-in reader on a deployed server, such as `X-Forwarded-User`."""
    comments = _only(raw.get("comments"), _COMMENTS_KEYS, "comments", where)
    value = _str(comments, "identity_header", "", where).strip()
    if value and not re.match(r"^[A-Za-z0-9][A-Za-z0-9-]*$", value):
        raise FolioError(f"{where}: `comments.identity_header` must be a header name, such as "
                         f"X-Forwarded-User, not `{value}`")
    return value


def _site_url(raw: dict[str, Any], where: str) -> str:
    """The published site's address, `https://...`, or empty when the site is not published."""
    value = _str(raw, "site_url", "", where).strip()
    if value and not re.match(r"^https?://[^\s]+$", value):
        raise FolioError(f"{where}: `site_url` must be an http(s) address, not `{value}`")
    return value.rstrip("/")


def load(library: Path) -> Charter:
    path = library / CHARTER
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise FolioError(f"{path}: not valid YAML: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise FolioError(f"{path}: the charter must be a mapping")
    return parse(raw, path)


def write(path: Path, raw: dict[str, Any]) -> None:
    path.write_text(dump(raw), encoding="utf-8")


def get_key(data: dict[str, Any], key: str) -> Any:
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise FolioError(f"no charter key `{key}`")
        node = node[part]
    return node


def coerce(key: str, value: str) -> Any:
    """A `config set` value typed by its key: lists split on commas, numbers and booleans typed."""
    if key in LIST_KEYS:
        return [v.strip() for v in value.split(",") if v.strip()]
    if key.startswith("genres."):
        if value in ("true", "false"):
            return value == "true"
        if value.lstrip("-").isdigit():
            return int(value)
        if "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
    return value


def set_key(raw: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    """A copy of the raw charter with `key` set; intermediate mappings are created."""
    parts = key.split(".")
    if parts[0] not in KEYS:
        raise FolioError(f"unknown charter key `{parts[0]}`")
    out = copy.deepcopy(raw)  # a copy that keeps the charter's key order
    node = out
    for part in parts[:-1]:
        child = node.get(part)
        if child is None:
            child = {}
            node[part] = child
        if not isinstance(child, dict):
            raise FolioError(f"charter key `{key}`: `{part}` is not a mapping")
        node = child
    node[parts[-1]] = value
    return out


# -- editing the charter's text in place ---------------------------------------

_LINE_RE = re.compile(r"^([ \t]*)([^\s#:][^:#]*?):(?:[ \t]+(.*?))?[ \t]*$")


def _content(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _flow(value: Any) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=1000)
    if text.endswith("\n...\n"):
        text = text[: -len("\n...\n")]
    return text.strip()


def _block_end(lines: list[str], k: int, end: int) -> int:
    """The line after the block that belongs to the key on line k."""
    own = _indent(lines[k])
    j = k + 1
    last = k + 1
    while j < end:
        if _content(lines[j]):
            if _indent(lines[j]) <= own and not lines[j].lstrip().startswith("- ") or _indent(lines[j]) < own:
                break
            last = j + 1
        j += 1
    return last


def edit_text(text: str, key: str, value: Any) -> str | None:
    """The charter's text with `key` set to `value`, every other line kept as written.

    Returns None when the key sits somewhere a line edit cannot reach (inside
    a flow mapping, say); the caller then writes the whole charter.
    """
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    parts = key.split(".")
    start, end, indent = 0, len(lines), 0
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        found = None
        for k in range(start, end):
            if not _content(lines[k]) or _indent(lines[k]) != indent:
                continue
            m = _LINE_RE.match(lines[k].rstrip("\n"))
            if m and m.group(2).strip() == part:
                found = (k, m)
                break
        if found is None:
            pad = " " * indent
            new = [f"{pad}{part}:" + (f" {_flow(value)}\n" if last else "\n")]
            for j, rest in enumerate(parts[i + 1:], start=1):
                tail = f" {_flow(value)}\n" if j == len(parts) - 1 - i else "\n"
                new.append(f"{pad}{'  ' * j}{rest}:{tail}")
            at = end
            while at > start and not _content(lines[at - 1]):
                at -= 1
            lines[at:at] = new
            return "".join(lines)
        k, m = found
        stop = _block_end(lines, k, end)
        rest = m.group(3) or ""
        if last:
            comment = ""
            hit = re.search(r"[ \t]+#.*$", rest)
            if hit:
                comment = "   " + hit.group(0).strip()
            lines[k:stop] = [f"{m.group(1)}{part}: {_flow(value)}{comment}\n"]
            return "".join(lines)
        if rest and not rest.startswith("#"):
            return None  # a flow mapping: no lines to descend into
        start, end = k + 1, stop
        children = [lines[j] for j in range(start, end) if _content(lines[j])]
        indent = _indent(children[0]) if children else _indent(lines[k]) + 2
    return None


def write_key(path: Path, raw: dict[str, Any], key: str, value: Any) -> None:
    """Write `raw` (the charter with `key` set) keeping the file's order and comments where it can."""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    edited = edit_text(text, key, value)
    if edited is not None:
        try:
            if (yaml.safe_load(edited) or {}) == raw:
                path.write_text(edited, encoding="utf-8")
                return
        except yaml.YAMLError:
            pass
    write(path, raw)
