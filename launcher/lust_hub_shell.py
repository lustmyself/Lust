"""The desktop hub's window: a WebView2 window in its own small process.

pywebview needs the main thread, which Lust's main loop holds, so Lust starts itself again
as `Lust.exe --lust-hub-window <url>` and this process only shows the page Lust serves
(launcher/lust_hub_server.py). It is frameless: the page draws its own title bar, drags by
its `pywebview-drag-region` and calls back here to minimize and close.

It closes with the Lust that started it (`--lust-parent <pid>`): a window left open runs
from Lust's files and kept an update from replacing them.
"""

from __future__ import annotations

import os
import sys
import threading

ARG = "--lust-hub-window"
PARENT_ARG = "--lust-parent"
SIZE = (1000, 584)  # fits the LoL page without empty space below it


class _Api:
    """What the page may call. pywebview hands the page every public attribute, walking into
    objects: a public window here made it read WebView2's controls from its own thread, which
    flooded the log and locked the window up. The window stays private."""

    def __init__(self) -> None:
        self._window = None

    def minimize(self) -> None:
        self._window.minimize()

    def close(self) -> None:
        self._window.destroy()


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
    api._window = webview.create_window(
        "Lust", url, js_api=api, width=SIZE[0], height=SIZE[1], min_size=(860, 520),
        frameless=True, easy_drag=False, background_color="#16141f",
    )
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
