#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom skins in the desktop hub.

The same files and switches as the "Custom skins" tab of the LUST panel in the client
(pengu/communication/lust_custom_skins.py): mod files in Lust's "custom skins" folder, each
switched on for one champion. The hub lists them, adds files dropped on the page, picks
the champion, switches them on and off, and deletes them.

The client's tab reads champion names from the client; the hub works without League, so it
reads them from CommunityDragon and keeps a copy for when it is offline.
"""

import json
import threading
import time
from pathlib import Path

from utils.core.logging import get_logger

log = get_logger()

CHAMPIONS_URL = ("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"
                 "v1/champion-summary.json")
CHAMPIONS_TTL_S = 6 * 60 * 60
CHAMPIONS_FILE = "lust-champions.json"

_lock = threading.Lock()
_champions: dict = {"at": 0.0, "items": []}

ERRORS = {
    "file is gone": "Bu dosya artık yok",
    "pick a champion first": "Önce şampiyonu seç",
    "file too large": "Dosya çok büyük",
    "upload interrupted": "Dosya yarım geldi",
}


def _custom():
    from pengu.communication import lust_custom_skins
    return lust_custom_skins


def clean_champions(data) -> list:
    """[{id, name, alias}] of real champions, by name."""
    result = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        cid, name, alias = item.get("id"), item.get("name"), item.get("alias")
        if isinstance(cid, int) and cid > 0 and isinstance(name, str) and isinstance(alias, str) and alias:
            result.append({"id": cid, "name": name[:40], "alias": alias.lower()})
    return sorted(result, key=lambda c: c["name"].casefold())


def _cache_path() -> Path:
    return _custom().folder() / CHAMPIONS_FILE


def champions() -> list:
    with _lock:
        if _champions["items"] and time.monotonic() - _champions["at"] < CHAMPIONS_TTL_S:
            return _champions["items"]
    items = []
    try:
        import requests
        from config import APP_USER_AGENT
        response = requests.get(CHAMPIONS_URL, timeout=8, headers={"User-Agent": APP_USER_AGENT})
        response.raise_for_status()
        items = clean_champions(response.json())
        if items:
            try:
                _cache_path().write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
    except Exception as e:  # noqa: BLE001
        log.info(f"[Skins] Could not read the champion list: {e}")
    if not items:
        try:
            items = clean_champions(json.loads(_cache_path().read_text(encoding="utf-8")))
        except (OSError, ValueError):
            items = []
    with _lock:
        # Without a list, try again in a minute instead of hours
        _champions.update(at=time.monotonic() - (0 if items else CHAMPIONS_TTL_S - 60), items=items)
    return items


def listing() -> dict:
    """What the hub's Skins page shows."""
    custom = _custom()
    champs = champions()
    by_alias = {c["alias"]: c for c in champs}
    by_id = {c["id"]: c for c in champs}
    skins = custom.list_skins()
    # A skin whose WAD names its champion gets that champion by itself, as in the client
    guessed = False
    for skin in skins:
        if skin["championId"] or skin["broken"] or skin.get("auto") is False:
            continue
        match = next((by_alias[w] for w in skin["wads"] if w in by_alias), None)
        if match:
            custom._set(skin["name"], None, match["id"])
            guessed = True
    if guessed:
        skins = custom.list_skins()
    try:
        from launcher.lust_settings import enabled
        on = enabled("custom_skins")
    except Exception:  # noqa: BLE001
        on = True
    return {
        "skins": [{
            "name": s["name"],
            "title": s["title"],
            "size": s["size"],
            "broken": s["broken"],
            "championId": s["championId"],
            "champion": (by_id.get(s["championId"]) or {}).get("name", ""),
            "enabled": s["enabled"],
            "status": s.get("status", "new"),
            "made": s.get("made"),
        } for s in skins],
        "champions": [{"id": c["id"], "name": c["name"]} for c in champs],
        "on": on,
    }


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


# ---- actions ----

def _message(error: str) -> str:
    return ERRORS.get(error, error)


def _entry(name: str) -> dict:
    return next((s for s in _custom().list_skins() if s["name"] == name), {})


def toggle(name: str, enabled: bool) -> str:
    error = _custom()._set(name, bool(enabled), None)
    if error:
        return _message(error)
    if not enabled:
        return ""
    state = _entry(name).get("status")
    if state == "crashed":
        return "Açıldı, ama bu skin bu yamada oyunu çökertmişti. Yine çökerse Lust onu kendisi kapatır."
    if state in ("old", "untested"):
        return "Açıldı. Bu yamada denenmedi: oyun açılmazsa Lust onu kendisi kapatır."
    return "Skin açıldı: o şampiyonun varsayılan skiniyle girince yüklenir"


def search_update(name: str) -> str:
    """Look the skin up on the web, for a version made for the current patch."""
    from urllib.parse import quote_plus
    import webbrowser
    entry = _entry(name)
    if not entry:
        return ""
    title = entry.get("title") or Path(name).stem
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(f"{title} league of legends custom skin runeforge"))
    return ""


def set_champion(name: str, champion_id) -> str:
    try:
        champion_id = int(champion_id or 0)
    except (TypeError, ValueError):
        return ""
    return _message(_custom()._set(name, None, max(champion_id, 0)))


def delete(name: str) -> str:
    custom = _custom()
    if not custom._valid_name(name):
        return ""
    path = custom.folder() / name
    try:
        path.unlink()
    except FileNotFoundError:
        return ""
    except OSError as e:
        log.warning(f"[Skins] Could not delete {name}: {e}")
        return "Silinemedi (oyunda kullanılıyor olabilir)"
    custom.list_skins()  # forgets the file's switches
    log.info(f"[Skins] Deleted {name}")
    return f"{Path(name).stem} silindi"


def import_upload(name: str, stream, length: int) -> str:
    """A file dropped on the hub page, streamed in from the hub server."""
    custom = _custom()
    name = Path(name or "").name.strip()
    if not custom._valid_name(name):
        return "Yalnızca .zip, .fantome ve .modpkg dosyaları eklenebilir"
    if not 0 < length <= custom.MAX_FILE_BYTES:
        return "Dosya çok büyük"
    folder = custom.folder()
    part = folder / f".{name}.part"
    try:
        left = length
        with part.open("wb") as handle:
            while left > 0:
                chunk = stream.read(min(left, 1024 * 1024))
                if not chunk:
                    return "Dosya yarım geldi"
                handle.write(chunk)
                left -= len(chunk)
        part.replace(folder / name)
        log.info(f"[Skins] Added {name}")
        return f"{Path(name).stem} eklendi"
    except OSError as e:
        log.warning(f"[Skins] Could not add {name}: {e}")
        return f"Eklenemedi: {e}"
    finally:
        part.unlink(missing_ok=True)


def open_folder() -> str:
    from utils.core.paths import open_folder_in_explorer
    open_folder_in_explorer(_custom().folder())
    return ""
