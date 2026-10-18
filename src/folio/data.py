"""Where folio's shipped genres, packs and skills live."""

from __future__ import annotations

from pathlib import Path

from .errors import FolioError

_SHIPPED = ("genres", "packs", "skills", "shell", "craft")


def data_root() -> Path:
    """The folder holding `genres/`, `packs/` and `skills/`.

    An installed wheel carries them in `folio/_data/`; a source checkout has
    them at the repository root, two levels above this package.
    """
    packaged = Path(__file__).resolve().parent / "_data"
    if (packaged / "genres").is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "genres").is_dir():
        return checkout
    raise FolioError(
        f"cannot find folio's shipped genres: looked in {packaged} and {checkout}"
    )


def shipped(name: str) -> Path:
    if name not in _SHIPPED:
        raise ValueError(name)
    return data_root() / name
