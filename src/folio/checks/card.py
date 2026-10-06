"""Card checks: what a genre's card asks of each of its documents."""

from __future__ import annotations

import re
from typing import Any, Callable

import yaml

from .. import regions
from ..documents import DocFile, Document
from ..html import NOT_PROSE, Element, elements_in
from ..library import Library
from ..links import Link, links_in
from ..util import parse_date, today

CardCheck = Callable[[Library, Document, DocFile, Any], list[str]]
_WORD_RE = re.compile(r"[^\W_]+(?:['’.-][^\W_]+)*")
_CITE_RE = re.compile(r"\\(?:no)?cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
_BIBLIO_RE = re.compile(r"\\bibliography\{([^}]*)\}")
_GRAPHICS_RE = re.compile(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^}]*)\}")
_BIB_KEY_RE = re.compile(r"@\s*[A-Za-z]+\s*[{(]\s*([^,\s]+)\s*,")


def _genre(doc: Document):
    assert doc.genre is not None
    return doc.genre


def word_count(df: DocFile) -> int:
    if df.body is None:
        return 0
    return len(_WORD_RE.findall(df.body.text(NOT_PROSE)))


def _cited(links: list[Link], doc: Document, count_defn: bool = True) -> list[Document]:
    out: list[Document] = []
    for link in links:
        if link.defn and not count_defn:
            continue
        for target in link.docs:
            if target is not doc and target not in out:
                out.append(target)
    return out


