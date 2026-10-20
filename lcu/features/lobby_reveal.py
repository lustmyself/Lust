#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lobby Reveal
Reads the Riot IDs of champ select teammates from the Riot Client chat
(ranked hides them in the League client) and builds an op.gg multi-search link.
Same approach as https://github.com/steele123/reveal.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote

import psutil
import requests

from utils.core.logging import get_logger

log = get_logger()

UX_PROCESS_NAMES = {"leagueclientux.exe", "leagueclient.exe"}

# webRegion values that op.gg spells differently
OPGG_REGION_ALIASES = {"SG2": "SG"}
# Riot platform ids by webRegion
RIOT_PLATFORMS = {
    "NA": "na1", "EUW": "euw1", "EUNE": "eun1", "BR": "br1", "JP": "jp1", "OCE": "oc1",
    "TR": "tr1", "LAN": "la1", "LAS": "la2", "ME": "me1", "SG": "sg2", "PH": "ph2",
    "TH": "th2", "TW": "tw2", "VN": "vn2",
}
# Porofessor's region slugs, for platform ids that differ from them
POROFESSOR_REGIONS = {
    "NA1": "na", "EUW1": "euw", "EUN1": "eune", "EUNE": "eune", "BR1": "br", "JP1": "jp",
    "OC1": "oce", "TR1": "tr", "LA1": "lan", "LA2": "las", "ME1": "me", "SG2": "sg",
    "PH2": "ph", "TH2": "th", "TW2": "tw", "VN2": "vn",
}


@dataclass(frozen=True)
class RiotClientCredentials:
    port: int
    token: str


@dataclass
class RevealedPlayer:
    game_name: str
    game_tag: str
    puuid: str = ""
    position: str = ""
    cell_id: Optional[int] = None
    pick_turn: Optional[int] = None

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.game_tag}" if self.game_tag else self.game_name

    def to_payload(self, region: str, platform: str = "", poro_region: str = "") -> dict:
        return {
            "uggUrl": build_ugg_profile_url(self, platform) if platform else "",
            "poroUrl": build_porofessor_url([self], poro_region),
            "gameName": self.game_name,
            "gameTag": self.game_tag,
            "riotId": self.riot_id,
            # The plugin looks up rank, recent games and mains with it
            "puuid": self.puuid,
            "position": self.position,
            "opggUrl": build_opgg_profile_url(self, region) if region else "",
        }


def parse_riotclient_args(args: List[str]) -> Optional[RiotClientCredentials]:
    """Pull --riotclient-app-port / --riotclient-auth-token from a UX command line."""
    options: Dict[str, str] = {}
    for index, arg in enumerate(args):
        key, separator, value = arg.partition("=")
        if key not in {"--riotclient-app-port", "--riotclient-auth-token"}:
            continue
        if not separator and index + 1 < len(args):
            value = args[index + 1]
        options[key] = value.strip('"')
    port_text = options.get("--riotclient-app-port", "")
    token = options.get("--riotclient-auth-token", "")
    if not port_text.isdecimal() or not token:
        return None
    port = int(port_text)
    if not 0 < port < 65536:
        return None
    return RiotClientCredentials(port, token)


def find_riotclient_credentials() -> Optional[RiotClientCredentials]:
    """Riot Client endpoint from the running League client. Never log the token."""
    try:
        for proc in psutil.process_iter(attrs=["name"]):
            try:
                if (proc.info.get("name") or "").lower() not in UX_PROCESS_NAMES:
                    continue
                creds = parse_riotclient_args(proc.cmdline())
                if creds:
                    return creds
            except (psutil.Error, OSError, ValueError):
                continue
    except (psutil.Error, OSError) as e:
        log.debug(f"[Reveal] Could not list client processes: {e}")
    return None


def parse_participants(data: Optional[dict]) -> List[RevealedPlayer]:
    """Keep only champ select chat participants, as reveal does."""
    players = []
    for p in (data or {}).get("participants") or []:
        if "champ-select" not in str(p.get("cid", "")):
            continue
        name = p.get("game_name") or ""
        if not name:
            continue
        players.append(RevealedPlayer(
            game_name=name,
            game_tag=p.get("game_tag") or "",
            puuid=p.get("puuid") or "",
        ))
    return players


