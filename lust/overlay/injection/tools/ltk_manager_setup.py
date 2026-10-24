#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help the user get LTK Manager, so Lust has an LTK patcher.

Lust needs ltk_patcher_host.exe and ltk_patcher_dll.dll, which come with LTK
Manager. When they are missing, unreadable or past their end of life, Lust
asks the user; on yes it downloads LTK Manager's latest official installer
from GitHub, checks its Authenticode signature (League Toolkit signs as
Natoken LLC) and opens it for the user to click through. Once it closes,
Lust copies the patcher from the new install.

Once LTK Manager is installed it is the player's own, kept current: when a newer
release is out (checked once a day) or the patcher no longer supports the game, Lust
downloads the signed installer and runs it silently (/S) to update it. A first install
still opens the installer for the player. Lust never ships or modifies the patcher.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from utils.core.logging import get_logger

from .ltk_manager import LTK_MANAGER_URL, host_locked, import_from_ltk_manager, user_patcher_dir, warn_if_host_locked
from .patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, check_ltk_patcher

log = get_logger()

RELEASES_API = "https://api.github.com/repos/LeagueToolkit/ltk-manager/releases/latest"
DOWNLOAD_PREFIX = "https://github.com/LeagueToolkit/ltk-manager/releases/download/"
SETUP_ASSET_RE = re.compile(r"^LTK\.Manager_[0-9][0-9A-Za-z.\-]*_x64-setup\.exe$")
# League Toolkit's code signing identity (Azure Trusted Signing profile "Natoken")
SIGNER_SUBJECT = "O=Natoken LLC"
MAX_PATCHER_BYTES = 32 * 1024 * 1024  # each patcher file is ~1 MB; a larger zip member is not one
MAX_SETUP_BYTES = 200 * 1024 * 1024


class SetupError(Exception):
    """A step of getting LTK Manager failed; the message is shown to the user."""


# ---------------------------------------------------------------------------
# Download and verify
# ---------------------------------------------------------------------------

def _latest_from_web(session: requests.Session) -> tuple:
    """(tag, URL, size) from github.com itself, which GitHub's API limit does not cover."""
    r = session.get("https://github.com/LeagueToolkit/ltk-manager/releases/latest",
                    timeout=15, allow_redirects=False)
    tag = r.headers.get("Location", "").rstrip("/").rsplit("/tag/", 1)[-1]
    if r.status_code not in (301, 302) or not re.fullmatch(r"v?[0-9][0-9A-Za-z.\-]*", tag):
        raise SetupError("Could not find LTK Manager's latest release")
    url = f"{DOWNLOAD_PREFIX}{tag}/LTK.Manager_{tag.lstrip('vV')}_x64-setup.exe"
    head = session.head(url, timeout=15, allow_redirects=True)
    head.raise_for_status()
    return tag, url, int(head.headers.get("Content-Length") or 0)


