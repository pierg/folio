"""The rail's evidence genres: `rail.evidence` in the charter, the packs' default, the gate and the shell."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from folio import charter, library
from folio.errors import FolioError
from folio.packs import load_pack
from folio.site.site import Site

from conftest import edit, folio, found

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "shell/folio.js").read_text(encoding="utf-8")
CSS = (ROOT / "shell/folio.css").read_text(encoding="utf-8")


def test_the_lab_pack_keeps_protocols_and_results_apart_by_default(sample: Path) -> None:
    lib = library.load_at(sample)
    assert lib.charter.rail_evidence is None
    assert lib.registry.packs["lab"].evidence == ["protocol", "result"]
    assert lib.rail_evidence() == ["protocol", "result"]
    assert Site.load(sample).site_data()["rail"] == {"evidence": ["protocol", "result"]}


def test_without_the_lab_pack_there_is_no_evidence(sample: Path) -> None:
    edit(sample / "folio.yaml", "packs: [lab, knowledge-base]", "packs: [knowledge-base]")
    assert library.load_at(sample).rail_evidence() == []


def test_a_genre_switched_off_leaves_the_packs_evidence(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "genres:\n  protocol: { enabled: false }\nchecks:")
    assert library.load_at(sample).rail_evidence() == ["result"]


def test_the_charter_sets_the_evidence_and_wins_over_the_packs(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  evidence: [result, source]\nchecks:")
    lib = library.load_at(sample)
    assert lib.rail_evidence() == ["result", "source"]
    assert Site.load(sample).site_data()["rail"]["evidence"] == ["result", "source"]
    assert not found(sample, "rail-genres")


def test_an_empty_list_keeps_every_genre_with_the_reading_genres(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  evidence: []\nchecks:")
    assert library.load_at(sample).rail_evidence() == []
    assert Site.load(sample).site_data()["rail"] == {"evidence": []}


@pytest.mark.parametrize("bad, message", [
    ({"rail": {"evidence": "protocol"}}, "rail.evidence"),
    ({"rail": {"evidence": ["result", "result"]}}, "listed twice"),
    ({"rail": {"order": ["report"]}}, "rail.order"),
    ({"rail": ["protocol"]}, "`rail` must be a mapping"),
])
def test_the_rail_block_is_checked(sample: Path, bad: dict, message: str) -> None:
    with pytest.raises(FolioError, match=message):
        charter.parse(bad, sample / "folio.yaml")


def test_the_gate_names_an_unknown_evidence_genre(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  evidence: [protocol, experiment]\nchecks:")
    problems = found(sample, "rail-genres")
    assert [p.path for p in problems] == ["folio.yaml"]
    assert "`experiment`" in problems[0].message and "no genre" in problems[0].message
    assert problems[0].severity == "error"


def test_the_gate_names_an_evidence_genre_whose_pack_is_off(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  evidence: [result, source]\nchecks:")
    edit(sample / "folio.yaml", "packs: [lab, knowledge-base]", "packs: [lab]")
    problems = found(sample, "rail-genres")
    assert len(problems) == 1 and "`source`" in problems[0].message and "knowledge-base" in problems[0].message


def test_a_pack_lists_only_its_own_genres_as_evidence(tmp_path: Path) -> None:
    pack = tmp_path / "mine"
    (pack / "genres" / "trial").mkdir(parents=True)
    (pack / "genres" / "trial" / "GENRE.md").write_text("---\nname: trial\n---\n")
    (pack / "PACK.md").write_text("---\nname: mine\ngenres: [trial]\nevidence: [trial, result]\n---\n# Mine\n")
    with pytest.raises(FolioError, match="`result`"):
        load_pack(pack, "library")
    (pack / "PACK.md").write_text("---\nname: mine\ngenres: [trial]\nevidence: [trial]\n---\n# Mine\n")
    assert load_pack(pack, "library").evidence == ["trial"]


def test_config_reads_and_sets_the_evidence(sample: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    assert folio(sample, "config", "get", "rail.evidence", monkeypatch=monkeypatch) == 0
    assert yaml.safe_load(capsys.readouterr().out) == ["protocol", "result"]
    assert folio(sample, "config", "set", "rail.evidence", "result", monkeypatch=monkeypatch) == 0
    assert yaml.safe_load((sample / "folio.yaml").read_text())["rail"] == {"evidence": ["result"]}
    assert library.load_at(sample).rail_evidence() == ["result"]


def test_the_shell_lists_evidence_last_and_apart() -> None:
    # The rail reads the site data's evidence genres, orders the reading genres by reading
    # order only when there are some, and gives the evidence one closed group of its own.
    assert "(D.site.rail || {}).evidence" in SHELL
    assert 'section("By genre", reading.map(' in SHELL
    assert 'reading.sort(evidence.length ? function (a, b) { return genreRank(a) - genreRank(b)' in SHELL
    assert 'group("evidence", head, proof, false,' in SHELL
    assert '"f-rsection f-revidence"' in SHELL and ".f-revidence" in CSS
    reading = SHELL.split("var READING = [", 1)[1].split("];", 1)[0]
    order = [g.strip().strip('"') for g in reading.split(",")]
    assert order.index("report") < order.index("concept") < order.index("protocol") < order.index("result")
