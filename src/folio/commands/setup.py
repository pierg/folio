"""`folio init`: a new library, its home page and the skills. The set-up skill records the setup in the journal."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .. import __version__, data, indexer
from .. import library as library_mod
from ..charter import CHARTER, write as write_charter
from ..documents import HOME_PATH
from ..errors import FolioError
from ..util import html_attr

_HOME = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="genre" content="map">
<meta name="description" content="{description}">
<link rel="stylesheet" href="/shell/folio.css">
<script src="/shell/folio.js" defer></script>
</head>
<body>
<main>

<ul class="rows">
</ul>

</main>
</body>
</html>
"""


def project_root(folder: Path) -> Path:
    """Where agents look for skills: the enclosing git work tree, or the library itself."""
    if shutil.which("git") is None:
        return folder
    result = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return folder
    return Path(result.stdout.strip()).resolve()


def install_skills(root: Path) -> list[str]:
    """Copy folio's skills into `.agents/skills/`, with `.claude/skills` linked to it."""
    changed = []
    target = root / ".agents" / "skills"
    target.mkdir(parents=True, exist_ok=True)
    for skill in sorted(data.shipped("skills").iterdir()):
        if not (skill / "SKILL.md").is_file():
            continue
        dest = target / skill.name
        existed = dest.exists()
        if existed:
            shutil.rmtree(dest)
        shutil.copytree(skill, dest)
        changed.append(f"{'updated' if existed else 'created'} {dest.relative_to(root)}/")
    link = root / ".claude" / "skills"
    wanted = os.path.join("..", ".agents", "skills")
    if link.is_symlink():
        if os.readlink(link) != wanted:
            raise FolioError(f"{link} links to {os.readlink(link)}, not {wanted}; move it aside first")
    elif link.exists():
        raise FolioError(f"{link} exists and is not a link to {wanted}; move it aside first")
    else:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(wanted)
        changed.append(f"linked .claude/skills -> {wanted}")
    return changed


# Never committed: the exported site, and the files `folio up` keeps while it serves.
GITIGNORE = ("_site/", ".folio/serve.pid", ".folio/serve.log", ".folio/build/")


def write_gitignore(folder: Path) -> list[str]:
    """Add folio's lines to the library's `.gitignore`, keeping any it already has."""
    path = folder / ".gitignore"
    have = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    missing = [line for line in GITIGNORE if line not in have]
    if not missing:
        return []
    path.write_text("\n".join(have + missing) + "\n", encoding="utf-8")
    return [f"{'updated' if have else 'created'} .gitignore"]


def init(folder: Path, name: str | None = None, purpose: str | None = None) -> list[str]:
    folder = folder.resolve()
    if (folder / CHARTER).exists():
        raise FolioError(f"{folder / CHARTER} already exists; this is a library already")
    if (folder / HOME_PATH).exists():
        raise FolioError(f"{folder / HOME_PATH} already exists")
    folder.mkdir(parents=True, exist_ok=True)
    changed = []
    name = (name or "").strip() or folder.name
    purpose = (purpose or "").strip()
    write_charter(folder / CHARTER, {
        "folio": __version__, "name": name, "purpose": purpose, "packs": [], "home": {"maps": []},
    })
    changed.append(f"created {CHARTER}")
    home = folder / HOME_PATH
    home.parent.mkdir(parents=True, exist_ok=True)
    # The home page has no title of its own: the shell and the indices use the charter's name.
    home.write_text(_HOME.format(description=html_attr(purpose or "The front door of this library.")),
                    encoding="utf-8")
    changed.append(f"created {HOME_PATH}")
    for sub in ("figures", "data"):
        keep = folder / "assets" / sub / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch()
        changed.append(f"created assets/{sub}/")
    (folder / "assets" / "refs.bib").touch()
    changed.append("created assets/refs.bib")
    changed.extend(write_gitignore(folder))
    root = project_root(folder)
    changed.extend(install_skills(root))
    lib = library_mod.load_at(folder)
    changed.extend(f"wrote {p}" for p in indexer.write(lib))
    return changed
