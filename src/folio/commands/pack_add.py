"""`folio pack add <name> --genres .. --workflows ..`: the library's own genres and workflows become a pack.

The genre folders and workflow files move into `packs/<name>/`, each card
and workflow names the pack, a PACK.md is written in pack-format.md's shape
with `{{...}}` text for the configure skill to fill, and the pack is
switched on in the charter so every document keeps its genre.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import library as library_mod
from ..edits import set_front
from ..errors import FolioError
from ..frontmatter import dump
from ..library import Library
from ..util import as_list, is_slug
from . import charter_cmds

_PACK_MD = """---
{front}---

# {title}

{{{{One sentence: what kind of work this pack is for.}}}}

## What it adds

{adds}

## When to switch it on

{{{{The kind of library that needs it, and what a library without it loses.}}}}

## What switching it on changes

Nothing is rewritten. {{{{What its rules flag in an existing library, and how the organise skill proposes the fixes.}}}}

## Working with other packs

{{{{Anything a reader of two packs together should know.}}}}
"""


def add(lib: Library, name: str, genres: str | None, workflows: str | None) -> list[str]:
    if not is_slug(name):
        raise FolioError(f"a pack name is lowercase words joined by hyphens, not `{name}`")
    if name in lib.registry.packs:
        raise FolioError(f"pack `{name}` exists ({lib.registry.packs[name].source})")
    genre_names, workflow_names = as_list(genres), as_list(workflows)
    if not genre_names and not workflow_names:
        raise FolioError("name at least one genre (--genres) or workflow (--workflows) to move into the pack")
    for g in genre_names:
        genre = lib.registry.get(g)
        if genre.source != "library" or len(genre.card_files) != 1:
            raise FolioError(f"genre `{g}` is not this library's own (it comes from {genre.source}); "
                             "a pack never redefines a core or pack genre")
        if genre.extends and lib.registry.genres[genre.extends].source == "library" \
                and genre.extends not in genre_names:
            raise FolioError(f"genre `{g}` extends the library's `{genre.extends}`; move both together")
    for w in workflow_names:
        wf = lib.registry.workflows.get(w)
        if wf is None:
            raise FolioError(f"no workflow `{w}`; `folio workflows` lists them")
        if wf.source != "library":
            raise FolioError(f"workflow `{w}` is not this library's own (it comes from {wf.source})")

    root = lib.root
    folder = root / "packs" / name
    charter_before = (root / "folio.yaml").read_text(encoding="utf-8")
    changes: list[str] = []
    moved: list[tuple[Path, Path, Path, str]] = []
    try:
        for g in genre_names:
            src, dst = root / "genres" / g, folder / "genres" / g
            dst.parent.mkdir(parents=True, exist_ok=True)
            card = dst / "GENRE.md"
            moved.append((src, dst, card, (src / "GENRE.md").read_text(encoding="utf-8")))
            shutil.move(str(src), str(dst))
            card.write_text(set_front(card.read_text(encoding="utf-8"), "pack", name), encoding="utf-8")
            changes.append(f"moved genres/{g}/ -> packs/{name}/genres/{g}/ (card names pack `{name}`)")
        for w in workflow_names:
            src, dst = root / "workflows" / f"{w}.md", folder / "workflows" / f"{w}.md"
            dst.parent.mkdir(parents=True, exist_ok=True)
            moved.append((src, dst, dst, src.read_text(encoding="utf-8")))
            shutil.move(str(src), str(dst))
            dst.write_text(set_front(dst.read_text(encoding="utf-8"), "pack", name), encoding="utf-8")
            changes.append(f"moved workflows/{w}.md -> packs/{name}/workflows/{w}.md")
        front = dump({"name": name, "version": "0.1.0", "requires": {"folio": ">=0.1.0"},
                      "genres": genre_names, "workflows": workflow_names})
        adds = "\n".join([f"- **{g}**: {{{{what this genre is, in one line}}}}" for g in genre_names]
                         + [f"- **{w}** (workflow): {{{{what you ask for and what you get}}}}"
                            for w in workflow_names])
        (folder / "PACK.md").write_text(_PACK_MD.format(front=front, title=name.replace("-", " ").capitalize(),
                                                        adds=adds), encoding="utf-8")
        changes.append(f"created packs/{name}/PACK.md")
        for d in (root / "genres", root / "workflows"):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        changes.append(charter_cmds.pack_on(library_mod.load_at(root), name))
    except FolioError:
        for src, dst, card, text in reversed(moved):
            if card.is_file():
                card.write_text(text, encoding="utf-8")
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
        shutil.rmtree(folder, ignore_errors=True)
        (root / "folio.yaml").write_text(charter_before, encoding="utf-8")
        raise
    changes.append(f"note: packs/{name}/PACK.md has {{{{...}}}} text for the configure skill to fill")
    return changes