def latest_release(session: requests.Session) -> tuple:
    """(tag, setup download URL, size) of LTK Manager's latest release."""
    try:
        r = session.get(RELEASES_API, timeout=15, headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        release = r.json()
    except requests.RequestException as e:
        log.info(f"[LTK] GitHub API unavailable ({e}); asking github.com")
        return _latest_from_web(session)
    for asset in release.get("assets") or []:
        name = asset.get("name") or ""
        url = asset.get("browser_download_url") or ""
        if SETUP_ASSET_RE.match(name) and url.startswith(DOWNLOAD_PREFIX):
            return release.get("tag_name") or "", url, int(asset.get("size") or 0)
    raise SetupError("LTK Manager's latest release has no Windows installer")


def download(session: requests.Session, url: str, size: int, dest: Path) -> None:
    if size <= 0 or size > MAX_SETUP_BYTES:
        raise SetupError(f"Unexpected LTK Manager installer size: {size} bytes")
    written = 0
    with session.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                written += len(chunk)
                if written > MAX_SETUP_BYTES:
                    raise SetupError("LTK Manager installer is larger than expected")
                f.write(chunk)
    if written != size:
        raise SetupError(f"LTK Manager download incomplete ({written} of {size} bytes)")


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


def verify_signature(path: Path) -> None:
    status, subject = signature_of(path)
    if status != "Valid" or SIGNER_SUBJECT not in subject:
        raise SetupError("The downloaded LTK Manager installer is not signed by League Toolkit "
                         f"(signature: {status or 'none'}, signer: {subject or 'none'}), so Lust did not open it")


def download_verified_installer(work: Path) -> Path:
    """Download LTK Manager's latest installer into work and verify it. Raises SetupError."""
    session = requests.Session()
    try:
        tag, url, size = latest_release(session)
        setup = work / url.rsplit("/", 1)[-1]
        log.info(f"[LTK] Downloading LTK Manager {tag}")
        download(session, url, size, setup)
    except requests.RequestException as e:
        raise SetupError(f"Could not download LTK Manager: {e}")
    finally:
        session.close()
    verify_signature(setup)
    log.info(f"[LTK] LTK Manager {tag} installer verified")
    return setup


def open_installer(setup: Path) -> None:
    """Open the installer for the user and wait until they close it."""
    try:
        subprocess.run([str(setup)], check=False)
    except OSError as e:
        raise SetupError(f"Could not open the LTK Manager installer: {e}")


# ---------------------------------------------------------------------------
# Startup flow
# ---------------------------------------------------------------------------

UPDATE_CHECK_S = 24 * 60 * 60


def installed_version() -> Optional[str]:
    """LTK Manager's version from its Windows uninstall entry, or None when it isn't installed."""
    if sys.platform != "win32":
        return None
    import winreg
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\LTK Manager") as key:
                return str(winreg.QueryValueEx(key, "DisplayVersion")[0]).strip() or None
        except OSError:
            continue
    return None


def _version(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text or ""))


