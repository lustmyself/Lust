"""Performance mode: while a match is being played, Lust's background work rests.

The hub's card refresh, the Rose guard, release checks and downloads, Spotify's theme
check and the hub window's watchdog wait for the match to end; Lust Offline's watcher
looks five times less often. Skin injection and the game tracking are not touched.
Switched in the hub's Settings ("performance_mode", on by default).
"""

from __future__ import annotations

import threading
import time

GAME = "league of legends.exe"
CHECK_EVERY_S = 5.0
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
