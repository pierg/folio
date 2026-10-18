"""The graph commands: maps, map rows, tags, mv, promote, rm, search, cards and pack add."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import edit, folio, problems

from folio import library, redirects


# The sample keeps one redirect of its own: the report moved before it was ever served.
FIXTURE_REDIRECTS = {"content/reports/pi-error-scaling/index.html": "content/reports/pi-error-scaling-report/index.html"}


def errors(lib_dir: Path) -> list:
    return [p for p in problems(lib_dir) if p.severity == "error"]


def gate(lib_dir: Path, monkeypatch) -> None:
    """Index, then the gate passes with no error."""
    assert folio(lib_dir, "index", monkeypatch=monkeypatch) == 0
    found = errors(lib_dir)
    assert not found, [p.line() for p in found]


def out_of(capsys) -> str:
    return capsys.readouterr().out


def commit_all(lib_dir: Path) -> None:
    """Put the library in git, so its addresses count as published."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    for args in (("init", "-q"), ("add", "-A"),
                 ("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "start")):
        subprocess.run(["git", "-C", str(lib_dir), *args], check=True, capture_output=True)


# maps and rows

def test_maps_listing(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "maps", "--json", monkeypatch=monkeypatch) == 0
    data = json.loads(out_of(capsys))
    maps = {m["id"]: m for m in data["maps"]}
    assert [m["id"] for m in data["maps"]][:3] == ["home", "attention", "lab-work"]
    assert maps["attention"]["top_level"] and maps["home"]["home"]
    assert maps["attention"]["rows"][0] == {"id": "softmax", "path": "content/concepts/softmax/index.html",
                                          "href": "/content/concepts/softmax/", "title": "Softmax",
                                          "reason": "Read first."}
    unmapped = {d["id"]: d for d in data["unmapped"]}
    assert "self-attention" in unmapped and not unmapped["self-attention"]["orphan"]
    assert "2026-10-01-set-up-the-library" not in unmapped
    assert folio(sample, "maps", monkeypatch=monkeypatch) == 0
    assert "on no map:" in out_of(capsys)


def test_map_add_reason_rm(sample: Path, monkeypatch, capsys) -> None:
    page = sample / "content/maps/lab-work.html"
    assert folio(sample, "map", "add", "lab-work", "R-3", "--reason", "The first & fastest.",
                 monkeypatch=monkeypatch) == 0
    assert "updated content/maps/lab-work.html: row added for R-3" in out_of(capsys)
    text = page.read_text()
    assert '<li><a href="/content/results/R-3.md">The error of the pi estimate fell with a fitted log-log slope of -0.483</a> ' \
           '<span class="why">The first &amp; fastest.</span></li>\n</ul>' in text
    gate(sample, monkeypatch)
    assert folio(sample, "map", "add", "lab-work", "R-3", monkeypatch=monkeypatch) == 2
    assert folio(sample, "map", "reason", "lab-work", "R-3", "Superseded; read R-4.", monkeypatch=monkeypatch) == 0
    assert '<span class="why">Superseded; read R-4.</span>' in page.read_text()
    assert folio(sample, "map", "reason", "lab-work", "R-3", "", monkeypatch=monkeypatch) == 0
    assert 'R-3.md">The error of the pi estimate fell with a fitted log-log slope of -0.483</a></li>' in page.read_text()
    out_of(capsys)
    assert folio(sample, "map", "rm", "lab-work", "R-3", monkeypatch=monkeypatch) == 0
    assert "row for R-3 removed" in out_of(capsys)
    assert "R-3.md" not in page.read_text()
    gate(sample, monkeypatch)


def test_map_add_without_rows_and_ambiguous_ids(sample: Path, monkeypatch, capsys) -> None:
    # The map command takes the map by its id.
    assert folio(sample, "map", "add", "attention", "self-attention", monkeypatch=monkeypatch) == 0
    assert '<a href="/content/concepts/self-attention/">Self-attention</a></li>' in \
           (sample / "content/maps/attention.html").read_text()
    home = sample / "content/index.html"
    edit(home, '<ul class="rows">\n<li><a href="/content/projects/attention-kernel/">Attention kernel</a> '
               '<span class="why">The project that started it.</span></li>\n</ul>\n', "")
    assert folio(sample, "map", "add", "content/index.html", "attention-kernel", monkeypatch=monkeypatch) == 0
    assert '<ul class="rows">\n<li><a href="/content/projects/attention-kernel/">Attention kernel</a></li>\n</ul>\n</main>' \
           in home.read_text()
    gate(sample, monkeypatch)


def test_map_rm_warns_of_an_orphan(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "map", "rm", "attention", "tiled-attention", monkeypatch=monkeypatch) == 0
    assert "tiled-attention is now on no map" in out_of(capsys)
    assert folio(sample, "map", "rm", "attention", "tiled-attention", monkeypatch=monkeypatch) == 2


# tags

def test_tags_list_and_rename(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "tags", "--json", monkeypatch=monkeypatch) == 0
    rows = {r["tag"]: r for r in json.loads(out_of(capsys))}
    assert rows["attention"]["count"] == 5 and "softmax" in rows["attention"]["documents"]
    assert rows["monte-carlo"]["documents"] == ["Q-1"]
    assert folio(sample, "tags", "rename", "attention", "long-context", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "updated content/entries/attention-is-quadratic/index.html: tag attention -> long-context" in out
    assert 'content="long-context"' in (sample / "content/entries/attention-is-quadratic/index.html").read_text()
    assert folio(sample, "tags", "rename", "monte-carlo", "sampling", monkeypatch=monkeypatch) == 0
    assert "updated content/questions/Q-1.md: tag monte-carlo -> sampling" in out_of(capsys)
    assert 'tags: ["sampling"]' in (sample / "content/questions/Q-1.md").read_text()
    gate(sample, monkeypatch)
    assert folio(sample, "tags", "rename", "nope", "other", monkeypatch=monkeypatch) == 2
    assert folio(sample, "tags", "rename", "setup", "Bad Tag", monkeypatch=monkeypatch) == 2


def test_tags_rename_leaves_permanent_documents(sample: Path, monkeypatch, capsys) -> None:
    before = (sample / "content/journal/2026/2026-10-01-set-up-the-library.md").read_text()
    assert folio(sample, "tags", "rename", "setup", "set-up", monkeypatch=monkeypatch) == 0
    assert "(permanent): it keeps the tag `setup`" in out_of(capsys)
    assert (sample / "content/journal/2026/2026-10-01-set-up-the-library.md").read_text() == before


# mv

def test_mv_rewrites_links_keeps_id_and_redirects(sample: Path, monkeypatch, capsys) -> None:
    commit_all(sample)
    concept = sample / "content/concepts/softmax"
    (concept / "index.annotations.json").write_text('{"threads": []}\n')
    assert folio(sample, "mv", "softmax", "softmax-function", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "moved content/concepts/softmax/index.html -> content/concepts/softmax-function/index.html" in out
    assert "moved content/concepts/softmax/index.annotations.json -> " \
           "content/concepts/softmax-function/index.annotations.json" in out
    assert "updated content/maps/attention.html: links to softmax rewritten" in out
    assert not concept.exists()
    new = sample / "content/concepts/softmax-function/index.html"
    assert '<meta name="id" content="softmax">' in new.read_text()
    assert 'href="../../concepts/softmax-function/"' in \
           (sample / "content/entries/attention-is-quadratic/index.html").read_text()
    assert redirects.load(sample) == {**FIXTURE_REDIRECTS, "content/concepts/softmax/index.html":
                                      "content/concepts/softmax-function/index.html"}
    lib = library.load_at(sample)
    assert [d.key for d in lib.find("softmax")] == ["content/concepts/softmax-function/index.html"]
    gate(sample, monkeypatch)  # \fcite{softmax} in the paper still resolves


def test_mv_chain_and_path_form(sample: Path, monkeypatch, capsys) -> None:
    commit_all(sample)
    assert folio(sample, "mv", "flashattention-tiling", "content/notes/tiling.html", monkeypatch=monkeypatch) == 0
    assert folio(sample, "mv", "flashattention-tiling", "tiling-by-blocks", monkeypatch=monkeypatch) == 0
    assert redirects.load(sample) == {**FIXTURE_REDIRECTS, 
        "content/notes/flashattention-tiling.html": "content/notes/tiling-by-blocks.html",
        "content/notes/tiling.html": "content/notes/tiling-by-blocks.html",
    }
    gate(sample, monkeypatch)
    assert folio(sample, "mv", "flashattention-tiling", "flashattention-tiling", monkeypatch=monkeypatch) == 0
    assert "content/notes/flashattention-tiling.html" not in redirects.load(sample)
    gate(sample, monkeypatch)


def test_mv_leaves_permanent_links_to_the_redirect(sample: Path, monkeypatch, capsys) -> None:
    entry = sample / "content/journal/2026/2026-10-01-set-up-the-library.md"
    entry.write_text(entry.read_text().rstrip("\n") + " See [self-attention](/content/concepts/self-attention/).\n")
    before = entry.read_text()
    commit_all(sample)
    assert folio(sample, "mv", "self-attention", "merging", monkeypatch=monkeypatch) == 0
    assert "left content/journal/2026/2026-10-01-set-up-the-library.md (permanent)" in out_of(capsys)
    assert entry.read_text() == before
    gate(sample, monkeypatch)  # the old address resolves through the redirect


def test_mv_refusals(sample: Path, monkeypatch, capsys) -> None:
    for args in (("R-3", "r-one"), ("Q-1", "q-one"), ("home", "start"), ("softmax", "Bad Slug"),
                 ("softmax", "content/notes/softmax.html"), ("softmax", "self-attention"),
                 ("2026-10-01-set-up-the-library", "x"), ("nothing-here", "x")):
        assert folio(sample, "mv", *args, monkeypatch=monkeypatch) == 2, args
    err = capsys.readouterr().err
    assert "R-3.md is permanent; it is never moved" in err and "never changes" in err
    gate(sample, monkeypatch)


def test_mv_multi_part_and_folder_files(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "mv", "content/guides/attention-from-scratch/index.html", "attention-basics", monkeypatch=monkeypatch) == 0
    guide = sample / "content/guides/attention-basics"
    assert sorted(p.name for p in guide.iterdir()) == ["01-scores.html", "02-softmax.html", "index.html"]
    assert folio(sample, "mv", "tiled-attention", "tiled-kernels", monkeypatch=monkeypatch) == 0
    assert (sample / "content/papers/tiled-kernels/main.tex").is_file()
    gate(sample, monkeypatch)


def test_mv_uses_git_mv_inside_a_work_tree(sample: Path, monkeypatch, capsys) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    def run(*a: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(sample), *a], check=True, capture_output=True, text=True)

    run("init", "-q")
    run("add", "-A")
    run("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "start")
    assert folio(sample, "mv", "self-attention", "merging", monkeypatch=monkeypatch) == 0
    status = run("status", "--short").stdout
    assert "R  content/concepts/self-attention/index.html -> content/concepts/merging/index.html" in status \
        or "RM content/concepts/self-attention/index.html -> content/concepts/merging/index.html" in status


# promote

def test_promote_note_to_entry(sample: Path, monkeypatch, capsys) -> None:
    note = sample / "content/notes/flashattention-tiling.html"
    (sample / "content/notes/flashattention-tiling.annotations.json").write_text('{"threads": []}\n')
    edit(note, "<main>\n", '<main>\n<p class="thesis">Tiles need a rescaled softmax.</p>\n'
                          "<h2>Why</h2>\n")
    assert folio(sample, "promote", "flashattention-tiling", "entry", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "moved content/notes/flashattention-tiling.html -> content/entries/flashattention-tiling/index.html" in out
    assert "moved content/notes/flashattention-tiling.annotations.json -> " \
           "content/entries/flashattention-tiling/index.annotations.json" in out
    page = (sample / "content/entries/flashattention-tiling/index.html").read_text()
    assert '<meta name="genre" content="entry">' in page
    assert '<li><a href="/content/entries/flashattention-tiling/">' in (sample / "content/maps/attention.html").read_text()
    assert library.load_at(sample).find("flashattention-tiling")[0].is_a("entry")
    gate(sample, monkeypatch)


def test_promote_refusals(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "promote", "tiled-attention", "entry", monkeypatch=monkeypatch) == 2
    assert "only between HTML genres" in capsys.readouterr().err
    assert folio(sample, "promote", "Q-1", "note", monkeypatch=monkeypatch) == 2
    assert folio(sample, "promote", "flashattention-tiling", "question", monkeypatch=monkeypatch) == 2
    assert folio(sample, "promote", "flashattention-tiling", "note", monkeypatch=monkeypatch) == 2
    assert folio(sample, "promote", "content/guides/attention-from-scratch/index.html", "entry", monkeypatch=monkeypatch) == 2
    assert "has parts" in capsys.readouterr().err
    assert folio(sample, "promote", "flashattention-tiling", "no-such-genre", monkeypatch=monkeypatch) == 2
    gate(sample, monkeypatch)


# rm --to

def test_rm_retires_into_another(sample: Path, monkeypatch, capsys) -> None:
    edit(sample / "content/entries/attention-is-quadratic/index.html", "</main>",
         '<p>See <a href="/content/concepts/self-attention/">self-attention</a>.</p>\n</main>')
    assert folio(sample, "map", "add", "attention", "self-attention", monkeypatch=monkeypatch) == 0
    out_of(capsys)
    assert folio(sample, "rm", "self-attention", "--to", "softmax", monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "updated content/maps/attention.html: links to self-attention now go to softmax " \
           "(1 duplicate row dropped)" in out
    assert "redirected content/concepts/self-attention/index.html -> content/concepts/softmax/index.html" in out
    retired = (sample / "content/concepts/self-attention/index.html").read_text()
    assert '<meta name="status" content="retired">' in retired
    assert '<meta name="replaced_by" content="softmax">' in retired
    attention = (sample / "content/maps/attention.html").read_text()
    assert attention.count('href="/content/concepts/softmax/"') == 1
    assert "self-attention" not in attention
    gate(sample, monkeypatch)


def test_rm_names_new_orphans_and_refusals(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "rm", "exact-attention", "--to", "attention-is-quadratic", monkeypatch=monkeypatch) == 0
    assert "note: content/sources/2022-flashattention/index.html was reachable only through exact-attention" \
           in out_of(capsys)
    assert folio(sample, "rm", "exact-attention", "--to", "attention-is-quadratic", monkeypatch=monkeypatch) == 2
    assert folio(sample, "rm", "R-3", "--to", "R-4", monkeypatch=monkeypatch) == 2
    assert folio(sample, "rm", "softmax", "--to", "softmax", monkeypatch=monkeypatch) == 2
    assert folio(sample, "rm", "softmax", "--to", "exact-attention", monkeypatch=monkeypatch) == 2


# search and cards

def test_search_this_and_other_libraries(sample: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "search", "softmax", "overflow", "--json", monkeypatch=monkeypatch) == 0
    hits = json.loads(out_of(capsys))
    assert hits[0]["id"] == "softmax" and {h["library"] for h in hits} == {"."}
    other = tmp_path / "other"
    shutil.copytree(sample, other)
    edit(other / "content/concepts/self-attention/index.html", "</main>", "<p>Zebra.</p>\n</main>")
    assert folio(other, "index", monkeypatch=monkeypatch) == 0
    with (sample / "folio.yaml").open("a") as fh:
        fh.write("search:\n  - ../other\n")
    out_of(capsys)
    assert folio(sample, "search", "zebra", monkeypatch=monkeypatch) == 0
    assert out_of(capsys) == "No matches.\n"
    assert folio(sample, "search", "zebra", "--all", monkeypatch=monkeypatch) == 0
    assert "[../other] self-attention (concept, live)" in out_of(capsys)
    (other / ".folio/search.json").unlink()  # search reads the files, not the index
    assert folio(sample, "search", "zebra", "--all", monkeypatch=monkeypatch) == 0
    assert "[../other] self-attention (concept, live)" in out_of(capsys)


def test_search_finds_new_documents_and_ids(sample: Path, monkeypatch, capsys) -> None:
    """kb finding 13: a document is found before `folio index`, and a word of its id matches."""
    assert folio(sample, "new", "note", "copy-on-write-trees", "--title", "Shadow paging",
                 "--description", "Pages are copied, never overwritten.", monkeypatch=monkeypatch) == 0
    out_of(capsys)
    assert folio(sample, "search", "write", "--json", monkeypatch=monkeypatch) == 0
    assert "copy-on-write-trees" in [h["id"] for h in json.loads(out_of(capsys))]
    assert folio(sample, "search", "copy", "paging", "--json", monkeypatch=monkeypatch) == 0
    assert [h["id"] for h in json.loads(out_of(capsys))] == ["copy-on-write-trees"]
    assert folio(sample, "search", "copy", "zebra", monkeypatch=monkeypatch) == 0
    assert out_of(capsys) == "No matches.\n"  # every word must match


def test_cards_filters(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "cards", "--json", monkeypatch=monkeypatch) == 0
    every = json.loads(out_of(capsys))
    assert len(every) == 2
    assert folio(sample, "cards", "--doc", "softmax", "--json", monkeypatch=monkeypatch) == 0
    assert [c["question"] for c in json.loads(out_of(capsys))] == ["Why subtract the maximum before the softmax?"]
    assert folio(sample, "cards", "--map", "lab-work", "--json", monkeypatch=monkeypatch) == 0
    assert json.loads(out_of(capsys)) == []
    assert folio(sample, "cards", "--map", "attention", "--tag", "attention", monkeypatch=monkeypatch) == 0
    assert out_of(capsys).strip().endswith("1 card")


# pack add

def test_pack_add_moves_genres_and_workflows(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "genre", "add", "derivation", monkeypatch=monkeypatch) == 0
    assert folio(sample, "workflow", "add", "derive", monkeypatch=monkeypatch) == 0
    out_of(capsys)
    assert folio(sample, "pack", "add", "numerics", "--genres", "derivation", "--workflows", "derive",
                 monkeypatch=monkeypatch) == 0
    out = out_of(capsys)
    assert "created packs/numerics/PACK.md" in out and "switched pack `numerics` on" in out
    assert not (sample / "genres").exists() and not (sample / "workflows").exists()
    pack = sample / "packs/numerics"
    assert "pack: \"numerics\"" in (pack / "genres/derivation/GENRE.md").read_text()
    lib = library.load_at(sample)
    assert lib.registry.genres["derivation"].pack == "numerics" and lib.registry.packs["numerics"].on
    assert lib.registry.workflows["derive"].pack == "numerics"
    head = (pack / "PACK.md").read_text()
    for heading in ("# Numerics", "## What it adds", "## When to switch it on",
                    "## What switching it on changes", "## Working with other packs"):
        assert heading in head
    gate(sample, monkeypatch)


def test_pack_add_refusals(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "pack", "add", "lab", "--genres", "note", monkeypatch=monkeypatch) == 2
    assert folio(sample, "pack", "add", "mine", "--genres", "note", monkeypatch=monkeypatch) == 2
    assert "never redefines" in capsys.readouterr().err
    assert folio(sample, "pack", "add", "mine", monkeypatch=monkeypatch) == 2
    assert folio(sample, "pack", "add", "mine", "--workflows", "ingest", monkeypatch=monkeypatch) == 2
    assert not (sample / "packs").exists()
