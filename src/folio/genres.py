"""Genre cards: loading, overriding, variants, and the per-library registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import data
from .charter import Charter
from .errors import FolioError
from .frontmatter import dump, merge_bodies, split
from .packs import Pack
from .util import deep_merge

FORMATS = {"html": ".html", "markdown": ".md", "latex": ".tex"}
LIVES = ("revised", "permanent", "frozen")
ON_MAP = ("required", "optional", "never", "exempt")
FIELD_TYPES = ("string", "integer", "date", "enum", "id", "ids", "path")
CORE_FIELDS = ("title", "description", "genre", "status", "tags", "id")
_CARD_KEYS = (
    "name", "extends", "pack", "format", "path", "id", "skeleton", "lives", "states",
    "frozen_in", "frozen_exits", "fields", "checks", "on_map", "parts",
)
_PART_KEYS = ("path", "skeleton", "checks", "on_map", "address", "lives")
PART_LIVES = ("revised", "permanent")
_FIELD_KEYS = ("name", "type", "required", "values", "genre", "status")
DEFAULT_STATES = ["draft", "live", "historical", "retired"]


@dataclass
class FieldSpec:
    name: str
    type: str
    required: bool = False
    values: list[str] | None = None
    genre: str | None = None
    status: list[str] | None = None


@dataclass
class PartSpec:
    name: str
    path: str
    skeleton: str
    checks: dict[str, Any]
    on_map: str
    address: bool
    lives: str = "revised"  # `permanent`: never edited once committed, nor anything in its folder


@dataclass
class Layer:
    """One GENRE.md: its front matter, its body and the folder it sits in."""

    front: dict[str, Any]
    body: str
    folder: Path
    source: str  # "core" | "pack" | "library"


@dataclass
class Genre:
    name: str
    source: str
    pack: str | None
    extends: str | None
    lineage: list[str]  # itself, then its parent, and so on
    format: str
    path: str
    prefix: str | None
    skeleton: str
    lives: str
    states: list[str]
    frozen_in: list[str]
    frozen_exits: list[str]
    fields: list[FieldSpec]
    checks: dict[str, Any]
    on_map: str
    parts: dict[str, PartSpec]
    body: str
    front: dict[str, Any]
    folders: list[Path]  # skeleton lookup, nearest first
    card_files: list[Path]
    enabled: bool = True
    active: bool = True

    @property
    def ext(self) -> str:
        return FORMATS[self.format]

    def is_a(self, name: str) -> bool:
        return name in self.lineage

    def field(self, name: str) -> FieldSpec | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def skeleton_file(self, name: str) -> Path:
        for folder in self.folders:
            candidate = folder / name
            if candidate.is_file():
                return candidate
        raise FolioError(f"genre `{self.name}`: skeleton `{name}` not found in {self.folders[0]}")

    def address_part(self) -> PartSpec | None:
        for part in self.parts.values():
            if part.address:
                return part
        return None

    def card_text(self) -> str:
        return "---\n" + dump(self.front) + "---\n\n" + self.body


@dataclass
class Workflow:
    name: str
    source: str
    pack: str | None
    file: Path
    front: dict[str, Any]
    body: str

    @property
    def summary(self) -> str:
        return str(self.front.get("summary", ""))


@dataclass
class Registry:
    genres: dict[str, Genre]
    workflows: dict[str, Workflow]
    packs: dict[str, Pack]
    unique: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> Genre:
        if name not in self.genres:
            raise FolioError(f"no genre `{name}`; `folio genres` lists them")
        return self.genres[name]

    def active(self) -> list[Genre]:
        return [g for g in self.genres.values() if g.active]


def _read_layer(card: Path, source: str) -> Layer:
    front, body = split(card.read_text(encoding="utf-8"), str(card))
    if front is None:
        raise FolioError(f"{card}: a genre card needs front matter")
    for key in front:
        if key not in _CARD_KEYS:
            raise FolioError(f"{card}: unknown key `{key}`")
    if front.get("name") != card.parent.name:
        raise FolioError(f"{card}: `name` must be `{card.parent.name}`, the card's folder")
    return Layer(front, body, card.parent, source)


def _cards_in(folder: Path, source: str) -> dict[str, Layer]:
    out: dict[str, Layer] = {}
    if folder.is_dir():
        for sub in sorted(folder.iterdir()):
            card = sub / "GENRE.md"
            if card.is_file():
                out[sub.name] = _read_layer(card, source)
    return out


def _defaults(name: str, fmt: str) -> dict[str, Any]:
    ext = FORMATS.get(fmt, ".html")
    return {
        "extends": None, "pack": None, "format": fmt,
        "path": f"content/{name}s/{{slug}}{ext}", "id": "slug",
        "skeleton": f"skeleton{ext}", "lives": "revised", "states": list(DEFAULT_STATES),
        "frozen_in": [], "frozen_exits": [], "fields": [], "checks": {}, "on_map": "required", "parts": {},
    }


def _fields(raw: Any, where: str) -> list[FieldSpec]:
    if not isinstance(raw, list):
        raise FolioError(f"{where}: `fields` must be a list")
    out = []
    for item in raw:
        if not isinstance(item, dict) or "name" not in item or "type" not in item:
            raise FolioError(f"{where}: each field needs a `name` and a `type`")
        for key in item:
            if key not in _FIELD_KEYS:
                raise FolioError(f"{where}: field `{item['name']}` has unknown key `{key}`")
        if item["type"] not in FIELD_TYPES:
            raise FolioError(f"{where}: field `{item['name']}` has unknown type `{item['type']}`")
        if item["name"] in CORE_FIELDS:
            raise FolioError(f"{where}: field `{item['name']}` is core metadata and is never declared")
        if item["type"] == "enum" and not item.get("values"):
            raise FolioError(f"{where}: enum field `{item['name']}` needs `values`")
        status = item.get("status")
        out.append(FieldSpec(
            name=item["name"], type=item["type"], required=bool(item.get("required", False)),
            values=[str(v) for v in item["values"]] if item.get("values") else None,
            genre=item.get("genre"), status=[str(s) for s in status] if status else None,
        ))
    return out


def _build(name: str, front: dict[str, Any], body: str, lineage: list[str], folders: list[Path],
           card_files: list[Path], source: str, where: str, card_checks: set[str]) -> Genre:
    fmt = front["format"]
    if fmt not in FORMATS:
        raise FolioError(f"{where}: unknown format `{fmt}`")
    if front["lives"] not in LIVES:
        raise FolioError(f"{where}: `lives` must be one of {', '.join(LIVES)}")
    if front["on_map"] not in ON_MAP:
        raise FolioError(f"{where}: `on_map` must be one of {', '.join(ON_MAP)}")
    id_mode = str(front["id"])
    prefix = None
    if id_mode.startswith("prefix:"):
        prefix = id_mode.split(":", 1)[1]
        if not prefix.isalpha():
            raise FolioError(f"{where}: `id: prefix:<letters>`, not `{id_mode}`")
    elif id_mode != "slug":
        raise FolioError(f"{where}: `id` is `slug` or `prefix:<letters>`")
    states = [str(s) for s in front["states"]]
    frozen_in = [str(s) for s in front["frozen_in"] or []]
    for state in frozen_in:
        if state not in states:
            raise FolioError(f"{where}: frozen_in state `{state}` is not in `states`")
    frozen_exits = [str(s) for s in front.get("frozen_exits") or []]
    for state in frozen_exits:
        if state not in states:
            raise FolioError(f"{where}: frozen_exits state `{state}` is not in `states`")
    checks = dict(front["checks"] or {})
    _validate_checks(checks, where, card_checks)
    parts: dict[str, PartSpec] = {}
    for pname, praw in (front["parts"] or {}).items():
        if not isinstance(praw, dict) or "path" not in praw:
            raise FolioError(f"{where}: part `{pname}` needs a `path`")
        for key in praw:
            if key not in _PART_KEYS:
                raise FolioError(f"{where}: part `{pname}` has unknown key `{key}`")
        pchecks = praw.get("checks")
        if pchecks is not None:
            _validate_checks(pchecks, f"{where} (part {pname})", card_checks)
        on_map = praw.get("on_map", front["on_map"])
        if on_map not in ON_MAP:
            raise FolioError(f"{where}: part `{pname}` has unknown on_map `{on_map}`")
        plives = praw.get("lives", "revised")
        if plives not in PART_LIVES:
            raise FolioError(f"{where}: part `{pname}` has `lives: {plives}`; a part is "
                             f"{' or '.join(PART_LIVES)}")
        parts[pname] = PartSpec(
            name=pname, path=praw["path"], skeleton=praw.get("skeleton", front["skeleton"]),
            checks=dict(pchecks) if pchecks is not None else dict(checks),
            on_map=on_map, address=bool(praw.get("address", False)), lives=plives,
        )
    if sum(1 for p in parts.values() if p.address) > 1:
        raise FolioError(f"{where}: only one part can be `address: true`")
    return Genre(
        name=name, source=source, pack=front.get("pack"), extends=front.get("extends"),
        lineage=lineage, format=fmt, path=front["path"], prefix=prefix,
        skeleton=front["skeleton"], lives=front["lives"], states=states, frozen_in=frozen_in,
        frozen_exits=frozen_exits,
        fields=_fields(front["fields"] or [], where), checks=checks, on_map=front["on_map"],
        parts=parts, body=body, front=front, folders=folders, card_files=card_files,
    )


def _validate_checks(checks: Any, where: str, card_checks: set[str]) -> None:
    if not isinstance(checks, dict):
        raise FolioError(f"{where}: `checks` must be a mapping")
    for name in checks:
        if name not in card_checks:
            raise FolioError(f"{where}: unknown card check `{name}`; checks.md lists them")


def load(library: Path, charter: Charter, packs: dict[str, Pack], card_checks: set[str]) -> Registry:
    """Every genre this library knows: core, every available pack, and its own `genres/`."""
    base: dict[str, list[Layer]] = {}
    origin: dict[str, str] = {}
    for name, layer in _cards_in(data.shipped("genres"), "core").items():
        base[name] = [layer]
        origin[name] = "core"
    for pack in packs.values():
        for name, layer in _cards_in(pack.folder / "genres", "pack").items():
            if name in origin:
                raise FolioError(
                    f"genre `{name}` is defined by both {origin[name]} and pack `{pack.name}`; "
                    "genre names are unique across the core and every pack"
                )
            layer.front.setdefault("pack", pack.name)
            if layer.front["pack"] != pack.name:
                raise FolioError(f"{layer.folder}/GENRE.md: `pack` must be `{pack.name}`")
            base[name] = [layer]
            origin[name] = f"pack `{pack.name}`"
    for name, layer in _cards_in(library / "genres", "library").items():
        if name in base and not layer.front.get("extends"):
            base[name].append(layer)
        elif name in base:
            raise FolioError(
                f"{layer.folder}/GENRE.md: `{name}` already exists; an override does not set `extends`"
            )
        else:
            base[name] = [layer]

    resolved: dict[str, tuple[dict, str, list[str], list[Path], list[Path], str]] = {}

    def resolve(name: str, chain: tuple[str, ...]) -> tuple[dict, str, list[str], list[Path], list[Path], str]:
        if name in resolved:
            return resolved[name]
        if name in chain:
            raise FolioError(f"genre `{name}` extends itself through {' -> '.join(chain)}")
        layers = base[name]
        parent_name = layers[0].front.get("extends")
        if parent_name:
            if parent_name not in base:
                raise FolioError(f"genre `{name}` extends `{parent_name}`, which does not exist")
            pfront, pbody, plineage, pfolders, _, _ = resolve(parent_name, chain + (name,))
            front = dict(pfront)
            front["parts"] = dict(pfront.get("parts") or {})
            body = pbody
            lineage = [name, *plineage]
            folders = list(pfolders)
        else:
            front = _defaults(name, layers[0].front.get("format", "html"))
            body = ""
            lineage = [name]
            folders = []
        for layer in layers:
            over = {k: v for k, v in layer.front.items() if k != "name"}
            front = deep_merge(front, over)
            body = merge_bodies(body, layer.body) if body else layer.body
            folders.insert(0, layer.folder)
        front["name"] = name
        source = layers[0].source
        out = (front, body, lineage, folders, [l.folder / "GENRE.md" for l in layers], source)
        resolved[name] = out
        return out

    genres: dict[str, Genre] = {}
    for name in sorted(base):
        front, body, lineage, folders, cards, source = resolve(name, ())
        genres[name] = _build(name, front, body, lineage, folders, cards, source,
                              str(cards[-1]), card_checks)

    for name, settings in charter.genres.items():
        if name not in genres:
            raise FolioError(f"folio.yaml: `genres.{name}` names no genre")
        genre = genres[name]
        for key, value in settings.items():
            if key == "enabled":
                if not isinstance(value, bool):
                    raise FolioError(f"folio.yaml: `genres.{name}.enabled` is true or false")
                genre.enabled = value
            elif key in card_checks:
                genre.checks[key] = value
                for part in genre.parts.values():
                    if key in part.checks:
                        part.checks[key] = value
            else:
                raise FolioError(
                    f"folio.yaml: `genres.{name}.{key}` is neither `enabled` nor a card check"
                )
    on = {p.name for p in packs.values() if p.on}
    for genre in genres.values():
        genre.active = genre.enabled and (genre.pack is None or genre.pack in on)
    return Registry(genres=genres, workflows=_workflows(library, packs), packs=packs)


def _workflows(library: Path, packs: dict[str, Pack]) -> dict[str, Workflow]:
    found: dict[str, Workflow] = {}

    def add(folder: Path, source: str, pack: str | None) -> None:
        if not folder.is_dir():
            return
        for file in sorted(folder.glob("*.md")):
            if file.stem in found:
                continue
            front, body = split(file.read_text(encoding="utf-8"), str(file))
            if front is None or front.get("name") != file.stem:
                raise FolioError(f"{file}: a workflow needs front matter whose `name` is `{file.stem}`")
            found[file.stem] = Workflow(file.stem, source, pack, file, front, body)

    add(library / "workflows", "library", None)
    for pack in packs.values():
        if pack.on:
            add(pack.folder / "workflows", "pack", pack.name)
    add(data.data_root() / "workflows", "core", None)
    return found
