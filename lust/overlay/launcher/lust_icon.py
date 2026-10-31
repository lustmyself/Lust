#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profile icon in the desktop hub: any summoner icon, owned or not, on the player's own screen.

Riot's servers only take an icon the account owns, so this never reaches them: the
LUST-ProfileIcon plugin swaps the icon id in what the client reads about the player
(current summoner, chat, lobby) and the client draws the chosen icon from its own files.
Friends and other players keep seeing the real icon.

The hub lists every icon from CommunityDragon; the choice waits in Lust's data folder and
the plugin asks for it over the bridge ("lust-profile-icon").
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
ICONS_URL = CDRAGON + "v1/summoner-icons.json"
ICONS_TTL_S = 6 * 60 * 60
CHOICE_FILE = "profile-icon.json"

_lock = threading.Lock()
_icons: tuple = (0.0, [])  # (fetched at, [icons])


def image_url(icon_id: int) -> str:
    return CDRAGON + f"v1/profile-icons/{int(icon_id)}.jpg"


def clean_icons(data) -> list:
    """[{id, title, year}] of every icon, newest first."""
    result, seen = [], set()
    for icon in data if isinstance(data, list) else []:
        if not isinstance(icon, dict):
            continue
        icon_id = icon.get("id")
        if not isinstance(icon_id, int) or isinstance(icon_id, bool) or icon_id < 0 or icon_id in seen:
            continue
        seen.add(icon_id)
        title = icon.get("title") if isinstance(icon.get("title"), str) else ""
        year = icon.get("yearReleased") if isinstance(icon.get("yearReleased"), int) else 0
        result.append({"id": icon_id, "title": title.strip()[:80] or f"Simge #{icon_id}", "year": year})
    result.sort(key=lambda i: i["id"], reverse=True)
    return result


def icons() -> list:
    global _icons
    with _lock:
        fetched, cached = _icons
        if cached and time.monotonic() - fetched < ICONS_TTL_S:
            return cached
    items = []
    try:
        import requests
        from config import APP_USER_AGENT
        response = requests.get(ICONS_URL, timeout=10, headers={"User-Agent": APP_USER_AGENT})
        response.raise_for_status()
        items = clean_icons(response.json())
    except Exception as e:  # noqa: BLE001
        log.info(f"[Icon] Could not read the icon list: {e}")
    if items:
        with _lock:
            _icons = (time.monotonic(), items)
    return items or cached


def icon(icon_id) -> Optional[dict]:
    try:
        icon_id = int(icon_id)
    except (TypeError, ValueError):
        return None
    return next((i for i in icons() if i["id"] == icon_id), None)


# ---- the choice ----

def _choice_path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / CHOICE_FILE


def chosen() -> int:
    """The icon the client shows instead of the real one, 0 for the real one."""
    try:
        value = json.loads(_choice_path().read_text(encoding="utf-8")).get("iconId")
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
    except (OSError, ValueError, AttributeError):
        return 0


def _save(icon_id: int) -> bool:
    try:
        if icon_id:
            _choice_path().write_text(json.dumps({"iconId": int(icon_id)}), encoding="utf-8")
        else:
            _choice_path().unlink(missing_ok=True)
        return True
    except OSError as e:
        log.warning(f"[Icon] Could not keep the icon choice: {e}")
        return False


def choose(icon_id) -> str:
    try:
        icon_id = int(icon_id)
    except (TypeError, ValueError):
        return ""
    if icon_id < 0:
        return ""
    if not _save(icon_id):
        return "Simge kaydedilemedi"
    if not icon_id:
        log.info("[Icon] Back to the account's own icon")
        return "Kendi simgene dönüldü"
    log.info(f"[Icon] Profile icon set to {icon_id}")
    name = (icon(icon_id) or {}).get("title") or f"Simge #{icon_id}"
    return f"Profil simgesi: {name}"


# ---- challenge tokens ----

TOKENS_PATH = "/lol-challenges/v1/update-player-preferences/"


def clear_tokens() -> str:
    """Take the challenge tokens off the profile (saved on Riot's side, like the client's own editor)."""
    from launcher.lust_offline import _lcu_credentials
    from launcher.lust_profile import _lcu
    if not _lcu_credentials():
        return "Tokenleri kaldırmak için LoL açık olmalı"
    if _lcu("POST", TOKENS_PATH, {"challengeIds": []}) is None:
        return "LoL tokenleri kaldıramadı, birazdan tekrar dene"
    log.info("[Icon] Challenge tokens cleared")
    return "Tokenler kaldırıldı"


# ---- the hub and the plugin ----

def listing() -> dict:
    current = chosen()
    return {"chosen": current, "icon": icon(current) if current else None, "icons": icons()}


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


def bridge_reply() -> dict:
    """What LUST-ProfileIcon asks for over the bridge."""
    return {"type": "lust-profile-icon", "iconId": chosen()}
