"""The desktop hub's window: Lust's own Tkinter window, no browser.

It runs on its own thread (Tk is touched only there) and shows what launcher/lust_hub.py
holds: startup progress, Lust's and League's status, the version, what's new, and the
quick actions. Closing it only hides it; the tray icon brings it back.

Everything is drawn on one canvas (rounded cards, icon tiles, pills), so card corners
blend into the background instead of showing Tk's square widget edges.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import time
from typing import Callable, Optional

from utils.core.logging import get_logger

log = get_logger()

BG_TOP = (13, 12, 19)
BG_BOTTOM = (22, 14, 34)
CARD = "#15141d"
CARD_HOVER = "#1c1a27"
CARD_LINE = "#24222f"
TILE = "#211f2c"
TEXT = "#f0eef5"
SUB = "#8d8a95"
FAINT = "#5d5a66"
ACCENT = "#a78bfa"
ACCENT_SOFT = "#2a2340"
ACCENT_LINE = "#4b3f73"
GREEN = "#4ade80"
AMBER = "#f5b14c"
RED = "#f87171"
RED_SOFT = "#2c1719"
YELLOW = "#f2c94c"

SIZE = (760, 640)
PAD = 18
GAP = 10
RADIUS = 14
FONT = "Segoe UI"
FONT_BOLD = ("Segoe UI Semibold",)
ICON_FONT = "Segoe MDL2 Assets"  # ships with Windows 10 and 11
ICONS = {
    "lust": "", "league": "", "skins": "", "appear": "",
    "play": "", "folder": "", "log": "", "power": "",
    "restart": "", "close": "", "sync": "", "download": "",
}
ICONS["music"] = "\ue8d6"
REFRESH_MS = 500
STATE_INTERVAL_S = 0.5

TEXT_STRINGS = {
    "en": {
        "lust": "Lust", "running": "Running", "starting": "Starting",
        "league": "League", "league_on": "Open", "league_off": "Closed",
        "skins": "Skins", "ready": "Ready", "not_ready": "Getting ready",
        "up_to_date": "Up to date", "new_version": "New version {v}",
        "checked": "last checked {when}", "never": "not yet", "check": "Check now", "update": "Update",
        "appear": "Appear as", "online": "Online", "offline": "Offline", "mobile": "Mobile",
        "offline_hint": "Open League from here to choose", "open_league": "Open League", "league_open": "League is open",
        "start_league": "Through Lust Offline", "mods": "Mods folder", "mods_sub": "Open in Explorer",
        "log": "Copy log", "log_sub": "Paste it into Discord", "autostart": "Start with Windows",
        "on": "On", "off": "Off", "restart": "Restart", "restart_sub": "Restart Lust",
        "quit": "Close Lust", "quit_sub": "Quit completely", "quit_confirm": "Click again",
        "client_hint": "Set your game settings by clicking the LUST tab in the LoL client.",
        "prompt_title": "Lust {v} is ready to install", "prompt_body": "You have {c}. Install it now?",
        "install": "Install", "later": "Not now", "just_now": "just now", "min_ago": "{n} min ago",
        "status_ready": "Ready", "status_starting": "Starting",
    },
    "tr": {
        "lust": "Lust", "running": "Çalışıyor", "starting": "Başlıyor",
        "league": "League", "league_on": "Açık", "league_off": "Kapalı",
        "skins": "Skinler", "ready": "Hazır", "not_ready": "Hazırlanıyor",
        "up_to_date": "Güncel", "new_version": "Yeni sürüm {v}",
        "checked": "son kontrol {when}", "never": "henüz yok", "check": "Şimdi kontrol et", "update": "Güncelle",
        "appear": "Görün", "online": "Çevrimiçi", "offline": "Çevrimdışı", "mobile": "Mobil",
        "offline_hint": "Seçmek için League'i buradan aç", "open_league": "League'i aç", "league_open": "League açık",
        "start_league": "Lust Offline üzerinden", "mods": "Mod klasörü", "mods_sub": "Gezginde aç",
        "log": "Logu kopyala", "log_sub": "Discord'a yapıştır", "autostart": "Windows ile başlat",
        "on": "Açık", "off": "Kapalı", "restart": "Yeniden başlat", "restart_sub": "Lust'ı yeniden başlat",
        "quit": "Lust'ı kapat", "quit_sub": "Tamamen kapat", "quit_confirm": "Tekrar tıkla",
        "client_hint": "Oyun ayarlarınızı LoL istemcisindeki LUST sekmesine tıklayarak ayarlayabilirsiniz.",
        "prompt_title": "Lust {v} kurulmaya hazır", "prompt_body": "Sendeki sürüm {c}. Şimdi kurulsun mu?",
        "install": "Kur", "later": "Şimdi değil", "just_now": "az önce", "min_ago": "{n} dk önce",
        "status_ready": "Hazır", "status_starting": "Başlıyor",
    },
}

_thread: Optional[threading.Thread] = None
_started = threading.Event()
_failed = False
_visible = False
_commands: "queue.Queue[str]" = queue.Queue()


def _in_game() -> bool:
    try:
        from launcher.lust_offline import _processes
        return bool(_processes({"league of legends.exe"}))
    except Exception:  # noqa: BLE001
        return False


def available() -> bool:
    try:
        import tkinter  # noqa: F401
        return True
    except ImportError:
        return False


def visible() -> bool:
    return _visible


def show() -> bool:
    """Open the window, or raise it when it's open. False when Tk can't start."""
    global _thread
    if _thread is None or not _thread.is_alive():
        if _failed:
            return False
        _started.clear()
        _thread = threading.Thread(target=_run, daemon=True, name="LustHubWindow")
        _thread.start()
        _started.wait(10)
        return not _failed and _thread.is_alive()
    _commands.put("show")
    return True


def _run() -> None:
    global _failed, _visible
    try:
        window = HubWindow()
    except Exception as exc:  # noqa: BLE001
        log.warning(f"[Hub] Window could not start: {exc}")
        _failed = True
        _started.set()
        return
    _visible = True
    _started.set()
    try:
        window.root.mainloop()
    finally:
        _visible = False


class _State:
    """The hub's state, read off the window's thread so a slow probe never stalls drawing."""

    def __init__(self) -> None:
        self.value: Optional[dict] = None
        self.wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True, name="LustHubState").start()

    def _loop(self) -> None:
        from launcher import lust_hub
        while True:
            if _visible or self.value is None:
                try:
                    self.value = lust_hub.snapshot()
                except Exception as exc:  # noqa: BLE001
                    log.debug(f"[Hub] State read failed: {exc}")
            self.wake.wait(STATE_INTERVAL_S)
            self.wake.clear()


def _blend(a, b, t):
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class HubWindow:
    def __init__(self) -> None:
        import tkinter as tk
        from config import APP_VERSION
        from launcher import lust_hub

        self.hub = lust_hub
        self.state = _State()
        self.lang = lust_hub.LANG
        self.version = APP_VERSION
        self.quit_armed = 0.0
        self.toast_id = None
        self.toast_after = None
        self.busy_pos = 0.0
        self.progress_value: Optional[int] = None
        self.hover: Optional[str] = None
        self.clickable: dict[str, Callable[[], None]] = {}
        self.enabled: dict[str, bool] = {}
        self.cards: dict[str, dict] = {}
        self.page = "lol"

        root = self.root = tk.Tk()
        root.withdraw()
        root.title("Lust")
        root.resizable(False, False)
        self.s = s = max(1.0, root.winfo_fpixels("1i") / 96)
        self.w, self.h = int(SIZE[0] * s), int(SIZE[1] * s)
        x = (root.winfo_screenwidth() - self.w) // 2
        y = (root.winfo_screenheight() - self.h) // 2
        root.geometry(f"{self.w}x{self.h}+{max(0, x)}+{max(0, y)}")
        try:
            from utils.core.paths import get_asset_path
            root.iconbitmap(default=str(get_asset_path("icon.ico")))
        except Exception:  # noqa: BLE001 - Tk's own icon then
            pass
        root.protocol("WM_DELETE_WINDOW", self.hide)

        c = self.c = tk.Canvas(root, width=self.w, height=self.h, highlightthickness=0, bd=0,
                               bg=_blend(BG_TOP, BG_TOP, 0))
        c.pack(fill="both", expand=True)
        self._background()
        self._layout()
        c.bind("<Motion>", self._motion)
        c.bind("<Leave>", lambda _e: self._set_hover(None))
        c.bind("<Button-1>", self._click)

        self._refresh()
        self._poll_commands()
        self._animate()
        self.reveal()

    # ---- drawing helpers ----

    def p(self, value: float) -> int:
        return int(value * self.s)

    def t(self, key: str, **values) -> str:
        text = TEXT_STRINGS.get(self.lang, TEXT_STRINGS["en"]).get(key, key)
        for name, value in values.items():
            text = text.replace("{" + name + "}", str(value))
        return text

    def rrect(self, x1, y1, x2, y2, r, **kw):
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                  x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.c.create_polygon(points, smooth=True, splinesteps=24, **kw)

    def _background(self) -> None:
        # A soft vertical fade with a violet glow toward the bottom right
        steps = 64
        for i in range(steps):
            y1 = self.h * i / steps
            y2 = self.h * (i + 1) / steps + 1
            self.c.create_rectangle(0, y1, self.w, y2, outline="", fill=_blend(BG_TOP, BG_BOTTOM, i / steps))

    def text(self, x, y, value="", size=10, color=TEXT, bold=False, anchor="w", width=0, tags=()):
        font = (FONT_BOLD[0] if bold else FONT, size)
        return self.c.create_text(x, y, text=value, fill=color, font=font, anchor=anchor,
                                  width=width or 0, tags=tags)

    def card(self, key, x1, y1, x2, y2, clickable: Optional[Callable[[], None]] = None, radius=RADIUS) -> dict:
        tag = f"card-{key}"
        bg = self.rrect(x1, y1, x2, y2, self.p(radius), fill=CARD, outline=CARD_LINE, tags=(tag, f"{tag}-bg"))
        card = {"tag": tag, "bg": bg, "box": (x1, y1, x2, y2), "fill": CARD, "hover_fill": CARD_HOVER}
        self.cards[key] = card
        if clickable:
            self.clickable[key] = clickable
            self.enabled[key] = True
        return card

    def tile(self, key, x1, y1, x2, y2, icon, clickable=None, danger=False) -> dict:
        """An icon square, a title and a subtitle, and a status dot on the right (as in the mockup)."""
        card = self.card(key, x1, y1, x2, y2, clickable)
        tag = card["tag"]
        size = self.p(36)
        cy = (y1 + y2) / 2
        ix1, iy1 = x1 + self.p(12), cy - size / 2
        card["icon_bg"] = self.rrect(ix1, iy1, ix1 + size, iy1 + size, self.p(10),
                                     fill=RED_SOFT if danger else TILE, outline="", tags=(tag,))
        card["icon"] = self.c.create_text(ix1 + size / 2, cy, text=ICONS.get(icon, ""),
                                          fill=RED if danger else ACCENT, font=(ICON_FONT, 13), tags=(tag,))
        tx = ix1 + size + self.p(12)
        card["title"] = self.text(tx, cy - self.p(9), size=10, bold=True, color=RED if danger else TEXT, tags=(tag,))
        card["sub"] = self.text(tx, cy + self.p(10), size=8, color=SUB, tags=(tag,))
        r = self.p(4)
        dx = x2 - self.p(18)
        card["dot"] = self.c.create_oval(dx - r, cy - r, dx + r, cy + r, fill=FAINT, outline="", tags=(tag,))
        card["danger"] = danger
        return card

    def pill(self, key, x1, y1, x2, y2, label, onclick, accent=False) -> dict:
        tag = f"card-{key}"
        bg = self.rrect(x1, y1, x2, y2, (y2 - y1) / 2, fill=ACCENT if accent else TILE, outline="", tags=(tag,))
        txt = self.text((x1 + x2) / 2, (y1 + y2) / 2, label, size=9, bold=True,
                        color="#15111f" if accent else TEXT, anchor="center", tags=(tag,))
        card = {"tag": tag, "bg": bg, "label": txt, "box": (x1, y1, x2, y2),
                "fill": ACCENT if accent else TILE, "hover_fill": "#c4b5fd" if accent else "#2c2a3a"}
        self.cards[key] = card
        self.clickable[key] = onclick
        self.enabled[key] = True
        return card

    # ---- layout ----

    def _layout(self) -> None:
        p, c = self.p, self.c
        left, right = p(PAD), self.w - p(PAD)
        width = right - left
        col = (width - 2 * p(GAP)) / 3

        # Header: version pill, tabs, status pill
        vx = left
        self.rrect(vx, p(27), vx + p(64), p(45), p(9), fill=CARD, outline=CARD_LINE)
        self.text(vx + p(32), p(36), self.version, size=8, color=SUB, anchor="center")
        self.status_pill = self.rrect(right - p(96), p(25), right, p(47), p(11), fill=CARD, outline=CARD_LINE)
        self.status_dot = c.create_oval(right - p(84), p(32), right - p(76), p(40), fill=AMBER, outline="")
        self.status_text = self.text(right - p(70), p(36), "", size=9, bold=True)

        # LoL / Spotify tabs
        tx = self.w / 2 - p(80)
        self.tab_lol = self.pill("tab_lol", tx, p(25), tx + p(76), p(47), "LoL", lambda: self._set_page("lol"))
        self.tab_spotify = self.pill("tab_spotify", tx + p(84), p(25), tx + p(160), p(47), "Spotify",
                                     lambda: self._set_page("spotify"))
        lol_start = len(c.find_all())

        # Where the game settings are
        self.hint = self.text(left, p(74), self.t("client_hint"), size=10, color=YELLOW, bold=True, width=width)

        # Row 1: Lust, League, skins
        y = p(100)
        h = p(62)
        self.t_lust = self.tile("lust", left, y, left + col, y + h, "lust")
        self.t_league = self.tile("league", left + col + p(GAP), y, left + 2 * col + p(GAP), y + h, "league")
        self.t_skins = self.tile("skins", right - col, y, right, y + h, "skins")

        # Row 2: startup progress, the update question, or the status picker (same place)
        y2 = y + h + p(GAP)
        h2 = p(70)
        self.row2 = (left, y2, right, y2 + h2)
        self._progress_items(left, y2, right, y2 + h2)
        self._prompt_items(left, y2, right, y2 + h2)
        self._appear_items(left, y2, right, y2 + h2)

        # Rows 3 and 4: actions
        y3 = y2 + h2 + p(GAP)
        h3 = p(60)
        xs = [left, left + col + p(GAP), right - col]
        self.a_league = self.tile("a_league", xs[0], y3, xs[0] + col, y3 + h3, "play", lambda: self._act("league"))
        self.a_mods = self.tile("a_mods", xs[1], y3, xs[1] + col, y3 + h3, "folder", lambda: self._act("mods"))
        self.a_log = self.tile("a_log", xs[2], y3, xs[2] + col, y3 + h3, "log", lambda: self._act("log"))
        y4 = y3 + h3 + p(GAP)
        self.a_auto = self.tile("a_auto", xs[0], y4, xs[0] + col, y4 + h3, "power", lambda: self._act("autostart"))
        self.a_restart = self.tile("a_restart", xs[1], y4, xs[1] + col, y4 + h3, "restart", lambda: self._act("restart"))
        self.a_quit = self.tile("a_quit", xs[2], y4, xs[2] + col, y4 + h3, "close", self._quit_clicked, danger=True)

        # Row 5: version, what's new, and the round update button
        y5 = y4 + h3 + p(GAP)
        bottom = self.h - p(PAD)
        self.v_card = self.card("version", left, y5, right, bottom)
        art = p(64)
        ay = y5 + p(16)
        self.rrect(left + p(16), ay, left + p(16) + art, ay + art, p(14), fill=ACCENT_SOFT, outline=ACCENT_LINE)
        mark = self.text(left + p(16) + art / 2, ay + art / 2, "L", color=ACCENT, anchor="center")
        c.itemconfig(mark, font=("Georgia", 24, "bold"))
        tx = left + p(16) + art + p(16)
        self.v_title = self.text(tx, ay + p(12), f"Lust {self.version}", size=12, bold=True)
        self.v_sub = self.text(tx, ay + p(34), "", size=9, color=SUB)
        self.v_news = self.text(tx, ay + p(52), "", size=8, color=SUB, anchor="nw", width=width - art - p(140))
        bx = right - p(40)
        by = (y5 + bottom) / 2
        br = p(24)
        self.v_button = self.c.create_oval(bx - br, by - br, bx + br, by + br, fill=ACCENT, outline="",
                                           tags=("card-v_button",))
        self.v_button_icon = self.c.create_text(bx, by, text=ICONS["sync"], fill="#15111f",
                                                font=(ICON_FONT, 14), tags=("card-v_button",))
        self.cards["v_button"] = {"tag": "card-v_button", "bg": self.v_button, "box": (bx - br, by - br, bx + br, by + br),
                                  "fill": ACCENT, "hover_fill": "#c4b5fd", "oval": True}
        self.clickable["v_button"] = self._update_clicked
        self.enabled["v_button"] = True

        for item in c.find_all()[lol_start:]:
            c.addtag_withtag("page-lol", item)
        self._spotify_layout()

        # Toast, drawn last so it sits on top
        self.toast_bg = self.rrect(0, 0, 1, 1, p(16), fill="#24212f", outline=ACCENT_LINE, state="hidden")
        self.toast_text = self.text(0, 0, "", size=9, color=TEXT, anchor="center", width=self.w - p(120))
        self.c.itemconfig(self.toast_text, state="hidden")

    def _progress_items(self, x1, y1, x2, y2) -> None:
        p = self.p
        card = self.card("progress", x1, y1, x2, y2)
        tag = card["tag"]
        self.p_status = self.text(x1 + p(18), y1 + p(20), "", size=10, bold=True, tags=(tag,))
        self.p_pct = self.text(x2 - p(18), y1 + p(20), "", size=10, bold=True, color=ACCENT, anchor="e", tags=(tag,))
        self.bar = (x1 + p(18), y1 + p(38), x2 - p(18), y1 + p(44))
        bx1, by1, bx2, by2 = self.bar
        self.rrect(bx1, by1, bx2, by2, p(3), fill="#2a2836", outline="", tags=(tag,))
        self.bar_fill = self.rrect(bx1, by1, bx1 + 1, by2, p(3), fill=ACCENT, outline="", tags=(tag,))
        self.p_detail = self.text(x1 + p(18), y1 + p(56), "", size=8, color=SUB, tags=(tag,))

    def _prompt_items(self, x1, y1, x2, y2) -> None:
        p = self.p
        card = self.card("prompt", x1, y1, x2, y2)
        self.c.itemconfig(card["bg"], outline=ACCENT_LINE, fill=ACCENT_SOFT)
        card["fill"] = card["hover_fill"] = ACCENT_SOFT
        tag = card["tag"]
        self.q_title = self.text(x1 + p(18), y1 + p(24), "", size=11, bold=True, tags=(tag,))
        self.q_body = self.text(x1 + p(18), y1 + p(46), "", size=9, color=SUB, tags=(tag,))
        cy = (y1 + y2) / 2
        self.q_yes = self.pill("q_yes", x2 - p(250), cy - p(15), x2 - p(140), cy + p(15), "", lambda: self._act("prompt", {"accept": True}), accent=True)
        self.q_no = self.pill("q_no", x2 - p(130), cy - p(15), x2 - p(18), cy + p(15), "", lambda: self._act("prompt", {"accept": False}))
        for item in (self.q_yes, self.q_no):
            self.c.addtag_withtag(tag, item["tag"])

    def _appear_items(self, x1, y1, x2, y2) -> None:
        p = self.p
        card = self.card("appear", x1, y1, x2, y2)
        tag = card["tag"]
        cy = (y1 + y2) / 2
        size = p(36)
        self.rrect(x1 + p(12), cy - size / 2, x1 + p(12) + size, cy + size / 2, p(10), fill=TILE, outline="", tags=(tag,))
        self.c.create_text(x1 + p(12) + size / 2, cy, text=ICONS["appear"], fill=ACCENT, font=(ICON_FONT, 13), tags=(tag,))
        self.ap_title = self.text(x1 + p(60), cy - p(9), "", size=10, bold=True, tags=(tag,))
        self.ap_sub = self.text(x1 + p(60), cy + p(10), "", size=8, color=SUB, tags=(tag,))
        # A segmented control: one track, the chosen status lit
        sx2 = x2 - p(16)
        sw = p(330)
        sx1 = sx2 - sw
        self.rrect(sx1, cy - p(17), sx2, cy + p(17), p(17), fill="#100f17", outline=CARD_LINE, tags=(tag,))
        self.segments = {}
        seg_w = (sw - p(8)) / 3
        for i, value in enumerate(("online", "offline", "mobile")):
            a = sx1 + p(4) + i * seg_w
            item = self.pill(f"seg_{value}", a, cy - p(13), a + seg_w, cy + p(13), "",
                             lambda v=value: self._act("status", {"value": v}))
            self.c.itemconfig(item["bg"], fill="#100f17")
            item["fill"] = "#100f17"
            item["hover_fill"] = "#1f1d2b"
            self.c.addtag_withtag(tag, item["tag"])
            self.segments[value] = item

    # ---- Spotify page ----

    def _spotify_layout(self) -> None:
        p, c = self.p, self.c
        start = len(c.find_all())
        left, right = p(PAD), self.w - p(PAD)
        width = right - left
        half = (width - p(GAP)) / 2
        y = p(76)
        h = p(62)
        self.sp_status = self.tile("sp_status", left, y, left + half, y + h, "music")
        self.sp_auto = self.tile("sp_auto", right - half, y, right, y + h, "sync", lambda: self._act("spotify_auto"))
        from launcher.lust_spotify import THEMES
        self.sp_keys = list(THEMES)
        self.sp_labels = {key: value[2] for key, value in THEMES.items()}
        self.sp_colors = {key: (value[3], value[4]) for key, value in THEMES.items()}
        self.sp_page = 0
        self.sp_images = {}
        self.sp_loaded = queue.Queue()
        self.sp_loading = False
        y2 = y + h + p(GAP)
        cols, rows = 4, 2
        self.sp_per_page = cols * rows
        box_w = (width - p(36) - (cols - 1) * p(10)) / cols
        img_h = (box_w - p(12)) * 9 / 16
        box_h = img_h + p(40)
        h2 = p(44) + rows * box_h + (rows - 1) * p(10) + p(14)
        self.card("sp_themes", left, y2, right, y2 + h2)
        self.text(left + p(18), y2 + p(20), "Tema", size=9, color=SUB)
        self.pill("sp_prev", right - p(108), y2 + p(9), right - p(78), y2 + p(31), "‹", lambda: self._sp_turn(-1))
        self.sp_pager = self.text(right - p(63), y2 + p(20), "", size=8, color=SUB, anchor="center")
        self.pill("sp_next", right - p(48), y2 + p(9), right - p(18), y2 + p(31), "›", lambda: self._sp_turn(1))
        self.sp_slots = []
        for i in range(self.sp_per_page):
            x1 = left + p(18) + (i % cols) * (box_w + p(10))
            by = y2 + p(40) + (i // cols) * (box_h + p(10))
            box = self.card(f"sp_slot_{i}", x1, by, x1 + box_w, by + box_h,
                            clickable=lambda i=i: self._sp_pick(i), radius=12)
            tag = box["tag"]
            ix1, iy1, ix2, iy2 = x1 + p(6), by + p(6), x1 + box_w - p(6), by + p(6) + img_h
            iw, ih = ix2 - ix1, iy2 - iy1
            # A drawn Spotify window, for themes without a screenshot
            mock = {
                "main": self.rrect(ix1, iy1, ix2, iy2, p(8), outline="", tags=(tag,)),
                "side": c.create_rectangle(ix1 + p(5), iy1 + p(5), ix1 + iw * 0.24, iy2 - p(18), outline="", tags=(tag,)),
                "bar": c.create_rectangle(ix1 + p(5), iy2 - p(14), ix2 - p(5), iy2 - p(5), outline="", tags=(tag,)),
                "cards": [c.create_rectangle(ix1 + iw * (0.29 + 0.235 * n), iy1 + ih * 0.32,
                                             ix1 + iw * (0.29 + 0.235 * n) + iw * 0.2, iy1 + ih * 0.62,
                                             outline="", tags=(tag,)) for n in range(3)],
                "title": c.create_rectangle(ix1 + iw * 0.29, iy1 + ih * 0.12, ix1 + iw * 0.6, iy1 + ih * 0.2,
                                            outline="", tags=(tag,)),
                "play": c.create_oval((ix1 + ix2) / 2 - p(4), iy2 - p(13), (ix1 + ix2) / 2 + p(4), iy2 - p(6),
                                      outline="", tags=(tag,)),
            }
            box["mock"] = mock
            box["image"] = c.create_image(ix1, iy1, anchor="nw", tags=(tag,))
            box["img_size"] = (int(iw), int(ih))
            box["label"] = self.text(x1 + p(12), iy2 + p(17), "", size=9, bold=True, tags=(tag,))
            self.sp_slots.append(box)
        y3 = y2 + h2 + p(GAP)
        self.pill("sp_apply", left, y3, left + half, y3 + p(40), "Temayı uygula", self._apply_theme, accent=True)
        self.pill("sp_restore", right - half, y3, right, y3 + p(40), "Orijinale döndür",
                  lambda: self._act("spotify_apply", {"theme": "original"}))
        self.sp_note = self.text(left, y3 + p(62), "Spicetify ile çalışır. Spotify'ın Microsoft Store sürümü "
                                 "desteklenmez; spotify.com'dan indirilen sürüm gerekir.", size=8, color=FAINT,
                                 width=width)
        for item in c.find_all()[start:]:
            c.addtag_withtag("page-spotify", item)
        c.itemconfig("page-spotify", state="hidden")

    def _choose_theme(self, key: str) -> None:
        self.sp_choice = key
        self._draw_spotify((self.state.value or {}).get("spotify") or {})

    def _apply_theme(self) -> None:
        self._act("spotify_apply", {"theme": self.sp_choice})

    def _sp_page_keys(self) -> list:
        start = self.sp_page * self.sp_per_page
        return self.sp_keys[start:start + self.sp_per_page]

    def _sp_turn(self, step: int) -> None:
        pages = (len(self.sp_keys) + self.sp_per_page - 1) // self.sp_per_page
        self.sp_page = (self.sp_page + step) % pages
        self._draw_slots()

    def _sp_pick(self, index: int) -> None:
        keys = self._sp_page_keys()
        if index < len(keys):
            self._choose_theme(keys[index])

    def _load_previews(self) -> None:
        """Screenshots download in the background; the Tk thread turns them into images."""
        if self.sp_loading:
            return
        self.sp_loading = True

        def run():
            from launcher import lust_spotify
            for key in self.sp_keys:
                path = lust_spotify.preview_path(key)
                if path:
                    self.sp_loaded.put((key, path))
        threading.Thread(target=run, daemon=True, name="LustSpotifyPreviews").start()

    def _take_previews(self) -> None:
        changed = False
        try:
            while True:
                key, path = self.sp_loaded.get_nowait()
                try:
                    from PIL import Image, ImageDraw, ImageTk
                    w, h = self.sp_slots[0]["img_size"]
                    scale = 2
                    with Image.open(path) as image:
                        picture = image.convert("RGB").resize((w * scale, h * scale), Image.LANCZOS)
                    mask = Image.new("L", picture.size, 0)
                    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *picture.size), self.p(8) * scale, fill=255)
                    framed = Image.new("RGB", picture.size, CARD)
                    framed.paste(picture, (0, 0), mask)
                    self.sp_images[key] = ImageTk.PhotoImage(framed.resize((w, h), Image.LANCZOS))
                    changed = True
                except Exception as exc:  # noqa: BLE001 - the drawn preview stays
                    log.debug(f"[Hub] Preview {key} not shown: {exc}")
        except queue.Empty:
            pass
        if changed and self.page == "spotify":
            self._draw_slots()

    def _draw_slots(self) -> None:
        c = self.c
        keys = self._sp_page_keys()
        pages = (len(self.sp_keys) + self.sp_per_page - 1) // self.sp_per_page
        c.itemconfig(self.sp_pager, text=f"{self.sp_page + 1}/{pages}")
        shown = self.page == "spotify"
        for index, box in enumerate(self.sp_slots):
            key = keys[index] if index < len(keys) else None
            self.enabled[f"sp_slot_{index}"] = key is not None
            if not key or not shown:
                c.itemconfig(box["tag"], state="hidden")
                continue
            c.itemconfig(box["tag"], state="normal")
            chosen = key == getattr(self, "sp_choice", None)
            c.itemconfig(box["bg"], outline=ACCENT if chosen else CARD_LINE, width=2 if chosen else 1)
            c.itemconfig(box["label"], text=self.sp_labels[key], fill=TEXT if chosen else SUB)
            image = self.sp_images.get(key)
            mock = box["mock"]
            mock_items = [mock["main"], mock["side"], mock["bar"], mock["title"], mock["play"], *mock["cards"]]
            if image:
                c.itemconfig(box["image"], image=image, state="normal")
                for item in mock_items:
                    c.itemconfig(item, state="hidden")
                continue
            c.itemconfig(box["image"], image="", state="hidden")
            bg, accent = self.sp_colors[key]
            panel = _blend(tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5)), (255, 255, 255), 0.07)
            for item, fill in ((mock["main"], bg), (mock["side"], panel), (mock["bar"], panel),
                               (mock["title"], accent), (mock["play"], accent)):
                c.itemconfig(item, fill=fill, state="normal")
            for item in mock["cards"]:
                c.itemconfig(item, fill=panel, state="normal")

    def _set_page(self, page: str) -> None:
        if page == self.page:
            return
        self.page = page
        self.c.itemconfig("page-lol", state="normal" if page == "lol" else "hidden")
        self.c.itemconfig("page-spotify", state="normal" if page == "spotify" else "hidden")
        self._set_hover(None)
        self._refresh(reschedule=False)

    def _draw_spotify(self, sp: dict) -> None:
        self._load_previews()
        if not getattr(self, "sp_choice", None):
            self.sp_choice = sp.get("theme") or "luminous"
        if sp.get("installed"):
            sub = f"{sp.get('version') or ''} · " + ("Uygulanıyor…" if sp.get("busy") else
                                                     ("Tema: " + self.sp_labels.get(sp.get("theme"), "Orijinal")))
            dot = AMBER if sp.get("busy") else GREEN
        else:
            sub = "Store sürümü desteklenmez" if sp.get("store") else "Bulunamadı"
            dot = RED
        self._tile_set(self.sp_status, "Spotify", sub, dot)
        self._tile_set(self.sp_auto, "Otomatik uygula", "Spotify güncellenince", ACCENT if sp.get("auto") else FAINT)
        self._draw_slots()
        ok = bool(sp.get("installed")) and not sp.get("busy")
        for key in ("sp_apply", "sp_restore"):
            self.enabled[key] = ok

    # ---- interaction ----

    def _key_at(self, x, y) -> Optional[str]:
        for key in reversed(list(self.clickable)):
            card = self.cards.get(key)
            if not card or self.c.itemcget(card["bg"], "state") == "hidden":
                continue
            x1, y1, x2, y2 = card["box"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return key
        return None

    def _motion(self, event) -> None:
        self._set_hover(self._key_at(event.x, event.y))

    def _set_hover(self, key: Optional[str]) -> None:
        if key == self.hover:
            return
        for name in (self.hover, key):
            if name and name in self.cards:
                card = self.cards[name]
                hot = name == key and self.enabled.get(name, True)
                fill = card.get("lit") or (card["hover_fill"] if hot else card["fill"])
                self.c.itemconfig(card["bg"], fill=fill)
        self.hover = key
        self.c.config(cursor="hand2" if key and self.enabled.get(key, True) else "")

    def _click(self, event) -> None:
        key = self._key_at(event.x, event.y)
        if key and self.enabled.get(key, True):
            self.clickable[key]()

    def _act(self, name: str, body: Optional[dict] = None) -> None:
        def run():
            self.hub.run_action(name, body)
            self.state.wake.set()
        threading.Thread(target=run, daemon=True, name=f"LustHub-{name}").start()

    def _update_clicked(self) -> None:
        state = self.state.value or {}
        if state.get("phase") != "ready":
            return
        self._act("update" if state.get("update_available") else "check")

    def _quit_clicked(self) -> None:
        if time.time() - self.quit_armed < 3:
            self._act("quit")
            return
        self.quit_armed = time.time()
        self._refresh(reschedule=False)
        self.root.after(3100, lambda: self._refresh(reschedule=False))

    def _ago(self, seconds) -> str:
        if not seconds:
            return self.t("never")
        minutes = int((time.time() - seconds) // 60)
        return self.t("just_now") if minutes < 1 else self.t("min_ago", n=minutes)

    # ---- showing ----

    def reveal(self) -> None:
        global _visible
        root = self.root
        root.deiconify()
        # Never jump over a match: during one the window opens behind the game
        if not _in_game():
            root.lift()
            root.attributes("-topmost", True)
            root.after(300, lambda: root.attributes("-topmost", False))
            root.focus_force()
        _visible = True
        self.state.wake.set()
        root.after(50, self._dark_title_bar)

    def hide(self) -> None:
        global _visible
        _visible = False
        self.root.withdraw()

    def _dark_title_bar(self) -> None:
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            value = ctypes.c_int(1)
            for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (19 before Windows 10 20H1)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value),
                                                              ctypes.sizeof(value)) == 0:
                    break
        except (AttributeError, OSError):
            pass

    def _poll_commands(self) -> None:
        try:
            while True:
                if _commands.get_nowait() == "show":
                    self.reveal()
        except queue.Empty:
            pass
        self._take_previews()
        self.root.after(100, self._poll_commands)

    # ---- state ----

    def _animate(self) -> None:
        x1, y1, x2, y2 = self.bar
        width = x2 - x1
        if self.c.itemcget(self.bar_fill, "state") != "hidden":
            if self.progress_value is None:
                self.busy_pos = (self.busy_pos + 0.015) % 1.3
                a = x1 + (self.busy_pos - 0.3) * width
                b = a + 0.3 * width
                a, b = max(x1, a), min(x2, b)
            else:
                a, b = x1, x1 + max(self.p(6), width * self.progress_value / 100)
            self._move_rrect(self.bar_fill, a, y1, max(a + 1, b), y2, self.p(3))
        self.root.after(30, self._animate)

    def _move_rrect(self, item, x1, y1, x2, y2, r) -> None:
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        self.c.coords(item, x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                      x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1)

    def _show_card(self, key: str, on: bool) -> None:
        self.c.itemconfig(self.cards[key]["tag"], state="normal" if on else "hidden")

    def _tile_set(self, card, title, sub, dot=None, enabled=True, key=None) -> None:
        self.c.itemconfig(card["title"], text=title,
                          fill=(RED if card.get("danger") else TEXT) if enabled else FAINT)
        self.c.itemconfig(card["sub"], text=sub)
        self.c.itemconfig(card["dot"], fill=dot or "", state="normal" if dot else "hidden")
        self.c.itemconfig(card["icon"], fill=(RED if card.get("danger") else ACCENT) if enabled else FAINT)
        if key:
            self.enabled[key] = enabled

    def _refresh(self, reschedule: bool = True) -> None:
        try:
            state = self.state.value
            if state:
                self._draw(state)
        except Exception as exc:  # noqa: BLE001 - keep the window alive
            log.debug(f"[Hub] Draw failed: {exc}")
        if reschedule:
            self.root.after(REFRESH_MS, self._refresh)

    def _draw(self, s: dict) -> None:
        c = self.c
        self._draw_toast(s)
        for key, item in (("lol", self.tab_lol), ("spotify", self.tab_spotify)):
            lit = key == self.page
            item["lit"] = ACCENT_SOFT if lit else None
            c.itemconfig(item["bg"], fill=ACCENT_SOFT if lit else item["fill"],
                         outline=ACCENT_LINE if lit else "")
            c.itemconfig(item["label"], fill="#c4b5fd" if lit else SUB)
        if self.page == "spotify" and s.get("prompt"):
            self._set_page("lol")  # the update question is on the LoL page
            return
        if self.page == "spotify":
            ready_all = s["running"] and s["ready"]
            c.itemconfig(self.status_dot, fill=GREEN if ready_all else AMBER)
            c.itemconfig(self.status_text, text=self.t("status_ready" if ready_all else "status_starting"))
            self._draw_spotify(s.get("spotify") or {})
            return
        if s.get("lang") and s["lang"] != self.lang:
            self.lang = s["lang"]
            c.itemconfig(self.hint, text=self.t("client_hint"))
        starting = s.get("phase") != "ready"
        ready_all = s["running"] and s["ready"]
        c.itemconfig(self.status_dot, fill=GREEN if ready_all else AMBER)
        c.itemconfig(self.status_text, text=self.t("status_ready" if ready_all else "status_starting"))

        self._tile_set(self.t_lust, self.t("lust"), self.t("running" if s["running"] else "starting"),
                       GREEN if s["running"] else AMBER)
        self._tile_set(self.t_league, self.t("league"), self.t("league_on" if s["league"] else "league_off"),
                       GREEN if s["league"] else FAINT)
        self._tile_set(self.t_skins, self.t("skins"), self.t("ready" if s["ready"] else "not_ready"),
                       GREEN if s["ready"] else AMBER)

        prompt = s.get("prompt")
        self._show_card("prompt", bool(prompt))
        self._show_card("progress", starting and not prompt)
        self._show_card("appear", not starting and not prompt)
        for key, on in (("q_yes", bool(prompt)), ("q_no", bool(prompt))):
            self.enabled[key] = on
        for value in self.segments:
            self.enabled[f"seg_{value}"] = not starting and not prompt
        if prompt:
            c.itemconfig(self.q_title, text=self.t("prompt_title", v=prompt["version"]))
            c.itemconfig(self.q_body, text=self.t("prompt_body", c=prompt["current"]))
            c.itemconfig(self.q_yes["label"], text=self.t("install"))
            c.itemconfig(self.q_no["label"], text=self.t("later"))
        elif starting:
            c.itemconfig(self.p_status, text=s.get("status") or s.get("detail") or "")
            c.itemconfig(self.p_detail, text=s.get("transfer") or (s.get("detail") if s.get("status") else ""))
            progress = s.get("progress")
            self.progress_value = None if progress is None else int(progress)
            c.itemconfig(self.p_pct, text="" if progress is None else f"%{int(progress)}")
        else:
            offline = s.get("offline") or {}
            running = bool(offline.get("running"))
            c.itemconfig(self.ap_title, text=self.t("appear"))
            c.itemconfig(self.ap_sub, text=self.t(offline.get("status") or "online") if running else self.t("offline_hint"))
            for value, item in self.segments.items():
                lit = running and offline.get("status") == value
                item["lit"] = ACCENT if lit else None
                c.itemconfig(item["bg"], fill=ACCENT if lit else item["fill"])
                c.itemconfig(item["label"], text=self.t(value),
                             fill="#15111f" if lit else (TEXT if running else FAINT))
                self.enabled[f"seg_{value}"] = running

        self._tile_set(self.a_league, self.t("league_open" if s["league"] else "open_league"),
                       self.t("start_league"), None, enabled=not s["league"], key="a_league")
        self._tile_set(self.a_mods, self.t("mods"), self.t("mods_sub"))
        self._tile_set(self.a_log, self.t("log"), self.t("log_sub"))
        self._tile_set(self.a_auto, self.t("autostart"), self.t("on" if s["autostart"] else "off"),
                       ACCENT if s["autostart"] else FAINT)
        self._tile_set(self.a_restart, self.t("restart"), self.t("restart_sub"), enabled=s["running"], key="a_restart")
        armed = time.time() - self.quit_armed < 3
        self._tile_set(self.a_quit, self.t("quit_confirm" if armed else "quit"), self.t("quit_sub"))

        if s["update_available"]:
            sub = self.t("new_version", v=s["latest"])
            c.itemconfig(self.v_button_icon, text=ICONS["download"])
        else:
            sub = f"{self.t('up_to_date')} · {self.t('checked', when=self._ago(s.get('checked_at')))}"
            c.itemconfig(self.v_button_icon, text=ICONS["sync"])
        c.itemconfig(self.v_sub, text=sub, fill=ACCENT if s["update_available"] else SUB)
        self.enabled["v_button"] = not starting
        c.itemconfig(self.v_button, fill=ACCENT if not starting else "#3a3550")
        items = (s.get("news") or {}).get("items") or []
        c.itemconfig(self.v_news, text="\n".join(f"•  {item}" for item in items[:3]))

    def _draw_toast(self, s: dict) -> None:
        toast = s.get("toast")
        if toast and toast.get("id") != self.toast_id:
            first = self.toast_id is None
            self.toast_id = toast.get("id")
            if not first:
                self._show_toast(toast.get("text", ""))
        elif self.toast_id is None:
            self.toast_id = 0

    def _show_toast(self, text: str) -> None:
        c, p = self.c, self.p
        c.itemconfig(self.toast_text, text=text, state="normal")
        c.coords(self.toast_text, self.w / 2, self.h - p(42))
        x1, y1, x2, y2 = c.bbox(self.toast_text)
        self._move_rrect(self.toast_bg, x1 - p(16), y1 - p(9), x2 + p(16), y2 + p(9), p(16))
        c.itemconfig(self.toast_bg, state="normal")
        c.tag_raise(self.toast_bg)
        c.tag_raise(self.toast_text)
        if self.toast_after:
            self.root.after_cancel(self.toast_after)

        def hide():
            c.itemconfig(self.toast_bg, state="hidden")
            c.itemconfig(self.toast_text, state="hidden")
        self.toast_after = self.root.after(3500, hide)
