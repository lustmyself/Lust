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

Friends paired with a code stay linked for good, lobby or not: each Lust keeps its own
room open (Party Mode's "home" room, from party_storage's key), and pasting a friend's
code once joins theirs every time Lust starts (lust-friends.json). One side pasting is
enough: both end up in the same room.

The rooms carry, next to the skin pick, the profile icon chosen in the hub
(launcher/lust_icon.py): LUST-ProfileIcon shows it for these players too.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
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
# Who we are, next to the pick: Riot ID and Discord account (shown in friends' lists)
PROFILE_KEYS = ("riot", "dc", "dcu", "dca")
EXTRA_KEYS = ("icon_id", "puuid", "removed") + PROFILE_KEYS
FRIENDS_FILE = "lust-friends.json"
# Our own code, kept so the hub shows it while League is closed too
MY_CODE_FILE = "lust-share-code.json"
# Party Mode stays in at most 8 rooms: ours, a lobby, a team and the friends'
MAX_FRIENDS = 5
# Players who paired with our code (they join our room; no room of theirs to open)
MAX_JOINED = 20

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


# ---- friends paired with a code ----

_friends_lock = threading.Lock()


def _friends_path():
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / FRIENDS_FILE


def _clean_profile(data) -> dict:
    """The Riot ID / Discord part of a friend entry or of a member's state, checked."""
    result = {}
    if not isinstance(data, dict):
        return result
    for key in PROFILE_KEYS:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            continue
        if key == "dca" and not re.fullmatch(r"https://cdn\.discordapp\.com/[\w/.?=-]{1,160}", value):
            continue
        result[key] = value[:64] if key != "dca" else value
    return result


