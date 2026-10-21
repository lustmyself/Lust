"""Clean up what older Lust versions left behind, once Lust runs.

- Update packages, their `.ready` marks and the staging folder in Lust's updates folder,
  except a newer package still waiting to be installed.
- Uninstall entries left by older installers (Lust once had Rose's AppId): an entry named
  Lust whose folder is this install is only a duplicate, so the entry goes; a Lust copy
  in another folder goes with its entry when that folder holds Lust.exe and no Rose.exe.

Old uninstallers are never run: they delete %LOCALAPPDATA%\\Lust (custom skins, mods,
settings) and turn Pengu Loader off, which would break the Lust that is running.
"""

from __future__ import annotations

import re
import shutil
import sys
import winreg
from pathlib import Path

from utils.core.logging import get_logger

log = get_logger()

OLD_APP_IDS = ("{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1",)
UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"


def _version(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text or ""))


def clean_updates(updates_dir: Path, current: str) -> int:
    """Remove update packages at or below the running version, and the staging folder."""
    removed = 0
    if not updates_dir.is_dir():
        return 0
    staging = updates_dir / "staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
        removed += 1
    for path in updates_dir.iterdir():
        match = re.match(r"update_package_([0-9.]+)\.zip(\.ready|\.part)?$", path.name)
        if match and _version(match.group(1)) <= _version(current):
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _entries():
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        for app_id in OLD_APP_IDS:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{UNINSTALL}\\{app_id}", 0,
                                    winreg.KEY_READ | view) as key:
                    values = {}
                    for name in ("DisplayName", "InstallLocation"):
                        try:
                            values[name] = str(winreg.QueryValueEx(key, name)[0])
                        except OSError:
                            values[name] = ""
                yield view, app_id, values
            except OSError:
                continue


def _delete_entry(view: int, app_id: str) -> None:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, UNINSTALL, 0, winreg.KEY_ALL_ACCESS | view) as key:
        winreg.DeleteKey(key, app_id)


def clean_old_installs(install_dir: Path) -> int:
    """Remove duplicate or stray installs left by Lust's older installers. Returns how many."""
    removed = 0
    here = install_dir.resolve()
    for view, app_id, values in _entries():
        if values["DisplayName"].strip() != "Lust":
            continue  # Rose's own entry, or something else: not ours
        folder = Path(values["InstallLocation"].strip().strip('"')) if values["InstallLocation"].strip() else None
        try:
            if folder and folder.exists() and folder.resolve() != here:
                if (folder / "Lust.exe").is_file() and not (folder / "Rose.exe").exists():
                    shutil.rmtree(folder, ignore_errors=True)
                    log.info(f"[Cleanup] Removed an old Lust copy in {folder}")
                else:
                    continue  # not plainly a Lust copy: leave the folder and its entry alone
            _delete_entry(view, app_id)
            removed += 1
            log.info(f"[Cleanup] Removed the old uninstall entry {app_id}")
        except OSError as exc:
            log.warning(f"[Cleanup] Could not remove the old install {app_id}: {exc}")
    return removed


def run() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        from config import APP_VERSION, get_config_file_path
        removed = clean_updates(get_config_file_path().parent / "updates", APP_VERSION)
        removed += clean_old_installs(Path(sys.executable).resolve().parent)
        if removed:
            log.info(f"[Cleanup] Removed {removed} leftover(s) of older Lust versions")
    except Exception as exc:  # noqa: BLE001 - never in the way of Lust
        log.warning(f"[Cleanup] Failed: {exc}")
