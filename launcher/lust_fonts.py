#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fonts in the desktop hub.

Font mods live in %LOCALAPPDATA%\\Lust\\mods\\fonts, the folder the client's custom mod panel
lists (its Fonts tab). The hub shows them, adds new ones (a file dropped on the page) and picks
the one the next game uses. The pick is the saved font choice (mod_historic "font") the
injection reads.

Lust ships one font, the Korean UttumDotum mod (assets/lust_fonts). It is added and picked once
on a fresh install, so it is the default; after that the user's choice stands, even "League's own".
"""

import json
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

CATEGORY = "fonts"
HISTORIC_KEY = "font"
MAX_FONT_BYTES = 200 * 1024 * 1024
DEFAULT_FILE = "korean-uttumdotum.fantome"
DEFAULT_NAME = "Korean (UttumDotum)"
MARKER = "lust_fonts.json"  # in Lust's user data folder: {"default_added": true}

_state = None
_lock = threading.Lock()


def attach_state(state) -> None:
    global _state
    _state = state


def _storage():
    from injection.mods.storage import ModStorageService
    return ModStorageService()


def _selected() -> Optional[str]:
    try:
        from utils.core.mod_historic import get_historic_mod
        value = get_historic_mod(HISTORIC_KEY)
        return value.replace("\\", "/") if isinstance(value, str) and value else None
    except Exception:  # noqa: BLE001
        return None


def _bundled() -> Path:
    from utils.core.paths import get_asset_path
    return get_asset_path(f"lust_fonts/{DEFAULT_FILE}")


def _marker_path() -> Path:
    from utils.core.paths import get_user_data_dir
    return Path(get_user_data_dir()) / MARKER


def _marker() -> dict:
    try:
        data = json.loads(_marker_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_marker(data: dict) -> None:
    from utils.core.atomic_file import atomic_write
    path = _marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_write(path) as handle:
        json.dump(data, handle)


def _default_id(storage) -> Optional[str]:
    for entry in storage.list_mods_for_category(CATEGORY):
        if (entry.get("displayName") or entry.get("name")) == DEFAULT_NAME:
            return entry["id"]
    return None


def ensure_default() -> None:
    """On a fresh install: add the bundled Korean font and pick it, once."""
    with _lock:
        if _marker().get("default_added"):
            return
        try:
            storage = _storage()
            font_id = _default_id(storage)
            if font_id is None:
                source = _bundled()
                if not source.is_file():
                    log.info("[Fonts] The bundled default font is missing; nothing to add")
                    return
                import_file(source, display_name=DEFAULT_NAME)
                font_id = _default_id(storage)
            if font_id and not _selected():
                from utils.core.mod_historic import write_historic_mod
                write_historic_mod(HISTORIC_KEY, font_id)
                log.info(f"[Fonts] Default font picked: {font_id}")
            _write_marker({"default_added": True})
        except Exception as e:  # noqa: BLE001
            log.warning(f"[Fonts] Could not add the default font: {e}")


def installed() -> list:
    storage = _storage()
    chosen = _selected()
    default_id = _default_id(storage)
    return [{
        "id": entry["id"],
        "name": entry.get("displayName") or entry["name"],
        "description": entry.get("description") or "",
        "selected": entry["id"] == chosen,
        "lust": entry["id"] == default_id,
    } for entry in storage.list_mods_for_category(CATEGORY)]


def listing() -> dict:
    """What the hub's Fonts page shows."""
    ensure_default()
    return {"installed": installed(), "selected": _selected()}


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


# ---- actions ----

def select(font_id: Optional[str]) -> str:
    """The font the next game uses (None: League's own)."""
    from utils.core.mod_historic import clear_historic_mod, write_historic_mod
    if not font_id:
        clear_historic_mod(HISTORIC_KEY)
        if _state is not None:
            _state.selected_font_mod = None
        return "Font: League'in kendi fontu"
    entry = next((f for f in installed() if f["id"] == font_id), None)
    if entry is None:
        return "Bu font artık yok"
    write_historic_mod(HISTORIC_KEY, font_id)
    if _state is not None:
        _state.selected_font_mod = None  # the injection takes the saved choice at the next game
    log.info(f"[Fonts] Font for the next game: {font_id}")
    return f"Sonraki maçta font: {entry['name']}"


def delete(font_id: str) -> str:
    entry = next((f for f in installed() if f["id"] == font_id), None)
    if entry is None:
        return ""
    if entry["selected"]:
        select(None)
    name = font_id.split("/", 1)[-1]
    return f"{entry['name']} silindi" if _storage().delete_category_mod(CATEGORY, name) else "Silinemedi"


def import_file(path: Path, display_name: Optional[str] = None) -> str:
    """Add a font mod archive (.zip, .fantome, .modpkg) to the fonts folder."""
    storage = _storage()
    _target, mod_name = storage.import_category_mod_file(CATEGORY, path)
    if display_name:
        try:
            storage.set_category_mod_display_name(CATEGORY, mod_name, display_name)
        except Exception as e:  # noqa: BLE001
            log.debug(f"[Fonts] Could not name {mod_name}: {e}")
    log.info(f"[Fonts] Added font mod {mod_name}")
    return mod_name


def import_upload(name: str, stream, length: int) -> str:
    """A file dropped on the hub page, streamed in from the hub server."""
    suffix = Path(name or "").suffix.lower()
    if suffix not in (".zip", ".fantome", ".modpkg"):
        return "Yalnızca .zip, .fantome ve .modpkg dosyaları eklenebilir"
    if not 0 < length <= MAX_FONT_BYTES:
        return "Dosya çok büyük"
    work = Path(tempfile.mkdtemp(prefix="lust-font-"))
    try:
        target = work / (Path(name).stem.strip()[:80] + suffix)
        left = length
        with target.open("wb") as handle:
            while left > 0:
                chunk = stream.read(min(left, 1024 * 1024))
                if not chunk:
                    return "Dosya yarım geldi"
                handle.write(chunk)
                left -= len(chunk)
        mod_name = import_file(target)
        return f"{mod_name} eklendi"
    except (OSError, ValueError) as e:
        log.warning(f"[Fonts] Could not add {name}: {e}")
        return f"Eklenemedi: {e}"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def open_folder() -> str:
    import os
    import sys
    folder = _storage().mods_root / CATEGORY
    if sys.platform == "win32":
        os.startfile(folder)
    return ""
