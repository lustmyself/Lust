#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Take the LTK patcher from an LTK Manager install.

LTK Manager (https://github.com/LeagueToolkit/ltk-manager) ships
ltk_patcher_host.exe and ltk_patcher_dll.dll in its install folder. When one
is installed, Lust copies both into its tools folder itself, and again
whenever LTK Manager has a newer patcher, so users never move files by hand.
Lust ships no copy of its own.

Since October 2026 some patcher builds verify their host and refuse any program
but LTK Manager ("host verification failed, refusing overlay"). Lust never
copies such a build over a working one: the copy it replaces is kept in
ltk-patcher-backup, a build that refused Lust is remembered by its SHA-256, and
the player can put a patcher of their own in Lust's data folder (ltk-patcher).
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from utils.core.logging import get_logger

from .patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, check_ltk_patcher

log = get_logger()

LTK_MANAGER_URL = "https://github.com/LeagueToolkit/ltk-manager/releases/latest"
LTK_MANAGER_NAME = "LTK Manager"

HOST_LOCK_MARKER = b"host verification failed"
HOST_LOCK_LINE = "host verification failed"
BACKUP_DIR = "ltk-patcher-backup"
REFUSED_FILE = "ltk-patcher-refused.txt"
USER_PATCHER_DIR = "ltk-patcher"

_UNINSTALL_KEYS = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
)


def _registry_install_dirs() -> List[Path]:
    """Install folders of LTK Manager from the Windows uninstall entries."""
    if sys.platform != "win32":
        return []
    import winreg

    dirs = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in _UNINSTALL_KEYS:
            try:
                root = winreg.OpenKey(hive, key_path)
            except OSError:
                continue
            with root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, i)) as entry:
                            values = {}
                            for name in ("DisplayName", "InstallLocation", "DisplayIcon"):
                                try:
                                    values[name] = str(winreg.QueryValueEx(entry, name)[0])
                                except OSError:
                                    pass
                    except OSError:
                        continue
                    if values.get("DisplayName", "").strip().lower() != LTK_MANAGER_NAME.lower():
                        continue
                    if values.get("InstallLocation"):
                        dirs.append(Path(values["InstallLocation"].strip('"')))
                    if values.get("DisplayIcon"):
                        icon = values["DisplayIcon"].split(",")[0].strip('"')
                        dirs.append(Path(icon).parent)
    return dirs


def user_patcher_dir() -> Path:
    """Where the player puts a patcher of their own (no admin rights needed)."""
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / USER_PATCHER_DIR


def _default_install_dirs() -> List[Path]:
    dirs = []
    try:
        folder = user_patcher_dir()
        folder.mkdir(parents=True, exist_ok=True)
        dirs.append(folder)
    except OSError:
        pass
    for var, sub in (
        ("ProgramFiles", LTK_MANAGER_NAME),
        ("ProgramFiles(x86)", LTK_MANAGER_NAME),
        ("LOCALAPPDATA", LTK_MANAGER_NAME),  # older per-user installs
        ("LOCALAPPDATA", os.path.join("Programs", LTK_MANAGER_NAME)),
    ):
        base = os.environ.get(var)
        if base:
            dirs.append(Path(base) / sub)
    return dirs


def find_ltk_manager_patchers(extra_dirs: Iterable[Path] = ()) -> List[Path]:
    """Folders holding both patcher files, from LTK Manager installs."""
    found, seen = [], set()
    for folder in [*extra_dirs, *_registry_install_dirs(), *_default_install_dirs()]:
        try:
            key = os.path.normcase(str(folder.resolve()))
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        if (folder / LTK_PATCHER_HOST).is_file() and (folder / LTK_PATCHER_DLL).is_file():
            found.append(folder)
    return found


def _dll_digest(folder: Path) -> Optional[str]:
    try:
        return hashlib.sha256((folder / LTK_PATCHER_DLL).read_bytes()).hexdigest()
    except OSError:
        return None


def _refused_digests(tools_dir: Path) -> set:
    try:
        return {line.strip() for line in (tools_dir / REFUSED_FILE).read_text(encoding="utf-8").splitlines()
                if line.strip()}
    except OSError:
        return set()


def host_locked(folder: Path, tools_dir: Path) -> bool:
    """True when the patcher in folder only runs inside LTK Manager."""
    try:
        data = (folder / LTK_PATCHER_DLL).read_bytes()
    except OSError:
        return False
    return HOST_LOCK_MARKER in data or hashlib.sha256(data).hexdigest() in _refused_digests(tools_dir)


