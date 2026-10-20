"""The desktop hub's window: a WebView2 window in its own small process.

pywebview needs the main thread, which Lust's main loop holds, so Lust starts itself again
as `Lust.exe --lust-hub-window <url>` and this process only shows the page Lust serves
(launcher/lust_hub_server.py). It is frameless: the page draws its own title bar, drags by
its `pywebview-drag-region` and calls back here to minimize and close.
"""

from __future__ import annotations

import sys

ARG = "--lust-hub-window"
SIZE = (1000, 660)


class _Api:
    def __init__(self) -> None:
        self.window = None

    def minimize(self) -> None:
        self.window.minimize()

    def close(self) -> None:
        self.window.destroy()


def run(url: str) -> None:
    import webview
    from utils.core.paths import get_user_data_dir

    api = _Api()
    api.window = webview.create_window(
        "Lust", url, js_api=api, width=SIZE[0], height=SIZE[1], min_size=(860, 600),
        frameless=True, easy_drag=False, background_color="#16141f",
    )
    storage = get_user_data_dir() / "hub-webview"
    storage.mkdir(parents=True, exist_ok=True)
    webview.start(gui="edgechromium", private_mode=False, storage_path=str(storage))


def main_if_window(argv=None) -> bool:
    """Run the window when this process was started for it. True when it was."""
    argv = sys.argv if argv is None else argv
    if ARG not in argv:
        return False
    index = argv.index(ARG)
    url = argv[index + 1] if index + 1 < len(argv) else ""
    if url.startswith("http://127.0.0.1:"):
        run(url)
    return True
