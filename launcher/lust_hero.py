"""The desktop hub's welcome card: the player, their rank and their last match.

While the League client runs, its local API gives the Riot ID, solo queue rank and the
last match (champion, result, KDA); the card shows that champion's splash art behind
it. Both are kept in Lust's data folder, so the card still shows them while the client
is closed.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from utils.core.logging import get_logger

log = get_logger()

REFRESH_S = 120
HISTORY_END = 19  # the client's own match history range (20 games)
RETRY_S = 10  # until the client answers the first time
QUEUES = {420: "Dereceli Tek/Çift", 440: "Dereceli Esnek", 400: "Normal", 430: "Normal", 490: "Hızlı Oyun",
          480: "Hızlı Oyun", 450: "ARAM", 1700: "Arena", 1900: "URF", 900: "URF"}
TIERS = {"IRON": "Demir", "BRONZE": "Bronz", "SILVER": "Gümüş", "GOLD": "Altın", "PLATINUM": "Platin",
         "EMERALD": "Zümrüt", "DIAMOND": "Elmas", "MASTER": "Ustalık", "GRANDMASTER": "Üstatlık",
         "CHALLENGER": "Şampiyonluk"}
# Challenger and Grandmaster LP cutoffs per server, from replays.lol (one page lists them all)
CUTOFF_URL = "https://www.replays.lol/cutoff/TR/challenger"
CUTOFF_TTL_S = 30 * 60
CUTOFF_STALE_S = 7 * 24 * 3600
PLATFORMS = {"NA": "NA1", "EUW": "EUW1", "EUNE": "EUN1", "KR": "KR", "BR": "BR1", "JP": "JP1", "LAN": "LA1", "LA1": "LA1",
             "LAS": "LA2", "LA2": "LA2", "OCE": "OC1", "OC1": "OC1", "TR": "TR1", "RU": "RU", "SG": "SG2", "PH": "PH2",
             "TH": "TH2", "VN": "VN2", "TW": "TW2", "ME": "ME1"}
_CUTOFF_RE = re.compile(r'"region":"([A-Z0-9]+)","challenger":(\d+),"grandmaster":(\d+),"timeFetched":(\d+)')
_cutoff_lock = threading.Lock()
_cutoffs: dict = {}
_cutoffs_at = 0.0
_lock = threading.Lock()
_data: Optional[dict] = None
_miss_logged = False
_started = False


def _dir() -> Path:
    from utils.core.paths import get_user_data_dir
    path = get_user_data_dir() / "hero"
    path.mkdir(parents=True, exist_ok=True)
    return path


def image_path() -> Path:
    return _dir() / "splash.jpg"


def get() -> Optional[dict]:
    """The card's data, from the client or as last seen."""
    global _data, _miss_logged
    with _lock:
        if not _data:
            # Read again until it works: a miss at startup left the card empty until the client answered
            try:
                _data = json.loads((_dir() / "hero.json").read_text(encoding="utf-8")) or None
            except (OSError, ValueError) as exc:
                if not _miss_logged:
                    _miss_logged = True
                    log.debug(f"[Hero] No saved card yet: {exc}")
        return dict(_data) if _data else None


def parse_cutoffs(page: str) -> dict:
    """{platform: {"challenger": lp, "grandmaster": lp}} from the replays.lol page, fresh ones only."""
    now_ms = time.time() * 1000
    found = {}
    for platform, challenger, grandmaster, fetched in _CUTOFF_RE.findall(page.replace('\\"', '"')):
        if now_ms - int(fetched) < CUTOFF_STALE_S * 1000:
            found[platform] = {"challenger": int(challenger), "grandmaster": int(grandmaster)}
    return found