def _copy_pair(source: Path, target: Path) -> None:
    """Copy both patcher files, staged so a failure never mixes two releases."""
    target.mkdir(parents=True, exist_ok=True)
    staged = {name: target / f".{name}.tmp" for name in (LTK_PATCHER_DLL, LTK_PATCHER_HOST)}
    try:
        for name, tmp in staged.items():
            shutil.copyfile(source / name, tmp)
        for name, tmp in staged.items():
            os.replace(tmp, target / name)
    finally:
        for tmp in staged.values():
            try:
                tmp.unlink()
            except OSError:
                pass


def import_from_ltk_manager(tools_dir: Path, extra_dirs: Iterable[Path] = ()) -> Optional[Path]:
    """Copy LTK Manager's patcher into tools_dir when it is newer than (or
    replaces a missing, unreadable or host-locked) one there. Returns the folder
    copied from, or None when nothing was copied."""
    current = check_ltk_patcher(tools_dir)
    current_locked = not current.missing and host_locked(tools_dir, tools_dir)
    backup = tools_dir / BACKUP_DIR
    candidates = list(find_ltk_manager_patchers(extra_dirs))
    if (backup / LTK_PATCHER_HOST).is_file() and (backup / LTK_PATCHER_DLL).is_file():
        candidates.append(backup)

    best, best_eol = None, None
    for folder in candidates:
        if host_locked(folder, tools_dir):
            log.warning(f"[LTK] Not taking the patcher in {folder}: it only runs inside LTK Manager")
            continue
        eol = check_ltk_patcher(folder).eol
        if eol is None:
            log.warning(f"[LTK] Ignoring unrecognized patcher DLL in {folder}")
            continue
        if best_eol is None or eol > best_eol:
            best, best_eol = folder, eol

    if best is None:
        return None
    if not current.missing and not current_locked and current.eol is not None and current.eol >= best_eol:
        return None  # what Lust has is as new as LTK Manager's

    try:
        if best == backup:
            _copy_pair(backup, tools_dir)
        else:
            if not current.missing and not current_locked:
                _copy_pair(tools_dir, backup)  # the working copy stays at hand
            _copy_pair(best, tools_dir)
    except OSError as e:
        log.warning(f"[LTK] Could not copy the patcher from {best}: {e}")
        return None
    log.info(f"[LTK] Copied the LTK patcher from {best}")
    return best


def _locked_text() -> tuple:
    folder = user_patcher_dir()
    turkish = ("Skinler yüklenmiyor: LTK Manager'ın yeni patcher'ı yalnızca LTK Manager içinde çalışıyor "
               "ve Lust'ı reddediyor. Kilitsiz (eski) ltk_patcher_host.exe ve ltk_patcher_dll.dll "
               f"dosyalarını {folder} klasörüne koy, sonra Lust'ı yeniden başlat.")
    english = ("Put an LTK patcher without host verification (ltk_patcher_host.exe and ltk_patcher_dll.dll) "
               f"in {folder}, then restart Lust. Lust no longer copies a locked patcher over a working one.")
    return turkish, english


def _tell_player(message: str) -> None:
    turkish, english = _locked_text()
    try:
        from launcher import lust_hub
        lust_hub.toast(turkish)
    except Exception:  # noqa: BLE001
        pass
    try:
        from utils.core.issue_reporter import report_issue
        report_issue("LTK_PATCHER_FAILED", "error", message, hint=english)
    except Exception:  # noqa: BLE001
        pass


def warn_if_host_locked(tools_dir: Path) -> bool:
    """At startup: tell the player when the only patcher Lust has refuses Lust."""
    status = check_ltk_patcher(tools_dir)
    if status.missing or not host_locked(tools_dir, tools_dir):
        return False
    log.error("[LTK] The LTK patcher in Lust's tools folder only runs inside LTK Manager: skins will not load")
    _tell_player("Skins will not load: this LTK patcher only runs inside LTK Manager (host verification).")
    return True


def patcher_refused_host(tools_dir: Path, line: str) -> None:
    """The DLL refused Lust as its host: never take this build again, and say so."""
    digest = _dll_digest(tools_dir)
    if digest and digest not in _refused_digests(tools_dir):
        try:
            with (tools_dir / REFUSED_FILE).open("a", encoding="utf-8") as handle:
                handle.write(digest + "\n")
        except OSError as e:
            log.warning(f"[LTK] Could not remember the refused patcher: {e}")
    log.error(f"[LTK] The LTK patcher refused Lust as its host ({line.strip()}); the game runs without mods")
    _tell_player("Injection failed: this LTK patcher only runs inside LTK Manager (host verification), "
                 "so the game started without mods.")
