"""The desktop hub's window: a WebView2 window in its own small process.

pywebview needs the main thread, which Lust's main loop holds, so Lust starts itself again
as `Lust.exe --lust-hub-window <url>` and this process only shows the page Lust serves
(launcher/lust_hub_server.py). It is frameless: the page draws its own title bar, drags by
its `pywebview-drag-region` and calls back here to minimize, maximize, go full screen, resize
from its edges and close. Its size and place are kept for the next time.

It closes with the Lust that started it (`--lust-parent <pid>`): a window left open runs
from Lust's files and kept an update from replacing them.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time

ARG = "--lust-hub-window"
PARENT_ARG = "--lust-parent"
SIZE = (1280, 800)
MIN_SIZE = (980, 640)
GEOMETRY_FILE = "hub-window.json"
EDGES = ("n", "s", "e", "w", "ne", "nw", "se", "sw")


# ---- size and place ----

def resized(edge: str, rect, dx: int, dy: int, min_size=MIN_SIZE):
    """The window's (left, top, right, bottom) after dragging `edge` by (dx, dy), never under min_size."""
    left, top, right, bottom = rect
    if "w" in edge:
        left = min(left + dx, right - min_size[0])
    if "e" in edge:
        right = max(right + dx, left + min_size[0])
    if "n" in edge:
        top = min(top + dy, bottom - min_size[1])
    if "s" in edge:
        bottom = max(bottom + dy, top + min_size[1])
    return left, top, right, bottom


def clean_geometry(data, screen=None):
    """A saved {x, y, width, height, maximized} that still fits: the size at least MIN_SIZE, the
    place kept only when the window's top lands on the screen. None when nothing usable is saved."""
    if not isinstance(data, dict):
        return None
    try:
        width, height = int(data.get("width")), int(data.get("height"))
    except (TypeError, ValueError):
        return None
    out = {"width": max(width, MIN_SIZE[0]), "height": max(height, MIN_SIZE[1]),
           "maximized": bool(data.get("maximized")), "x": None, "y": None}
    x, y = data.get("x"), data.get("y")
    if isinstance(x, int) and isinstance(y, int) and screen:
        sx, sy, sw, sh = screen
        if sx - out["width"] + 120 <= x <= sx + sw - 120 and sy <= y <= sy + sh - 60:
            out["x"], out["y"] = x, y
    return out


def _geometry_path():
    from utils.core.paths import get_user_data_dir
    return get_user_data_dir() / GEOMETRY_FILE


