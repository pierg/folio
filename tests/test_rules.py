"""The packs' rule checks: uncited-number, cites-superseded, unverified-identifier, source-pointer."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import edit, found

from folio.checks.rules import measurements, pointers

NOTE = "content/notes/flashattention-tiling.html"
REPORT = "content/reports/pi-error-scaling-report/index.html"
SOURCE = "content/sources/2017-attention-is-all-you-need/index.html"
TEX = "content/papers/tiled-attention/main.tex"


@pytest.mark.parametrize("text", ["took 45 ms", "won 12% of runs", "a 3× speed-up", "7 of 10 trials",
                                  "scored 0.93", "ratio 3/4", "2.5x faster", "used 2 GB"])
def test_measurement_shapes(text: str) -> None:
    assert measurements(text)


@pytest.mark.parametrize("text", ["sequences of 1000 tokens", "in 2019", "on 2026-10-03", "see R-12",
                                  "version 0.1.0", "section 3.2", "§4.1", "v2.1", "two of them",
                                  "https://example.org/a/1.5"])
def test_not_measurements(text: str) -> None:
    assert measurements(text) == []


def test_uncited_number_in_a_sentence(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>", "the exact result. It took 45 ms.</p>")
    msgs = found(sample, "uncited-number")
    assert [(p.path, p.severity) for p in msgs] == [(NOTE, "error")]  # the charter makes it an error
    assert "45 ms" in msgs[0].message


def test_cited_in_the_same_sentence(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. It took 41 ms (<a href="/content/results/R-4.md">R-4</a>).</p>')
    assert found(sample, "uncited-number") == []


def test_cite_in_another_sentence_does_not_count(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. It took 41 ms. See <a href="/content/results/R-4.md">R-4</a>.</p>')
    assert len(found(sample, "uncited-number")) == 1


def test_list_item_and_table_row_are_units(sample: Path) -> None:
    edit(sample / REPORT, "<li>Anything about another estimator.</li>",
         '<li>Tiled took 41 ms. That is the re-run (<a href="/content/results/R-4.md">R-4</a>).</li>'
         '</ul><table><tr><td>tiled</td><td>41 ms</td><td><a href="/content/results/R-4.md">R-4</a></td></tr>'
         '<tr><td>naive</td><td>63 ms</td></tr></table><ul>')
    msgs = found(sample, "uncited-number")
    assert len(msgs) == 1 and "63 ms" in msgs[0].message


def test_not_measured_and_code_are_skipped(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. A <span class="not-measured">2/3</span> majority. <code>x = 0.5</code></p>')
    assert found(sample, "uncited-number") == []


def test_a_source_counts_with_the_knowledge_base_pack(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. One study saw 12% (<a href="/content/sources/2017-attention-is-all-you-need/">study</a>).</p>')
    assert found(sample, "uncited-number") == []
    edit(sample / "folio.yaml", "packs: [lab, knowledge-base]", "packs: [lab]")
    assert len(found(sample, "uncited-number")) == 1


def test_claim_body_and_records(sample: Path) -> None:
    edit(sample / "content/claims/C-1.md", "square root of the sample size.", "square root of the sample size, within 35%.")
    assert [p.path for p in found(sample, "uncited-number")] == ["content/claims/C-1.md"]
    edit(sample / "content/claims/C-1.md", "within 35%.", "within 35% (`R-4`).")
    assert found(sample, "uncited-number") == []
    edit(sample / "content/journal/2026/2026-10-01-set-up-the-library.md", "packs.", "packs in 45 ms.")
    assert found(sample, "uncited-number") == []  # a record is not flagged


def test_latex(sample: Path) -> None:
    edit(sample / TEX, "is rescaled.", "is rescaled, and 41 ms faster.")
    assert [p.path for p in found(sample, "uncited-number")] == [TEX]
    edit(sample / TEX, "41 ms faster.", "41 ms faster \\fcite{R-4}.")
    assert found(sample, "uncited-number") == []
    edit(sample / TEX, "[width=\\linewidth]", "[width=0.5\\linewidth]")
    assert found(sample, "uncited-number") == []


def test_rule_off_with_its_pack(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>", "the exact result. It took 45 ms.</p>")
    edit(sample / "folio.yaml", "packs: [lab, knowledge-base]", "packs: [knowledge-base]")
    assert found(sample, "uncited-number") == []


def test_cites_superseded(sample: Path) -> None:
    edit(sample / REPORT, "R-4.md\">R-4", "R-3.md\">R-3")
    assert found(sample, "cites-superseded") == []  # a live report is frozen: not flagged
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. See <a href="/content/results/R-3.md">R-3</a>.</p>')
    msgs = found(sample, "cites-superseded")
    assert [(p.path, p.severity) for p in msgs] == [(NOTE, "warning")]
    assert "R-4" in msgs[0].message and "superseded" in msgs[0].message
    edit(sample / NOTE, '<meta name="genre" content="note">',
         '<meta name="genre" content="note">\n<meta name="status" content="historical">')
    assert found(sample, "cites-superseded") == []


def test_cites_live_result_is_fine(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. See <a href="/content/results/R-4.md">R-4</a>.</p>')
    assert found(sample, "cites-superseded") == []


def test_verified_identifier_passes(sample: Path) -> None:
    assert found(sample, "unverified-identifier") == []


@pytest.mark.parametrize("old,new,words", [
    (' data-verified="2026-10-01"', "", "data-verified"),
    ('data-verified="2026-10-01"', 'data-verified="2027-01-01"', "future"),
    ('data-kind="arxiv"', 'data-kind="pmid"', "data-kind"),
    ('href="https://arxiv.org/abs/1706.03762"', 'href="https://arxiv.org/abs/1706.03763"', "different"),
    (">1706.03762<", ">arXiv:1706.03762<", "shaped"),
    ('class="identifier" ', "", "not an"),
])
def test_unverified_identifier(sample: Path, old: str, new: str, words: str) -> None:
    edit(sample / SOURCE, old, new)
    msgs = found(sample, "unverified-identifier")
    assert len(msgs) == 1 and words in msgs[0].message and msgs[0].severity == "error"


@pytest.mark.parametrize("text", ["(Section 5.3)", "in Table 7", "§4", "Appendix C", "Fig. 2", "footnote 6",
                                  "Figures 3 and 4", "Eq. 12", "see Listing 2", "App. B"])
def test_pointer_shapes(text: str) -> None:
    assert pointers(text)


@pytest.mark.parametrize("text", ["Theorem 2", "Lemma 3", "Definition 1", "a table of 7 rows",
                                  "an appendix a reader skips", "the figure shows", "Section headings"])
def test_not_pointers(text: str) -> None:
    assert pointers(text) == []


def test_source_pointer_flags_prose(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         "the exact result (Section 5.3, Table 7). See Appendix C.</p>")
    msgs = found(sample, "source-pointer")
    assert [(p.path, p.severity) for p in msgs] == [(NOTE, "warning")]
    assert msgs[0].message.startswith("3 pointer(s)") and "Section 5.3" in msgs[0].message


def test_source_pointer_skips_code_and_attributes(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         'the exact result. Run <code>show Table 7</code> and read'
         ' <a href="/content/notes/flashattention-tiling.html#Section 5" title="Figure 3">the note</a>.</p>')
    assert found(sample, "source-pointer") == []


def test_source_pointer_skips_the_journal(sample: Path) -> None:
    edit(sample / "content/journal/2026/2026-10-02-lab-meeting.md", "next.", "next, as Section 5.3 says.")
    assert found(sample, "source-pointer") == []


def test_source_pointer_severity_from_the_charter(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>", "the exact result (Table 7).</p>")
    edit(sample / "folio.yaml", "  uncited-number: error", "  uncited-number: error\n  source-pointer: error")
    assert [p.severity for p in found(sample, "source-pointer")] == ["error"]
    edit(sample / "folio.yaml", "source-pointer: error", "source-pointer: off")
    assert found(sample, "source-pointer") == []


def test_source_pointer_skips_the_pages_own_labels(sample: Path) -> None:
    edit(sample / NOTE, "the exact result.</p>",
         "the exact result, as (§4) and Figure 3 show; chapter 03 §2 says more.</p>"
         "<h2>§4 · Tiling</h2><figure><figcaption>Figure 3. One tile at a time.</figcaption></figure>")
    assert found(sample, "source-pointer") == []
    edit(sample / NOTE, "chapter 03 §2 says more.", "chapter 03 §2 says more, and so does Figure 5.")
    msgs = found(sample, "source-pointer")
    assert len(msgs) == 1 and msgs[0].message.startswith("1 pointer(s)") and "Figure 5" in msgs[0].message
