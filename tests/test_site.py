from __future__ import annotations

import json
import re
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from conftest import folio

from folio.errors import FolioError
from folio.site import serve
from folio.site.site import Site, export

SRC = Path(__file__).resolve().parents[1] / "src"


def test_export_writes_every_page(sample: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "site"
    assert folio(sample, "export", "--out", str(out), monkeypatch=monkeypatch) == 0
    assert capsys.readouterr().out.startswith("exported 26 pages to ")
    for page in ["index.html", "content/index.html", "content/concepts/softmax/index.html",
                 "content/guides/attention-from-scratch/02-softmax.html", "content/papers/tiled-attention/index.html",
                 "content/journal/index.html", "shell/folio.css", "shell/folio.js",
                 ".folio/catalog.json", ".folio/backlinks.json", ".folio/nav.json", ".folio/site.json",
                 "assets/data/pi-errors.csv"]:
        assert (out / page).is_file(), page
    assert not (out / "content/results/R-3.md").exists()
    assert not list(out.rglob("*.annotations.json"))
    assert "url=/content/" in (out / "index.html").read_text()
    # kb finding 6: a source's kept original is never published, though `folio serve` shows it.
    assert (sample / "content/sources/2017-attention-is-all-you-need/original.pdf").is_file()
    assert not list(out.rglob("original.*"))
    assert Site.load(sample).get("content/sources/2017-attention-is-all-you-need/original.pdf") is not None
    # Decision 8: the home page's title is the charter's name.
    assert "<title>Research notes</title>" in (out / "content/index.html").read_text()


def test_records_render_in_the_shell(sample: Path, tmp_path: Path) -> None:
    export(sample, tmp_path / "site")
    page = (tmp_path / "site/content/results/R-4.html").read_text()
    assert '<meta name="title" content="The RMS error of the pi estimate fell with a fitted log-log slope of -0.493">' in page
    assert '<meta name="description" content="The slope of the RMS error against the number of points, re-folded.">' in page
    assert '<meta name="genre" content="result">' in page
    assert '<meta name="folio-source" content="content/results/R-4.md">' in page
    assert '<link rel="stylesheet" href="/shell/folio.css">' in page
    assert "<h1" not in page
    # an id in backticks links to the record it names, at its rendered page
    assert '<a class="f-cite" href="/content/results/R-3.html"' in page and '><code>R-3</code></a>' in page
    # the derived status, not a written one
    old = (tmp_path / "site/content/results/R-3.html").read_text()
    assert '<meta name="status" content="superseded">' in old


def test_links_are_rewritten(sample: Path, tmp_path: Path) -> None:
    export(sample, tmp_path / "site")
    entry = (tmp_path / "site/content/journal/2026/2026-10-02-recorded-r-4.html").read_text()
    assert 'href="/content/protocols/pi-error-scaling.html"' in entry
    assert 'href="/content/' in entry and not re.search(r'href="[^"]*\.md"', entry)


def test_base_path_prefixes_root_links(sample: Path, tmp_path: Path) -> None:
    export(sample, tmp_path / "site", base="/notes/")
    home = (tmp_path / "site/content/index.html").read_text()
    assert 'href="/notes/shell/folio.css"' in home
    assert 'src="/notes/shell/folio.js"' in home
    assert 'href="/notes/content/projects/attention-kernel/"' in home
    with pytest.raises(FolioError):
        export(sample, tmp_path / "other", base="notes")


def test_site_data_carries_home_maps_and_kinds(sample: Path) -> None:
    data = Site.load(sample).site_data()
    assert data["home"]["maps"] == ["attention", "lab-work"]
    assert "meeting" in data["journal"]["kinds"] and "decision" in data["journal"]["kinds"]
    assert data["journal"]["url"] == "/content/journal/"
    assert data["live"] is False


def test_pages_without_the_script_get_it(sample: Path) -> None:
    report = sample / "content/notes/flashattention-tiling.html"
    report.write_text(report.read_text().replace('<script src="/shell/folio.js" defer></script>\n', ""))
    body = Site.load(sample).get("content/notes/flashattention-tiling.html").body.decode()
    assert body.count("/shell/folio.js") == 1


def test_redirects_are_served(sample: Path, tmp_path: Path) -> None:
    (sample / ".folio/redirects.json").write_text(json.dumps(
        {"redirects": {"content/notes/old-name.html": "content/notes/flashattention-tiling.html",
                       "content/results/R-9.md": "content/results/R-4.md"}}))
    export(sample, tmp_path / "site")
    assert "url=/content/notes/flashattention-tiling.html" in (tmp_path / "site/content/notes/old-name.html").read_text()
    assert "url=/content/results/R-4.html" in (tmp_path / "site/content/results/R-9.html").read_text()
    assert not (tmp_path / "site/.folio/redirects.json").exists()


def test_export_refuses_to_write_over_the_library(sample: Path, tmp_path: Path) -> None:
    for out in (sample, sample / "content", sample / ".folio" / "x"):
        with pytest.raises(FolioError):
            export(sample, out)
    stranger = tmp_path / "full"
    stranger.mkdir()
    (stranger / "keep.txt").write_text("mine")
    with pytest.raises(FolioError):
        export(sample, stranger)
    export(sample, sample / "_site")
    export(sample, sample / "_site")  # an earlier export is replaced


@pytest.fixture
def live(sample: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler_for(sample))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _post(url: str, data: dict) -> tuple[int, dict]:
    req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_serve_matches_export(live: str) -> None:
    status, page = _get(live + "/content/results/R-4.html")
    assert status == 200 and '<meta name="folio-source" content="content/results/R-4.md">' in page
    status, data = _get(live + "/.folio/site.json")
    assert json.loads(data)["live"] is True
    assert _get(live + "/folio.yaml")[0] == 404
    assert _get(live + "/content/concepts/softmax/")[0] == 200
    status, _ = _get(live + "/content/journal/")
    assert status == 200


def test_serve_reads_and_writes_annotations(live: str, sample: Path) -> None:
    doc = "content/notes/flashattention-tiling.html"
    status, body = _post(live + "/_folio/annotations", {
        "action": "add", "doc": doc, "kind": "question", "quote": "the exact result",
        "body": "Why?", "author": "reader"})
    assert status == 200, body
    thread = body["thread"]
    status, body = _post(live + "/_folio/annotations", {
        "action": "reply", "doc": doc, "id": thread["id"], "body": "Because.", "state": "addressed"})
    assert status == 200 and body["thread"]["state"] == "open"  # a reader's reply never moves the state
    status, text = _get(live + "/_folio/annotations?doc=" + doc)
    assert [(t["state"], t["word"]) for t in json.loads(text)["threads"]] == [("open", "waiting")]
    status, body = _post(live + "/_folio/annotations", {"action": "add", "doc": doc, "body": "x"})
    assert status == 200 and body["thread"]["quote"] == ""  # a thread about the whole page
    status, body = _post(live + "/_folio/annotations", {"action": "add", "doc": doc, "body": "x",
                                                         "quote": "not on this page at all"})
    assert status == 400 and "quote" in body["error"]


def test_up_and_down(sample: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")]))
    try:
        message = serve.up(sample, port=5197)
        assert "serving" in message
        assert (sample / serve.PID_FILE).is_file()
        assert "already serving" in serve.up(sample, port=5197)
        assert not (sample / ".folio/.gitignore").exists()  # fix2 22: init's .gitignore covers it
    finally:
        assert "stopped" in serve.down(sample)
    assert serve.down(sample) == "no server running"
