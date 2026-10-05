from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import FIXTURE, edit, folio

from folio import __version__
from folio.cli import LATER, main, parser
from folio.links import resolve_href


def test_help_lists_every_command(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for name in ["init", "check", "index", "genres", "genre", "workflows", "workflow", "new", "journal",
                 "cite", "config", "pack", "version", *LATER]:
        assert name in out
    assert parser().prog == "folio"


def test_version(capsys) -> None:
    assert main(["version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_later_commands_say_so(sample: Path, monkeypatch, capsys) -> None:
    if not LATER:
        pytest.skip("every command is available")
    assert folio(sample, next(iter(LATER)), monkeypatch=monkeypatch) == 2
    assert "not available" in capsys.readouterr().err


def test_check_output_and_exit(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "the exact result.", "{{more}}")
    before = {p: p.read_bytes() for p in sample.rglob("*") if p.is_file()}
    assert folio(sample, "check", monkeypatch=monkeypatch) == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[:-1] == sorted(lines[:-1])
    assert "content/notes/flashattention-tiling.html: error placeholder: placeholder left: {{more}}" in lines
    assert lines[-1].startswith("folio check:")
    assert {p: p.read_bytes() for p in sample.rglob("*") if p.is_file()} == before
    assert folio(sample, "check", "--json", monkeypatch=monkeypatch) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["errors"] >= 1 and {"path", "severity", "check", "message"} <= set(data["problems"][0])


def test_warnings_do_not_fail(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / "content/projects/attention-kernel/index.html", "2026-09-20", "2025-01-01")
    folio(sample, "index", monkeypatch=monkeypatch)
    assert folio(sample, "check", monkeypatch=monkeypatch) == 0
    assert "warning stale_after_days" in capsys.readouterr().out


def test_genres_listing(monkeypatch, capsys) -> None:
    assert folio(FIXTURE, "genres", "--json", monkeypatch=monkeypatch) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert rows["result"]["source"] == "pack:lab" and rows["note"]["source"] == "core"
    assert len(rows) == 16


def test_resolve_href() -> None:
    lib = FIXTURE
    page = "content/maps/attention.html"
    assert resolve_href(lib, page, "/content/concepts/softmax/") == "content/concepts/softmax/index.html"
    assert resolve_href(lib, page, "/content/concepts/softmax") == "content/concepts/softmax/index.html"
    assert resolve_href(lib, page, "../notes/flashattention-tiling.html#x") == "content/notes/flashattention-tiling.html"
    assert resolve_href(lib, page, "/content/results/R-3.html") == "content/results/R-3.md"
    assert resolve_href(lib, page, "/assets/refs.bib") == "assets/refs.bib"
    assert resolve_href(lib, page, "/content/nope/") is None
