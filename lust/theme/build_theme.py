"""Build the LUST-Theme Pengu plugin from an Elaina theme release.

Usage:
    python lust/theme/build_theme.py ElainaV4.zip elaina-theme-data-X.Y.Z.tgz

ElainaV4.zip is the release asset from github.com/Elaina69/Elaina-theme and the
.tgz is the matching `elaina-theme-data` package from npm (both MIT). The output
replaces lust/overlay/Pengu Loader/plugins/LUST-Theme, which sync.py then copies
into the tree like any other overlay file.

What changes compared to Elaina:
- Every "Elaina" name becomes "Lust" (code, storage keys, CSS, locales, files).
- The data module the theme loads from jsdelivr at every start is replaced by
  lust/theme/data, shipped inside the plugin: no remote code, no tracking,
  no cloud backup or icon upload to Elaina's server.
- Elaina/anime artwork, the bundled songs, contributor photos, donation links,
  custom champion art and fonts we can't redistribute are removed or replaced
  with Lust's Kai'Sa artwork.
- Settings that broadcast fake rank/mastery to friends start disabled.
"""

import io
import re
import shutil
import sys
import tarfile
import tempfile
import wave
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "lust" / "overlay" / "Pengu Loader" / "plugins" / "LUST-Theme"
BRAND = ROOT / "lust" / "overlay" / "assets"
REPO_URL = "https://github.com/lustmyself/Lust"

TEXT_SUFFIXES = {".js", ".css", ".txt", ".json", ".md", ".url"}

# Files dropped from the release (relative to the plugin root).
REMOVE = [
    "assets/backgrounds/audio/Laur - Mellifluous.flac",
    "assets/backgrounds/audio/Laur - その花は世界を紡ぐ.flac",
    "assets/backgrounds/wallpapers/elaina1.webm",
    "assets/backgrounds/wallpapers/elaina2.jpg",
    "assets/champs",
    "assets/icon/about-us",
    "assets/icon/avatar.gif",
    "assets/icon/loading.gif",
    "assets/icon/animation-logo.gif",
    "assets/icon/ko-fi.webp",
    "assets/icon/paypal.png",
    "assets/icon/momo.svg",
    "assets/fonts/elaina-herculanum_roman.ttf",
    "assets/fonts/aegirseaborn.ttf",
    "assets/fonts/minecraftregular-bmg3.otf",
]

ABOUT_US = '''async function aboutustab(panel) {
  panel.prepend(
    UI.createRow("", [
      UI.createRow("Developer", [
        UI.createRow("dev-avatar", [
          UI.createRow("dev-div", [
            UI.createImageWithLink(true, "logo.png", "dev_ava", "%s", () => {
            }),
            UI.createLabel("Lust", "first_line_elaina"),
            UI.createLabel("github.com/lustmyself/Lust", "")
          ])
        ])
      ])
    ])
  );
}

''' % REPO_URL

