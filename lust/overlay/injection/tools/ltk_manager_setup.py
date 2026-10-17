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

Lust never installs anything silently and never ships or modifies the patcher.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional

import requests

from utils.core.logging import get_logger

from .ltk_manager import LTK_MANAGER_URL, import_from_ltk_manager
from .patcher import check_ltk_patcher

log = get_logger()

RELEASES_API = "https://api.github.com/repos/LeagueToolkit/ltk-manager/releases/latest"
DOWNLOAD_PREFIX = "https://github.com/LeagueToolkit/ltk-manager/releases/download/"
SETUP_ASSET_RE = re.compile(r"^LTK\.Manager_[0-9][0-9A-Za-z.\-]*_x64-setup\.exe$")
# League Toolkit's code signing identity (Azure Trusted Signing profile "Natoken")
SIGNER_SUBJECT = "O=Natoken LLC"
MAX_SETUP_BYTES = 200 * 1024 * 1024


class SetupError(Exception):
    """A step of getting LTK Manager failed; the message is shown to the user."""


# ---------------------------------------------------------------------------
# Download and verify
# ---------------------------------------------------------------------------

def latest_release(session: requests.Session) -> tuple:
    """(tag, setup download URL, size) of LTK Manager's latest release."""
    r = session.get(RELEASES_API, timeout=15, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    release = r.json()
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

def patcher_needs_update(tools_dir: Path, game_dir: Optional[Path]) -> bool:
    status = check_ltk_patcher(tools_dir)
    return bool(status.missing) or status.eol is None or status.expired_for(game_dir)


def ensure_ltk_patcher(tools_dir: Path, game_dir: Optional[Path],
                       ask: Optional[Callable[[str], bool]] = None,
                       fetch: Optional[Callable[[Path], Path]] = None,
                       run_installer: Optional[Callable[[Path], None]] = None,
                       report_error: Optional[Callable[[str], None]] = None) -> None:
    """Get a usable patcher into tools_dir, offering to set up LTK Manager.

    Anything left unresolved falls through to Lust's missing-patcher dialog.
    """
    ask = ask or ask_to_install
    fetch = fetch or (lambda work: with_progress(lambda: download_verified_installer(work)))
    run_installer = run_installer or open_installer
    report_error = report_error or show_error

    import_from_ltk_manager(tools_dir)
    if not patcher_needs_update(tools_dir, game_dir):
        return

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


def startup_check(tools_dir: Path) -> None:
    """Entry point from Lust's startup patcher check."""
    from config import get_config_option

    league_path = get_config_option("General", "leaguePath")
    ensure_ltk_patcher(tools_dir, Path(league_path) if league_path else None)


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
