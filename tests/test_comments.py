"""Comments through `folio serve`: who writes, how each comment is committed and pushed, and what readers see."""

from __future__ import annotations

import json
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from folio import annotations as ann
from folio import library
from folio.charter import load as load_charter
from folio.errors import FolioError
from folio.site import review, serve
from folio.site.identity import Policy, is_loopback
from folio.site.site import Site, export_site

DOC = "content/notes/flashattention-tiling.html"
SIDECAR = "content/notes/flashattention-tiling.annotations.json"
QUOTE = "the exact result"


@pytest.fixture(autouse=True)
def plain_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No global or system git settings: no signing, no name but the one a test sets."""
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def make_repo(path: Path, name: str = "Ada Reader", email: str = "ada@example.org") -> Path:
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", name)
    git(path, "config", "user.email", email)
    git(path, "add", "-A", ".")
    git(path, "commit", "-q", "-m", "start")
    return path


class Server:
    def __init__(self, root: Path, host: str = "127.0.0.1", push: bool = False) -> None:
        comments = serve.Comments(root, host, push)
        self.startup = comments.startup()
        self.http = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.handler_for(root, comments))
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

    def post(self, data: dict | bytes, headers: dict | None = None) -> tuple[int, dict]:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        req = urllib.request.Request(self.url + serve.API, body,
                                     {"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def ask(self, body: str = "Why?", **extra) -> tuple[int, dict]:
        return self.post({"action": "add", "doc": DOC, "kind": "question", "quote": QUOTE, "body": body, **extra})


@pytest.fixture
def server_for():
    servers: list[Server] = []

    def start(root: Path, host: str = "127.0.0.1", push: bool = False) -> Server:
        s = Server(root, host, push)
        servers.append(s)
        return s
    yield start
    for s in servers:
        s.close()


# -- who is commenting ------------------------------------------------------------


def test_identity_comes_from_git_locally(sample: Path, server_for) -> None:
    make_repo(sample)
    srv = server_for(sample)
    status, body = srv.ask(author="Someone Else")  # a name in the request is ignored
    assert status == 200, body
    assert body["thread"]["author"] == "Ada Reader"
    site = json.loads(srv.get("/.folio/site.json")[1])
    assert site["comments"] == {"open": True, "who": "Ada Reader", "reason": None}


def test_a_public_address_without_an_identity_header_is_read_only(sample: Path, server_for) -> None:
    make_repo(sample)
    srv = server_for(sample, host="0.0.0.0")
    assert "read-only" in srv.startup
    status, body = srv.ask()
    assert status == 403 and "identity_header" in body["error"]
    assert not (sample / SIDECAR).exists()
    site = json.loads(srv.get("/.folio/site.json")[1])
    assert site["comments"]["open"] is False and "identity_header" in site["comments"]["reason"]


def test_a_public_address_takes_the_proxy_header(sample: Path, server_for) -> None:
    make_repo(sample)
    (sample / "folio.yaml").write_text((sample / "folio.yaml").read_text()
                                       + "comments:\n  identity_header: X-Forwarded-User\n")
    git(sample, "commit", "-q", "-am", "name the header")
    srv = server_for(sample, host="0.0.0.0")
    assert "X-Forwarded-User" in srv.startup
    status, body = srv.ask()
    assert status == 403 and "X-Forwarded-User" in body["error"]
    status, body = srv.post(
        {"action": "add", "doc": DOC, "kind": "question", "quote": QUOTE, "body": "Why?"},
        {"X-Forwarded-User": "grace@example.org"})
    assert status == 200 and body["thread"]["author"] == "grace@example.org"
    assert git(sample, "log", "-1", "--format=%an <%ae>") == "grace@example.org <grace@example.org>"


def test_identity_header_is_validated(sample: Path) -> None:
    (sample / "folio.yaml").write_text((sample / "folio.yaml").read_text()
                                       + "comments:\n  identity_header: 'X User: 1'\n")
    with pytest.raises(FolioError, match="identity_header"):
        load_charter(sample)


def test_loopback_names() -> None:
    assert is_loopback("127.0.0.1") and is_loopback("::1") and is_loopback("localhost")
    assert not is_loopback("0.0.0.0") and not is_loopback("192.168.1.4")
    policy = Policy(Path("."), "0.0.0.0", "")
    assert policy.who({})[0] is None


# -- each comment is a commit ------------------------------------------------------


def test_each_comment_is_one_commit_holding_only_its_annotation_file(sample: Path, server_for) -> None:
    make_repo(sample)
    git(sample, "checkout", "-q", "-b", "notes")
    (sample / "content/notes/flashattention-tiling.html").write_text(
        (sample / DOC).read_text().replace("running maximum", "running  maximum"))  # an unrelated edit, staged
    git(sample, "add", DOC)
    doc_id = library.load_at(sample).by_path[DOC].doc.id
    srv = server_for(sample)
    assert srv.ask()[0] == 200
    assert git(sample, "rev-parse", "--abbrev-ref", "HEAD") == "notes"
    assert git(sample, "log", "-1", "--format=%s|%an") == f"Comment on {doc_id}|Ada Reader"
    assert git(sample, "show", "--name-only", "--format=", "HEAD").split() == [SIDECAR]
    assert git(sample, "diff", "--cached", "--name-only") == DOC  # the owner's staged edit is left as it was
    thread = json.loads((sample / SIDECAR).read_text())["threads"][0]
    status, _ = srv.post({"action": "reply", "doc": DOC, "id": thread["id"], "body": "More."})
    assert status == 200
    assert git(sample, "rev-list", "--count", "notes") == "3"


def test_outside_git_the_file_is_written_and_the_startup_line_says_so(sample: Path, server_for) -> None:
    srv = server_for(sample)
    assert "not in git" in srv.startup
    assert srv.ask()[0] == 200
    assert (sample / SIDECAR).is_file()


def test_push_needs_git(sample: Path) -> None:
    with pytest.raises(FolioError, match="--push"):
        serve.Comments(sample, push=True)


def _remote(tmp_path: Path, sample: Path) -> tuple[Path, Path]:
    """A bare remote holding the sample, and a clone of it to serve."""
    make_repo(sample)
    bare = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(sample), str(bare))
    clone = tmp_path / "served"
    git(tmp_path, "clone", "-q", str(bare), str(clone))
    git(clone, "config", "user.name", "Ada Reader")
    git(clone, "config", "user.email", "ada@example.org")
    return bare, clone


def test_push_sends_each_comment_to_the_remote(tmp_path: Path, sample: Path, server_for) -> None:
    bare, clone = _remote(tmp_path, sample)
    srv = server_for(clone, push=True)
    assert "pushed" in srv.startup
    assert srv.ask()[0] == 200
    assert git(bare, "log", "-1", "--format=%s").startswith("Comment on ")
    assert git(clone, "status", "--porcelain") == ""


def test_push_conflict_refuses_and_leaves_nothing(tmp_path: Path, sample: Path, server_for) -> None:
    bare, clone = _remote(tmp_path, sample)
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    git(other, "config", "user.name", "Other")
    git(other, "config", "user.email", "o@example.org")
    (other / SIDECAR).write_text('{"version": 1, "threads": []}\n')
    git(other, "add", SIDECAR)
    git(other, "commit", "-q", "-m", "theirs")
    git(other, "push", "-q")
    (clone / SIDECAR).write_text('{"threads": [], "version": 1}\n')  # an unpushed local commit that conflicts
    git(clone, "add", SIDECAR)
    git(clone, "commit", "-q", "-m", "ours")
    head, text = git(clone, "rev-parse", "HEAD"), (clone / SIDECAR).read_text()
    srv = server_for(clone, push=True)
    status, body = srv.ask()
    assert status == 400 and "not saved" in body["error"]
    assert git(clone, "rev-parse", "HEAD") == head
    assert (clone / SIDECAR).read_text() == text
    assert git(clone, "status", "--porcelain") == ""


def test_push_failure_rolls_back_the_commit(tmp_path: Path, sample: Path, server_for) -> None:
    bare, clone = _remote(tmp_path, sample)
    hook = bare / "hooks/pre-receive"
    hook.write_text("#!/bin/sh\necho closed for the night >&2\nexit 1\n")
    hook.chmod(0o755)
    head = git(clone, "rev-parse", "HEAD")
    srv = server_for(clone, push=True)
    status, body = srv.ask()
    assert status == 400 and "push" in body["error"]
    assert git(clone, "rev-parse", "HEAD") == head
    assert not (clone / SIDECAR).exists()
    assert git(clone, "status", "--porcelain") == ""


# -- requests the server refuses ----------------------------------------------------


def test_cross_origin_and_bad_requests_are_refused(sample: Path, server_for) -> None:
    make_repo(sample)
    srv = server_for(sample)
    status, body = srv.post({"action": "add", "doc": DOC, "body": "x"}, {"Origin": "http://evil.example"})
    assert status == 403
    assert srv.post({"action": "add", "doc": DOC, "body": "x"}, {"Origin": srv.url})[0] == 200
    assert srv.get("/content/", {"Host": "evil.example:5170"})[0] == 403
    req = urllib.request.Request(srv.url + serve.API, b"action=add", {"Content-Type": "text/plain"})
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 415
    assert srv.post(json.dumps({"body": "x" * (serve.MAX_BODY + 1)}).encode())[0] == 413
    status, body = srv.post({"action": "add", "doc": "folio.yaml", "body": "x"})
    assert status == 400 and "no document" in body["error"]
    status, body = srv.post({"action": "add", "doc": "content/../folio.yaml", "body": "x"})
    assert status == 400


# -- what readers see ---------------------------------------------------------------


def test_inbox_lists_waiting_questions_and_resting_flags_newest_first(sample: Path, monkeypatch, server_for) -> None:
    lib = library.load_at(sample)
    ann.add(lib, DOC, "question", QUOTE, "Why?", "reader")
    monkeypatch.setenv("FOLIO_TODAY", "2026-10-04")
    ann.add(lib, DOC, "flag", "", "An example of my own.", "agent:w", label="example")
    closed = ann.add(lib, DOC, "question", "", "Done?", "reader")
    ann.reply(lib, DOC, closed["id"], "Yes.", "agent:w", state="addressed")
    data = review.inbox(library.load_at(sample))
    assert (data["waiting"], data["resting"]) == (1, 1)
    assert [(r["kind"], r["word"]) for r in data["threads"]] == [("flag", "resting"), ("question", "waiting")]
    assert data["threads"][1]["url"] == "/" + DOC and data["threads"][1]["title"]
    srv = server_for(sample)
    assert json.loads(srv.get(serve.INBOX)[1])["waiting"] == 1
    status, page = srv.get("/content/review/")
    assert status == 200 and 'name="folio-view" content="review"' in page


def test_plain_words() -> None:
    def thread(kind, *states):
        return {"kind": kind, "state": states[-1] if states else ("noted" if kind == "flag" else "open"),
                "messages": [{"state": None}] + [{"state": s} for s in states]}
    assert review.plain(thread("question")) == {"word": "waiting", "how": None}
    assert review.plain(thread("flag")) == {"word": "resting", "how": None}
    assert review.plain(thread("flag", "addressed")) == {"word": "closed", "how": "kept"}
    assert review.plain(thread("flag", "open", "addressed")) == {"word": "closed", "how": "changed"}
    assert review.plain(thread("question", "addressed")) == {"word": "closed", "how": "changed"}
    assert review.plain(thread("question", "declined"))["how"] == "declined"
    assert review.plain(thread("question", "withdrawn"))["how"] == "withdrawn"


def test_keep_and_change_a_resting_flag(sample: Path, server_for) -> None:
    make_repo(sample)
    lib = library.load_at(sample)
    keep = ann.add(lib, DOC, "flag", QUOTE, "My framing.", "agent:w")
    change = ann.add(lib, DOC, "flag", "", "My example.", "agent:w")
    question = ann.add(lib, DOC, "question", "", "Why?", "reader")
    srv = server_for(sample)
    status, body = srv.post({"action": "keep", "doc": DOC, "id": keep["id"]})
    assert status == 200 and body["thread"]["state"] == "addressed"
    assert srv.post({"action": "change", "doc": DOC, "id": change["id"], "body": ""})[0] == 400
    status, body = srv.post({"action": "change", "doc": DOC, "id": change["id"], "body": "Use a smaller list."})
    assert status == 200 and body["thread"]["state"] == "open"
    assert body["thread"]["messages"][-1]["author"] == "Ada Reader"
    assert srv.post({"action": "keep", "doc": DOC, "id": question["id"]})[0] == 400
    threads = {t["id"]: t for t in json.loads(srv.get(serve.API + "?doc=" + DOC)[1])["threads"]}
    assert (threads[keep["id"]]["word"], threads[keep["id"]]["how"]) == ("closed", "kept")
    assert threads[change["id"]]["word"] == "waiting"
    assert {r["id"] for r in review.inbox(library.load_at(sample))["threads"]} == {question["id"], change["id"]}


def test_what_changed_comes_from_git(sample: Path, server_for) -> None:
    make_repo(sample)
    srv = server_for(sample)
    status, body = srv.ask("Say what each tile updates.")
    thread = body["thread"]
    page = sample / DOC
    page.write_text(page.read_text().replace("rescaled this way gives the exact result",
                                             "gives the result a full score matrix would give"))
    lib = library.load_at(sample)
    ann.reply(lib, DOC, thread["id"], "Named the secondary key.", "agent:w", state="addressed")
    threads = json.loads(srv.get(serve.API + "?doc=" + DOC)[1])["threads"]
    assert "changed" not in threads[0]  # the reply is not committed yet: nothing is shown
    git(sample, "add", DOC, SIDECAR)
    git(sample, "commit", "-q", "-m", "address")
    shown = json.loads(srv.get(serve.API + "?doc=" + DOC)[1])["threads"][0]
    assert shown["how"] == "changed"
    before, after = shown["changed"]["before"], shown["changed"]["after"]
    assert before["text"] == "rescaled this way gives the exact result."
    assert after["text"] == "gives the result a full score matrix would give."
    assert before["lead"].endswith("softmax") and after["lead"] == before["lead"]


def test_what_changed_is_omitted_without_history(sample: Path) -> None:
    lib = library.load_at(sample)
    t = ann.add(lib, DOC, "question", QUOTE, "Why?", "reader")
    t = ann.reply(lib, DOC, t["id"], "Because.", "agent", state="addressed")
    assert review.changed(library.load_at(sample), DOC, t) is None


def test_an_exported_site_carries_no_comments(sample: Path, tmp_path: Path) -> None:
    lib = library.load_at(sample)
    ann.add(lib, DOC, "question", QUOTE, "Why?", "reader")
    written, _ = export_site(sample, tmp_path / "out")
    assert not any(p.endswith(".annotations.json") for p in written)
    assert "content/review/index.html" not in written
    assert json.loads((tmp_path / "out/.folio/site.json").read_text())["comments"] is None
    assert Site.load(sample).site_data()["comments"] is None


# -- the server keeps what it loaded --------------------------------------------------


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
    with urllib.request.urlopen(s.url + serve.API + "?doc=" + DOC) as r:
        assert r.headers["Cache-Control"] == "no-store" and r.headers["ETag"] is None


def test_an_author_deletes_their_own_thread_and_its_id_is_not_reused(sample: Path, server_for) -> None:
    make_repo(sample)
    lib = library.load_at(sample)
    theirs = ann.add(lib, DOC, "flag", "", "An agent's flag.", "agent:w")
    srv = server_for(sample)
    status, body = srv.ask("Mine.")
    assert status == 200
    mine = body["thread"]["id"]
    doc_id = library.load_at(sample).by_path[DOC].doc.id
    assert srv.post({"action": "delete", "doc": DOC, "id": theirs["id"]})[0] == 400  # not the reader's thread
    status, _ = srv.post({"action": "delete", "doc": DOC, "id": mine})
    assert status == 200
    data = json.loads((sample / SIDECAR).read_text())
    assert [t["id"] for t in data["threads"]] == [theirs["id"]]
    assert data["deleted"] == [mine]
    assert git(sample, "log", "-1", "--format=%s|%an") == f"Delete a comment on {doc_id}|Ada Reader"
    assert mine in git(sample, "show", "HEAD~1:" + SIDECAR)  # history keeps what was said
    assert srv.post({"action": "delete", "doc": DOC, "id": mine})[0] == 400
    status, body = srv.ask("Again.")
    assert body["thread"]["id"] not in {mine, theirs["id"]}


def test_the_header_offers_the_page_path_to_copy() -> None:
    shell = (Path(__file__).resolve().parents[1] / "shell" / "folio.js").read_text()
    assert "function copyPath(path)" in shell and r"index\.html$" in shell