def _load_geometry():
    try:
        data = json.loads(_geometry_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return clean_geometry(data, _virtual_screen())


def _save_geometry(rect, maximized: bool) -> None:
    if not rect:
        return
    left, top, right, bottom = rect
    data = {"x": left, "y": top, "width": right - left, "height": bottom - top, "maximized": maximized}
    try:
        _geometry_path().write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def _virtual_screen():
    if sys.platform != "win32":
        return None
    import ctypes
    metric = ctypes.windll.user32.GetSystemMetrics
    return metric(76), metric(77), metric(78), metric(79)  # SM_X/Y/CX/CYVIRTUALSCREEN


class _Win32:
    """The window by its handle: Win32 calls work from any thread, unlike the WinForms form."""

    SWP = 0x0004 | 0x0010  # SWP_NOZORDER | SWP_NOACTIVATE

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.wintypes = ctypes, wintypes
        self.user32 = ctypes.windll.user32
        self.hwnd = 0

    def find(self) -> int:
        """This process's visible top-level window."""
        if self.hwnd and self.user32.IsWindow(self.hwnd):
            return self.hwnd
        ctypes, wintypes = self.ctypes, self.wintypes
        pid = os.getpid()
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def check(hwnd, _):
            owner = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and self.user32.IsWindowVisible(hwnd):
                found.append(hwnd)
                return False
            return True

        self.user32.EnumWindows(check, 0)
        self.hwnd = found[0] if found else 0
        return self.hwnd

    def rect(self):
        hwnd = self.find()
        if not hwnd:
            return None
        r = self.wintypes.RECT()
        self.user32.GetWindowRect(hwnd, self.ctypes.byref(r))
        return r.left, r.top, r.right, r.bottom

    def place(self, rect) -> None:
        hwnd = self.find()
        if hwnd and rect:
            left, top, right, bottom = rect
            self.user32.SetWindowPos(hwnd, 0, left, top, right - left, bottom - top, self.SWP)

    def monitor(self, work: bool):
        """The (left, top, right, bottom) of the window's screen: without the taskbar when `work`."""
        ctypes, wintypes = self.ctypes, self.wintypes

        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

        hwnd = self.find()
        if not hwnd:
            return None
        self.user32.MonitorFromWindow.restype = ctypes.c_void_p
        monitor = self.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not self.user32.GetMonitorInfoW(ctypes.c_void_p(monitor), ctypes.byref(info)):
            return None
        r = info.rcWork if work else info.rcMonitor
        return r.left, r.top, r.right, r.bottom

    def cursor(self):
        point = self.wintypes.POINT()
        self.user32.GetCursorPos(self.ctypes.byref(point))
        return point.x, point.y

    def mouse_down(self) -> bool:
        return bool(self.user32.GetAsyncKeyState(0x01) & 0x8000)  # VK_LBUTTON


class _Api:
    """What the page may call. pywebview hands the page every public attribute, walking into
    objects: a public window here made it read WebView2's controls from its own thread, which
    flooded the log and locked the window up. The window stays private."""

    def __init__(self) -> None:
        self._window = None
        self._win32 = None
        self._mode = "normal"  # normal, maximized, fullscreen
        self._normal = None  # the window's rect before it was maximized or went full screen
        self._resizing = False

    def _w(self):
        if self._win32 is None:
            self._win32 = _Win32()
        return self._win32

    def minimize(self) -> None:
        self._window.minimize()

    def close(self) -> None:
        self._remember()
        self._window.destroy()

    def _remember(self) -> None:
        try:
            rect = self._normal if self._mode != "normal" else self._w().rect()
            _save_geometry(rect, self._mode == "maximized")
        except Exception:  # noqa: BLE001
            pass

    def _fill(self, mode: str) -> str:
        win = self._w()
        if self._mode == mode:
            win.place(self._normal)
            self._mode = "normal"
            return self._mode
        if self._mode == "normal":
            self._normal = win.rect()
        area = win.monitor(work=(mode == "maximized"))
        if area:
            win.place(area)
            self._mode = mode
        return self._mode

    def toggle_maximize(self) -> str:
        """Fill the screen above the taskbar, or go back. The new mode for the page."""
        return self._fill("maximized")

    def toggle_fullscreen(self) -> str:
        """Fill the whole screen (F11), or go back."""
        return self._fill("fullscreen")

    def mode(self) -> str:
        return self._mode

    def begin_resize(self, edge: str) -> None:
        """The page's edge was pressed: follow the mouse until the button is let go."""
        if edge not in EDGES or self._mode != "normal" or self._resizing:
            return
        self._resizing = True
        threading.Thread(target=self._follow, args=(edge,), daemon=True, name="LustHubResize").start()

    def _follow(self, edge: str) -> None:
        win = self._w()
        try:
            start, origin = win.rect(), win.cursor()
            if not start:
                return
            last = start
            while win.mouse_down():
                x, y = win.cursor()
                rect = resized(edge, start, x - origin[0], y - origin[1])
                if rect != last:
                    win.place(rect)
                    last = rect
                time.sleep(0.012)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._resizing = False


def _close_with(pid: int, api: "_Api") -> None:
    """Wait for the Lust that started this window, then close it."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return  # can't watch it: the window stays until it is closed
    kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0xFFFFFFFF)
    kernel32.CloseHandle(ctypes.c_void_p(handle))
    threading.Timer(1.0, lambda: os._exit(0)).start()
    try:
        api._remember()
        api._window.destroy()
    except Exception:  # noqa: BLE001
        pass


def _wait_for_old_webview(storage, timeout: float = 8.0) -> None:
    """A window that just closed may still have WebView2 running on the same browser folder;
    starting another one on it then can lock the new window up."""
    import time
    import psutil
    folder = str(storage).lower()
    deadline = time.time() + timeout
    while time.time() < deadline:
        busy = False
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if (proc.info.get("name") or "").lower() == "msedgewebview2.exe" \
                        and folder in " ".join(proc.info.get("cmdline") or []).lower():
                    busy = True
                    break
            except psutil.Error:
                continue
        if not busy:
            return
        time.sleep(0.3)


def run(url: str, parent: int = 0) -> None:
    import webview
    from utils.core.paths import get_user_data_dir

    api = _Api()
    try:
        saved = _load_geometry()
    except Exception:  # noqa: BLE001
        saved = None
    width, height = (saved["width"], saved["height"]) if saved else SIZE
    place = {"x": saved["x"], "y": saved["y"]} if saved and saved["x"] is not None else {}
    api._window = webview.create_window(
        "Lust", url, js_api=api, width=width, height=height, min_size=MIN_SIZE,
        frameless=True, easy_drag=False, background_color="#0a0d2c", **place,
    )
    if saved and saved["maximized"]:
        api._window.events.shown += lambda: api.toggle_maximize()
    if parent:
        threading.Thread(target=_close_with, args=(parent, api), daemon=True, name="LustHubParent").start()
    storage = get_user_data_dir() / "hub-webview"
    storage.mkdir(parents=True, exist_ok=True)
    try:
        _wait_for_old_webview(storage)
    except Exception:  # noqa: BLE001
        pass
    webview.start(gui="edgechromium", private_mode=False, storage_path=str(storage))


def main_if_window(argv=None) -> bool:
    """Run the window when this process was started for it. True when it was."""
    argv = sys.argv if argv is None else argv
    if ARG not in argv:
        return False
    index = argv.index(ARG)
    url = argv[index + 1] if index + 1 < len(argv) else ""
    parent = 0
    if PARENT_ARG in argv:
        value = argv[argv.index(PARENT_ARG) + 1] if argv.index(PARENT_ARG) + 1 < len(argv) else ""
        parent = int(value) if value.isdigit() else 0
    if url.startswith("http://127.0.0.1:"):
        run(url, parent)
    return True
