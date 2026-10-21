"""Lust's desktop hub: a small window for startup progress, updates and quick actions.

The window is Lust's own (Tkinter, drawn in launcher/lust_hub_window.py): no
browser, no local web server. This module holds what it shows and what its buttons do.

Startup progress that the Win32 launcher dialog used to show goes to the hub
(HubDialog has the dialog's methods). After startup the hub keeps running: the tray
icon opens it again, it checks for new Lust releases, and its buttons open League,
change the Lust Offline status, open the mods folder, copy the log, toggle Start
with Windows, restart Lust and close Lust.
"""

from __future__ import annotations

import atexit
import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Callable, Optional

from config import APP_VERSION
from utils.core.logging import get_logger

log = get_logger()

UPDATE_CHECK_INTERVAL_S = 30 * 60
WINDOW_WAIT_S = 15.0

_lock = threading.RLock()
_tray = None  # TrayManager once Lust runs
_cache: dict = {}
_state = {
    "phase": "starting",  # starting -> ready
    "detail": "",
    "status": "",
    "progress": None,  # None: busy without a percentage
    "transfer": "",
    "ready": False,
    "latest": "",
    "checked_at": 0,
    "prompt": None,  # {"version": ...} while the launcher asks about an update
    "toast": None,
}
_prompt_answer: Optional[bool] = None
_prompt_event = threading.Event()


# ---- language ----

LANG = "tr"

# Launcher and downloader messages, by prefix (the rest of the message is kept)
TR_MESSAGES = [
    ("Preparing Lust", "Lust hazırlanıyor"),
    ("Checking for updates", "Güncellemeler kontrol ediliyor"),
    ("Contacting update server", "Güncelleme sunucusuna bağlanılıyor"),
    ("Update available", "Güncelleme var"),
    ("Update skipped", "Güncelleme atlandı"),
    ("Updating Lust", "Lust güncelleniyor"),
    ("Downloading update", "Güncelleme indiriliyor"),
    ("Extracting update", "Güncelleme açılıyor"),
    ("Installing update", "Güncelleme kuruluyor"),
    ("Update installed. Restarting", "Güncelleme kuruldu, yeniden başlatılıyor"),
    ("Update installed", "Güncelleme kuruldu"),
    ("Update failed", "Güncelleme başarısız"),
    ("Update check failed", "Güncelleme kontrolü başarısız"),
    ("Launcher is already up to date", "Lust güncel"),
    ("Continuing startup", "Açılışa devam ediliyor"),
    ("Verifying game hashes", "Oyun dosyaları doğrulanıyor"),
    ("Checking game hashes", "Oyun dosyaları kontrol ediliyor"),
    ("Updating game hashes", "Oyun dosyaları güncelleniyor"),
    ("Game hashes are valid", "Oyun dosyaları geçerli"),
    ("Game hashes updated successfully", "Oyun dosyaları güncellendi"),
    ("Downloading hash file", "Hash dosyası indiriliyor"),
    ("Merging hashes files", "Hash dosyaları birleştiriliyor"),
    ("Verifying skin library", "Skin kütüphanesi doğrulanıyor"),
    ("Checking installed skins", "Kurulu skinler kontrol ediliyor"),
    ("Checking for skin updates", "Skin güncellemeleri kontrol ediliyor"),
    ("Downloading latest skins", "Son skinler indiriliyor"),
    ("Downloading skins", "Skinler indiriliyor"),
    ("Downloading", "İndiriliyor"),
    ("Extracting skin ID mapping", "Skin kimlikleri çıkarılıyor"),
    ("Extracting skins", "Skinler çıkarılıyor"),
    ("Extracting previews", "Önizlemeler çıkarılıyor"),
    ("Extracting", "Çıkarılıyor"),
    ("Skins ready", "Skinler hazır"),
    ("Skin download failed", "Skin indirme başarısız"),
    ("All checks complete", "Tüm kontroller tamam"),
    ("Launching Lust", "Lust başlatılıyor"),
]


