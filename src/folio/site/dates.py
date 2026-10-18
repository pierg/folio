"""`created` and `updated` for each file, from git history. Nobody writes them."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_MARK = "\x01"


def from_git(library: Path) -> dict[str, dict[str, str]]:
    """Each path (from the library root) mapped to its first and last commit dates.

    A library outside git, or a file never committed, has no entry: the shell
    then shows no dates rather than invented ones.
    """
    if shutil.which("git") is None:
        return {}
    inside = subprocess.run(["git", "-C", str(library), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True)
    if inside.returncode != 0:
        return {}
    log = subprocess.run(
        ["git", "-C", str(library), "log", f"--format={_MARK}%as", "--name-only", "--relative",
         "--no-renames", "--", "."],
        capture_output=True, text=True, check=True,
    )
    out: dict[str, dict[str, str]] = {}
    date = ""
    for line in log.stdout.splitlines():
        if line.startswith(_MARK):
            date = line[1:]
        elif line.strip():
            entry = out.setdefault(line.strip(), {"created": date, "updated": date})
            entry["created"] = date  # the log runs newest first, so the last seen is the first commit
    return out
