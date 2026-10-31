"""Sign in with Discord: the hub shows the player's Discord name and avatar.

The hub opens Discord's sign-in page in the browser (OAuth2, scope "identify" only).
Discord sends the browser back to the hub's own address (/discord) with a short-lived
access token in the URL fragment; that page hands it to the hub together with the
one-time state the hub made, the hub asks Discord who signed in, keeps the name, id and
avatar in discord.json, and forgets the token. Nothing else from Discord is read.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from utils.core.logging import get_logger

log = get_logger()

# The Lust application on the Discord developer portal. Its OAuth2 redirects list
# http://127.0.0.1:47823/discord through http://127.0.0.1:47827/discord (the hub's ports).
CLIENT_ID = "1565953763796328478"
FILE = "discord.json"
AVATAR = "discord-avatar.png"
STATE_TTL_S = 600

_lock = threading.Lock()
_pending: dict = {}  # state -> time it was made


def _dir() -> Path:
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir()


def available() -> bool:
    return bool(CLIENT_ID)


def user() -> Optional[dict]:
    """{id, name, username, avatar} of the signed-in Discord account, or None."""
    try:
        data = json.loads((_dir() / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("id"):
        return None
    avatar = _dir() / AVATAR
    return {"id": str(data["id"]), "name": str(data.get("name") or data.get("username") or ""),
            "username": str(data.get("username") or ""),
            "avatar": int(avatar.stat().st_mtime) if avatar.exists() else 0}


def avatar_path() -> Path:
    return _dir() / AVATAR


def login_url(port: int) -> Optional[str]:
    """The Discord sign-in page; the browser comes back to this hub's /discord."""
    if not CLIENT_ID:
        return None
    state = secrets.token_urlsafe(24)
    now = time.time()
    with _lock:
        for old in [s for s, at in _pending.items() if now - at > STATE_TTL_S]:
            _pending.pop(old, None)
        _pending[state] = now
    return "https://discord.com/oauth2/authorize?" + urlencode({
        "client_id": CLIENT_ID, "response_type": "token", "scope": "identify",
        "redirect_uri": f"http://127.0.0.1:{port}/discord", "state": state, "prompt": "none",
    })


def _take_state(state: str) -> bool:
    with _lock:
        made = _pending.pop(state, None)
    return made is not None and time.time() - made <= STATE_TTL_S


def finish(access_token: str, state: str) -> str:
    """The browser came back from Discord: check the state, read who signed in."""
    if not isinstance(state, str) or not _take_state(state):
        return "Giriş süresi doldu, uygulamadan tekrar dene"
    if not isinstance(access_token, str) or not access_token:
        return "Discord girişi iptal edildi"
    import requests
    try:
        response = requests.get("https://discord.com/api/v10/users/@me", timeout=10,
                                headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        me = response.json()
    except (requests.RequestException, ValueError) as e:
        log.warning(f"[Discord] Could not read the account: {e}")
        return "Discord'a ulaşılamadı"
    if not isinstance(me, dict) or not me.get("id"):
        return "Discord hesabı okunamadı"
    data = {"id": str(me["id"]), "username": str(me.get("username") or ""),
            "name": str(me.get("global_name") or me.get("username") or "")}
    try:
        (_dir() / FILE).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        log.warning(f"[Discord] Could not save: {e}")
        return "Kaydedilemedi"
    _save_avatar(data["id"], me.get("avatar"))
    log.info("[Discord] Signed in")
    return f"Discord ile giriş yapıldı: {data['name']}"


def _save_avatar(user_id: str, avatar: Optional[str]) -> None:
    import requests
    if avatar:
        url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=128"
    else:
        url = f"https://cdn.discordapp.com/embed/avatars/{(int(user_id) >> 22) % 6}.png"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        avatar_path().write_bytes(response.content)
    except (requests.RequestException, OSError, ValueError) as e:
        log.info(f"[Discord] No avatar: {e}")


def logout() -> str:
    for name in (FILE, AVATAR):
        try:
            (_dir() / name).unlink(missing_ok=True)
        except OSError:
            pass
    return "Discord hesabından çıkış yapıldı"


CALLBACK_PAGE = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Lust · Discord</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0e2a;color:#e8e6ff;
font:15px/1.5 "Segoe UI",system-ui,sans-serif}main{text-align:center;padding:24px}b{display:block;font-size:20px;margin-bottom:6px}
span{color:#a5a3c9}</style></head><body><main><b id="t">Giriş yapılıyor…</b><span id="s">Bu sekmeyi kapatabilirsin.</span></main>
<script>
const p = new URLSearchParams(location.hash.slice(1));
history.replaceState(null, "", location.pathname);
fetch("/discord/finish", { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ access_token: p.get("access_token") || "", state: p.get("state") || "" }) })
  .then((r) => r.json()).then((out) => { document.getElementById("t").textContent = out.message || "Tamam"; })
  .catch(() => { document.getElementById("t").textContent = "Lust'a ulaşılamadı"; });
</script></body></html>"""