def _translate(text: str) -> str:
    if LANG != "tr" or not text:
        return text
    for english, turkish in TR_MESSAGES:
        if text.startswith(english):
            rest = text[len(english):]
            rest = re.sub(r"^(\.\.\.|…)", "…", rest)
            return turkish + rest
    return text


# ---- state ----

def _set(**values) -> None:
    with _lock:
        _state.update(values)


def toast(text: str) -> None:
    _set(toast={"text": text, "id": time.time()})


def window_visible() -> bool:
    from launcher import lust_hub_server, lust_hub_window
    return lust_hub_server.page_open() or lust_hub_window.visible()


def set_ready(ready: bool) -> None:
    """Lust's tray icon went bloomed (skins ready, injection possible) or wilted."""
    _set(ready=bool(ready))


def _cached(key: str, ttl: float, compute: Callable):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        value = compute()
    except Exception as exc:  # noqa: BLE001 - a status probe must never break the window
        log.debug(f"[Hub] {key} probe failed: {exc}")
        value = hit[1] if hit else None
    _cache[key] = (now, value)
    return value


def _league_running() -> bool:
    from launcher.lust_offline import LEAGUE_CLIENT_PROCESSES, _processes
    return bool(_processes(LEAGUE_CLIENT_PROCESSES))


def _offline_status():
    from launcher.lust_offline import current_status, lust_offline_running
    return {"running": lust_offline_running(), "status": current_status()}


def _autostart() -> bool:
    from utils.system.admin_utils import is_registered_for_autostart
    return is_registered_for_autostart()


def _news():
    from utils.core.paths import get_assets_dir
    path = get_assets_dir().parent / "Pengu Loader" / "plugins" / "LUST-News" / "whats-new.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"version": data.get("version", ""), "items": data.get(LANG) or data.get("en") or []}


def _hero():
    from launcher import lust_hero
    return lust_hero.get()


def _auto_update_on() -> bool:
    from launcher import lust_autoupdate
    return lust_autoupdate.enabled()


def _auto_update_pending():
    from launcher import lust_autoupdate
    return lust_autoupdate.pending()


def _toggle_auto_update() -> str:
    from launcher import lust_autoupdate
    on = not lust_autoupdate.enabled()
    lust_autoupdate.set_enabled(on)
    _cache.pop("auto_update", None)
    if on:
        threading.Thread(target=_check_release, daemon=True).start()
    return "Otomatik güncelleme açık" if on else "Otomatik güncelleme kapalı: yeni sürümde sorulacak"


def _rose_status():
    from launcher import lust_rose
    return lust_rose.status()


def _rose_uninstall() -> str:
    from launcher import lust_rose
    _cache.pop("rose", None)
    return lust_rose.uninstall()


def _spotify_status():
    from launcher import lust_spotify
    return lust_spotify.status()


def _spotify_apply(theme: str) -> str:
    from launcher import lust_spotify
    toast("Spotify teması uygulanıyor…")
    _cache.pop("spotify", None)
    message = lust_spotify.apply(theme)
    _cache.pop("spotify", None)
    return message


def _spotify_auto() -> str:
    from launcher import lust_spotify
    lust_spotify.set_auto(not lust_spotify.settings().get("auto", True))
    _cache.pop("spotify", None)
    return ""


def _version_tuple(version: str):
    return tuple(int(part) for part in re.findall(r"\d+", version or ""))


def _refresh_language() -> None:
    # The desktop hub is in Turkish (its English texts stay for a later language choice)
    global LANG
    LANG = "tr"


def snapshot() -> dict:
    _refresh_language()
    with _lock:
        state = dict(_state)
    latest = state.pop("latest")
    state.update(
        lang=LANG,
        version=APP_VERSION,
        latest=latest,
        update_available=bool(latest) and _version_tuple(latest) > _version_tuple(APP_VERSION),
        running=_tray is not None,
        league=bool(_cached("league", 2, _league_running)),
        offline=_cached("offline", 2, _offline_status) or {"running": False, "status": ""},
        autostart=bool(_cached("autostart", 30, _autostart)),
        news=_cached("news", 300, _news) or {"version": "", "items": []},
        spotify=_cached("spotify", 5, _spotify_status) or {},
        rose=_cached("rose", 20, _rose_status) or {},
        auto_update=_cached("auto_update", 5, _auto_update_on),
        pending=_auto_update_pending(),
        hero=_hero(),
    )
    state["detail"] = _translate(state["detail"])
    state["status"] = _translate(state["status"])
    return state


