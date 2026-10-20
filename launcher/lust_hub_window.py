"""The desktop hub's window: Lust's own Tkinter window, no browser.

It runs on its own thread (Tk is touched only there) and shows what launcher/lust_hub.py
holds: startup progress, Lust's and League's status, the version, what's new, and the
quick actions. Closing it only hides it; the tray icon brings it back.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import time
from typing import Callable, Optional

from utils.core.logging import get_logger

log = get_logger()

BG = "#0b0e14"
PANEL = "#0f131b"
LINE = "#1e2328"
HOVER = "#151a22"
RAISED = "#1e2328"
GOLD_DIM = "#785a28"
TEXT_COLOR = "#cdbe91"
BRIGHT = "#f0e6d2"
MUTED = "#7a7568"
PURPLE = "#a78bfa"
PURPLE_BG = "#211c33"
GREEN = "#0acf83"
YELLOW = "#f2c94c"
AMBER = "#e8a33a"
RED = "#e07a7a"
RED_LINE = "#5a2a2a"
RED_BG = "#2a1416"

SIZE = (780, 630)
FONT = "Segoe UI"
ICON_FONT = "Segoe MDL2 Assets"  # ships with Windows 10 and 11
ICONS = {"play": "", "folder": "", "log": "", "power": "",
         "restart": "", "close": ""}
REFRESH_MS = 500
STATE_INTERVAL_S = 0.5

TEXT = {
    "en": {
        "status": "Status", "running": "Lust is running", "starting": "Lust is starting",
        "league_on": "League is open", "league_off": "League is closed",
        "ready": "Skins ready", "not_ready": "Skins getting ready",
        "version": "Version", "up_to_date": "Up to date", "new_version": "New version",
        "checked": "Last checked", "never": "not yet", "check": "Check now", "update": "Update",
        "whats_new": "What's new", "actions": "Quick actions",
        "open_league": "Open League", "league_open": "League is open",
        "appear": "Appear as", "online": "Online", "offline": "Offline", "mobile": "Mobile",
        "offline_hint": "Open League from here to choose your status",
        "mods": "Open mods folder", "log": "Copy log", "autostart": "Start with Windows",
        "on": "On", "off": "Off", "restart": "Restart Lust", "quit": "Close Lust",
        "quit_confirm": "Click again to close Lust",
        "client_hint": "Set your game settings by clicking the LUST tab in the LoL client.",
        "prompt_title": "Lust {v} is ready to install", "prompt_body": "You have {c}. Install it now?",
        "install": "Install", "later": "Not now", "just_now": "just now", "min_ago": "{n} min ago",
    },
    "tr": {
        "status": "Durum", "running": "Lust çalışıyor", "starting": "Lust başlıyor",
        "league_on": "League açık", "league_off": "League kapalı",
        "ready": "Skinler hazır", "not_ready": "Skinler hazırlanıyor",
        "version": "Sürüm", "up_to_date": "Güncel", "new_version": "Yeni sürüm",
        "checked": "Son kontrol", "never": "henüz yok", "check": "Şimdi kontrol et", "update": "Güncelle",
        "whats_new": "Yenilikler", "actions": "Hızlı işlemler",
        "open_league": "League'i aç", "league_open": "League açık",
        "appear": "Görün", "online": "Çevrimiçi", "offline": "Çevrimdışı", "mobile": "Mobil",
        "offline_hint": "Durum seçmek için League'i buradan aç",
        "mods": "Mod klasörünü aç", "log": "Logu kopyala", "autostart": "Windows ile başlat",
        "on": "Açık", "off": "Kapalı", "restart": "Lust'ı yeniden başlat", "quit": "Lust'ı kapat",
        "quit_confirm": "Kapatmak için tekrar tıkla",
        "client_hint": "Oyun ayarlarınızı LoL istemcisindeki LUST sekmesine tıklayarak ayarlayabilirsiniz.",
        "prompt_title": "Lust {v} kurulmaya hazır", "prompt_body": "Sendeki sürüm {c}. Şimdi kurulsun mu?",
        "install": "Kur", "later": "Şimdi değil", "just_now": "az önce", "min_ago": "{n} dk önce",
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


class Button:
    """A flat button (a frame with an icon, a text and an optional value at the end)."""

    STYLES = {
        "normal": {"bg": BG, "fg": TEXT_COLOR, "line": LINE, "hover_bg": HOVER, "hover_fg": BRIGHT,
                   "hover_line": GOLD_DIM, "icon": TEXT_COLOR},
        "primary": {"bg": RAISED, "fg": TEXT_COLOR, "line": GOLD_DIM, "hover_bg": "#232a33",
                    "hover_fg": BRIGHT, "hover_line": GOLD_DIM, "icon": PURPLE},
        "danger": {"bg": BG, "fg": RED, "line": RED_LINE, "hover_bg": RED_BG, "hover_fg": RED,
                   "hover_line": RED, "icon": RED},
        "chip": {"bg": PANEL, "fg": TEXT_COLOR, "line": LINE, "hover_bg": HOVER, "hover_fg": BRIGHT,
                 "hover_line": GOLD_DIM, "icon": TEXT_COLOR},
    }

    def __init__(self, parent, command: Callable[[], None], icon: str = "", style: str = "normal",
                 chip: bool = False) -> None:
        import tkinter as tk
        self.style = dict(self.STYLES[style])
        self.command = command
        self.enabled = True
        self.selected = False
        self.hover = False
        pad = (10, 4) if chip else (12, 8)
        self.frame = tk.Frame(parent, highlightthickness=1, cursor="hand2")
        self.icon = tk.Label(self.frame, text=ICONS.get(icon, ""), font=(ICON_FONT, 10)) if icon else None
        if self.icon:
            self.icon.pack(side="left", padx=(pad[0], 0), pady=pad[1])
        self.label = tk.Label(self.frame, font=(FONT, 9 if chip else 10), anchor="w")
        self.label.pack(side="left", padx=(8 if icon else pad[0], pad[0]), pady=pad[1],
                        fill="x", expand=not chip)
        self.end = tk.Label(self.frame, font=(FONT, 9))
        for widget in (self.frame, self.label, self.end, *( [self.icon] if self.icon else [])):
            widget.bind("<Enter>", lambda _e: self._hover(True))
            widget.bind("<Leave>", lambda _e: self._hover(False))
            widget.bind("<Button-1>", lambda _e: self._click())
        self._paint()

    def _hover(self, on: bool) -> None:
        self.hover = on
        self._paint()

    def _click(self) -> None:
        if self.enabled:
            self.command()

    def set(self, text: str, enabled: bool = True, end: Optional[str] = None,
            end_on: bool = False, selected: bool = False) -> None:
        if self.label.cget("text") != text:
            self.label.config(text=text)
        if end is None:
            self.end.pack_forget()
        else:
            if not self.end.winfo_ismapped():
                self.end.pack(side="right", padx=(0, 12))
            self.end.config(text=end, fg=PURPLE if end_on else MUTED)
        if (enabled, selected) != (self.enabled, self.selected):
            self.enabled, self.selected = enabled, selected
            self.frame.config(cursor="hand2" if enabled else "arrow")
        self._paint()

    def _paint(self) -> None:
        s = self.style
        hot = self.hover and self.enabled
        bg = PURPLE_BG if self.selected else (s["hover_bg"] if hot else s["bg"])
        fg = BRIGHT if self.selected else (MUTED if not self.enabled else (s["hover_fg"] if hot else s["fg"]))
        line = PURPLE if self.selected else (s["hover_line"] if hot else s["line"])
        self.frame.config(bg=bg, highlightbackground=line, highlightcolor=line)
        self.label.config(bg=bg, fg=fg)
        self.end.config(bg=bg)
        if self.icon:
            self.icon.config(bg=bg, fg=MUTED if not self.enabled else s["icon"])


class HubWindow:
    def __init__(self) -> None:
        import tkinter as tk
        from config import APP_VERSION
        from launcher import lust_hub

        self.tk = tk
        self.hub = lust_hub
        self.state = _State()
        self.lang = lust_hub.LANG
        self.texts: list = []  # (widget, key) re-labelled when the language changes
        self.quit_armed = 0.0
        self.toast_id = None
        self.toast_after = None
        self.busy_pos = 0.0
        self.news_key = None
        self.progress_value: Optional[int] = None

        root = self.root = tk.Tk()
        root.withdraw()
        root.title("Lust")
        root.configure(bg=BG)
        root.resizable(False, False)
        scale = max(1.0, root.winfo_fpixels("1i") / 96)
        self.scale = scale
        width, height = int(SIZE[0] * scale), int(SIZE[1] * scale)
        x = (root.winfo_screenwidth() - width) // 2
        y = (root.winfo_screenheight() - height) // 2
        root.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        try:
            from utils.core.paths import get_asset_path
            root.iconbitmap(default=str(get_asset_path("icon.ico")))
        except Exception:  # noqa: BLE001 - Tk's own icon then
            pass
        root.protocol("WM_DELETE_WINDOW", self.hide)

        tk.Frame(root, bg=PURPLE, height=2).pack(fill="x")
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=20, pady=(12, 10))
        tk.Label(header, text="LUST", bg=BG, fg=PURPLE, font=("Georgia", 17, "bold")).pack(side="left")
        tk.Label(header, text=f"  {APP_VERSION}", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left", pady=(6, 0))
        tk.Frame(root, bg=LINE, height=1).pack(fill="x")
        # Where the game settings are: the client's LUST tab, not this window
        hint = self.tk.Label(root, bg=BG, fg=YELLOW, font=(FONT, 11, "bold"), anchor="w",
                             wraplength=int((SIZE[0] - 40) * scale), justify="left")
        hint.pack(fill="x", padx=20, pady=(12, 0))
        self.texts.append((hint, "client_hint"))

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=5, uniform="col")
        body.columnconfigure(1, weight=4, uniform="col")
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        # Update prompt (only while the launcher asks)
        self.prompt = self._card(left, line=PURPLE)
        self.prompt.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.prompt_title = tk.Label(self.prompt, bg=PANEL, fg=BRIGHT, font=(FONT, 10), anchor="w")
        self.prompt_title.pack(fill="x")
        self.prompt_body = tk.Label(self.prompt, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w")
        self.prompt_body.pack(fill="x")
        buttons = tk.Frame(self.prompt, bg=PANEL)
        buttons.pack(anchor="w", pady=(8, 0))
        self.prompt_yes = Button(buttons, lambda: self._act("prompt", {"accept": True}), style="primary", chip=True)
        self.prompt_yes.frame.pack(side="left")
        self.prompt_no = Button(buttons, lambda: self._act("prompt", {"accept": False}), style="chip", chip=True)
        self.prompt_no.frame.pack(side="left", padx=(8, 0))
        self.prompt.grid_remove()

        # Status
        status = self._card(left)
        status.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._label(status, "status", small=True).pack(anchor="w", pady=(0, 6))
        self.dots = {}
        for key in ("run", "league", "ready"):
            row = tk.Frame(status, bg=PANEL)
            row.pack(fill="x", pady=1)
            dot = tk.Canvas(row, width=10, height=10, bg=PANEL, highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=MUTED, outline="", tags="dot")
            dot.pack(side="left", padx=(0, 8))
            text = tk.Label(row, bg=PANEL, fg=TEXT_COLOR, font=(FONT, 10), anchor="w")
            text.pack(side="left")
            self.dots[key] = (dot, text)

        # Startup progress
        self.progress = self._card(left)
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        line = tk.Frame(self.progress, bg=PANEL)
        line.pack(fill="x")
        self.p_status = tk.Label(line, bg=PANEL, fg=TEXT_COLOR, font=(FONT, 10), anchor="w")
        self.p_status.pack(side="left")
        self.p_pct = tk.Label(line, bg=PANEL, fg=PURPLE, font=(FONT, 10))
        self.p_pct.pack(side="right")
        self.bar = tk.Canvas(self.progress, height=int(6 * scale), bg=LINE, highlightthickness=0)
        self.bar.pack(fill="x", pady=(8, 6))
        self.bar.create_rectangle(0, 0, 0, 0, fill=PURPLE, outline="", tags="fill")
        self.p_detail = tk.Label(self.progress, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w")
        self.p_detail.pack(fill="x")

        # Version
        version = self._card(left)
        version.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        line = tk.Frame(version, bg=PANEL)
        line.pack(fill="x")
        self._label(line, "version").pack(side="left")
        self.u_state = tk.Label(line, bg=PANEL, fg=GREEN, font=(FONT, 9))
        self.u_state.pack(side="right")
        line = tk.Frame(version, bg=PANEL)
        line.pack(fill="x", pady=(6, 0))
        self.u_checked = tk.Label(line, bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.u_checked.pack(side="left")
        self.u_button = tk.Label(line, bg=PANEL, fg=PURPLE, font=(FONT, 9), cursor="hand2")
        self.u_button.pack(side="right")
        self.u_button.bind("<Button-1>", lambda _e: self._update_clicked())
        self.u_button.bind("<Enter>", lambda _e: self.u_button.config(fg=BRIGHT))
        self.u_button.bind("<Leave>", lambda _e: self.u_button.config(fg=PURPLE))

        # What's new
        news = self.news_card = self._card(left)
        news.grid(row=4, column=0, sticky="nsew")
        left.rowconfigure(4, weight=1)
        self._label(news, "whats_new", small=True).pack(anchor="w", pady=(0, 6))
        self.news = tk.Frame(news, bg=PANEL)
        self.news.pack(fill="both", expand=True)

        # Quick actions
        self._label(right, "actions", small=True, bg=BG).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.b_league = Button(right, lambda: self._act("league"), icon="play", style="primary")
        self.b_league.frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        appear = self._card(right, pad=(12, 8))
        appear.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self._label(appear, "appear", small=True).pack(anchor="w")
        chips = tk.Frame(appear, bg=PANEL)
        chips.pack(anchor="w", pady=(6, 0))
        self.chips = {}
        for value in ("online", "offline", "mobile"):
            chip = Button(chips, lambda v=value: self._act("status", {"value": v}), style="chip", chip=True)
            chip.frame.pack(side="left", padx=(0, 6))
            self.chips[value] = chip
        self.offline_hint = self._label(appear, "offline_hint", small=True)
        self.b_mods = Button(right, lambda: self._act("mods"), icon="folder")
        self.b_mods.frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.b_log = Button(right, lambda: self._act("log"), icon="log")
        self.b_log.frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        self.b_autostart = Button(right, lambda: self._act("autostart"), icon="power")
        self.b_autostart.frame.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        self.b_restart = Button(right, lambda: self._act("restart"), icon="restart")
        self.b_restart.frame.grid(row=6, column=0, sticky="ew")
        right.rowconfigure(7, weight=1)
        self.b_quit = Button(right, self._quit_clicked, icon="close", style="danger")
        self.b_quit.frame.grid(row=8, column=0, sticky="ew")

        self.toast = tk.Label(root, bg=RAISED, fg=BRIGHT, font=(FONT, 9), padx=14, pady=8,
                              highlightthickness=1, highlightbackground=GOLD_DIM,
                              wraplength=int(600 * scale))

        self._relabel()
        self._refresh()
        self._poll_commands()
        self._animate()
        self.reveal()

    # ---- helpers ----

    def _card(self, parent, line: str = LINE, pad=(14, 12)):
        return self.tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=line,
                             highlightcolor=line, padx=pad[0], pady=pad[1])

    def _label(self, parent, key: str, small: bool = False, bg: str = PANEL):
        label = self.tk.Label(parent, bg=bg, fg=MUTED if small else TEXT_COLOR,
                              font=(FONT, 9 if small else 10), anchor="w")
        self.texts.append((label, key))
        return label

    def t(self, key: str, **values) -> str:
        text = TEXT.get(self.lang, TEXT["en"]).get(key, key)
        for name, value in values.items():
            text = text.replace("{" + name + "}", str(value))
        return text

    def _relabel(self) -> None:
        for widget, key in self.texts:
            widget.config(text=self.t(key))

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

    def _ago(self, seconds: int) -> str:
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
        self.root.after(100, self._poll_commands)

    # ---- drawing ----

    def _animate(self) -> None:
        width = self.bar.winfo_width()
        if self.progress_value is None and width > 1:
            self.busy_pos = (self.busy_pos + 0.02) % 1.3
            start = (self.busy_pos - 0.3) * width
            self.bar.coords("fill", start, 0, start + 0.3 * width, self.bar.winfo_height())
        elif width > 1:
            self.bar.coords("fill", 0, 0, width * self.progress_value / 100, self.bar.winfo_height())
        self.root.after(30, self._animate)

    def _dot(self, key: str, text: str, color: str) -> None:
        dot, label = self.dots[key]
        dot.itemconfig("dot", fill=color)
        label.config(text=text)

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
        if s.get("lang") and s["lang"] != self.lang:
            self.lang = s["lang"]
            self._relabel()
            self.news_key = None
        starting = s.get("phase") != "ready"
        self._dot("run", self.t("running" if s["running"] else "starting"), GREEN if s["running"] else AMBER)
        self._dot("league", self.t("league_on" if s["league"] else "league_off"), GREEN if s["league"] else MUTED)
        self._dot("ready", self.t("ready" if s["ready"] else "not_ready"), GREEN if s["ready"] else AMBER)

        if starting:
            self.progress.grid()
            self.p_status.config(text=s.get("status") or s.get("detail") or "")
            self.p_detail.config(text=s.get("transfer") or (s.get("detail") if s.get("status") else ""))
            progress = s.get("progress")
            self.progress_value = None if progress is None else int(progress)
            self.p_pct.config(text="" if progress is None else f"%{int(progress)}")
        else:
            self.progress.grid_remove()

        if s["update_available"]:
            self.u_state.config(text=f"{self.t('new_version')}: {s['latest']}", fg=PURPLE)
        else:
            self.u_state.config(text=self.t("up_to_date"), fg=GREEN)
        self.u_checked.config(text=f"{self.t('checked')}: {self._ago(s.get('checked_at'))}")
        self.u_button.config(text="" if starting else self.t("update" if s["update_available"] else "check"))

        news = s.get("news") or {}
        key = (self.lang, tuple(news.get("items") or []))
        if key != self.news_key:
            self.news_key = key
            for child in self.news.winfo_children():
                child.destroy()
            wrap = int(self.news.winfo_width() or 320 * self.scale) - 24
            for item in (news.get("items") or [])[:3]:
                row = self.tk.Frame(self.news, bg=PANEL)
                row.pack(fill="x", pady=1)
                self.tk.Label(row, text="•", bg=PANEL, fg=GOLD_DIM, font=(FONT, 10)).pack(side="left", anchor="n")
                self.tk.Label(row, text=item, bg=PANEL, fg=TEXT_COLOR, font=(FONT, 9), justify="left",
                              anchor="w", wraplength=max(200, wrap)).pack(side="left", padx=(6, 0), fill="x")

        prompt = s.get("prompt")
        if prompt:
            self.prompt.grid()
            self.prompt_title.config(text=self.t("prompt_title", v=prompt["version"]))
            self.prompt_body.config(text=self.t("prompt_body", c=prompt["current"]))
            self.prompt_yes.set(self.t("install"))
            self.prompt_no.set(self.t("later"))
            self.news_card.grid_remove()  # room for the question
        else:
            self.prompt.grid_remove()
            self.news_card.grid()

        self.b_league.set(self.t("league_open" if s["league"] else "open_league"), enabled=not s["league"])
        offline = s.get("offline") or {}
        for value, chip in self.chips.items():
            chip.set(self.t(value), enabled=bool(offline.get("running")),
                     selected=bool(offline.get("running")) and offline.get("status") == value)
        if offline.get("running"):
            self.offline_hint.pack_forget()
        elif not self.offline_hint.winfo_ismapped():
            self.offline_hint.pack(anchor="w", pady=(6, 0))
        self.b_mods.set(self.t("mods"))
        self.b_log.set(self.t("log"))
        self.b_autostart.set(self.t("autostart"), end=self.t("on" if s["autostart"] else "off"), end_on=s["autostart"])
        self.b_restart.set(self.t("restart"), enabled=s["running"])
        self.b_quit.set(self.t("quit_confirm" if time.time() - self.quit_armed < 3 else "quit"))

        toast = s.get("toast")
        if toast and toast.get("id") != self.toast_id:
            first = self.toast_id is None
            self.toast_id = toast.get("id")
            if not first:
                self._show_toast(toast.get("text", ""))
        elif self.toast_id is None:
            self.toast_id = 0

    def _show_toast(self, text: str) -> None:
        self.toast.config(text=text)
        self.toast.place(relx=0.5, rely=1.0, y=-16, anchor="s")
        self.toast.lift()
        if self.toast_after:
            self.root.after_cancel(self.toast_after)
        self.toast_after = self.root.after(3500, self.toast.place_forget)
