"""Auto Accept, Auto Ban and Auto Pick from the desktop app.

While League is open a small thread watches the client (LCU): it accepts the ready check,
and in champ select it bans and picks for the player when their turn comes, taking the first
champion of their list that is still free. Each switch and both lists are the player's own,
kept in Lust's data folder as lust-auto.json.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

FILE = "lust-auto.json"
MAX_CHOICES = 5
DEFAULTS = {"accept": False, "ban": False, "pick": False, "bans": [], "picks": []}
IDLE_S = 3.0   # League closed or nothing to do
BUSY_S = 1.0   # ready check or champ select
CREDS_TTL_S = 30.0

_lock = threading.Lock()
_cache: Optional[dict] = None
_thread: Optional[threading.Thread] = None
_creds: dict = {"at": 0.0, "value": None}
_done: set = set()  # action ids this champ select already answered


# ---- settings ----

def clean(data) -> dict:
    out = dict(DEFAULTS)
    if not isinstance(data, dict):
        return out
    for key in ("accept", "ban", "pick"):
        if isinstance(data.get(key), bool):
            out[key] = data[key]
    for key in ("bans", "picks"):
        values = data.get(key) if isinstance(data.get(key), list) else []
        ids = []
        for value in values:
            if isinstance(value, int) and not isinstance(value, bool) and value > 0 and value not in ids:
                ids.append(value)
        out[key] = ids[:MAX_CHOICES]
    return out


def _path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / FILE


def settings() -> dict:
    global _cache
    with _lock:
        if _cache is None:
            try:
                _cache = clean(json.loads(_path().read_text(encoding="utf-8")))
            except (OSError, ValueError):
                _cache = dict(DEFAULTS)
        return json.loads(json.dumps(_cache))


def update(changes: dict) -> str:
    global _cache
    merged = settings()
    merged.update(changes if isinstance(changes, dict) else {})
    cleaned = clean(merged)
    with _lock:
        _cache = cleaned
        try:
            _path().write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning(f"[Auto] Could not save: {exc}")
            return "Kaydedilemedi"
    if cleaned["accept"] or cleaned["ban"] or cleaned["pick"]:
        start()
    return ""


def _reveal() -> dict:
    """Lobby Reveal: its switch and the teammates it found in this champ select."""
    from launcher.lust_settings import enabled
    out = {"on": enabled("lobby_reveal"), "active": False, "players": [], "multiUrl": ""}
    try:
        from threads.core.lobby_reveal_thread import latest
        team = latest()
    except Exception:  # noqa: BLE001
        team = {}
    if team.get("active"):
        out.update(active=True, multiUrl=team.get("multiUrl", ""),
                   players=[{k: p.get(k, "") for k in ("gameName", "gameTag", "position", "opggUrl")}
                            for p in team.get("players") or []])
    return out


def listing() -> dict:
    from launcher import lust_skins
    return dict(settings(), champions=[{"id": c["id"], "name": c["name"]} for c in lust_skins.champions()],
                max=MAX_CHOICES, reveal=_reveal())


def dumps_listing() -> bytes:
    return json.dumps(listing(), ensure_ascii=False).encode("utf-8")


# ---- champ select ----

def _taken(session: dict) -> set:
    """Champions nobody else may pick now: banned, picked, or hovered by a teammate."""
    taken = set()
    bans = session.get("bans") or {}
    for key in ("myTeamBans", "theirTeamBans"):
        taken.update(c for c in bans.get(key) or [] if isinstance(c, int) and c > 0)
    for group in session.get("actions") or []:
        for action in group or []:
            if action.get("completed") and action.get("championId"):
                taken.add(action["championId"])
    return taken


def choose(session: dict, config: dict, pickable=None, bannable=None) -> Optional[tuple]:
    """(action id, champion id, kind) to answer now, or None. Only the player's own action
    that is in progress; bans skip what a teammate wants to play."""
    if not isinstance(session, dict):
        return None
    me = session.get("localPlayerCellId")
    taken = _taken(session)
    friends = {m.get("championPickIntent") for m in session.get("myTeam") or [] if m.get("cellId") != me}
    friends.update(m.get("championId") for m in session.get("myTeam") or [] if m.get("cellId") != me)
    for group in session.get("actions") or []:
        for action in group or []:
            if action.get("actorCellId") != me or action.get("completed") or not action.get("isInProgress"):
                continue
            kind = action.get("type")
            if kind == "ban" and config.get("ban"):
                allowed = bannable
                choices = [c for c in config.get("bans") or [] if c not in taken and c not in friends]
            elif kind == "pick" and config.get("pick"):
                allowed = pickable
                choices = [c for c in config.get("picks") or [] if c not in taken]
            else:
                continue
            if allowed is not None:
                choices = [c for c in choices if c in allowed]
            if choices:
                return action.get("id"), choices[0], kind
    return None


# ---- the client ----

def _credentials():
    now = time.monotonic()
    if _creds["value"] and now - _creds["at"] < CREDS_TTL_S:
        return _creds["value"]
    from launcher.lust_offline import _lcu_credentials
    _creds.update(at=now, value=_lcu_credentials())
    return _creds["value"]


def _lcu(method: str, path: str, body=None):
    creds = _credentials()
    if not creds:
        return None
    port, token = creds
    import requests
    try:
        response = requests.request(method, f"https://127.0.0.1:{port}{path}", auth=("riot", token), json=body,
                                    verify=False, timeout=3, proxies={"http": None, "https": None})
    except requests.RequestException:
        _creds["at"] = 0.0  # League may have restarted with a new port
        return None
    if not response.ok:
        return None
    try:
        return response.json() if response.content else {}
    except ValueError:
        return {}


def _accept() -> None:
    check = _lcu("GET", "/lol-matchmaking/v1/ready-check")
    if isinstance(check, dict) and check.get("state") == "InProgress" and check.get("playerResponse") == "None":
        if _lcu("POST", "/lol-matchmaking/v1/ready-check/accept") is not None:
            log.info("[Auto] Ready check accepted")


def _champ_select(config: dict) -> None:
    session = _lcu("GET", "/lol-champ-select/v1/session")
    if not isinstance(session, dict):
        return
    pickable = _lcu("GET", "/lol-champ-select/v1/pickable-champion-ids") if config["pick"] else None
    bannable = _lcu("GET", "/lol-champ-select/v1/bannable-champion-ids") if config["ban"] else None
    found = choose(session, config, set(pickable) if isinstance(pickable, list) else None,
                   set(bannable) if isinstance(bannable, list) else None)
    if not found or found[0] in _done:
        return
    action_id, champion, kind = found
    path = f"/lol-champ-select/v1/session/actions/{action_id}"
    if _lcu("PATCH", path, {"championId": champion}) is None:
        return
    if _lcu("POST", path + "/complete", {"championId": champion}) is not None:
        _done.add(action_id)
        log.info(f"[Auto] {kind} {champion}")


def _tick() -> float:
    config = settings()
    if not (config["accept"] or config["ban"] or config["pick"]):
        return IDLE_S
    phase = _lcu("GET", "/lol-gameflow/v1/gameflow-phase")
    if phase == "ReadyCheck" and config["accept"]:
        _accept()
        return BUSY_S
    if phase == "ChampSelect" and (config["ban"] or config["pick"]):
        _champ_select(config)
        return BUSY_S
    _done.clear()
    return IDLE_S


def _any_on(config) -> bool:
    return bool(config and (config["accept"] or config["ban"] or config["pick"]))


def _run() -> None:
    global _thread
    while True:
        if not _any_on(settings()):
            with _lock:
                # A switch turned on just now keeps this thread instead of starting another
                if not _any_on(_cache):
                    _thread = None
                    return
        try:
            delay = _tick()
        except Exception as exc:  # noqa: BLE001
            log.debug(f"[Auto] {exc}")
            delay = IDLE_S
        time.sleep(delay)


def start() -> None:
    """Watch the client while any switch is on (the thread ends when all are off)."""
    global _thread
    config = settings()
    if not (config["accept"] or config["ban"] or config["pick"]):
        return
    with _lock:
        if _thread is not None:
            return
        _thread = threading.Thread(target=_run, daemon=True, name="LustAuto")
        _thread.start()
