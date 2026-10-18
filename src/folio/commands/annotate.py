"""`folio annotations`: list, show, add, reply to and resolve comment threads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .. import annotations as ann
from .. import library as library_mod
from ..errors import FolioError

USAGE = ("usage: folio annotations list [--state <s>] [--json] | show <doc> | "
         "add <doc> --kind flag|question [--quote ..] --body .. [--label ..] --author <who> | "
         "reply <doc> <id> --body .. --author <who> [--state <s>] | "
         "resolve [--doc ..] [--label ..] --state <s> --body .. [--author <who>]")


def _line(r: dict[str, Any]) -> str:
    label = f" [{r['label']}]" if r["label"] else ""
    about = f"\"{r['quote']}\"" if r["quote"] else "(the whole document)"
    return f"{r['path']} {r['id']} {r['kind']}{label} {r['state']}: {about}"


def run(args: argparse.Namespace) -> int:
    lib = library_mod.load(Path.cwd())
    words = args.words
    action = words[0] if words else "list"

    def need(*names: str) -> None:
        for name in names:
            if getattr(args, name) is None:
                raise FolioError(f"folio annotations {action} needs --{name}")

    if action == "list":
        if len(words) > 1:
            raise FolioError(USAGE)
        state = args.state or "open"
        if state != "all" and state not in ann.STATES:
            raise FolioError(f"state `{state}` is not one of {', '.join(ann.STATES)} or all")
        rows = [ann.row(lib, r, t) for r, t in ann.all_threads(lib) if state == "all" or t.get("state") == state]
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            for r in rows:
                print(_line(r))
        return 0
    if action == "show":
        if len(words) != 2:
            raise FolioError(USAGE)
        doc = ann.resolve_file(lib, words[1]).doc
        files = doc.files if doc is not None else []
        threads = [(f.path, t) for f in files for t in ann.load_threads(lib.root, f.path)]
        if args.json:
            print(json.dumps([{**ann.row(lib, r, t), "thread": t} for r, t in threads], indent=2,
                             ensure_ascii=False))
            return 0
        for rel, t in threads:
            print(_line(ann.row(lib, rel, t)))
            for m in t.get("messages") or []:
                moved = f" -> {m['state']}" if m.get("state") else ""
                print(f"  {m.get('date')} {m.get('author')}{moved}: {m.get('body')}")
        if not threads:
            print("No threads.")
        return 0
    if action == "add":
        if len(words) != 2:
            raise FolioError(USAGE)
        need("kind", "body", "author")
        rel = ann.resolve_file(lib, words[1]).path
        t = ann.add(lib, rel, args.kind, args.quote, args.body, args.author, args.label)
        print(f"added {t['id']} ({t['state']}) to {ann.sidecar_path(rel)}")
        return 0
    if action == "reply":
        if len(words) != 3:
            raise FolioError(USAGE)
        need("body", "author")
        rel = ann.resolve_file(lib, words[1]).path
        t = ann.reply(lib, rel, words[2], args.body, args.author, args.state)
        print(f"replied to {t['id']} ({t['state']}) in {ann.sidecar_path(rel)}")
        return 0
    if action == "resolve":
        if len(words) != 1:
            raise FolioError(USAGE)
        need("state", "body")
        moved = ann.resolve(lib, args.state, args.body, args.author or "agent", doc=args.doc, label=args.label)
        for rel, t in moved:
            print(f"moved {t['id']} to {t['state']} in {ann.sidecar_path(rel)}")
        if not moved:
            print("No open or noted thread matches.")
        return 0
    raise FolioError(USAGE)


def register(sub: Any) -> None:
    s = sub.add_parser(
        "annotations", help="List, show, add, reply to and resolve comment threads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Comment threads on documents. <doc> is an id or a path.\n\n"
                    "  list [--state open|noted|addressed|declined|withdrawn|all] [--json]\n"
                    "      threads in that state (default open)\n"
                    "  show <doc> [--json]                 every thread on a document, with its messages\n"
                    "  add <doc> --kind flag|question [--quote ..] --body .. --author <who> [--label ..]\n"
                    "      open a thread on a passage; with no --quote it is about the whole document\n"
                    "  reply <doc> <id> --body .. --author <who> [--state <s>]\n"
                    "      answer a thread, and move it to a state\n"
                    "  resolve --state <s> --body .. [--doc ..] [--label ..] [--author <who>]\n"
                    "      move every open or noted thread the filters pick to one state")
    s.add_argument("words", nargs="*", metavar="list|show|add|reply|resolve ...")
    for flag in ("--state", "--kind", "--quote", "--body", "--label", "--author", "--doc"):
        s.add_argument(flag)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=run)
