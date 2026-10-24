#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map skins in the desktop hub.

Map mods live in %LOCALAPPDATA%\\Lust\\mods\\maps, the same folder the client's custom mod
panel lists (its Maps tab). The hub shows them with their preview, adds new ones (a file
picked or dropped on the page, or one from Lust's map catalog) and picks the one the next
game uses. The pick is the saved map choice (mod_historic "map") the injection reads.

The catalog is lust/maps.json in Lust's repo, read at runtime: each entry names a .zip,
.fantome or .modpkg by https URL and SHA-256, so only files the catalog vouches for are
installed. Only maps whose authors allow redistribution belong there.
"""

import hashlib
import json
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

CATEGORY = "maps"
CATALOG_URL = "https://raw.githubusercontent.com/lustmyself/Lust/main/lust/maps.json"
CATALOG_TTL_S = 30 * 60
MAX_MAP_BYTES = 600 * 1024 * 1024
PREVIEW_NAMES = ("preview.png", "preview.jpg", "preview.jpeg", "preview.webp",
                 "META/image.png", "META/image.jpg", "image.png", "image.jpg")
PREVIEW_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

_state = None  # Lust's shared state, so a pick made here replaces one made in the client
_lock = threading.Lock()
_catalog: dict = {"at": 0.0, "items": []}
_installing: set = set()


def attach_state(state) -> None:
    global _state
    _state = state


def _storage():
    from injection.mods.storage import ModStorageService
    return ModStorageService()


def _selected() -> Optional[str]:
    try:
        from utils.core.mod_historic import get_historic_mod
        value = get_historic_mod("map")
        return value.replace("\\", "/") if isinstance(value, str) and value else None
    except Exception:  # noqa: BLE001
        return None


def preview_path(storage, map_id: str) -> Optional[Path]:
    """The preview image inside an installed map mod, when it has one."""
    for entry in storage.list_mods_for_category(CATEGORY):
        if entry.get("id") != map_id:
            continue
        folder = storage.mods_root / entry["path"]
        for name in PREVIEW_NAMES:
            candidate = folder / name
            if candidate.is_file() and candidate.suffix.lower() in PREVIEW_TYPES:
                return candidate
    return None


def installed() -> list:
    storage = _storage()
    chosen = _selected()
    maps = []
    for entry in storage.list_mods_for_category(CATEGORY):
        maps.append({
            "id": entry["id"],
            "name": entry.get("displayName") or entry["name"],
            "description": entry.get("description") or "",
            "preview": preview_path(storage, entry["id"]) is not None,
            "selected": entry["id"] == chosen,
        })
    return maps


# ---- catalog ----

def _is_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def clean_catalog(data) -> list:
    """The catalog's usable entries: https files with a SHA-256, https previews only."""
    items = data.get("maps") if isinstance(data, dict) else None
    result, seen = [], set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key, url = item.get("id"), item.get("url")
        if not (isinstance(key, str) and key.replace("-", "").replace("_", "").isalnum() and len(key) <= 64):
            continue
        if not (isinstance(url, str) and url.startswith("https://") and _is_sha256(item.get("sha256"))):
            continue
        if key in seen:
            continue
        seen.add(key)
        preview = item.get("preview")
        result.append({
            "id": key,
            "name": str(item.get("name") or key)[:80],
            "description": str(item.get("description") or "")[:300],
            "author": str(item.get("author") or "")[:80],
            "preview": preview if isinstance(preview, str) and preview.startswith("https://") else "",
            "url": url,
            "sha256": item["sha256"].lower(),
            "file": "map." + (url.rsplit(".", 1)[-1].lower() if url.lower().endswith((".zip", ".fantome", ".modpkg"))
                              else "zip"),
        })
    return result


def catalog(refresh: bool = False) -> list:
    with _lock:
        if not refresh and _catalog["at"] and time.monotonic() - _catalog["at"] < CATALOG_TTL_S:
            return _catalog["items"]
    try:
        import requests
        from config import APP_USER_AGENT
        response = requests.get(CATALOG_URL, timeout=8, headers={"User-Agent": APP_USER_AGENT})
        response.raise_for_status()
        items = clean_catalog(response.json())
    except Exception as e:  # noqa: BLE001
        log.info(f"[Maps] Could not read the map catalog: {e}")
        with _lock:
            items = _catalog["items"]
    with _lock:
        _catalog.update(at=time.monotonic(), items=items)
    return items


def listing() -> dict:
    """What the hub's Map page shows."""
    maps = installed()
    names = {m["name"].casefold() for m in maps}
    items = [dict(item, installed=item["name"].casefold() in names, installing=item["id"] in _installing)
             for item in catalog()]
    for item in items:
        item.pop("url", None), item.pop("sha256", None), item.pop("file", None)
    return {"installed": maps, "catalog": items, "selected": _selected()}


# ---- actions ----

def select(map_id: Optional[str]) -> str:
    """The map the next game uses (None: League's own)."""
    from utils.core.mod_historic import clear_historic_mod, write_historic_mod
    if not map_id:
        clear_historic_mod("map")
        if _state is not None:
            _state.selected_map_mod = None
        return "Harita: League'in kendi haritası"
    entry = next((m for m in installed() if m["id"] == map_id), None)
    if entry is None:
        return "Bu harita artık yok"
    write_historic_mod("map", map_id)
    if _state is not None:
        _state.selected_map_mod = None  # the injection takes the saved choice at the next game
    log.info(f"[Maps] Map skin for the next game: {map_id}")
    return f"Sonraki maçta harita: {entry['name']}"


def delete(map_id: str) -> str:
    entry = next((m for m in installed() if m["id"] == map_id), None)
    if entry is None:
        return ""
    if entry["selected"]:
        select(None)
    name = map_id.split("/", 1)[-1]
    return f"{entry['name']} silindi" if _storage().delete_category_mod(CATEGORY, name) else "Silinemedi"


def import_file(path: Path, display_name: Optional[str] = None) -> str:
    """Add a map mod archive (.zip, .fantome, .modpkg) to the maps folder."""
    storage = _storage()
    _target, mod_name = storage.import_category_mod_file(CATEGORY, path)
    if display_name:
        try:
            storage.set_category_mod_display_name(CATEGORY, mod_name, display_name)
        except Exception as e:  # noqa: BLE001
            log.debug(f"[Maps] Could not name {mod_name}: {e}")
    log.info(f"[Maps] Added map mod {mod_name}")
    return mod_name


def import_upload(name: str, stream, length: int) -> str:
    """A file dropped on the hub page, streamed in from the hub server."""
    suffix = Path(name or "").suffix.lower()
    if suffix not in (".zip", ".fantome", ".modpkg"):
        return "Yalnızca .zip, .fantome ve .modpkg dosyaları eklenebilir"
    if not 0 < length <= MAX_MAP_BYTES:
        return "Dosya çok büyük"
    work = Path(tempfile.mkdtemp(prefix="lust-map-"))
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
        log.warning(f"[Maps] Could not add {name}: {e}")
        return f"Eklenemedi: {e}"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def install(catalog_id: str) -> str:
    """Download a catalog map, check its SHA-256 and add it."""
    item = next((i for i in catalog() if i["id"] == catalog_id), None)
    if item is None:
        return "Bu harita katalogda yok"
    with _lock:
        if catalog_id in _installing:
            return ""
        _installing.add(catalog_id)
    work = Path(tempfile.mkdtemp(prefix="lust-map-"))
    try:
        import requests
        from config import APP_USER_AGENT
        target = work / item["file"].replace("map", catalog_id, 1)
        digest = hashlib.sha256()
        size = 0
        with requests.get(item["url"], stream=True, timeout=30, headers={"User-Agent": APP_USER_AGENT}) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_MAP_BYTES:
                        return "Dosya çok büyük"
                    digest.update(chunk)
                    handle.write(chunk)
        if digest.hexdigest() != item["sha256"]:
            log.warning(f"[Maps] {catalog_id}: SHA-256 does not match the catalog; not installed")
            return "İndirilen dosya katalogla eşleşmiyor; kurulmadı"
        import_file(target, display_name=item["name"])
        return f"{item['name']} kuruldu"
    except Exception as e:  # noqa: BLE001
        log.warning(f"[Maps] Could not install {catalog_id}: {e}")
        return "Harita indirilemedi"
    finally:
        with _lock:
            _installing.discard(catalog_id)
        shutil.rmtree(work, ignore_errors=True)


def preview_bytes(map_id: str) -> Optional[tuple]:
    """(bytes, content type) of an installed map's preview."""
    path = preview_path(_storage(), map_id)
    if path is None:
        return None
    try:
        return path.read_bytes(), PREVIEW_TYPES[path.suffix.lower()]
    except OSError:
        return None


def open_folder() -> str:
    import os
    import sys
    folder = _storage().mods_root / CATEGORY
    if sys.platform == "win32":
        os.startfile(folder)
    return ""


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")
