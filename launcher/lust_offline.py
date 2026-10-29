"""Start League through Lust Offline, the chat proxy that lets you appear offline.

Lust Offline (lust/offline, a rebranded Deceive) must start the Riot Client itself
so it can route chat through its proxy. Lust does that when it starts: a Riot
Client idling in the background is closed and restarted through the proxy, an
open game is left alone (closing it would be worse than appearing online), and
nothing starts when Lust itself was started with Windows.

After that a watcher covers League opened the usual way while Lust runs: a Riot
Client starting for League without the proxy (the League shortcut), or a League
client just started from a Riot Client that was already open, is closed at once
and started again through Lust Offline. Other games are never touched.
"""

from __future__ import annotations

import ctypes
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

import psutil
import pystray
import requests

from utils.core.logging import get_logger
from utils.core.paths import get_assets_dir

log = get_logger()

# Lust's autostart runs at logon; don't open League by itself then.
BOOT_GRACE_MS = 3 * 60 * 1000
GAME_PROCESSES = {
    "leagueclient.exe",
    "leagueclientux.exe",
    "league of legends.exe",
    "valorant-win64-shipping.exe",
    "lor.exe",
    "lustoffline.exe",
}
RIOT_CLIENT_PROCESSES = {"riotclientservices.exe", "riot client.exe", "riotclientux.exe"}
LEAGUE_CLIENT_PROCESSES = {"leagueclient.exe", "leagueclientux.exe"}
WATCH_INTERVAL_S = 1.0
# A League client younger than this is still starting up and safe to restart.
FRESH_CLIENT_S = 20
RESTART_COOLDOWN_S = 30


def _processes(names):
    found = []
    for proc in psutil.process_iter(["name"]):
        if (proc.info.get("name") or "").lower() in names:
            found.append(proc)
    return found


def _started_at_logon() -> bool:
    """Start with Windows runs Lust from Task Scheduler, whose host is svchost.exe."""
    try:
        parent = psutil.Process().parent()
        return bool(parent) and (parent.name() or "").lower() == "svchost.exe"
    except psutil.Error:
        return False


def _exe():
    return get_assets_dir().parent / "injection" / "tools" / "LustOffline.exe"


def _close(names):
    procs = _processes(names)
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    psutil.wait_procs(procs, timeout=5)
    if procs:
        time.sleep(2)  # the Riot Client takes a moment to release its ports


# Lust Offline points the Riot Client's chat at this name, which public DNS answers with
# 127.0.0.1. Some ISPs and routers (DNS rebinding protection) refuse such answers, and
# Lust Offline then stops with "failing to resolve some required domains". Lust runs as
# administrator, so it puts the name in the hosts file instead of making the player do it.
LOCALHOST_DOMAIN = "deceive-localhost.molenzwiebel.xyz"
HOSTS_ENTRY = f"127.0.0.1 {LOCALHOST_DOMAIN}"


def _hosts_file() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"


def _hosts_has_entry(text: str) -> bool:
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 2 and fields[0] == "127.0.0.1" and LOCALHOST_DOMAIN in (f.lower() for f in fields[1:]):
            return True
    return False


def _resolves_to_loopback() -> bool:
    try:
        infos = socket.getaddrinfo(LOCALHOST_DOMAIN, None, socket.AF_INET)
    except OSError:
        return False
    return any(info[4][0] == "127.0.0.1" for info in infos)


def ensure_localhost_resolution() -> bool:
    """Make LOCALHOST_DOMAIN resolve to 127.0.0.1, adding a hosts entry when DNS won't."""
    hosts = _hosts_file()
    try:
        text = hosts.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    if _hosts_has_entry(text) or _resolves_to_loopback():
        return True
    log.info(f"[LustOffline] {LOCALHOST_DOMAIN} does not resolve to 127.0.0.1; adding it to the hosts file")
    try:
        if hosts.exists():
            os.chmod(hosts, 0o666)  # clears a read-only flag
        with open(hosts, "a", encoding="utf-8") as f:
            if text and not text.endswith("\n"):
                f.write("\n")
            f.write(f"{HOSTS_ENTRY}  # Lust Offline\n")
    except OSError as exc:
        log.warning(f"[LustOffline] Could not add {LOCALHOST_DOMAIN} to the hosts file: {exc}")
        return False
    try:
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        pass
    return True


