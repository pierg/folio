"""Who is commenting. A reader never types a name: the server knows it.

Locally the commenter is the library repository's `git config user.name`
(the operating-system user outside git). On a deployed server the host's
sign-in proxy names the reader in a request header, and the charter's
`comments.identity_header` says which. A server on a public address with
no such header configured, or a request that lacks it, takes no comments.
"""

from __future__ import annotations

import getpass
import ipaddress
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

LOOPBACK_NAMES = ("localhost",)


@dataclass(frozen=True)
class Who:
    name: str
    email: str = ""


def is_loopback(host: str) -> bool:
    """True when the address only this machine can reach: 127.0.0.1, ::1, localhost."""
    host = host.strip("[]")
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _git_config(root: Path, key: str) -> str:
    if shutil.which("git") is None:
        return ""
    result = subprocess.run(["git", "-C", str(root), "config", key], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def local(root: Path) -> Who:
    """The person at this machine: git's user.name and user.email, else the operating-system user."""
    name = _git_config(root, "user.name")
    if name:
        return Who(name, _git_config(root, "user.email"))
    try:
        return Who(getpass.getuser())
    except (KeyError, OSError):
        return Who("")


def from_header(value: str) -> Who:
    """The reader a sign-in proxy names: a user name or an email address."""
    value = value.strip()
    return Who(value, value if "@" in value else "")


@dataclass(frozen=True)
class Policy:
    """Whether this server takes comments, and from whom.

    `header` is the charter's `comments.identity_header` (empty when unset).
    """

    root: Path
    host: str
    header: str

    @property
    def public(self) -> bool:
        return not is_loopback(self.host)

    def refusal(self) -> str | None:
        """Why this server takes no comments at all, or None when it may."""
        if self.public and not self.header:
            return ("Comments are read-only here: this library is served on a public address and "
                    "folio.yaml names no comments.identity_header, so the server cannot tell who is writing.")
        return None

    def who(self, headers: Mapping[str, str]) -> tuple[Who | None, str | None]:
        """The commenter of one request, or None and the reason a comment is refused."""
        refusal = self.refusal()
        if refusal:
            return None, refusal
        if self.header:
            value = (headers.get(self.header) or "").strip()
            if value:
                return from_header(value), None
            if self.public:
                return None, (f"Comments are read-only for you: the request carries no {self.header} "
                              "header, so you are not signed in.")
        who = local(self.root)
        if not who.name:
            return None, "Comments are read-only: no git user.name and no operating-system user to write as."
        return who, None
