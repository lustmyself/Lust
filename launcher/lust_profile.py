#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profile background in the desktop hub.

League's profile page (Overview) shows a skin's splash art behind the player. The client
keeps the choice on Riot's servers through its local API, so it shows for friends who
open the profile too, and the client takes any skin's id there, owned or not.

The hub lists champions and their skins from CommunityDragon (as the Custom skins page
does) and sets the chosen skin through the client. Picked while League is closed, the
choice waits in Lust's data folder and is set the next time the client answers.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

CDRAGON = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"
CHAMPION_URL = CDRAGON + "v1/champions/{id}.json"
PROFILE_PATH = "/lol-summoner/v1/current-summoner/summoner-profile"
SKINS_TTL_S = 6 * 60 * 60
PENDING_FILE = "profile-background.json"

_lock = threading.Lock()
_skins: dict = {}  # champion id -> (fetched at, [skins])


def asset_url(path) -> str:
    """CommunityDragon's copy of a client asset path (/lol-game-data/assets/ASSETS/...)."""
    if not isinstance(path, str) or not path.startswith("/lol-game-data/assets/"):
        return ""
    return CDRAGON + path[len("/lol-game-data/assets/"):].lower()


def clean_skins(data) -> list:
    """[{id, name, tile, splash}] of a champion's skins, base first, tiered skins' tiers each."""
    result = []
    if not isinstance(data, dict):
        return result
    champion = data.get("name") if isinstance(data.get("name"), str) else ""
    for skin in data.get("skins") if isinstance(data.get("skins"), list) else []:
        if not isinstance(skin, dict):
            continue
        entries = [skin]
        tiers = (skin.get("questSkinInfo") or {}).get("tiers") if isinstance(skin.get("questSkinInfo"), dict) else None
        if isinstance(tiers, list) and tiers:
            entries = [t for t in tiers if isinstance(t, dict)] or [skin]
        for entry in entries:
            sid, name = entry.get("id"), entry.get("name")
            if not isinstance(sid, int) or sid <= 0 or not isinstance(name, str):
                continue
            if any(s["id"] == sid for s in result):
                continue
            result.append({
                "id": sid,
                "name": (champion if skin.get("isBase") and champion else name)[:60],
                "base": bool(skin.get("isBase")),
                "tile": asset_url(entry.get("tilePath") or skin.get("tilePath")),
                "splash": asset_url(entry.get("uncenteredSplashPath") or entry.get("splashPath")
                                    or skin.get("uncenteredSplashPath") or skin.get("splashPath")),
            })
    return result


def skins(champion_id) -> list:
    try:
        champion_id = int(champion_id)
    except (TypeError, ValueError):
        return []
    if champion_id <= 0:
        return []
    with _lock:
        cached = _skins.get(champion_id)
        if cached and time.monotonic() - cached[0] < SKINS_TTL_S:
            return cached[1]
    items = []
    try:
        import requests
        from config import APP_USER_AGENT
        response = requests.get(CHAMPION_URL.format(id=champion_id), timeout=8, headers={"User-Agent": APP_USER_AGENT})
        response.raise_for_status()
        items = clean_skins(response.json())
    except Exception as e:  # noqa: BLE001
        log.info(f"[Profile] Could not read the skins of champion {champion_id}: {e}")
    if items:
        with _lock:
            _skins[champion_id] = (time.monotonic(), items)
    return items


def skin(skin_id) -> Optional[dict]:
    """A skin by id; its champion is the id without the last three digits."""
    try:
        skin_id = int(skin_id)
    except (TypeError, ValueError):
        return None
    if skin_id <= 0:
        return None
    return next((s for s in skins(skin_id // 1000) if s["id"] == skin_id), None)


# ---- the client ----

def _lcu(method: str, path: str, body=None):
    """The client's answer as JSON, None when it isn't running or says no."""
    from launcher.lust_offline import _lcu_credentials
    creds = _lcu_credentials()
    if not creds:
        return None
    port, token = creds
    import requests
    try:
        response = requests.request(method, f"https://127.0.0.1:{port}{path}", auth=("riot", token), json=body,
                                    verify=False, timeout=5, proxies={"http": None, "https": None})
        response.raise_for_status()
        return response.json() if response.content else {}
    except (requests.RequestException, ValueError) as e:
        log.info(f"[Profile] {method} {path} failed: {e}")
        return None


def current() -> Optional[int]:
    """The background skin the client shows now, None while it isn't running."""
    profile = _lcu("GET", PROFILE_PATH)
    if not isinstance(profile, dict):
        return None
    try:
        return int(profile.get("backgroundSkinId") or 0)
    except (TypeError, ValueError):
        return 0


def _push(skin_id: int) -> bool:
    return _lcu("POST", PROFILE_PATH, {"key": "backgroundSkinId", "value": int(skin_id)}) is not None


# ---- the choice waiting for the client ----

def _pending_path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / PENDING_FILE


def pending() -> int:
    try:
        value = json.loads(_pending_path().read_text(encoding="utf-8")).get("pending")
        return value if isinstance(value, int) and value > 0 else 0
    except (OSError, ValueError, AttributeError):
        return 0


def _set_pending(skin_id: int) -> None:
    try:
        if skin_id:
            _pending_path().write_text(json.dumps({"pending": int(skin_id)}), encoding="utf-8")
        else:
            _pending_path().unlink(missing_ok=True)
    except OSError as e:
        log.warning(f"[Profile] Could not keep the background choice: {e}")


def apply_pending() -> None:
    """Set a background picked while League was closed (called once the client answers)."""
    skin_id = pending()
    if skin_id and _push(skin_id):
        _set_pending(0)
        log.info(f"[Profile] Background set to skin {skin_id}")


# ---- the hub ----

def listing() -> dict:
    """What the hub's Profile page shows."""
    from launcher import lust_skins
    now = current()
    waiting = pending()
    shown = waiting or now or 0
    return {
        "online": now is not None,
        "current": shown,
        "pending": bool(waiting),
        "skin": skin(shown) if shown else None,
        "champions": [{"id": c["id"], "name": c["name"]} for c in lust_skins.champions()],
    }


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


def dumps_skins(champion_id) -> bytes:
    return json.dumps({"skins": skins(champion_id)}, ensure_ascii=False).encode("utf-8")


def set_background(skin_id) -> str:
    try:
        skin_id = int(skin_id)
    except (TypeError, ValueError):
        return ""
    if skin_id <= 0:
        return ""
    from launcher.lust_offline import _lcu_credentials
    name = (skin(skin_id) or {}).get("name") or "Arka plan"
    if not _lcu_credentials():
        _set_pending(skin_id)
        return f"{name} seçildi: LoL açılınca profiline konur"
    if _push(skin_id):
        _set_pending(0)
        log.info(f"[Profile] Background set to skin {skin_id}")
        return f"Profil arka planı: {name}"
    return "LoL arka planı değiştiremedi, birazdan tekrar dene"
