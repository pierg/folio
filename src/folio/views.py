"""Views: pages a library shows that no file holds.

A document is a file under `content/`. A view is drawn from data when it is asked for: a lab's
record, a build's results, anything a library wants shown in its shell that is not prose someone
wrote. The charter names each provider as a Python module under `views:`. The module has one
function, `provider(library_root)`, that returns an object with:

    prefix      the first segment of every path it serves, such as `lab`: exactly one path segment
                (letters, digits, `.`, `_`, `-`), not a name folio serves itself
    title       its name in the rail (the prefix when absent)
    home        True when the site's front page should be this provider's; at most one provider asks
    get(path)   a `View` for a path under the prefix (`""` is its front page), or None
    rail()      its entries in the rail: a list of {title, url, status, tone, items: [...], open}; `status` is the
                provider's own word for the entry's state, `tone` (ok, warn, info, bad or none) colours its dot;
                an entry with `items` is a group, and `open: True` shows it open until the reader closes it
    search()    its entries in the search index, shaped like `.folio/search.json`'s
    paths()     every path it serves, for the exported site
    stamp()     a short string that changes when anything it draws from changes
    backlinks() for each document path, the view pages that point at it: {path: [{title, url, status}]}

folio draws the shell around a view exactly as it does around a document: the rail, the header from
the view's title, description, genre and status, the outline, search. A view's own panel sections
go beside the page. folio never looks inside the data a provider reads.

A provider is code. folio imports the module and runs it with the rights of the process that serves
or checks the library, so a library that names one is trusted as much as the machine it runs on.
Whoever runs folio installs the provider in folio's own environment. A library cannot bring its
own: a module whose file is inside the library's folder, or inside the repository that holds it, is
refused before it is imported. The one exception is the running Python's own library directories
(its standard library and its site-packages), which may sit in a `.venv` kept in the repository.

The boundary: folio trusts whatever is installed in the environment that runs it. That environment
must not be writable by a pull of the served repository. A module committed into an environment
inside the working tree is code on the host, and folio cannot tell it from an installed one.

A provider that fails does not stop the site. `get()` raising gives that page a 500; `stamp()` raising
keeps the last stamp; `rail()`, `search()`, `backlinks()` and `paths()` raising give nothing for that
provider. Each failure is written to the error stream with its traceback. `folio export` is strict:
there a failure stops the export.
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import sysconfig
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import FolioError

if TYPE_CHECKING:
    from .library import Library

RESERVED = ("content", "assets", "shell", ".folio", "_folio", "index.html", ".nojekyll")  # paths folio serves itself
_PREFIX_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class View:
    title: str
    main: str  # the HTML inside <main>; it writes no <h1>, the shell draws the header
    description: str = ""
    genre: str = ""
    status: str = ""
    head: str = ""  # a <style> block of the provider's own, using the shell's tokens
    panels: list[tuple[str, str]] = field(default_factory=list)  # (title, HTML) for the page panel
    path: str = ""  # the file or folder this view is drawn from, for the header's copy-path control


class Provider:
    """A provider as folio calls it: the module's own object, with every call guarded."""

    def __init__(self, module: str, made: Any) -> None:
        self.module = module
        self.made = made
        self.prefix: str = made.prefix
        self.title = str(getattr(made, "title", "") or self.prefix)
        self.home = bool(getattr(made, "home", False))
        self._stamp = ""
        self.failures = 0  # how many calls have failed: an answer built across a failure is not kept (serve.py)

    def _failed(self, what: str) -> None:
        self.failures += 1
        sys.stderr.write(f"folio: view provider `{self.module}` failed in {what}:\n{traceback.format_exc()}")
        sys.stderr.flush()

    def _call(self, name: str, empty: Any, strict: bool) -> Any:
        try:
            got = getattr(self.made, name)()
            return empty if got is None else got
        except Exception as err:
            if strict:
                raise FolioError(f"view provider `{self.module}` failed in {name}() ({type(err).__name__}: {err})") from err
            self._failed(f"{name}()")
            return empty

    def get(self, path: str) -> View | None:
        """The view at a path under the prefix, or None. It raises what the provider raises."""
        return self.made.get(path)

    def rail(self, strict: bool = False) -> list:
        return list(self._call("rail", [], strict))

    def search(self, strict: bool = False) -> list:
        return list(self._call("search", [], strict))

    def paths(self, strict: bool = False) -> list:
        return list(self._call("paths", [], strict))

    def backlinks(self, strict: bool = False) -> dict:
        return dict(self._call("backlinks", {}, strict))

    def stamp(self) -> str:
        """The provider's stamp; the last one it gave when it fails, so the documents keep being served."""
        try:
            self._stamp = str(self.made.stamp())
        except Exception:
            self._failed("stamp()")
        return self._stamp