def check_require(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    out = [f"missing required part `{name}`" for name in setting
           if not regions.find(df, _genre(doc), name)]
    if df.body is not None and df.body.first("h1") is not None:
        out.append("has an <h1> of its own; the shell draws the title from metadata")
    return out


def check_forbid(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    return [f"has `{name}`, which this genre forbids" for name in setting
            if regions.find(df, _genre(doc), name)]


def check_max_words(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    count = word_count(df)
    if count > int(setting):
        return [f"{count} words; the limit is {setting}"]
    return []


def _cites_level(level: str, links: list[Link], doc: Document, where: str) -> list[str]:
    if level == "none":
        cited = _cited(links, doc, count_defn=False)
        if cited:
            return [f"{where} cites {', '.join(d.id for d in cited)}; it must cite nothing"]
    elif level == "any":
        if not _cited(links, doc):
            return [f"{where} cites no document; it must cite at least one"]
    elif level == "results":
        if not any(d.is_a("result") for d in _cited(links, doc)):
            return [f"{where} cites no result; it must cite at least one"]
    else:
        return [f"unknown cites setting `{level}`; use none, any or results"]
    return []


def check_cites(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if isinstance(setting, str):
        return _cites_level(setting, lib.links.get(df.path, []), doc, "the document")
    out = []
    for part, level in setting.items():
        for nodes in regions.find(df, _genre(doc), part):
            out.extend(_cites_level(level, links_in(lib, df, nodes), doc, f"part `{part}`"))
    return out


def _defn_name(el: Element) -> str:
    for inner in el.iter():
        if "defn-name" in inner.classes:
            return " ".join(inner.text().split()).lower()
    return ""


def _definitions(lib: Library) -> dict[str, list[DocFile]]:
    cache = lib.cache.get("defn")
    if cache is None:
        cache = {}
        for df in lib.files:
            if df.body is None:
                continue
            for el in df.body.iter():
                if "defn" in el.classes:
                    name = _defn_name(el)
                    if name and "{{" not in name:
                        cache.setdefault(name, []).append(df)
        lib.cache["defn"] = cache
    return cache


def check_defined_once(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if not setting or df.body is None:
        return []
    out = []
    for el in df.body.iter():
        if "defn" not in el.classes:
            continue
        name = _defn_name(el)
        others = sorted({o.path for o in _definitions(lib).get(name, []) if o.doc is not doc})
        if others:
            out.append(f"`{name}` is also defined in {', '.join(others)}")
    return out


def check_min_links(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    count = len(_cited(lib.links.get(df.path, []), doc))
    if count < int(setting):
        return [f"links to {count} other documents; it needs at least {setting}"]
    return []


def check_forward_links(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if setting != "marked" or "nn" not in df.captures:
        return []
    here = int(df.captures["nn"])
    out = []
    for link in lib.links.get(df.path, []):
        if link.kind != "href" or link.target is None or link.element is None:
            continue
        target = lib.by_path.get(link.target)
        if target is None or target.doc is not doc or target.part != df.part or "nn" not in target.captures:
            continue
        if int(target.captures["nn"]) > here and not link.element.has("data-fwd"):
            out.append(f"links forward to {target.path} without data-fwd")
    return out


def check_stale_after_days(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df is not doc.meta_file or doc.status != "live":
        return []
    reviewed = parse_date(df.meta.get("reviewed"))
    if reviewed is None:
        return []
    age = (today() - reviewed).days
    if age > int(setting):
        return [f"reviewed {reviewed.isoformat()}, {age} days ago; review it within {setting} days"]
    return []


def check_kinds(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df is not doc.meta_file:
        return []
    kind = df.meta.get("kind")
    if kind is None or "{{" in str(kind):
        return []
    accepted = list(setting or [])
    for pack in lib.registry.packs.values():
        if pack.on:
            accepted.extend(pack.journal_kinds)
    accepted.extend(lib.charter.journal_kinds)
    if str(kind) not in accepted:
        return [f"kind `{kind}` is not one this library accepts: {', '.join(dict.fromkeys(accepted))}"]
    return []


def check_bib(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df.latex is None:
        return []
    bib = (lib.root / str(setting)).resolve()
    out = []
    keys: set[str] = set()
    if bib.is_file():
        keys = set(_BIB_KEY_RE.findall(bib.read_text(encoding="utf-8")))
    cited = [k.strip() for m in _CITE_RE.finditer(df.latex) for k in m.group(1).split(",") if k.strip()]
    if cited and not bib.is_file():
        out.append(f"cites {', '.join(cited)} but {setting} does not exist")
    else:
        out.extend(f"\\cite key `{k}` is not in {setting}" for k in dict.fromkeys(cited)
                   if k not in keys and "{{" not in k)
    folder = df.abspath.parent
    for match in _BIBLIO_RE.finditer(df.latex):
        for name in match.group(1).split(","):
            name = name.strip()
            target = (folder / (name if name.endswith(".bib") else name + ".bib")).resolve()
            if target != bib:
                out.append(f"\\bibliography{{{name}}} is not {setting}")
    if "\\begin{thebibliography}" in df.latex:
        out.append("has a bibliography of its own; use " + str(setting))
    for own in sorted(folder.glob("*.bib")):
        if own.resolve() != bib:
            out.append(f"has a bibliography file of its own, {own.name}; use {setting}")
    return out


def check_figures(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df.latex is None:
        return []
    figures = (lib.root / str(setting)).resolve()
    out = []
    for match in _GRAPHICS_RE.finditer(df.latex):
        name = match.group(1).strip()
        if not name or "{{" in name:
            continue
        found = False
        for base in (figures, df.abspath.parent):
            target = (base / name).resolve()
            if not (target == figures or figures in target.parents):
                continue
            if target.is_file() or any(p.is_file() for p in target.parent.glob(target.name + ".*")):
                found = True
                break
        if not found:
            out.append(f"\\includegraphics{{{name}}} names no file in {setting}")
    return out


def check_original_beside(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if not setting or df is not doc.meta_file:
        return []
    value = str(df.meta.get("original") or "")
    if not value or "{{" in value or value.startswith("Not kept:"):
        return []
    if not re.match(r"^original\.[A-Za-z0-9]+$", value):
        return [f"original `{value}` must be `original.<ext>` or start with `Not kept:`"]
    if not (df.abspath.parent / value).is_file():
        return [f"original `{value}` is not beside the page"]
    return []


def check_min_sources(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df.body is None:
        return []
    cited = {d.key for d in _cited(lib.links.get(df.path, []), doc) if d.is_a("source") or d.is_a("reading")}
    if len(cited) < int(setting):
        return [f"cites {len(cited)} sources or readings; it needs at least {setting}"]
    return []


def check_answer_cites(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    if df is not doc.meta_file or doc.status not in ("answered", "narrowed"):
        return []
    genres = list(setting)
    for nodes in regions.find(df, _genre(doc), "answer"):
        for target in _cited(links_in(lib, df, nodes), doc):
            if any(target.is_a(g) for g in genres):
                return []
    return [f"status is `{doc.status}` but the answer cites no {' or '.join(genres)}"]


def _items(doc: Document, df: DocFile, part: str) -> list[str] | None:
    found = regions.find(df, _genre(doc), part)
    if not found:
        return None
    return [" ".join(li.text().split()) for nodes in found for li in regions.list_items(nodes)]


def check_prediction_ids(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    items = _items(doc, df, "predictions")
    if not setting or items is None:
        return []
    out = []
    if not items:
        out.append("the predictions part has no list items")
    for i, item in enumerate(items, start=1):
        if not re.match(rf"^P{i}:", item):
            out.append(f"prediction {i} does not open with `P{i}:`")
        if not re.search(r"Confidence:\s*\d+(?:\.\d+)?\s*%\.?$", item):
            out.append(f"prediction {i} does not end with `Confidence: <n>%`")
    return out


def check_rule_ids(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    items = _items(doc, df, "rules")
    if not setting or items is None:
        return []
    out = []
    kills = 0
    if not items:
        out.append("the rules part has no list items")
    for i, item in enumerate(items, start=1):
        match = re.match(rf"^D{i}(?:\s*\(kill\))?:(\s*\(kill\))?", item)
        if not match:
            out.append(f"rule {i} does not open with `D{i}:`")
        elif "(kill)" in match.group(0):
            kills += 1
    if items and kills != 1:
        out.append(f"{kills} rules are marked (kill); exactly one must be")
    return out


def check_pinned_config(lib: Library, doc: Document, df: DocFile, setting: Any) -> list[str]:
    found = regions.find(df, _genre(doc), "configuration")
    if not setting or not found:
        return []
    blocks = [el for nodes in found for el in elements_in(nodes)
              if el.tag == "code" and el.inside("pre") and "language-yaml" in el.classes]
    if len(blocks) != 1:
        return [f"the configuration part holds {len(blocks)} fenced yaml blocks; it needs exactly one"]
    text = blocks[0].text()
    if "{{" in text:
        return []
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"the configuration does not parse as YAML: {str(exc).splitlines()[0]}"]
    return []


CARD_CHECKS: dict[str, CardCheck] = {
    "require": check_require,
    "forbid": check_forbid,
    "max_words": check_max_words,
    "cites": check_cites,
    "defined_once": check_defined_once,
    "min_links": check_min_links,
    "forward_links": check_forward_links,
    "stale_after_days": check_stale_after_days,
    "kinds": check_kinds,
    "bib": check_bib,
    "figures": check_figures,
    "original_beside": check_original_beside,
    "min_sources": check_min_sources,
    "answer_cites": check_answer_cites,
    "prediction_ids": check_prediction_ids,
    "rule_ids": check_rule_ids,
    "pinned_config": check_pinned_config,
}
