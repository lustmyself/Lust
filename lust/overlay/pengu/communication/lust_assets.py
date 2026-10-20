"""The theme's asset folders (wallpapers, audio, banners, fonts) for its settings.

Pengu 1.1.6 plugins can't list or write files, so LUST-Theme asks Lust over the
bridge ("lust-assets" messages) to list a folder, open it, delete a file, or save
a file dropped on the settings. Bridge messages stay under the WebSocket's 1 MB
limit, so dropped files arrive in chunks and are written once complete.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from utils.core.logging import get_logger
from utils.core.paths import get_user_data_dir, open_folder_in_explorer

log = get_logger()

# kind -> (folder in LUST-Theme, accepted extensions)
KINDS = {
    "wallpaper": ("assets/backgrounds/wallpapers",
                  {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".mp4", ".webm", ".mkv", ".mov", ".m4v"}),
    "audio": ("assets/backgrounds/audio", {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus"}),
    "banner": ("assets/icon/regalia-banners", {".png", ".jpg", ".jpeg", ".gif", ".webp"}),
    "font": ("assets/fonts", {".ttf", ".otf", ".woff", ".woff2"}),
}
MAX_FILE_BYTES = 300 * 1024 * 1024
BAD_NAME = re.compile(r'[\\/:*?"<>|]|^\.|\.\.')


def _folder(kind: str) -> Path:
    return get_user_data_dir() / "Pengu Loader" / "plugins" / "LUST-Theme" / KINDS[kind][0]


def _valid_name(kind: str, name: str) -> bool:
    return (bool(name) and len(name) <= 120 and not BAD_NAME.search(name)
            and Path(name).suffix.lower() in KINDS[kind][1])


def list_files(kind: str) -> list[str]:
    folder = _folder(kind)
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_file() and _valid_name(kind, p.name))


def _save_chunk(kind: str, name: str, index: int, total: int, data: str) -> str:
    folder = _folder(kind)
    folder.mkdir(parents=True, exist_ok=True)
    part = folder / f".{name}.part"
    chunk = base64.b64decode(data, validate=True)
    if index == 0:
        part.write_bytes(chunk)
    else:
        if not part.exists():
            return "upload interrupted"
        with part.open("ab") as handle:
            handle.write(chunk)
    if part.stat().st_size > MAX_FILE_BYTES:
        part.unlink(missing_ok=True)
        return "file too large"
    if index == total - 1:
        part.replace(folder / name)
        log.info(f"[LustAssets] Added {kind} {name}")
    return ""


def handle(payload: dict) -> dict:
    """Answer one "lust-assets" bridge message."""
    kind = str(payload.get("kind") or "")
    action = str(payload.get("action") or "")
    request_id = payload.get("requestId")
    reply = {"type": "lust-assets", "kind": kind, "action": action, "requestId": request_id, "error": ""}
    if kind not in KINDS:
        reply["error"] = "unknown kind"
        return reply
    name = str(payload.get("name") or "")
    try:
        if action == "open":
            open_folder_in_explorer(_folder(kind))
        elif action == "delete":
            if not _valid_name(kind, name):
                reply["error"] = "bad file name"
            else:
                (_folder(kind) / name).unlink(missing_ok=True)
                log.info(f"[LustAssets] Deleted {kind} {name}")
        elif action == "save":
            if not _valid_name(kind, name):
                reply["error"] = "bad file name"
            else:
                index, total = int(payload.get("index", 0)), int(payload.get("total", 1))
                reply["error"] = _save_chunk(kind, name, index, total, str(payload.get("data") or ""))
                reply["done"] = index == total - 1
        elif action != "list":
            reply["error"] = "unknown action"
    except Exception as exc:  # noqa: BLE001 - reported back to the settings
        log.warning(f"[LustAssets] {action} {kind} {name} failed: {exc}")
        reply["error"] = str(exc)
    reply["files"] = list_files(kind)
    return reply
