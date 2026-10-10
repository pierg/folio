"""A deck as a PDF: its slides as the page draws them, one per page, rendered by headless Chrome.

The shell's print styles lay a deck out at 1600 by 900, one slide per page,
every build shown. Chrome prints the served page with those styles. `folio
serve` renders on request (`/_folio/pdf?doc=...`); `folio export` renders each
deck once and publishes the PDF beside it.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from ..errors import FolioError
from ..library import Library

ENV = "FOLIO_CHROME"
NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
MAC_APPS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
WAIT_MS = 8000  # how long the page's script may run before the PDF is taken
TIMEOUT = 120   # seconds before a render is given up


def find_chrome() -> str | None:
    """The Chrome or Chromium to render with: $FOLIO_CHROME, then the usual names and places."""
    named = os.environ.get(ENV)
    if named:
        if not Path(named).is_file():
            raise FolioError(f"{ENV}={named} is not a file")
        return named
    for name in NAMES:
        found = shutil.which(name)
        if found:
            return found
    for app in MAC_APPS:
        if Path(app).is_file():
            return app
    return None


def missing() -> str:
    return (f"a deck's PDF needs Chrome or Chromium, which was not found; install one or set {ENV} "
            "to its executable")


def decks(lib: Library) -> list:
    return [d for d in lib.documents if d.is_a("deck")]


def site_path(doc) -> str:
    """Where a deck's PDF is published: `<id>.pdf` beside the deck's page."""
    return doc.key.rsplit("/", 1)[0] + "/" + doc.id + ".pdf"


def render(url: str, dest: Path, chrome: str | None = None) -> None:
    """Print the page at `url` to `dest` with headless Chrome; fail loud when no PDF comes out."""
    chrome = chrome or find_chrome()
    if chrome is None:
        raise FolioError(missing())
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Headless Chrome keeps its own temporary profile; a fresh --user-data-dir makes it hang on exit.
    command = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               f"--virtual-time-budget={WAIT_MS}", f"--print-to-pdf={dest}", url]
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise FolioError(f"{url}: Chrome ran for more than {TIMEOUT} s and was stopped") from exc
    if not dest.is_file() or dest.stat().st_size == 0:
        tail = "\n".join((run.stderr or "").strip().splitlines()[-5:])
        raise FolioError(f"{url}: Chrome wrote no PDF (exit {run.returncode})" + (f":\n{tail}" if tail else ""))


def fingerprint(lib: Library, doc, shell: Path) -> str:
    """What a deck's PDF depends on: its file and the shell that draws it."""
    h = hashlib.sha256()
    for path in [doc.address_file.abspath, shell / "folio.css", shell / "folio.js"]:
        h.update(Path(path).read_bytes())
    return h.hexdigest()[:16]
