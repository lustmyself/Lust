"""Spotify themes for the desktop hub's Spotify tab, through Spicetify.

Lust doesn't patch Spotify itself: it downloads the official Spicetify CLI from its
GitHub releases (github.com/spicetify/cli, LGPL) into Lust's data folder and runs it.
Themes: Luminous (streetraceing/luminous, MIT), Lust's purple and pink (written
here), Sleek's schemes from spicetify-themes (MIT), or Spotify's original look. Spotify updates wipe the patch,
so with "auto" on Lust applies the theme again when Spotify.exe changes.
Lust runs elevated and Spicetify refuses that unless told --bypass-admin.
"""

from __future__ import annotations

import ctypes
import io
import json
import os
import subprocess
import threading
import zipfile
from pathlib import Path
from typing import Optional

import requests

from utils.core.logging import get_logger
from utils.core.paths import get_user_data_dir

log = get_logger()

RELEASES = "https://api.github.com/repos/spicetify/cli/releases/latest"
SLEEK = "https://raw.githubusercontent.com/spicetify/spicetify-themes/master/Sleek/"
LUMINOUS = "https://raw.githubusercontent.com/streetraceing/luminous/main/release/"  # MIT
# key: (theme folder, color scheme, label, preview background, preview accent), in the tab's order
THEMES = {
    "luminous": ("Luminous", "Base", "Luminous", "#1b1b2f", "#7dd3fc"),
    "nord": ("Sleek", "Nord", "Nord", "#2e3440", "#88c0d0"),
    "lust": ("Lust", "Lust", "Mor", "#1a1026", "#a78bfa"),
    "pink": ("Lust", "Pink", "Pembe", "#1f0f18", "#f472b6"),
    "catppuccin": ("Sleek", "Catppuccin", "Catppuccin", "#1e1e2e", "#cba6f7"),
    "dracula": ("Sleek", "Dracula", "Dracula", "#282a36", "#ff79c6"),
    "tokyonight": ("Sleek", "TokyoNight", "Tokyo Night", "#1a1b26", "#7aa2f7"),
    "rosepine": ("Sleek", "RosePine", "Rosé Pine", "#191724", "#ebbcba"),
    "ayudark": ("Sleek", "AyuDark", "Ayu Dark", "#0b0e14", "#e6b450"),
    "eldritch": ("Sleek", "Eldritch", "Eldritch", "#212337", "#37f499"),
    "bladerunner": ("Sleek", "BladeRunner", "Blade Runner", "#0d0d1a", "#ff2e88"),
    "vantablack": ("Sleek", "VantaBlack", "Vantablack", "#000000", "#ffffff"),
    "ultrablack": ("Sleek", "UltraBlack", "UltraBlack", "#050505", "#9ca3af"),
    "cherry": ("Sleek", "Cherry", "Cherry", "#1a0a10", "#f43f5e"),
    "coral": ("Sleek", "Coral", "Coral", "#1b1b1b", "#ff7f50"),
    "deep": ("Sleek", "Deep", "Deep", "#0a0f1f", "#3b82f6"),
    "futura": ("Sleek", "Futura", "Futura", "#101820", "#f2aa4c"),
    "elementary": ("Sleek", "Elementary", "Elementary", "#1c1c1c", "#3689e6"),
    "wealthy": ("Sleek", "Wealthy", "Wealthy", "#0f1410", "#d4af37"),
    "greener": ("Sleek", "Greener", "Greener", "#0d1a12", "#22c55e"),
    "psycho": ("Sleek", "Psycho", "Psycho", "#1a0d1a", "#ff00ff"),
    "original": ("", "", "Orijinal", "#121212", "#1db954"),
}
LUST_COLORS = """[Lust]
text               = f0eef5
subtext            = 8d8a95
main               = 0d0c13
sidebar            = 0b0a10
player             = 0b0a10
card               = 15141d
shadow             = 000000
selected-row       = a78bfa
button             = a78bfa
button-active      = c4b5fd
button-disabled    = 3a3550
tab-active         = 2a2340
notification       = a78bfa
notification-error = f87171
misc               = 24222f

[Pink]
text               = fdf2f8
subtext            = 9d8a95
main               = 140b10
sidebar            = 100809
player             = 100809
card               = 1f0f18
shadow             = 000000
selected-row       = f472b6
button             = f472b6
button-active      = f9a8d4
button-disabled    = 4a2a3a
tab-active         = 3a1a2c
notification       = f472b6
notification-error = f87171
misc               = 2f1a26
"""
LUST_CSS = """/* Lust for Spotify: rounded cards, one purple accent */
.main-card-card, .main-trackList-trackListRow { border-radius: 10px !important; }
.main-playButton-PlayButton button span, .encore-bright-accent-set { background-color: var(--spice-button) !important; }
"""
_lock = threading.Lock()
_busy = False


def _dir() -> Path:
    path = get_user_data_dir() / "spicetify"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _settings_path() -> Path:
    return get_user_data_dir() / "spotify.json"


def settings() -> dict:
    try:
        return json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"theme": "", "auto": True, "marker": ""}


def _save(values: dict) -> None:
    data = {**settings(), **values}
    _settings_path().write_text(json.dumps(data), encoding="utf-8")


def spotify_exe() -> Optional[Path]:
    path = Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe"
    return path if path.is_file() else None


