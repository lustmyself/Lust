#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get Lust an LTK patcher that runs with it.

Lust needs ltk_patcher_host.exe and ltk_patcher_dll.dll. LTK Manager's own builds since
1.30 refuse any host but LTK Manager, so Lust neither installs nor updates LTK Manager.
At startup Lust takes an ltk_patcher.zip the player put in the Downloads folder, without
asking: only when both files are signed by League Toolkit (Natoken LLC) and the DLL runs
outside LTK Manager. It shows no dialog and opens no page; without a usable patcher Lust
keeps running and the hub's Settings tile says why skins don't load. Lust never ships the
patcher itself.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

from utils.core.logging import get_logger

from .ltk_manager import PATCHER_URL, host_locked, import_from_ltk_manager, user_patcher_dir, warn_if_host_locked  # noqa: F401
from .patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, check_ltk_patcher
from .patcher_manifest import known_build, manifest, sha256_of

log = get_logger()

# League Toolkit's code signing identity (Azure Trusted Signing profile "Natoken")
SIGNER_SUBJECT = "O=Natoken LLC"
MAX_PATCHER_BYTES = 32 * 1024 * 1024  # each patcher file is ~1 MB; a larger zip member is not one
# Warn this long before the patcher's end of life (League's next update then stops it)
EOL_WARN_S = 5 * 24 * 60 * 60

_tools_dir: Optional[Path] = None  # the tools folder startup_check looked at, for the hub


def signature_of(path: Path) -> tuple:
    """(status, signer subject) from Windows' Authenticode check."""
    import os
    script = ("$s = Get-AuthenticodeSignature -LiteralPath $env:LUST_VERIFY_PATH; "
              "Write-Output ('{0}|{1}' -f $s.Status, $s.SignerCertificate.Subject)")
    env = dict(os.environ, LUST_VERIFY_PATH=str(path))
    out = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, env=env, timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ).stdout.strip()
    status, _, subject = out.partition("|")
    return status, subject


def _signed_by_ltk(result: tuple) -> bool:
    status, subject = result
    return status == "Valid" and SIGNER_SUBJECT in subject


# ---------------------------------------------------------------------------
# The patcher the player downloaded
# ---------------------------------------------------------------------------

def _downloads_dir() -> Path:
    """The Downloads folder where Windows keeps it (players move it to another drive)."""
    if sys.platform == "win32":
        try:
            import ctypes
            import uuid
            folder_id = (ctypes.c_byte * 16).from_buffer_copy(
                uuid.UUID("374DE290-123F-4565-9164-39C4925E467B").bytes_le)  # FOLDERID_Downloads
            path = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path)) == 0:
                try:
                    return Path(path.value)
                finally:
                    ctypes.windll.ole32.CoTaskMemFree(path)
        except (OSError, AttributeError, ValueError):
            pass
    return Path.home() / "Downloads"


def _plain_name(name: str) -> str:
    """A browser's second copy ("ltk_patcher_dll (1).dll") under its real name."""
    return re.sub(r"\s*\(\d+\)(?=\.[^.]+$)", "", name).lower()


def _read_patcher(source: Path) -> Optional[dict]:
    """Both patcher files from a zip or a folder, by name, or None when it has not both."""
    names = (LTK_PATCHER_DLL, LTK_PATCHER_HOST)
    if source.is_file():
        with zipfile.ZipFile(source) as zipped:
            found = {_plain_name(Path(info.filename).name): info for info in zipped.infolist() if not info.is_dir()}
            if all(name in found and found[name].file_size <= MAX_PATCHER_BYTES for name in names):
                return {name: zipped.read(found[name]) for name in names}
        return None
    found = {_plain_name(path.name): path for path in source.iterdir() if path.is_file()}
    if all(name in found and found[name].stat().st_size <= MAX_PATCHER_BYTES for name in names):
        return {name: found[name].read_bytes() for name in names}
    return None