def run_installer_silently(setup: Path) -> None:
    """Update an installed LTK Manager without showing its installer."""
    try:
        subprocess.run([str(setup), "/S"], check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SetupError(f"Could not update LTK Manager: {e}")


def _due_for_check() -> bool:
    from utils.core.paths import get_user_data_dir
    stamp = get_user_data_dir() / "ltk-update-check"
    try:
        if time.time() - stamp.stat().st_mtime < UPDATE_CHECK_S:
            return False
    except OSError:
        pass
    try:
        stamp.write_text(str(int(time.time())), encoding="utf-8")
    except OSError:
        pass
    return True


def update_installed(tools_dir: Path, current: str, fetch: Callable[[Path], Path],
                     run_silent: Callable[[Path], None]) -> bool:
    """Update the player's LTK Manager to the latest release and take its patcher. True when done."""
    work = Path(tempfile.mkdtemp(prefix="lust-ltk-"))
    try:
        setup = fetch(work)
        log.info(f"[LTK] Updating LTK Manager {current} silently")
        run_silent(setup)
    except SetupError as e:
        log.warning(f"[LTK] {e}")
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if import_from_ltk_manager(tools_dir):
        log.info(f"[LTK] Patcher taken from the updated LTK Manager ({installed_version()})")
        return True
    return False


def _update_if_newer(tools_dir: Path) -> None:
    """In the background: a newer LTK Manager release replaces the installed one."""
    try:
        current = installed_version()
        if not current or not _due_for_check():
            return
        session = requests.Session()
        try:
            tag, _, _ = latest_release(session)
        finally:
            session.close()
        if _version(tag) <= _version(current):
            return
        log.info(f"[LTK] LTK Manager {tag} is out (installed: {current})")
        update_installed(tools_dir, current, download_verified_installer, run_installer_silently)
    except Exception as e:  # noqa: BLE001 - never in the way of starting Lust
        log.info(f"[LTK] Background LTK Manager check failed: {e}")


def patcher_needs_update(tools_dir: Path, game_dir: Optional[Path]) -> bool:
    status = check_ltk_patcher(tools_dir)
    return bool(status.missing) or status.eol is None or status.expired_for(game_dir)


def ensure_ltk_patcher(tools_dir: Path, game_dir: Optional[Path],
                       ask: Optional[Callable[[str], bool]] = None,
                       fetch: Optional[Callable[[Path], Path]] = None,
                       run_installer: Optional[Callable[[Path], None]] = None,
                       report_error: Optional[Callable[[str], None]] = None,
                       installed: Optional[Callable[[], Optional[str]]] = None,
                       run_silent: Optional[Callable[[Path], None]] = None,
                       background: Optional[Callable[[Path], None]] = None) -> None:
    """Get a usable patcher into tools_dir: update an installed LTK Manager silently,
    or offer to set it up. Anything left unresolved falls through to Lust's
    missing-patcher dialog.
    """
    ask = ask or ask_to_install
    fetch = fetch or (lambda work: with_progress(lambda: download_verified_installer(work)))
    run_installer = run_installer or open_installer
    report_error = report_error or show_error
    installed = installed or installed_version
    run_silent = run_silent or run_installer_silently
    if background is None:
        def background(tools):
            threading.Thread(target=_update_if_newer, args=(tools,), daemon=True, name="LtkUpdate").start()

    import_from_ltk_manager(tools_dir)
    current = installed()
    if not patcher_needs_update(tools_dir, game_dir):
        if current:
            background(tools_dir)  # a newer release, once a day, without holding up Lust
        return

    if current:
        # The player's LTK Manager no longer supports the game: update it now, silently
        if update_installed(tools_dir, current, fetch, run_silent) and not patcher_needs_update(tools_dir, game_dir):
            return
        log.info("[LTK] Silent LTK Manager update did not give a usable patcher; asking")

    status = check_ltk_patcher(tools_dir)
    if not ask("update" if not status.missing and status.eol is not None else "install"):
        log.info("[LTK] User declined getting LTK Manager")
        return

    work = Path(tempfile.mkdtemp(prefix="lust-ltk-"))
    try:
        setup = fetch(work)
        run_installer(setup)
    except SetupError as e:
        log.warning(f"[LTK] {e}")
        report_error(str(e))
        return
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if import_from_ltk_manager(tools_dir):
        log.info("[LTK] Patcher taken from the new LTK Manager install")
    elif patcher_needs_update(tools_dir, game_dir):
        log.info("[LTK] LTK Manager setup closed without a usable patcher")


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
    """The LTK patcher the player downloaded (Rose's Discord shares ltk_patcher.zip) goes to
    Lust's ltk-patcher folder, where the import takes it: from ltk_patcher*.zip, an extracted
    ltk_patcher* folder or loose files in Downloads, only when both files are signed by League
    Toolkit and the DLL runs outside LTK Manager. True when it was taken."""
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
            unsigned = [name for name in names if not _signed_by_ltk(signature(work / name))]
            if unsigned:
                log.warning(f"[LTK] {source.name}: {', '.join(unsigned)} not signed by League Toolkit; not taken")
                continue
            target = user_patcher_dir()
            if all((target / name).is_file() and (target / name).read_bytes() == (work / name).read_bytes()
                   for name in names):
                return False  # taken at an earlier start
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copyfile(work / name, target / name)
            log.info(f"[LTK] Took the LTK patcher from {source}")
            return True
        except (OSError, zipfile.BadZipFile) as e:
            log.info(f"[LTK] Could not read {source.name}: {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return False


def _signed_by_ltk(result: tuple) -> bool:
    status, subject = result
    return status == "Valid" and SIGNER_SUBJECT in subject


def startup_check(tools_dir: Path) -> None:
    """Entry point from Lust's startup patcher check."""
    from config import get_config_option

    league_path = get_config_option("General", "leaguePath")
    take_downloaded_patcher(tools_dir)
    ensure_ltk_patcher(tools_dir, Path(league_path) if league_path else None)
    warn_if_host_locked(tools_dir)


# ---------------------------------------------------------------------------
# Native dialogs (Windows Task Dialog; MessageBox when unavailable)
# ---------------------------------------------------------------------------

TD_INFORMATION_ICON = 0xFFFD
TDF_ENABLE_HYPERLINKS = 0x0001
TDF_SHOW_MARQUEE_PROGRESS_BAR = 0x0400
TDF_CALLBACK_TIMER = 0x0800
TDCBF_OK_BUTTON, TDCBF_CANCEL_BUTTON = 0x0001, 0x0008
TDN_CREATED, TDN_HYPERLINK_CLICKED, TDN_TIMER = 0, 3, 4
TDM_CLICK_BUTTON, TDM_SET_PROGRESS_BAR_MARQUEE, TDM_ENABLE_BUTTON = 0x0466, 0x046B, 0x046F
IDCANCEL = 2


def _run_task_dialog(title, instruction, content, buttons=(), flags=0, common=0,
                     on_event=None, footer=None) -> Optional[int]:
    """Show a Task Dialog; returns the pressed button id, or None if unavailable."""
    if sys.platform != "win32":
        return None
    import ctypes
    import webbrowser
    from ctypes import wintypes

    class Button(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("nButtonID", wintypes.INT), ("pszButtonText", wintypes.LPCWSTR)]

    class Config(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("cbSize", wintypes.UINT), ("hwndParent", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE), ("dwFlags", wintypes.DWORD),
            ("dwCommonButtons", wintypes.DWORD), ("pszWindowTitle", wintypes.LPCWSTR),
            ("hMainIcon", ctypes.c_void_p), ("pszMainInstruction", wintypes.LPCWSTR),
            ("pszContent", wintypes.LPCWSTR), ("cButtons", wintypes.UINT),
            ("pButtons", ctypes.POINTER(Button)), ("nDefaultButton", wintypes.INT),
            ("cRadioButtons", wintypes.UINT), ("pRadioButtons", ctypes.c_void_p),
            ("nDefaultRadioButton", wintypes.INT), ("pszVerificationText", wintypes.LPCWSTR),
            ("pszExpandedInformation", wintypes.LPCWSTR), ("pszExpandedControlText", wintypes.LPCWSTR),
            ("pszCollapsedControlText", wintypes.LPCWSTR), ("hFooterIcon", ctypes.c_void_p),
            ("pszFooter", wintypes.LPCWSTR), ("pfCallback", ctypes.c_void_p),
            ("lpCallbackData", wintypes.LPARAM), ("cxWidth", wintypes.UINT),
        ]

    callback_type = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM, wintypes.LPARAM)

    def callback(hwnd, notification, wparam, lparam, ref):
        if notification == TDN_HYPERLINK_CLICKED:
            try:
                webbrowser.open(ctypes.wstring_at(lparam))
            except Exception:
                pass
        if on_event:
            try:
                on_event(hwnd, notification)
            except Exception:
                pass
        return 0

    cb = callback_type(callback)
    button_array = (Button * max(1, len(buttons)))(*[Button(i, t) for i, t in buttons])
    config = Config(
        cbSize=ctypes.sizeof(Config), dwFlags=TDF_ENABLE_HYPERLINKS | flags,
        dwCommonButtons=common, pszWindowTitle=title, hMainIcon=TD_INFORMATION_ICON,
        pszMainInstruction=instruction, pszContent=content,
        cButtons=len(buttons), pButtons=button_array if buttons else None,
        nDefaultButton=buttons[0][0] if buttons else 0, pszFooter=footer,
        pfCallback=ctypes.cast(cb, ctypes.c_void_p), cxWidth=240,
    )
    pressed = wintypes.INT()
    try:
        fn = ctypes.windll.comctl32.TaskDialogIndirect
        fn.restype = ctypes.c_long
        fn.argtypes = [ctypes.POINTER(Config), ctypes.POINTER(wintypes.INT),
                       ctypes.POINTER(wintypes.INT), ctypes.POINTER(wintypes.BOOL)]
        if fn(ctypes.byref(config), ctypes.byref(pressed), None, None) != 0:
            return None
    except (AttributeError, OSError, ctypes.ArgumentError):
        return None
    return pressed.value


def _message_box(text, title, flags) -> int:
    if sys.platform != "win32":
        return 0
    import ctypes
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags | 0x00040000)  # MB_TOPMOST


