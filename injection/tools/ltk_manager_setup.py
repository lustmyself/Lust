#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get Lust an LTK patcher that runs with it.

Lust needs ltk_patcher_host.exe and ltk_patcher_dll.dll. LTK Manager's own builds since
1.30 refuse any host but LTK Manager, so Lust neither installs nor updates LTK Manager.
When the patcher is missing, past its end of life or locked, Lust opens the download page
of the ltk_patcher.zip that Rose's Discord shares (#tutorial) and waits for it in the
Downloads folder, without a restart. It takes the files only when both are signed by League
Toolkit (Natoken LLC) and the DLL runs outside LTK Manager, so a link that changes can't give
players anything else. Lust never ships the patcher itself.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile
from pathlib import Path
from typing import Callable, Optional

from utils.core.logging import get_logger

from .ltk_manager import PATCHER_URL, host_locked, import_from_ltk_manager, user_patcher_dir, warn_if_host_locked  # noqa: F401
from .patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, check_ltk_patcher
from .patcher_manifest import download_url, known_build, manifest, newest_eol, sha256_of

log = get_logger()

# League Toolkit's code signing identity (Azure Trusted Signing profile "Natoken")
SIGNER_SUBJECT = "O=Natoken LLC"
MAX_PATCHER_BYTES = 32 * 1024 * 1024  # each patcher file is ~1 MB; a larger zip member is not one
WAIT_S = 15 * 60
POLL_S = 3
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


def ensure_ltk_patcher(tools_dir: Path, game_dir: Optional[Path],
                       ask: Optional[Callable[[str], bool]] = None,
                       wait: Optional[Callable[[Callable[[], bool]], bool]] = None,
                       open_page: Callable[[str], object] = webbrowser.open) -> bool:
    """Get a usable patcher into tools_dir: one already downloaded, or, with the player's
    yes, the download page and a wait for the zip. True when the patcher is usable."""
    ask = ask or ask_to_download
    wait = wait or wait_for_download
    _take(tools_dir)
    problem = patcher_problem(tools_dir, game_dir)
    if problem is None:
        return True
    log.info(f"[LTK] The patcher is {problem}; asking the player to download ltk_patcher.zip")
    if not ask(problem):
        log.info("[LTK] The player put off downloading the patcher")
        return False

    def ready() -> bool:
        _take(tools_dir)
        return patcher_problem(tools_dir, game_dir) is None

    open_page(download_url())
    if wait(ready):
        log.info("[LTK] Patcher installed from the download")
        try:
            from launcher import lust_hub
            lust_hub.toast("LTK patcher kuruldu: skinler hazır.")
        except Exception:  # noqa: BLE001
            pass
        return True
    log.info("[LTK] No usable patcher arrived in Downloads")
    return False


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


def warn_if_expiring(tools_dir: Path, game_dir: Optional[Path]) -> bool:
    """Tell the player ahead of time that the patcher is about to stop working."""
    eol = expiring_soon(tools_dir, game_dir)
    if eol is None:
        return False
    newer = (newest_eol() or 0) > eol
    turkish = (f"LTK patcher'ın süresi {_date(eol)} tarihinde doluyor: League'in bir sonraki güncellemesinden "
               "sonra skinler yüklenmez. ")
    turkish += ("Yeni ltk_patcher.zip çıktı: hub'daki \"İndirme sayfasını aç\" düğmesine bas." if newer else
                "Rose Discord'unda (#tutorial) yeni ltk_patcher.zip paylaşılınca indir.")
    log.warning(f"[LTK] The patcher reaches its end of life on {_date(eol)}"
                + ("; a newer build is listed" if newer else ""))
    try:
        from launcher import lust_hub
        lust_hub.toast(turkish)
    except Exception:  # noqa: BLE001
        pass
    try:
        from utils.core.issue_reporter import report_issue
        report_issue("LTK_PATCHER_EXPIRING", "warning",
                     f"The LTK patcher stops working with game builds after {_date(eol)}.",
                     hint=f"Download the newer ltk_patcher.zip ({download_url()}) into your Downloads folder.")
    except Exception:  # noqa: BLE001
        pass
    return True


def _game_dir() -> Optional[Path]:
    from config import get_config_option
    league_path = get_config_option("General", "leaguePath")
    return Path(league_path) if league_path else None


def startup_check(tools_dir: Path) -> None:
    """Entry point from Lust's startup patcher check."""
    global _tools_dir
    _tools_dir = tools_dir
    manifest(refresh=True)  # a new link or build in lust/patcher.json reaches players without a release
    game_dir = _game_dir()
    ensure_ltk_patcher(tools_dir, game_dir)
    if not warn_if_host_locked(tools_dir):
        warn_if_expiring(tools_dir, game_dir)


# ---------------------------------------------------------------------------
# The hub's patcher card
# ---------------------------------------------------------------------------

_hub_wait = threading.Event()


def hub_status() -> dict:
    """What the hub's patcher card shows: state ok, missing, locked, expired or expiring."""
    if _tools_dir is None:
        return {"state": "ok"}
    game_dir = _game_dir()
    problem = patcher_problem(_tools_dir, game_dir)
    eol = check_ltk_patcher(_tools_dir).eol
    state = problem or ("expiring" if expiring_soon(_tools_dir, game_dir) else "ok")
    return {"state": state, "eol": _date(eol) if eol else "", "waiting": _hub_wait.is_set(),
            "newer": bool(eol and (newest_eol() or 0) > eol)}


