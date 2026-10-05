"""`folio genres`, `folio genre ...`, `folio workflows` and `folio workflow add`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import FolioError
from ..genres import Genre
from ..library import Library
from ..util import is_slug


def _rel(lib: Library, path: Path) -> str:
    try:
        return path.relative_to(lib.root).as_posix()
    except ValueError:
        return str(path)


def _origin(genre: Genre) -> str:
    if genre.source == "pack":
        return f"pack:{genre.pack}"
    return genre.source


def genre_rows(lib: Library, every: bool = False) -> list[dict[str, Any]]:
    """The genres a library can use now; with `every`, also those of packs that are off."""
    rows = []
    for genre in (lib.registry.genres.values() if every else lib.registry.active()):
        overridden = genre.source != "library" and any(
            lib.root in f.parents for f in genre.card_files)
        rows.append({
            "name": genre.name, "source": _origin(genre), "pack": genre.pack,
            "extends": genre.extends, "format": genre.format, "path": genre.path,
            "parts": {p.name: p.path for p in genre.parts.values()},
            "card": _rel(lib, genre.card_files[-1]),
            "cards": [_rel(lib, f) for f in genre.card_files],
            "overridden": overridden,
        })
    return rows


def card(lib: Library, name: str) -> str:
    return lib.registry.get(name).card_text()


_NEW_CARD = """---
name: {name}
format: html
path: content/{name}s/{{slug}}.html
id: slug
skeleton: skeleton.html
lives: revised
states: [draft, live, historical, retired]
checks: {{}}
on_map: required
---

# {title}

{{{{One sentence: the job this genre does that no other does.}}}}

## Reader

{{{{Who reads it and what they already know.}}}}

## Voice

{{{{The register, in a few plain sentences, with one short example.}}}}

## Metadata

No fields beyond the core. {{{{What a good title and description say for this genre.}}}}

## Shape

{{{{The body's parts, in order, and the markup that carries each one.}}}}

## Forbidden

- {{{{What this genre never does, and which check catches it, or "judged, not checked".}}}}

## Steps

- {{{{What is special about writing or revising this genre.}}}}

## Lifecycle

{{{{How it changes over time, and what it is promoted to or from.}}}}
"""

_NEW_VARIANT = """---
name: {name}
extends: {parent}
---

# {title}

{{{{One sentence: the second audience this variant of {parent} is for.}}}}

## Voice

{{{{The register for that audience, with one short example.}}}}
"""

_NEW_SKELETON = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{{{title}}}}</title>
<meta name="genre" content="{{genre}}">
<meta name="title" content="{{{{title}}}}">
<meta name="description" content="{{{{one sentence: what this document is}}}}">
<meta name="tags" content="{{{{tags}}}}">
<link rel="stylesheet" href="/shell/folio.css">
<script src="/shell/folio.js" defer></script>
</head>
<body>
<main>

<p>{{{{the body}}}}</p>

</main>
</body>
</html>
"""

_OVERRIDE = """---
name: {name}
---
"""

_NEW_WORKFLOW = """---
name: {name}
summary: "{{{{One line: what you ask for and what you get.}}}}"
inputs:
  - "{{{{name}}}}: {{{{what the run skill asks for, if the request did not give it}}}}"
produces: []
---

# {title}

{{{{One sentence: what you ask for and what you get.}}}}

## Steps

1. {{{{A step, naming the skill or command it uses. Every document goes through the write skill.}}}}

## Stops

- {{{{When the workflow stops and asks the owner instead of guessing.}}}}

## Done when

- `folio check` passes.
"""


def _title(name: str) -> str:
    return name.replace("-", " ").capitalize()


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        raise FolioError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def add(lib: Library, name: str, extends: str | None) -> list[str]:
    if not is_slug(name):
        raise FolioError(f"a genre name is lowercase words joined by hyphens, not `{name}`")
    if name in lib.registry.genres:
        raise FolioError(f"genre `{name}` exists; use `folio genre override {name}` to change it")
    folder = lib.root / "genres" / name
    if extends is not None:
        lib.registry.get(extends)
        _write_new(folder / "GENRE.md", _NEW_VARIANT.format(name=name, parent=extends, title=_title(name)))
        return [f"created genres/{name}/GENRE.md"]
    _write_new(folder / "GENRE.md", _NEW_CARD.format(name=name, title=_title(name)))
    _write_new(folder / "skeleton.html", _NEW_SKELETON.format())
    return [f"created genres/{name}/GENRE.md", f"created genres/{name}/skeleton.html"]


def override(lib: Library, name: str) -> list[str]:
    genre = lib.registry.get(name)
    if genre.source == "library":
        raise FolioError(f"genre `{name}` is this library's own; edit genres/{name}/GENRE.md")
    card_path = lib.root / "genres" / name / "GENRE.md"
    _write_new(card_path, _OVERRIDE.format(name=name))
    return [f"created genres/{name}/GENRE.md"]


def workflow_rows(lib: Library) -> list[dict[str, Any]]:
    return [
        {"name": wf.name, "source": f"pack:{wf.pack}" if wf.pack else wf.source,
         "summary": wf.summary, "file": _rel(lib, wf.file)}
        for wf in sorted(lib.registry.workflows.values(), key=lambda w: w.name)
    ]


def workflow_add(lib: Library, name: str) -> list[str]:
    if not is_slug(name):
        raise FolioError(f"a workflow name is lowercase words joined by hyphens, not `{name}`")
    if name in lib.registry.workflows:
        raise FolioError(f"workflow `{name}` exists ({workflow_source(lib, name)})")
    _write_new(lib.root / "workflows" / f"{name}.md", _NEW_WORKFLOW.format(name=name, title=_title(name)))
    return [f"created workflows/{name}.md"]


def workflow_source(lib: Library, name: str) -> str:
    return _rel(lib, lib.registry.workflows[name].file)
