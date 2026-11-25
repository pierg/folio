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


def words(pdf: Path) -> str:
    """The PDF's text, one space between words; empty when pdftotext is not installed."""
    if shutil.which("pdftotext") is None:
        return ""
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return " ".join(text.split())


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
    # An \fcite is not part of the text: the abstract reads as the PDF prints it.
    edit(sample / f"{PAPER}/main.tex", "is rescaled.", "is rescaled\\fcite{softmax}.\n\nA second \\emph{point}.")
    assert catalog_entry(sample)["abstract"] == (
        "Attention computed one tile of keys at a time is exact when the softmax is rescaled.\n\nA second point.")


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

    # The PDF prints no id: the sentence around an \fcite stands on its own, and nothing links out.
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
    pdf = sample / ".folio/build/tiled-attention/main.pdf"
    assert pdf.is_file() and uris(pdf) == []
    text = words(pdf)
    assert "[softmax]" not in text and ("standard definition of the softmax, after [1]" in text or not text)
    with (sample / "folio.yaml").open("a") as f:
        f.write("site_url: https://example.org/notes/\n")
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
    cites = (sample / ".folio/build/tiled-attention/folio-cites.tex").read_text()
    assert "\\foliocite{softmax}{Softmax}{https://example.org/notes/content/concepts/softmax/}" in cites
    assert "\\folioshowids" not in cites and uris(pdf) == []
    # A review build prints each id after the text it backs, linked to its page.
    assert folio(sample, "paper", "build", "tiled-attention", "--ids", monkeypatch=monkeypatch) == 0
    cites = (sample / ".folio/build/tiled-attention/folio-cites.tex").read_text()
    assert cites.splitlines()[1] == "\\folioshowids"
    assert uris(pdf) == [b"https://example.org/notes/content/concepts/softmax/"]
    text = words(pdf)
    assert "softmax[softmax]" in text or not text  # pdftotext may space the raised mark from the comma
    # The copy that leaves the library is the plain build.
    assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
    assert uris(pdf) == []
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


CITER = '''
from folio.views import View
class P:
    prefix, title, home = "lab", "Lab", False
    def get(self, path): return View(title="G1.Q2", main="<p>x</p>") if path == "G1.Q2" else None
    def rail(self): return []
    def search(self): return []
    def paths(self): return ["G1.Q2"]
    def stamp(self): return "1"
    def backlinks(self): return {}
    def cite(self, ident): return {"title": "Does it hold", "url": "/lab/G1.Q2/"} if ident == "G1.Q2" else None
def provider(root): return P()
'''


def test_a_paper_cites_an_id_a_view_owns(sample: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    mods = tmp_path / "mods"
    mods.mkdir()
    (mods / "citeviews.py").write_text(CITER)
    monkeypatch.syspath_prepend(str(mods))
    with (sample / "folio.yaml").open("a") as f:
        f.write("views: [citeviews]\nsite_url: https://example.org/notes/\n")
    edit(sample / f"{PAPER}/main.tex", "Background", "Background, as \\fcite{G1.Q2} asks")
    from folio.checks.gate import broken_link
    lib = library.load(sample)
    assert not [p for p in broken_link(lib) if "G1.Q2" in p[1]]
    edit(sample / f"{PAPER}/main.tex", "as \\fcite{G1.Q2} asks", "as \\fcite{G9.Q9} asks")
    assert [p for p in broken_link(library.load(sample)) if "G9.Q9" in p[1]]
    if HAS_LATEXMK:
        edit(sample / f"{PAPER}/main.tex", "\\fcite{G9.Q9}", "\\fcite{G1.Q2}")
        assert folio(sample, "paper", "build", "tiled-attention", monkeypatch=monkeypatch) == 0
        cites = (sample / ".folio/build/tiled-attention/folio-cites.tex").read_text()
        assert "\\foliocite{G1.Q2}{Does it hold}{https://example.org/notes/lab/G1.Q2/}" in cites


@needs_latex
def test_the_served_pdf_is_built_again_when_the_source_changed(sample: Path) -> None:
    import os
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    from folio import paper as paper_mod
    from folio.site.serve import handler_for

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(sample, "127.0.0.1"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{PAPER}/paper.pdf"
    try:
        # no build yet: the click builds it
        first = urllib.request.urlopen(url).read()
        assert first.startswith(b"%PDF")
        lib = library.load(sample)
        doc = next(d for d in lib.documents if d.is_a("paper"))
        pdf = paper_mod.current_pdf(lib, doc)
        assert pdf is not None and not paper_mod.stale(lib, doc)
        built = pdf.stat().st_mtime
        # unchanged: served as it is
        urllib.request.urlopen(url).read()
        assert pdf.stat().st_mtime == built
        # the source changed: built again
        main = sample / f"{PAPER}/main.tex"
        edit(main, "Background", "Context")
        os.utime(main, (built + 5, built + 5))
        urllib.request.urlopen(url).read()
        assert pdf.stat().st_mtime > built
        # a source that does not compile shows its error, not the old PDF
        edit(main, "Context", "Context \\undefinedcommandhere")
        os.utime(main, (built + 50, built + 50))
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(url)
        assert err.value.code == 500 and b"did not compile" in err.value.read()
    finally:
        server.shutdown()