def _repository(root: Path) -> Path | None:
    """The working tree that holds the library: the nearest folder, from the library up, with a `.git`."""
    for folder in (root, *root.parents):
        if (folder / ".git").exists():
            return folder
    return None


def _places(spec: Any) -> list[Path]:
    """Where a module's code is, from its import spec: its file, and a package's folders."""
    out = []
    origin = getattr(spec, "origin", None)
    if origin and origin not in ("built-in", "frozen", "namespace"):
        out.append(Path(origin))
    out += [Path(p) for p in (getattr(spec, "submodule_search_locations", None) or [])]
    return out


def _refuse_inside(lib: "Library", name: str, places: list[Path]) -> None:
    """A provider is installed by whoever runs folio; the library, and its repository, cannot hold it."""
    where = lib.charter.path
    root = lib.root.resolve()
    repo = _repository(root)
    own = _own_libraries()
    for place in places:
        place = place.resolve()  # where the code really is, whatever links lead to it
        if any(place == env or env in place.parents for env in own):
            continue  # the running Python's own library directories, even in a `.venv` kept in the repository
        if place == root or root in place.parents:
            raise FolioError(f"{where}: `views` names `{name}`, found at {place}, inside the library. A provider is code "
                             "that runs with the server's rights: a library cannot bring its own. Install it in folio's "
                             "environment, from outside the library")
        if repo is not None and (place == repo or repo in place.parents):
            raise FolioError(f"{where}: `views` names `{name}`, found at {place}, inside the repository that holds the "
                             f"library ({repo}). A provider is code that runs with the server's rights: the served "
                             "repository cannot bring its own. Install it in folio's environment, from outside the repository")


def _own_libraries() -> set[Path]:
    """The running Python's library directories: its standard library and its site-packages, as they
    really are on disk. Not the whole prefix: a repository can sit under a prefix, or hold one."""
    paths = sysconfig.get_paths()
    return {Path(paths[key]).resolve() for key in ("stdlib", "platstdlib", "purelib", "platlib") if paths.get(key)}


def _check_prefix(where: Path, name: str, prefix: Any) -> None:
    if not isinstance(prefix, str) or not prefix:
        raise FolioError(f"{where}: view provider `{name}` has an empty prefix; it is one path segment, such as `lab`")
    if "/" in prefix:
        raise FolioError(f"{where}: view provider `{name}` has prefix `{prefix}`, which holds a `/`; "
                         "a prefix is exactly one path segment")
    if prefix in RESERVED:
        raise FolioError(f"{where}: view provider `{name}` has prefix `{prefix}`, a path folio serves itself")
    if not _PREFIX_RE.fullmatch(prefix):
        raise FolioError(f"{where}: view provider `{name}` has prefix `{prefix}`; a prefix starts with a letter or a "
                         "digit and holds only letters, digits, `.`, `_` and `-`")


