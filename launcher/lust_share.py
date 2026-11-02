#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lust users see each other's skins and profile icons, with nothing to paste.

Rose's Party Mode (party/) sends each player's pick through a small relay server
(lust/relay, a Cloudflare worker) and puts the others' skins into the game on this PC.
Rose joins its rooms by pasted tokens; Lust joins them by itself:

- in the lobby, a room for the lobby (duo, flex): from the lobby's partyId
- in champ select, a room for our team: from the game id and our side

Only Lust users are in these rooms, so only they see each other's picks. A player
without Lust keeps seeing the real skins. Off with the "share_skins" setting, and
whenever Lust was built without a relay address.

The rooms carry, next to the skin pick, the profile icon chosen in the hub
(launcher/lust_icon.py): LUST-ProfileIcon shows it for these players too.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from typing import Dict, List, Optional, Set

from utils.core.logging import get_logger

log = get_logger()

CHECK_S = 2.0
# During a match nothing changes: look less often (performance mode)
CHECK_IN_GAME_S = 15.0
# After a failed start (no server, no League): try again after this long
RETRY_S = 60.0
LOBBY_PHASES = ("Lobby", "Matchmaking", "ReadyCheck")
# The rooms stay as they are while the game starts: the others' skins are put in then
KEEP_PHASES = ("GameStart", "InProgress", "Reconnect")
# What our state carries next to the skin pick
EXTRA_KEYS = ("icon_id", "puuid")

_lock = threading.Lock()
_runner: Optional["_Runner"] = None


