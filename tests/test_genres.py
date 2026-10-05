from __future__ import annotations

from pathlib import Path

import pytest
from conftest import edit, folio, found

from folio import library
from folio.errors import FolioError


def test_lookup_order_and_sources(sample: Path) -> None:
    reg = library.load_at(sample).registry
    assert reg.genres["concept"].source == "core"
    assert reg.genres["result"].source == "pack" and reg.genres["result"].pack == "lab"
    assert reg.genres["result"].prefix == "R"


def test_override_merges_keys_and_sections(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "genre", "override", "concept", monkeypatch=monkeypatch) == 0
    card = sample / "genres/concept/GENRE.md"
    card.write_text("---\nname: concept\nchecks:\n  max_words: 10\n---\n\n## Voice\n\nWarm.\n")
    genre = library.load_at(sample).registry.genres["concept"]
    assert genre.checks["max_words"] == 10
    assert genre.checks["require"] == ["defn"]  # kept from the core card
    assert "Warm." in genre.body and "## Reader" in genre.body and "Impersonal" not in genre.body
    assert genre.skeleton_file("skeleton.html").parent.name == "concept"
    assert len(found(sample, "max_words")) == 2
    capsys.readouterr()
    assert folio(sample, "genre", "concept", monkeypatch=monkeypatch) == 0
    assert "max_words: 10" in capsys.readouterr().out


def test_variant_extends(sample: Path, monkeypatch) -> None:
    assert folio(sample, "genre", "add", "paper-workshop", "--extends", "paper", monkeypatch=monkeypatch) == 0
    reg = library.load_at(sample).registry
    variant = reg.genres["paper-workshop"]
    assert variant.lineage == ["paper-workshop", "paper"]
    assert variant.path == reg.genres["paper"].path and "landing" in variant.parts
    assert variant.skeleton_file("skeleton.tex").name == "skeleton.tex"
    # A variant's document shares the parent's path; its landing page names the genre.
    folder = sample / "content/papers/tiled-attention"
    edit(folder / "index.html", 'content="paper"', 'content="paper-workshop"')
    lib = library.load_at(sample)
    doc = [d for d in lib.documents if d.id == "tiled-attention"][0]
    assert doc.genre_name == "paper-workshop" and len(doc.files) == 2


def test_new_custom_genre_and_workflow(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "genre", "add", "derivation", monkeypatch=monkeypatch) == 0
    assert (sample / "genres/derivation/skeleton.html").is_file()
    assert folio(sample, "new", "derivation", "softmax-gradient", "--title", "Softmax gradient", monkeypatch=monkeypatch) == 0
    assert (sample / "content/derivations/softmax-gradient.html").is_file()
    assert folio(sample, "workflow", "add", "derive", monkeypatch=monkeypatch) == 0
    capsys.readouterr()
    assert folio(sample, "workflows", "--json", monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out
    assert '"derive"' in out and '"record-a-result"' in out
    assert folio(sample, "genre", "add", "concept", monkeypatch=monkeypatch) == 2


def test_genre_disabled_in_charter(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / "folio.yaml", "checks:\n", "genres:\n  survey: { enabled: false }\nchecks:\n")
    assert folio(sample, "genres", "--json", monkeypatch=monkeypatch) == 0
    assert '"survey"' not in capsys.readouterr().out
    assert folio(sample, "new", "survey", "x", monkeypatch=monkeypatch) == 2


def test_pack_genre_may_not_redefine_core(sample: Path) -> None:
    pack = sample / "packs/mine"
    (pack / "genres/note").mkdir(parents=True)
    (pack / "PACK.md").write_text("---\nname: mine\ngenres: [note]\n---\n\n# Mine\n\nMine.\n")
    (pack / "genres/note/GENRE.md").write_text("---\nname: note\npack: mine\n---\n")
    with pytest.raises(FolioError, match="unique"):
        library.load_at(sample)


def test_library_pack(sample: Path, monkeypatch) -> None:
    pack = sample / "packs/numerics"
    (pack / "genres/proof").mkdir(parents=True)
    (pack / "PACK.md").write_text("---\nname: numerics\ngenres: [proof]\n---\n\n# Numerics\n\nFor derivations.\n")
    (pack / "genres/proof/GENRE.md").write_text("---\nname: proof\npack: numerics\n---\n\n# Proof\n")
    (pack / "genres/proof/skeleton.html").write_text("<html><head></head><body></body></html>")
    assert not library.load_at(sample).registry.genres["proof"].active
    assert folio(sample, "pack", "on", "numerics", monkeypatch=monkeypatch) == 0
    assert library.load_at(sample).registry.genres["proof"].active


def test_unknown_card_check(sample: Path) -> None:
    (sample / "genres/note").mkdir(parents=True)
    (sample / "genres/note/GENRE.md").write_text("---\nname: note\nchecks: { max_wordz: 3 }\n---\n")
    with pytest.raises(FolioError, match="max_wordz"):
        library.load_at(sample)
