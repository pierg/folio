"""The `folio` command line. Only skills call it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from . import __version__, indexer
from . import library as library_mod
from .checks.run import run as run_checks
from .commands import annotate, charter_cmds, graph_cli, create, genre_cmds, query, setup
from .errors import FolioError

# Commands the engine names but does not carry yet.
LATER: dict[str, str] = {}


def _lib() -> library_mod.Library:
    return library_mod.load(Path.cwd())


def _print_changes(changes: list[str]) -> None:
    for line in changes:
        print(line)


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def cmd_init(args: argparse.Namespace) -> int:
    _print_changes(setup.init(Path(args.dir), name=args.name, purpose=args.purpose))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lib = _lib()
    problems = run_checks(lib)
    errors = sum(1 for p in problems if p.severity == "error")
    warnings = sum(1 for p in problems if p.severity == "warning")
    if args.json:
        _json({"problems": [p.as_dict() for p in problems], "errors": errors, "warnings": warnings,
               "documents": len(lib.documents)})
    else:
        for problem in problems:
            print(problem.line())
        print(f"folio check: {len(lib.documents)} documents, {errors} errors, {warnings} warnings")
    return 1 if errors else 0


def cmd_index(args: argparse.Namespace) -> int:
    changed = indexer.write(_lib())
    _print_changes([f"wrote {p}" for p in changed] or ["the indices in .folio/ are current"])
    return 0


def cmd_genres(args: argparse.Namespace) -> int:
    lib, found = library_mod.load_or_shipped(Path.cwd())
    rows = genre_cmds.genre_rows(lib, every=not found)
    if not found and not args.json:
        print("No library here; these are the genres folio ships. A pack's genres need the pack on.")
    if args.json:
        _json(rows)
    else:
        for row in rows:
            extra = " (overridden)" if row["overridden"] else ""
            print(f"{row['name']:<16} {row['source'] + extra:<28} {row['path']:<44} {row['card']}")
    return 0


def cmd_genre(args: argparse.Namespace) -> int:
    words = args.words
    if words[0] not in ("add", "override") and len(words) == 1 and not args.extends:
        print(genre_cmds.card(library_mod.load_or_shipped(Path.cwd())[0], words[0]), end="")
        return 0
    lib = _lib()
    if words[0] == "add":
        if len(words) != 2:
            raise FolioError("usage: folio genre add <name> [--extends <parent>]")
        _print_changes(genre_cmds.add(lib, words[1], args.extends))
    elif words[0] == "override":
        if len(words) != 2:
            raise FolioError("usage: folio genre override <name>")
        _print_changes(genre_cmds.override(lib, words[1]))
    else:
        if len(words) != 1 or args.extends:
            raise FolioError("usage: folio genre <name> | add <name> [--extends <parent>] | override <name>")
        print(genre_cmds.card(lib, words[0]), end="")
    return 0


def cmd_workflows(args: argparse.Namespace) -> int:
    rows = genre_cmds.workflow_rows(_lib())
    if args.json:
        _json(rows)
    else:
        for row in rows:
            print(f"{row['name']:<20} {row['source']:<22} {row['file']}")
    return 0


def cmd_workflow(args: argparse.Namespace) -> int:
    _print_changes(genre_cmds.workflow_add(_lib(), args.name))
    return 0


def cmd_new(args: argparse.Namespace, extra: list[str]) -> int:
    fields: dict[str, str] = {}
    i = 0
    while i < len(extra):
        token = extra[i]
        if not token.startswith("--") or i + 1 >= len(extra):
            raise FolioError(f"cannot read `{token}`; give fields as --<field> <value>")
        key, value = token[2:], extra[i + 1]
        if "=" in key:
            key, value = key.split("=", 1)
            i += 1
        else:
            i += 2
        fields[key] = value
    written = create.new(_lib(), args.genre, args.slug, part=tuple(args.part) if args.part else None,
                         title=args.title, description=args.description, tags=args.tags, fields=fields,
                         status=args.status)
    _print_changes([f"created {p}" for p in written])
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    lib = _lib()
    if args.action == "add":
        for name in ("title", "description", "body"):
            if getattr(args, name) is None:
                raise FolioError(f"folio journal add needs --{name}")
        rel = create.journal_add(lib, title=args.title, description=args.description, body=args.body,
                                 kind=args.kind, about=args.about, date=args.date, tags=args.tags)
        print(f"created {rel}")
        return 0
    if args.action is not None:
        raise FolioError(f"unknown journal action `{args.action}`; use `folio journal add` or no action")
    entries = query.journal(lib, kind=args.kind, about=args.about, tag=args.tag, since=args.since)
    if args.json:
        _json(entries)
    elif not entries:
        print("No journal entries match.")
    else:
        for e in entries:
            kind = f" [{e['kind']}]" if e["kind"] else ""
            print(f"{e['date']}{kind} {e['title']} ({e['path']})")
    return 0


def cmd_cite(args: argparse.Namespace) -> int:
    rows = query.cite(_lib(), args.id)
    if args.json:
        _json(rows)
    else:
        for row in rows:
            print(f"{row['id']} ({row['genre']}, {row['status']}): {row['title']}")
            print(f"  path:        {row['path']}")
            print(f"  description: {row['description']}")
            for fmt, markup in row["markup"].items():
                if markup is not None:
                    print(f"  {fmt + ':':<12} {markup}")
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    root = setup.project_root(_lib().root)
    if args.action == "update":
        changes = setup.update_skills(root)
        _print_changes(changes or ["the skills are current"])
        return 0
    rows = setup.skills_status(root)
    if args.json:
        _json([{"name": name, "state": state} for name, state in rows])
    else:
        for name, state in rows:
            print(f"{name:<12} {state}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    lib = _lib()
    if args.action == "get":
        if len(args.rest) > 1:
            raise FolioError("usage: folio config get [<key>]")
        print(charter_cmds.get(lib, args.rest[0] if args.rest else None))
    else:
        if len(args.rest) != 2:
            raise FolioError("usage: folio config set <key> <value>")
        print(charter_cmds.set_value(lib, args.rest[0], args.rest[1]))
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    if args.action == "list":
        here, found = library_mod.load_or_shipped(Path.cwd())
        rows = charter_cmds.pack_list(here)
        if args.json:
            _json(rows)
        else:
            if not found:
                print("No library here; these are the packs folio ships.")
            for row in rows:
                state = ("on " if row["on"] else "off") if found else "-  "
                print(f"{row['name']:<16} {state} {row['source']:<8} {row['purpose']}")
        return 0
    lib = _lib()
    if args.action == "add":
        return graph_cli.cmd_pack_add(lib, args.name, args.genres, args.workflows)
    if args.action == "on" and args.git:
        raise FolioError("git-pinned packs are not supported yet")
    if not args.name:
        raise FolioError(f"usage: folio pack {args.action} <name>")
    if args.action == "on":
        print(charter_cmds.pack_on(lib, args.name))
    else:
        print(charter_cmds.pack_off(lib, args.name))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .site import serve

    lib = _lib()
    if args.command == "serve":
        serve.serve(lib.root, args.port, args.host, args.push)
    elif args.command == "up":
        print(serve.up(lib.root, args.port, args.host, args.push))
    else:
        print(serve.down(lib.root))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from .site.site import export_site

    lib = _lib()
    out = Path(args.out) if args.out else lib.root / "_site"
    warnings: list[str] = []
    written, pages = export_site(lib.root, out, args.base, warnings)
    print(f"exported {len(pages)} pages to {out.resolve()} ({len(written)} files in all, base {args.base})")
    for warning in warnings:
        print(f"warning: {warning}")
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    from . import paper

    lib = _lib()
    if args.action == "build":
        print(f"built {paper.build(lib, args.slug).rel}")
    elif args.action == "freeze":
        if not args.version:
            raise FolioError("usage: folio paper freeze <slug> --version <v>")
        _print_changes(paper.freeze(lib, args.slug, args.version))
    else:
        rows = paper.versions(lib, args.slug)
        if args.json:
            _json(rows)
        elif not rows:
            print(f"{args.slug} has no versions yet; `folio paper freeze` makes one.")
        else:
            for row in rows:
                print(f"{row['name']:<16} {row['date']:<12} {row['path']}")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"folio {__version__}")
    return 0


def _later(name: str) -> int:
    raise FolioError(f"`folio {name}` is not available in this version of the engine")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="folio", description="Build and keep a folio library. Skills call this.")
    p.add_argument("--version", action="version", version=f"folio {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("init", help="Create a library: charter, content/, assets/, home page and skills.")
    s.add_argument("dir", nargs="?", default=".")
    s.add_argument("--name", help="the library's name, shown as the home page's title (default: the folder's)")
    s.add_argument("--purpose", help="one sentence: what the library is for")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("check", help="The gate: name every problem in one pass. Changes nothing.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("index", help="Regenerate the indices in .folio/.")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("genres", help="The genres available, with where each comes from.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_genres)

    s = sub.add_parser("genre", help="Print a merged card; `add` a genre or variant; `override` one.")
    s.add_argument("words", nargs="+", metavar="<name> | add <name> | override <name>")
    s.add_argument("--extends")
    s.set_defaults(func=cmd_genre)

    s = sub.add_parser("workflows", help="The workflows available, with where each comes from.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_workflows)

    s = sub.add_parser("workflow", help="Scaffold a workflow in the library: `add <name>`.")
    s.add_argument("action", choices=["add"])
    s.add_argument("name")
    s.set_defaults(func=cmd_workflow)

    s = sub.add_parser(
        "new", help="Create a document, or a part, from its genre's skeleton.",
        description="Create a document, or a part, from its genre's skeleton. A new document is live; "
                    "give --status draft only to hold it back. The slug becomes its id, which must be "
                    "free across the whole library; a record genre takes the next free number instead.",
        epilog="Any field the genre declares is set with --<field> <value> (for example --rank 2, "
               "--question Q-1, --authors \"A, B\"); `folio genre <name>` lists the genre's fields "
               "and their types.")
    s.add_argument("genre")
    s.add_argument("slug", nargs="?")
    s.add_argument("--part", nargs=2, metavar=("PART", "NAME"))
    s.add_argument("--title")
    s.add_argument("--description")
    s.add_argument("--tags", help="comma-separated lowercase slugs")
    s.add_argument("--status", help="one of the genre's states; omit it for a live document")
    s.set_defaults(func=cmd_new, takes_extra=True)

    s = sub.add_parser("journal", help="List journal entries, newest first; `add` writes a new one.")
    s.add_argument("action", nargs="?")
    for flag in ("--title", "--description", "--body", "--kind", "--about", "--date", "--tags",
                 "--tag", "--since"):
        s.add_argument(flag)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_journal)

    s = sub.add_parser("cite", help="A document's path, status and citation markup.")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_cite)

    s = sub.add_parser("config", help="Read or change the charter: `get [<key>]`, `set <key> <value>`.")
    s.add_argument("action", choices=["get", "set"])
    s.add_argument("rest", nargs="*")
    s.set_defaults(func=cmd_config)

    s = sub.add_parser("pack", help="List the packs, switch one `on` or `off`, or `add` one from library genres.")
    s.add_argument("action", choices=["list", "on", "off", "add"])
    s.add_argument("name", nargs="?")
    s.add_argument("--git")
    s.add_argument("--ref")
    s.add_argument("--genres")
    s.add_argument("--workflows")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_pack)

    for name, summary in LATER.items():
        s = sub.add_parser(name, help=summary + " (not available yet)")
        s.add_argument("rest", nargs=argparse.REMAINDER)
        s.set_defaults(func=lambda a, n=name: _later(n))

    s = sub.add_parser("paper", help="Build a paper, freeze a version of it, or list its versions.")
    s.add_argument("action", choices=["build", "freeze", "versions"])
    s.add_argument("slug")
    s.add_argument("--version", dest="version", help="freeze: the new version's name, such as v1")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_paper)

    for name, summary in (("serve", "Serve the library, in the foreground."),
                          ("up", "Serve the library, in the background."),
                          ("down", "Stop the background server.")):
        s = sub.add_parser(name, help=summary)
        if name != "down":
            s.add_argument("--port", type=int, default=5170)
            s.add_argument("--host", default="127.0.0.1",
                           help="the address to listen on (default 127.0.0.1, this machine only)")
            s.add_argument("--push", action="store_true",
                           help="pull before and push after each comment's commit (for a deployed server)")
        s.set_defaults(func=cmd_serve)

    s = sub.add_parser("export", help="Write the static site.")
    s.add_argument("--out")
    s.add_argument("--base", default="/")
    s.set_defaults(func=cmd_export)

    annotate.register(sub)
    graph_cli.register(sub)

    s = sub.add_parser("skills", help="The installed skills against folio's own; `update` refreshes the stale ones.")
    s.add_argument("action", nargs="?", choices=["update"])
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_skills)

    s = sub.add_parser("version", help="The engine version.")
    s.set_defaults(func=cmd_version)
    _describe(sub)
    return p


def _describe(sub: Any) -> None:
    """Every subcommand's `--help` opens with its one-line description."""
    helps = {a.dest: a.help for a in sub._choices_actions}
    for name, command in sub.choices.items():
        if command.description is None:
            command.description = helps.get(name)