def _key(*parts) -> str:
    raw = "|".join(str(part) for part in ("lust-share",) + parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def lobby_room(lobby) -> Optional[str]:
    """The room of a lobby with someone else in it, or None."""
    if not isinstance(lobby, dict):
        return None
    party_id = lobby.get("partyId")
    members = lobby.get("members")
    if not isinstance(party_id, str) or not party_id or not isinstance(members, list):
        return None
    if len([m for m in members if isinstance(m, dict)]) < 2:
        return None
    return _key("lobby", party_id)


def team_room(session, game_id=None) -> Optional[str]:
    """The room of our champ select team, or None (no game id, or alone on the team)."""
    if not isinstance(session, dict):
        return None
    team = [p for p in session.get("myTeam") or [] if isinstance(p, dict)]
    if len(team) < 2:
        return None
    gid = session.get("gameId") or game_id
    try:
        gid = int(gid or 0)
    except (TypeError, ValueError):
        gid = 0
    if gid <= 0:
        return None
    cell = session.get("localPlayerCellId")
    me = next((p for p in team if p.get("cellId") == cell), team[0])
    side = me.get("team") or ("blue" if (cell or 0) < 5 else "red")
    return _key("team", gid, side)


def rooms_for(lcu, phase: Optional[str]) -> Optional[Set[str]]:
    """The rooms to be in now; None keeps the current ones."""
    if phase in KEEP_PHASES:
        return None
    if phase in LOBBY_PHASES:
        room = lobby_room(lcu.get("/lol-lobby/v2/lobby"))
        return {room} if room else set()
    if phase == "ChampSelect":
        session = lcu.session
        game_id = None
        if isinstance(session, dict) and not session.get("gameId"):
            flow = lcu.get("/lol-gameflow/v1/session")
            game_id = ((flow or {}).get("gameData") or {}).get("gameId") if isinstance(flow, dict) else None
        room = team_room(session, game_id)
        return {room} if room else set()
    return set()


def relay_url() -> str:
    try:
        from party.network import ws_relay
        return ws_relay.RELAY_URL or ""
    except Exception:  # noqa: BLE001
        return ""


def wanted() -> bool:
    try:
        from launcher.lust_settings import enabled
        if not enabled("share_skins"):
            return False
    except Exception:  # noqa: BLE001
        pass
    return bool(relay_url())


def _my_icon() -> int:
    try:
        from launcher.lust_icon import chosen
        return chosen()
    except Exception:  # noqa: BLE001
        return 0


def _manager_class():
    from party.core.party_manager import PartyManager

    class LustPartyManager(PartyManager):
        """Party Mode in rooms Lust picks itself: no home room, no tokens."""

        my_puuid = ""

        async def enable(self) -> str:
            from party.discovery.lobby_matcher import LobbyMatcher
            from party.discovery.skin_collector import SkinCollector
            if self.party_state.enabled:
                return ""
            self._lobby_matcher = LobbyMatcher(self.lcu, self.state)
            self._skin_collector = SkinCollector(self.state)
            summoner = self.lcu.current_summoner
            my_id = self._lobby_matcher.get_my_summoner_id()
            if not my_id:
                raise RuntimeError("League is not running")
            self.my_puuid = str((summoner or {}).get("puuid") or "") if isinstance(summoner, dict) else ""
            self.party_state.my_summoner_id = my_id
            self.party_state.my_summoner_name = self._lobby_matcher.get_my_summoner_name()
            self._running = True
            self.party_state.enabled = True
            self.party_state.connection = "online"
            self._lobby_check_task = asyncio.create_task(self._lobby_check_loop())
            self._skin_broadcast_task = asyncio.create_task(self._skin_broadcast_loop())
            log.info("[Share] Sharing skins with other Lust users")
            return ""

        def _follow_advertised_rooms(self):
            # Only the rooms of our own lobby and team
            return

        async def _publish_state(self):
            state = dict(self._skin_state or {})
            if state:
                state["sent_at"] = int(time.time() * 1000)
            self._published_state = state or None
            relays = list(self._relays.values())
            if relays:
                await asyncio.gather(*(r.send_state(self._published_state) for r in relays),
                                     return_exceptions=True)

        def _current_skin_state(self) -> Optional[dict]:
            skin = super()._current_skin_state()
            if skin is None and self.state.phase != "ChampSelect" and self._skin_state:
                # Keep our last pick until the next champ select (see the base)
                skin = {k: v for k, v in self._skin_state.items() if k not in EXTRA_KEYS}
            state = dict(skin or {})
            icon = _my_icon()
            if icon:
                state["icon_id"] = icon
                if self.my_puuid:
                    state["puuid"] = self.my_puuid
            return state or None

        async def sync_rooms(self, keys: Set[str]) -> None:
            for key in [k for k in self._relays if k not in keys]:
                relay = self._relays.pop(key, None)
                if relay:
                    log.info(f"[Share] Leaving room {key[:8]}")
                    await relay.disconnect()
            for key in keys:
                if key in self._relays:
                    self._relays[key].resume()
                    continue
                log.info(f"[Share] Joining room {key[:8]}")
                error = await self._join_room(key)
                if error:
                    log.info(f"[Share] Could not join room {key[:8]}: {error}")
            self._refresh_peers()

        def shared_icons(self) -> List[dict]:
            icons = []
            for sid, (member, _connected) in list(self._merged_members().items()):
                skin = member.get("skin")
                icon = skin.get("icon_id") if isinstance(skin, dict) else None
                if isinstance(icon, int) and not isinstance(icon, bool) and icon > 0:
                    puuid = skin.get("puuid")
                    icons.append({"summonerId": str(sid), "iconId": icon,
                                  "puuid": puuid if isinstance(puuid, str) else ""})
            return icons

    return LustPartyManager


class _Runner:
    def __init__(self, lcu, state, injection_manager):
        self.lcu = lcu
        self.state = state
        self.injection_manager = injection_manager
        self.manager = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._failed_at = 0.0

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as e:  # noqa: BLE001
            log.warning(f"[Share] Stopped: {e}")

    async def _main(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception as e:  # noqa: BLE001
                log.debug(f"[Share] {e}")
            await asyncio.sleep(CHECK_IN_GAME_S if self.state.phase == "InProgress" else CHECK_S)

    async def _tick(self) -> None:
        want = wanted() and bool(getattr(self.lcu, "ok", False))
        if not want:
            await self._stop()
            return
        if self.manager is None:
            if time.monotonic() - self._failed_at < RETRY_S:
                return
            if getattr(self.state, "party_manager", None) is not None:
                return  # Rose's own Party Mode is running
            manager = _manager_class()(self.lcu, self.state, self.injection_manager)
            try:
                await manager.enable()
            except Exception as e:  # noqa: BLE001
                self._failed_at = time.monotonic()
                log.info(f"[Share] Not started: {e}")
                await manager.disable()
                return
            self.manager = manager
            self.state.party_manager = manager
        keys = await asyncio.to_thread(rooms_for, self.lcu, self.state.phase)
        if keys is not None:
            await self.manager.sync_rooms(keys)

    async def _stop(self) -> None:
        manager, self.manager = self.manager, None
        if manager is None:
            return
        if getattr(self.state, "party_manager", None) is manager:
            self.state.party_manager = None
        await manager.disable()
        log.info("[Share] Stopped sharing skins")


def attach(lcu, state, injection_manager) -> None:
    """Start sharing (from Lust's start-up, once the League client parts exist)."""
    global _runner
    with _lock:
        if _runner is not None:
            return
        _runner = _Runner(lcu, state, injection_manager)
        threading.Thread(target=_runner.run, daemon=True, name="LustShare").start()


def shared_icons() -> List[dict]:
    """The profile icons other Lust users in our rooms picked, for LUST-ProfileIcon."""
    manager = _runner.manager if _runner else None
    if manager is None:
        return []
    try:
        return manager.shared_icons()
    except Exception:  # noqa: BLE001
        return []


def status() -> Dict[str, object]:
    """For the hub: whether sharing runs and with how many Lust users right now."""
    manager = _runner.manager if _runner else None
    peers = len(manager.party_state.peers) if manager is not None else 0
    return {"available": bool(relay_url()), "running": manager is not None, "peers": peers}