# ---- actions ----

def _open_league() -> str:
    from launcher import lust_offline
    if _league_running():
        return "League zaten açık" if LANG == "tr" else "League is already open"
    exe = lust_offline._exe()
    if not exe.exists():
        return "Lust Offline bulunamadı" if LANG == "tr" else "Lust Offline is missing"
    lust_offline._close(lust_offline.RIOT_CLIENT_PROCESSES)
    if lust_offline._launch(exe):
        return "League açılıyor…" if LANG == "tr" else "Opening League…"
    return "League açılamadı" if LANG == "tr" else "Couldn't open League"


def _set_offline(command: str) -> str:
    from launcher.lust_offline import set_status
    _cache.pop("offline", None)
    if set_status(command):
        return ""
    return ("Durum değişmedi: League, Lust üzerinden açılmamış" if LANG == "tr"
            else "Status unchanged: League wasn't opened through Lust")


def _open_mods() -> str:
    from utils.core.paths import get_user_data_dir, open_folder_in_explorer
    folder = get_user_data_dir() / "mods"
    folder.mkdir(parents=True, exist_ok=True)
    open_folder_in_explorer(folder)
    return ""


def _copy_log() -> str:
    from utils.core.paths import get_user_data_dir
    logs = sorted((get_user_data_dir() / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime)
    if not logs:
        return "Henüz log yok" if LANG == "tr" else "No log yet"
    # A file on the clipboard: pasting into Discord or a GitHub issue attaches it
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "Set-Clipboard -LiteralPath $env:LUST_LOG"],
        env={**os.environ, "LUST_LOG": str(logs[-1])},
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=15,
    )
    if result.returncode != 0:
        return "Log kopyalanamadı" if LANG == "tr" else "Couldn't copy the log"
    return ("Log panoya kopyalandı: Discord'a ya da GitHub'a yapıştırabilirsin" if LANG == "tr"
            else "Log copied: paste it into Discord or a GitHub issue")


def _toggle_autostart() -> str:
    from utils.system.admin_utils import register_autostart, unregister_autostart
    on = _autostart()
    ok, message = unregister_autostart() if on else register_autostart()
    _cache.pop("autostart", None)
    log.info(f"[Hub] Start with Windows {'off' if on else 'on'}: {message}")
    if not ok:
        return "Değiştirilemedi" if LANG == "tr" else "Couldn't change it"
    return ""


def _restart() -> str:
    if _tray is None:
        return ""
    threading.Thread(target=lambda: _tray._on_restart(_tray.icon, None), daemon=True).start()
    return ""


def _quit() -> str:
    if _tray is None:
        # Still starting up: nothing to clean up yet
        threading.Timer(0.3, lambda: os._exit(0)).start()
        return ""
    threading.Thread(target=lambda: _tray._on_quit(_tray.icon, None), daemon=True).start()
    return ""


def _update_now() -> str:
    """Restart into the launcher, which installs the release without asking again."""
    from utils.core.paths import get_user_data_dir
    (get_user_data_dir() / "hub_update_accepted").write_text(APP_VERSION, encoding="utf-8")
    return _restart()


def _check_now() -> str:
    threading.Thread(target=_check_release, daemon=True).start()
    return ""


def _answer_prompt(accept: bool) -> str:
    global _prompt_answer
    _prompt_answer = accept
    _set(prompt=None)
    _prompt_event.set()
    return ""


