"""One place per page: the placement and heading-size checks, place and used_by in the catalog,
`folio map add --section` and `folio map move`, and `folio new`'s note."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import edit, folio, found, problems
from folio import indexer, library
from folio.charter import load as load_charter

ATTENTION = "content/maps/attention.html"
LAB = "content/maps/lab-work.html"
ENTRY = "content/entries/attention-is-quadratic/index.html"
ENTRY_ROW = '<li><a href="/content/entries/attention-is-quadratic/">Why attention is quadratic</a></li>\n'
SOURCE = "content/sources/2017-attention-is-all-you-need/index.html"
SHELL = (Path(__file__).resolve().parents[1] / "shell/folio.js").read_text(encoding="utf-8")


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


def test_a_list_styled_like_rows_without_the_rows_class_is_a_pointer(sample: Path) -> None:
    edit(sample / LAB, "<ul class=\"rows\">", '<h2 id="background">Background</h2>\n<ul class="lab-rows">\n'
         '<li><a href="/content/entries/attention-is-quadratic/">Why</a></li>\n</ul>\n<ul class="rows">')
    assert messages(sample, "placement") == []
    assert catalog(sample)["attention-is-quadratic"]["place"]["map"] == "attention"


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


def test_folio_maps_does_not_list_a_source_as_on_no_map(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "maps", "--json", monkeypatch=monkeypatch) == 0
    unmapped = {d["id"] for d in json.loads(out_of(capsys))["unmapped"]}
    assert "2017-attention-is-all-you-need" not in unmapped and "2017-attention-is-all-you-need-reading" not in unmapped


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
    assert folio(sample, "new", "map", "other-map", monkeypatch=monkeypatch) == 0
    assert "needs a place" not in out_of(capsys)
    edit(sample / "folio.yaml", "checks:\n", "checks:\n  placement: off\n")
    assert folio(sample, "new", "note", "alibi", monkeypatch=monkeypatch) == 0
    assert "needs a place" not in out_of(capsys)


def test_the_charter_names_what_was_removed(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:", "save:\n  review: after\nchecks:")
    with pytest.raises(Exception, match="save.review` was removed"):
        load_charter(sample)
    edit(sample / "folio.yaml", "save:\n  review: after\n", "comments:\n  identity_header: X-User\n")
    with pytest.raises(Exception, match="comments` was removed"):
        load_charter(sample)


# -- the shell ----------------------------------------------------------------------

def test_the_shell_draws_the_path_the_rail_and_the_sources() -> None:
    assert "function placePath(doc, part)" in SHELL and '"aria-label": "Where this page lives"' in SHELL
    assert "!(d.place && d.place.map !== map.id)" in SHELL  # the rail reads the same place
    assert 'class: "f-rdraft"' in SHELL and 'd.status !== "draft" && inFocus(d); });\n      var name' not in SHELL
    assert "function mapSources(map)" in SHELL and 'panelSection("Sources"' in SHELL
    assert "_folio/annotations" not in SHELL and "_folio/inbox" not in SHELL


def test_problems_name_no_file_twice_for_one_place(sample: Path) -> None:
    edit(sample / ATTENTION, ENTRY_ROW, "")
    assert [p.path for p in problems(sample) if p.check == "placement"] == [ENTRY]