def load_friends() -> dict:
    """{"friends": [{"id", "key", "name"}], "removed": [summoner ids], "joined": [{"id", "name"}]}

    "joined" are the players who pasted our code: they come into our own room, we
    have no code of theirs, but they are friends all the same.
    """
    try:
        data = json.loads(_friends_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    friends = []
    for f in data.get("friends") or [] if isinstance(data, dict) else []:
        if not isinstance(f, dict):
            continue
        try:
            sid, key = int(f.get("id")), bytes.fromhex(str(f.get("key")))
        except (TypeError, ValueError):
            continue
        if sid > 0 and len(key) == 32:
            friends.append({"id": sid, "key": key.hex(), "name": str(f.get("name") or "")[:64], **_clean_profile(f)})
    removed = [r for r in (data.get("removed") or [] if isinstance(data, dict) else []) if isinstance(r, int)]
    joined = []
    for j in data.get("joined") or [] if isinstance(data, dict) else []:
        if not isinstance(j, dict):
            continue
        try:
            sid = int(j.get("id"))
        except (TypeError, ValueError):
            continue
        if sid > 0 and sid not in removed and all(f["id"] != sid for f in friends) and all(x["id"] != sid for x in joined):
            joined.append({"id": sid, "name": str(j.get("name") or "")[:64], **_clean_profile(j)})
    return {"friends": friends[:MAX_FRIENDS], "removed": removed, "joined": joined[:MAX_JOINED]}


def _save_friends(data: dict) -> bool:
    try:
        path = _friends_path()
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(path)
        return True
    except OSError as e:
        log.warning(f"[Share] Could not save friends: {e}")
        return False


def load_my_code() -> str:
    """The code we showed last (it stays the same: same account, same key)."""
    from utils.core.paths import get_user_data_dir
    try:
        data = json.loads((get_user_data_dir() / MY_CODE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    code = data.get("code") if isinstance(data, dict) else None
    return code if isinstance(code, str) else ""


def save_my_code(code: str) -> None:
    if not code or code == load_my_code():
        return
    from utils.core.paths import get_user_data_dir
    try:
        path = get_user_data_dir() / MY_CODE_FILE
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(json.dumps({"code": code}), encoding="utf-8")
        temporary.replace(path)
    except OSError as e:
        log.debug(f"[Share] Could not save our code: {e}")


def _code_matches(code: str, summoner_id, key) -> bool:
    """Whether a code is ours: same account, same key."""
    from party.protocol.token_codec import PartyToken
    try:
        token = PartyToken.decode(code)
    except ValueError:
        return False
    return bool(key) and token.summoner_id == summoner_id and token.encryption_key == key


def friend_room(friend: dict) -> str:
    from party.network.ws_relay import compute_room_key
    return compute_room_key(int(friend["id"]), bytes.fromhex(friend["key"]))


def add_friend(code: str) -> str:
    """Pair with a friend's code, for good. The answer is shown to the player."""
    from party.protocol.token_codec import PartyToken
    code = "".join(str(code or "").split())
    if not code:
        return "Önce arkadaşının kodunu yapıştır"
    try:
        token = PartyToken.decode(code)
    except ValueError:
        return "Bu bir Lust kodu değil: kodun tamamını kopyala (LUST: ile başlar)"
    manager = _runner.manager if _runner else None
    if manager is not None and token.summoner_id == manager.party_state.my_summoner_id:
        return "Bu senin kendi kodun: onu arkadaşına gönder"
    with _friends_lock:
        data = load_friends()
        if any(f["id"] == token.summoner_id for f in data["friends"]):
            return "Bu arkadaşla zaten eşleştin"
        if len(data["friends"]) >= MAX_FRIENDS:
            return f"En fazla {MAX_FRIENDS} arkadaşla eşleşebilirsin: önce birini çıkar"
        data["friends"].append({"id": token.summoner_id, "key": token.encryption_key.hex(), "name": ""})
        data["joined"] = [j for j in data["joined"] if j["id"] != token.summoner_id]
        data["removed"] = [r for r in data["removed"] if r != token.summoner_id]
        if not _save_friends(data):
            return "Arkadaş kaydedilemedi"
    log.info(f"[Share] Paired with summoner {token.summoner_id}")
    return "Eşleşildi: Lust açıkken skinlerinizi birbirinizde görürsünüz"


def remove_friend(summoner_id) -> str:
    try:
        sid = int(summoner_id)
    except (TypeError, ValueError):
        return ""
    with _friends_lock:
        data = load_friends()
        data["friends"] = [f for f in data["friends"] if f["id"] != sid]
        data["joined"] = [j for j in data["joined"] if j["id"] != sid]
        # They stop seeing us too, even though they kept our code (see Party Mode's "removed")
        if sid not in data["removed"]:
            data["removed"].append(sid)
        if not _save_friends(data):
            return "Arkadaş çıkarılamadı"
    return "Arkadaş çıkarıldı"


def _member_id(member) -> int:
    try:
        return int(member.get("summoner_id"))
    except (AttributeError, TypeError, ValueError):
        return 0


def _member_name(member) -> str:
    name = str(member.get("summoner_name") or "") if isinstance(member, dict) else ""
    return "" if name == "Unknown" else name[:64]


def _member_profile(member) -> dict:
    """{"name", "riot", "dc", "dcu", "dca"} a member shows now (empty values left out)."""
    skin = member.get("skin") if isinstance(member, dict) else None
    result = _clean_profile(skin)
    name = _member_name(member)
    if name:
        result["name"] = name
    return result


def _friend_row(f: dict, online: bool) -> dict:
    row = {"id": str(f["id"]), "name": f.get("name") or "Arkadaş", "online": online}
    row.update({key: f[key] for key in PROFILE_KEYS if f.get(key)})
    return row


def _remember_names(names: Dict[int, dict], joined: Optional[Dict[int, dict]] = None) -> None:
    """Keep friends' last name and profile (shown while they are away), and the players
    who joined our room with our code. names / joined: {summoner id: {"name", "riot", ...}}"""
    with _friends_lock:
        data = load_friends()
        changed = False
        for f in data["friends"] + data["joined"]:
            seen = names.get(f["id"]) or {}
            for key, value in seen.items():
                if value and f.get(key) != value:
                    f[key], changed = value, True
        known = {f["id"] for f in data["friends"] + data["joined"]} | set(data["removed"])
        for sid, seen in (joined or {}).items():
            if sid not in known and len(data["joined"]) < MAX_JOINED:
                data["joined"].append({"id": sid, "name": "", **{k: v for k, v in seen.items() if v}})
                known.add(sid)
                changed = True
        if changed:
            _save_friends(data)


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


def _my_profile(lcu) -> dict:
    """Our Riot ID (from the League client) and Discord account (if signed in in the hub)."""
    result = {}
    summoner = getattr(lcu, "current_summoner", None)
    if isinstance(summoner, dict):
        name, tag = summoner.get("gameName"), summoner.get("tagLine")
        if isinstance(name, str) and name:
            result["riot"] = f"{name}#{tag}" if isinstance(tag, str) and tag else name
    try:
        from launcher import lust_discord
        user = lust_discord.user()
    except Exception:  # noqa: BLE001
        user = None
    if user:
        if user.get("name"):
            result["dc"] = user["name"]
        if user.get("username"):
            result["dcu"] = user["username"]
        if user.get("avatar_url"):
            result["dca"] = user["avatar_url"]
    return _clean_profile(result)


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
            # Our own room, where friends who have our code find us
            from party.core.party_storage import load_party_key
            from party.network.ws_relay import compute_room_key
            self._my_key = load_party_key(my_id)
            self._home_room = compute_room_key(my_id, self._my_key)
            self.code()
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
            if self._ignored_peers:
                state["removed"] = sorted(self._ignored_peers)
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
            state.update(_my_profile(self.lcu))
            icon = _my_icon()
            if icon:
                state["icon_id"] = icon
                if self.my_puuid:
                    state["puuid"] = self.my_puuid
            return state or None

        def pair_rooms(self) -> Set[str]:
            """Our own room and our friends' rooms (always open)."""
            data = load_friends()
            removed = set(data["removed"])
            if removed != self._ignored_peers:
                self._ignored_peers = removed
                self._need_publish = True  # tell the rooms
            rooms = {self._home_room} if self._home_room else set()
            for friend in data["friends"]:
                try:
                    rooms.add(friend_room(friend))
                except (KeyError, ValueError):
                    continue
            return rooms

        def code(self) -> str:
            """Our code, the same one every time: Rose stamps a new time into it on each call,
            which made the code shown in the hub change every second."""
            saved = load_my_code()
            if saved and _code_matches(saved, self.party_state.my_summoner_id, self._my_key):
                return saved
            fresh = self._fresh_token() or ""
            save_my_code(fresh)
            return fresh

        def friends(self) -> List[dict]:
            members = self._merged_members()
            data = load_friends()
            # Who is in our own room pasted our code: a friend too
            home = self._relays.get(self._home_room) if self._home_room else None
            new = {}
            listed = {f["id"] for f in data["friends"] + data["joined"]}
            for member in list(home.members) if home else []:
                sid = _member_id(member)
                if sid and sid in members and sid not in listed:
                    new[sid] = _member_profile(members[sid][0])
            result, seen = [], {}
            for f in data["friends"] + data["joined"] + [{"id": k} for k in new]:
                entry = members.get(f["id"])
                now = _member_profile(entry[0]) if entry else {}
                if now:
                    seen[f["id"]] = now
                # Away: the name and accounts seen last
                result.append(_friend_row({**f, **now}, bool(entry and entry[1])))
            if seen or new:
                _remember_names(seen, new)
            return result

        async def sync_rooms(self, keys: Set[str], resume: bool = False) -> None:
            if getattr(self, "_need_publish", False):
                self._need_publish = False
                await self._publish_state()
            for key in [k for k in self._relays if k not in keys]:
                relay = self._relays.pop(key, None)
                if relay:
                    log.info(f"[Share] Leaving room {key[:8]}")
                    await relay.disconnect()
            for key in keys:
                if key in self._relays:
                    if resume:
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
        self._auto: Set[str] = set()
        self._phase = None
        self._paired: Set[str] = set()
        # Why sharing is not running while it should, for the hub ("" when it runs or League is closed)
        self.error = ""

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
            self.error = ""
            await self._stop()
            return
        if self.manager is None:
            if time.monotonic() - self._failed_at < RETRY_S:
                return
            if getattr(self.state, "party_manager", None) is not None:
                self.error = "party"
                return  # Rose's own Party Mode is running
            manager = _manager_class()(self.lcu, self.state, self.injection_manager)
            try:
                await manager.enable()
            except Exception as e:  # noqa: BLE001
                self._failed_at = time.monotonic()
                log.info(f"[Share] Not started: {e}")
                self.error = str(e)[:120] or "failed"
                await manager.disable()
                return
            self.error = ""
            self.manager = manager
            self.state.party_manager = manager
        keys = await asyncio.to_thread(rooms_for, self.lcu, self.state.phase)
        if keys is not None:
            self._auto = keys
        paired = self.manager.pair_rooms()
        # Rooms that gave up reconnecting try again when the party is needed: a new
        # lobby or champ select, or a friend just added
        phase = self.state.phase
        resume = (phase != self._phase and phase in LOBBY_PHASES + ("ChampSelect",)) or paired != self._paired
        self._phase, self._paired = phase, paired
        await self.manager.sync_rooms(self._auto | paired, resume=resume)

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
    """For the hub: whether sharing runs, our code, our friends, and how many Lust users see us now."""
    manager = _runner.manager if _runner else None
    result: Dict[str, object] = {"available": bool(relay_url()), "running": manager is not None, "peers": 0,
                                 "code": "", "friends": [], "error": _runner.error if _runner else ""}
    if manager is not None:
        try:
            result["peers"] = len(manager.party_state.peers)
            result["code"] = manager.code()
            result["friends"] = manager.friends()
        except Exception as e:  # noqa: BLE001
            log.debug(f"[Share] status: {e}")
    else:
        result["friends"] = [_friend_row(f, False) for data in [load_friends()] for f in data["friends"] + data["joined"]]
    if not result["code"]:
        # League closed or not connected yet: our code is still the same
        result["code"] = load_my_code()
    return result
