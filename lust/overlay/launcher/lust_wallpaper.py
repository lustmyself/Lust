"""The LoL client's wallpaper, picked from the desktop app.

The LUST theme shows a picture or video behind the League client (or League's own
background). The files live in the theme's wallpapers folder; which one is on lives in
the client. The app keeps the player's choice in lust-wallpaper.json and tells the theme
over the bridge ("lust-wallpaper"): at once while League is open, and when the theme
starts and asks ("get"). The theme reports what it shows ("state"), so the app shows
the current one too.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

FILE = "lust-wallpaper.json"
KIND = "wallpaper"
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".bmp": "image/bmp",
         ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
         ".mov": "video/quicktime", ".m4v": "video/mp4"}
MAX_BYTES = 300 * 1024 * 1024

_lock = threading.Lock()
_reported: dict = {}  # what the theme said it shows: {league, name}


def _assets():
    from pengu.communication import lust_assets
    return lust_assets


def _path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / FILE


def clean(data) -> dict:
    """{league, name, rev}: League's own background, or a wallpaper file by name."""
    if not isinstance(data, dict):
        return {"league": True, "name": "", "rev": 0}
    name = data.get("name") if isinstance(data.get("name"), str) else ""
    rev = data.get("rev") if isinstance(data.get("rev"), int) and not isinstance(data.get("rev"), bool) else 0
    return {"league": bool(data.get("league", not name)), "name": name[:120], "rev": max(rev, 0)}


def choice() -> Optional[dict]:
    """The app's saved choice, or None when the app never picked one."""
    try:
        return clean(json.loads(_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def files() -> list:
    return _assets().list_files(KIND)


def is_video(name: str) -> bool:
    return Path(name).suffix.lower() not in IMAGES


def current() -> dict:
    """What the client shows: the theme's report, else the app's choice, else League's own."""
    with _lock:
        reported = dict(_reported)
    if reported:
        return {"league": bool(reported.get("league")), "name": str(reported.get("name") or "")}
    saved = choice()
    return {"league": saved["league"], "name": saved["name"]} if saved else {"league": True, "name": ""}


def listing() -> dict:
    now = current()
    return {
        "files": [{"name": name, "video": is_video(name)} for name in files()],
        "league": now["league"],
        "name": now["name"],
        "connected": bool(_reported),
    }


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


def _message(saved: dict) -> dict:
    return {"type": "lust-wallpaper", "action": "apply", **saved}


def choose(name: Optional[str]) -> str:
    """name None: League's own background; otherwise that wallpaper file."""
    if name is not None and name not in files():
        return "Bu duvar kağıdı bulunamadı"
    saved = choice() or clean(None)
    saved = {"league": name is None, "name": name or saved["name"], "rev": saved["rev"] + 1}
    try:
        _path().write_text(json.dumps(saved), encoding="utf-8")
    except OSError as e:
        log.warning(f"[Wallpaper] Could not save: {e}")
        return "Kaydedilemedi"
    with _lock:
        _reported.update(league=saved["league"], name=saved["name"])
    sent = _broadcast(_message(saved))
    label = "LoL'ün kendi arka planı" if name is None else name
    return f"{label} seçildi" + ("" if sent else ": League açılınca uygulanır")


def _broadcast(message: dict) -> bool:
    try:
        from launcher import lust_client
        broadcaster = lust_client._broadcaster()
        server = getattr(broadcaster, "websocket_server", None)
        if broadcaster is None or not getattr(server, "connections", None):
            return False
        broadcaster.broadcast_raw(json.dumps(message))
        return True
    except Exception as e:  # noqa: BLE001
        log.info(f"[Wallpaper] Could not reach the client: {e}")
        return False


def bridge_reply(payload: dict) -> dict:
    """The theme asks for the app's choice ("get") or says what it shows ("state")."""
    action = str(payload.get("action") or "")
    if action == "state":
        with _lock:
            _reported.clear()
            _reported.update(league=bool(payload.get("league")), name=str(payload.get("name") or "")[:120])
        return {"type": "lust-wallpaper", "action": "noted"}
    saved = choice()
    return _message(saved) if saved else {"type": "lust-wallpaper", "action": "none"}


def delete(name: str) -> str:
    names = files()
    if name not in names:
        return "Bu duvar kağıdı bulunamadı"
    if len(names) <= 1:
        return "En az bir duvar kağıdı kalmalı"
    reply = _assets().handle({"kind": KIND, "action": "delete", "name": name})
    if reply.get("error"):
        return f"Silinemedi: {reply['error']}"
    if current()["name"] == name:
        choose(None)
    return f"{name} silindi"


def open_folder() -> str:
    _assets().handle({"kind": KIND, "action": "open"})
    return ""


def file_info(name: str) -> Optional[tuple]:
    """(path, content type) of a wallpaper file the hub page may show."""
    if name not in files():
        return None
    path = _assets()._folder(KIND) / name
    return (path, TYPES.get(path.suffix.lower(), "application/octet-stream")) if path.is_file() else None


def import_upload(name: str, stream, length: int) -> str:
    """A picture or video dropped on the hub page, streamed in from the hub server."""
    assets = _assets()
    name = Path(name or "").name.strip()
    if not assets._valid_name(KIND, name):
        return "Yalnızca resim (.jpg, .png, .webp, .gif) ve video (.mp4, .webm) eklenebilir"
    if not 0 < length <= MAX_BYTES:
        return "Dosya çok büyük"
    folder = assets._folder(KIND)
    folder.mkdir(parents=True, exist_ok=True)
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
    except OSError as e:
        log.warning(f"[Wallpaper] Could not add {name}: {e}")
        return f"Eklenemedi: {e}"
    finally:
        part.unlink(missing_ok=True)
    log.info(f"[Wallpaper] Added {name}")
    return f"{name} eklendi"
