"""Every `folio` command the skills, workflows, cards and specs name exists, with the flags they give it."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from folio.cli import parser

ROOT = Path(__file__).resolve().parent.parent
DOCS = [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("packs/*/workflows/*.md"), *ROOT.glob("packs/*/PACK.md"),
        *ROOT.glob("packs/*/rules.md"), *ROOT.glob("genres/*/GENRE.md"), *ROOT.glob("packs/*/genres/*/GENRE.md"),
        *ROOT.glob("docs/spec/*.md"), ROOT / "shell/COMPONENTS.md", ROOT / "SETUP.md",
        ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CONTRIBUTING.md"]
_SPAN_RE = re.compile(r"`(folio [^`]+)`")
_FLAG_RE = re.compile(r"(?<![\w<])--[a-z][a-z-]*")


def _commands() -> dict[str, argparse.ArgumentParser]:
    p = parser()
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return dict(sub.choices)


def test_every_named_command_and_flag_exists() -> None:
    commands = _commands()
    wrong = []
    for path in DOCS:
        if not path.is_file():
            continue
        for span in _SPAN_RE.findall(path.read_text(encoding="utf-8")):
            words = span.split()
            if len(words) < 2 or words[1].startswith(("<", "-")):
                continue
            name = words[1]
            if name not in commands:
                wrong.append(f"{path.relative_to(ROOT)}: `{span}` names no command `{name}`")
                continue
            command = commands[name]
            if command.get_default("takes_extra"):
                continue  # `folio new` takes any field the genre declares
            known = {o for a in command._actions for o in a.option_strings}
            for flag in _FLAG_RE.findall(span):
                if flag not in known:
                    wrong.append(f"{path.relative_to(ROOT)}: `{span}`: `folio {name}` has no {flag}")
    assert wrong == []
