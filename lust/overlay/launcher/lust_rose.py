"""Rose installed next to Lust: both register their Pengu Loader for League in the same
place, so with Rose running the client loads Rose's plugins too (its rose icon beside LUST).

The desktop hub tells the player and offers Rose's own uninstaller, which opens visibly
and asks them; Lust never removes another program by itself.
"""

from __future__ import annotations

import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

import psutil

from utils.core.logging import get_logger

log = get_logger()

UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"


def _uninstaller_from_registry() -> Optional[Path]:
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY, 0, winreg.KEY_READ | view) as root:
                for index in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, index)) as key:
                            if winreg.QueryValueEx(key, "DisplayName")[0] != "Rose":
                                continue
                            command = winreg.QueryValueEx(key, "UninstallString")[0]
                    except OSError:
                        continue
                    path = Path(command.strip().strip('"'))
                    if path.is_file():
                        return path
        except OSError:
            continue
    return None


def _folder() -> Optional[Path]:
    folder = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Rose"
    return folder if (folder / "Rose.exe").is_file() else None


def status() -> dict:
    running = any((p.info.get("name") or "").lower() == "rose.exe" for p in psutil.process_iter(["name"]))
    uninstaller = _uninstaller_from_registry()
    folder = _folder()
    if not uninstaller and folder and (folder / "unins000.exe").is_file():
        uninstaller = folder / "unins000.exe"
    return {"installed": bool(uninstaller or folder), "running": running, "can_uninstall": bool(uninstaller)}


def uninstall() -> str:
    """Close Rose and open its own uninstaller. Returns the message for the hub."""
    current = status()
    if not current["installed"]:
        return "Rose kurulu değil"
    for proc in psutil.process_iter(["name"]):
        if (proc.info.get("name") or "").lower() == "rose.exe":
            try:
                proc.terminate()
            except psutil.Error:
                pass
    uninstaller = _uninstaller_from_registry()
    folder = _folder()
    if not uninstaller and folder and (folder / "unins000.exe").is_file():
        uninstaller = folder / "unins000.exe"
    if not uninstaller:
        return "Rose kapatıldı; kaldırmak için Windows Ayarlar > Uygulamalar'dan Rose'u kaldır"
    try:
        subprocess.Popen([str(uninstaller)], close_fds=True)
    except OSError as exc:
        log.warning(f"[Rose] Could not open Rose's uninstaller: {exc}")
        return "Rose'un kaldırıcısı açılamadı"
    log.info(f"[Rose] Opened Rose's uninstaller: {uninstaller}")
    return "Rose'un kaldırıcısı açıldı: onaylayınca Rose kaldırılır, sonra League'i yeniden başlat"
