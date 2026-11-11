"""`folio serve`: a live, read-only site that follows its files."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from folio.site import serve
from folio.site.site import Site

DOC = "content/notes/flashattention-tiling.html"
QUOTE = "the exact result"


class Server:
    def __init__(self, root: Path, host: str = "127.0.0.1") -> None:
        self.http = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.handler_for(root, host))
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.http.server_address[1]}"

    def close(self) -> None:
        self.http.shutdown()
        self.http.server_close()

    def get(self, path: str, headers: dict | None = None) -> tuple[int, str]:
        req = urllib.request.Request(self.url + path, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    def post(self, path: str, body: bytes = b"{}") -> int:
        req = urllib.request.Request(self.url + path, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status
        except urllib.error.HTTPError as exc:
            return exc.code


@pytest.fixture
def server_for():
    servers: list[Server] = []

    def start(root: Path, host: str = "127.0.0.1") -> Server:
        s = Server(root, host)
        servers.append(s)
        return s
    yield start
    for s in servers:
        s.close()


def test_loopback_names() -> None:
    assert serve.is_loopback("127.0.0.1") and serve.is_loopback("::1") and serve.is_loopback("localhost")
    assert not serve.is_loopback("0.0.0.0") and not serve.is_loopback("192.168.1.4")


def test_the_server_is_read_only(sample: Path, server_for) -> None:
    srv = server_for(sample)
    assert srv.post("/" + DOC) == 405
    assert srv.post("/_folio/annotations") == 405
    assert srv.get("/_folio/annotations?doc=" + DOC)[0] == 404
    assert srv.get("/content/review/")[0] == 404


def test_a_loopback_server_answers_only_a_loopback_host(sample: Path, server_for) -> None:
    assert server_for(sample).get("/content/", {"Host": "evil.example:5170"})[0] == 403
    assert server_for(sample, "0.0.0.0").get("/content/", {"Host": "notes.example.org"})[0] == 200


def test_the_server_loads_the_library_again_only_when_a_file_changes(sample: Path, server_for, monkeypatch) -> None:
    loads = []
    real = Site.load.__func__
    monkeypatch.setattr(Site, "load", classmethod(lambda cls, *a, **k: loads.append(1) or real(cls, *a, **k)))
    s = server_for(sample)
    for _ in range(3):
        assert s.get("/" + DOC)[0] == 200
        assert s.get("/shell/folio.css")[0] == 200
    assert len(loads) == 1
    page = sample / DOC
    page.write_text(page.read_text().replace(QUOTE, "a phrase written while the server runs"))
    assert "a phrase written while the server runs" in s.get("/" + DOC)[1]
    assert len(loads) == 2


def test_an_unchanged_file_is_answered_with_304(sample: Path, server_for) -> None:
    s = server_for(sample)
    with urllib.request.urlopen(s.url + "/" + DOC) as r:
        etag = r.headers["ETag"]
        assert etag and r.headers["Cache-Control"] == "no-cache"
    req = urllib.request.Request(s.url + "/" + DOC, headers={"If-None-Match": etag})
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 304
    with urllib.request.urlopen(s.url + "/_folio/etag?path=/" + DOC) as r:
        assert r.headers["Cache-Control"] == "no-store" and r.headers["ETag"] is None


def test_the_header_offers_the_page_path_to_copy() -> None:
    shell = (Path(__file__).resolve().parents[1] / "shell" / "folio.js").read_text()
    assert "function copyPath(path)" in shell and r"index\.html$" in shell


def test_a_leftover_comment_file_is_never_served_or_exported(sample: Path, tmp_path: Path) -> None:
    from folio.site.site import export_site

    left = sample / "content/notes/flashattention-tiling.annotations.json"
    left.write_text('{"threads": [{"author": "a reader"}]}\n')
    assert Site.load(sample).get("content/notes/flashattention-tiling.annotations.json") is None
    export_site(sample, tmp_path / "site")
    assert not list((tmp_path / "site").rglob("*.annotations.json"))
