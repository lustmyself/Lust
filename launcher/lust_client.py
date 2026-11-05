"""The LoL client's LUST panel, opened from the desktop app.

The client no longer shows a LUST item in its top bar: the theme, wallpaper, plugin and
Lobby Reveal settings that still live in the client open from the app's Settings page.
Lust tells the client's plugins over its bridge (LUST-UI listens for "lust-open-hub").
"""

from __future__ import annotations

import json

from utils.core.logging import get_logger

log = get_logger()

_state = None


def attach_state(state) -> None:
    global _state
    _state = state


def _broadcaster():
    ui_thread = getattr(_state, "ui_skin_thread", None)
    return getattr(ui_thread, "broadcaster", None)


def open_panel(league_running: bool) -> str:
    if not league_running:
        return "Önce League'i aç: bu ayarlar LoL istemcisinin içinde"
    broadcaster = _broadcaster()
    server = getattr(broadcaster, "websocket_server", None)
    if broadcaster is None or not getattr(server, "connections", None):
        return "LoL istemcisine bağlanılamadı: League tamamen açılınca tekrar dene"
    try:
        broadcaster.broadcast_raw(json.dumps({"type": "lust-open-hub"}))
    except Exception as e:  # noqa: BLE001
        log.info(f"[Client] Could not open the LUST panel: {e}")
        return "LoL istemcisine bağlanılamadı"
    return "LUST paneli LoL istemcisinde açıldı"
