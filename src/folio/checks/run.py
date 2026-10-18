"""Run every check once and collect every problem, sorted."""

from __future__ import annotations

from ..library import Library
from .card import CARD_CHECKS
from .gate import GATE_CHECKS
from .lifecycle import permanent_parts
from .later import GIT_CHECKS, LIBRARY_CHECKS, LIFECYCLE_CHECKS, RULE_CHECKS, history_notice
from .problems import Problem
from .registry import BY_NAME


def severity(lib: Library, name: str) -> str:
    return lib.charter.checks.get(name, BY_NAME[name].default)


def run(lib: Library) -> list[Problem]:
    problems: list[Problem] = []

    def add(name: str, found: list[tuple[str, str]]) -> None:
        level = severity(lib, name)
        if level == "off":
            return
        problems.extend(Problem(path, level, name, message) for path, message in found)

    problems.extend(history_notice(lib, {n: severity(lib, n) for n in GIT_CHECKS}))
    for name, gate in GATE_CHECKS.items():
        add(name, gate(lib))
    for name, check in LIBRARY_CHECKS.items():
        add(name, check(lib))
    on = {p.name for p in lib.registry.packs.values() if p.on}
    for name, rule in RULE_CHECKS.items():
        if BY_NAME[name].pack in on:
            add(name, rule(lib))
    for doc in lib.documents:
        genre = doc.genre
        if genre is None:
            continue
        if genre.lives in LIFECYCLE_CHECKS:
            add(genre.lives, LIFECYCLE_CHECKS[genre.lives](lib, doc))
        if any(p.lives == "permanent" for p in genre.parts.values()):
            add("permanent", permanent_parts(lib, doc))
        if doc.status == "retired":
            continue  # its address redirects to its replacement; only its lifecycle is still checked
        for df in doc.files:
            checks = genre.parts[df.part].checks if df.part is not None else genre.checks
            # `require` also bars an <h1> of the document's own, so it runs on every card.
            checks = {"require": [], **checks}
            for name, setting in checks.items():
                if name in LIFECYCLE_CHECKS or setting is None or setting is False:
                    continue
                add(name, [(df.path, m) for m in CARD_CHECKS[name](lib, doc, df, setting)])
    return sorted(set(problems))