def _make(lib: "Library", name: str) -> Provider:
    where = lib.charter.path
    missing = (f"{where}: `views` names `{name}`, which is not installed in the environment running folio "
               f"({sys.executable}). Install the package that provides it there")
    top = name.split(".", 1)[0]
    try:
        spec = importlib.util.find_spec(top)  # finds the top package without running any of its code
    except Exception as err:
        raise FolioError(f"{where}: `views` names `{name}`, which cannot be found ({type(err).__name__}: {err})") from err
    if spec is None:
        raise FolioError(missing)
    _refuse_inside(lib, name, _places(spec))
    if "." in name:
        # The packages above the module are outside the library, so they may run; the module itself
        # is found, and placed, before any of its own code does.
        try:
            spec = importlib.util.find_spec(name)
        except ModuleNotFoundError as err:
            raise FolioError(missing) from err
        except Exception as err:
            raise FolioError(f"{where}: `views` names `{name}`, which cannot be imported ({type(err).__name__}: {err})") from err
        if spec is None:
            raise FolioError(missing)
        _refuse_inside(lib, name, _places(spec))
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as err:
        if err.name and (err.name == name or name.startswith(err.name + ".")):
            raise FolioError(missing) from err
        raise FolioError(f"{where}: `views` names `{name}`, which cannot be imported ({type(err).__name__}: {err})") from err
    except Exception as err:
        raise FolioError(f"{where}: `views` names `{name}`, which cannot be imported ({type(err).__name__}: {err})") from err
    _refuse_inside(lib, name, _places(getattr(module, "__spec__", None)))
    if not callable(getattr(module, "provider", None)):
        raise FolioError(f"{where}: `views` names `{name}`, which has no `provider(library_root)`")
    try:
        made = module.provider(lib.root)
    except Exception as err:
        raise FolioError(f"{where}: `views` names `{name}`, whose `provider(library_root)` failed "
                         f"({type(err).__name__}: {err})") from err
    if not hasattr(made, "prefix"):
        raise FolioError(f"{where}: view provider `{name}` has no `prefix`")
    _check_prefix(where, name, made.prefix)
    return Provider(name, made)


def load(lib: "Library") -> list[Provider]:
    """The providers the charter names, made once for this load of the library."""
    failed = getattr(lib, "_views_error", None)
    if failed is not None:
        raise FolioError(failed)
    made = getattr(lib, "_views", None)
    if made is None:
        try:
            made = [_make(lib, name) for name in lib.charter.views]
            where = lib.charter.path
            taken: dict[str, str] = {}
            for p in made:
                if p.prefix in taken:
                    raise FolioError(f"{where}: view providers `{taken[p.prefix]}` and `{p.module}` both take the prefix `{p.prefix}`")
                taken[p.prefix] = p.module
            fronts = [p.module for p in made if p.home]
            if len(fronts) > 1:
                raise FolioError(f"{where}: view providers {', '.join(f'`{m}`' for m in fronts)} each ask for the "
                                 "site's front page; one may")
        except FolioError as err:
            lib._views_error = str(err)  # type: ignore[attr-defined]
            raise
        lib._views = made  # type: ignore[attr-defined]
    return made


def problem(lib: "Library") -> str | None:
    """Why the charter's providers cannot be loaded, for the gate; None when they can."""
    try:
        load(lib)
    except FolioError as err:
        text = str(err)
        lead = f"{lib.charter.path}: "
        return text[len(lead):] if text.startswith(lead) else text
    return None


def owner(lib: "Library", path: str) -> tuple[Provider, str] | None:
    """The provider a site path belongs to, and the path inside it."""
    path = path.split("#", 1)[0].split("?", 1)[0].lstrip("/")
    for provider in load(lib):
        if path == provider.prefix or path.startswith(provider.prefix + "/"):
            inner = path[len(provider.prefix):].strip("/")
            if inner == "index.html":
                inner = ""
            elif inner.endswith("/index.html"):
                inner = inner[: -len("/index.html")]
            return provider, inner
    return None


def resolves(lib: "Library", href: str) -> bool:
    """Whether a link from a document lands on a view. A provider that cannot be loaded, or that
    fails, answers nothing: the `views` check reports the first, the error stream the second."""
    if not href.startswith("/"):
        return False
    try:
        found = owner(lib, href)
        return found is not None and found[0].get(found[1]) is not None
    except FolioError:
        return False
    except Exception:
        found[0]._failed(f"get() for {href}")
        return False
