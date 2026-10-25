#!/usr/bin/env python3
"""
Rebuild the Lust source tree from a Rose release.

    python lust/sync.py <rose-git-ref>

Run from the repository root. Every tracked file outside .github/ and lust/
is replaced by the Rose tree at <rose-git-ref>, then:

1. Rose -> Lust in file contents and paths (real external service URLs kept)
2. Rose's GitHub repo links -> Lust's repo (updates, installer, README)
3. the "Rose" labels inside the prebuilt Pengu Loader core.dll -> "Lust"
4. lust/overlay/ is copied on top (Kai'Sa icons, lobby reveal)
5. EDITS below are applied to Rose files Lust changes

Any step that no longer fits Rose's code fails loudly instead of guessing.
"""

import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "lust" / "overlay"
KEEP = {".github", "lust"}  # Lust's own; never taken from Rose

LUST_REPO = "lustmyself/Lust"

# Real external services: renaming them would only produce dead links.
URL_RE = re.compile(r"https?://[^\s\"'<>)`\]]+")
LOCAL_URL_PREFIXES = ("http://127.0.0.1", "https://plugins/", "http://localhost")
KEEP_WORDS = re.compile(r"\b(proses\w*)\b")  # Indonesian "process", not the brand
REPO_LINK_RE = re.compile(r"Alban1911/Rose(?![-A-Za-z])")
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".ttf", ".otf", ".woff", ".woff2",
    ".ogg", ".mp3", ".wav", ".exe", ".dll", ".pdb", ".zip", ".7z", ".bin", ".wad",
}
DLL_LABELS = [b'legend:"Rose"', b'>Rose</h3>', b'content:"Rose"']


def swap(s):
    return s.replace("ROSE", "LUST").replace("Rose", "Lust").replace("rose", "lust")


def rebrand_text(text):
    pieces, pos = [], 0
    for m in URL_RE.finditer(text):
        pieces.append((False, text[pos:m.start()]))
        url = m.group()
        pieces.append((True, swap(url) if url.startswith(LOCAL_URL_PREFIXES) else url))
        pos = m.end()
    pieces.append((False, text[pos:]))
    out = []
    for is_url, chunk in pieces:
        if is_url:
            out.append(chunk)
            continue
        parts = KEEP_WORDS.split(chunk)
        out.append("".join(p if i % 2 else swap(p) for i, p in enumerate(parts)))
    return REPO_LINK_RE.sub(LUST_REPO, "".join(out))


def read_text(path):
    if path.suffix.lower() in BINARY_EXT:
        return None
    raw = path.read_bytes()
    if b"\0" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def write_text(path, text):
    path.write_bytes(text.encode("utf-8"))