def _store_install() -> bool:
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsApps"
    try:
        return any(p.name.startswith("SpotifyAB.SpotifyMusic") for p in root.iterdir())
    except OSError:
        return False


def _file_version(path: Path) -> str:
    try:
        version = ctypes.windll.version
        size = version.GetFileVersionInfoSizeW(str(path), None)
        buffer = ctypes.create_string_buffer(size)
        version.GetFileVersionInfoW(str(path), 0, size, buffer)
        info = ctypes.c_void_p()
        length = ctypes.c_uint()
        version.VerQueryValueW(buffer, "\\", ctypes.byref(info), ctypes.byref(length))
        ms, ls = ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32 * 4)).contents[2:4]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:  # noqa: BLE001
        return ""


def _marker(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def status() -> dict:
    exe = spotify_exe()
    current = settings()
    return {
        "installed": bool(exe),
        "store": not exe and _store_install(),
        "version": _file_version(exe) if exe else "",
        "theme": current.get("theme", ""),
        "auto": bool(current.get("auto", True)),
        "busy": _busy,
    }


def _cli() -> Path:
    exe = _dir() / "cli" / "spicetify.exe"
    if exe.is_file():
        return exe
    release = requests.get(RELEASES, timeout=20).json()
    asset = next(a for a in release["assets"] if a["name"].endswith("-windows-x64.zip"))
    data = requests.get(asset["browser_download_url"], timeout=120).content
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(exe.parent)
    log.info(f"[Spotify] Spicetify {release.get('tag_name')} downloaded")
    return exe


def _run(*args: str) -> str:
    result = subprocess.run(
        [str(_cli()), *args, "--bypass-admin", "--no-restart"] if args[0] != "config" else
        [str(_cli()), *args, "--bypass-admin"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = (result.stdout + result.stderr).strip()
    log.info(f"[Spotify] spicetify {' '.join(args)} -> {result.returncode}")
    if result.returncode != 0 or "error" in output.lower().split("\n")[-1]:
        raise RuntimeError(output.splitlines()[-1] if output else f"exit {result.returncode}")
    return output


def _themes_dir() -> Path:
    path = Path(os.environ.get("APPDATA", "")) / "spicetify" / "Themes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _install_theme(key: str) -> None:
    folder = THEMES[key][0]
    target = _themes_dir() / folder
    target.mkdir(parents=True, exist_ok=True)
    if folder == "Lust":
        (target / "color.ini").write_text(LUST_COLORS, encoding="utf-8")
        (target / "user.css").write_text(LUST_CSS, encoding="utf-8")
    elif folder == "Luminous":
        for name in ("color.ini", "user.css", "theme.js"):
            response = requests.get(LUMINOUS + name, timeout=30)
            response.raise_for_status()
            (target / name).write_bytes(response.content)
    elif not (target / "color.ini").exists():
        for name in ("color.ini", "user.css"):
            response = requests.get(SLEEK + name, timeout=30)
            response.raise_for_status()
            (target / name).write_bytes(response.content)


def _restart_spotify() -> None:
    subprocess.run(["taskkill", "/IM", "Spotify.exe", "/F"], capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    exe = spotify_exe()
    if exe:
        # As the player, not elevated like Lust: through Explorer
        subprocess.Popen(["explorer.exe", str(exe)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def apply(key: str) -> str:
    """Apply a theme ("original" restores Spotify). Returns the message for the hub."""
    global _busy
    exe = spotify_exe()
    if not exe:
        return ("Microsoft Store'daki Spotify desteklenmiyor: spotify.com'dan indir" if _store_install()
                else "Spotify bulunamadı")
    if key not in THEMES:
        return ""
    with _lock:
        _busy = True
        try:
            _run("config")  # creates Spicetify's config on the first run
            if key == "original":
                _run("restore")
                _save({"theme": "", "marker": _marker(exe)})
                message = "Spotify orijinal görünümüne döndü"
            else:
                _install_theme(key)
                folder, scheme = THEMES[key][:2]
                # Luminous draws with its own script
                _run("config", "current_theme", folder, "color_scheme", scheme,
                     "inject_theme_js", "1" if folder == "Luminous" else "0")
                _run("backup", "apply")
                _save({"theme": key, "marker": _marker(exe)})
                message = "Tema uygulandı"
            _restart_spotify()
            return message
        except Exception as exc:  # noqa: BLE001
            log.warning(f"[Spotify] {key} failed: {exc}")
            return f"Uygulanamadı: {exc}"[:160]
        finally:
            _busy = False


def set_auto(on: bool) -> None:
    _save({"auto": bool(on)})


def reapply_if_updated() -> Optional[str]:
    """Spotify updated since the theme was applied (its patch is gone): apply it again."""
    current = settings()
    exe = spotify_exe()
    if not exe or not current.get("theme") or not current.get("auto", True):
        return None
    if current.get("marker") == _marker(exe):
        return None
    log.info("[Spotify] Spotify changed since the theme was applied; applying it again")
    with _lock:
        try:
            _run("backup", "apply")
            _save({"marker": _marker(exe)})
            return "Spotify güncellenmiş; tema yeniden uygulandı"
        except Exception as exc:  # noqa: BLE001
            log.warning(f"[Spotify] Re-apply failed: {exc}")
            return None