# (file, old, new): exact replacements applied before renaming. Each must match.
PATCHES = [
    # Default wallpaper/audio are Lust's own files.
    ("index.js",
     '"Wallpaper-list": ["elaina1.webm", "elaina2.jpg"],',
     '"Wallpaper-list": ["lust-wallpaper.webm", "lust-wallpaper.jpg"],'),
    ("index.js",
     '"Audio-list": ["Laur - その花は世界を紡ぐ.flac", "Laur - Mellifluous.flac"],',
     '"Audio-list": ["lust-silence.wav"],'),
    # Cloud backup went to Elaina's server: hide that part of the backup tab.
    ("index.js",
     "const cloud = await cloudBackupSection();",
     "const cloud = { elements: [], postSetup: async () => {} };"),
    # Easter egg that opens Elaina's server.
    ("index.js",
     '          window.open(`${ElainaData.get("Elaina-domain-server")}elaina_nsfw/easteregg1`, "_blank");\n',
     ""),
    # NSFW toggle only drove Elaina's counter and easter egg.
    ("index.js",
     'async function nsfwSection() {\n  return UI.createCheckBox(',
     'async function nsfwSection() {\n  return document.createElement("div");\n  return UI.createCheckBox('),
    # Links to Elaina's repo point at Lust.
    ("index.js",
     "https://github.com/Elaina69/Elaina-V4/releases/tag/v${cdn.version}",
     REPO_URL + "/releases"),
    ("index.js", "https://github.com/Elaina69/Elaina-V4/releases", REPO_URL + "/releases"),
    ("index.js", '"ElainaV4",\n          "https://github.com/Elaina69/Elaina-V4",',
     '"Lust",\n          "' + REPO_URL + '",'),
    # Default settings.
    ("config/datastoreDefault.js", '"Rank-line1"                    : "Apprentice",',
     '"Rank-line1"                    : "Daughter of",'),
    ("config/datastoreDefault.js", '"Rank-line2"                    : "Witch",',
     '"Rank-line2"                    : "the Void",'),
    ("config/datastoreDefault.js", '"CurrentFont"                   : "elaina-herculanum_roman.ttf",',
     '"CurrentFont"                   : "beaufortforlol-bold.ttf",'),
    ("config/datastoreDefault.js",
     '\t\t"aegirseaborn.ttf",\n\t\t"elaina-herculanum_roman.ttf",\n\t\t"minecraftregular-bmg3.otf",\n\t\t"roboto-medium.ttf"',
     '\t\t"beaufortforlol-bold.ttf",\n\t\t"roboto-medium.ttf"'),
    ("config/datastoreDefault.js", '"nickname-color"                : "#f2c1d0",',
     '"nickname-color"                : "#b48cff",'),
    ("config/datastoreDefault.js", '"nickname-color-with-opacity"   : "#f2c1d0ff",',
     '"nickname-color-with-opacity"   : "#b48cffff",'),
    ("config/datastoreDefault.js", '"disable-theme-audio"           : false,',
     '"disable-theme-audio"           : true,'),
    ("config/datastoreDefault.js", '"holiday-message"               : true,',
     '"holiday-message"               : false,'),
    ("config/datastoreDefault.js", '"sync-user-icons"               : true,',
     '"sync-user-icons"               : false,'),
    ("config/datastoreDefault.js", '"Runes-BG"                      : true,',
     '"Runes-BG"                      : false,'),
    # These PUT fake values to /lol-chat/v1/me, which friends see.
    ("config/datastoreDefault.js", '"Custom-mastery-score"          : true,',
     '"Custom-mastery-score"          : false,'),
    ("config/datastoreDefault.js", '"Custom-rank"                   : true,',
     '"Custom-rank"                   : false,'),
    ("config/datastoreDefault.js", '"Custom-challenge-crystal"      : true,',
     '"Custom-challenge-crystal"      : false,'),
    ("config/icons.js", '"animation-logo.gif"', '"animation-logo.png"'),
    ("config/icons.js", '"loading.gif"', '"loading.png"'),
    ("config/icons.js", '"avatar.gif"', '"avatar.png"'),
]

# Names that must not go through the plain Elaina -> Lust rename.
PRE_RENAMES = [
    (re.compile(r"https://github\.com/Elaina69\b[\w./-]*"), REPO_URL),
    (re.compile(r"Elaina Da Catto"), "Lust"),
    (re.compile(r"elaina ?da ?catto", re.I), "lust"),
    (re.compile(r"Elaina69"), "lustmyself"),
    (re.compile(r"elaina[-_]?v[24]", re.I), "Lust"),
]


def match_case(word, repl):
    if word.isupper():
        return repl.upper()
    if word[0].isupper():
        return repl.capitalize()
    return repl.lower()


def rename(text):
    for pattern, repl in PRE_RENAMES:
        text = pattern.sub(repl, text)
    return re.sub(r"elaina", lambda m: match_case(m.group(0), "lust"), text, flags=re.I)


def apply_patches(root):
    for rel, old, new in PATCHES:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        if old not in text:
            sys.exit(f"[theme] patch target not found in {rel}: {old[:70]!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")

    index = root / "index.js"
    text = index.read_text(encoding="utf-8")
    start = text.find("async function aboutustab(panel) {")
    end = text.find("const datapath$5 = ", start)
    if start < 0 or end < 0:
        sys.exit("[theme] about-us tab not found in index.js")
    index.write_text(text[:start] + ABOUT_US + text[end:], encoding="utf-8")


def rename_tree(root):
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        # The MIT notice keeps Elaina's copyright line as the license requires.
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and path.name != "LICENSE.txt":
            text = path.read_text(encoding="utf-8")
            renamed = rename(text)
            if renamed != text:
                path.write_text(renamed, encoding="utf-8")
        if "elaina" in path.name.lower():
            path.rename(path.with_name(rename(path.name)))


# Artwork ---------------------------------------------------------------------

VOID_TOP = (18, 10, 36)
VOID_BOTTOM = (59, 29, 110)