ACTIONS: dict[str, Callable[[dict], str]] = {
    "league": lambda body: _open_league(),
    "status": lambda body: _set_offline(body.get("value", "")) if body.get("value") in ("online", "offline", "mobile") else "",
    "mods": lambda body: _open_mods(),
    "log": lambda body: _copy_log(),
    "autostart": lambda body: _toggle_autostart(),
    "restart": lambda body: _restart(),
    "quit": lambda body: _quit(),
    "update": lambda body: _update_now(),
    "check": lambda body: _check_now(),
    "prompt": lambda body: _answer_prompt(bool(body.get("accept"))),
    "spotify_apply": lambda body: _spotify_apply(str(body.get("theme") or "")),
    "spotify_auto": lambda body: _spotify_auto(),
    "rose_uninstall": lambda body: _rose_uninstall(),
    "auto_update": lambda body: _toggle_auto_update(),
}


# ---- release check ----

def _check_release() -> None:
    try:
        from launcher.update.github_client import GitHubClient
        client = GitHubClient(timeout=10)
        release = client.get_latest_release()
        if release:
            _set(latest=client.get_release_version(release).lstrip("vV"), checked_at=int(time.time()))
            from launcher import lust_autoupdate
            lust_autoupdate.on_release(client, release, APP_VERSION)
    except Exception as exc:  # noqa: BLE001
        log.debug(f"[Hub] Release check failed: {exc}")


def _release_watch() -> None:
    while True:
        _check_release()
        time.sleep(UPDATE_CHECK_INTERVAL_S)
        _spotify_reapply()


QUIET_FLAG = "hub_quiet_restart"
QUIET_FOR_S = 180


def mark_quiet_restart() -> None:
    """The next start (a silent update) keeps the hub window closed unless it was open."""
    if window_visible():
        return
    try:
        from utils.core.paths import get_user_data_dir
        (get_user_data_dir() / QUIET_FLAG).write_text("1", encoding="utf-8")
    except OSError:
        pass


def _take_quiet_restart() -> bool:
    try:
        from utils.core.paths import get_user_data_dir
        flag = get_user_data_dir() / QUIET_FLAG
        if not flag.exists():
            return False
        # An update starts Lust twice (to install, then the new version): both stay quiet
        if time.time() - flag.stat().st_mtime < QUIET_FOR_S:
            return True
        flag.unlink()
    except OSError:
        pass
    return False


def take_update_acceptance() -> bool:
    """True once when the player pressed Update in the hub before this restart."""
    try:
        from utils.core.paths import get_user_data_dir
        flag = get_user_data_dir() / "hub_update_accepted"
        if flag.exists():
            flag.unlink()
            return True
    except OSError:
        pass
    return False


def run_action(name: str, body: Optional[dict] = None) -> str:
    """Run a hub button's action (off the window's thread: some take a moment) and toast its message."""
    action = ACTIONS.get(name)
    if not action:
        return ""
    try:
        message = action(body or {})
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[Hub] Action {name} failed: {exc}")
        message = "Bir şeyler ters gitti" if LANG == "tr" else "Something went wrong"
    if message:
        toast(message)
    return message


# ---- window ----

_shell: Optional[subprocess.Popen] = None
SHELL_START_S = 12.0
# A hub window Windows calls "not responding" this long is closed and opened again
WATCH_EVERY_S = 5.0
HUNG_STRIKES = 3
MAX_REOPENS = 2
_watchdog_started = False
_reopens = 0
_use_basic_window = False


def _shell_window() -> int:
    """The WebView2 window of the running shell process, if it shows one."""
    if not _shell or _shell.poll() is not None:
        return 0
    user32 = ctypes.windll.user32
    found = []
    pid = ctypes.c_ulong()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def check(hwnd, _):
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == _shell.pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(check, 0)
    return found[0] if found else 0