def cutoffs_for(region: str) -> Optional[dict]:
    """The server's Challenger and Grandmaster cutoffs (region as the client names it, e.g. TR)."""
    global _cutoffs, _cutoffs_at
    platform = PLATFORMS.get((region or "").upper(), (region or "").upper())
    with _cutoff_lock:
        if time.time() - _cutoffs_at > CUTOFF_TTL_S:
            try:
                response = requests.get(CUTOFF_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0 Lust"})
                response.raise_for_status()
                found = parse_cutoffs(response.text)
                if found:
                    _cutoffs = found
            except requests.RequestException as exc:
                log.debug(f"[Hero] Could not read the LP cutoffs: {exc}")
            _cutoffs_at = time.time()
        cutoff = _cutoffs.get(platform)
    return dict(cutoff, region=(region or "").upper()) if cutoff else None


def _rank_text(solo: dict) -> str:
    tier = solo.get("tier") or ""
    if not tier or tier == "NONE":
        return "Derecesiz"
    division = solo.get("division") or ""
    name = TIERS.get(tier, tier.title())
    if division and division != "NA" and tier not in ("MASTER", "GRANDMASTER", "CHALLENGER"):
        name += f" {division}"
    return f"{name} · {solo.get('leaguePoints', 0)} LP"


def refresh() -> bool:
    """Read the card from the client. False when the client isn't reachable."""
    global _data
    from launcher.lust_offline import _lcu_credentials
    creds = _lcu_credentials()
    if not creds:
        return False
    port, token = creds

    def get_json(path):
        response = requests.get(f"https://127.0.0.1:{port}{path}", auth=("riot", token), verify=False,
                                timeout=5, proxies={"http": None, "https": None})
        response.raise_for_status()
        return response

    try:
        summoner = get_json("/lol-summoner/v1/current-summoner").json()
        solo = (get_json("/lol-ranked/v1/current-ranked-stats").json().get("queueMap") or {}).get("RANKED_SOLO_5x5") or {}
        data = {
            "name": summoner.get("gameName") or summoner.get("displayName") or "",
            "tag": summoner.get("tagLine") or "",
            "level": summoner.get("summonerLevel") or 0,
            "rank": _rank_text(solo),
            "tier": (solo.get("tier") or "").lower(),
            "wins": solo.get("wins") or 0,
            "losses": solo.get("losses") or 0,
            "lp": solo.get("leaguePoints") or 0,
            "updated": int(time.time()),
        }
        try:
            data["cutoff"] = cutoffs_for(get_json("/riotclient/region-locale").json().get("region") or "")
        except (requests.RequestException, ValueError):
            pass
        # The client caches match history by whatever range was asked last and shows that in its
        # own Match History: asking for its usual 20 keeps that list whole (asking for 2 cut it to 2)
        games = ((get_json(f"/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex={HISTORY_END}")
                  .json().get("games") or {}).get("games") or [])
        games = sorted(games, key=lambda g: g.get("gameCreation") or 0, reverse=True)
        if games:
            game = games[0]
            player = game["participants"][0]
            stats = player.get("stats") or {}
            champion = get_json(f"/lol-game-data/assets/v1/champions/{int(player['championId'])}.json").json()
            data["last"] = {
                "champion": champion.get("name") or "",
                "win": bool(stats.get("win")),
                "kda": f"{stats.get('kills', 0)}/{stats.get('deaths', 0)}/{stats.get('assists', 0)}",
                "queue": QUEUES.get(game.get("queueId"), "Maç"),
                "when": game.get("gameCreationDate") or "",
            }
            skins = champion.get("skins") or []
            splash = (skins[0].get("uncenteredSplashPath") or skins[0].get("splashPath")) if skins else None
            if splash and (champion.get("name") != (get() or {}).get("last", {}).get("champion")
                           or not image_path().exists()):
                image_path().write_bytes(get_json(splash).content)
            data["image"] = int(image_path().stat().st_mtime) if image_path().exists() else 0
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, OSError) as exc:
        log.debug(f"[Hero] Could not read the card from the client: {exc}")
        return False
    with _lock:
        _data = data
        try:
            (_dir() / "hero.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return True


def start() -> None:
    global _started
    if _started:
        return
    _started = True

    def loop():
        from launcher.lust_perf import resting
        while True:
            if resting():
                time.sleep(30)  # performance mode: the card waits for the match to end
                continue
            try:
                ok = refresh()
            except Exception as exc:  # noqa: BLE001
                log.debug(f"[Hero] Refresh failed: {exc}")
                ok = False
            if ok:
                try:
                    from launcher import lust_profile
                    lust_profile.apply_pending()  # a background picked while League was closed
                except Exception as exc:  # noqa: BLE001
                    log.debug(f"[Hero] Profile background failed: {exc}")
            time.sleep(REFRESH_S if ok else RETRY_S)

    threading.Thread(target=loop, daemon=True, name="LustHero").start()