def _take_fields(p: argparse.ArgumentParser, argv: list[str]) -> tuple[list[str], list[str]]:
    """Lift `folio new`'s free --<field> <value> pairs out of argv before argparse reads it.

    Left in, a field's value can be taken for the optional slug: Python 3.12.8 and later
    match positionals across unknown options, so `new result --protocol P` read P as the slug.
    """
    first = next((i for i, t in enumerate(argv) if not t.startswith("-")), None)
    if first is None or argv[first] != "new":
        return argv, []
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    known = sub.choices["new"]._option_string_actions
    kept, fields = argv[:first + 1], []
    i = first + 1
    while i < len(argv):
        token = argv[i]
        name = token.split("=", 1)[0]
        if token.startswith("--") and name not in known:
            width = 1 if "=" in token else 2
            fields.extend(argv[i:i + width])
        else:
            action = known.get(name) if token.startswith("-") else None
            takes = action.nargs if action is not None and isinstance(action.nargs, int) else (
                1 if action is not None and action.nargs is None else 0)
            width = 1 if "=" in token else 1 + takes
            kept.extend(argv[i:i + width])
        i += width
    return kept, fields


def main(argv: list[str] | None = None) -> int:
    p = parser()
    argv, fields = _take_fields(p, list(sys.argv[1:] if argv is None else argv))
    args, extra = p.parse_known_args(argv)
    extra = fields + extra
    if args.command is None:
        p.print_help()
        return 2
    try:
        if getattr(args, "takes_extra", False):
            return args.func(args, extra)
        if extra:
            p.error(f"unrecognised arguments: {' '.join(extra)}")
        return args.func(args)
    except FolioError as exc:
        print(f"folio: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
