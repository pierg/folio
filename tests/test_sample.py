from __future__ import annotations

import json
from pathlib import Path

from conftest import FIXTURE, folio, problems

from folio import indexer, library


def test_sample_passes_with_no_problems() -> None:
    assert [p.line() for p in problems(FIXTURE)] == []


def test_sample_indices_are_current() -> None:
    assert indexer.stale(library.load_at(FIXTURE)) == []


def test_sample_uses_every_core_and_pack_genre() -> None:
    lib = library.load_at(FIXTURE)
    used = {d.genre_name for d in lib.documents}
    core = {"concept", "note", "entry", "map", "guide", "project", "journal", "paper"}
    packs = {"source", "reading", "survey", "question", "protocol", "result", "claim", "report"}
    assert core | packs <= used


def test_derived_status_and_ids() -> None:
    lib = library.load_at(FIXTURE)
    by = {d.id: d for d in lib.documents if d.genre_name != "reading"}
    assert by["R-3"].status == "superseded"
    assert by["R-4"].status == "live"
    assert by["home"].is_home
    assert by["2026-10-01-set-up-the-library"].genre_name == "journal"
    assert len(lib.find("2017-attention-is-all-you-need")) == 1
    assert lib.find("2017-attention-is-all-you-need-reading")[0].is_a("reading")


def test_index_contents() -> None:
    lib = library.load_at(FIXTURE)
    built = {k: json.loads(v) for k, v in indexer.build(lib).items()}
    chapters = built["nav.json"]["content/guides/attention-from-scratch/index.html"]["chapters"]
    assert [c["number"] for c in chapters] == [1, 2]
    journal = built["journal.json"]
    assert [e["date"] for e in journal] == sorted((e["date"] for e in journal), reverse=True)
    assert {c["question"] for c in built["cards.json"]} == {
        "Why subtract the maximum before the softmax?", "Why does the paper scale the dot products?"}
    q = built["backlinks.json"]["content/questions/Q-1.md"]
    assert q["fields"] == {"question": ["content/protocols/pi-error-scaling.md"]}
    r1 = built["backlinks.json"]["content/results/R-3.md"]
    assert r1["superseded_by"] == ["content/results/R-4.md"]
    home = built["backlinks.json"]["content/index.html"]
    assert [a["kind"] for a in home["about"]] == ["decision"]
    paper = [d for d in built["catalog.json"]["documents"] if d["id"] == "tiled-attention"][0]
    assert paper["url"] == "/content/papers/tiled-attention/"
    assert paper["title"] == "Tiled attention"


def test_index_writes_nothing_when_current(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    assert "current" in capsys.readouterr().out
