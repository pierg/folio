"""`folio config` and `folio pack`: reading and changing the charter."""

from __future__ import annotations

from typing import Any

import yaml

from .. import charter as charter_mod
from .. import indexer
from .. import library as library_mod
from ..charter import CHARTER
from ..errors import FolioError
from ..library import Library


def _show(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return yaml.safe_dump(value, sort_keys=False, default_flow_style=True, width=1000).strip()
    return str(value)


def get(lib: Library, key: str | None) -> str:
    effective = lib.charter.effective()
    if key is None:
        return yaml.safe_dump(effective, sort_keys=False, allow_unicode=True, width=1000).rstrip()
    value = charter_mod.get_key(effective, key)
    if isinstance(value, (dict, list)):
        return yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=1000).rstrip()
    return str(value)


def _commit(lib: Library, raw: dict[str, Any], key: str) -> list[str]:
    """Write the new charter in place, keeping its order and comments where it can.

    The old charter comes back if the library no longer loads. The indices
    are rewritten, since the charter's name and packs show in them.
    """
    path = lib.root / CHARTER
    charter_mod.parse(raw, path)
    before = path.read_text(encoding="utf-8")
    charter_mod.write_key(path, raw, key, charter_mod.get_key(raw, key))
    try:
        new = library_mod.load_at(lib.root)
    except FolioError:
        path.write_text(before, encoding="utf-8")
        raise
    return [f"wrote {p}" for p in indexer.write(new)]


def set_value(lib: Library, key: str, value: str) -> str:
    typed = charter_mod.coerce(key, value)
    try:
        old = charter_mod.get_key(lib.charter.effective(), key)
    except FolioError:
        old = None
    indices = _commit(lib, charter_mod.set_key(lib.charter.raw, key, typed), key)
    return "\n".join([f"updated {CHARTER}: {key}: {_show(old)} -> {_show(typed)}", *indices])


def pack_list(lib: Library) -> list[dict[str, Any]]:
    return [
        {"name": p.name, "on": p.on, "source": p.source, "version": p.version,
         "purpose": p.purpose, "genres": p.genres, "workflows": p.workflows,
         "journal_kinds": p.journal_kinds}
        for p in sorted(lib.registry.packs.values(), key=lambda p: p.name)
    ]


def pack_on(lib: Library, name: str) -> str:
    if name not in lib.registry.packs:
        raise FolioError(f"no pack `{name}`; `folio pack list` shows them")
    if name in lib.charter.pack_names:
        return f"pack `{name}` is already on"
    raw = charter_mod.set_key(lib.charter.raw, "packs", list(lib.charter.raw.get("packs") or []) + [name])
    indices = _commit(lib, raw, "packs")
    return "\n".join([f"updated {CHARTER}: switched pack `{name}` on", *indices])


def pack_off(lib: Library, name: str) -> str:
    if name not in lib.charter.pack_names:
        raise FolioError(f"pack `{name}` is not on")
    kept = [p for p in lib.charter.raw.get("packs") or []
            if (p if isinstance(p, str) else p.get("name")) != name]
    indices = _commit(lib, charter_mod.set_key(lib.charter.raw, "packs", kept), "packs")
    return "\n".join([f"updated {CHARTER}: switched pack `{name}` off", *indices])
