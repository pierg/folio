"""Regression tests for the findings of the kb and lab trials, one or more per finding."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import edit, folio, found

from folio import library, redirects


def out_of(capsys) -> str:
    return capsys.readouterr().out


def commit_all(lib_dir: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    for args in (("init", "-q"), ("add", "-A"),
                 ("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "start")):
        subprocess.run(["git", "-C", str(lib_dir), *args], check=True, capture_output=True)


# Ids are unique across the library (kb 2, lab 1)

def test_new_refuses_an_id_another_genre_holds(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "new", "report", "pi-error-scaling", monkeypatch=monkeypatch) == 2
    assert "taken by content/protocols/pi-error-scaling.md" in capsys.readouterr().err
    assert folio(sample, "new", "note", "softmax", monkeypatch=monkeypatch) == 2


def test_journal_add_skips_a_taken_id(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "journal", "add", "--title", "Set up the library", "--description", "Again.",
                 "--body", "Again.", "--date", "2026-10-01", monkeypatch=monkeypatch) == 0
    assert "2026-10-01-set-up-the-library-2.md" in out_of(capsys)


# `folio new` writes the genre asked for, and a live document (kb 1, kb 8, decisions 9 and 10)

def test_new_variant_writes_its_own_genre(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "genre", "add", "beginner-entry", "--extends", "entry", monkeypatch=monkeypatch) == 0
    assert folio(sample, "new", "beginner-entry", "what-an-update-does", monkeypatch=monkeypatch) == 0
    page = (sample / "content/entries/what-an-update-does/index.html").read_text()
    assert '<meta name="genre" content="beginner-entry">' in page and "{genre}" not in page
    doc = library.load_at(sample).find("what-an-update-does")[0]
    assert doc.genre_name == "beginner-entry" and doc.is_a("entry")


def test_new_document_is_live_unless_held(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "note", "fresh-note", monkeypatch=monkeypatch) == 0
    page = (sample / "content/notes/fresh-note.html").read_text()
    assert 'name="status"' not in page
    assert library.load_at(sample).find("fresh-note")[0].status == "live"
    assert folio(sample, "new", "note", "held-note", "--status", "draft", monkeypatch=monkeypatch) == 0
    assert library.load_at(sample).find("held-note")[0].status == "draft"
    assert folio(sample, "new", "note", "odd-note", "--status", "locked", monkeypatch=monkeypatch) == 2


def test_new_help_names_the_field_flags(capsys) -> None:
    from folio.cli import main

    with pytest.raises(SystemExit):
        main(["new", "--help"])
    assert "--<field> <value>" in capsys.readouterr().out


def test_new_paper_title_fills_main_tex(sample: Path, monkeypatch) -> None:
    """lab 12: the title has one home, given once."""
    assert folio(sample, "new", "paper", "cache-paper", "--title", "Caches & tails",
                 monkeypatch=monkeypatch) == 0
    tex = (sample / "content/papers/cache-paper/main.tex").read_text()
    assert r"\title{Caches \& tails}" in tex
    assert 'content="Caches &amp; tails"' in (sample / "content/papers/cache-paper/index.html").read_text()


# `folio mv` of a never-committed document (lab 2)

def test_mv_of_a_never_committed_document_takes_the_new_id(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "mv", "flashattention-tiling", "tiling", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "its id is now `tiling`" in out
    page = (sample / "content/notes/tiling.html").read_text()
    assert 'name="id"' not in page
    assert "content/notes/flashattention-tiling.html" not in redirects.load(sample)
    assert library.load_at(sample).find("tiling")


def test_mv_of_a_committed_document_keeps_its_id_and_says_it_staged(sample: Path, monkeypatch, capsys) -> None:
    commit_all(sample)
    assert folio(sample, "mv", "flashattention-tiling", "tiling", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "staged the rename" in out and "redirected content/notes/flashattention-tiling.html" in out
    assert library.load_at(sample).find("flashattention-tiling")[0].key == "content/notes/tiling.html"


# Orphans: `optional` needs a row or a link from a document on any map (kb 5, lab 6)

def test_optional_document_linked_from_a_map_that_is_not_on_the_home_page(sample: Path) -> None:
    (sample / "folio.yaml").write_text((sample / "folio.yaml").read_text()
                                       .replace("maps: [attention, lab-work]", "maps: [lab-work]"))
    orphans = {p.path for p in found(sample, "orphan")}
    # The concepts are linked from the attention map's documents, which are on a map: not orphans.
    assert "content/concepts/softmax/index.html" not in orphans
    assert "content/concepts/self-attention/index.html" not in orphans


# Without a library (lab 7)

def test_pack_list_and_genres_without_a_library(tmp_path: Path, monkeypatch, capsys) -> None:
    empty = tmp_path / "nothing"
    empty.mkdir()
    assert folio(empty, "pack", "list", "--json", monkeypatch=monkeypatch) == 0
    assert {p["name"] for p in json.loads(out_of(capsys))} >= {"lab", "knowledge-base"}
    assert folio(empty, "genres", "--json", monkeypatch=monkeypatch) == 0
    names = {g["name"] for g in json.loads(out_of(capsys))}
    assert {"concept", "result", "source"} <= names
    assert folio(empty, "genre", "concept", monkeypatch=monkeypatch) == 0
    assert folio(empty, "check", monkeypatch=monkeypatch) == 2


# Init, the home page's title, and config set (kb 3, kb 7, lab 8, lab 18, lab 20)

def test_init_name_purpose_gitignore_and_home_title(tmp_path: Path, monkeypatch, capsys) -> None:
    lib = tmp_path / "db-notes"
    assert folio(tmp_path, "init", "db-notes", "--name", "How databases store data",
                 "--purpose", "Notes on storage engines.", monkeypatch=monkeypatch) == 0
    home = (lib / "content/index.html").read_text()
    assert "<title>" not in home and 'name="title"' not in home
    assert 'content="Notes on storage engines."' in home
    assert (lib / ".gitignore").read_text().splitlines() == ["_site/", ".folio/serve.pid", ".folio/serve.log",
                                                                 ".folio/build/"]
    loaded = library.load_at(lib)
    assert loaded.find("home")[0].title == "How databases store data"
    capsys.readouterr()
    assert folio(lib, "config", "set", "name", "Storage engines", monkeypatch=monkeypatch) == 0
    catalog = json.loads((lib / ".folio/catalog.json").read_text())
    assert next(d for d in catalog["documents"] if d["id"] == "home")["title"] == "Storage engines"
    assert folio(lib, "check", monkeypatch=monkeypatch) == 0, out_of(capsys)


def test_config_set_keeps_order_and_comments(sample: Path, monkeypatch) -> None:
    charter = sample / "folio.yaml"
    charter.write_text("# the charter\n" + charter.read_text().replace(
        "purpose:", "# why it exists\npurpose:"))
    assert folio(sample, "config", "set", "name", "Attention library", monkeypatch=monkeypatch) == 0
    assert folio(sample, "config", "set", "home.maps", "lab-work,attention", monkeypatch=monkeypatch) == 0
    text = charter.read_text()
    assert text.startswith("# the charter\nfolio: 0.1.0\nname: Attention library\n# why it exists\npurpose:")
    assert "maps: [lab-work, attention]" in text
    keys = [line.split(":")[0] for line in text.splitlines() if line and line[0].isalpha()]
    assert keys[:4] == ["folio", "name", "purpose", "reader"]


# Annotations about the whole document (kb 4, decision 12)

def test_annotation_without_a_quote(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "annotations", "add", "softmax", "--kind", "question", "--body", "Too short?",
                 "--author", "owner", monkeypatch=monkeypatch) == 0
    assert folio(sample, "annotations", "list", monkeypatch=monkeypatch) == 0
    assert "(the whole document)" in out_of(capsys)
    assert found(sample, "stale-quote") == []


# Cite (kb 17, lab 11)

def test_cite_takes_a_path_and_gives_one_form(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "cite", "content/results/R-4.md", "--json", monkeypatch=monkeypatch) == 0
    rows = json.loads(out_of(capsys))
    assert len(rows) == 1 and rows[0]["markup"]["markdown"] == "`R-4`"
    assert folio(sample, "cite", "softmax", "--json", monkeypatch=monkeypatch) == 0
    row = json.loads(out_of(capsys))[0]
    assert row["markup"]["markdown"] == "`softmax`" and row["markup"]["latex"] == r"\fcite{softmax}"


# Map rows in place (kb 15, lab 16)

def test_map_add_group_and_after(sample: Path, monkeypatch) -> None:
    assert folio(sample, "map", "add", "attention", "self-attention", "--after", "softmax",
                 monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/attention.html").read_text()
    assert text.index("/content/concepts/softmax/") < text.index("/content/concepts/self-attention/") \
        < text.index("/content/notes/flashattention-tiling.html")
    assert folio(sample, "map", "add", "lab-work", "softmax", "--group", "Background",
                 monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/lab-work.html").read_text()
    assert '<h2 id="background">Background</h2>\n<ul class="rows">\n<li><a href="/content/concepts/softmax/"' in text
    assert folio(sample, "map", "add", "attention", "tiled-attention", "--group", "Reading",
                 monkeypatch=monkeypatch) == 2  # already listed
    assert folio(sample, "map", "rm", "attention", "tiled-attention", monkeypatch=monkeypatch) == 0
    assert folio(sample, "map", "add", "attention", "tiled-attention", "--group", "basics",
                 monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/attention.html").read_text()
    basics = text[text.index('id="basics"'):text.index('id="reading"')]
    assert "/content/papers/tiled-attention/" in basics