def _open_web() -> bool:
    """The WebView2 window (a second Lust process, see lust_hub_shell). False when it can't show."""
    global _shell
    from launcher import lust_hub_server
    from launcher.lust_hub_shell import ARG, PARENT_ARG
    if not lust_hub_server.start():
        return False
    hwnd = _shell_window()
    if hwnd:
        from launcher.lust_hub_window import _in_game
        if not _in_game():
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    if getattr(sys, "frozen", False):
        command = [sys.executable, ARG, lust_hub_server.url()]
    else:
        from utils.core.paths import get_app_dir
        command = [sys.executable, str(get_app_dir() / "main.py"), ARG, lust_hub_server.url()]
    # The window closes with this Lust, so it never holds Lust's files during an update
    command += [PARENT_ARG, str(os.getpid())]
    try:
        _shell = subprocess.Popen(command, close_fds=True,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        log.warning(f"[Hub] Could not start the hub window: {exc}")
        return False
    _start_watchdog()
    deadline = time.time() + SHELL_START_S
    while time.time() < deadline:
        if lust_hub_server.page_open():
            return True
        if _shell.poll() is not None:
            log.warning(f"[Hub] The hub window closed at once (exit {_shell.returncode}); using the basic window")
            return False
        time.sleep(0.1)
    return _shell.poll() is None


def _close_shell() -> None:
    if _shell and _shell.poll() is None:
        _shell.terminate()


def _kill_shell(shell: subprocess.Popen) -> None:
    """End the window process and its WebView2 processes, which hold its browser folder."""
    try:
        import psutil
        parent = psutil.Process(shell.pid)
        procs = parent.children(recursive=True) + [parent]
        for proc in procs:
            try:
                proc.kill()
            except psutil.Error:
                pass
        psutil.wait_procs(procs, timeout=5)
    except Exception as exc:  # noqa: BLE001
        log.debug(f"[Hub] Could not end the hub window: {exc}")


def _window_hung() -> bool:
    hwnd = _shell_window()
    return bool(hwnd) and bool(ctypes.windll.user32.IsHungAppWindow(hwnd))


def _watch_shell() -> None:
    """The WebView2 window can lock up while it starts (seen right after a restart, when the
    previous window's WebView2 was still closing). Close it and open it again; after a few
    tries the basic window is used instead."""
    global _reopens, _use_basic_window
    strikes = 0
    while True:
        time.sleep(WATCH_EVERY_S)
        try:
            strikes = strikes + 1 if _window_hung() else 0
            if strikes < HUNG_STRIKES:
                continue
            strikes = 0
            shell = _shell
            log.warning("[Hub] The hub window stopped responding; closing it")
            _kill_shell(shell)
            _reopens += 1
            if _reopens > MAX_REOPENS:
                log.warning("[Hub] The hub window keeps locking up; using the basic window")
                _use_basic_window = True
            time.sleep(1)
            open_window()
        except Exception as exc:  # noqa: BLE001
            log.debug(f"[Hub] Window watch failed: {exc}")


def _start_watchdog() -> None:
    global _watchdog_started
    if not _watchdog_started:
        _watchdog_started = True
        threading.Thread(target=_watch_shell, daemon=True, name="LustHubWatch").start()


atexit.register(_close_shell)


def open_window() -> bool:
    """Show the hub window (raise it when it's already open). False when it can't be shown.

    The WebView2 window first; Lust's basic Tk window when WebView2 can't start.
    """
    if sys.platform != "win32":
        return False
    try:
        if not _use_basic_window and _open_web():
            return True
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[Hub] Hub window failed: {exc}")
    try:
        from launcher import lust_hub_window
        return lust_hub_window.show()
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[Hub] Could not open the window: {exc}")
        return False


def attach(tray_manager) -> None:
    """Lust is running: the hub gets its tray callbacks and starts watching for releases."""
    global _tray
    _tray = tray_manager
    _set(phase="ready", progress=100, detail="", status="")
    threading.Thread(target=_release_watch, daemon=True, name="LustHubReleases").start()
    threading.Thread(target=_spotify_reapply, daemon=True, name="LustSpotify").start()
    from launcher import lust_cleanup, lust_rose
    threading.Thread(target=lust_cleanup.run, daemon=True, name="LustCleanup").start()
    lust_rose.keep_rose_off()
    from launcher import lust_hero
    lust_hero.start()


def _spotify_reapply() -> None:
    try:
        from launcher import lust_spotify
        message = lust_spotify.reapply_if_updated()
        if message:
            toast(message)
    except Exception as exc:  # noqa: BLE001
        log.debug(f"[Hub] Spotify re-apply failed: {exc}")


# ---- startup (the launcher's dialog) ----

def _started_quietly() -> bool:
    """Started with Windows: stay in the tray unless something needs the player."""
    from launcher.lust_offline import BOOT_GRACE_MS, _started_at_logon
    uptime = ctypes.windll.kernel32.GetTickCount64
    uptime.restype = ctypes.c_ulonglong
    return uptime() < BOOT_GRACE_MS or _started_at_logon()


class HubDialog:
    """The launcher dialog's methods, shown in the hub instead of a Win32 window."""

    hwnd = None

    def __init__(self, show: bool) -> None:
        self._show = show
        self._bytes = None
        _set(phase="starting", detail="Preparing Lust…", status="", progress=None, transfer="")

    def show_window(self, *_args) -> None:
        if self._show:
            open_window()

    def pump_messages(self, block: bool = False) -> bool:
        if block:
            time.sleep(0.1)
        return True

    def allow_close(self) -> None:
        pass

    def destroy_window(self) -> None:
        pass

    def set_detail(self, text: str) -> None:
        _set(detail=text)

    def set_status(self, text: str) -> None:
        clean = re.sub(r"\s*/\s*\?\s*$", "", text or "").strip()
        sizes = re.findall(r"\d+(?:\.\d+)?\s*(?:B|KB|MB|GB|TB)\b", clean, flags=re.IGNORECASE)
        title = re.sub(r"\s*\d+(?:\.\d+)?\s*(?:B|KB|MB|GB|TB)(?:\s*/\s*\d+(?:\.\d+)?\s*(?:B|KB|MB|GB|TB))?\s*$",
                       "", clean, flags=re.IGNORECASE).strip()
        values = {"status": title or clean}
        if sizes and self._bytes is None:
            values["transfer"] = " / ".join(sizes[:2])
        _set(**values)

    def set_progress(self, value: int) -> None:
        try:
            _set(progress=max(0, min(100, int(value))))
        except (TypeError, ValueError):
            pass

    def reset_progress(self) -> None:
        _set(progress=None)

    def set_marquee(self, enabled: bool) -> None:
        if enabled:
            _set(progress=None)

    def clear_transfer_text(self) -> None:
        self._bytes = None
        _set(transfer="")

    @staticmethod
    def _mb(value: int) -> str:
        return f"{value / (1024 * 1024):.1f} MB"

    def update_transfer_progress(self, downloaded: int, total: Optional[int]) -> None:
        self._bytes = downloaded
        text = self._mb(downloaded) + (f" / {self._mb(total)}" if total else "")
        values = {"transfer": text}
        if total:
            values["progress"] = int(downloaded * 100 / total)
        _set(**values)

    def confirm_update(self, remote_version: str, local_version: str) -> Optional[bool]:
        """Ask in the hub. None when the window can't be shown, so the caller asks its own way."""
        global _prompt_answer
        if take_update_acceptance():
            log.info(f"[Hub] Update to {remote_version} accepted in the hub before restarting")
            return True
        from launcher import lust_autoupdate
        if lust_autoupdate.enabled():
            log.info(f"[Hub] Auto update is on: installing {remote_version} without asking")
            return True
        _prompt_event.clear()
        _prompt_answer = None
        _set(prompt={"version": remote_version, "current": local_version})
        if not window_visible():
            open_window()
            deadline = time.time() + WINDOW_WAIT_S
            while not window_visible() and time.time() < deadline:
                time.sleep(0.2)
            if not window_visible():
                _set(prompt=None)
                return None
        # Closing the window without answering is a "not now"
        while not _prompt_event.wait(0.3) and window_visible():
            pass
        _set(prompt=None)
        return bool(_prompt_answer)


def make_launcher_dialog():
    """The hub when its window can be shown, else Rose's Win32 progress dialog."""
    if sys.platform == "win32":
        try:
            from launcher import lust_hub_window
            if lust_hub_window.available():
                # Started with Windows, during a match or by a silent update: stay in the tray
                quiet = _take_quiet_restart()
                return HubDialog(show=not quiet and not _started_quietly() and not lust_hub_window._in_game())
        except Exception as exc:  # noqa: BLE001
            log.warning(f"[Hub] Window unavailable: {exc}")
    from launcher.ui.update_dialog import UpdateDialog
    return UpdateDialog()
