"""`folio serve`, `folio up` and `folio down`: the site, served with the comment panel."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from .. import library as library_mod
from ..errors import FolioError
from ..indexer import INDEX_DIR
from . import notes, review
from .identity import Policy, is_loopback
from .record import Recorder
from .site import Site

HOST = "127.0.0.1"
PORT = 5170
PID_FILE = f"{INDEX_DIR}/serve.pid"
LOG_FILE = f"{INDEX_DIR}/serve.log"
API = "/_folio/annotations"
INBOX = "/_folio/inbox"
MAX_BODY = 64 * 1024  # bytes a comment request may carry


class Comments:
    """How one running server takes comments: who may write, and how a comment is recorded."""

    def __init__(self, root: Path, host: str = HOST, push: bool = False) -> None:
        lib = library_mod.load_at(root)
        self.root = root
        self.host = host
        self.policy = Policy(root, host, lib.charter.identity_header)
        self.recorder = Recorder(lib.root, push)

    def startup(self) -> str:
        refusal = self.policy.refusal()
        if refusal:
            return "comments are read-only: a public address needs comments.identity_header in folio.yaml"
        who = f"the {self.policy.header} header" if self.policy.header else "your git user.name"
        return f"comments are written as {who}; {self.recorder.describe()}"

    def status(self, headers: Mapping[str, str]) -> dict[str, object]:
        """What the shell needs to know about commenting, for one request."""
        who, refusal = self.policy.who(headers)
        return {"open": who is not None, "who": who.name if who else None, "reason": refusal}


def _hostname(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("["):
        return value[1:value.find("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def handler_for(root: Path, comments: Comments | None = None) -> type[BaseHTTPRequestHandler]:
    comments = comments or Comments(root)

    class Handler(BaseHTTPRequestHandler):
        server_version = "folio"

        def log_message(self, format: str, *args: object) -> None:
            sys.stderr.write(f"{self.address_string()} {format % args}\n")

        def _send(self, status: int, body: bytes, kind: str, location: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if location:
                self.send_header("Location", location)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, value: object) -> None:
            self._send(status, json.dumps(value).encode(), "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            """On a loopback address, only a loopback Host: another site's name pointed here gets nothing."""
            if comments.policy.public:
                return True
            return is_loopback(_hostname(self.headers.get("Host") or ""))

        def _same_origin(self) -> bool:
            origin = self.headers.get("Origin")
            if origin is None:
                return True
            hosts = {(self.headers.get(h) or "").strip().lower() for h in ("Host", "X-Forwarded-Host")} - {""}
            return urlsplit(origin).netloc.lower() in hosts

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            if not self._host_ok():
                self._send(403, b"Forbidden host", "text/plain; charset=utf-8")
                return
            url = urlsplit(self.path)
            # Each request loads the library afresh, so an edit shows on the next reload.
            site = Site.load(root, live=True)
            site.comments = comments.status(self.headers)
            try:
                if url.path == API:
                    doc = parse_qs(url.query).get("doc", [""])[0]
                    self._json(200, {"threads": notes.threads(site.lib, doc)})
                    return
                if url.path == INBOX:
                    self._json(200, review.inbox(site.lib))
                    return
            except FolioError as exc:
                self._json(400, {"error": str(exc)})
                return
            response = site.get(unquote(url.path))
            if response is None:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            self._send(response.status, response.body, response.content_type, response.location)

        def do_POST(self) -> None:
            if urlsplit(self.path).path != API:
                self._send(405, b"Read only", "text/plain; charset=utf-8")
                return
            if not self._host_ok() or not self._same_origin():
                self._json(403, {"error": "Comments are taken only from pages this server serves."})
                return
            kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if kind != "application/json":
                self._json(415, {"error": "Send the comment as JSON."})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                self._json(413, {"error": f"A comment request may hold at most {MAX_BODY // 1024} KB."})
                return
            who, refusal = comments.policy.who(self.headers)
            if who is None:
                self._json(403, {"error": refusal})
                return
            try:
                request = json.loads(self.rfile.read(length) or b"{}")
                site = Site.load(root, live=True)
                self._json(200, {"thread": notes.act(site.lib, request, who, comments.recorder)})
            except (FolioError, ValueError) as exc:
                self._json(400, {"error": str(exc)})

    return Handler


def serve(root: Path, port: int = PORT, host: str = HOST, push: bool = False) -> None:
    Site.load(root)  # fail before listening when the library does not load
    comments = Comments(root, host, push)
    server = ThreadingHTTPServer((host, port), handler_for(root, comments))
    shown = f"[{host}]" if ":" in host else host
    print(f"serving {root} at http://{shown}:{port}/content/; {comments.startup()} (Ctrl-C stops)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _running(root: Path) -> dict | None:
    path = root / PID_FILE
    if not path.is_file():
        return None
    info = json.loads(path.read_text(encoding="utf-8"))
    try:
        os.kill(int(info["pid"]), 0)
    except (ProcessLookupError, PermissionError):
        path.unlink()
        return None
    return info


def up(root: Path, port: int = PORT, host: str = HOST, push: bool = False) -> str:
    info = _running(root)
    if info is not None:
        return f"already serving at http://{info.get('host', HOST)}:{info['port']}/content/ (pid {info['pid']})"
    Site.load(root)
    Comments(root, host, push)  # fail here, not in the background, when --push cannot work
    (root / INDEX_DIR).mkdir(exist_ok=True)  # `folio init`'s .gitignore covers the runtime files
    log = open(root / LOG_FILE, "ab")
    command = [sys.executable, "-m", "folio", "serve", "--host", host, "--port", str(port)]
    proc = subprocess.Popen(
        command + (["--push"] if push else []),
        cwd=root, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
    )
    time.sleep(0.5)
    if proc.poll() is not None:
        raise FolioError(f"the server stopped at once; see {LOG_FILE}")
    (root / PID_FILE).write_text(json.dumps({"pid": proc.pid, "host": host, "port": port}) + "\n",
                                 encoding="utf-8")
    return f"serving at http://{host}:{port}/content/ (pid {proc.pid}); `folio down` stops it"


def down(root: Path) -> str:
    info = _running(root)
    if info is None:
        return "no server running"
    os.kill(int(info["pid"]), signal.SIGTERM)
    (root / PID_FILE).unlink()
    return f"stopped the server (pid {info['pid']})"
