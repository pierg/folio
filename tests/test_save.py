"""`folio save`, the charter's `save` block, and the page ETag a served page polls to follow edits."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import edit, folio
from folio.charter import load as load_charter
from folio.commands import save
from folio.errors import FolioError
from test_comments import Server

NOTE = "content/notes/flashattention-tiling.html"
CONCEPT = "content/concepts/softmax/index.html"


@pytest.fixture(autouse=True)
def plain_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def clone_of(bare: Path, where: Path, name: str) -> Path:
    git(where.parent, "clone", "-q", str(bare), str(where))
    git(where, "config", "user.name", name)
    git(where, "config", "user.email", f"{name.lower()}@example.org")
    return where


@pytest.fixture
def remote(tmp_path: Path, sample: Path) -> tuple[Path, Path]:
    """A bare remote holding the sample, and one clone to work in."""
    git(sample, "init", "-q", "-b", "main")
    git(sample, "config", "user.name", "Ada")
    git(sample, "config", "user.email", "ada@example.org")
    git(sample, "add", "-A", ".")
    git(sample, "commit", "-q", "-m", "start")
    bare = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(sample), str(bare))
    return bare, clone_of(bare, tmp_path / "work", "Ada")


def test_save_commits_and_pushes_only_the_content(remote, monkeypatch: pytest.MonkeyPatch) -> None:
    bare, work = remote
    edit(work / NOTE, "gives the exact result", "gives exactly the result")
    edit(work / "folio.yaml", "name: Research notes", "name: Research library")  # not content
    monkeypatch.chdir(work)
    done = save.save(work)
    assert done.pushed and done.commit
    assert git(bare, "log", "-1", "--format=%s") == "Update flashattention-tiling"
    assert NOTE in git(bare, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert "folio.yaml" not in git(bare, "show", "--name-only", "--format=", "HEAD")
    assert done.left == ["folio.yaml"]
    assert git(work, "status", "--porcelain") == "M folio.yaml"


def test_nothing_to_save(remote, monkeypatch: pytest.MonkeyPatch) -> None:
    bare, work = remote
    head = git(bare, "rev-parse", "HEAD")
    monkeypatch.chdir(work)
    assert save.save(work).commit is None
    assert git(bare, "rev-parse", "HEAD") == head


def test_save_lands_on_top_of_what_others_pushed(tmp_path: Path, remote, monkeypatch: pytest.MonkeyPatch) -> None:
    bare, work = remote
    other = clone_of(bare, tmp_path / "other", "Bea")
    edit(other / CONCEPT, "</main>", "<p>One more line.</p>\n</main>")
    git(other, "commit", "-qam", "theirs")
    git(other, "push", "-q")
    edit(work / NOTE, "gives the exact result", "gives exactly the result")
    monkeypatch.chdir(work)
    assert save.save(work).pushed
    log = git(bare, "log", "--format=%s", "-3").splitlines()
    assert log[:2] == ["Update flashattention-tiling", "theirs"]


def test_save_tries_again_when_the_push_is_refused(tmp_path: Path, remote, monkeypatch: pytest.MonkeyPatch) -> None:
    bare, work = remote
    once = tmp_path / "refused-once"
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(f"#!/bin/sh\nif [ ! -f {once} ]; then touch {once}; echo busy >&2; exit 1; fi\n")
    hook.chmod(0o755)
    edit(work / NOTE, "gives the exact result", "gives exactly the result")
    monkeypatch.chdir(work)
    done = save.save(work)
    assert done.pushed and once.exists()
    assert git(bare, "log", "-1", "--format=%s") == "Update flashattention-tiling"
    assert git(work, "status", "--porcelain") == ""


def test_a_failing_gate_saves_nothing(remote, monkeypatch: pytest.MonkeyPatch) -> None:
    bare, work = remote
    edit(work / "folio.yaml", "checks:", "save:\n  gate: \"false\"\nchecks:")
    git(work, "commit", "-qam", "a gate that always fails")
    git(work, "push", "-q")
    head = git(bare, "rev-parse", "HEAD")
    edit(work / NOTE, "gives the exact result", "gives exactly the result")
    monkeypatch.chdir(work)
    with pytest.raises(FolioError, match="the gate `false` failed"):
        save.save(work)
    assert git(bare, "rev-parse", "HEAD") == head
    assert "gives exactly the result" in (work / NOTE).read_text()


def test_save_prints_each_page_under_the_live_address(remote, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    bare, work = remote
    edit(work / "folio.yaml", "checks:", "save:\n  url: https://notes.example.org/\nchecks:")
    git(work, "commit", "-qam", "served live")
    git(work, "push", "-q")
    edit(work / NOTE, "gives the exact result", "gives exactly the result")
    assert folio(work, "save", "-m", "Tighten the tiling note", monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out
    assert "and pushed" in out
    assert "flashattention-tiling (live) https://notes.example.org/content/notes/flashattention-tiling.html" in out
    assert git(bare, "log", "-1", "--format=%s") == "Tighten the tiling note"


def test_no_push_commits_without_an_upstream(sample: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    git(sample, "init", "-q", "-b", "main")
    git(sample, "config", "user.name", "Ada")
    git(sample, "config", "user.email", "ada@example.org")
    git(sample, "add", "-A", ".")
    git(sample, "commit", "-q", "-m", "start")
    edit(sample / NOTE, "gives the exact result", "gives exactly the result")
    monkeypatch.chdir(sample)
    with pytest.raises(FolioError, match="no upstream"):
        save.save(sample)
    done = save.save(sample, push=False)
    assert done.commit and not done.pushed


def test_the_save_block_is_checked(sample: Path) -> None:
    charter = sample / "folio.yaml"
    edit(charter, "checks:", "save:\n  review: drafts\n  url: https://notes.example.org\nchecks:")
    settings = load_charter(sample).save
    assert (settings.review, settings.url, settings.gate) == ("drafts", "https://notes.example.org", "")
    edit(charter, "review: drafts", "review: everything")
    with pytest.raises(FolioError, match="save.review"):
        load_charter(sample)


def test_under_review_a_new_document_starts_as_a_draft(sample: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: drafts\nchecks:")
    assert folio(sample, "new", "note", "rope-scaling", "--title", "RoPE scaling",
                 "--description", "Why rotary positions stretch.", monkeypatch=monkeypatch) == 0
    page = next((sample / "content" / "notes").glob("rope-scaling*"))
    text = page.read_text() if page.is_file() else (page / "index.html").read_text()
    assert 'name="status" content="draft"' in text or "status: draft" in text


def test_a_served_page_reports_its_etag_and_it_follows_edits(sample: Path) -> None:
    srv = Server(sample)
    try:
        status, body = srv.get("/_folio/etag?path=/" + NOTE)
        first = json.loads(body)["etag"]
        assert status == 200 and first
        edit(sample / NOTE, "gives the exact result", "gives exactly the result")
        second = json.loads(srv.get("/_folio/etag?path=/" + NOTE)[1])["etag"]
        assert second and second != first
        assert json.loads(srv.get("/_folio/etag?path=/content/nowhere.html")[1])["etag"] is None
    finally:
        srv.close()
