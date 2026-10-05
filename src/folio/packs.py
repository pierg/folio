"""Packs: genres, workflows, rules and journal kinds, switched on in the charter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import data
from .charter import Charter
from .errors import FolioError
from .frontmatter import split

_PACK_KEYS = ("name", "version", "requires", "genres", "workflows", "rules", "journal_kinds")


@dataclass
class Pack:
    name: str
    folder: Path
    source: str  # "shipped" | "library"
    version: str
    genres: list[str]
    workflows: list[str]
    rules: str | None
    journal_kinds: list[str]
    purpose: str
    on: bool = False
    extra: dict = field(default_factory=dict)


def _purpose(body: str) -> str:
    """The pack's one-sentence purpose: the first paragraph after its `#` heading."""
    lines = body.strip().splitlines()
    para: list[str] = []
    for line in lines[1:] if lines and lines[0].startswith("# ") else lines:
        if line.strip():
            if line.startswith("#"):
                break
            para.append(line.strip())
        elif para:
            break
    return " ".join(para)


def load_pack(folder: Path, source: str) -> Pack:
    card = folder / "PACK.md"
    if not card.is_file():
        raise FolioError(f"{folder}: a pack needs a PACK.md")
    front, body = split(card.read_text(encoding="utf-8"), str(card))
    if front is None:
        raise FolioError(f"{card}: needs front matter")
    for key in front:
        if key not in _PACK_KEYS:
            raise FolioError(f"{card}: unknown key `{key}`")
    name = front.get("name")
    if name != folder.name:
        raise FolioError(f"{card}: `name` must be `{folder.name}`, the pack's folder")
    genres = list(front.get("genres") or [])
    for genre in genres:
        if not (folder / "genres" / genre / "GENRE.md").is_file():
            raise FolioError(f"{card}: lists genre `{genre}` but genres/{genre}/GENRE.md is missing")
    workflows = list(front.get("workflows") or [])
    for wf in workflows:
        if not (folder / "workflows" / f"{wf}.md").is_file():
            raise FolioError(f"{card}: lists workflow `{wf}` but workflows/{wf}.md is missing")
    return Pack(
        name=name,
        folder=folder,
        source=source,
        version=str(front.get("version", "")),
        genres=genres,
        workflows=workflows,
        rules=front.get("rules"),
        journal_kinds=[str(k) for k in front.get("journal_kinds") or []],
        purpose=_purpose(body),
    )


def available(library: Path, charter: Charter) -> dict[str, Pack]:
    """Every pack this library can use: its own `packs/` first, then folio's shipped ones."""
    found: dict[str, Pack] = {}
    own = library / "packs"
    if own.is_dir():
        for folder in sorted(own.iterdir()):
            if folder.is_dir():
                found[folder.name] = load_pack(folder, "library")
    for folder in sorted(data.shipped("packs").iterdir()):
        if folder.is_dir() and folder.name not in found:
            found[folder.name] = load_pack(folder, "shipped")
    for ref in charter.packs:
        if ref.git is not None:
            raise FolioError(
                f"pack `{ref.name}` is pinned to a git repository; git-pinned packs are not supported yet"
            )
        if ref.name not in found:
            raise FolioError(
                f"the charter switches on pack `{ref.name}`, which is neither shipped nor in packs/"
            )
        found[ref.name].on = True
    return found
