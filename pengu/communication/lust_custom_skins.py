"""Custom skins: mod files the player drops in a folder and switches on per champion.

The "Custom skins" tab of the Lust hub in the client lists the .zip / .fantome /
.modpkg files in Lust's "custom skins" folder (its + button opens the folder, so
files are copied and pasted in; files dropped on the tab are sent here in chunks).
Each file says which champion it is for (its WAD is named after the champion,
Ahri.wad.client); the tab matches that to the client's champion list, or the
player picks the champion. A switched-on skin plays whenever that champion goes
into a game, on the skin picked: the injection trigger asks custom_mod_for().
One skin per champion is on at a time.

Skins made for an older League version can crash the game. Each skin remembers the game
build (the game executable's build stamp, new every patch) it last played on without a crash,
and the one it crashed on, so the hub can tell "works on this patch", "not tried since League
updated", "crashed on this patch" and "made long before this patch" apart.
"""

from __future__ import annotations

import base64
import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger
from utils.core.paths import get_user_data_dir, open_folder_in_explorer

log = get_logger()

SUFFIXES = {".zip", ".fantome", ".modpkg"}
STATE_FILE = "lust-custom-skins.json"
MAX_FILE_BYTES = 1024 * 1024 * 1024
BAD_NAME = re.compile(r'[\\/:*?"<>|]|^\.|\.\.')
WAD_RE = re.compile(r"(?:^|/)([A-Za-z0-9_]+)\.wad(?:\.client)?(?:/|$)", re.IGNORECASE)
_lock = threading.RLock()
_playing: Optional[str] = None  # the custom skin of the injection in progress
_playing_build: Optional[int] = None
OLD_AFTER_S = 90 * 24 * 60 * 60  # made this long before the game build: likely outdated
_build_cache: dict = {"at": 0.0, "build": None}


def folder() -> Path:
    path = get_user_data_dir() / "custom skins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def game_build() -> Optional[int]:
    """The installed game's build stamp (changes with every League patch), None when unknown."""
    if time.monotonic() - _build_cache["at"] < 60:
        return _build_cache["build"]
    build = None
    try:
        from injection.config.config_manager import ConfigManager
        from injection.tools.patcher import read_game_build
        league = ConfigManager().load_league_path()
        build = read_game_build(Path(league)) if league else None
    except Exception as exc:  # noqa: BLE001
        log.debug(f"[CustomSkins] Could not read the game build: {exc}")
    _build_cache.update(at=time.monotonic(), build=build)
    return build


def status(entry: dict, build: Optional[int]) -> str:
    """ok, crashed, untested (worked before League updated), old (made long before this patch) or new."""
    if entry.get("crashed_build") and (build is None or entry["crashed_build"] == build):
        return "crashed"
    if build is not None and entry.get("worked_build") == build:
        return "ok"
    if entry.get("worked_build"):
        return "untested"
    made = entry.get("made")
    if build is not None and isinstance(made, (int, float)) and made and build - made > OLD_AFTER_S:
        return "old"
    return "new"


def _made(path: Path) -> Optional[int]:
    """When the mod was packed: its newest file's date inside the archive."""
    if path.suffix.lower() not in {".zip", ".fantome"}:
        return None
    try:
        import zipfile
        with zipfile.ZipFile(path) as archive:
            stamps = [time.mktime(info.date_time + (0, 0, -1)) for info in archive.infolist()
                      if info.date_time[0] > 1980]
        return int(max(stamps)) if stamps else None
    except Exception:  # noqa: BLE001
        return None


def _valid_name(name: str) -> bool:
    return (bool(name) and len(name) <= 160 and not BAD_NAME.search(name)
            and Path(name).suffix.lower() in SUFFIXES)


