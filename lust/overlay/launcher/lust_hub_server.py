"""The desktop hub's page, served on 127.0.0.1 to the WebView2 window (launcher/lust_hub_shell.py).

Every API call needs the token baked into the page and a 127.0.0.1 Host header, so other
web pages and DNS rebinding can't drive it. A window left open from a previous Lust (after
an update or a restart) gets 403, reloads, and picks up the new token.
"""

from __future__ import annotations

import json
import re
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

PORTS = range(47823, 47833)
PAGE_ALIVE_S = 4.0

_server: Optional[ThreadingHTTPServer] = None
_port = 0
_token = secrets.token_urlsafe(24)
_last_seen = 0.0
_lock = threading.Lock()


def page_open() -> bool:
    return time.time() - _last_seen < PAGE_ALIVE_S


def url() -> str:
    return f"http://127.0.0.1:{_port}/"


def _themes() -> list:
    from launcher.lust_spotify import PREVIEWS, THEMES
    return [{"key": key, "label": value[2], "bg": value[3], "accent": value[4], "preview": key in PREVIEWS}
            for key, value in THEMES.items()]


class _Handler(BaseHTTPRequestHandler):
    server_version = "LustHub"

    def log_message(self, *args) -> None:
        pass

    def _allowed_host(self) -> bool:
        return self.headers.get("Host", "") in (f"127.0.0.1:{_port}", f"localhost:{_port}")

    def _authorized(self) -> bool:
        return self._allowed_host() and secrets.compare_digest(self.headers.get("X-Lust-Hub", ""), _token)

    def _send(self, code: int, body: bytes = b"", kind: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        global _last_seen
        if not self._allowed_host():
            return self._send(403)
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            from config import APP_VERSION
            from launcher.lust_hub_web import render
            page = render(_token, APP_VERSION, _themes())
            return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/state":
            if not self._authorized():
                return self._send(403)
            _last_seen = time.time()
            from launcher import lust_hub
            return self._send(200, json.dumps(lust_hub.snapshot()).encode("utf-8"), "application/json")
        match = re.fullmatch(r"/preview/([a-z]+)\.png", path)
        if match:
            from launcher import lust_spotify
            preview = lust_spotify.preview_path(match.group(1)) if match.group(1) in lust_spotify.PREVIEWS else None
            if preview:
                return self._send(200, preview.read_bytes(), "image/png")
            return self._send(404)
        if path == "/hero.jpg":
            from launcher import lust_hero
            try:
                return self._send(200, lust_hero.image_path().read_bytes(), "image/jpeg")
            except OSError:
                return self._send(404)
        if path == "/api/maps":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_maps
            return self._send(200, lust_maps.dumps_listing(), "application/json")
        if path == "/api/fonts":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_fonts
            return self._send(200, lust_fonts.dumps_listing(), "application/json")
        if path == "/api/skins":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_skins
            return self._send(200, lust_skins.dumps_listing(), "application/json")
        if path == "/api/profile":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_profile
            return self._send(200, lust_profile.dumps_listing(), "application/json")
        if path == "/api/profile/skins":
            if not self._authorized():
                return self._send(403)
            from urllib.parse import parse_qs
            from launcher import lust_profile
            champion = (parse_qs(self.path.split("?", 1)[-1]).get("champion") or [""])[0]
            return self._send(200, lust_profile.dumps_skins(champion), "application/json")
        if path == "/map-preview":
            from urllib.parse import parse_qs
            from launcher import lust_maps
            map_id = (parse_qs(self.path.split("?", 1)[-1]).get("id") or [""])[0]
            found = lust_maps.preview_bytes(map_id) if map_id else None
            return self._send(200, *found) if found else self._send(404)
        if path == "/api/media":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_media
            return self._send(200, json.dumps(lust_media.state()).encode("utf-8"), "application/json")
        if path == "/api/level":
            if not self._authorized():
                return self._send(403)
            from launcher import lust_media
            return self._send(200, json.dumps({"level": round(lust_media.level(), 3)}).encode("utf-8"), "application/json")
        if path == "/cover.jpg":
            from launcher import lust_media
            try:
                return self._send(200, lust_media.cover_path().read_bytes(), "image/jpeg")
            except OSError:
                return self._send(404)
        if path == "/icon.png":
            try:
                from utils.core.paths import get_asset_path
                return self._send(200, get_asset_path("tray_ready.png").read_bytes(), "image/png")
            except OSError:
                return self._send(404)
        return self._send(404)

    def do_POST(self) -> None:  # noqa: N802
        if self._authorized() and self.path.startswith("/api/media/"):
            from launcher import lust_media
            ok = lust_media.control(self.path.rsplit("/", 1)[-1])
            return self._send(200 if ok else 404, b'{"ok": true}' if ok else b"", "application/json")
        if self._authorized() and self.path.startswith("/api/maps/upload"):
            from urllib.parse import parse_qs, unquote
            from launcher import lust_hub, lust_maps
            name = unquote((parse_qs(self.path.split("?", 1)[-1]).get("name") or [""])[0])
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            message = lust_maps.import_upload(name, self.rfile, length)
            if message:
                lust_hub.toast(message)
            return self._send(200, json.dumps({"message": message}).encode("utf-8"), "application/json")
        if self._authorized() and self.path.startswith("/api/fonts/upload"):
            from urllib.parse import parse_qs, unquote
            from launcher import lust_fonts, lust_hub
            name = unquote((parse_qs(self.path.split("?", 1)[-1]).get("name") or [""])[0])
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            message = lust_fonts.import_upload(name, self.rfile, length)
            if message:
                lust_hub.toast(message)
            return self._send(200, json.dumps({"message": message}).encode("utf-8"), "application/json")
        if self._authorized() and self.path.startswith("/api/skins/upload"):
            from urllib.parse import parse_qs, unquote
            from launcher import lust_hub, lust_skins
            name = unquote((parse_qs(self.path.split("?", 1)[-1]).get("name") or [""])[0])
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            message = lust_skins.import_upload(name, self.rfile, length)
            if message:
                lust_hub.toast(message)
            return self._send(200, json.dumps({"message": message}).encode("utf-8"), "application/json")
        if not self._authorized() or not self.path.startswith("/api/action/"):
            return self._send(403)
        name = self.path.rsplit("/", 1)[-1]
        from launcher import lust_hub
        if name not in lust_hub.ACTIONS:
            return self._send(404)
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 4096)
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        # Some actions take a while (Spotify themes); the page polls for the result
        threading.Thread(target=lust_hub.run_action, args=(name, body if isinstance(body, dict) else {}),
                         daemon=True, name=f"LustHub-{name}").start()
        return self._send(200, b'{"ok": true}', "application/json")


class _Server(ThreadingHTTPServer):
    # Windows lets SO_REUSEADDR share a port another process listens on; the hub's must be its own
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def start() -> bool:
    global _server, _port
    with _lock:
        if _server:
            return True
        for port in PORTS:
            try:
                server = _Server(("127.0.0.1", port), _Handler)
            except OSError:
                continue
            _server, _port = server, port
            threading.Thread(target=server.serve_forever, daemon=True, name="LustHubServer").start()
            log.info(f"[Hub] Serving the hub page on 127.0.0.1:{port}")
            return True
    log.warning("[Hub] No free port for the hub page")
    return False