def hub_download(open_page: Callable[[str], object] = webbrowser.open) -> str:
    """The hub's button: open the download page and take the zip once it lands in Downloads."""
    if _tools_dir is None:
        return ""
    tools_dir, game_dir = _tools_dir, _game_dir()
    open_page(download_url())
    if _hub_wait.is_set():
        return "ltk_patcher.zip bekleniyor"
    _hub_wait.set()
    before = sha256_of(tools_dir / LTK_PATCHER_DLL)

    def watch():
        deadline = time.monotonic() + WAIT_S
        try:
            while time.monotonic() < deadline:
                try:
                    _take(tools_dir)
                    changed = sha256_of(tools_dir / LTK_PATCHER_DLL) != before
                    if changed and patcher_problem(tools_dir, game_dir) is None:
                        log.info("[LTK] Patcher installed from the hub's download")
                        try:
                            from launcher import lust_hub
                            lust_hub.toast("LTK patcher kuruldu: skinler hazır.")
                        except Exception:  # noqa: BLE001
                            pass
                        return
                except Exception as e:  # noqa: BLE001 - a half-written download, read again next time
                    log.debug(f"[LTK] Waiting for the patcher: {e}")
                time.sleep(POLL_S)
        finally:
            _hub_wait.clear()

    threading.Thread(target=watch, daemon=True, name="LtkHubWait").start()
    return "İndirme sayfası açıldı: zip İndirilenler'e inince Lust kurar"


# ---------------------------------------------------------------------------
# Native dialogs (Windows Task Dialog; MessageBox when unavailable)
# ---------------------------------------------------------------------------

TD_INFORMATION_ICON = 0xFFFD
TDF_ENABLE_HYPERLINKS = 0x0001
TDF_SHOW_MARQUEE_PROGRESS_BAR = 0x0400
TDF_CALLBACK_TIMER = 0x0800
TDCBF_CANCEL_BUTTON = 0x0008
TDN_CREATED, TDN_HYPERLINK_CLICKED, TDN_TIMER = 0, 3, 4
TDM_CLICK_BUTTON, TDM_SET_PROGRESS_BAR_MARQUEE = 0x0466, 0x046B
IDCANCEL = 2


def _run_task_dialog(title, instruction, content, buttons=(), flags=0, common=0,
                     on_event=None, footer=None) -> Optional[int]:
    """Show a Task Dialog; returns the pressed button id, or None if unavailable."""
    if sys.platform != "win32":
        return None
    import ctypes
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


ASK_TITLE = {
    "missing": "Skinler için LTK patcher gerekli",
    "locked": "Bu LTK patcher Lust'la çalışmıyor",
    "expired": "LTK patcher'ın süresi doldu",
}
ASK_TEXT = (
    "Lust skinleri oyuna LTK patcher ile koyar. LTK Manager'ın yeni sürümleri Lust'la çalışmıyor; "
    "çalışan patcher, Rose Discord'unun #tutorial kanalında paylaşılan ltk_patcher.zip.\n\n"
    "\"İndirme sayfasını aç\"a bas ve açılan sayfadan ltk_patcher.zip'i indir. Lust onu İndirilenler "
    "klasöründe bulur, League Toolkit imzasını kontrol eder ve kendisi kurar. Yeniden başlatmana gerek yok."
)


def ask_to_download(problem: str) -> bool:
    open_id, later_id = 1001, 1002
    instruction = ASK_TITLE.get(problem, ASK_TITLE["missing"])
    url = download_url()
    footer = f'<a href="{url}">ltk_patcher.zip</a> (Rose Discord, #tutorial)'
    pressed = _run_task_dialog(
        "Lust", instruction, ASK_TEXT,
        buttons=((open_id, "İndirme sayfasını aç"), (later_id, "Sonra")), footer=footer,
    )
    if pressed is None:
        return _message_box(f"{instruction}\n\n{ASK_TEXT}\n\n{url}",
                            "Lust", 0x00000004 | 0x00000020) == 6  # MB_YESNO | ICONQUESTION, IDYES
    return pressed == open_id


def wait_for_download(ready: Callable[[], bool], timeout_s: float = WAIT_S, poll_s: float = POLL_S) -> bool:
    """Check ready() every few seconds behind a marquee dialog until it is True, the
    player cancels, or the time is up. True when it became ready."""
    done = threading.Event()
    stop = threading.Event()
    outcome = {"ready": False}

    def poll():
        deadline = time.monotonic() + timeout_s
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                if ready():
                    outcome["ready"] = True
                    break
            except Exception as e:  # noqa: BLE001 - a half-written download, read again next time
                log.debug(f"[LTK] Waiting for the patcher: {e}")
            stop.wait(poll_s)
        done.set()

    worker = threading.Thread(target=poll, daemon=True, name="LtkWait")
    worker.start()

    def on_event(hwnd, notification):
        import ctypes
        send = ctypes.windll.user32.SendMessageW
        if notification == TDN_CREATED:
            send(hwnd, TDM_SET_PROGRESS_BAR_MARQUEE, 1, 30)
        elif notification == TDN_TIMER and done.is_set():
            send(hwnd, TDM_CLICK_BUTTON, IDCANCEL, 0)

    _run_task_dialog(
        "Lust", "ltk_patcher.zip bekleniyor...",
        "İndirme bitince Lust dosyayı İndirilenler klasöründe bulur ve kurar. "
        "Bu pencere kendiliğinden kapanır.",
        flags=TDF_SHOW_MARQUEE_PROGRESS_BAR | TDF_CALLBACK_TIMER, common=TDCBF_CANCEL_BUTTON,
        on_event=on_event,
    )
    stop.set()  # the player closed the window, or none could be shown: don't hold Lust's start
    worker.join()
    return outcome["ready"]