def _load() -> dict:
    try:
        data = json.loads((folder() / STATE_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(state: dict) -> None:
    path = folder() / STATE_FILE
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def inspect(path: Path) -> dict:
    """The WAD names in a mod (champion candidates) and the title its info.json gives."""
    from utils.core.safe_extract import list_mod_archive
    wads: list[str] = []
    title = ""
    try:
        for member in list_mod_archive(path):
            match = WAD_RE.search(member.replace("\\", "/"))
            if match and match.group(1).lower() not in wads:
                wads.append(match.group(1).lower())
    except Exception as exc:  # noqa: BLE001 - a broken file is listed, just without a champion
        log.info(f"[CustomSkins] Could not read {path.name}: {exc}")
        return {"wads": [], "title": "", "broken": True}
    if path.suffix.lower() in {".zip", ".fantome"}:
        try:
            import zipfile
            with zipfile.ZipFile(path) as archive:
                info_name = next((n for n in archive.namelist() if n.lower() == "meta/info.json"), None)
                if info_name:
                    info = json.loads(archive.read(info_name).decode("utf-8-sig", errors="replace"))
                    title = str(info.get("Name") or info.get("name") or "")[:80]
        except Exception:  # noqa: BLE001
            pass
    return {"wads": wads, "title": title, "broken": False, "made": _made(path)}


def list_skins() -> list[dict]:
    with _lock:
        state = _load()
        files = sorted((p for p in folder().iterdir() if p.is_file() and _valid_name(p.name)),
                       key=lambda p: p.name.casefold())
        changed = False
        build = game_build()
        skins = []
        for path in files:
            stat = path.stat()
            entry = state.get(path.name) if isinstance(state.get(path.name), dict) else {}
            key = f"{stat.st_size}:{int(stat.st_mtime)}"
            if entry.get("key") != key or "made" not in entry:
                entry = {**entry, **inspect(path), "key": key}
                state[path.name] = entry
                changed = True
            skins.append({
                "name": path.name,
                "title": entry.get("title") or path.stem,
                "size": stat.st_size,
                "wads": entry.get("wads") or [],
                "broken": bool(entry.get("broken")),
                "championId": entry.get("championId"),
                "enabled": bool(entry.get("enabled")),
                "auto": entry.get("auto", True),
                "made": entry.get("made"),
                "status": status(entry, build),
            })
        # Forget files that were removed from the folder
        for name in [n for n in state if n not in {p.name for p in files}]:
            del state[name]
            changed = True
        if changed:
            _save(state)
        return skins


def _set(name: str, enabled: Optional[bool], champion_id: Optional[int]) -> str:
    with _lock:
        state = _load()
        if not _valid_name(name) or not (folder() / name).is_file():
            return "file is gone"
        entry = state.setdefault(name, {})
        if champion_id is not None:
            new_champion = champion_id if champion_id > 0 else None
            if new_champion != entry.get("championId"):
                entry["enabled"] = False
            entry["championId"] = new_champion
            # Cleared by the player: the tab stops guessing the champion from the file
            entry["auto"] = new_champion is not None
        if enabled is not None:
            if enabled and not entry.get("championId"):
                return "pick a champion first"
            entry["enabled"] = bool(enabled)
            if enabled:
                # One skin per champion
                for other, other_entry in state.items():
                    if other != name and isinstance(other_entry, dict) \
                            and other_entry.get("championId") == entry.get("championId"):
                        other_entry["enabled"] = False
        _save(state)
        log.info(f"[CustomSkins] {name}: champion={entry.get('championId')} enabled={entry.get('enabled')}")
        return ""


def _save_chunk(name: str, index: int, total: int, data: str) -> str:
    target = folder()
    part = target / f".{name}.part"
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
        part.replace(target / name)
        log.info(f"[CustomSkins] Added {name}")
    return ""


def handle(payload: dict) -> dict:
    """Answer one "lust-custom-skins" bridge message."""
    action = str(payload.get("action") or "")
    reply = {"type": "lust-custom-skins", "action": action, "requestId": payload.get("requestId"), "error": ""}
    name = str(payload.get("name") or "")
    try:
        if action == "list":
            reply["skins"] = list_skins()
        elif action == "open":
            open_folder_in_explorer(folder())
        elif action == "set":
            enabled = payload.get("enabled")
            champion = payload.get("championId")
            reply["error"] = _set(
                name,
                None if enabled is None else bool(enabled),
                None if champion is None else int(champion),
            )
            reply["skins"] = list_skins()
        elif action == "chunk":
            if not _valid_name(name):
                reply["error"] = "this file type is not a mod (.zip, .fantome, .modpkg)"
            else:
                reply["error"] = _save_chunk(name, int(payload.get("index", 0)), int(payload.get("total", 1)),
                                             str(payload.get("data") or ""))
        else:
            reply["error"] = "unknown action"
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[CustomSkins] {action} failed: {exc}")
        reply["error"] = str(exc)
    return reply


def custom_mod_for(champion_id, skin_id) -> Optional[dict]:
    """The switched-on custom skin for a champion, as a selected custom mod on the skin picked in
    champ select: a mod made for one of the champion's skins (EDG Aphelios, say) needs that skin
    picked, one made for the default skin goes in with the default skin."""
    global _playing
    _playing = None  # a new game: only a skin picked for it can be blamed for a crash
    try:
        champion_id = int(champion_id)
        skin_id = int(skin_id)
    except (TypeError, ValueError):
        return None
    if champion_id <= 0 or skin_id // 1000 != champion_id:
        return None
    from launcher.lust_settings import enabled
    if not enabled("custom_skins"):
        return None
    with _lock:
        state = _load()
    for name, entry in state.items():
        if not isinstance(entry, dict) or not entry.get("enabled") or entry.get("championId") != champion_id:
            continue
        path = folder() / name
        if not _valid_name(name) or not path.is_file():
            continue
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)[:60] or "skin"
        log.info(f"[CustomSkins] {name} plays on champion {champion_id}, skin {skin_id}")
        global _playing_build
        _playing = name
        _playing_build = game_build()
        return {
            "skin_id": skin_id,
            "storage_skin_id": skin_id,
            "target_skin_ids": [skin_id],
            "champion_id": champion_id,
            "mod_name": entry.get("title") or path.stem,
            "display_name": entry.get("title") or path.stem,
            "mod_path": str(path),
            "mod_folder_name": f"lust-custom-{safe}",
            "relative_path": None,  # not one of the mod wheel's: nothing saved as its history
        }
    return None


def game_ran_fine() -> None:
    """The game ran past the crash window with the mods in: the custom skin in play works on this patch."""
    name, build = _playing, _playing_build
    if not name or not build:
        return
    with _lock:
        state = _load()
        entry = state.get(name)
        if isinstance(entry, dict) and (entry.get("worked_build") != build or entry.get("crashed_build")):
            entry["worked_build"] = build
            entry.pop("crashed_build", None)
            _save(state)
            log.info(f"[CustomSkins] {name} works on game build {build}")


def game_keeps_crashing() -> None:
    """The game closed right after loading its mods, again and again: tell the player, and
    switch off the custom skin in play (made for an older game version, most of the time)."""
    global _playing
    name, _playing = _playing, None
    title = ""
    if name:
        with _lock:
            state = _load()
            entry = state.get(name)
            if isinstance(entry, dict) and entry.get("enabled"):
                entry["enabled"] = False
                if _playing_build:
                    entry["crashed_build"] = _playing_build
                title = entry.get("title") or Path(name).stem
                _save(state)
                log.warning(f"[CustomSkins] {name} crashed the game; switched off")
    tr_text = (f"Oyun \"{title}\" yüzünden açılmıyordu; bu özel skin kapatıldı. Oyun artık modsuz açılacak. "
               "Skin büyük ihtimalle eski bir oyun sürümü için yapılmış: hub'daki Custom skinler sekmesinden "
               "güncelini arayabilirsin." if title else
               "Oyun modlar yüklenince kapanıyordu; enjeksiyon durduruldu, oyun modsuz açılacak.")
    try:
        from launcher import lust_hub
        lust_hub.toast(tr_text)
    except Exception:  # noqa: BLE001
        pass
    try:
        from utils.core.issue_reporter import report_issue
        report_issue(
            "LUST_MOD_CRASH",
            "error",
            f"The game closed right after loading {('the custom skin ' + title) if title else 'its mods'}, "
            "so Lust stopped injecting and the game starts without mods.",
            hint=("That custom skin was switched off. It was most likely made for an older League version: "
                  "get an updated version of it." if title else
                  "One of the selected mods breaks the game, most likely one made for an older League version."),
        )
    except Exception:  # noqa: BLE001
        pass
