"""The desktop hub's Settings page: switches the rest of Lust reads.

Kept in Lust's data folder as hub-settings.json. Start with Windows and silent updates
keep their own places (the scheduled task, config.ini); everything else is here.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from utils.core.logging import get_logger

log = get_logger()

DEFAULTS = {
    "skins": True,           # inject skins at all
    "custom_skins": True,    # play switched-on custom skins
    "lobby_reveal": True,    # teammates' names in champ select
    "rose_guard": True,      # close Rose and take the League hook back
    "quiet_start": False,    # start in the tray, no hub window
    "launch_league": True,   # open League through Lust Offline when Lust starts
    "backdrop": "cinematic", # the hub's background
    "reduce_motion": False,  # the hub without animations
}
CHOICES = {"backdrop": ("cinematic", "hextech")}
FILE = "hub-settings.json"
_lock = threading.Lock()
_cache: dict | None = None


def _path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / FILE


def all_settings() -> dict:
    global _cache
    with _lock:
        if _cache is None:
            try:
                saved = json.loads(_path().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                saved = {}
            _cache = {key: saved.get(key, value) for key, value in DEFAULTS.items()
                      if isinstance(saved.get(key, value), type(value))}
            for key, value in DEFAULTS.items():
                _cache.setdefault(key, value)
        return dict(_cache)


def get(key: str):
    return all_settings().get(key, DEFAULTS.get(key))


def enabled(key: str) -> bool:
    """A switch is on (unknown keys count as on, so a missing setting never turns Lust off)."""
    value = get(key)
    return value if isinstance(value, bool) else True


def set_value(key: str, value) -> bool:
    """Save one setting. False when the key or the value isn't one the page offers."""
    global _cache
    if key not in DEFAULTS:
        return False
    if isinstance(DEFAULTS[key], bool):
        if not isinstance(value, bool):
            return False
    elif value not in CHOICES.get(key, ()):
        return False
    current = all_settings()
    current[key] = value
    with _lock:
        _cache = current
        try:
            _path().write_text(json.dumps(current, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning(f"[Settings] Could not save {key}: {exc}")
            return False
    log.info(f"[Settings] {key} = {value}")
    return True