def take_downloaded_patcher(tools_dir: Path, downloads: Optional[Path] = None,
                            signature: Callable[[Path], tuple] = signature_of) -> bool:
    """The LTK patcher the player downloaded goes to Lust's ltk-patcher folder, where the
    import takes it: from ltk_patcher*.zip, an extracted ltk_patcher* folder or loose files
    in Downloads, only when both files are signed by League Toolkit and the DLL runs outside
    LTK Manager. True when it was taken."""
    downloads = downloads or _downloads_dir()
    try:
        sources = sorted((p for p in downloads.iterdir() if p.name.lower().startswith("ltk_patcher")
                          and (p.is_dir() or p.suffix.lower() == ".zip")),
                         key=lambda p: p.stat().st_mtime, reverse=True) + [downloads]
    except OSError:
        return False
    names = (LTK_PATCHER_DLL, LTK_PATCHER_HOST)
    for source in sources:
        work = Path(tempfile.mkdtemp(prefix="lust-ltk-zip-"))
        try:
            files = _read_patcher(source)
            if files is None:
                continue
            for name, data in files.items():
                (work / name).write_bytes(data)
            if host_locked(work, tools_dir):
                log.info(f"[LTK] {source.name} only runs inside LTK Manager; not taken")
                continue
            # A build lust/patcher.json lists by hash needs no signature (redistributed copies drop it)
            if known_build(work / LTK_PATCHER_DLL, work / LTK_PATCHER_HOST) is None:
                unsigned = [name for name in names if not _signed_by_ltk(signature(work / name))]
                if unsigned:
                    log.warning(f"[LTK] {source.name}: {', '.join(unsigned)} not signed by League Toolkit "
                                "and not listed in the patcher manifest; not taken")
                    continue
            target = user_patcher_dir()
            if all((target / name).is_file() and (target / name).read_bytes() == (work / name).read_bytes()
                   for name in names):
                return False  # taken before
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copyfile(work / name, target / name)
            log.info(f"[LTK] Took the LTK patcher from {source} (dll sha256 {sha256_of(target / LTK_PATCHER_DLL)}, "
                     f"host sha256 {sha256_of(target / LTK_PATCHER_HOST)})")
            return True
        except (OSError, zipfile.BadZipFile) as e:
            log.info(f"[LTK] Could not read {source.name}: {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return False


# ---------------------------------------------------------------------------
# Startup flow
# ---------------------------------------------------------------------------

def patcher_problem(tools_dir: Path, game_dir: Optional[Path]) -> Optional[str]:
    """Why the patcher in tools_dir can't put skins in game ("missing", "locked",
    "expired"), or None when it can."""
    status = check_ltk_patcher(tools_dir)
    if status.missing or status.eol is None:
        return "missing"
    if host_locked(tools_dir, tools_dir):
        return "locked"
    if status.expired_for(game_dir):
        return "expired"
    return None


def _take(tools_dir: Path) -> None:
    take_downloaded_patcher(tools_dir)
    import_from_ltk_manager(tools_dir)


def expiring_soon(tools_dir: Path, game_dir: Optional[Path], now: Optional[float] = None) -> Optional[int]:
    """The patcher's end-of-life date when it is close or past but League has not updated
    yet (the game's next update then stops it), else None."""
    status = check_ltk_patcher(tools_dir)
    if status.missing or status.eol is None or status.expired_for(game_dir):
        return None
    now = time.time() if now is None else now
    return status.eol if status.eol - now <= EOL_WARN_S else None


def _date(timestamp: int) -> str:
    return time.strftime("%d.%m.%Y", time.localtime(timestamp))


def expiring_text(eol: int, now: Optional[float] = None) -> str:
    """The warning in Turkish. The DLL only refuses League builds made after its end of life,
    so once the date has passed it still works until League's next update."""
    now = time.time() if now is None else now
    if eol <= now:
        return (f"LTK patcher'ın süresi {_date(eol)} tarihinde doldu ama şimdiki League sürümüyle hâlâ çalışıyor; "
                "League'in bir sonraki güncellemesinden sonra skinler yüklenmez.")
    return (f"LTK patcher'ın süresi {_date(eol)} tarihinde doluyor: League'in bir sonraki güncellemesinden "
            "sonra skinler yüklenmez.")


def warn_if_expiring(tools_dir: Path, game_dir: Optional[Path]) -> bool:
    """Tell the player ahead of time that the patcher is about to stop working."""
    eol = expiring_soon(tools_dir, game_dir)
    if eol is None:
        return False
    log.warning(f"[LTK] The patcher reaches its end of life on {_date(eol)}")
    try:
        from launcher import lust_hub
        lust_hub.toast(expiring_text(eol))
    except Exception:  # noqa: BLE001
        pass
    try:
        from utils.core.issue_reporter import report_issue
        report_issue("LTK_PATCHER_EXPIRING", "warning",
                     f"The LTK patcher stops working with game builds after {_date(eol)}.")
    except Exception:  # noqa: BLE001
        pass
    return True


def _game_dir() -> Optional[Path]:
    from config import get_config_option
    league_path = get_config_option("General", "leaguePath")
    return Path(league_path) if league_path else None


def startup_check(tools_dir: Path) -> None:
    """Entry point from Lust's startup patcher check: no dialog, Lust starts either way."""
    global _tools_dir
    _tools_dir = tools_dir
    manifest(refresh=True)  # a new build in lust/patcher.json reaches players without a release
    game_dir = _game_dir()
    _take(tools_dir)
    problem = patcher_problem(tools_dir, game_dir)
    if problem:
        log.warning(f"[LTK] The LTK patcher is {problem}: Lust keeps running, skins won't load")
    if not warn_if_host_locked(tools_dir):
        warn_if_expiring(tools_dir, game_dir)


def hub_status() -> dict:
    """What the hub's Settings tile shows: state ok, missing, locked, expired or expiring."""
    if _tools_dir is None:
        return {"state": "ok"}
    game_dir = _game_dir()
    problem = patcher_problem(_tools_dir, game_dir)
    eol = check_ltk_patcher(_tools_dir).eol
    state = problem or ("expiring" if expiring_soon(_tools_dir, game_dir) else "ok")
    return {"state": state, "eol": _date(eol) if eol else "", "past": bool(eol and eol <= time.time())}
