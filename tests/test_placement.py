"""One place per page: the placement and heading-size checks, place and used_by in the catalog,
`folio map add --section` and `folio map move`, `folio new`'s note, and review after landing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import edit, folio, found, problems
from folio import annotations, indexer, library, reviews
from folio.charter import load as load_charter
from folio.commands import save

ATTENTION = "content/maps/attention.html"
LAB = "content/maps/lab-work.html"
ENTRY = "content/entries/attention-is-quadratic/index.html"
ENTRY_ROW = '<li><a href="/content/entries/attention-is-quadratic/">Why attention is quadratic</a></li>\n'
SOURCE = "content/sources/2017-attention-is-all-you-need/index.html"
SHELL = (Path(__file__).resolve().parents[1] / "shell/folio.js").read_text(encoding="utf-8")


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


def make_repo(path: Path) -> Path:
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Ada")
    git(path, "config", "user.email", "ada@example.org")
    git(path, "add", "-A", ".")
    git(path, "commit", "-q", "-m", "start")
    return path


def messages(lib_dir: Path, check: str) -> list[tuple[str, str]]:
    return [(p.path, p.message) for p in found(lib_dir, check)]


def catalog(lib_dir: Path) -> dict[str, dict]:
    built = json.loads(indexer.build(library.load_at(lib_dir))["catalog.json"])
    return {d["id"]: d for d in built["documents"]}


def out_of(capsys) -> str:
    return capsys.readouterr().out


# -- the check ----------------------------------------------------------------------

def test_the_sample_has_every_page_in_one_place(sample: Path) -> None:
    assert found(sample, "placement") == [] and found(sample, "heading-size") == []


def test_a_placed_page_on_no_home_map_is_named(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    edit(sample / "content/concepts/softmax/index.html", "</main>",
         '<p><a href="/content/entries/attention-is-quadratic/">Why</a></p>\n</main>')
    (msg,) = messages(sample, "placement")
    assert msg[0] == ENTRY and "on no home map" in msg[1] and "--section" in msg[1]
    assert found(sample, "placement")[0].severity == "warning"


def test_two_home_maps_are_two_places(sample: Path) -> None:
    edit(sample / LAB, "<ul class=\"rows\">", '<h2 id="background">Background</h2>\n<ul class="rows">\n'
         '<li><a href="/content/entries/attention-is-quadratic/">Why</a></li>')
    (msg,) = messages(sample, "placement")
    assert msg[0] == ENTRY and "2 places" in msg[1] and "attention, lab-work" in msg[1]
    assert "folio map move" in msg[1]
    assert catalog(sample)["attention-is-quadratic"]["place"] is None


def test_a_row_above_the_first_heading_is_under_none(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    edit(sample / ATTENTION, '<h2 id="take">', '<ul class="rows">\n' + ENTRY_ROW + '</ul>\n<h2 id="take">')
    (msg,) = messages(sample, "placement")
    assert msg[0] == ENTRY and "outside every heading" in msg[1] and "(the map has no heading)" not in msg[1]
    assert catalog(sample)["attention-is-quadratic"]["place"] == {"map": "attention", "section": None, "anchor": None}


def test_a_map_with_placed_rows_needs_a_heading(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    edit(sample / LAB, "<ul class=\"rows\">", '<ul class="rows">\n' + ENTRY_ROW)
    (msg,) = messages(sample, "placement")
    assert "home map `lab-work` outside every heading (the map has no heading)" in msg[1]


def test_a_mention_in_a_maps_prose_is_not_a_place(sample: Path) -> None:
    edit(sample / LAB, "<ul class=\"rows\">",
         '<p>See also <a href="/content/entries/attention-is-quadratic/">the cost</a>.</p>\n<ul class="rows">')
    assert found(sample, "placement") == []
    assert catalog(sample)["attention-is-quadratic"]["place"]["map"] == "attention"


def test_a_row_on_a_map_that_is_not_a_home_map_is_not_a_place(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "map", "reading-path", "--title", "A path", "--description", "In order.",
                 monkeypatch=monkeypatch) == 0
    assert folio(sample, "map", "add", "reading-path", "attention-is-quadratic", "--section", "First",
                 monkeypatch=monkeypatch) == 0
    edit(sample / ATTENTION, '<h2 id="reading">', '<p><a href="/content/maps/reading-path.html">A path</a></p>\n'
                                                 '<h2 id="reading">')
    assert found(sample, "placement") == []


def test_a_cited_page_is_never_a_row(sample: Path) -> None:
    edit(sample / ATTENTION, "</ul>\n<h2 id=\"reading\">",
         '<li><a href="/content/sources/2017-attention-is-all-you-need/">AIAYN</a></li>\n</ul>\n<h2 id="reading">')
    (msg,) = messages(sample, "placement")
    assert msg[0] == SOURCE and "row on map `attention`" in msg[1] and "cited, never placed" in msg[1]


def test_a_retired_page_needs_no_place(sample: Path, monkeypatch) -> None:
    assert folio(sample, "rm", "attention-is-quadratic", "--to", "softmax", monkeypatch=monkeypatch) == 0
    assert found(sample, "placement") == []


def test_the_charter_makes_placement_an_error_or_turns_it_off(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    edit(sample / "folio.yaml", "checks:\n", "checks:\n  placement: error\n")
    assert [p.severity for p in found(sample, "placement")] == ["error"]
    edit(sample / "folio.yaml", "placement: error", "placement: off")
    assert found(sample, "placement") == []


def test_no_home_maps_is_said_once_on_the_charter(sample: Path) -> None:
    edit(sample / "folio.yaml", "maps: [attention, lab-work]", "maps: []")
    (msg,) = messages(sample, "placement")
    assert msg[0] == "folio.yaml" and "lists none under `home.maps`" in msg[1]


def test_a_heading_past_twelve_rows_warns(sample: Path) -> None:
    rows = "".join(f'<li><a href="/content/concepts/c{i}/">C{i}</a></li>\n' for i in range(12))
    for i in range(12):
        folder = sample / f"content/concepts/c{i}"
        folder.mkdir()
        (folder / "index.html").write_text(
            (sample / "content/concepts/self-attention/index.html").read_text()
            .replace('id="self-attention"', f'id="c{i}"')
            .replace("Self-attention", f"Term {i}"))
    edit(sample / ATTENTION, '<h2 id="reading">', '<ul class="rows">\n' + rows + '</ul>\n<h2 id="reading">')
    (msg,) = messages(sample, "heading-size")
    assert msg[0] == ATTENTION and "heading `Basics` holds 17 rows" in msg[1]
    assert found(sample, "heading-size")[0].severity == "warning"


# -- the index ----------------------------------------------------------------------

def test_the_catalog_holds_each_place_and_each_sources_maps(sample: Path) -> None:
    docs = catalog(sample)
    assert docs["attention-is-quadratic"]["place"] == {"map": "attention", "section": "Basics", "anchor": "basics"}
    assert docs["2017-attention-is-all-you-need-reading"]["place"]["section"] == "Reading"
    assert docs["2017-attention-is-all-you-need"]["used_by"] == ["attention"]
    assert "place" not in docs["2017-attention-is-all-you-need"]
    assert "place" not in docs["attention"] and "used_by" not in docs["attention-is-quadratic"]


def test_an_anchor_is_the_headings_id_or_its_text_as_the_shell_slugs_it(sample: Path) -> None:
    edit(sample / ATTENTION, '<h2 id="basics">Basics</h2>', "<h2>The <em>very</em> basics!</h2>")
    assert catalog(sample)["softmax"]["place"] == {"map": "attention", "section": "The very basics!",
                                                   "anchor": "the-very-basics"}
    assert "function slug(text) { return text.toLowerCase().replace(/[^a-z0-9]+/g, \"-\")" in SHELL


def test_a_source_is_used_by_each_home_map_that_links_it_in_the_charters_order(sample: Path) -> None:
    edit(sample / LAB, "<ul class=\"rows\">",
         '<p>Background: <a href="/content/sources/2017-attention-is-all-you-need/">the paper</a>.</p>\n<ul class="rows">')
    edit(sample / "folio.yaml", "maps: [attention, lab-work]", "maps: [lab-work, attention]")
    assert catalog(sample)["2017-attention-is-all-you-need"]["used_by"] == ["lab-work", "attention"]


# -- folio map add and move ---------------------------------------------------------------

def test_map_add_puts_a_row_under_a_section(sample: Path, monkeypatch) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    assert folio(sample, "map", "add", "attention", "attention-is-quadratic", "--section", "Reading",
                 monkeypatch=monkeypatch) == 0
    assert catalog(sample)["attention-is-quadratic"]["place"]["section"] == "Reading"


def test_map_add_refuses_a_second_place_and_a_source(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "map", "add", "lab-work", "softmax", "--section", "Background", monkeypatch=monkeypatch) == 2
    err = capsys.readouterr().err
    assert "already has its place on home map attention" in err and "folio map move softmax --to lab-work" in err
    assert folio(sample, "map", "add", "lab-work", "2017-attention-is-all-you-need", "--section", "Background",
                 monkeypatch=monkeypatch) == 2
    assert "it is cited, never placed" in capsys.readouterr().err
    edit(sample / "folio.yaml", "checks:\n", "checks:\n  placement: off\n")
    assert folio(sample, "map", "add", "lab-work", "softmax", monkeypatch=monkeypatch) == 0


def test_map_add_refuses_a_place_outside_every_heading(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    assert folio(sample, "map", "add", "lab-work", "attention-is-quadratic", monkeypatch=monkeypatch) == 2
    assert "outside every heading on home map lab-work; give --section" in capsys.readouterr().err
    assert folio(sample, "map", "add", "lab-work", "attention-is-quadratic", "--section", "Background",
                 monkeypatch=monkeypatch) == 0
    assert found(sample, "placement") == []


def test_map_move_moves_a_row_to_another_map_and_heading(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "map", "move", "softmax", "--to", "lab-work#Background", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "row for softmax moved to lab-work" in out and "moved here from attention in `Background`" in out
    assert "/content/concepts/softmax/" not in (sample / ATTENTION).read_text().split("<main>")[1].split("Basics")[1] \
        .split("Reading")[0]
    text = (sample / LAB).read_text()
    assert '<h2 id="background">Background</h2>\n<ul class="rows">\n<li><a href="/content/concepts/softmax/">' \
           'Softmax</a> <span class="why">Read first.</span></li>' in text
    assert catalog(sample)["softmax"]["place"] == {"map": "lab-work", "section": "Background", "anchor": "background"}
    assert found(sample, "placement") == []


def test_map_move_within_a_map_and_by_a_headings_id(sample: Path, monkeypatch) -> None:
    assert folio(sample, "map", "move", "attention-is-quadratic", "--to", "attention#reading",
                 monkeypatch=monkeypatch) == 0
    assert catalog(sample)["attention-is-quadratic"]["place"]["section"] == "Reading"
    assert (sample / ATTENTION).read_text().count("/content/entries/attention-is-quadratic/") == 1


def test_map_move_asks_which_row_when_several_maps_list_it(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / LAB, "<ul class=\"rows\">", '<h2 id="background">Background</h2>\n<ul class="rows">\n'
         '<li><a href="/content/entries/attention-is-quadratic/">Why</a></li>')
    assert folio(sample, "map", "move", "attention-is-quadratic", "--to", "attention#Reading",
                 monkeypatch=monkeypatch) == 2
    assert "give --from <map>" in capsys.readouterr().err
    assert folio(sample, "map", "move", "attention-is-quadratic", "--to", "attention#Reading", "--from", "lab-work",
                 monkeypatch=monkeypatch) == 2
    assert "attention already lists" in capsys.readouterr().err
    assert folio(sample, "map", "rm", "lab-work", "attention-is-quadratic", monkeypatch=monkeypatch) == 0
    assert found(sample, "placement") == []


def test_map_move_needs_to_and_names_what_is_wrong(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "map", "move", "softmax", monkeypatch=monkeypatch) == 2
    assert "folio map move <doc> --to" in capsys.readouterr().err
    assert folio(sample, "map", "add", "attention", "softmax", "--to", "x", monkeypatch=monkeypatch) == 2
    assert "--to and --from go with `folio map move`" in capsys.readouterr().err
    assert folio(sample, "map", "move", "2017-attention-is-all-you-need", "--to", "attention",
                 monkeypatch=monkeypatch) == 2
    assert "cited, never placed" in capsys.readouterr().err


# -- folio new -----------------------------------------------------------------------

def test_new_says_a_placed_page_needs_a_place(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "new", "note", "rope", "--title", "RoPE", "--description", "Rotary.",
                 monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "note: rope needs a place before it is saved" in out and "--section <heading>" in out
    assert "To review" not in out
    assert folio(sample, "new", "map", "other-map", monkeypatch=monkeypatch) == 0
    assert "needs a place" not in out_of(capsys)
    edit(sample / "folio.yaml", "checks:\n", "checks:\n  placement: off\n")
    assert folio(sample, "new", "note", "alibi", monkeypatch=monkeypatch) == 0
    assert "needs a place" not in out_of(capsys)


def test_under_review_after_a_new_page_starts_live_and_on_the_list(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: after\nchecks:")
    assert load_charter(sample).save.review == "after"
    assert folio(sample, "new", "note", "rope", "--title", "RoPE", "--description", "Rotary.",
                 monkeypatch=monkeypatch) == 0
    assert "rope is live and on the To review list" in out_of(capsys)
    text = (sample / "content/notes/rope.html").read_text()
    assert 'name="status"' not in text
    marks = annotations.review_marks(sample, "content/notes/rope.html")
    assert [(m["mark"], m["note"], m["date"]) for m in marks] == [("changed", "new", "2026-10-03")]
    assert folio(sample, "journal", "add", "--title", "A day", "--description", "D.", "--body", "B.",
                 monkeypatch=monkeypatch) == 0
    lib = library.load_at(sample)
    assert [r["doc"] for r in reviews.to_review(lib)] == ["rope"]


# -- review after landing -----------------------------------------------------------------

def test_review_add_list_and_done(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "review", "list", monkeypatch=monkeypatch) == 0
    assert "Nothing to review." in out_of(capsys)
    assert folio(sample, "review", "add", "softmax", "--note", "New overflow section", "--author", "agent:w",
                 monkeypatch=monkeypatch) == 0
    monkeypatch.setenv("FOLIO_TODAY", "2026-10-05")
    assert folio(sample, "review", "add", "attention-is-quadratic", "--note", "Rewrote the opening",
                 "--author", "agent:w", monkeypatch=monkeypatch) == 0
    out_of(capsys)
    assert folio(sample, "review", "list", "--json", monkeypatch=monkeypatch) == 0
    rows = json.loads(out_of(capsys))
    assert [(r["doc"], r["date"], r["note"], r["state"]) for r in rows] == [
        ("attention-is-quadratic", "2026-10-05", "Rewrote the opening", "to review"),
        ("softmax", "2026-10-03", "New overflow section", "to review")]
    assert folio(sample, "review", "done", "softmax", "--author", "Ada", monkeypatch=monkeypatch) == 0
    assert "softmax reviewed" in out_of(capsys)
    assert folio(sample, "review", "list", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "attention-is-quadratic" in out and "softmax" not in out
    assert folio(sample, "review", "list", "--all", monkeypatch=monkeypatch) == 0
    assert "softmax (concept) [reviewed]" in out_of(capsys)
    assert folio(sample, "review", "done", "softmax", "--author", "Ada", monkeypatch=monkeypatch) == 2
    assert "not on the To review list" in capsys.readouterr().err
    sidecar = json.loads((sample / "content/concepts/softmax/index.annotations.json").read_text())
    assert [m["mark"] for m in sidecar["review"]] == ["changed", "reviewed"] and sidecar["threads"] == []
    # A later change puts it back.
    assert folio(sample, "review", "add", "softmax", "--note", "Fixed the bound", monkeypatch=monkeypatch) == 0
    assert {r["doc"] for r in reviews.to_review(library.load_at(sample))} == {"attention-is-quadratic", "softmax"}


def test_review_marks_live_beside_threads_and_are_kept(sample: Path, monkeypatch) -> None:
    rel = "content/notes/flashattention-tiling.html"
    assert folio(sample, "review", "add", "flashattention-tiling", "--note", "Shorter", "--author", "a",
                 monkeypatch=monkeypatch) == 0
    lib = library.load_at(sample)
    annotations.add(lib, rel, "question", "the exact result", "Why?", "Ada")
    data = json.loads((sample / annotations.sidecar_path(rel)).read_text())
    assert len(data["threads"]) == 1 and data["review"][0]["note"] == "Shorter"
    assert found(sample, "stale-quote") == []


def test_review_refuses_what_never_goes_on_the_list(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "review", "add", "R-4", "--note", "x", monkeypatch=monkeypatch) == 2
    assert "does not go on the To review list" in capsys.readouterr().err
    assert folio(sample, "review", "add", "softmax", monkeypatch=monkeypatch) == 2
    assert "needs --note" in capsys.readouterr().err


def test_a_retired_page_leaves_the_list(sample: Path, monkeypatch) -> None:
    assert folio(sample, "review", "add", "attention-is-quadratic", "--note", "x", monkeypatch=monkeypatch) == 0
    assert folio(sample, "rm", "attention-is-quadratic", "--to", "softmax", monkeypatch=monkeypatch) == 0
    assert reviews.to_review(library.load_at(sample)) == []


def test_save_under_after_puts_new_pages_on_the_list(sample: Path, monkeypatch) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: after\nchecks:")
    make_repo(sample)
    (sample / "content/notes/plain.html").write_text(
        (sample / "content/notes/flashattention-tiling.html").read_text().replace("FlashAttention tiling", "Plain"))
    edit(sample / ATTENTION, "</ul>\n<h2 id=\"reading\">",
         '<li><a href="/content/notes/plain.html">Plain</a></li>\n</ul>\n<h2 id="reading">')
    edit(sample / "content/concepts/softmax/index.html", "</main>", "<p>More.</p>\n</main>")
    monkeypatch.chdir(sample)
    done = save.save(sample, push=False)
    assert done.commit is not None
    assert "content/notes/plain.annotations.json" in done.files
    lib = library.load_at(sample)
    assert [r["doc"] for r in reviews.to_review(lib)] == ["plain"]  # an edit is a change only when said
    assert git(sample, "status", "--porcelain") == ""


def test_the_server_records_a_reviewed_mark_as_a_commit(sample: Path, server_for) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: after\nchecks:")
    make_repo(sample)
    lib = library.load_at(sample)
    reviews.changed(lib, "softmax", "New section", "agent")
    srv = server_for(sample)
    status, body = srv.get("/_folio/inbox")
    data = json.loads(body)
    assert status == 200 and data["reviewing"] == 1 and data["to_review"][0]["doc"] == "softmax"
    status, reply = srv.post({"action": "reviewed", "doc": "content/concepts/softmax/index.html"})
    assert status == 200 and reply["thread"]["reviewed"] == "softmax"
    assert git(sample, "log", "-1", "--format=%s %an") == "Review softmax Ada"
    assert git(sample, "show", "--name-only", "--format=", "HEAD") == "content/concepts/softmax/index.annotations.json"
    assert json.loads(srv.get("/_folio/inbox")[1])["reviewing"] == 0
    status, reply = srv.post({"action": "reviewed", "doc": "content/concepts/softmax/index.html"})
    assert status == 400 and "not on the To review list" in reply["error"]


def test_charter_takes_after_and_refuses_other_words(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: later\nchecks:")
    with pytest.raises(Exception, match="drafts or after"):
        load_charter(sample)


# -- the shell ----------------------------------------------------------------------

def test_the_shell_draws_the_path_the_rail_the_sources_and_the_review_tab() -> None:
    assert "function placePath(doc, part)" in SHELL and '"aria-label": "Where this page lives"' in SHELL
    assert "!(d.place && d.place.map !== map.id)" in SHELL  # the rail reads the same place
    assert 'class: "f-rdraft"' in SHELL and 'd.status !== "draft" && inFocus(d); });\n      var name' not in SHELL
    assert "function mapSources(map)" in SHELL and 'panelSection("Sources"' in SHELL
    assert 'chip("review", "To review"' in SHELL and 'action: "reviewed"' in SHELL


def test_problems_name_no_file_twice_for_one_place(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    assert [p.path for p in problems(sample) if p.check == "placement"] == [ENTRY]


@pytest.fixture
def server_for():
    from test_comments import Server

    servers = []

    def start(root: Path):
        s = Server(root)
        servers.append(s)
        return s
    yield start
    for s in servers:
        s.close()