ASK_TEXT = {
    "install": ("Lust needs the LTK patcher to put skins in game. It comes with LTK Manager, "
                "a free mod manager by League Toolkit.\n\n"
                "Lust can download the LTK Manager installer from its official GitHub page, "
                "check that it is signed by League Toolkit, and open it for you."),
    "update": ("League has updated past the date your LTK patcher supports, so skins will not "
               "load until it is updated.\n\n"
               "Lust can download the latest LTK Manager installer from its official GitHub page, "
               "check that it is signed by League Toolkit, and open it for you."),
}


def ask_to_install(kind: str) -> bool:
    get_id, later_id = 1001, 1002
    instruction = "Get LTK Manager?" if kind == "install" else "Update the LTK patcher?"
    footer = f'LTK Manager: <a href="{LTK_MANAGER_URL}">github.com/LeagueToolkit/ltk-manager</a>'
    pressed = _run_task_dialog(
        "Lust", instruction, ASK_TEXT[kind],
        buttons=((get_id, "Download and open the installer"), (later_id, "Not now")), footer=footer,
    )
    if pressed is None:
        return _message_box(f"{instruction}\n\n{ASK_TEXT[kind]}\n\n{LTK_MANAGER_URL}",
                            "Lust", 0x00000004 | 0x00000020) == 6  # MB_YESNO | ICONQUESTION, IDYES
    return pressed == get_id


