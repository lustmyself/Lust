"""Silent updates: download a new Lust while it runs, install it when League is closed.

The hub's release check calls `on_release()`: with "auto update" on (the default) the
update package is downloaded in the background into Lust's updates folder, next to a
`.ready` file holding its size. The launcher's update sequence then skips its own
download for that package, and the hub's update question answers itself.

The install needs Lust to restart into its launcher. That happens only while no League
client or game runs (checked twice, a minute apart), so nobody is cut off mid-game;
otherwise the package waits for the next start.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

import requests

from utils.core.logging import get_logger

log = get_logger()

CONFIG_KEY = "autoUpdate"
IDLE_CHECK_S = 60
LEAGUE = {"leagueclient.exe", "leagueclientux.exe", "league of legends.exe"}
_lock = threading.Lock()
_pending: Optional[str] = None  # version downloaded and waiting to be installed
_waiter: Optional[threading.Thread] = None


def enabled() -> bool:
    from config import get_config_option
    return (get_config_option("General", CONFIG_KEY) or "1") != "0"


def set_enabled(on: bool) -> None:
    from config import set_config_option
    set_config_option("General", CONFIG_KEY, "1" if on else "0")


def pending() -> Optional[str]:
    return _pending


def _updates_dir() -> Path:
    from config import get_config_file_path
    path = get_config_file_path().parent / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ready_path(zip_path: Path) -> Path:
    return zip_path.with_name(zip_path.name + ".ready")


def is_ready(zip_path: Path) -> bool:
    """The package was fully downloaded in the background."""
    try:
        return zip_path.is_file() and ready_path(zip_path).read_text(encoding="utf-8").strip() == str(zip_path.stat().st_size)
    except OSError:
        return False


def _download(url: str, target: Path, expected: int = 0) -> bool:
    part = target.with_name(target.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with part.open("wb") as handle:
                for chunk in response.iter_content(1024 * 256):
                    handle.write(chunk)
        size = part.stat().st_size
        if size == 0 or (expected and size != expected):
            raise OSError(f"size {size}, expected {expected}")
        import zipfile
        with zipfile.ZipFile(part) as archive:
            if archive.testzip() is not None:
                raise OSError("the package is damaged")
        part.replace(target)
        ready_path(target).write_text(str(size), encoding="utf-8")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[AutoUpdate] Download failed: {exc}")
        part.unlink(missing_ok=True)
        return False


def _league_running() -> bool:
    import psutil
    return any((p.info.get("name") or "").lower() in LEAGUE for p in psutil.process_iter(["name"]))


def _install_when_idle(version: str) -> None:
    """Restart Lust into its installer once League has been closed for a minute."""
    idle_checks = 0
    while _pending == version and enabled():
        idle_checks = idle_checks + 1 if not _league_running() else 0
        if idle_checks >= 2:
            from launcher import lust_hub
            log.info(f"[AutoUpdate] League is closed; restarting Lust to install {version}")
            lust_hub.toast(f"Lust {version} kuruluyor, birkaç saniye sürecek")
            lust_hub.mark_quiet_restart()
            time.sleep(3)
            lust_hub.run_action("update")
            return
        time.sleep(IDLE_CHECK_S)


def on_release(client, release: dict, current: str) -> None:
    """A release check found `release`: download it in the background when it is newer."""
    global _pending, _waiter
    from launcher import lust_hub
    version = client.get_release_version(release).lstrip("vV")
    if not enabled() or not lust_hub._version_tuple(version) > lust_hub._version_tuple(current):
        return
    asset = client.get_zip_asset(release)
    if not asset or not asset.get("browser_download_url"):
        return
    target = _updates_dir() / (asset.get("name") or f"update_package_{version}.zip")
    with _lock:
        if _pending == version:
            return
        if not is_ready(target):
            log.info(f"[AutoUpdate] Downloading Lust {version} in the background")
            if not _download(asset["browser_download_url"], target, int(asset.get("size") or 0)):
                return
        _pending = version
    log.info(f"[AutoUpdate] Lust {version} is downloaded and waits for League to be closed")
    lust_hub.toast(f"Lust {version} indirildi; League kapalıyken kendiliğinden kurulacak")
    if not _waiter or not _waiter.is_alive():
        _waiter = threading.Thread(target=_install_when_idle, args=(version,), daemon=True, name="LustAutoUpdate")
        _waiter.start()
