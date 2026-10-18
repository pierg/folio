"""`folio paper build`, `freeze` and `versions`; the abstract and versions on the landing page."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import zlib
from pathlib import Path

import pytest
from conftest import edit, folio, found

from folio import indexer, library
from folio.site.site import Site, export_site

PAPER = "content/papers/tiled-attention"
HAS_LATEXMK = shutil.which("latexmk") is not None
needs_latex = pytest.mark.skipif(not HAS_LATEXMK, reason="latexmk is not installed, so no paper can be built")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false",
                    *args], cwd=repo, check=True, capture_output=True)


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A", ".")
    git(repo, "commit", "-q", "-m", message)


def catalog_entry(lib_dir: Path) -> dict:
    entries = indexer.catalog(library.load_at(lib_dir))["documents"]
    return next(e for e in entries if e["id"] == "tiled-attention")


def uris(pdf: Path) -> list[bytes]:
    data = pdf.read_bytes()
    found_uris = re.findall(rb"/URI\s*\(([^)]*)\)", data)
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            found_uris += re.findall(rb"/URI\s*\(([^)]*)\)", zlib.decompress(match.group(1)))
        except zlib.error:
            continue
    return found_uris


def test_abstract_is_read_from_the_source(sample: Path) -> None:
    entry = catalog_entry(sample)
    assert entry["abstract"] == "Attention computed one tile of keys at a time is exact when the softmax is rescaled."
    assert entry["versions"] == []
    edit(sample / f"{PAPER}/main.tex", "is rescaled.", "is rescaled, as \\fcite{softmax} defines it.\n\nA second \\emph{point}.")
    assert catalog_entry(sample)["abstract"] == (
        "Attention computed one tile of keys at a time is exact when the softmax is rescaled, as softmax "
        "defines it.\n\nA second point.")


def test_build_needs_latexmk(sample: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("folio.paper.shutil.which", lambda name: None)
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 2
    assert "latexmk" in capsys.readouterr().err


def test_build_refuses_an_unknown_fcite(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / f"{PAPER}/main.tex", r"\fcite{softmax}", r"\fcite{no-such}")
    monkeypatch.setattr("folio.paper.shutil.which", lambda name: "/bin/true")
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 2
    assert "\\fcite{no-such} names no document" in capsys.readouterr().err


def test_freeze_needs_a_slug_name(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "paper", "freeze", "tiled-attention", "--version", "Final 1", monkeypatch=monkeypatch) == 2
    assert folio(sample, "paper", "freeze", "tiled-attention", monkeypatch=monkeypatch) == 2
    assert folio(sample, "paper", "build", "softmax", monkeypatch=monkeypatch) == 2
    assert "not a paper" in capsys.readouterr().err


@needs_latex
def test_build_freeze_and_publish(sample: Path, monkeypatch, capsys) -> None:
    (sample / ".gitignore").write_text("_site/\n.folio/build/\n")
    git(sample, "init", "-q")
    commit(sample, "first")

    # Without a site_url, an \fcite prints its id and links nowhere.
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
    pdf = sample / ".folio/build/tiled-attention/main.pdf"
    assert pdf.is_file() and uris(pdf) == []
    with (sample / "folio.yaml").open("a") as f:
        f.write("site_url: https://example.org/notes/\n")
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
    cites = (sample / ".folio/build/tiled-attention/folio-cites.tex").read_text()
    assert "\\foliocite{softmax}{Softmax}{https://example.org/notes/content/concepts/softmax/}" in cites
    assert uris(pdf) == [b"https://example.org/notes/content/concepts/softmax/"]
    commit(sample, "site url")  # the build folder stays out of git
    assert "folio-cites" not in subprocess.run(["git", "ls-files"], cwd=sample, capture_output=True, text=True).stdout

    # Freeze v1, edit the source (allowed), freeze v2.
    capsys.readouterr()
    assert folio(sample, "paper", "freeze", "tiled-attention", "--version", "v1", monkeypatch=monkeypatch) == 0
    assert f"created {PAPER}/versions/v1/paper.pdf" in capsys.readouterr().out
    assert folio(sample, "paper", "versions", "tiled-attention", monkeypatch=monkeypatch) == 0
    assert "v1" in (out := capsys.readouterr().out) and "uncommitted" in out
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    commit(sample, "freeze v1")
    edit(sample / f"{PAPER}/main.tex", "Background", "Context")
    assert folio(sample, "paper", "freeze", "tiled-attention", "--version", "v1", monkeypatch=monkeypatch) == 2
    assert "never replaced" in capsys.readouterr().err
    assert folio(sample, "paper", "freeze", "tiled-attention", "--version", "v2", monkeypatch=monkeypatch) == 0
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    commit(sample, "freeze v2")
    assert folio(sample, "check", monkeypatch=monkeypatch) == 0
    capsys.readouterr()
    assert folio(sample, "paper", "versions", "tiled-attention", "--json", monkeypatch=monkeypatch) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["name"] for r in rows] == ["v1", "v2"] and all(r["date"] != "uncommitted" for r in rows)
    assert "Background" in (sample / f"{PAPER}/versions/v1/main.tex").read_text()
    assert "Context" in (sample / f"{PAPER}/versions/v2/main.tex").read_text()

    # A committed version never changes: neither its source, nor its PDF, nor a new file there.
    edit(sample / f"{PAPER}/versions/v1/main.tex", "Background", "Setting")
    msgs = found(sample, "permanent")
    assert [p.path for p in msgs] == [f"{PAPER}/versions/v1/main.tex"]
    git(sample, "checkout", "-q", "--", f"{PAPER}/versions/v1/main.tex")
    (sample / f"{PAPER}/versions/v2/paper.pdf").write_bytes(b"%PDF-1.4 changed")
    (sample / f"{PAPER}/versions/v1/notes.txt").write_text("later")
    assert sorted(p.path for p in found(sample, "permanent")) == [f"{PAPER}/versions/v1/main.tex",
                                                                    f"{PAPER}/versions/v2/main.tex"]
    git(sample, "checkout", "-q", "--", f"{PAPER}/versions/v2/paper.pdf")
    (sample / f"{PAPER}/versions/v1/notes.txt").unlink()
    assert found(sample, "permanent") == []

    # The landing page's data: abstract, versions, the current build. The site serves both PDFs.
    entry = catalog_entry(sample)
    assert entry["abstract"].startswith("Attention computed")
    assert [(v["name"], v["pdf"]) for v in entry["versions"]] == [
        ("v1", f"{PAPER}/versions/v1/paper.pdf"), ("v2", f"{PAPER}/versions/v2/paper.pdf")]
    site = Site.load(sample)
    data = site.site_data()
    assert data["builds"] == {f"{PAPER}/main.tex": f"/{PAPER}/paper.pdf"}
    assert f"{PAPER}/versions/v1/main.tex" in data["dates"]
    out = sample.parent / "site"
    written, _ = export_site(sample, out)
    for path in (f"{PAPER}/paper.pdf", f"{PAPER}/versions/v1/paper.pdf", f"{PAPER}/versions/v2/paper.pdf"):
        assert path in written and (out / path).read_bytes().startswith(b"%PDF")
    assert (out / f"{PAPER}/paper.pdf").read_bytes() == pdf.read_bytes()
    exported = json.loads((out / ".folio/catalog.json").read_text())
    paper = next(d for d in exported["documents"] if d["id"] == "tiled-attention")
    assert paper["abstract"] and len(paper["versions"]) == 2
