"""Annotation threads in sidecars, the `folio annotations` commands, and the stale-quote check."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import edit, folio, found

from folio import annotations, library

NOTE = "content/notes/flashattention-tiling.html"
SIDECAR = "content/notes/flashattention-tiling.annotations.json"


def test_sidecar_path() -> None:
    assert annotations.sidecar_path(NOTE) == SIDECAR
    assert annotations.sidecar_path("content/concepts/x/index.html") == "content/concepts/x/index.annotations.json"


def test_add_reply_show_list(sample: Path, monkeypatch, capsys) -> None:
    def run(*args: str) -> str:
        code = folio(sample, "annotations", *args, monkeypatch=monkeypatch)
        out = capsys.readouterr()
        assert code == 0, out.err
        return out.out

    run("add", "flashattention-tiling", "--kind", "question", "--quote", "updates a running   maximum",
        "--body", "Which maximum is kept?", "--author", "reader")
    run("add", NOTE, "--kind", "flag", "--label", "example", "--quote", "rescaled this way",
        "--body", "My own example.", "--author", "agent")
    data = json.loads((sample / SIDECAR).read_text())
    assert [(t["id"], t["state"]) for t in data["threads"]] == [("a1", "open"), ("a2", "noted")]
    assert data["threads"][0]["quote"] == "updates a running maximum"

    rows = json.loads(run("list", "--json"))
    assert [(r["doc"], r["id"], r["state"]) for r in rows] == [("flashattention-tiling", "a1", "open")]
    assert len(json.loads(run("list", "--state", "noted", "--json"))) == 1

    run("reply", "flashattention-tiling", "a1", "--body", "The largest score so far.", "--author", "agent",
        "--state", "addressed")
    assert json.loads(run("list", "--json")) == []
    shown = run("show", "flashattention-tiling")
    assert "a1" in shown and "-> addressed" in shown and "Which maximum is kept?" in shown

    out = run("resolve", "--label", "example", "--state", "addressed", "--body", "Kept.")
    assert "a2" in out
    data = json.loads((sample / SIDECAR).read_text())
    assert [t["state"] for t in data["threads"]] == ["addressed", "addressed"]
    assert [len(t["messages"]) for t in data["threads"]] == [2, 2]  # nothing deleted


def test_add_refuses_a_quote_not_on_the_page(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "annotations", "add", "flashattention-tiling", "--kind", "question", "--quote", "nowhere",
                 "--body", "?", "--author", "r", monkeypatch=monkeypatch) == 2
    assert "not on" in capsys.readouterr().err
    assert folio(sample, "annotations", "reply", "flashattention-tiling", "a9", "--body", "x", "--author", "r",
                 monkeypatch=monkeypatch) == 2
    assert folio(sample, "annotations", "add", "flashattention-tiling", "--kind", "praise", "--quote", "tile",
                 "--body", "x", "--author", "r", monkeypatch=monkeypatch) == 2


def test_stale_quote(sample: Path) -> None:
    lib = library.load_at(sample)
    annotations.add(lib, NOTE, "question", "rescaled this way gives the exact result", "Why?", "reader")
    annotations.add(lib, NOTE, "flag", "updates a running maximum", "Added.", "agent")
    assert found(sample, "stale-quote") == []
    edit(sample / NOTE, "rescaled this way gives the exact result", "gives the same result")
    edit(sample / NOTE, "updates a running maximum", "updates a running total")
    msgs = found(sample, "stale-quote")
    assert [(p.path, p.severity) for p in msgs] == [(NOTE, "error")]  # the noted flag is not checked
    annotations.reply(library.load_at(sample), NOTE, "a1", "Rewritten.", "agent", "addressed")
    assert found(sample, "stale-quote") == []


def test_stale_quote_on_a_missing_file(sample: Path) -> None:
    lib = library.load_at(sample)
    annotations.add(lib, NOTE, "question", "rescaled this way", "Why?", "reader")
    (sample / NOTE).rename(sample / "content/notes/elsewhere.txt")
    assert [p.path for p in found(sample, "stale-quote")] == [SIDECAR]


def test_placeholder_after_a_latex_command(sample: Path) -> None:
    tex = sample / "content/papers/tiled-attention/main.tex"
    edit(tex, "\\graphicspath{%\n{../../../assets/figures/}%\n}", "\\graphicspath{{../../../assets/figures/}}")
    assert found(sample, "placeholder") == []
    edit(tex, "\\maketitle", "\\maketitle {{an abstract}}")
    assert len(found(sample, "placeholder")) == 1
