"""A deck's PDF: rendered by headless Chrome when served, published beside the deck when exported."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from folio.errors import FolioError
from folio.site import pdf, serve
from folio.site.site import export_site

DECK = "content/decks/attention-in-five-minutes/index.html"


def _installed() -> bool:
    try:
        return pdf.find_chrome() is not None
    except FolioError:
        return False


@pytest.mark.chrome  # reads the real lookup, not the suite's stand-in
def test_chrome_from_the_environment(tmp_path: Path, monkeypatch) -> None:
    fake = tmp_path / "chrome"
    fake.write_text("")
    monkeypatch.setenv(pdf.ENV, str(fake))
    assert pdf.find_chrome() == str(fake)
    monkeypatch.setenv(pdf.ENV, str(tmp_path / "missing"))
    with pytest.raises(FolioError, match=pdf.ENV):
        pdf.find_chrome()


def test_export_without_chrome_warns_and_lists_no_pdf(sample: Path, tmp_path: Path, monkeypatch) -> None:
    warnings: list[str] = []
    written, _ = export_site(sample, tmp_path / "site", "/", warnings)
    assert any("deck" in w and "Chrome" in w for w in warnings)
    assert not any(p.endswith(".pdf") and "/decks/" in p for p in written)
    data = json.loads((tmp_path / "site/.folio/site.json").read_text())
    assert data["pdfs"] == {}


def test_served_pdf_without_chrome_says_why(sample: Path, monkeypatch) -> None:
    monkeypatch.setattr(pdf, "find_chrome", lambda: None)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(sample.parent / "tmp"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler_for(sample))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/_folio/pdf?doc={DECK}"
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url)
        assert exc.value.code == 400
        assert "Chrome" in json.loads(exc.value.read())["error"]
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url.replace(DECK, "content/index.html"))
        assert "no deck" in json.loads(exc.value.read())["error"]
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.chrome
@pytest.mark.skipif(not _installed(), reason="needs Chrome or Chromium")
def test_export_publishes_each_deck_pdf(sample: Path, tmp_path: Path) -> None:
    written, _ = export_site(sample, tmp_path / "site", "/docs/")
    path = "content/decks/attention-in-five-minutes/attention-in-five-minutes.pdf"
    assert path in written
    assert (tmp_path / "site" / path).read_bytes().startswith(b"%PDF")
    data = json.loads((tmp_path / "site/.folio/site.json").read_text())
    assert data["pdfs"] == {DECK: "/" + path}


@pytest.mark.chrome
@pytest.mark.skipif(not _installed(), reason="needs Chrome or Chromium")
def test_served_pdf_downloads(sample: Path, monkeypatch) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(sample.parent / "tmp"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler_for(sample))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/_folio/pdf?doc=attention-in-five-minutes"
        with urllib.request.urlopen(url) as r:
            assert r.headers["Content-Type"] == "application/pdf"
            assert 'filename="attention-in-five-minutes.pdf"' in r.headers["Content-Disposition"]
            assert r.read().startswith(b"%PDF")
    finally:
        server.shutdown()
        server.server_close()
