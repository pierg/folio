"""The one list of checks, matching docs/spec/checks.md: names, kinds and default severities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckSpec:
    name: str
    kind: str  # "gate" | "card" | "lifecycle" | "rule"
    default: str  # "error" | "warning"
    pack: str | None = None


CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec("broken-link", "gate", "error"),
    CheckSpec("library-link", "gate", "warning"),
    CheckSpec("location", "gate", "error"),
    CheckSpec("fields", "gate", "error"),
    CheckSpec("status", "gate", "error"),
    CheckSpec("placeholder", "gate", "error"),
    CheckSpec("orphan", "gate", "error"),
    CheckSpec("home-maps", "gate", "error"),
    CheckSpec("unique-id", "gate", "error"),
    CheckSpec("index-current", "gate", "error"),
    CheckSpec("stale-quote", "gate", "error"),
    CheckSpec("require", "card", "error"),
    CheckSpec("forbid", "card", "error"),
    CheckSpec("max_words", "card", "error"),
    CheckSpec("cites", "card", "error"),
    CheckSpec("defined_once", "card", "error"),
    CheckSpec("min_links", "card", "error"),
    CheckSpec("forward_links", "card", "error"),
    CheckSpec("stale_after_days", "card", "warning"),
    CheckSpec("permanent", "lifecycle", "error"),
    CheckSpec("frozen", "lifecycle", "error"),
    CheckSpec("kinds", "card", "error"),
    CheckSpec("bib", "card", "error"),
    CheckSpec("figures", "card", "error"),
    CheckSpec("original_beside", "card", "error"),
    CheckSpec("min_sources", "card", "error"),
    CheckSpec("answer_cites", "card", "error"),
    CheckSpec("prediction_ids", "card", "error"),
    CheckSpec("rule_ids", "card", "error"),
    CheckSpec("pinned_config", "card", "error"),
    CheckSpec("uncited-number", "rule", "warning", "lab"),
    CheckSpec("cites-superseded", "rule", "warning", "lab"),
    CheckSpec("unverified-identifier", "rule", "error", "knowledge-base"),
    CheckSpec("source-pointer", "rule", "warning", "knowledge-base"),
)

BY_NAME = {c.name: c for c in CHECKS}


def check_names() -> set[str]:
    return set(BY_NAME)


def card_check_names() -> set[str]:
    """The names a card may list under `checks:`: card checks and the lifecycle checks."""
    return {c.name for c in CHECKS if c.kind in ("card", "lifecycle")}
