"""One failing case per implemented check, each asserting the check's name."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from conftest import edit, found, names

from folio.checks.registry import BY_NAME, CHECKS

SPEC = Path(__file__).resolve().parents[1] / "docs" / "spec" / "checks.md"


def test_registry_matches_the_spec() -> None:
    text = SPEC.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([a-z_-]+)` \|", text, re.M)
    assert sorted(rows) == sorted(c.name for c in CHECKS)
    for line in text.splitlines():
        match = re.match(r"^\| `([a-z_-]+)` \|.*\| (error|warning)", line)
        if match:
            assert BY_NAME[match.group(1)].default == match.group(2), line


def test_broken_link(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "/content/concepts/softmax/", "/content/concepts/nope/")
    assert "broken-link" in names(sample)


def test_broken_link_backticked_record_id(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "`R-4`", "`R-9`")
    msgs = [p.message for p in found(sample, "broken-link")]
    assert any("R-9" in m for m in msgs)


def test_broken_link_fcite(sample: Path) -> None:
    edit(sample / "content/papers/tiled-attention/main.tex", r"\fcite{softmax}", r"\fcite{no-such}")
    assert any("no-such" in p.message for p in found(sample, "broken-link"))


def test_md_link_to_html_resolves_to_record(sample: Path) -> None:
    edit(sample / "content/reports/pi-error-scaling-report/index.html", "/content/results/R-4.md", "/content/results/R-4.html")
    assert found(sample, "broken-link") == []


def test_location(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", 'content="note"', 'content="entry"')
    assert "location" in names(sample)


def test_location_unknown_genre(sample: Path) -> None:
    (sample / "content/stray.html").write_text(
        '<html><head><meta name="genre" content="widget"></head><body></body></html>')
    assert any("widget" in p.message for p in found(sample, "location"))


def test_fields_missing_and_typed(sample: Path) -> None:
    edit(sample / "content/questions/Q-1.md", "rank: 1", "rank: high")
    edit(sample / "content/notes/flashattention-tiling.html", '<meta name="description"', '<meta name="x"')
    msgs = [p.message for p in found(sample, "fields")]
    assert any("rank" in m for m in msgs)
    assert any("description" in m for m in msgs)


def test_fields_id_limits_and_path(sample: Path) -> None:
    edit(sample / "content/protocols/pi-error-scaling.md", "status: locked", "status: draft")
    edit(sample / "content/results/R-4.md", "evidence: assets/data/pi-errors.csv", "evidence: assets/data/gone.csv")
    msgs = [p.message for p in found(sample, "fields")]
    assert any("must be locked" in m for m in msgs)
    assert any("gone.csv" in m for m in msgs)


def test_fields_permanent_writes_no_status(sample: Path) -> None:
    edit(sample / "content/results/R-4.md", "genre: result", "genre: result\nstatus: live")
    assert any("permanent" in p.message for p in found(sample, "fields"))


def test_status(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "status: live", "status: shaky")
    assert "status" in names(sample)


def test_placeholder(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "the exact result.", "{{say more}}")
    assert "placeholder" in names(sample)


def test_orphan_required(sample: Path) -> None:
    edit(sample / "content/maps/attention.html",
         '<li><a href="/content/entries/attention-is-quadratic/">Why attention is quadratic</a></li>', "")
    assert [p.path for p in found(sample, "orphan")] == ["content/entries/attention-is-quadratic/index.html"]


def test_orphan_optional(sample: Path) -> None:
    edit(sample / "content/maps/attention.html",
         '<li><a href="/content/notes/flashattention-tiling.html">FlashAttention tiling</a></li>', "")
    assert [p.path for p in found(sample, "orphan")] == ["content/notes/flashattention-tiling.html"]


def test_orphan_journal_links_do_not_count(sample: Path) -> None:
    edit(sample / "content/maps/lab-work.html",
         '<li><a href="/content/reports/pi-error-scaling-report/">The error of the pi estimate fell as 1/sqrt(n)</a></li>', "")
    assert [p.path for p in found(sample, "orphan")] == ["content/reports/pi-error-scaling-report/index.html"]


def test_orphan_part_never_on_a_map(sample: Path) -> None:
    edit(sample / "content/maps/attention.html", "</ul>",
         '<li><a href="/content/guides/attention-from-scratch/01-scores.html">Comparing</a></li></ul>')
    assert [p.path for p in found(sample, "orphan")] == ["content/guides/attention-from-scratch/01-scores.html"]


def test_home_maps(sample: Path) -> None:
    edit(sample / "folio.yaml", "maps: [attention, lab-work]", "maps: [attention, lab-work, missing]")
    assert [p.path for p in found(sample, "home-maps")] == ["folio.yaml"]


def test_home_maps_draft(sample: Path) -> None:
    edit(sample / "content/maps/lab-work.html", '<meta name="description"', '<meta name="status" content="draft">\n<meta name="description"')
    assert any("draft" in p.message for p in found(sample, "home-maps"))


def test_unique_id_record_form(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "id: C-1", "id: C-7")
    assert "unique-id" in names(sample)


def test_unique_id_duplicate_record(sample: Path) -> None:
    text = (sample / "content/results/R-4.md").read_text()
    (sample / "content/results/R-5.md").write_text(text)
    msgs = [p.message for p in found(sample, "unique-id")]
    assert any("also the id of content/results/R-4.md" in m for m in msgs)


def test_unique_id_across_genres(sample: Path) -> None:
    """Two documents of different genres may not share an id (lab finding 1, kb finding 2)."""
    shutil.copytree(sample / "content/concepts/self-attention", sample / "content/entries/self-attention")
    edit(sample / "content/entries/self-attention/index.html", 'content="concept"', 'content="entry"')
    msgs = [(p.path, p.message) for p in found(sample, "unique-id")]
    assert msgs and all("self-attention" in m for _, m in msgs)


def test_index_current(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "the exact result", "the first pass's order")
    assert [p.check for p in found(sample, "index-current")] == ["index-current"]
    (sample / ".folio/nav.json").unlink()
    assert any("missing" in p.message for p in found(sample, "index-current"))


def test_require(sample: Path) -> None:
    edit(sample / "content/concepts/softmax/index.html", 'class="defn"', 'class="lede"')
    assert any("defn" in p.message for p in found(sample, "require"))


def test_cards_leave_form_to_the_page(sample: Path) -> None:
    """A page genre prescribes no markup: an entry with no thesis or sections, and a concept with h2, pass."""
    edit(sample / "content/entries/attention-is-quadratic/index.html", 'class="thesis"', 'class="lede"')
    edit(sample / "content/concepts/softmax/index.html", "<h3>The trap</h3>", "<h2>The trap</h2>")
    edit(sample / "content/guides/attention-from-scratch/02-softmax.html", '<details class="check">', '<details class="note">')
    assert not {"require", "forbid", "max_words"} & names(sample)


def test_require_markdown_section(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "## Must not be said", "## Other")
    assert any("must-not" in p.message for p in found(sample, "require"))


def test_require_no_h1(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "<main>", "<main>\n<h1>Title</h1>")
    assert any("h1" in p.message for p in found(sample, "require"))


def test_require_latex(sample: Path) -> None:
    edit(sample / "content/papers/tiled-attention/main.tex", "\\begin{abstract}", "\\begin{summary}")
    assert any("abstract" in p.message for p in found(sample, "require"))


def test_forbid(sample: Path) -> None:
    (sample / "genres/concept").mkdir(parents=True)
    (sample / "genres/concept/GENRE.md").write_text("---\nname: concept\nchecks:\n  forbid: [h2]\n---\n")
    edit(sample / "content/concepts/softmax/index.html", "<h3>The trap</h3>", "<h2>The trap</h2>")
    assert "forbid" in names(sample)


def test_max_words(sample: Path) -> None:
    edit(sample / "content/results/R-4.md", "It replaces", "word " * 200 + "It replaces")
    assert "max_words" in names(sample)


def test_cites_none_in_part(sample: Path) -> None:
    edit(sample / "content/concepts/softmax/index.html", "sum of the exponentials.",
         'sum of the exponentials, as <a href="/content/notes/flashattention-tiling.html">shown</a>.')
    assert any("defn" in p.message for p in found(sample, "cites"))


def test_cites_none_allows_defn_links(sample: Path) -> None:
    edit(sample / "content/concepts/softmax/index.html", "sum of the exponentials.",
         'sum of the <a class="defn-link" href="/content/concepts/self-attention/">exponentials</a>.')
    assert found(sample, "cites") == []


def test_cites_results(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "`R-4`", "the slope")
    assert "cites" in names(sample)


def test_cites_any(sample: Path) -> None:
    edit(sample / "content/papers/tiled-attention/main.tex", r"\fcite{softmax}", "the usual definition")
    assert "cites" in names(sample)


def test_defined_once(sample: Path) -> None:
    edit(sample / "content/concepts/self-attention/index.html", '<span class="defn-name">Self-attention</span>',
         '<span class="defn-name">Softmax</span>')
    assert len(found(sample, "defined_once")) == 2


def test_min_links(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html",
         '<a class="defn-link" href="/content/concepts/softmax/">softmax</a>', "softmax")
    assert "min_links" in names(sample)


def test_forward_links(sample: Path) -> None:
    edit(sample / "content/guides/attention-from-scratch/01-scores.html", "<a data-fwd ", "<a ")
    assert "forward_links" not in names(sample)  # judged by default
    (sample / "genres/guide").mkdir(parents=True)
    (sample / "genres/guide/GENRE.md").write_text(
        "---\nname: guide\nparts:\n  chapter:\n    checks:\n      forward_links: marked\n---\n")
    assert "forward_links" in names(sample)


def test_layout(sample: Path) -> None:
    edit(sample / "content/notes/flashattention-tiling.html", "</head>", '<meta name="layout" content="wide">\n</head>')
    assert any("layout" in p.message for p in found(sample, "fields"))


def test_stale_after_days(sample: Path) -> None:
    edit(sample / "content/projects/attention-kernel/index.html", "2026-09-20", "2026-01-01")
    stale = found(sample, "stale_after_days")
    assert [p.severity for p in stale] == ["warning"]


def test_kinds(sample: Path) -> None:
    edit(sample / "content/journal/2026/2026-10-02-lab-meeting.md", "kind: meeting", "kind: party")
    assert "kinds" in names(sample)


def test_kinds_accepts_pack_and_charter_kinds(sample: Path) -> None:
    assert found(sample, "kinds") == []
    edit(sample / "folio.yaml", "packs: [lab, knowledge-base]", "packs: [knowledge-base]")
    assert any("run" in p.message for p in found(sample, "kinds"))


def test_bib(sample: Path) -> None:
    edit(sample / "content/papers/tiled-attention/main.tex", r"\cite{vaswani2017}", r"\cite{nobody2000}")
    assert "bib" in names(sample)


def test_bib_own_file(sample: Path) -> None:
    (sample / "content/papers/tiled-attention/own.bib").write_text("")
    assert any("own.bib" in p.message for p in found(sample, "bib"))


def test_figures(sample: Path) -> None:
    edit(sample / "content/papers/tiled-attention/main.tex", "{attention-tiling}", "{elsewhere}")
    assert "figures" in names(sample)


def test_original_beside(sample: Path) -> None:
    (sample / "content/sources/2017-attention-is-all-you-need/original.pdf").unlink()
    assert "original_beside" in names(sample)


def test_min_sources(sample: Path) -> None:
    edit(sample / "content/surveys/exact-attention.html", "/content/sources/2022-flashattention/", "https://example.org/")
    assert "min_sources" in names(sample)


def test_answer_cites(sample: Path) -> None:
    edit(sample / "content/questions/Q-1.md", "Yes, see `R-4` and `C-1`.", "Yes.")
    assert "answer_cites" in names(sample)


def test_prediction_ids(sample: Path) -> None:
    edit(sample / "content/protocols/pi-error-scaling.md", "- P1: the slope lies between -0.55 and -0.45. Confidence: 85%.",
         "- P2: the slope is near -0.5.")
    msgs = [p.message for p in found(sample, "prediction_ids")]
    assert len(msgs) == 2


def test_rule_ids(sample: Path) -> None:
    edit(sample / "content/protocols/pi-error-scaling.md", "- D2 (kill):", "- D2:")
    assert any("kill" in p.message for p in found(sample, "rule_ids"))


def test_pinned_config(sample: Path) -> None:
    edit(sample / "content/protocols/pi-error-scaling.md", "repeats: 100", "seed: [7")
    assert "pinned_config" in names(sample)


@pytest.mark.parametrize("severity", ["warning", "off"])
def test_charter_sets_severity(sample: Path, severity: str) -> None:
    edit(sample / "folio.yaml", "checks:\n", f"checks:\n  min_links: {severity}\n")
    edit(sample / "content/notes/flashattention-tiling.html",
         '<a class="defn-link" href="/content/concepts/softmax/">softmax</a>', "softmax")
    got = [p.severity for p in found(sample, "min_links")]
    assert got == ([] if severity == "off" else ["warning"])


def test_charter_genre_setting_overrides_card(sample: Path) -> None:
    edit(sample / "folio.yaml", "checks:\n", "genres:\n  concept: { max_words: 5 }\nchecks:\n")
    assert {p.path for p in found(sample, "max_words")} == {
        "content/concepts/softmax/index.html", "content/concepts/self-attention/index.html"}
