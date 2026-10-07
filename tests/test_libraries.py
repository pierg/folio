"""Links into another library the charter names (model §4, §10)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from conftest import edit, folio, found, problems

from folio import charter, library, redirects
from folio.errors import FolioError
from folio.site.site import Site

ENTRY = "content/entries/attention-is-quadratic/index.html"


@pytest.fixture
def pair(sample: Path, tmp_path: Path) -> tuple[Path, Path]:
    """The sample library, and a copy of it named `other` in its charter."""
    other = tmp_path / "other"
    shutil.copytree(sample, other, symlinks=True)
    with (sample / "folio.yaml").open("a") as fh:
        fh.write("libraries:\n  other:\n    path: ../other\n    url: http://localhost:5180/\n")
    return sample, other


def errors(lib_dir: Path) -> list[str]:
    return [p.line() for p in problems(lib_dir) if p.severity == "error"]


def out_of(capsys) -> str:
    return capsys.readouterr().out


def test_the_charter_names_libraries(pair: tuple[Path, Path]) -> None:
    sample, _ = pair
    lib = library.load_at(sample)
    ref = lib.charter.libraries["other"]
    assert (ref.path, ref.url) == ("../other", "http://localhost:5180")
    assert lib.charter.effective()["libraries"] == {"other": {"path": "../other", "url": "http://localhost:5180"}}
    for bad, words in (({"http": {"path": "x"}}, "the web already uses"),
                       ({"Other": {"path": "x"}}, "lowercase slug"),
                       ({"other": {"url": "http://x"}}, "needs a `path`"),
                       ({"other": {"path": "x", "url": "ftp://x"}}, r"http\(s\) address"),
                       ({"other": {"path": "x", "colour": "red"}}, "unknown key")):
        with pytest.raises(FolioError, match=words):
            charter.parse({"libraries": bad}, sample / "folio.yaml")


def test_a_link_into_another_library_is_checked_there(pair: tuple[Path, Path]) -> None:
    sample, other = pair
    edit(sample / ENTRY, "</main>",
         '<p>See <a href="other:/content/concepts/softmax/">softmax there</a> and '
         '<a href="other:/content/concepts/nothing/">nothing there</a>.</p>\n</main>')
    broken = [p.message for p in found(sample, "broken-link")]
    assert broken == ["`other:/content/concepts/nothing/` resolves to nothing in that library"]
    assert not found(sample, "library-link")
    # Without the other library on this machine, its links are not checked, and the gate says so once.
    shutil.rmtree(other)
    assert not found(sample, "broken-link")
    warned = found(sample, "library-link")
    assert [(p.path, p.severity, p.message) for p in warned] == [
        ("folio.yaml", "warning", "library `other` is not at `../other`, so its 2 links are not checked")]


def test_a_link_into_another_library_is_no_citation(pair: tuple[Path, Path], monkeypatch) -> None:
    sample, _ = pair
    edit(sample / ENTRY, "</main>", '<p><a href="other:/content/concepts/softmax/">softmax</a></p>\n</main>')
    lib = library.load_at(sample)
    links = [lk for lk in lib.links[ENTRY] if lk.kind == "library"]
    assert len(links) == 1 and links[0].resolved and links[0].docs == []
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    backlinks = json.loads((sample / ".folio/backlinks.json").read_text())
    assert "other:/content/concepts/softmax/" not in json.dumps(backlinks)
    assert not errors(sample)


def test_serve_and_export_send_the_link_to_the_library(pair: tuple[Path, Path], monkeypatch, tmp_path: Path) -> None:
    sample, _ = pair
    edit(sample / ENTRY, "</main>",
         '<p><a href="other:/content/concepts/softmax/#trap">softmax</a></p>\n</main>')
    with (sample / "content/claims/C-1.md").open("a") as fh:
        fh.write("\nSee [the claim there](other:/content/claims/C-1.md).\n")
    site = Site.load(sample)
    page = site.get(ENTRY).body.decode()
    assert 'href="http://localhost:5180/content/concepts/softmax/#trap" data-library="other"' in page
    record = site.get("content/claims/C-1.html").body.decode()
    assert 'href="http://localhost:5180/content/claims/C-1.html" data-library="other"' in record
    assert site.site_data()["libraries"] == {"other": {"url": "http://localhost:5180"}}
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    out = tmp_path / "site"
    assert folio(sample, "export", "--out", str(out), monkeypatch=monkeypatch) == 0
    assert 'data-library="other"' in (out / ENTRY).read_text()


def test_without_a_url_the_link_is_served_as_written(pair: tuple[Path, Path]) -> None:
    sample, _ = pair
    edit(sample / "folio.yaml", "    url: http://localhost:5180/\n", "")
    edit(sample / ENTRY, "</main>", '<p><a href="other:/content/concepts/softmax/">softmax</a></p>\n</main>')
    page = Site.load(sample).get(ENTRY).body.decode()
    assert 'href="other:/content/concepts/softmax/" data-library="other"' in page


def test_rm_retires_a_document_into_another_library(pair: tuple[Path, Path], monkeypatch, capsys) -> None:
    sample, _ = pair
    assert folio(sample, "map", "add", "attention", "self-attention", monkeypatch=monkeypatch) == 0
    edit(sample / ENTRY, "</main>",
         '<p>See <a class="defn-link" href="/content/concepts/self-attention/">self-attention</a>.</p>\n</main>')
    out_of(capsys)
    assert folio(sample, "rm", "self-attention", "--to", "other:softmax", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "redirected content/concepts/self-attention/index.html -> other:content/concepts/softmax/index.html" in out
    retired = (sample / "content/concepts/self-attention/index.html").read_text()
    assert '<meta name="status" content="retired">' in retired
    assert '<meta name="replaced_by" content="other:softmax">' in retired
    assert redirects.load(sample)["content/concepts/self-attention/index.html"] == \
        "other:content/concepts/softmax/index.html"
    assert "1 row dropped" in out
    assert "other:" not in (sample / "content/maps/attention.html").read_text()
    assert not any('defn-link" href="other:' in p.read_text() or 'class="defn-link" href="other:' in p.read_text()
                   for p in sample.rglob("*.html"))
    rewritten = [p for p in sample.rglob("*.html") if 'href="other:/content/concepts/softmax/' in p.read_text()]
    assert rewritten, "the links to the retired concept now lead into the other library"
    assert not any('href="/content/concepts/self-attention/' in p.read_text()
                   for p in sample.rglob("*.html") if "self-attention" not in str(p))
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    assert not errors(sample)
    # The old address, still linked from any frozen page, redirects into the other library.
    moved = Site.load(sample).get("content/concepts/self-attention/index.html").body.decode()
    assert 'url=http://localhost:5180/content/concepts/softmax/index.html' in moved


def test_an_old_address_redirected_elsewhere_is_checked_there(pair: tuple[Path, Path], monkeypatch) -> None:
    sample, other = pair
    assert folio(sample, "rm", "self-attention", "--to", "other:softmax", monkeypatch=monkeypatch) == 0
    edit(sample / ENTRY, "</main>", '<p><a href="/content/concepts/self-attention/">old</a></p>\n</main>')
    # A retired document stays at its address; once its file is gone, the redirect carries the link.
    shutil.rmtree(sample / "content/concepts/self-attention")
    assert not found(sample, "broken-link")
    shutil.rmtree(other / "content/concepts/softmax")
    assert any("self-attention" in p.message for p in found(sample, "broken-link"))


def test_rm_into_another_library_refusals(pair: tuple[Path, Path], monkeypatch, capsys) -> None:
    sample, other = pair
    assert folio(sample, "rm", "self-attention", "--to", "other:nothing", monkeypatch=monkeypatch) == 2
    assert folio(sample, "rm", "R-3", "--to", "other:softmax", monkeypatch=monkeypatch) == 2
    shutil.rmtree(other)
    assert folio(sample, "rm", "self-attention", "--to", "other:softmax", monkeypatch=monkeypatch) == 2
    assert "is not at `../other`" in capsys.readouterr().err


def test_cite_and_search_reach_the_other_library(pair: tuple[Path, Path], monkeypatch, capsys) -> None:
    sample, other = pair
    assert folio(sample, "cite", "other:softmax", "--json", monkeypatch=monkeypatch) == 0
    row = json.loads(out_of(capsys))[0]
    assert row["id"] == "other:softmax" and row["library"] == "other"
    assert row["markup"]["html"].startswith('<a href="other:/content/concepts/softmax/">')
    assert row["markup"]["latex"] is None
    assert folio(sample, "cite", "other:softmax", monkeypatch=monkeypatch) == 0
    assert "latex" not in out_of(capsys)
    edit(other / "content/concepts/self-attention/index.html", "</main>", "<p>Zebra.</p>\n</main>")
    assert folio(sample, "search", "zebra", "--all", monkeypatch=monkeypatch) == 0
    assert "[other] self-attention (concept, live)" in out_of(capsys)
