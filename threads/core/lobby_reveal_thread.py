#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lobby Reveal Thread
While in champ select, polls the Riot Client chat for teammates' Riot IDs and
sends them, with an op.gg multi-search link, to the LUST-LobbyReveal plugin.
"""

import threading
import time
from typing import Optional

from lcu import LCU
from lcu.features.lobby_reveal import (
    RiotClientChat,
    apply_champ_select_session,
    build_opgg_multi_url,
    build_porofessor_url,
    build_ugg_multi_url,
    opgg_region,
    parse_participants,
    porofessor_region,
    riot_platform,
)
from state import SharedState
from utils.core.logging import get_logger

log = get_logger()

POLL_INTERVAL_S = 1.5
# Lust marks the last seconds of champ select, once every pick is locked, FINALIZATION
CHAMP_SELECT_PHASES = {"ChampSelect", "FINALIZATION"}
# Re-send the same team now and then so a plugin that reloads mid champ select catches up
REBROADCAST_INTERVAL_S = 5.0

# The last team sent, for Lust's desktop app (its Champ select page shows it too)
_latest: dict = {"active": False, "players": []}


def latest() -> dict:
    return dict(_latest)


class LobbyRevealThread(threading.Thread):
    def __init__(self, lcu: LCU, state: SharedState):
        super().__init__(daemon=True, name="LobbyReveal")
        self.lcu = lcu
        self.state = state
        self.chat = RiotClientChat()
        self._stop_event = threading.Event()
        self._last_payload: Optional[dict] = None
        self._last_sent_at = 0.0
        self._region = ""
        self._poro_region = ""
        self._platform = ""

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL_S):
            try:
                self._tick()
            except Exception as e:
                log.debug(f"[Reveal] Poll failed: {e}")

    def _tick(self) -> None:
        from launcher.lust_settings import enabled
        if getattr(self.state, "phase", None) not in CHAMP_SELECT_PHASES or not enabled("lobby_reveal"):
            if self._last_payload is not None and self._last_payload.get("active"):
                self._send({"active": False, "players": [], "region": "", "multiUrl": "", "poroUrl": "", "uggUrl": ""})
            self._region = ""
            self._poro_region = ""
            self._platform = ""
            return

        if not self._region:
            locale = self.lcu.region_locale if self.lcu.ok else None
            web_region = (locale or {}).get("webRegion")
            self._region = opgg_region(web_region)
            self._poro_region = porofessor_region(web_region)
            self._platform = riot_platform(web_region)

        players = parse_participants(self.chat.get_participants())
        if not players:
            return
        apply_champ_select_session(players, self.lcu.session if self.lcu.ok else None)

        payload = {
            "active": True,
            "region": self._region,
            "players": [p.to_payload(self._region, self._platform, self._poro_region) for p in players],
            "multiUrl": build_opgg_multi_url(players, self._region),
            "poroUrl": build_porofessor_url(players, self._poro_region),
            "uggUrl": build_ugg_multi_url(players, self._platform),
        }
        now = time.monotonic()
        if payload != self._last_payload:
            log.info(f"[Reveal] {len(players)} teammate(s) revealed in champ select")
            self._send(payload)
        elif now - self._last_sent_at >= REBROADCAST_INTERVAL_S:
            self._send(payload)

    def _send(self, payload: dict) -> None:
        global _latest
        _latest = payload
        ui_thread = getattr(self.state, "ui_skin_thread", None)
        broadcaster = getattr(ui_thread, "broadcaster", None)
        if broadcaster is None:
            return
        broadcaster.broadcast_lobby_reveal(payload)
        self._last_payload = payload
        self._last_sent_at = time.monotonic()
