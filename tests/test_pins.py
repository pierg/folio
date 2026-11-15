"""Pinned pages: `rail.pinned` in the charter, the gate and the shell."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from folio import library
from folio.errors import FolioError
from folio.site.site import Site

from conftest import edit, folio, found

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "shell/folio.js").read_text(encoding="utf-8")


def test_nothing_is_pinned_by_default(sample: Path) -> None:
    lib = library.load_at(sample)
    assert lib.charter.rail_pinned == []
    assert Site.load(sample).site_data()["rail"]["pinned"] == []
    assert not found(sample, "rail-pinned")


def test_the_charter_pins_documents_in_its_order(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  pinned: [R-4, self-attention, lab-work]\nchecks:")
    assert library.load_at(sample).charter.rail_pinned == ["R-4", "self-attention", "lab-work"]
    assert Site.load(sample).site_data()["rail"]["pinned"] == ["R-4", "self-attention", "lab-work"]
    assert not found(sample, "rail-pinned")


def test_config_set_pins_and_unpins(sample: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert folio(sample, "config", "set", "rail.pinned", "softmax, Q-1", monkeypatch=monkeypatch) == 0
    assert yaml.safe_load((sample / "folio.yaml").read_text())["rail"] == {"pinned": ["softmax", "Q-1"]}
    assert folio(sample, "config", "set", "rail.pinned", "", monkeypatch=monkeypatch) == 0
    assert library.load_at(sample).charter.rail_pinned == []


def test_pins_must_be_a_list_of_ids(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  pinned: softmax\nchecks:")
    with pytest.raises(FolioError, match="rail.pinned"):
        library.load_at(sample)


@pytest.mark.parametrize("pins, says", [
    ("[no-such-page]", "`no-such-page`, which is no document"),
    ("[softmax, Softmax]", "lists `Softmax` twice"),
    ("[2026-10-02-lab-meeting]", "a journal entry"),
])
def test_the_gate_names_a_bad_pin(sample: Path, pins: str, says: str) -> None:
    edit(sample / "folio.yaml", "checks:", f"rail:\n  pinned: {pins}\nchecks:")
    problems = found(sample, "rail-pinned")
    assert [p.path for p in problems] == ["folio.yaml"]
    assert says in problems[0].message


def test_a_pin_matches_its_id_without_regard_to_case(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "rail:\n  pinned: [r-4]\nchecks:")
    assert not found(sample, "rail-pinned")


def test_the_shell_draws_a_pinned_section_from_the_site_data() -> None:
    assert "(D.site.rail || {}).pinned" in SHELL
    assert 'section("Pinned"' in SHELL


def test_the_header_has_a_pin_button_kept_in_this_browser() -> None:
    assert "function pinButton(doc)" in SHELL
    assert 'store("pins"' in SHELL
    assert "concat(localPins())" in SHELL  # the reader's pins follow the charter's in the rail
