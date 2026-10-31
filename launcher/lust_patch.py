"""League's latest patch notes for the hub's Patch notes tile and page.

Riot's Turkish news site lists the patch notes; the newest article's champion section gives
the champions that changed, each with Riot's one-line summary. A copy is kept on disk so the
page has something to show offline, and the site is read again every few hours.
"""

from __future__ import annotations

import html
import json
import re
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

SITE = "https://www.leagueoflegends.com"
INDEX_URL = SITE + "/tr-tr/news/tags/patch-notes/"
TTL_S = 6 * 60 * 60
CACHE_FILE = "lust-patch-notes.json"
ICON_URL = ("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"
            "v1/champion-icons/{id}.png")

_lock = threading.Lock()
_notes: dict = {"at": 0.0, "data": None}
_busy = threading.Lock()

LINK_RE = re.compile(r'href="((?:https://www\.leagueoflegends\.com)?/[a-z]{2}-[a-z]{2}/news/game-updates/'
                     r'[^"#?]*patch[^"#?]*notes[^"#?]*)"', re.I)
VERSION_RE = re.compile(r"patch-(\d{1,2})-(\d{1,2})", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def _text(fragment: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def latest_link(index_html: str) -> Optional[str]:
    """The newest patch notes article on the index page (the site lists newest first)."""
    match = LINK_RE.search(index_html or "")
    if not match:
        return None
    link = match.group(1)
    return link if link.startswith("http") else SITE + link


def version_of(link: str) -> str:
    match = VERSION_RE.search(link or "")
    return f"{match.group(1)}.{match.group(2)}" if match else ""


def _section(article: str, ids) -> str:
    """The article's text from the first <h2> whose id is one of `ids` to the next <h2>."""
    for section_id in ids:
        start = re.search(rf'<h2[^>]*id="{section_id}"', article, re.I)
        if start:
            end = re.search(r"<h2[\s>]", article[start.end():], re.I)
            return article[start.end(): start.end() + end.start()] if end else article[start.end():]
    return ""


def parse_article(article: str) -> dict:
    """{title, champions: [{name, alias, summary}], items} from a patch notes article."""
    title = ""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", article or "", re.I | re.S)
    if match:
        title = _text(match.group(1))
    champions = []
    section = _section(article or "", ("patch-champions", "patch-champion"))
    blocks = re.split(r"(?=<h3[^>]*class=\"[^\"]*change-title)", section, flags=re.I)
    for block in blocks:
        head = re.match(r'<h3[^>]*class="[^"]*change-title[^"]*"[^>]*>(.*?)</h3>', block, re.I | re.S)
        if not head:
            continue
        name = _text(head.group(1))
        if not name or len(name) > 40:
            continue
        alias = ""
        anchor = re.search(r'id="patch-([a-z0-9-]+)"', block[:300], re.I)
        if anchor:
            alias = anchor.group(1).replace("-", "").lower()
        summary = ""
        quote = re.search(r"<blockquote[^>]*>(.*?)</blockquote>", block, re.I | re.S)
        if quote:
            summary = _text(quote.group(1))[:280]
        champions.append({"name": name, "alias": alias, "summary": summary})
    items = len(re.findall(r'class="[^"]*change-title', _section(article or "", ("patch-items",)), re.I))
    return {"title": title, "champions": champions[:80], "items": items}


def _with_icons(champions: list) -> list:
    """Each champion with its CommunityDragon icon, matched by alias or name."""
    try:
        from launcher import lust_skins
        known = lust_skins.champions()
    except Exception:  # noqa: BLE001
        known = []
    key = lambda value: re.sub(r"[^a-z0-9]", "", (value or "").casefold())  # noqa: E731
    by_alias = {c["alias"]: c["id"] for c in known}
    by_name = {key(c["name"]): c["id"] for c in known}
    out = []
    for champion in champions:
        cid = by_alias.get(champion.get("alias")) or by_name.get(key(champion.get("name")))
        out.append(dict(champion, icon=ICON_URL.format(id=cid) if cid else ""))
    return out


def _get(url: str) -> str:
    import requests
    from config import APP_USER_AGENT
    response = requests.get(url, timeout=10, headers={"User-Agent": APP_USER_AGENT, "Accept-Language": "tr-TR,tr"})
    response.raise_for_status()
    return response.text


def _cache_path() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / CACHE_FILE


def _read_cache() -> Optional[dict]:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("url") else None


def fetch() -> Optional[dict]:
    """Read the newest patch notes from Riot's site."""
    link = latest_link(_get(INDEX_URL))
    if not link:
        log.info("[Patch] No patch notes link on the news page")
        return None
    data = parse_article(_get(link))
    data.update(url=link, version=version_of(link), fetched=int(time.time()),
                champions=_with_icons(data["champions"]))
    try:
        _cache_path().write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return data


def _refresh() -> None:
    if not _busy.acquire(blocking=False):
        return
    try:
        data = fetch()
    except Exception as e:  # noqa: BLE001
        log.info(f"[Patch] Could not read the patch notes: {e}")
        data = None
    finally:
        _busy.release()
    with _lock:
        if data:
            _notes.update(at=time.monotonic(), data=data)
        else:
            # Try again in ten minutes instead of hours
            _notes["at"] = time.monotonic() - TTL_S + 600


def notes() -> dict:
    """What the hub shows right away: the newest notes it has (from disk at first), reading
    Riot's site again in the background when they are old. {} until anything is known."""
    with _lock:
        data, at = _notes["data"], _notes["at"]
    if data is None:
        data = _read_cache()
        with _lock:
            _notes["data"] = data
    if not at or time.monotonic() - at > TTL_S:
        with _lock:
            _notes["at"] = time.monotonic()
        threading.Thread(target=_refresh, daemon=True, name="LustPatchNotes").start()
    return dict(data or {}, loading=_busy.locked())


def summary() -> dict:
    data = notes()
    return {"version": data.get("version", ""), "changed": len(data.get("champions") or []),
            "icons": [c["icon"] for c in (data.get("champions") or []) if c.get("icon")][:5]}


def open_notes() -> str:
    url = (notes() or {}).get("url") or INDEX_URL
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        return "Tarayıcı açılamadı"
    return "Yama notları tarayıcıda açılıyor"


def dumps() -> bytes:
    return json.dumps(notes(), ensure_ascii=False).encode("utf-8")
