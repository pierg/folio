"""A new library, from `folio init` to a passing gate."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from conftest import folio, problems

from folio import library


def fill(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert old in text, (old, path)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def drop(path: Path, pattern: str) -> None:
    text = path.read_text(encoding="utf-8")
    new = re.sub(pattern, "", text, flags=re.S)
    assert new != text, (pattern, path)
    path.write_text(new, encoding="utf-8")


def test_init_new_journal_index_check(tmp_path: Path, monkeypatch, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    lib = project / "docs"
    assert folio(project, "init", "docs", monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out
    assert "created folio.yaml" in out and "created content/index.html" in out
    assert "content/journal" not in out and not (lib / "content/journal").exists()
    # Skills go to the project root, where agents look for them.
    assert (project / ".agents/skills/write/SKILL.md").is_file()
    link = project / ".claude/skills"
    assert link.is_symlink() and os.readlink(link) == os.path.join("..", ".agents", "skills")
    assert problems(lib) == []

    def run(*args: str) -> None:
        assert folio(lib, *args, monkeypatch=monkeypatch) == 0, capsys.readouterr()

    run("new", "map", "attention", "--title", "Attention", "--description", "What we know about attention.")
    run("new", "concept", "softmax", "--title", "Softmax",
        "--description", "The function that turns scores into weights.", "--tags", "attention")
    run("new", "note", "flashattention-tiling", "--title", "Tiling needs a rescaled softmax",
        "--description", "Tiled attention is exact only if the softmax is rescaled per tile.")
    run("new", "guide", "attention-from-scratch", "--title", "Attention", "--description", "Compute one layer and say what it costs.")
    run("new", "guide", "attention-from-scratch", "--part", "chapter", "weights", "--title", "Weights",
        "--description", "You can turn scores into weights.")
    run("config", "set", "home.maps", "attention")

    concept = lib / "content/concepts/softmax/index.html"
    drop(concept, r"<figure>.*?</figure>\n")
    drop(concept, r"<h3>Why it matters</h3>.*?</p>\n")
    drop(concept, r"<h3>Related</h3>.*?</p>\n")
    fill(concept, {
        "{{term}}": "Softmax",
        "{{one to three sentences that define the term; no citations; every symbol named here}}":
            "The softmax divides the exponential of each score by the sum of them all.",
        "{{the usual misreading, named precisely}}": "The softmax weights every score; it does not pick the largest.",
    })
    note = lib / "content/notes/flashattention-tiling.html"
    fill(note, {
        '<meta name="tags" content="{{tags}}">\n': "",
        "{{the reason and the consequence, in one to three short paragraphs or one figure; link the}}":
            "Each tile rescales the running sum under a",
        "{{link to a concept}}": "/content/concepts/softmax/",
        "{{concept}}": "softmax",
        " {{it uses}}": "",
    })
    guide = lib / "content/guides/attention-from-scratch/index.html"
    fill(guide, {'<meta name="tags" content="{{tags}}">\n': "",
                 "{{who this guide is for, and what it assumes they know}}": "Anyone who knows a dot product."})
    chapter = lib / "content/guides/attention-from-scratch/01-weights.html"
    fill(chapter, {
        '<meta name="tags" content="{{tags}}">\n': "",
        "{{section-id}}": "weights", "{{one idea}}": "Weights",
        "{{show the idea, then name it; link a term other pages need to its}}": "Scores become weights under a",
        "{{link to a concept}}": "/content/concepts/softmax/", "{{concept}}": "softmax",
        "{{a question that tests this section}}": "What do the weights in a row sum to?", "{{the answer}}": "One.",
    })
    attention_map = lib / "content/maps/attention.html"
    drop(attention_map, r'<h2 id="take">.*?</p>\n')
    drop(attention_map, r'<h2 id="open">.*?</ul>\n')
    fill(attention_map, {
        '<meta name="tags" content="{{tags}}">\n': "",
        '<h2 id="{{group-id}}">{{group name}}</h2>': '<h2 id="start">Start</h2>',
        '<li><a href="{{link to a document}}">{{its title}}</a> <span class="why">{{optional: the reason to follow it from this map; delete the span to show its description}}</span></li>':
            '<li><a href="/content/concepts/softmax/">Softmax</a></li>\n'
            '<li><a href="/content/notes/flashattention-tiling.html">Tiling</a></li>\n'
            '<li><a href="/content/guides/attention-from-scratch/">Attention</a></li>',
    })
    run("journal", "add", "--title", "Wrote the attention pages", "--description", "First pages on attention.",
        "--body", "Added the softmax concept and its note.", "--kind", "decision",
        "--about", "softmax,flashattention-tiling", "--tags", "attention")
    assert folio(lib, "journal", "add", "--title", "x", "--description", "x", "--body", "x",
                 "--kind", "party", monkeypatch=monkeypatch) == 2
    capsys.readouterr()

    assert folio(lib, "check", monkeypatch=monkeypatch) == 1
    assert "index-current" in capsys.readouterr().out
    run("index")
    capsys.readouterr()
    code = folio(lib, "check", monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert code == 0, out
    assert out.strip().endswith("0 errors, 0 warnings")

    run("journal", "--kind", "decision", "--json")
    entries = json.loads(capsys.readouterr().out)
    assert [e["title"] for e in entries] == ["Wrote the attention pages"]
    run("cite", "softmax", "--json")
    cited = json.loads(capsys.readouterr().out)
    assert cited[0]["markup"]["html"] == '<a class="defn-link" href="/content/concepts/softmax/">Softmax</a>'
    assert len(library.load_at(lib).documents) == 6


def test_init_refuses_an_existing_library(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "init", ".", monkeypatch=monkeypatch) == 2
    assert "already" in capsys.readouterr().err


def test_new_record_takes_next_id(sample: Path, monkeypatch, capsys) -> None:
    assert folio(sample, "new", "result", "--protocol", "pi-error-scaling", monkeypatch=monkeypatch) == 0
    assert "content/results/R-5.md" in capsys.readouterr().out
    text = (sample / "content/results/R-5.md").read_text()
    assert "id: R-5" in text and 'protocol: "pi-error-scaling"' in text and "date: 2026-10-03" in text
    assert folio(sample, "new", "result", "R-9", monkeypatch=monkeypatch) == 2
    assert folio(sample, "new", "claim", "--nosuch", "x", monkeypatch=monkeypatch) == 2


def test_new_paper_writes_both_parts(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "paper", "second", "--title", "Second", monkeypatch=monkeypatch) == 0
    landing = (sample / "content/papers/second/index.html").read_text()
    assert '<meta name="title" content="Second">' in landing and 'class="pdf"' not in landing
    assert (sample / "content/papers/second/main.tex").is_file()
    assert not (sample / "content/papers/second/versions").exists()
    # A version is a snapshot `folio paper freeze` writes, never a skeleton.
    assert folio(sample, "new", "paper", "second", "--part", "version", "v1", monkeypatch=monkeypatch) == 2


def test_new_chapter_numbers(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "guide", "attention-from-scratch", "--part", "chapter", "merging", monkeypatch=monkeypatch) == 0
    assert (sample / "content/guides/attention-from-scratch/03-merging.html").is_file()
    assert folio(sample, "new", "guide", "nope", "--part", "chapter", "x", monkeypatch=monkeypatch) == 2