def with_progress(work: Callable):
    """Run work() in a thread behind a marquee dialog; return its result or raise its error."""
    outcome = {}

    def target():
        try:
            outcome["result"] = work()
        except Exception as e:
            outcome["error"] = e

    worker = threading.Thread(target=target, daemon=True)
    worker.start()

    def on_event(hwnd, notification):
        import ctypes
        send = ctypes.windll.user32.SendMessageW
        if notification == TDN_CREATED:
            send(hwnd, TDM_SET_PROGRESS_BAR_MARQUEE, 1, 30)
            send(hwnd, TDM_ENABLE_BUTTON, IDCANCEL, 0)
        elif notification == TDN_TIMER and not worker.is_alive():
            send(hwnd, TDM_ENABLE_BUTTON, IDCANCEL, 1)
            send(hwnd, TDM_CLICK_BUTTON, IDCANCEL, 0)

    _run_task_dialog(
        "Lust", "Downloading LTK Manager...",
        "Getting the installer from LTK Manager's official GitHub page and checking its signature.",
        flags=TDF_SHOW_MARQUEE_PROGRESS_BAR | TDF_CALLBACK_TIMER, common=TDCBF_CANCEL_BUTTON,
        on_event=on_event,
    )
    worker.join()  # also when no dialog could be shown
    error = outcome.get("error")
    if error is not None:
        if isinstance(error, SetupError):
            raise error
        raise SetupError(f"Could not get LTK Manager: {error}")
    return outcome.get("result")


def show_error(message: str) -> None:
    text = (f"{message}\n\nYou can install LTK Manager yourself from {LTK_MANAGER_URL}, "
            "then restart Lust.")
    if _run_task_dialog("Lust", "Could not get LTK Manager", text, common=TDCBF_OK_BUTTON) is None:
        _message_box(text, "Lust", 0x00000030)  # MB_ICONWARNING