def gradient(size, top=VOID_TOP, bottom=VOID_BOTTOM):
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        draw.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def fit(img, size):
    img = img.copy()
    img.thumbnail(size, Image.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return canvas


def with_logo(bg, logo, width_ratio, opacity=1.0, glow=True):
    bg = bg.convert("RGBA")
    logo = logo.copy()
    target = int(bg.width * width_ratio)
    logo = logo.resize((target, int(logo.height * target / logo.width)), Image.LANCZOS)
    if opacity < 1:
        logo.putalpha(logo.getchannel("A").point(lambda a: int(a * opacity)))
    pos = ((bg.width - logo.width) // 2, (bg.height - logo.height) // 2)
    if glow:
        halo = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        shadow = Image.new("RGBA", logo.size, (139, 92, 246, 0))
        shadow.putalpha(logo.getchannel("A").point(lambda a: int(a * 0.8)))
        halo.alpha_composite(shadow, pos)
        bg.alpha_composite(halo.filter(ImageFilter.GaussianBlur(bg.width // 60)))
    bg.alpha_composite(logo, pos)
    return bg


def write_silence(path, seconds=1, rate=8000):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(rate)
        wav.writeframes(bytes([128]) * rate * seconds)


def make_art(root):
    word = Image.open(BRAND / "golden_lust.png").convert("RGBA")
    word = word.crop(word.getbbox())
    ring = Image.open(BRAND / "lust_without_bg.png").convert("RGBA")
    square = Image.open(BRAND / "icon.png").convert("RGBA")
    icon = root / "assets" / "icon"
    bgs = root / "assets" / "backgrounds"

    shutil.copy2(HERE / "art" / "lust-wallpaper.webm", bgs / "wallpapers" / "lust-wallpaper.webm")
    with_logo(gradient((1920, 1080)), word, 0.32).convert("RGB").save(
        bgs / "wallpapers" / "lust-wallpaper.jpg", quality=90)
    write_silence(bgs / "audio" / "lust-silence.wav")

    fit(word, (551, 476)).save(icon / "animation-logo.png")
    fit(ring, (250, 250)).save(icon / "logo.png")
    fit(ring, (320, 320)).save(icon / "loading.png")
    square.resize((362, 362), Image.LANCZOS).save(icon / "avatar.png")
    for name, size in [("clash.png", 300), ("rank.png", 300), ("rp-icon.png", 128),
                       ("be-icon.png", 128), ("ticker.png", 128), ("mouse-cursor.png", 32)]:
        fit(ring, (size, size)).save(icon / name)

    with_logo(gradient((1600, 900)), word, 0.25, opacity=0.35, glow=False).convert("RGB").save(
        icon / "hover-card-backdrop.jpg", quality=90)
    with_logo(gradient((1280, 720)), word, 0.3, opacity=0.5).convert("RGB").save(
        icon / "plugins-icons" / "ll-settings.jpg", quality=90)

    # One tint per rune tree, used only when "Runes-BG" is turned on.
    tints = {"precision": (200, 170, 110), "domination": (210, 60, 70), "sorcery": (110, 120, 240),
             "resolve": (90, 190, 120), "inspiration": (80, 200, 220)}
    for name, tint in tints.items():
        bottom = tuple((a + b) // 2 for a, b in zip(VOID_BOTTOM, tint))
        with_logo(gradient((1920, 1080), VOID_TOP, bottom), word, 0.2, opacity=0.25, glow=False) \
            .convert("RGB").save(bgs / "runes" / f"{name}.jpg", quality=88)


# Data module -------------------------------------------------------------------

def install_data(root, data_pkg, version):
    data = root / f"elaina-theme-data@{version}"
    shutil.copytree(HERE / "data", data)
    (data / "src" / "update").mkdir(parents=True, exist_ok=True)
    shutil.copy2(data_pkg / "src" / "update" / "update.js", data / "src" / "update" / "update.js")
    shutil.copy2(data_pkg / "LICENSE.txt", data / "LICENSE.txt")

    (root / "config" / "cdnServer.js").write_text(
        "// Lust: the theme data module ships inside this plugin instead of loading from a CDN.\n"
        "export default {\n"
        '    "cdn-url": new URL("../", import.meta.url).href,\n'
        f'    "version": "{version}"\n'
        "}\n",
        encoding="utf-8",
    )


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    release_zip, data_tgz = map(Path, sys.argv[1:])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        theme = tmp / "theme"
        with zipfile.ZipFile(release_zip) as z:
            z.extractall(theme)
        with tarfile.open(data_tgz) as t:
            t.extractall(tmp / "data", filter="data")
        data_pkg = tmp / "data" / "package"
        version = re.search(r'"version":\s*"([^"]+)"',
                            (data_pkg / "package.json").read_text(encoding="utf-8")).group(1)

        for rel in REMOVE:
            path = theme / rel
            if not path.exists():
                sys.exit(f"[theme] expected file missing from release: {rel}")
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        (theme / "config" / "champsBgList.js").write_text("export default []\n", encoding="utf-8")

        apply_patches(theme)
        make_art(theme)
        install_data(theme, data_pkg, version)
        shutil.copy2(data_pkg / "LICENSE.txt", theme / "LICENSE.txt")
        rename_tree(theme)

        leftovers = [str(p.relative_to(theme)) for p in theme.rglob("*")
                     if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and p.name != "LICENSE.txt"
                     and re.search(r"elaina", p.read_text(encoding="utf-8"), re.I)]
        if leftovers:
            sys.exit(f"[theme] Elaina left in: {leftovers}")

        if OUT.exists():
            shutil.rmtree(OUT)
        shutil.copytree(theme, OUT)
    print(f"[theme] LUST-Theme {version} written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
