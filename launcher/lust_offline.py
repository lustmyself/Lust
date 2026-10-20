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
import subprocess
import sys
import threading
import time

import psutil

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


def _launch(exe) -> bool:
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
        time.sleep(WATCH_INTERVAL_S)


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
    games = _processes(GAME_PROCESSES)
    if games:
        log.info(f"[LustOffline] {games[0].info['name']} is already running; not restarting it")
        return
    _close(RIOT_CLIENT_PROCESSES)
    if _launch(exe):
        log.info("[LustOffline] Started League through Lust Offline")