def apply_champ_select_session(players: List[RevealedPlayer], session: Optional[dict]) -> None:
    """Add roles and pick order from the champ select session, then sort by pick order."""
    by_puuid = {m.get("puuid"): m for m in (session or {}).get("myTeam") or [] if m.get("puuid")}
    for player in players:
        member = by_puuid.get(player.puuid)
        if not member:
            continue
        player.position = (member.get("assignedPosition") or "").lower()
        player.cell_id = member.get("cellId")
        player.pick_turn = member.get("pickTurn")
    players.sort(key=lambda p: (
        p.pick_turn if p.pick_turn is not None else 1 << 30,
        p.cell_id if p.cell_id is not None else 1 << 30,
    ))


def opgg_region(web_region: Optional[str]) -> str:
    region = (web_region or "").upper()
    return OPGG_REGION_ALIASES.get(region, region).lower()


def build_opgg_multi_url(players: List[RevealedPlayer], region: str) -> str:
    if not players or not region:
        return ""
    summoners = ",".join(p.riot_id for p in players)
    return f"https://www.op.gg/multisearch/{region}?summoners={quote(summoners)}"


def riot_platform(web_region: Optional[str]) -> str:
    """Riot platform id (euw1, na1, ...), which u.gg uses."""
    region = (web_region or "").upper()
    if region[-1:].isdigit() or region in {"KR", "RU"}:
        return region.lower()
    return RIOT_PLATFORMS.get(region, region.lower())


def build_ugg_multi_url(players: List[RevealedPlayer], platform: str) -> str:
    if not players or not platform:
        return ""
    summoners = ",".join(f"{p.game_name}-{p.game_tag}" if p.game_tag else p.game_name for p in players)
    return f"https://u.gg/lol/multisearch?region={platform}&summoners={quote(summoners)}"


def build_ugg_profile_url(player: RevealedPlayer, platform: str) -> str:
    slug = f"{player.game_name}-{player.game_tag}" if player.game_tag else player.game_name
    return f"https://u.gg/lol/profile/{platform}/{quote(slug)}/overview"


def porofessor_region(web_region: Optional[str]) -> str:
    region = (web_region or "").upper()
    return POROFESSOR_REGIONS.get(region, region.lower())


def build_porofessor_url(players: List[RevealedPlayer], region: str) -> str:
    """Porofessor's pre-game page for the whole team."""
    if not players or not region:
        return ""
    slugs = ",".join(
        quote(f"{p.game_name}-{p.game_tag}" if p.game_tag else p.game_name, safe="") for p in players
    )
    return f"https://porofessor.gg/pregame/{region}/{slugs}"


def build_opgg_profile_url(player: RevealedPlayer, region: str) -> str:
    slug = f"{player.game_name}-{player.game_tag}" if player.game_tag else player.game_name
    return f"https://www.op.gg/summoners/{region}/{quote(slug)}"


class RiotClientChat:
    """Minimal Riot Client API access for /chat/v5/participants."""

    def __init__(self):
        self._creds: Optional[RiotClientCredentials] = None
        self._session = requests.Session()
        self._session.verify = False  # self-signed cert on 127.0.0.1
        self._session.trust_env = False
        self._session.proxies.update({"http": None, "https": None})

    def reset(self) -> None:
        self._creds = None

    def get_participants(self, timeout: float = 2.0) -> Optional[dict]:
        if self._creds is None:
            self._creds = find_riotclient_credentials()
            if self._creds is None:
                return None
        try:
            r = self._session.get(
                f"https://127.0.0.1:{self._creds.port}/chat/v5/participants",
                auth=("riot", self._creds.token),
                timeout=timeout,
            )
        except requests.RequestException as e:
            log.debug(f"[Reveal] Riot Client chat unreachable: {e}")
            self._creds = None  # the client may have restarted with new credentials
            return None
        if r.status_code in (401, 403):
            self._creds = None
            return None
        if not r.ok:
            return None
        try:
            return r.json()
        except ValueError:
            return None
