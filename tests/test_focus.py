"""Topics: what falls under each home map, as `folio index` writes it into the catalog (model.md §5)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import edit, folio

from folio import indexer, library


def topics(lib_dir: Path) -> dict[str, list[str]]:
    """Each document's topics, by id."""
    lib = library.load_at(lib_dir)
    under = indexer.topics(lib)
    return {doc.id: under[doc.key] for doc in lib.documents}


def test_rows_concepts_and_journal(sample: Path) -> None:
    t = topics(sample)
    # Listed on a home map.
    assert t["softmax"] == ["attention"]
    assert t["Q-1"] == ["lab-work"]
    assert t["attention"] == ["attention"] and t["lab-work"] == ["lab-work"]
    # A concept no map lists, linked from a document under the map.
    assert t["self-attention"] == ["attention"]
    # Reached only through a field of another record: under no topic.
    assert t["R-3"] == [] and t["pi-error-scaling"] == []
    # The home page is under every topic, in the charter's order, and so is an entry about it.
    assert t["home"] == ["attention", "lab-work"]
    assert t["2026-10-01-set-up-the-library"] == ["attention", "lab-work"]
    # An entry about documents under no topic is under none.
    assert t["2026-10-02-recorded-r-4"] == []


def test_maps_listing_maps(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "map", "results", "--title", "Results", "--description", "The measured results.",
                 monkeypatch=monkeypatch) == 0
    assert folio(sample, "map", "add", "results", "R-4", monkeypatch=monkeypatch) == 0
    # A map no home map lists: its rows are under no topic.
    assert topics(sample)["R-4"] == []
    assert folio(sample, "map", "add", "lab-work", "results", monkeypatch=monkeypatch) == 0
    t = topics(sample)
    assert t["results"] == ["lab-work"] and t["R-4"] == ["lab-work"]
    # The journal entry about R-4 follows it.
    assert t["2026-10-02-recorded-r-4"] == ["lab-work"]
    # A document under two home maps has both, in the charter's order.
    assert folio(sample, "map", "add", "attention", "results", monkeypatch=monkeypatch) == 0
    assert topics(sample)["R-4"] == ["attention", "lab-work"]


def test_concepts_follow_links_only_from_documents_in_the_topic(sample: Path, monkeypatch) -> None:
    assert folio(sample, "new", "concept", "pivot", "--title", "Pivot", "--description", "The element a partition splits around.",
                 monkeypatch=monkeypatch) == 0
    assert topics(sample)["pivot"] == []
    # Linked from a concept that is itself only reached through a link: still under the topic.
    edit(sample / "content/concepts/self-attention/index.html", "</main>",
         '<p>See <a class="defn-link" href="/content/concepts/pivot/">pivot</a>.</p>\n</main>')
    assert topics(sample)["pivot"] == ["attention"]
    # Once its map leaves the charter's home maps, nothing is under that topic.
    edit(sample / "folio.yaml", "maps: [attention, lab-work]", "maps: [lab-work]")
    t = topics(sample)
    assert t["pivot"] == [] and t["home"] == ["lab-work"]


def test_catalog_carries_topics(sample: Path, monkeypatch) -> None:
    assert folio(sample, "index", monkeypatch=monkeypatch) == 0
    docs = {d["id"]: d for d in json.loads((sample / ".folio/catalog.json").read_text())["documents"]}
    assert docs["self-attention"]["topics"] == ["attention"]
    assert docs["home"]["topics"] == ["attention", "lab-work"]
    assert all("topics" in d for d in docs.values())
