from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from folio import library
from folio.checks.run import run
from folio.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "sample"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOLIO_TODAY", "2026-10-03")


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    dest = tmp_path / "sample"
    shutil.copytree(FIXTURE, dest, symlinks=True)
    return dest


def problems(lib_dir: Path):
    return run(library.load_at(lib_dir))


def names(lib_dir: Path) -> set[str]:
    return {p.check for p in problems(lib_dir)}


def found(lib_dir: Path, check: str):
    return [p for p in problems(lib_dir) if p.check == check]


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def folio(lib_dir: Path, *args: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.chdir(lib_dir)
    return main(list(args))


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "chrome: renders a deck's PDF with Chrome; other tests run as if none were installed")


@pytest.fixture(autouse=True)
def _no_chrome_unless_asked(request, monkeypatch) -> None:
    """Only tests marked `chrome` render PDFs; the rest export decks without one, quickly."""
    if request.node.get_closest_marker("chrome") is None:
        from folio.site import pdf
        monkeypatch.setattr(pdf, "find_chrome", lambda: None)
