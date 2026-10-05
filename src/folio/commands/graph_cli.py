"""The command line of the library graph: maps, tags, mv, promote, rm, search, cards, pack add."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .. import library as library_mod
from ..errors import FolioError
from . import lookup, maps_cmds, move, pack_add, tags_cmds

MAP_USAGE = ('usage: folio map add <map> <doc> [--reason ".."] [--group <heading>] [--after <doc>] | '
             'reason <map> <doc> ".." | rm <map> <doc>')
COMMANDS = ("maps", "map", "tags", "mv", "promote", "rm", "search", "cards")


def _lib() -> library_mod.Library:
    return library_mod.load(Path.cwd())


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _print(lines: list[str]) -> int:
    for line in lines:
        print(line)
    return 0


def cmd_maps(args: argparse.Namespace) -> int:
    data = maps_cmds.listing(_lib())
    if args.json:
        _json(data)
        return 0
    for m in data["maps"]:
        mark = " (home)" if m["home"] else " (top-level)" if m["top_level"] else ""
        print(f"{m['id']}{mark}: {m['title']} [{m['path']}]")
        for row in m["rows"]:
            why = f" - {row['reason']}" if row["reason"] else ""
            print(f"  {row['id'] or '?'}: {row['title'] or row['href']}{why}")
    if data["unmapped"]:
        print("on no map:")
        for d in data["unmapped"]:
            orphan = "  orphan: the gate flags it" if d["orphan"] else ""
            print(f"  {d['id']} ({d['genre']}): {d['path']}{orphan}")
    return 0


def cmd_map(args: argparse.Namespace) -> int:
    lib = _lib()
    w = args.words
    placed = args.group is not None or args.after is not None
    if w[0] == "add" and len(w) == 3:
        return _print(maps_cmds.add(lib, w[1], w[2], args.reason, group=args.group, after=args.after))
    if placed:
        raise FolioError("--group and --after go with `folio map add`")
    if w[0] == "reason" and len(w) == 4 and args.reason is None:
        return _print(maps_cmds.reason(lib, w[1], w[2], w[3]))
    if w[0] == "rm" and len(w) == 3 and args.reason is None:
        return _print(maps_cmds.remove(lib, w[1], w[2]))
    raise FolioError(MAP_USAGE)


def cmd_tags(args: argparse.Namespace) -> int:
    lib = _lib()
    if args.words:
        if len(args.words) != 3 or args.words[0] != "rename":
            raise FolioError("usage: folio tags [rename <old> <new>]")
        return _print(tags_cmds.rename(lib, args.words[1], args.words[2]))
    rows = tags_cmds.listing(lib)
    if args.json:
        _json(rows)
    else:
        for row in rows:
            print(f"{row['tag']:<24} {row['count']:>3}  {', '.join(row['documents'])}")
    return 0


def cmd_mv(args: argparse.Namespace) -> int:
    return _print(move.mv(_lib(), args.doc, args.to))


def cmd_promote(args: argparse.Namespace) -> int:
    return _print(move.promote(_lib(), args.doc, args.genre))


def cmd_rm(args: argparse.Namespace) -> int:
    return _print(move.rm(_lib(), args.doc, args.to))


def cmd_search(args: argparse.Namespace) -> int:
    hits = lookup.search(_lib(), " ".join(args.words), args.all)
    if args.json:
        _json(hits)
    elif not hits:
        print("No matches.")
    for h in [] if args.json else hits:
        where = "" if h["library"] == "." else f"[{h['library']}] "
        part = f", {h['part']}" if h["part"] else ""
        print(f"{where}{h['id']} ({h['genre']}{part}, {h['status']}): {h['title']} - {h['path']}")
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    rows = lookup.cards(_lib(), map_ref=args.map, tag=args.tag, doc_ref=args.doc)
    if args.json:
        _json(rows)
        return 0
    for c in rows:
        print(f"Q: {c['question']}\nA: {c['answer']}\n   ({c['doc']}, {c['path']})")
    print(f"{len(rows)} card{'s' if len(rows) != 1 else ''}")
    return 0


def cmd_pack_add(lib: library_mod.Library, name: str | None, genres: str | None,
                 workflows: str | None) -> int:
    if not name:
        raise FolioError("usage: folio pack add <name> --genres .. --workflows ..")
    return _print(pack_add.add(lib, name, genres, workflows))


def register(sub: Any) -> None:
    s = sub.add_parser("maps", help="The maps, what each lists, and the documents on no map.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_maps)

    s = sub.add_parser(
        "map", help="Change a map's rows: `add`, `reason` or `rm` one.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Change a map's rows.\n\n"
                    "  folio map add <map> <doc> [--reason ..] [--group <heading>] [--after <doc>]\n"
                    "      add a row; at the end of the last group, at the end of the group under\n"
                    "      <heading> (a new group when none has it), or right after <doc>'s row\n"
                    "  folio map reason <map> <doc> \"..\"   set or clear a row's one-line reason\n"
                    "  folio map rm <map> <doc>             remove a row")
    s.add_argument("words", nargs="+", metavar="add|reason|rm ...")
    s.add_argument("--reason", help="why to follow the document from this map, in one line")
    s.add_argument("--group", help="the heading of the group to add the row to")
    s.add_argument("--after", help="the document whose row the new row follows")
    s.set_defaults(func=cmd_map)

    s = sub.add_parser("tags", help="The tags in use; `rename <old> <new>` renames one everywhere.")
    s.add_argument("words", nargs="*")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_tags)

    s = sub.add_parser("mv", help="Move a document to a new slug or path, keeping links, comments, id and dates.")
    s.add_argument("doc")
    s.add_argument("to")
    s.set_defaults(func=cmd_mv)

    s = sub.add_parser("promote", help="Change a document's genre, keeping its id, links, comments and dates.")
    s.add_argument("doc")
    s.add_argument("genre")
    s.set_defaults(func=cmd_promote)

    s = sub.add_parser("rm", help="Retire a document into another: `rm <doc> --to <doc>`.")
    s.add_argument("doc")
    s.add_argument("--to", required=True)
    s.set_defaults(func=cmd_rm)

    s = sub.add_parser("search", help="Search this library, or with --all every library the charter lists.",
                       description="Search titles, ids, tags, descriptions and text. A document matches only "
                                   "when every word given is a whole word in it or the start of one; words "
                                   "under two characters are ignored. Each hit shows its status, and retired "
                                   "documents come last. The files are read as they are now, so a document is "
                                   "found before `folio index` runs.")
    s.add_argument("words", nargs="+", help="every word must match a word or its start (case does not matter)")
    s.add_argument("--all", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("cards", help="The flashcards (details.card) in scope, read from the files as they are now.")
    for flag in ("--map", "--tag", "--doc"):
        s.add_argument(flag)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_cards)
