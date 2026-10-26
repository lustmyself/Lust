"""Performance mode: while a match is being played, Lust's background work rests.

The hub's card refresh, the Rose guard, release checks and downloads, Spotify's theme
check and the hub window's watchdog wait for the match to end; Lust Offline's watcher
looks five times less often, and Lust's own Lust.exe processes drop to below normal
priority so the game always comes first for the CPU. That waits until the loading screen
is over (the game's Live Client Data API answers with a game time): lowered during the
load, alt-tab showed a black screen. The hub's WebView2 and the LTK patcher keep their
priority. Skin injection and the game tracking are not touched. Switched in the hub's
Settings ("performance_mode", on by default).
"""

from __future__ import annotations

import threading
import time

GAME = "league of legends.exe"
CHECK_EVERY_S = 5.0
LOWER_AFTER_S = 60.0       # the game loads first: Lust's priority drops once a match has run this long
PRIORITY_EVERY_S = 10.0
LIVE_GAME_URL = "https://127.0.0.1:2999/liveclientdata/gamestats"  # answers once the load is over
_lock = threading.Lock()
_checked_at = 0.0
_in_game = False


def _game_running() -> bool:
    import psutil
    for proc in psutil.process_iter(["name"]):
        if (proc.info.get("name") or "").lower() == GAME:
            return True
    return False


def in_game() -> bool:
    """A match is running (checked at most every few seconds)."""
    global _checked_at, _in_game
    with _lock:
        if time.time() - _checked_at >= CHECK_EVERY_S:
            try:
                _in_game = _game_running()
            except Exception:  # noqa: BLE001 - never in the way of Lust
                _in_game = False
            _checked_at = time.time()
        return _in_game


def resting() -> bool:
    """Background work should wait: performance mode is on and a match is running."""
    try:
        from launcher.lust_settings import enabled
        if not enabled("performance_mode"):
            return False
    except Exception:  # noqa: BLE001
        pass
    return in_game()


def _game_loaded() -> bool:
    """The loading screen is over: the game's own local API reports a running game time."""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(LIVE_GAME_URL, timeout=1.0, verify=False)  # Riot's self-signed cert
        return resp.status_code == 200 and float(resp.json().get("gameTime") or 0) > 0
    except Exception:  # noqa: BLE001 - not loaded yet, or no API: keep the normal priority
        return False


def _own_processes():
    """Lust's own Lust.exe processes; never WebView2, the LTK patcher or anything else."""
    import os
    import sys
    import psutil
    me = psutil.Process()
    names = {os.path.basename(sys.executable).lower()}
    procs = [me]
    for child in me.children(recursive=True):
        try:
            if child.name().lower() in names:
                procs.append(child)
        except psutil.Error:
            continue
    return procs


def set_low_priority(low: bool) -> None:
    import psutil
    if not hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):  # Windows only
        return
    level = psutil.BELOW_NORMAL_PRIORITY_CLASS if low else psutil.NORMAL_PRIORITY_CLASS
    for proc in _own_processes():
        try:
            proc.nice(level)
        except psutil.Error:
            continue


def _priority_watch() -> None:
    from utils.core.logging import get_logger
    log = get_logger()
    lowered, since = False, None
    while True:
        try:
            if resting():
                since = since or time.time()
                if not lowered and time.time() - since >= LOWER_AFTER_S and _game_loaded():
                    set_low_priority(True)
                    lowered = True
                    log.info("[Perf] Match running: Lust runs at below normal priority")
            else:
                since = None
                if lowered:
                    set_low_priority(False)
                    lowered = False
                    log.info("[Perf] Match over: Lust's priority is back to normal")
        except Exception as exc:  # noqa: BLE001 - never in the way of Lust
            log.debug(f"[Perf] Could not change Lust's priority: {exc}")
        time.sleep(PRIORITY_EVERY_S)


_watch_started = False


def start() -> None:
    """Lower Lust's priority during matches (performance mode)."""
    global _watch_started
    if _watch_started:
        return
    _watch_started = True
    threading.Thread(target=_priority_watch, daemon=True, name="LustPerf").start()
