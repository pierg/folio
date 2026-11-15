"""A view's rail: a tree at any depth, with a sign, a pulse, a mark, a short id, folds, counts and a key."""

from __future__ import annotations

from pathlib import Path

from folio import views

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "shell/folio.js").read_text(encoding="utf-8")
CSS = (ROOT / "shell/folio.css").read_text(encoding="utf-8")


def test_the_contract_names_every_key_the_shell_reads() -> None:
    doc = views.__doc__ or ""
    for key in ("tone", "sign", "pulse", "gone", "mark", "summary", "fold", "legend", "kind"):
        assert key in doc, key
    for key in ("it.sign", "it.pulse", "it.gone", "it.mark", "it.id", "it.summary", "g.fold", "it.legend", "it.kind"):
        assert key in SHELL, key


def test_a_group_nests_at_any_depth_and_opens_on_the_page_being_read() -> None:
    assert "function holdsHere(it) { return isHere(it) || (it.items || []).some(holdsHere); }" in SHELL
    assert "if (it.items) return el(\"li\", null, [vgroup(it)]);" in SHELL  # a group inside a group is drawn the same way
    assert ".f-rail .f-rlist .f-rgroup .f-rlist" in CSS


def test_a_sign_carries_its_tone_and_a_live_one_pulses_unless_motion_is_reduced() -> None:
    assert '"data-t": it.tone' in SHELL and '(it.pulse ? " f-vpulse" : "")' in SHELL
    for tone in ("ok", "warn", "bad", "info", "ink", "gone"):  # plain is the default
        assert f'[data-t="{tone}"]' in CSS, tone
    assert "@keyframes" in CSS and "prefers-reduced-motion" in CSS


def test_what_is_folded_and_the_key_come_last_and_closed() -> None:
    assert 'wrap.classList.add("f-vfold")' in SHELL and ".f-vfold" in CSS
    assert 'el("details", { class: "f-vlegend" }' in SHELL and ".f-vlegend" in CSS
    assert "if (g.legend) return;  // a key goes last" in SHELL
