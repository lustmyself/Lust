"""Start League through Lust Offline, the chat proxy that lets you appear offline.

Lust Offline (lust/offline, a rebranded Deceive) must start the Riot Client itself
so it can route chat through its proxy. Lust does that when it starts. A Riot
Client idling in the background is closed and restarted through the proxy; an
open game is left alone (closing it would be worse than appearing online), and
nothing starts when Lust itself was started with Windows.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
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


def _close_riot_client():
    procs = _processes(RIOT_CLIENT_PROCESSES)
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    psutil.wait_procs(procs, timeout=5)
    if procs:
        time.sleep(2)  # the Riot Client takes a moment to release its ports


def start_league_through_lust_offline() -> None:
    if sys.platform != "win32":
        return
    exe = get_assets_dir().parent / "injection" / "tools" / "LustOffline.exe"
    if not exe.exists():
        log.warning(f"[LustOffline] {exe} is missing; League is not started")
        return
    uptime = ctypes.windll.kernel32.GetTickCount64
    uptime.restype = ctypes.c_ulonglong
    if uptime() < BOOT_GRACE_MS or _started_at_logon():
        log.info("[LustOffline] Started with Windows; leaving League closed")
        return
    games = _processes(GAME_PROCESSES)
    if games:
        log.info(f"[LustOffline] {games[0].info['name']} is already running; not restarting it")
        return
    try:
        _close_riot_client()
        subprocess.Popen(
            [str(exe), "lol"],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        log.info("[LustOffline] Started League through Lust Offline")
    except OSError as exc:
        log.warning(f"[LustOffline] Could not start Lust Offline: {exc}")
