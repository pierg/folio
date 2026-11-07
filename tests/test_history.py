"""The checks that read git history: permanent, frozen, record-id reuse (unique-id), and the no-git warning."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import edit, found, problems

from folio import history, library

JOURNAL = "content/journal/2026/2026-10-01-set-up-the-library.md"
PROTOCOL = "content/protocols/pi-error-scaling.md"
REPORT = "content/reports/pi-error-scaling-report/index.html"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false",
                    *args], cwd=repo, check=True, capture_output=True)


def commit(repo: Path, message: str = "change") -> None:
    git(repo, "add", "-A", ".")
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(sample: Path) -> Path:
    git(sample, "init", "-q")
    commit(sample, "first")
    return sample


def test_no_git_gives_one_warning(sample: Path) -> None:
    notices = [p for p in problems(sample) if p.path == "folio.yaml"]
    assert len(notices) == 1 and notices[0].severity == "warning"
    assert "not in a git repository" in notices[0].message


def test_committed_library_passes(repo: Path) -> None:
    assert [p.line() for p in problems(repo)] == []


def test_permanent_working_tree_edit(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    assert [p.path for p in found(repo, "permanent")] == [JOURNAL]
    commit(repo)
    assert [p.path for p in found(repo, "permanent")] == [JOURNAL]
    edit(repo / JOURNAL, "Set up this library", "Set up the library")
    assert found(repo, "permanent") == []  # restored to its first version


def test_permanent_uncommitted_new_entry_is_fine(repo: Path) -> None:
    new = repo / "content/journal/2026/2026-10-03-later.md"
    new.write_text((repo / JOURNAL).read_text().replace("date: 2026-10-01", "date: 2026-10-03"))
    assert found(repo, "permanent") == []


def test_frozen_edit_while_locked(repo: Path) -> None:
    edit(repo / PROTOCOL, "Each point is an independent draw, inside the quarter circle or not.", "Each point is a draw.")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and msgs[0].path == PROTOCOL and "locked" in msgs[0].message
    commit(repo)
    assert len(found(repo, "frozen")) == 1


def test_frozen_status_may_only_move_forward(repo: Path) -> None:
    edit(repo / PROTOCOL, "status: locked", "status: abandoned")
    assert found(repo, "frozen") == []
    commit(repo, "abandon")
    assert found(repo, "frozen") == []
    edit(repo / PROTOCOL, "status: abandoned", "status: locked")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and "never undone" in msgs[0].message


def test_unlocking_is_an_error(repo: Path) -> None:
    edit(repo / PROTOCOL, "status: locked", "status: draft")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and "after being frozen" in msgs[0].message


def test_unlock_edit_relock_is_caught(repo: Path) -> None:
    """Lab finding 3: locked -> draft -> edit -> locked must not launder an edit."""
    edit(repo / PROTOCOL, "status: locked", "status: draft")
    commit(repo, "unlock")
    edit(repo / PROTOCOL, "Each point is an independent draw, inside the quarter circle or not.", "Each point is a draw.")
    commit(repo, "edit")
    edit(repo / PROTOCOL, "status: draft", "status: locked")
    commit(repo, "lock again")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and "changed since it was frozen" in msgs[0].message


def test_leaving_frozen_with_other_changes(repo: Path) -> None:
    edit(repo / PROTOCOL, "status: locked", "status: abandoned")
    edit(repo / PROTOCOL, "Each point is an independent draw, inside the quarter circle or not.", "Each point is a draw.")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and "only the status may change" in msgs[0].message
    commit(repo, "abandon and edit")
    assert len(found(repo, "frozen")) == 1  # the history keeps it


def test_frozen_html_status_meta(repo: Path) -> None:
    """A report is frozen once `live`; its HTML status meta may move on to `historical` alone."""
    edit(repo / REPORT, "We ran the estimator at every size.", "We ran it.")
    assert len(found(repo, "frozen")) == 1
    edit(repo / REPORT, "We ran it.", "We ran the estimator at every size.")
    edit(repo / REPORT, '<meta name="status" content="live">', '<meta name="status" content="historical">')
    assert found(repo, "frozen") == []


def test_paper_source_stays_revised(repo: Path) -> None:
    edit(repo / "content/papers/tiled-attention/main.tex", "Background", "Context")
    commit(repo)
    assert found(repo, "frozen") == [] and found(repo, "permanent") == []


def test_record_id_reused_after_deletion(repo: Path) -> None:
    claim = repo / "content/claims/C-1.md"
    text = claim.read_text()
    git(repo, "rm", "-q", "content/claims/C-1.md")
    git(repo, "commit", "-q", "-m", "drop C-1")
    assert not [p for p in found(repo, "unique-id") if "reused" in p.message]
    claim.parent.mkdir(exist_ok=True)
    claim.write_text(text)
    msgs = [p for p in found(repo, "unique-id") if "never reused" in p.message]
    assert [p.path for p in msgs] == ["content/claims/C-1.md"]


def test_dates(repo: Path) -> None:
    lib = library.load_at(repo)
    created, updated = history.dates(lib, JOURNAL)
    assert created is not None and created == updated
    assert history.dates(lib, "content/nothing.md") == (None, None)


def _baseline(repo: Path, *paths: str) -> None:
    import hashlib
    lines = "".join(f"{hashlib.sha256((repo / p).read_bytes()).hexdigest()}  {p}\n" for p in paths)
    (repo / "baseline.sha256").write_text(lines)
    (repo / "folio.yaml").write_text((repo / "folio.yaml").read_text() + "baseline: baseline.sha256\n")


def test_baseline_accepts_a_recorded_rewrite(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    edit(repo / PROTOCOL, "Each point is an independent draw, inside the quarter circle or not.", "Each point is a draw.")
    commit(repo, "rewrite")
    assert found(repo, "permanent") and found(repo, "frozen")
    _baseline(repo, JOURNAL, PROTOCOL)
    commit(repo, "baseline")
    assert found(repo, "permanent") == [] and found(repo, "frozen") == []
    edit(repo / JOURNAL, "Set up this library", "Set up a library")  # after the baseline: an edit again
    assert [p.path for p in found(repo, "permanent")] == [JOURNAL]
    edit(repo / PROTOCOL, "Each point is a draw.", "Each point is one draw.")
    assert [p.path for p in found(repo, "frozen")] == [PROTOCOL]


def test_baseline_passes_before_the_commit(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    edit(repo / PROTOCOL, "Each point is an independent draw, inside the quarter circle or not.", "Each point is a draw.")
    _baseline(repo, JOURNAL, PROTOCOL)  # nothing committed: `folio save` runs the gate first
    assert found(repo, "permanent") == [] and found(repo, "frozen") == []


def test_baseline_never_unfreezes(repo: Path) -> None:
    edit(repo / PROTOCOL, "status: locked", "status: draft")
    _baseline(repo, PROTOCOL)
    commit(repo, "a rewrite that also sets the status back")
    msgs = found(repo, "frozen")
    assert len(msgs) == 1 and "draft" in msgs[0].message


def test_baseline_lines_are_only_added(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    _baseline(repo, JOURNAL)
    commit(repo, "rewrite")
    edit(repo / JOURNAL, "Set up this library", "Set up a library")
    import hashlib
    digest = hashlib.sha256((repo / JOURNAL).read_bytes()).hexdigest()
    (repo / "baseline.sha256").write_text(f"{digest}  {JOURNAL}\n")  # swapping the line for a later edit
    with pytest.raises(Exception, match="only ever added"):
        problems(repo)


def test_baseline_survives_a_squash(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    _baseline(repo, JOURNAL)
    commit(repo, "rewrite and baseline in one commit, as a squash merge lands them")
    assert found(repo, "permanent") == []


def test_baseline_file_must_exist(repo: Path) -> None:
    (repo / "folio.yaml").write_text((repo / "folio.yaml").read_text() + "baseline: nowhere.sha256\n")
    with pytest.raises(Exception, match="does not exist"):
        problems(repo)


def test_baseline_stays_in_the_library(repo: Path) -> None:
    (repo / "folio.yaml").write_text((repo / "folio.yaml").read_text() + "baseline: ../outside.sha256\n")
    with pytest.raises(Exception, match="inside the library"):
        library.load_at(repo)


def test_baseline_key_is_fixed_once_set(repo: Path) -> None:
    edit(repo / JOURNAL, "Set up the library", "Set up this library")
    _baseline(repo, JOURNAL)
    commit(repo, "rewrite")
    (repo / "b2.sha256").write_text("")
    edit(repo / "folio.yaml", "baseline: baseline.sha256", "baseline: b2.sha256")
    with pytest.raises(Exception, match="names the same file for good"):
        problems(repo)
