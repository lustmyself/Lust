#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Take the LTK patcher from an LTK Manager install.

LTK Manager (https://github.com/LeagueToolkit/ltk-manager) ships
ltk_patcher_host.exe and ltk_patcher_dll.dll in its install folder. When one
is installed, Lust copies both into its tools folder itself, and again
whenever LTK Manager has a newer patcher, so users never move files by hand.
Lust ships no copy of its own.
"""

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


def _default_install_dirs() -> List[Path]:
    dirs = []
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


def import_from_ltk_manager(tools_dir: Path, extra_dirs: Iterable[Path] = ()) -> Optional[Path]:
    """Copy LTK Manager's patcher into tools_dir when it is newer than (or
    replaces a missing or unreadable) one there. Returns the folder copied
    from, or None when nothing was copied."""
    current = check_ltk_patcher(tools_dir)
    best, best_eol = None, None
    for folder in find_ltk_manager_patchers(extra_dirs):
        eol = check_ltk_patcher(folder).eol
        if eol is None:
            log.warning(f"[LTK] Ignoring unrecognized patcher DLL in {folder}")
            continue
        if best_eol is None or eol > best_eol:
            best, best_eol = folder, eol

    if best is None:
        return None
    if not current.missing and current.eol is not None and current.eol >= best_eol:
        return None  # what Lust has is as new as LTK Manager's

    # Stage both first so a failed copy never leaves a host and DLL from different releases
    staged = {name: tools_dir / f".{name}.tmp" for name in (LTK_PATCHER_DLL, LTK_PATCHER_HOST)}
    try:
        tools_dir.mkdir(parents=True, exist_ok=True)
        for name, tmp in staged.items():
            shutil.copyfile(best / name, tmp)
        for name, tmp in staged.items():
            os.replace(tmp, tools_dir / name)
    except OSError as e:
        log.warning(f"[LTK] Could not copy the patcher from {best}: {e}")
        return None
    finally:
        for tmp in staged.values():
            try:
                tmp.unlink()
            except OSError:
                pass
    log.info(f"[LTK] Copied the LTK patcher from {best}")
    return best
