"""The checks that read git history or a pack's rules, registered by name.

The lifecycle checks and record-id reuse live in `lifecycle`, the pack rules
in `rules`.
"""

from __future__ import annotations

from .. import history
from ..library import Library
from .lifecycle import frozen, permanent
from .problems import Problem
from .rules import cites_superseded, source_pointer, uncited_number, unverified_identifier

GIT_CHECKS = ("permanent", "frozen", "unique-id")


def history_notice(lib: Library, severity: dict[str, str]) -> list[Problem]:
    """One warning when the library has no git history to check its lifecycles against."""
    if history.in_git(lib):
        return []
    wanted = []
    for doc in lib.documents:
        genre = doc.genre
        if genre is None:
            continue
        if genre.lives in ("permanent", "frozen"):
            wanted.append(genre.lives)
        if any(df.part is not None and genre.parts[df.part].lives == "permanent" for df in doc.files):
            wanted.append("permanent")
        if genre.prefix:
            wanted.append("unique-id")
    live = [name for name in GIT_CHECKS if name in wanted and severity.get(name) != "off"]
    if not live:
        return []
    return [Problem("folio.yaml", "warning", live[0],
                    "the library is not in a git repository (or git is not installed), so "
                    f"{', '.join(live)} could not be checked against history and were skipped")]


LIFECYCLE_CHECKS = {"permanent": permanent, "frozen": frozen}
RULE_CHECKS = {
    "uncited-number": uncited_number,
    "cites-superseded": cites_superseded,
    "unverified-identifier": unverified_identifier,
    "source-pointer": source_pointer,
}