def _launch(exe) -> bool:
    ensure_localhost_resolution()
    try:
        subprocess.Popen(
            [str(exe), "lol"],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        return True
    except OSError as exc:
        log.warning(f"[LustOffline] Could not start Lust Offline: {exc}")
        return False


def league_without_proxy() -> bool:
    """League is starting through a Riot Client that doesn't route chat through Lust Offline."""
    if _processes({"lustoffline.exe", "league of legends.exe"}):
        return False
    services = _processes({"riotclientservices.exe"})
    if not services:
        return False
    for proc in services:
        try:
            args = " ".join(proc.cmdline())
        except psutil.Error:
            continue
        if "--client-config-url" in args:
            return False
        if "--launch-product=league_of_legends" in args:
            return True
    # Play pressed in a Riot Client that was already open
    now = time.time()
    for proc in _processes(LEAGUE_CLIENT_PROCESSES):
        try:
            if now - proc.create_time() < FRESH_CLIENT_S:
                return True
        except psutil.Error:
            continue
    return False


def _watch(exe) -> None:
    while True:
        try:
            if league_without_proxy():
                log.info("[LustOffline] League opened without Lust Offline; restarting it through Lust Offline")
                _close(LEAGUE_CLIENT_PROCESSES | RIOT_CLIENT_PROCESSES)
                if _launch(exe):
                    time.sleep(RESTART_COOLDOWN_S)
        except Exception as exc:  # keep watching whatever happens
            log.debug(f"[LustOffline] Watch failed: {exc}")
        # Performance mode: during a match nobody opens League a second time, so look less often
        from launcher.lust_perf import resting
        time.sleep(WATCH_INTERVAL_S * 5 if resting() else WATCH_INTERVAL_S)


# ---- Status (Lust's tray menu) ----

# Lust Offline takes commands as chat messages to its "Lust Active!" friend and keeps
# the status it applies in this file ("chat" is online).
STATUS_FILE = Path(os.environ.get("APPDATA", "")) / "Lust Offline" / "status"
LUST_OFFLINE_FRIEND = "41c322a1-b328-495b-a004-5ccd3e45eae8@eu1.pvp.net"
STATUSES = [("online", "Online"), ("offline", "Offline"), ("mobile", "Mobile")]


def lust_offline_running() -> bool:
    return bool(_processes({"lustoffline.exe"}))


def _status_from_chat() -> str:
    """The status Lust Offline last confirmed in its chat ("You are now appearing offline")."""
    creds = _lcu_credentials()
    if not creds:
        return ""
    port, token = creds
    url = f"https://127.0.0.1:{port}/lol-chat/v1/conversations/{quote(LUST_OFFLINE_FRIEND, safe='')}/messages"
    try:
        messages = requests.get(url, auth=("riot", token), verify=False, timeout=2,
                                proxies={"http": None, "https": None}).json()
    except (requests.RequestException, ValueError):
        return ""
    for message in reversed(messages if isinstance(messages, list) else []):
        match = re.search(r"appearing (online|offline|mobile)", str(message.get("body", "")), re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return ""


def current_status() -> str:
    # Lust Offline writes its status file only now and then, so its chat comes first
    status = _status_from_chat()
    if status:
        return status
    try:
        status = STATUS_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return "online" if status == "chat" else status


def _lcu_credentials():
    """App port and token from the League client's command line. Never log the token."""
    for proc in _processes({"leagueclientux.exe"}):
        try:
            args = proc.cmdline()
        except psutil.Error:
            continue
        options = dict(arg.split("=", 1) for arg in args if arg.startswith("--") and "=" in arg)
        port, token = options.get("--app-port", ""), options.get("--remoting-auth-token", "")
        if port.isdecimal() and token:
            return int(port), token
    return None


def set_status(command: str) -> bool:
    creds = _lcu_credentials()
    if not creds:
        return False
    port, token = creds
    url = f"https://127.0.0.1:{port}/lol-chat/v1/conversations/{quote(LUST_OFFLINE_FRIEND, safe='')}/messages"
    try:
        response = requests.post(url, json={"body": command, "type": "chat"}, auth=("riot", token),
                                 verify=False, timeout=3, proxies={"http": None, "https": None})
        return response.ok
    except requests.RequestException as exc:
        log.warning(f"[LustOffline] Could not change status: {exc}")
        return False


def tray_status_menu() -> pystray.Menu:
    """Online / Offline / Mobile for Lust's tray icon (Lust Offline's own is hidden)."""
    def item(command, label):
        return pystray.MenuItem(
            label,
            lambda icon, menu_item: set_status(command),
            checked=lambda menu_item: lust_offline_running() and current_status() == command,
            radio=True,
            enabled=lambda menu_item: lust_offline_running(),
        )

    return pystray.Menu(
        *(item(command, label) for command, label in STATUSES),
        pystray.MenuItem(
            "League wasn't started through Lust",
            None,
            enabled=False,
            visible=lambda menu_item: not lust_offline_running(),
        ),
    )


def start_league_through_lust_offline() -> None:
    if sys.platform != "win32":
        return
    exe = _exe()
    if not exe.exists():
        log.warning(f"[LustOffline] {exe} is missing; League is not started")
        return
    threading.Thread(target=_watch, args=(exe,), daemon=True, name="LustOfflineWatch").start()

    uptime = ctypes.windll.kernel32.GetTickCount64
    uptime.restype = ctypes.c_ulonglong
    if uptime() < BOOT_GRACE_MS or _started_at_logon():
        log.info("[LustOffline] Started with Windows; leaving League closed")
        return
    from launcher.lust_settings import enabled
    if not enabled("launch_league"):
        log.info("[LustOffline] Opening League with Lust is off in the hub's settings")
        return
    games = _processes(GAME_PROCESSES)
    if games:
        log.info(f"[LustOffline] {games[0].info['name']} is already running; not restarting it")
        return
    _close(RIOT_CLIENT_PROCESSES)
    if _launch(exe):
        log.info("[LustOffline] Started League through Lust Offline")
