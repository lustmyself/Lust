"""Build Lust Offline from a Deceive checkout.

Usage:
    python lust/offline/build_offline.py path/to/Deceive

Deceive (github.com/molenzwiebel/Deceive, GPL-3.0) proxies Riot chat so you can
appear offline. This script copies its source into lust/offline/src, renames
everything users see to Lust, removes the first-launch messages (chat welcome,
tray balloon, update prompt), builds it with `dotnet build` and puts the exe in
lust/overlay/injection/tools/LustOffline.exe. The modified source stays in the
repo because the GPL requires it to ship with the binary.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "lust" / "offline" / "src"
EXE = ROOT / "lust" / "overlay" / "injection" / "tools" / "LustOffline.exe"
ICON = ROOT / "lust" / "overlay" / "assets" / "icon.ico"
REPO_URL = "https://github.com/lustmyself/Lust"

# (file, old, new): exact replacements in Deceive's source. Each must match.
PATCHES = [
    # No welcome messages in chat on the first launch.
    ("Deceive/MainController.cs",
     "if (!SentIntroductionText && !Persistence.GetHasShownIntroduction())",
     "if (false)"),
    # No "masking your status" balloon when it starts.
    ("Deceive/MainController.cs", "        TrayIcon.ShowBalloonTip(5000);\n", ""),
    # No tray icon of its own: Lust's tray menu and the CUSTOMIZE tab set the status.
    ("Deceive/MainController.cs", "            Visible = true,\n", "            Visible = false,\n"),
    # The status file keeps the status in use, not only the one at exit: Lust's hub reads it
    ("Deceive/MainController.cs",
     "    private async Task UpdateStatusAsync(string newStatus)\n    {\n",
     "    private async Task UpdateStatusAsync(string newStatus)\n    {\n"
     "        try { File.WriteAllText(StatusFile, newStatus); } catch (IOException) { }\n"),
    # Lust ships updates itself; no prompt to download Deceive.
    ("Deceive/StartupHandler.cs", "        _ = Utils.CheckForUpdatesAsync();\n", ""),
    ("Deceive/StartupHandler.cs",
     'public static string DeceiveTitle => "Deceive " + Utils.DeceiveVersion;',
     'public static string DeceiveTitle => "Lust Offline";'),
    # Its own settings folder, apart from Lust's.
    ("Deceive/Persistence.cs",
     'Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Deceive")',
     'Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Lust Offline")'),
    # Lust has no FAQ of its own: the DNS fix lives in Deceive's.
    ("Deceive/Utils.cs", "Please see the Deceive FAQ for more information.",
     "Please see the FAQ for more information."),
    ("Deceive/Utils.cs", 'Process.Start("https://github.com/molenzwiebel/Deceive#FAQ");',
     'Process.Start("https://github.com/molenzwiebel/Deceive#faq");'),
    ("Deceive/Deceive.csproj",
     "    <OutputType>WinExe</OutputType>\n",
     "    <OutputType>WinExe</OutputType>\n    <AssemblyName>LustOffline</AssemblyName>\n"
     "    <Product>Lust Offline</Product>\n    <AssemblyTitle>Lust Offline</AssemblyTitle>\n"
     "    <Company>Lust</Company>\n"
     "    <Copyright>Copyright (c) molenzwiebel and Lust contributors, GPL-3.0</Copyright>\n"),
]

STRING_LITERAL = re.compile(r'\$?"(?:[^"\\\n]|\\.)*"')
# The word alone, so names inside interpolations ({DeceiveTitle}) keep working.
WORD = re.compile(r"\bDeceive\b")
# Resource lookups use the namespace inside a string; leave those alone.
SKIP_RENAME = {"Deceive/Properties/Resources.Designer.cs"}


def rename_strings(text):
    # Links to Deceive's repo point at Lust's, except its FAQ section
    text = re.sub(r"https://github\.com/molenzwiebel/Deceive(?!#faq)", REPO_URL, text)
    return STRING_LITERAL.sub(
        lambda m: m.group(0) if "molenzwiebel/Deceive#faq" in m.group(0) else WORD.sub("Lust", m.group(0)),
        text)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    upstream = Path(sys.argv[1])

    if SRC.exists():
        shutil.rmtree(SRC)
    shutil.copytree(upstream / "Deceive", SRC / "Deceive",
                    ignore=shutil.ignore_patterns("bin", "obj"))
    for name in ("Deceive.sln", "LICENSE", "README.md"):
        shutil.copy2(upstream / name, SRC / name)

    for rel, old, new in PATCHES:
        path = SRC / rel
        text = path.read_text(encoding="utf-8-sig")
        if old not in text:
            sys.exit(f"[offline] patch target not found in {rel}: {old[:70]!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")

    for path in (SRC / "Deceive").rglob("*.cs"):
        rel = path.relative_to(SRC).as_posix()
        if rel in SKIP_RENAME:
            continue
        text = path.read_text(encoding="utf-8-sig")
        renamed = rename_strings(text)
        if renamed != text:
            path.write_text(renamed, encoding="utf-8")
        leftover = [m.group(0) for m in STRING_LITERAL.finditer(renamed)
                    if WORD.search(m.group(0).replace("molenzwiebel/Deceive#faq", ""))]
        if leftover:
            sys.exit(f"[offline] Deceive left in {rel}: {leftover[:3]}")

    shutil.copy2(ICON, SRC / "Deceive" / "Resources" / "deceive.ico")

    subprocess.run(["dotnet", "build", str(SRC / "Deceive" / "Deceive.csproj"),
                    "-c", "Release", "-nologo", "-v", "q"], check=True)
    built = SRC / "Deceive" / "bin" / "Release" / "net472" / "LustOffline.exe"
    EXE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, EXE)
    shutil.rmtree(SRC / "Deceive" / "bin")
    shutil.rmtree(SRC / "Deceive" / "obj")
    print(f"[offline] {EXE.relative_to(ROOT)} built from {upstream}")


if __name__ == "__main__":
    main()
