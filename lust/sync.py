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
import os
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
    dll.write_bytes(data)


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
        if new in text:
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


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    ref = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        extract_rose(ref, tree)
        rebrand_tree(tree)
        patch_core_dll(tree)
        copy_overlay(tree)
        apply_edits(tree)
        install(tree)
    print(f"[sync] Lust tree rebuilt from Rose {ref}")


if __name__ == "__main__":
    main()