def extract_rose(ref, dest):
    data = subprocess.run(["git", "archive", "--format=tar", ref], cwd=ROOT,
                          check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")


def rebrand_tree(tree):
    for path in tree.rglob("*"):
        if path.is_file() and path.name != "LICENSE":  # MIT: keep the copyright notice
            text = read_text(path)
            if text is not None:
                new = rebrand_text(text)
                if new != text:
                    write_text(path, new)
    # Rename deepest paths first so parents still exist
    for path in sorted(tree.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if re.search("rose", path.name, re.I):
            path.rename(path.with_name(swap(path.name)))


def patch_core_dll(tree):
    dll = tree / "Pengu Loader" / "core.dll"
    if not dll.exists():
        print("[sync] note: no prebuilt core.dll")
        return
    data = dll.read_bytes()
    for label in DLL_LABELS:
        if label not in data:
            print(f"[sync] note: core.dll label {label!r} not found")
        data = data.replace(label, label.replace(b"Rose", b"Lust"))
    # UTF-16 strings: %LOCALAPPDATA%\Rose\config.ini (where core.dll finds the
    # plugins folder; with Rose's path it loads no plugins at all), its log
    # folder and the version info
    config_path = "\\Rose\\config.ini".encode("utf-16-le")
    if config_path not in data:
        raise SystemExit("[sync] core.dll no longer reads %LOCALAPPDATA%\\Rose\\config.ini; "
                         "check where it finds the plugins folder before releasing")
    for old in ("Rose", "ROSE"):
        data = data.replace(old.encode("utf-16-le"), swap(old).encode("utf-16-le"))
    data = patch_welcome_popup(data)
    data = patch_loading_screen(data)
    # Same-length ASCII fixes: the command palette's "Lust" entry opened Rose's GitHub
    # (Lust's repo URL is one byte longer, so its owner; a URL's trailing spaces are
    # ignored), and the debug path named ROSE-Pengu
    for old, new in ((b'window.open("https://github.com/Alban1911/Rose","_blank")',
                      b'window.open("https://github.com/lustmyself    ","_blank")'),
                     (b"\\ROSE-Pengu\\", b"\\LUST-Pengu\\")):
        if len(old) != len(new):
            raise SystemExit("[sync] a core.dll patch changes the file's length")
        data = data.replace(old, new)
    dll.write_bytes(data)


# The client's loading screen: a round image (League's rose profile icon) over "LUST"
LOADING_CSS = (
    b'div[id^=index_loading_div]:before{content:"";'
    b'background-image:url(/lol-game-data/assets/v1/profile-icons/7.jpg);'
    b'background-repeat:no-repeat;background-size:cover;width:144px;height:144px;border-radius:50%}'
    b'div[id^=index_loading_div]:after{margin-top:32px;content:"Lust";color:#e2e1e1;'
    b'font-family:Inter,sans-serif;font-size:1rem;text-transform:uppercase}'
)
# Nothing on it: no image and no text while the client loads (at login and after a match)
EMPTY_LOADING_CSS = b'div[id^=index_loading_div]:before,div[id^=index_loading_div]:after{display:none}'


def patch_loading_screen(data):
    if data.count(LOADING_CSS) != 1:
        raise SystemExit("[sync] the client loading screen CSS changed in core.dll")
    padding = len(LOADING_CSS) - len(EMPTY_LOADING_CSS)
    if padding < 0:
        raise SystemExit("[sync] the empty loading screen CSS is longer than the original")
    return data.replace(LOADING_CSS, EMPTY_LOADING_CSS + b" " * padding)


POPUP_ICON = ROOT / "lust" / "assets" / "popup_icon.jpg"
POPUP_IMAGE_RE = re.compile(rb"data:image/jpeg;base64,([A-Za-z0-9+/]+=*)")
POPUP_BADGES = b'class="flex mt-5 space-x-1"'  # Discord / Ko-fi / GitHub badges


def jpeg_base64_of_length(jpeg, length):
    """Base64 of jpeg, padded with a JPEG comment segment to exactly `length` chars."""
    import base64
    target = length // 4 * 3  # bytes that encode to `length` chars without "="
    filler = target - len(jpeg) - 4  # COM marker + 2 length bytes
    if length % 4 or not 0 <= filler <= 65533:
        raise SystemExit(f"[sync] popup icon cannot be fitted into {length} base64 chars")
    comment = b"\xff\xfe" + (filler + 2).to_bytes(2, "big") + b" " * filler
    encoded = base64.b64encode(jpeg[:2] + comment + jpeg[2:])  # right after SOI
    assert len(encoded) == length
    return encoded


def patch_welcome_popup(data):
    """Kai'Sa instead of the rose in Pengu's welcome popup, without the badges.
    Every replacement keeps the byte length, so the DLL layout is untouched."""
    images = list(POPUP_IMAGE_RE.finditer(data))
    if len(images) != 1:
        raise SystemExit(f"[sync] expected one embedded JPEG in core.dll, found {len(images)}")
    start, end = images[0].span(1)
    data = data[:start] + jpeg_base64_of_length(POPUP_ICON.read_bytes(), end - start) + data[end:]

    if data.count(POPUP_BADGES) != 1:
        raise SystemExit("[sync] welcome popup badges not found in core.dll")
    hidden = b'style="display:none"'
    return data.replace(POPUP_BADGES, hidden + b" " * (len(POPUP_BADGES) - len(hidden)))


def copy_overlay(tree):
    for src in OVERLAY.rglob("*"):
        if src.is_file():
            dst = tree / src.relative_to(OVERLAY)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


UI_JS = "Pengu Loader/plugins/LUST-UI/index.js"
NAV_CSS = r"""    /* The nav item shows the word LUST where Rose had its golden rose */
    lol-uikit-navigation-item.menu_item_Golden\\ Lust .menu-item-icon-wrapper {
      width: auto;
      padding: 0 6px;
    }

    lol-uikit-navigation-item.menu_item_Golden\\ Lust .lust-nav-label {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      font-family: "Beaufort for LOL", serif;
      font-weight: 700;
      font-size: 15px;
      letter-spacing: 1.5px;
      color: #c8aa6e;
      transition: color 0.15s, text-shadow 0.15s;
      cursor: pointer;
      user-select: none;
    }

    lol-uikit-navigation-item.menu_item_Golden\\ Lust:hover .lust-nav-label {
      color: #f0e6d2;
      text-shadow: 0 0 6px rgba(200, 170, 110, 0.8);
    }

"""
NAV_ACTIVE_ANCHOR = "    /* Prevent active state styling for Golden Lust */\n"
UPDATE_URL = f'GITHUB_RELEASE_API = "https://api.github.com/repos/{LUST_REPO}/releases/latest"\n'
REQUEST_LINE = "        try:\n            response = requests.get(GITHUB_RELEASE_API"
ANALYTICS_ANCHOR = "    # Initialize analytics thread\n"
SEND_ANCHOR = "    def _send_message(self, message: str) -> None:\n"

# (file, old, new): exact text in the rebranded Rose file -> Lust's version
EDITS = [
    # Client nav bar: the word LUST instead of the golden rose mask
    (UI_JS, NAV_ACTIVE_ANCHOR, NAV_CSS + NAV_ACTIVE_ANCHOR),
    (UI_JS,
     "    // Check if Golden Lust item already exists by checking for the golden_lust.png image\n"
     "    const existingItem = rightNavMenu.querySelector(\n"
     "      'lol-uikit-navigation-item .menu-item-icon[style*=\"golden_lust.png\"]'\n",
     "    // Check if Golden Lust item already exists by checking for its LUST label\n"
     "    const existingItem = rightNavMenu.querySelector(\n"
     "      \"lol-uikit-navigation-item .lust-nav-label\"\n"),
    (UI_JS,
     '    icon.className = "menu-item-icon";\n'
     "    icon.style.webkitMaskImage = `url(http://127.0.0.1:${window.__lustBridge ? window.__lustBridge.port : 50000}/asset/golden_lust.png)`;\n",
     '    icon.className = "lust-nav-label";\n'
     '    icon.textContent = "LUST";\n'),
    # Updates come from Lust's releases
    ("launcher/update/github_client.py", UPDATE_URL,
     "# Lust's own releases. Never point this at Rose's: its update would replace Lust with Rose.\n"
     "# An empty value turns update checks off.\n" + UPDATE_URL),
    ("launcher/update/github_client.py", REQUEST_LINE,
     "        if not GITHUB_RELEASE_API:\n"
     '            log.info("Update check skipped: no release repository configured")\n'
     "            return None\n" + REQUEST_LINE),
    # Lobby reveal: thread, broadcast, packaging
    ("main/core/threads.py",
     "from threads import PhaseThread, WSEventThread, LCUMonitorThread\n",
     "from threads import PhaseThread, WSEventThread, LCUMonitorThread\n"
     "from threads.core.lobby_reveal_thread import LobbyRevealThread\n"),
    ("main/core/threads.py", ANALYTICS_ANCHOR,
     "    # Champ select teammate names + op.gg (LUST-LobbyReveal plugin)\n"
     "    t_reveal = LobbyRevealThread(lcu, state)\n"
     '    thread_manager.register("Lobby Reveal", t_reveal, stop_method=t_reveal.stop)\n'
     "\n" + ANALYTICS_ANCHOR),
    ("pengu/communication/broadcaster.py", SEND_ANCHOR,
     "    def broadcast_lobby_reveal(self, payload: dict) -> None:\n"
     '        """Broadcast revealed champ select teammates to the LobbyReveal plugin"""\n'
     "        if not self.websocket_server.loop or not self.websocket_server.connections:\n"
     "            return\n"
     '        self._send_message(json.dumps({"type": "lobby-reveal", **payload}))\n'
     "\n" + SEND_ANCHOR),
    ("Lust.spec", "    'lcu.features.lcu_swiftplay',\n",
     "    'lcu.features.lcu_swiftplay',\n    'lcu.features.lobby_reveal',\n"),
    ("Lust.spec", "    'threads.core.lcu_monitor_thread',\n",
     "    'threads.core.lcu_monitor_thread',\n    'threads.core.lobby_reveal_thread',\n"),
]

# LTK patcher via LTK Manager (injection/tools/ltk_manager*.py in the overlay)
EDITS += [
    ('main/__init__.py',
     '    """Return (title, status_title, status_body, steps) for an LTK patcher problem."""\n    source = "Get both files from LTK Manager."\n',
     '    """Return (title, status_title, status_body, steps) for an LTK patcher problem."""\n    # Lust installs a downloaded ltk_patcher.zip by itself (injection/tools/ltk_manager_setup.py)\n    install = (\n        "1. Download ltk_patcher.zip: https://www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file\\n"\n        "2. Leave it in your Downloads folder (zipped or extracted).\\n"\n        "3. Restart Lust: it checks the files and installs them by itself."\n    )\n'),
    ('main/__init__.py',
     '            f"The ltk_patcher_dll.dll in Lust\'s tools folder does not support game builds released after {detail}, and League has updated since.",\n            f"1. Update LTK Manager, then get both files from it.\\n"\n            "2. Open Lust\'s tools folder.\\n"\n            "3. Replace both files, then restart Lust.",\n',
     '            f"The ltk_patcher_dll.dll in Lust\'s tools folder does not support game builds released after {detail}, and League has updated since.",\n            "1. Download the newer ltk_patcher.zip that Rose\'s Discord shares (#tutorial) into your Downloads folder.\\n"\n            "2. Restart Lust: it checks the files and installs them by itself.",\n'),
    ('main/__init__.py',
     '            "The ltk_patcher_dll.dll in Lust\'s tools folder is not a recognized LTK patcher DLL.",\n            f"1. {source}\\n"\n            "2. Open Lust\'s tools folder.\\n"\n            "3. Replace both files, then restart Lust.",\n',
     '            "The ltk_patcher_dll.dll in Lust\'s tools folder is not a recognized LTK patcher DLL.",\n            install,\n'),
    ('main/__init__.py',
     '        "One Lust component is missing",\n        f"Lust needs {detail or \'the LTK patcher\'} in its tools folder before it can start.",\n        f"1. {source}\\n"\n        "2. Open Lust\'s tools folder.\\n"\n        "3. Place both files there, then restart Lust.",\n',
     '        "One Lust component is missing",\n        f"Lust needs {detail or \'the LTK patcher\'} (ltk_patcher.zip) before it can start.",\n        install,\n'),
    ('main/__init__.py',
     '    )\n    footer = "Please do not request or share this file in Discord. Lust cannot distribute it because of licensing restrictions."\n',
     '    )\n    footer = (\'<a href="https://www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file">ltk_patcher.zip</a> \'\n              "(Rose\'s Discord, #tutorial). Lust only installs files signed by League Toolkit.")\n'),
    ('main/__init__.py',
     '        f"{status_title}\\n\\n{status_body}\\n\\nHow to fix it:\\n{steps}\\n\\n"\n        "Please do not request or share this file in Discord.\\n"\n        "Discord: https://discord.gg/roseskins\\n\\n"\n',
     '        f"{status_title}\\n\\n{status_body}\\n\\nHow to fix it:\\n{steps}\\n\\n"\n        "Lust only installs patcher files signed by League Toolkit.\\n\\n"\n'),
    ('main/__init__.py',
     '    _sync_cslol_stub(tools_dir)\n    status = check_ltk_patcher(tools_dir)\n',
     '    _sync_cslol_stub(tools_dir)\n    try:\n        # Takes a downloaded ltk_patcher.zip, or opens its download page and waits for it\n        from injection.tools.ltk_manager_setup import startup_check\n        startup_check(tools_dir)\n    except Exception as e:\n        log.warning(f"[LTK] Could not set up the patcher: {e}")\n    status = check_ltk_patcher(tools_dir)\n'),
    ('README.md',
     '- **League of Legends** installed\n- **LTK patcher** - You must provide it yourself (see below)\n',
     '- **League of Legends** installed\n- **LTK patcher** - `ltk_patcher.zip`, which Lust asks you to download (see below)\n'),
    ('README.md',
     '\nDue to DMCA restrictions, Lust cannot distribute the LTK patcher. Get its two files, `ltk_patcher_host.exe` and `ltk_patcher_dll.dll`, from an LTK Manager install.\n',
     '\nLust injects with the LTK patcher (`ltk_patcher_host.exe` and `ltk_patcher_dll.dll`). LTK Manager\'s own builds since 1.30 refuse every program but LTK Manager, so Lust uses the [ltk_patcher.zip](https://www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file) that Rose\'s Discord shares (#tutorial). When the patcher is missing, Lust opens that page: download the zip and Lust finds it in your Downloads folder, checks that both files are signed by League Toolkit, and installs them.\n'),
    ('README.md',
     '\nOn first launch, Lust asks for these files and opens its tools folder, where they go. The patcher stops working with game builds released after its end-of-life date: Lust then tells you to update LTK Manager and replace both files.\n',
     '\nThe patcher stops working with game builds released after its end-of-life date: Lust then asks for the newer ltk_patcher.zip the same way.\n'),
]

# One click on the LUST label toggled the panel twice (nav item + section listeners),
# so closing reopened it at once. The nav item's capture listener toggles alone.
EDITS += [
    (UI_JS,
     "            e.stopPropagation();\n"
     "            e.preventDefault();\n"
     "\n"
     "            // Dispatch event to open settings panel\n"
     '            const event = new CustomEvent("lust-open-settings", {\n'
     "              detail: { navItem: navItem },\n"
     "              bubbles: true,\n"
     "              cancelable: true,\n"
     "            });\n"
     "            window.dispatchEvent(event);\n"
     "            log.info(\n"
     '              "Dispatched lust-open-settings event from Golden Lust section"\n'
     "            );\n",
     "            e.stopPropagation();\n"
     "            e.preventDefault();\n"
     "            // The nav item's capture listener already toggled the settings panel\n"),
]

# LUST-Theme's asset library lists, opens, deletes and receives its files through Lust
EDITS += [
    ('pengu/communication/message_handler.py',
     '        # Route to appropriate handler\n'
     '        if payload_type in {"chroma-log", "plugin-log"}:\n',
     '        # Route to appropriate handler\n'
     '        if payload_type == "lust-assets":\n'
     '            from pengu.communication.lust_assets import handle as _handle_lust_assets\n'
     '            self._send_response(json.dumps(_handle_lust_assets(payload)))\n'
     '            return\n'
     '        if payload_type in {"chroma-log", "plugin-log"}:\n'),
    ('Lust.spec', "    'launcher.core',\n", "    'launcher.core',\n    'pengu.communication.lust_assets',\n"),
]

# Once Pengu is active, an earlier "could not be activated" report no longer applies:
# Troubleshooting kept showing it after Lust had recovered by itself.
PENGU_PY = 'utils/integration/pengu_loader.py'
EDITS += [
    (PENGU_PY, "def activate() -> bool:\n",
     "def _clear_stale_activation_issue() -> None:\n"
     '    """Pengu is active now: drop an earlier "could not be activated" report."""\n'
     "    try:\n"
     "        from utils.core.issue_reporter import remove_issues\n"
     '        remove_issues(lambda line, fix: "Pengu Loader could not be activated" in line)\n'
     "    except Exception as e:\n"
     "        log.debug('Could not clear the old Pengu activation report: %s', e)\n"
     "\n\n"
     "def activate() -> bool:\n"),
    (PENGU_PY,
     "            log.error('Pengu activation command succeeded, but status is %s.', status.value)\n"
     "            return False\n"
     "        return True\n",
     "            log.error('Pengu activation command succeeded, but status is %s.', status.value)\n"
     "            return False\n"
     "        _clear_stale_activation_issue()\n"
     "        return True\n"),
    (PENGU_PY,
     "                log.info('Lust Loader enabled; client restart deferred until the client is ready.')\n"
     "        return True\n",
     "                log.info('Lust Loader enabled; client restart deferred until the client is ready.')\n"
     "        _clear_stale_activation_issue()\n"
     "        return True\n"),
]

# Lust Offline's status lives in Lust's tray menu (its own tray icon is hidden)
EDITS += [
    ('utils/integration/tray_manager.py',
     '            pystray.MenuItem("Open Mods Folder", self._on_open_mods),\n',
     '            pystray.MenuItem("Open Mods Folder", self._on_open_mods),\n'
     '            pystray.MenuItem("Status", _lust_offline_status_menu()),\n'),
    ('utils/integration/tray_manager.py',
     "    def _create_menu(self) -> pystray.Menu:\n",
     "    def _create_menu(self) -> pystray.Menu:\n"
     "        from launcher.lust_offline import tray_status_menu as _lust_offline_status_menu\n"),
]

# Lust.exe carries version info: antivirus heuristics distrust exes without any
LUST_VERSION_INFO = '''# Lust: version info for Lust.exe (antivirus heuristics distrust exes without any)
import re as _re
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
)
_lust_version = _re.search(r'APP_VERSION = "([^"]+)"', Path('config.py').read_text(encoding='utf-8')).group(1)
_lust_numbers = tuple((list(map(int, _re.findall(r'\\d+', _lust_version))) + [0, 0, 0, 0])[:4])
lust_version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_lust_numbers, prodvers=_lust_numbers),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', 'Lust Team'),
            StringStruct('FileDescription', 'Lust'),
            StringStruct('FileVersion', _lust_version),
            StringStruct('InternalName', 'Lust'),
            StringStruct('LegalCopyright', 'Lust Team, MIT License'),
            StringStruct('OriginalFilename', 'Lust.exe'),
            StringStruct('ProductName', 'Lust'),
            StringStruct('ProductVersion', _lust_version),
        ])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)

'''
EDITS += [
    ('Lust.spec', "exe = EXE(\n", LUST_VERSION_INFO + "exe = EXE(\n"),
    ('Lust.spec', "    icon='assets/icon.ico',\n    uac_admin=True,",
     "    icon='assets/icon.ico',\n    version=lust_version_info,\n    uac_admin=True,"),
]

# Lust Offline: League starts through the chat proxy built from lust/offline
EDITS += [
    ('main/__init__.py',
     '    # Initialize core components\n',
     '    # Start with Windows is on by default, set once on the first run\n'
     '    from launcher.autostart_default import apply_autostart_default\n'
     '    apply_autostart_default()\n'
     '\n'
     '    # Open League through Lust Offline so the player can appear offline\n'
     '    from launcher.lust_offline import start_league_through_lust_offline\n'
     '    start_league_through_lust_offline()\n'
     '\n'
     '    # Initialize core components\n'),
    ('Lust.spec', "    'launcher.core',\n",
     "    'launcher.core',\n    'launcher.lust_offline',\n    'launcher.autostart_default',\n"),
    ('Lust.spec', "    'injection/tools/mod-tools.exe',\n",
     "    'injection/tools/mod-tools.exe',\n    'injection/tools/LustOffline.exe',  # built by lust/offline/build_offline.py\n"),
]


# Desktop hub (launcher/lust_hub.py): startup progress, updates and quick actions in one window
EDITS += [
    ('launcher/core/launcher.py',
     '    updater_log.info("Launcher sequence starting.")\n    dialog = UpdateDialog()\n',
     '    updater_log.info("Launcher sequence starting.")\n'
     '    from launcher.lust_hub import make_launcher_dialog\n'
     '    dialog = make_launcher_dialog()\n'),
    ('launcher/core/launcher.py',
     '    result = user32.MessageBoxW(\n'
     '        dialog.hwnd or None,\n'
     '        message,\n'
     '        "Lust update available",\n'
     '        MB_YESNO | MB_ICONINFORMATION | MB_DEFBUTTON2 | MB_TOPMOST,\n'
     '    )\n'
     '    accepted = result == IDYES\n',
     '    # The desktop hub asks in its window; None means no hub page, so ask with a message box\n'
     '    hub_answer = dialog.confirm_update(remote_version, local_version) if hasattr(dialog, "confirm_update") else None\n'
     '    if hub_answer is not None:\n'
     '        accepted = hub_answer\n'
     '    else:\n'
     '        result = user32.MessageBoxW(\n'
     '            dialog.hwnd or None,\n'
     '            message,\n'
     '            "Lust update available",\n'
     '            MB_YESNO | MB_ICONINFORMATION | MB_DEFBUTTON2 | MB_TOPMOST,\n'
     '        )\n'
     '        accepted = result == IDYES\n'),
    ('main/__init__.py',
     '        tray_manager.restart_callback = updated_tray_restart_callback\n',
     '        tray_manager.restart_callback = updated_tray_restart_callback\n'
     '\n'
     '        # The desktop hub takes over from the launcher and uses the tray\'s quit and restart\n'
     '        from launcher.lust_hub import attach as attach_hub\n'
     '        attach_hub(tray_manager)\n'),
    ('utils/integration/tray_manager.py',
     '            pystray.MenuItem("Open Mods Folder", self._on_open_mods),\n',
     '            pystray.MenuItem("Lust Hub", self._on_open_hub, default=True),\n'
     '            pystray.MenuItem("Open Mods Folder", self._on_open_mods),\n'),
    ('utils/integration/tray_manager.py',
     '    def _on_open_mods(self, icon, item):\n',
     '    def _on_open_hub(self, icon, item):\n'
     '        """Open Lust\'s desktop hub (a left click on the tray icon does this too)."""\n'
     '        try:\n'
     '            from launcher.lust_hub import open_window\n'
     '\n'
     '            open_window()\n'
     '        except Exception as e:\n'
     '            log.error(f"Failed to open the Lust hub: {e}")\n'
     '\n'
     '    def _on_open_mods(self, icon, item):\n'),
    ('utils/integration/tray_manager.py',
     '        # Wait for tray icon to be ready (up to 5 seconds)\n',
     '        try:\n'
     '            from launcher.lust_hub import set_ready as _hub_set_ready\n'
     '\n'
     '            _hub_set_ready(status == "unlocked")\n'
     '        except Exception as e:\n'
     '            log.debug(f"Hub status update failed: {e}")\n'
     '\n'
     '        # Wait for tray icon to be ready (up to 5 seconds)\n'),
    ('Lust.spec', "    'launcher.core',\n",
     "    'launcher.core',\n    'launcher.lust_hub',\n    'launcher.lust_hub_window',\n    'launcher.lust_spotify',\n    'tkinter',\n"),
]



# LP cutoffs for the client hub's welcome card: the page can't read replays.lol itself (no CORS)
EDITS += [
    ('pengu/communication/message_handler.py',
     '        if payload_type == "lust-assets":\n',
     '        if payload_type == "lust-cutoffs":\n'
     '            def _reply_cutoffs(request=payload):\n'
     '                from launcher.lust_hero import cutoffs_for\n'
     '                self._send_response(json.dumps({"type": "lust-cutoffs", "requestId": request.get("requestId"),\n'
     '                                                "cutoff": cutoffs_for(str(request.get("region") or ""))}))\n'
     '            threading.Thread(target=_reply_cutoffs, daemon=True, name="LustCutoffs").start()\n'
     '            return\n'
     '        if payload_type == "lust-assets":\n'),
]


# Updates: a Lust process left running from the install folder (an old hub window) locked
# Lust.exe and its DLLs, robocopy gave up on them and the update hung on "restarting"
EDITS += [
    ('launcher/update/update_installer.py',
     'echo [%date% %time%] Mirroring files >> "%LOG%"\n',
     'echo [%date% %time%] Closing Lust windows left open >> "%LOG%"\n'
     'powershell -NoProfile -NonInteractive -Command "Get-Process -Name Lust -ErrorAction SilentlyContinue'
     ' | Where-Object { $_.Path -and $_.Path.StartsWith($env:DEST, [StringComparison]::OrdinalIgnoreCase) }'
     ' | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 800" >nul 2>&1\n'
     'echo [%date% %time%] Mirroring files >> "%LOG%"\n'),
]


# Privacy: Rose's analytics sent a heartbeat with this PC's machine and install IDs to Rose's
# server every 15 minutes. Lust sends nothing of the kind.
EDITS += [
    ('config.py',
     "ANALYTICS_SERVER_URL = 'https://analytics.rosekeys.site/'  # Analytics server endpoint\n",
     "ANALYTICS_SERVER_URL = ''  # Lust has no analytics server\n"),
    ('config.py',
     "ANALYTICS_ENABLED = True  # Enable/disable analytics tracking\n",
     "ANALYTICS_ENABLED = False  # Lust sends no usage data anywhere\n"),
    ('analytics/tests/test_analytics.py',
     '    def test_missing_config_option_keeps_analytics_enabled(self, post, get_install_id):\n'
     '        post.return_value = Mock(status_code=204)\n'
     '        with patch("analytics.core.analytics_client.get_config_option", return_value=None):\n'
     '            self.assertTrue(AnalyticsClient().send_ping("1.2.14"))\n',
     '    def test_lust_sends_nothing_by_default(self, post, get_install_id):\n'
     '        post.return_value = Mock(status_code=204)\n'
     '        with patch("analytics.core.analytics_client.get_config_option", return_value=None):\n'
     '            self.assertFalse(AnalyticsClient().send_ping("1.2.14"))\n'
     '        post.assert_not_called()\n'),
]


# README: Lust's own features, privacy and links (no Rose analytics, donation or Discord)
EDITS += [
    ('README.md',
     '[issue forms](https://github.com/lustmyself/Lust/issues/new/choose), and ask\nfor installation help on [Discord](https://discord.com/invite/roseskins).\n',
     '[issue forms](https://github.com/lustmyself/Lust/issues/new/choose); installation\nquestions are welcome there too.\n'),
    ('README.md',
     '- **Party Mode**: Enables skin sharing between friends in the same lobby via a Cloudflare WebSocket relay\n',
     '- **Party Mode**: Skin sharing between friends through a WebSocket relay (off in Lust: no relay server)\n'),
    ('README.md',
     '# 🌹 Lust - Effortless Skin Changer for LoL\n',
     '# 💜 Lust - Effortless Skin Changer for LoL\n'),
    ('README.md',
     '[![Installer](https://img.shields.io/badge/Installer-Windows-32A832)](https://github.com/lustmyself/Lust/releases/latest) [![Ko-Fi](https://img.shields.io/badge/KoFi-Donate-C03030?logo=ko-fi&logoColor=white)](https://ko-fi.com/roseapp) [![Discord](https://img.shields.io/discord/1490473857075642621?color=32A832&logo=discord&logoColor=white&label=Discord)](https://discord.com/invite/roseskins) [![License](https://img.shields.io/badge/License-MIT-C03030)](LICENSE) [![Downloads](https://img.shields.io/github/downloads/lustmyself/Lust/total?color=32A832&label=Downloads&cacheSeconds=86400)](https://github.com/lustmyself/Lust/releases/latest)\n',
     '[![Installer](https://img.shields.io/badge/Installer-Windows-32A832)](https://github.com/lustmyself/Lust/releases/latest) [![License](https://img.shields.io/badge/License-MIT-C03030)](LICENSE) [![Downloads](https://img.shields.io/github/downloads/lustmyself/Lust/total?color=32A832&label=Downloads&cacheSeconds=86400)](https://github.com/lustmyself/Lust/releases/latest)\n'),
    ('README.md',
     '### Analytics and privacy\n\nLust sends a pseudonymous, randomly generated installation ID and the app version\nto `https://analytics.rosekeys.site/` when analytics are enabled. The ID is not derived\nfrom the Windows Machine GUID. Analytics can be disabled with\n`ANALYTICS_ENABLED = False` in `config.py`.\n\nThe analytics API and dashboard are maintained separately from this public\nclient repository. Only aggregate usage metrics are exposed through the\ndashboard; raw activity and server credentials remain private.\n\n',
     '### Privacy\n\nLust sends no usage data anywhere: the analytics Rose has are switched off.\nIt talks to GitHub (updates, skins), the League client on your PC, and replays.lol for\nthe LP cutoffs on the welcome card.\n\n'),
    ('README.md',
     '### Cloudflare Workers\n\n- **lust-party-relay**: Durable Object-backed WebSocket relay that manages party rooms (max 10 members per room) for real-time skin selection broadcasting between friends. It refuses Lust versions older than 1.4.4\n\n',
     '<!-- Rose\'s party relay server is not part of Lust -->\n\n'),
    ('README.md',
     "- **Party Mode**: Friends running Lust 1.4.4 or newer see each other's skins and custom mods in game\n",
     "- **Desktop hub**: Startup progress, updates, your Riot ID, rank, last match and your server's\n  Grandmaster and Challenger LP cutoffs, quick actions and Lust Offline's status\n- **Lust Offline**: Appear offline or on mobile to your friends while you play\n- **Custom skins tab**: Drop your own `.fantome`, `.zip` or `.modpkg` skins in and switch them\n  on per champion; they play on the champion's default skin\n- **Spotify themes**: 22 Spicetify themes for the Spotify desktop app, re-applied after\n  Spotify updates\n- **Silent updates**: New versions download in the background and install while League is closed\n- **Lobby Reveal**: Your teammates' names and op.gg links in champion select\n- **Party Mode**: Needs a party relay server; Lust doesn't run one, so it is off\n"),
    ('README.md',
     '## Support\n\nIf you enjoy Lust and want to support its development:\n\n[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/roseapp)\n\nYour support helps keep the project alive and motivates continued development!\n\n',
     '## Support\n\nFound a bug or have an idea? Open an [issue](https://github.com/lustmyself/Lust/issues/new/choose).\n\n'),
]


# Rose's Discord and Ko-fi links led Lust players to Rose's community and donations
EDITS += [
    ('Pengu Loader/plugins/LUST-SettingsPanel/index.js',
     '    const discordLink = document.createElement("a");\n    discordLink.className = "settings-link";\n    discordLink.href = DISCORD_INVITE_URL;\n    discordLink.target = "_blank";\n    discordLink.textContent = "Discord";\n    linksSection.appendChild(discordLink);\n\n    const kofiLink = document.createElement("a");\n    kofiLink.className = "settings-link";\n    kofiLink.href = KOFI_URL;\n    kofiLink.target = "_blank";\n    kofiLink.textContent = "Ko-Fi";\n    linksSection.appendChild(kofiLink);\n\n',
     '    // Lust: the GitHub link only\n'),
    ('CONTRIBUTING.md',
     ', submit pull requests, or join our [Discord](https://discord.com/invite/roseskins) for discussions and installation help.',
     ', or submit pull requests.'),
]


# Party Mode's plugin is gone (see REMOVE): only the skin monitor's ports are checked
EDITS += [
    ('pengu/tests/test_bridge_port_range.py',
     "        for plugin in ('LUST-SkinMonitor', 'LUST-PartyMode'):\n",
     "        for plugin in ('LUST-SkinMonitor',):\n"),
]


# Retired Lust plugins leave the runtime Pengu Loader the client loads plugins from
EDITS += [
    ('utils/integration/pengu_loader.py',
     '        log.info("Synced Pengu Loader to runtime directory (preserving user files): %s", runtime_dir)\n',
     '        # Lust plugins a newer Lust no longer ships stay here otherwise (the copy keeps extras)\n        try:\n            from launcher.lust_cleanup import clean_retired_plugins\n            clean_retired_plugins(runtime_dir / "plugins")\n        except Exception as exc:\n            log.debug("Could not remove retired Lust plugins: %s", exc)\n        log.info("Synced Pengu Loader to runtime directory (preserving user files): %s", runtime_dir)\n'),
]


# The hub's Settings page: the skins master switch
EDITS += [
    ('threads/handlers/injection_trigger.py',
     '            log.error(f"   Loadout Timer: #{ticker_id}")\n            log.error("=" * LOG_SEPARATOR_WIDTH)\n            return\n        \n        # Check if custom mod is selected for this skin (before logging)\n',
     '            log.error(f"   Loadout Timer: #{ticker_id}")\n            log.error("=" * LOG_SEPARATOR_WIDTH)\n            return\n        \n        # Lust: skins switched off in the hub\'s settings: the game starts without mods\n        try:\n            from launcher.lust_settings import enabled as _lust_setting\n            if not _lust_setting("skins"):\n                log.info("[Settings] Skins are off in the hub: nothing is injected")\n                return\n        except Exception as e:\n            log.debug(f"[Settings] Could not read the skins switch: {e}")\n        # Check if custom mod is selected for this skin (before logging)\n'),
    ('Lust.spec', "    'launcher.lust_hub',\n", "    'launcher.lust_hub',\n    'launcher.lust_settings',\n"),
]


# Spotify's now playing in the hub (launcher/lust_media.py): Windows' media controls and
# Spotify's own audio session (mute, sound level for the visualizer)
EDITS += [
    ('requirements.txt', 'Pillow==10.4.0\n', 'Pillow==10.4.0\nwinrt-runtime==3.2.1\nwinrt-Windows.Foundation==3.2.1\nwinrt-Windows.Foundation.Collections==3.2.1\nwinrt-Windows.Media.Control==3.2.1\nwinrt-Windows.Storage.Streams==3.2.1\ncomtypes==1.4.17\npycaw==20260927\n'),
    ('Lust.spec', "    'launcher.lust_settings',\n", "    'launcher.lust_settings',\n    'launcher.lust_media',\n    'launcher.lust_perf',\n    'winrt.windows.foundation',\n    'winrt.windows.foundation.collections',\n    'winrt.windows.media.control',\n    'winrt.windows.storage.streams',\n    'comtypes',\n    'pycaw.pycaw',\n"),
]


# Updates: Lust Offline keeps running while the Riot Client is open, so its exe was locked and
# the copy failed; that file is left alone while it runs. A failed copy no longer waits on a
# "press any key" window with Lust closed: it starts Lust again.
EDITS += [
    ('launcher/update/update_installer.py',
     'robocopy "%SOURCE%" "%DEST%" /MIR /R:5 /W:2 /NFL /NDL /NJH /NJS /XD __pycache__ "%SOURCE%\\Pengu Loader\\plugins" /XF config.ini ltk_patcher_host.exe ltk_patcher_dll.dll hashes.game.txt >> "%LOG%" 2>&1\n',
     'set "KEEP_OFFLINE="\npowershell -NoProfile -NonInteractive -Command "if (Get-Process -Name LustOffline -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($env:DEST, [StringComparison]::OrdinalIgnoreCase) }) { exit 1 }" >nul 2>&1\nif errorlevel 1 (\n    set "KEEP_OFFLINE=LustOffline.exe"\n    echo [%date% %time%] Lust Offline is running ^(League chat goes through it^): its file stays as it is >> "%LOG%"\n)\nrobocopy "%SOURCE%" "%DEST%" /MIR /R:5 /W:2 /NFL /NDL /NJH /NJS /XD __pycache__ "%SOURCE%\\Pengu Loader\\plugins" /XF config.ini ltk_patcher_host.exe ltk_patcher_dll.dll hashes.game.txt %KEEP_OFFLINE% >> "%LOG%" 2>&1\n'),
    ('launcher/update/update_installer.py',
     'echo [%date% %time%] Update failed >> "%LOG%"\necho Update failed, details in "%LOG%"\necho Press any key to close.\npause >nul\nexit 1\n',
     'echo [%date% %time%] Update failed; starting Lust again >> "%LOG%"\nstart "" /D "%DEST%" "%DEST%\\%EXE%"\nexit 1\n'),
]


# Restarts keep Pengu on (utils/integration/pengu_loader.py, main/__init__.py)
EDITS += [
    ('utils/integration/pengu_loader.py',
     'def restore_after_lust() -> bool:\n    with _operation_lock:\n        session = _read_session()\n',
     '# Lust: a restart (the hub\'s Restart or an update) keeps Pengu on. Switching it off made the\n# next Lust unable to switch it back on while League was open ("close the running League\n# Client"), and the LUST tab was gone until League restarted. The next Lust adopts it.\nRESTART_KEEP_S = 120\n\n\ndef _keep_flag() -> Path:\n    return get_user_data_dir() / "pengu_keep_for_restart"\n\n\ndef keep_on_for_restart() -> None:\n    """Lust is about to restart: leave Pengu on when this process exits."""\n    import time\n    try:\n        _keep_flag().write_text(str(time.time()), encoding="utf-8")\n    except OSError as exc:\n        log.debug("Could not mark the restart for Pengu: %s", exc)\n\n\ndef _restarting() -> bool:\n    import time\n    flag = _keep_flag()\n    try:\n        fresh = time.time() - flag.stat().st_mtime < RESTART_KEEP_S\n        flag.unlink()\n        return fresh\n    except OSError:\n        return False\n\n\ndef restore_after_lust() -> bool:\n    if _restarting():\n        log.info("Lust is restarting: Pengu stays on and the next Lust adopts it.")\n        return True\n    with _operation_lock:\n        session = _read_session()\n'),
    ('main/__init__.py',
     '        log.info(f"Restart scheduled via {batch_path}")\n        return True\n',
     '        log.info(f"Restart scheduled via {batch_path}")\n        try:\n            pengu_loader.keep_on_for_restart()\n        except Exception as e:\n            log.debug(f"Could not keep Pengu on for the restart: {e}")\n        return True\n'),
]


# Lust's CLAUDE.md (working notes that survive a fresh machine) is tracked, not ignored
EDITS += [
    ('.gitignore', 'chroma_issue.txt\nCLAUDE.md\n', 'chroma_issue.txt\n# CLAUDE.md: Lust keeps its notes for Claude Code in the repo (lust/overlay/CLAUDE.md)\n'),
]

# Custom skins (pengu/communication/lust_custom_skins.py): the Lust hub's Custom skins tab
# replaces champ select's Custom mods button; a switched-on skin plays on its champion's default skin
EDITS += [
    ('pengu/communication/message_handler.py',
     '        if payload_type == "lust-assets":\n',
     '        if payload_type == "lust-custom-skins":\n'
     '            from pengu.communication.lust_custom_skins import handle as _handle_custom_skins\n'
     '            self._send_response(json.dumps(_handle_custom_skins(payload)))\n'
     '            return\n'
     '        if payload_type == "lust-assets":\n'),
    ('threads/handlers/injection_trigger.py',
     '            # Auto-select previously used custom mods (so users don\'t need to open the Custom Mods UI)\n',
     '            # Lust custom skins: the one switched on for this champion plays on its default skin\n'
     '            if not selected_custom_mod:\n'
     '                try:\n'
     '                    from pengu.communication.lust_custom_skins import custom_mod_for\n'
     '                    lust_custom_skin = custom_mod_for(\n'
     '                        self.state.locked_champ_id or self.state.hovered_champ_id,\n'
     '                        effective_skin_id or ui_skin_id,\n'
     '                    )\n'
     '                    if lust_custom_skin:\n'
     '                        self.state.selected_custom_mod = lust_custom_skin\n'
     '                        selected_custom_mod = lust_custom_skin\n'
     '                except Exception as e:\n'
     '                    log.warning(f"[CustomSkins] Could not pick a custom skin: {e}")\n'
     '\n'
     '            # Auto-select previously used custom mods (so users don\'t need to open the Custom Mods UI)\n'),
    # The button is never put in champ select (a CSS hide lost to the plugin's own !important rule)
    ('Pengu Loader/plugins/LUST-CustomWheel/index.js',
     '    // Append to container (same structure as QUIT button)\n'
     '    targetContainer.appendChild(button);\n',
     '    // Lust: custom skins live in the Lust hub (Custom skins tab), not in champ select\n'
     '    return;\n'
     '    // Append to container (same structure as QUIT button)\n'
     '    targetContainer.appendChild(button);\n'),
    ('Lust.spec', "    'launcher.core',\n", "    'launcher.core',\n    'pengu.communication.lust_custom_skins',\n"),
]


# A mod that crashes the game (made for an older League version) made the client reconnect
# forever: each new game process was hooked and crashed again. Two exits within
# QUICK_EXIT_S of the DLL attaching stop the injection, so the next reconnect starts clean.
OVERLAY_PY = 'injection/overlay/overlay_manager.py'
EDITS += [
    (OVERLAY_PY,
     'KILLED_EXIT_CODE = 0x40010004\n',
     'KILLED_EXIT_CODE = 0x40010004\n'
     '# Lust: the game closing this soon after the DLL attached, twice in a row, is a mod crashing it\n'
     'QUICK_EXIT_S = 20.0\n'
     'QUICK_EXITS_TO_STOP = 2\n'),
    (OVERLAY_PY,
     '                        if parts[2] == "failed":\n'
     '                            session["error"] = message or "injection failed"\n',
     '                        if parts[2] == "failed":\n'
     '                            session["error"] = message or "injection failed"\n'
     '                        elif parts[2] == "injected":\n'
     '                            session["injected_at"] = time.monotonic()\n'
     '                        elif parts[2] == "exited" and session.get("injected_at"):\n'
     '                            quick = time.monotonic() - session.pop("injected_at") < QUICK_EXIT_S\n'
     '                            session["quick_exits"] = session.get("quick_exits", 0) + 1 if quick else 0\n'
     '                            if not quick:\n'
     '                                try:\n'
     '                                    from pengu.communication.lust_custom_skins import game_ran_fine\n'
     '                                    game_ran_fine()\n'
     '                                except Exception as e:\n'
     '                                    log.debug(f"[INJECT] Custom skin check failed: {e}")\n'
     '                            if session["quick_exits"] >= QUICK_EXITS_TO_STOP and not session.get("crash_loop"):\n'
     '                                session["crash_loop"] = True\n'
     '                                session["error"] = "the game closed right after loading the mods, every time"\n'
     '                                log.error("[INJECT] The game closed right after loading the mods "\n'
     '                                          f"{session[\'quick_exits\']} times in a row; stopping the injection")\n'
     '                                try:\n'
     '                                    from pengu.communication.lust_custom_skins import game_keeps_crashing\n'
     '                                    game_keeps_crashing()\n'
     '                                except Exception as e:\n'
     '                                    log.debug(f"[INJECT] Crash report failed: {e}")\n'),
    (OVERLAY_PY,
     '            while proc.poll() is None:\n'
     '                if session["state"] == "failed":\n'
     '                    break\n',
     '            while proc.poll() is None:\n'
     '                if session["state"] == "failed" or session.get("crash_loop"):\n'
     '                    break\n'),
    (OVERLAY_PY,
     '            if session["error"]:\n'
     '                log.error(f"[INJECT] LTK patcher failed: {session[\'error\']}")\n',
     '            if session.get("crash_loop"):\n'
     '                # Reported by game_keeps_crashing, in the player\'s words\n'
     '                self._log_runoverlay_tail(runoverlay_log)\n'
     '                return 1\n'
     '            if session["error"]:\n'
     '                log.error(f"[INJECT] LTK patcher failed: {session[\'error\']}")\n'),
]


# LTK patcher builds from October 2026 verify their host and refuse any program but LTK Manager
# ("host verification failed, refusing overlay"): the game then starts without mods. The build
# is remembered so Lust never takes it again (injection/tools/ltk_manager.py), and the player is
# told in Turkish what to do instead of a generic patcher failure.
EDITS += [
    (OVERLAY_PY,
     '                    elif parts[0] == "dll" and " ERROR " in line:\n'
     '                        # e.g. "overlay verification failed, disabling overlay"\n',
     '                    elif parts[0] == "dll" and "host verification failed" in line:\n'
     '                        # Lust: a patcher build that runs only inside LTK Manager\n'
     '                        session["error"] = line\n'
     '                        session["host_locked"] = True\n'
     '                        log.error("[INJECT] LTK patcher DLL refused Lust as its host - overlay not applied")\n'
     '                        try:\n'
     '                            from ..tools.ltk_manager import patcher_refused_host\n'
     '                            patcher_refused_host(host_exe.parent, line)\n'
     '                        except Exception as e:\n'
     '                            log.debug(f"[INJECT] Could not record the refused patcher: {e}")\n'
     '                    elif parts[0] == "dll" and " ERROR " in line:\n'
     '                        # e.g. "overlay verification failed, disabling overlay"\n'),
    (OVERLAY_PY,
     '            if session.get("crash_loop"):\n'
     '                # Reported by game_keeps_crashing, in the player\'s words\n'
     '                self._log_runoverlay_tail(runoverlay_log)\n'
     '                return 1\n',
     '            if session.get("crash_loop"):\n'
     '                # Reported by game_keeps_crashing, in the player\'s words\n'
     '                self._log_runoverlay_tail(runoverlay_log)\n'
     '                return 1\n'
     '            if session.get("host_locked"):\n'
     '                # Reported by patcher_refused_host, in the player\'s words\n'
     '                self._log_runoverlay_tail(runoverlay_log)\n'
     '                return 1\n'),
    # Troubleshooting names the lock and what to do, instead of "retry the next game"
    (OVERLAY_PY,
     '    if "SetWindowsHookEx" in reason:\n'
     '        return "hook"\n',
     '    if "host verification" in reason:\n'
     '        return "locked"  # Lust: a patcher build that runs only inside LTK Manager\n'
     '    if "SetWindowsHookEx" in reason:\n'
     '        return "hook"\n'),
    ('Pengu Loader/plugins/LUST-SettingsPanel/index.js',
     "            crashed: () => t('Fix: the LTK patcher crashed. Retry the next game. If it crashes every game, update your LTK patcher files.'),\n",
     "            crashed: () => t('Fix: the LTK patcher crashed. Retry the next game. If it crashes every game, update your LTK patcher files.'),\n"
     r'            locked: () => t("Fix: download ltk_patcher.zip (www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file, shared in the Rose Discord #tutorial) into your Downloads folder and restart Lust: it checks the League Toolkit signature and installs it. Or put both files in %LOCALAPPDATA%\\Lust\\ltk-patcher."),'
     '\n'),
    ('Pengu Loader/plugins/LUST-SettingsPanel/index.js',
     "              detail ? t('What happened: {detail}', { detail }) : t('What happened: the LTK patcher reported an error.'),\n",
     "              e?.cause === 'locked' ? t('What happened: this LTK patcher only runs inside LTK Manager, so it refused Lust and the game started without skins.')\n"
     "                : detail ? t('What happened: {detail}', { detail }) : t('What happened: the LTK patcher reported an error.'),\n"),
]

# Lust's own texts in the client plugins' languages (LUST-I18n): Turkish where Lust has it,
# English in the others, so every language keeps the same keys
LOCALE_STRINGS = {
    "What happened: this LTK patcher only runs inside LTK Manager, so it refused Lust and the game started without skins.":
        {"tr": "Ne oldu: bu LTK patcher yalnızca LTK Manager içinde çalışıyor; Lust'ı reddetti ve oyun skinsiz açıldı."},
    "Fix: download ltk_patcher.zip (www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file, shared in the Rose "
    "Discord #tutorial) into your Downloads folder and restart Lust: it checks the League Toolkit signature and "
    "installs it. Or put both files in %LOCALAPPDATA%\\Lust\\ltk-patcher.":
        {"tr": "Çözüm: ltk_patcher.zip'i (www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file, Rose "
               "Discord'u #tutorial) İndirilenler klasörüne indir ve Lust'ı yeniden başlat: Lust League Toolkit "
               "imzasını kontrol edip kendisi kurar. Ya da iki dosyayı %LOCALAPPDATA%\\Lust\\ltk-patcher klasörüne koy."},
}


# Desktop hub in WebView2 (launcher/lust_hub_shell.py): Lust.exe --lust-hub-window <url> shows it
EDITS += [
    ('main/__init__.py',
     '    """Program entry point that prepares and launches Lust."""\n    args = setup_arguments()\n',
     '    """Program entry point that prepares and launches Lust."""\n'
     '    # The desktop hub window runs as a second Lust process (pywebview needs a main thread)\n'
     '    from launcher.lust_hub_shell import main_if_window\n'
     '    if main_if_window():\n'
     '        return\n'
     '    args = setup_arguments()\n'),
    ('requirements.txt', 'requests==2.31.0\n', 'requests==2.31.0\npywebview==6.2.1\n'),
    ('Lust.spec', "    'launcher.core',\n",
     "    'launcher.core',\n    'launcher.lust_hub_server',\n    'launcher.lust_hub_shell',\n"
     "    'launcher.lust_hub_web',\n    'launcher.lust_rose',\n    'webview',\n    'webview.platforms.edgechromium',\n"
     "    'webview.platforms.winforms',\n    'clr',\n    'clr_loader',\n"),
    ('Lust.spec', "# Include the source-built Pengu Loader runtime used for Lust activation/deactivation\n",
     "# pywebview's WebView2 DLLs for the desktop hub window\n"
     "try:\n"
     "    webview_datas = collect_data_files('webview')\n"
     "    datas += webview_datas\n"
     "    print(f\"[OK] Collected {len(webview_datas)} pywebview data files\")\n"
     "except Exception as e:\n"
     "    print(f\"[WARNING] Could not collect pywebview data files: {e}\")\n\n"
     "# Include the source-built Pengu Loader runtime used for Lust activation/deactivation\n"),
]


# Lust's installer had Rose's AppId: Inno Setup took Lust for a Rose upgrade on a PC with
# Rose, reusing Rose's folder and uninstall entry. Lust has its own id, and never takes over
# a previous folder by itself.
EDITS += [
    ('installer.iss', 'AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}\n',
     'AppId={{18B5D16F-154B-43C8-A6DF-21CB903DE869}}\nUsePreviousAppDir=no\n'),
]


# The installer wrote a second Apps entry (Uninstall\Lust) beside Inno's own AppId entry and nothing
# removed it, so a dead "Lust" stayed in Windows' Apps list after an uninstall. As Rose's main
# (d0ae51d2, 459f7e4b): no duplicate, the old one goes on install and uninstall, and Lust writes its
# running version to Inno's entry.
EDITS += [
    ('installer.iss',
     "procedure _DeleteLocalAppDataLust();\n",
     "const\n"
     "  LegacyUninstallKey = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}';\n"
     "\n"
     "procedure _CleanupLegacyUninstallEntry();\n"
     "var\n"
     "  InstallLocation: string;\n"
     "  DisplayName: string;\n"
     "  Publisher: string;\n"
     "begin\n"
     "  { Inno owns the AppId-based Apps entry. Remove only our duplicate from older\n"
     "    installers, and only when it belongs to this installation. }\n"
     "  if RegQueryStringValue(HKLM, LegacyUninstallKey, 'InstallLocation', InstallLocation) and\n"
     "     RegQueryStringValue(HKLM, LegacyUninstallKey, 'DisplayName', DisplayName) and\n"
     "     RegQueryStringValue(HKLM, LegacyUninstallKey, 'Publisher', Publisher) and\n"
     "     (CompareText(AddBackslash(InstallLocation), AddBackslash(ExpandConstant('{app}'))) = 0) and\n"
     "     (DisplayName = '{#MyAppName}') and (Publisher = '{#MyAppPublisher}') then\n"
     "  begin\n"
     "    RegDeleteKeyIncludingSubkeys(HKLM, LegacyUninstallKey);\n"
     "  end;\n"
     "end;\n"
     "\n"
     "procedure _DeleteLocalAppDataLust();\n"),
    ('installer.iss',
     "  if CurUninstallStep = usUninstall then\n"
     "  begin\n"
     "    _CleanupStartupRegistry();\n",
     "  if CurUninstallStep = usUninstall then\n"
     "  begin\n"
     "    _CleanupStartupRegistry();\n"
     "    _CleanupLegacyUninstallEntry();\n"),
    ('installer.iss',
     "    // Create registry entries for Windows Apps list\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'DisplayName', '{#MyAppName}');\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'DisplayVersion', '{#MyAppVersion}');\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'Publisher', '{#MyAppPublisher}');\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'URLInfoAbout', '{#MyAppURL}');\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'InstallLocation', ExpandConstant('{app}'));\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'UninstallString', ExpandConstant('{uninstallexe}'));\n"
     "    RegWriteDWordValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'NoModify', 1);\n"
     "    RegWriteDWordValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'NoRepair', 1);\n"
     "    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{#MyAppName}', 'DisplayIcon', ExpandConstant('{app}\\{#MyAppExeName}'));\n",
     "    { Inno writes the Apps entry itself: drop the duplicate older installers wrote }\n"
     "    _CleanupLegacyUninstallEntry();\n"),
    ('main/__init__.py',
     '    try:\n'
     '        import winreg\n'
     '        key_path = r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Lust"\n'
     '        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:\n'
     '            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)\n'
     '    except Exception:\n'
     '        pass\n',
     '    try:\n'
     '        import winreg\n'
     '    except ImportError:\n'
     '        return\n'
     '    uninstall = r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"\n'
     "    # Inno's entry is named after the AppId as written (AppId={{...}} keeps the closing }}); the\n"
     "    # duplicate Uninstall\\Lust of older installers is kept in sync while it exists\n"
     '    for name in ("{18B5D16F-154B-43C8-A6DF-21CB903DE869}}_is1", "Lust"):\n'
     '        try:\n'
     '            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"{uninstall}\\{name}", 0, winreg.KEY_SET_VALUE) as key:\n'
     '                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)\n'
     '        except Exception:\n'
     '            pass\n'),
]


# Update check without GitHub's API when its hourly limit is used up (60 calls per IP,
# shared with the skin downloader): releases/latest redirects to the newest tag, and the
# update package's name follows from it
GH_CLIENT = "launcher/update/github_client.py"
EDITS += [
    (GH_CLIENT,
     '        except Exception as e:\n'
     '            log.warning("Update check failed while fetching latest release: %s", e)\n'
     '            return None\n',
     '        except Exception as e:\n'
     '            log.warning("Update check failed while fetching latest release: %s", e)\n'
     '            return self._latest_from_web()\n'
     '\n'
     '    def _latest_from_web(self) -> Optional[dict]:\n'
     '        """The latest release from github.com itself, which the API limit does not cover."""\n'
     '        repo = GITHUB_RELEASE_API.split("/repos/", 1)[-1].rsplit("/releases", 1)[0]\n'
     '        try:\n'
     '            response = requests.get(f"https://github.com/{repo}/releases/latest",\n'
     '                                    timeout=self.timeout, allow_redirects=False)\n'
     '            tag = response.headers.get("Location", "").rstrip("/").rsplit("/tag/", 1)[-1]\n'
     '        except Exception as e:\n'
     '            log.warning("Update check from github.com failed too: %s", e)\n'
     '            return None\n'
     '        if response.status_code not in (301, 302) or not re.fullmatch(r"v?[0-9][0-9A-Za-z.]*", tag):\n'
     '            log.warning("Update check from github.com found no release tag")\n'
     '            return None\n'
     '        version = tag.lstrip("vV")\n'
     '        name = f"update_package_{version}.zip"\n'
     '        log.info("Latest release %s found on github.com (API limit reached)", tag)\n'
     '        return {"tag_name": tag, "assets": [{\n'
     '            "name": name, "size": 0,\n'
     '            "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}",\n'
     '        }]}\n'),
    (GH_CLIENT, "from typing import Optional\n", "import re\nfrom typing import Optional\n"),
]


# Silent updates (launcher/lust_autoupdate.py): a package downloaded in the background is
# installed as it is, without downloading it again
EDITS += [
    ("launcher/update/update_sequence.py",
     "        status_callback(f\"Downloading update {remote_version or ''}\")\n"
     "        if not self.downloader.download_update(\n",
     "        from launcher.lust_autoupdate import is_ready\n"
     "        predownloaded = is_ready(zip_path)\n"
     "        if predownloaded:\n"
     "            status_callback(\"Update downloaded in the background\")\n"
     "        else:\n"
     "            status_callback(f\"Downloading update {remote_version or ''}\")\n"
     "        if not predownloaded and not self.downloader.download_update(\n"),
    ("Lust.spec", "    'launcher.core',\n", "    'launcher.core',\n    'launcher.lust_autoupdate',\n    'launcher.lust_cleanup',\n    'launcher.lust_hero',\n"),
]


# Map skins in the hub (launcher/lust_maps.py) and the patcher manifest
# (injection/tools/patcher_manifest.py): the hub sees the shared state, PyInstaller takes both
EDITS += [
    ("main/core/initialization.py",
     '        state = SharedState()\n        log.info("Shared state initialized")\n',
     '        state = SharedState()\n        log.info("Shared state initialized")\n'
     '        try:\n'
     '            from launcher import lust_maps\n'
     '            lust_maps.attach_state(state)\n'
     '        except Exception as e:  # noqa: BLE001\n'
     '            log.debug(f"[Maps] Hub map picks stay saved choices only: {e}")\n'),
    ("Lust.spec", "    'launcher.lust_offline',\n    'launcher.autostart_default',\n",
     "    'launcher.lust_offline',\n    'launcher.lust_maps',\n    'injection.tools.patcher_manifest',\n"
     "    'launcher.autostart_default',\n"),
]


# Rose's files that Lust doesn't use: dropped from the tree on every sync
REMOVE = [
    "relay-worker",  # Rose's party relay server (Cloudflare worker); Lust runs no relay
    # Party Mode needs that relay: its lobby button opened a panel that could never connect
    "Pengu Loader/plugins/LUST-PartyMode",
]


def remove_unused(tree):
    for rel in REMOVE:
        path = tree / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def add_locale_strings(tree):
    """Add LOCALE_STRINGS to every LUST-I18n language, right after the opening brace."""
    for path in sorted((tree / "Pengu Loader/plugins/LUST-I18n/locales").glob("*.json")):
        raw = read_text(path)
        newline = "\r\n" if "\r\n" in raw else "\n"
        present = json.loads(raw)
        lines = [f"  {json.dumps(key, ensure_ascii=False)}: {json.dumps(values.get(path.stem, key), ensure_ascii=False)},"
                 for key, values in LOCALE_STRINGS.items() if key not in present]
        if not lines:
            continue
        head, rest = raw.split("{", 1)
        write_text(path, head + "{" + newline + newline.join(lines) + rest)


def apply_edits(tree):
    failures = []
    for rel, old, new in EDITS:
        path = tree / rel
        if not path.exists():
            failures.append(f"{rel}: file is gone")
            continue
        raw = read_text(path)
        crlf = "\r\n" in raw
        text = raw.replace("\r\n", "\n")
        # Already applied. An empty replacement is "in" every text, so it counts as applied
        # only once its old text is gone
        if (new and new in text) or (not new and old not in text):
            continue
        if text.count(old) != 1:
            failures.append(f"{rel}: expected text found {text.count(old)} times:\n{old[:200]}")
            continue
        text = text.replace(old, new)
        write_text(path, text.replace("\n", "\r\n") if crlf else text)
    if failures:
        raise SystemExit("[sync] Lust's edits no longer fit Rose's code:\n\n" + "\n\n".join(failures))


def install(tree):
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                             capture_output=True).stdout.decode("utf-8").split("\0")
    for rel in filter(None, tracked):
        if rel.split("/", 1)[0] in KEEP:
            continue
        path = ROOT / rel
        if path.is_file():
            path.unlink()
    for src in tree.rglob("*"):
        rel = src.relative_to(tree)
        if rel.parts[0] in KEEP or not src.is_file():
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    # Drop directories emptied by Rose deleting files
    for path in sorted(ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and ".git" not in path.parts and not any(path.iterdir()):
            path.rmdir()


LUST_PATCH = ROOT / "lust" / "lust_patch.txt"


def lust_version(rose_version):
    """Rose's version, plus Lust's own patch number while Lust follows that Rose release.

    lust_patch.txt holds "<rose version> <patch>": raise the patch to ship Lust fixes
    (1.4.9 -> 1.4.9.1 -> 1.4.9.2). A newer Rose release starts again without one.
    """
    try:
        rose, patch = LUST_PATCH.read_text(encoding="utf-8").split()
    except (OSError, ValueError):
        return rose_version
    return f"{rose_version}.{int(patch)}" if rose == rose_version and int(patch) > 0 else rose_version


def apply_lust_version(tree):
    config = tree / "config.py"
    text = config.read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("[sync] APP_VERSION not found in config.py")
    rose_version = match.group(1)
    version = lust_version(rose_version)
    if version == rose_version:
        return
    config.write_text(text.replace(f'APP_VERSION = "{rose_version}"', f'APP_VERSION = "{version}"', 1),
                      encoding="utf-8")
    iss = tree / "installer.iss"
    iss_text = iss.read_text(encoding="utf-8")
    for old, new in [(f'#define MyAppVersion "{rose_version}"', f'#define MyAppVersion "{version}"'),
                     (f'#define MyAppVersionInfo "{rose_version}.0"', f'#define MyAppVersionInfo "{version}"')]:
        if old not in iss_text:
            raise SystemExit(f"[sync] {old!r} not found in installer.iss")
        iss_text = iss_text.replace(old, new, 1)
    iss.write_text(iss_text, encoding="utf-8")
    print(f"[sync] Lust version {version}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    ref = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        extract_rose(ref, tree)
        rebrand_tree(tree)
        patch_core_dll(tree)
        remove_unused(tree)
        copy_overlay(tree)
        apply_edits(tree)
        add_locale_strings(tree)
        apply_lust_version(tree)
        install(tree)
    print(f"[sync] Lust tree rebuilt from Rose {ref}")


if __name__ == "__main__":
    main()
