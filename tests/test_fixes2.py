"""Regression tests for the second fix pass (lab2 and kb2 findings), one or more per decision."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import edit, folio, found

from folio import library
from folio.cli import parser
from folio.site.site import Site

ROOT = Path(__file__).resolve().parent.parent
SHELL = (ROOT / "shell/folio.js").read_text(encoding="utf-8")
NOTE = "content/notes/flashattention-tiling.html"


def out_of(capsys) -> str:
    return capsys.readouterr().out


def git(lib_dir: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(lib_dir), *args], check=True, capture_output=True,
                          text=True).stdout


def commit_all(lib_dir: Path, message: str = "start") -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    if not (lib_dir / ".git").exists():
        git(lib_dir, "init", "-q")
    git(lib_dir, "add", "-A")
    git(lib_dir, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", message)


def note_body(lib_dir: Path, body: str) -> None:
    path = lib_dir / NOTE
    text = path.read_text()
    start, end = text.index("<main>") + len("<main>"), text.index("</main>")
    path.write_text(text[:start] + "\n" + body + "\n" + text[end:])


# 1. A result's protocol may be abandoned

def test_result_of_an_abandoned_protocol_stays_valid(sample: Path) -> None:
    edit(sample / "content/protocols/pi-error-scaling.md", "status: locked", "status: abandoned")
    assert not [p for p in found(sample, "fields") if p.path.startswith("content/results/")]
    edit(sample / "content/protocols/pi-error-scaling.md", "status: abandoned", "status: draft")
    assert [p for p in found(sample, "fields") if p.path.startswith("content/results/")]


# 2. A protocol cited beside a number counts

def test_uncited_number_accepts_a_protocol_citation(sample: Path) -> None:
    note_body(sample, '<p>The threshold was 80% of lists.</p>')
    assert [p for p in found(sample, "uncited-number") if p.path == NOTE]
    note_body(sample, '<p>The threshold was 80% of lists, set in '
                      '<a href="/content/protocols/pi-error-scaling.md">the protocol</a>.</p>')
    assert not [p for p in found(sample, "uncited-number") if p.path == NOTE]


# 3. An honest mention of a superseded result is not flagged

def test_cites_superseded_spares_an_honest_mention(sample: Path) -> None:
    note_body(sample, '<p>The first run, <a href="/content/results/R-3.md">R-3</a>, fitted the mean absolute error.</p>')
    assert [p for p in found(sample, "cites-superseded") if p.path == NOTE]
    note_body(sample, '<p>The first run, <a href="/content/results/R-3.md">R-3</a>, since superseded, '
                      'fitted the mean absolute error.</p>')
    assert not [p for p in found(sample, "cites-superseded") if p.path == NOTE]
    note_body(sample, '<ul><li><a href="/content/results/R-3.md">R-3</a> (retracted)</li>'
                      '<li><a href="/content/results/R-3.md">R-3</a> again</li></ul>')
    assert [p for p in found(sample, "cites-superseded") if p.path == NOTE]  # the second item says nothing


# 4. A map row's link text is the shell's, from the catalog

def test_uncited_number_ignores_map_row_link_text(sample: Path) -> None:
    edit(sample / "content/maps/lab-work.html", ">The pi estimate's error falls as 1/sqrt(n)</a>",
         ">The pi estimate's error falls 2× per 4× points</a>")
    assert not [p for p in found(sample, "uncited-number") if p.path == "content/maps/lab-work.html"]
    edit(sample / "content/maps/lab-work.html", "</ul>", "</ul>\n<p>It wins 3× often.</p>")
    assert [p for p in found(sample, "uncited-number") if p.path == "content/maps/lab-work.html"]


def test_shell_draws_row_text_from_the_catalog() -> None:
    assert "if (target.title) a.textContent = target.title;" in SHELL


# 6. Ids compare without regard to case

def test_ids_compare_without_case(sample: Path, monkeypatch, capsys) -> None:
    lib = library.load_at(sample)
    assert lib.find("r-3")[0].id == "R-3" and lib.by_id.get("SOFTMAX")
    assert folio(sample, "cite", "c-1", monkeypatch=monkeypatch) == 0
    assert "C-1 (claim" in out_of(capsys)
    assert folio(sample, "journal", "--about", "r-4", monkeypatch=monkeypatch) == 0
    assert "Recorded R-4" in out_of(capsys)
    edit(sample / NOTE, '<meta name="genre"', '<meta name="id" content="SoftMax">\n<meta name="genre"')
    assert any("ids are unique" in p.message for p in found(sample, "unique-id"))


def test_new_refuses_an_id_taken_in_another_case(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / NOTE, '<meta name="genre"', '<meta name="id" content="Fresh-Note">\n<meta name="genre"')
    assert folio(sample, "new", "note", "fresh-note", monkeypatch=monkeypatch) == 2
    assert "taken by content/notes/flashattention-tiling.html" in capsys.readouterr().err


# 7. Set-up commits assets/

def test_init_leaves_assets_committable(tmp_path: Path, monkeypatch) -> None:
    assert folio(tmp_path, "init", "lib", monkeypatch=monkeypatch) == 0
    assert (tmp_path / "lib/assets/figures/.gitkeep").is_file() and (tmp_path / "lib/assets/data/.gitkeep").is_file()
    assert "`assets/`" in (ROOT / "skills/set-up/SKILL.md").read_text()


# 10. Fields in the card's order

def test_catalog_keeps_the_card_field_order(sample: Path) -> None:
    from folio import indexer

    entry = next(d for d in indexer.catalog(library.load_at(sample))["documents"] if d["id"] == "R-4")
    assert entry["field_order"] == ["protocol", "number", "baseline", "bound", "evidence", "rederive", "date",
                                    "supersedes"]
    assert "doc.field_order" in SHELL


# 11. Frozen since

def test_site_data_says_since_when_a_document_is_frozen(sample: Path) -> None:
    protocol = sample / "content/protocols/pi-error-scaling.md"
    edit(protocol, "status: locked", "status: draft")
    key = "content/protocols/pi-error-scaling.md"
    commit_all(sample)
    assert key not in Site.load(sample).site_data()["frozen"]
    edit(protocol, "status: draft", "status: locked")
    assert key not in Site.load(sample).site_data()["frozen"]  # not committed yet
    commit_all(sample, "lock")
    frozen = Site.load(sample).site_data()["frozen"]
    assert key in frozen and "content/notes/flashattention-tiling.html" not in frozen
    assert frozen["content/protocols/pi-error-scaling.md"] == git(sample, "log", "-1", "--format=%cs").strip()
    assert '"Frozen since "' in SHELL


# 12. The journal slug from the first six words

def test_journal_slug_takes_the_first_six_words(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "journal", "add", "--title", "Decided to keep the tiled kernel for every long sequence",
                 "--description", "Kept.", "--body", "Kept.", monkeypatch=monkeypatch) == 0
    assert "2026-10-03-decided-to-keep-the-tiled-kernel.md" in out_of(capsys)


# 13 and 16. A map's rows, in its own order; the Cites panel leaves them out

def test_catalog_lists_map_rows_in_their_order(sample: Path, monkeypatch) -> None:
    from folio import indexer

    def rows() -> list[str]:
        cat = indexer.catalog(library.load_at(sample))["documents"]
        return next(d for d in cat if d["id"] == "lab-work")["rows"]

    assert rows() == ["content/questions/Q-1.md", "content/claims/C-1.md",
                      "content/reports/pi-error-scaling-report/index.html"]
    assert folio(sample, "map", "add", "lab-work", "R-4", "--after", "Q-1", monkeypatch=monkeypatch) == 0
    assert rows()[:2] == ["content/questions/Q-1.md", "content/results/R-4.md"]
    assert "(map.rows || []).map(byKey)" in SHELL
    assert "!rows[p]" in SHELL


# 15. A whole-page comment from the drawer

def test_drawer_offers_a_whole_page_comment() -> None:
    assert "Comment on the whole page" in SHELL and 'pendingQuote = ""; render();' in SHELL


# 17 and 21. New groups, and a fresh map's placeholder group

def test_map_add_on_a_fresh_map_replaces_the_placeholder(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "map", "fresh-map", monkeypatch=monkeypatch) == 0
    assert folio(sample, "map", "add", "fresh-map", "softmax", "--group", "Basics", monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/fresh-map.html").read_text()
    assert "{{group name}}" not in text and "{{link to a document}}" not in text
    assert text.index('<h2 id="basics">Basics</h2>') < text.index('<h2 id="open">')
    assert folio(sample, "map", "add", "fresh-map", "self-attention", monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/fresh-map.html").read_text()
    assert text.count('<ul class="rows">') == 1


def test_map_add_new_group_at_the_end_or_after_a_group(sample: Path, monkeypatch, capsys) -> None:
    attention = sample / "content/maps/attention.html"
    assert folio(sample, "map", "add", "attention", "self-attention", "--group", "Later", monkeypatch=monkeypatch) == 0
    text = attention.read_text()
    assert text.index('<h2 id="later">') > text.index('<h2 id="reading">')
    assert folio(sample, "map", "add", "attention", "2022-flashattention", "--group", "Surveys", "--after", "Basics",
                 monkeypatch=monkeypatch) == 0
    text = attention.read_text()
    assert text.index('<h2 id="basics">') < text.index('<h2 id="surveys">') < text.index('<h2 id="reading">')
    assert folio(sample, "map", "add", "attention", "R-4", "--after", "Basics", monkeypatch=monkeypatch) == 2
    assert "names a group" in capsys.readouterr().err


# 19 and 23. mv and rm stage what they change; rm names link text to review

def test_mv_and_rm_stage_their_changes(sample: Path, monkeypatch, capsys) -> None:
    commit_all(sample)
    assert folio(sample, "mv", "softmax", "softmax-function", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "staged" in out and "(git add)" in out
    unstaged = git(sample, "diff", "--name-only").split()
    assert not [p for p in unstaged if p.startswith("content/")]
    commit_all(sample, "moved")
    assert folio(sample, "rm", "self-attention", "--to", "softmax", monkeypatch=monkeypatch) == 0
    assert not [p for p in git(sample, "diff", "--name-only").split() if p.startswith("content/")]


def test_rm_names_link_text_that_still_names_the_retired_title(sample: Path, monkeypatch, capsys) -> None:
    note_body(sample, '<p>See <a href="/content/concepts/self-attention/">Self-attention</a> for the scores.</p>')
    assert folio(sample, "rm", "self-attention", "--to", "softmax", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert f'review: {NOTE} links to softmax with the text "Self-attention"' in out
    assert "review: content/maps/" not in out  # a map row's text is the shell's


# 25. Search: whole words or prefixes, statuses, retired last

def test_search_matches_words_and_prefixes(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "search", "soft", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "softmax (concept, live)" in out
    assert folio(sample, "search", "oftmax", monkeypatch=monkeypatch) == 0
    assert "softmax" not in out_of(capsys)  # inside a word is not a match
    assert folio(sample, "search", "a", monkeypatch=monkeypatch) == 2
    assert folio(sample, "search", "a", "soft", monkeypatch=monkeypatch) == 0
    assert "softmax" in out_of(capsys)


def test_search_lists_retired_documents_last(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "rm", "self-attention", "--to", "softmax", monkeypatch=monkeypatch) == 0
    capsys.readouterr()
    assert folio(sample, "search", "attention", "--json", monkeypatch=monkeypatch) == 0
    hits = json.loads(out_of(capsys))
    statuses = [h["status"] for h in hits]
    assert "retired" in statuses and statuses.index("retired") == len(statuses) - statuses.count("retired")


# 26. Journal chips show the genre

def test_journal_chips_show_the_genre() -> None:
    assert "function docChip(d)" in SHELL and SHELL.count("docChip(") >= 3


# 27. CLI polish

def test_every_subcommand_has_a_description() -> None:
    import argparse

    sub = next(a for a in parser()._actions if isinstance(a, argparse._SubParsersAction))
    assert all(c.description for c in sub.choices.values())
    assert all(a.help for a in sub._choices_actions)


def test_empty_answers_read_the_same(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "search", "zebra", monkeypatch=monkeypatch) == 0
    assert out_of(capsys) == "No matches.\n"
    assert folio(sample, "journal", "--kind", "meeting", "--since", "2027-01-01", monkeypatch=monkeypatch) == 0
    assert out_of(capsys) == "No journal entries match.\n"


def test_written_text_keeps_apostrophes_readable(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "note", "owners-note", "--title", "The owner's \"pick\" & more",
                 "--description", "It's one.", monkeypatch=monkeypatch) == 0
    page = (sample / "content/notes/owners-note.html").read_text()
    assert "&#x27;" not in page and "<title>The owner's \"pick\" &amp; more</title>" in page
    assert 'content="The owner\'s &quot;pick&quot; &amp; more"' in page
    assert library.load_at(sample).find("owners-note")[0].title == "The owner's \"pick\" & more"
    assert folio(sample, "map", "add", "attention", "owners-note", "--reason", "It's short.",
                 monkeypatch=monkeypatch) == 0
    text = (sample / "content/maps/attention.html").read_text()
    assert ">The owner's \"pick\" &amp; more</a> <span class=\"why\">It's short.</span>" in text


def test_the_library_rail_is_drawn_from_the_indices(sample: Path) -> None:
    # The rail lists each home map's rows and every document by genre, from catalog.json alone.
    from folio import indexer
    assert "function rail(view, rel)" in SHELL and 'store("rail:" + key' in SHELL
    assert 'e.key === "["' in SHELL and "f-rail-open" in SHELL
    lib = library.load_at(sample)
    docs = indexer.catalog(lib)["documents"]
    by_id = {d["id"]: d for d in docs}
    assert lib.charter.home_maps
    for map_id in lib.charter.home_maps:
        assert isinstance(by_id[map_id].get("rows"), list)
    assert all(d["genre"] and d["title"] and d["url"] for d in docs)
