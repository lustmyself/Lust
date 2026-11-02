#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skin sharing with friends in the desktop hub.

Lust remembers the last skin (or chroma) used on each champion in historic.json, and
puts it on again the next time that champion is locked in with the default skin. The
Share page turns that list into a short code ("LUST-...") a friend pastes into their own
Lust: they see the skins, tick the champions they want, and those go into their own
historic.json. No server is involved; everything is inside the code.

Custom skins ("path:..." entries) stay out: the friend may not have the same file.

Code layout (before base64url): version byte (1), name length + UTF-8 name (the sender's
Riot name, at most 16 bytes), then per champion, sorted by id, the champion id as the
difference from the previous one and the skin's number (skin id - champion id * 1000),
both as varints; last, one check byte (crc32 & 0xff).
"""

from __future__ import annotations

import base64
import json
import zlib
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

PREFIX = "LUST-"
VERSION = 1
NAME_BYTES = 16
MAX_ENTRIES = 200


# ---- the code ----

def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= len(data) or shift > 28:
            raise ValueError("cut short")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def _clean(skins) -> dict:
    """{champion id: skin id} from {champion: skin} or a list of skin ids; bad ones dropped."""
    pairs = skins.items() if isinstance(skins, dict) else ((None, s) for s in skins or [])
    result = {}
    for champion, skin in pairs:
        try:
            skin = int(skin)
            champion = int(champion) if champion is not None else skin // 1000
        except (TypeError, ValueError):
            continue
        if champion > 0 and skin // 1000 == champion and skin % 1000 > 0:
            result[champion] = skin
    return result


def encode(skins, name: str = "") -> str:
    """The share code of {champion id: skin id} (or a list of skin ids). Default skins are left out."""
    entries = sorted(_clean(skins).items())[:MAX_ENTRIES]
    raw = (name or "").strip().encode("utf-8")[:NAME_BYTES].decode("utf-8", "ignore").encode("utf-8")
    body = bytearray([VERSION, len(raw)]) + raw
    previous = 0
    for champion, skin in entries:
        body += _varint(champion - previous) + _varint(skin - champion * 1000)
        previous = champion
    body.append(zlib.crc32(bytes(body)) & 0xFF)
    return PREFIX + base64.urlsafe_b64encode(bytes(body)).decode("ascii").rstrip("=")


def decode(code: str) -> Optional[dict]:
    """{"name", "skins": {champion id: skin id}} of a share code, or None when it is not one."""
    if not isinstance(code, str):
        return None
    text = "".join(code.split())
    at = text.upper().find(PREFIX)
    if at < 0:
        return None
    text = text[at + len(PREFIX):]
    try:
        data = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (ValueError, TypeError):
        return None
    if len(data) < 3 or data[0] != VERSION or zlib.crc32(data[:-1]) & 0xFF != data[-1]:
        return None
    data = data[:-1]
    size = data[1]
    if 2 + size > len(data):
        return None
    name = data[2:2 + size].decode("utf-8", "replace")
    skins, pos, champion = {}, 2 + size, 0
    try:
        while pos < len(data) and len(skins) < MAX_ENTRIES:
            step, pos = _read_varint(data, pos)
            number, pos = _read_varint(data, pos)
            champion += step
            if champion > 0 and 0 < number < 1000:
                skins[champion] = champion * 1000 + number
    except ValueError:
        return None
    return {"name": name, "skins": skins}


# ---- names and pictures ----

def _profile():
    from launcher import lust_profile
    return lust_profile


def _champion_names() -> dict:
    try:
        from launcher import lust_skins
        return {c["id"]: c["name"] for c in lust_skins.champions()}
    except Exception:  # noqa: BLE001
        return {}


def describe(skins: dict) -> list:
    """[{champion, championName, skinId, skin, chroma, color, tile}] for {champion: skin id}."""
    if not skins:
        return []
    names = _champion_names()
    with ThreadPoolExecutor(max_workers=8) as pool:
        listings = dict(zip(skins, pool.map(_profile().skins, list(skins))))
    result = []
    for champion, skin_id in skins.items():
        found = chroma = None
        for entry in listings.get(champion) or []:
            if entry["id"] == skin_id:
                found = entry
                break
            chroma = next((c for c in entry.get("chromas") or [] if c["id"] == skin_id), None)
            if chroma:
                found = entry
                break
        result.append({
            "champion": champion,
            "championName": names.get(champion) or (found or {}).get("name") or f"#{champion}",
            "skinId": skin_id,
            "skin": (found or {}).get("name") or f"Skin {skin_id % 1000}",
            "chroma": (chroma or {}).get("name") or "",
            "color": (chroma or {}).get("color") or "",
            "tile": (found or {}).get("tile") or (found or {}).get("splash") or "",
        })
    result.sort(key=lambda e: e["championName"].casefold())
    return result


# ---- the hub ----

def _historic():
    from utils.core import historic
    return historic


def mine() -> dict:
    """Your saved skins: {champion id: skin id}, and how many custom skins were left out."""
    skins, custom = {}, 0
    for key, value in _historic().load_historic_map().items():
        if isinstance(value, str):
            custom += 1
            continue
        cleaned = _clean({key: value})
        skins.update(cleaned)
    return {"skins": skins, "custom": custom}


def _my_name() -> str:
    try:
        from launcher import lust_hero
        return ((lust_hero.get() or {}).get("name") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def listing() -> dict:
    """What the Share page shows on the left: your skins and their code."""
    own = mine()
    return {
        "skins": describe(own["skins"]),
        "custom": own["custom"],
        "code": encode(own["skins"], _my_name()) if own["skins"] else "",
    }


def peek(code: str) -> dict:
    """What a friend's code holds, next to what you have now on the same champions."""
    found = decode(code)
    if found is None:
        return {"ok": False}
    own = mine()["skins"]
    items = describe(found["skins"])
    for item in items:
        item["same"] = own.get(item["champion"]) == item["skinId"]
        item["replaces"] = bool(own.get(item["champion"])) and not item["same"]
    return {"ok": True, "name": found["name"], "skins": items}


def import_code(code: str, champions=None) -> str:
    """Save a friend's skins as yours; only the listed champions when given."""
    found = decode(code)
    if found is None:
        return "Bu kod okunamadı: tamamını kopyaladığından emin ol"
    wanted = None
    if isinstance(champions, list):
        wanted = set()
        for c in champions:
            try:
                wanted.add(int(c))
            except (TypeError, ValueError):
                continue
    count = 0
    for champion, skin_id in found["skins"].items():
        if wanted is not None and champion not in wanted:
            continue
        _historic().write_historic_entry(champion, skin_id)
        count += 1
    if not count:
        return "Hiç skin seçilmedi"
    log.info(f"[Share] Imported {count} skins")
    who = f"{found['name']}: " if found["name"] else ""
    return f"{who}{count} skin alındı, o şampiyonları seçince champ select'te gelir"


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


def dumps_peek(code: str) -> bytes:
    return json.dumps(peek(code), ensure_ascii=False).encode("utf-8")
