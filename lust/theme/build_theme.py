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

ADD_WALLPAPER_JS = '''    const addBg = this.createElementWithId("div", "add-bg");
    addBg.textContent = "+";
    addBg.title = "Add wallpaper";
    const addBgName = this.createElementWithId("input", "add-bg-name");
    addBgName.type = "text";
    addBgName.placeholder = "Paste the file, type its name";
    addBgName.hidden = true;
    wallpaperControls.append(addBg, addBgName);
    addBg.addEventListener("click", () => {
      window.openPluginsFolder(`${ElainaData.get("Plugin-folder-name")}/assets/backgrounds/wallpapers`);
      addBgName.hidden = false;
      addBgName.focus();
    });
    addBgName.addEventListener("keydown", async (event) => {
      event.stopPropagation();
      if (event.key === "Escape") {
        addBgName.hidden = true;
        return;
      }
      if (event.key !== "Enter")
        return;
      const name = addBgName.value.trim();
      const fail = (message) => {
        addBgName.value = "";
        addBgName.placeholder = message;
      };
      if (!fileRegex.Wallpaper.test(name.toLowerCase()) || /[\\\\/:*?"<>|]/.test(name))
        return fail("Not a video or image file name");
      const controller = new AbortController();
      const res = await fetch(`//plugins/${getThemeName()}/assets/backgrounds/wallpapers/${encodeURIComponent(name)}`, { signal: controller.signal }).catch(() => null);
      controller.abort();
      if (!res || !res.ok)
        return fail(`${name} is not in the folder`);
      const list = ElainaData.get("Wallpaper-list");
      if (!list.includes(name)) {
        list.push(name);
        ElainaData.set("Wallpaper-list", list);
        const option = document.createElement("lol-uikit-dropdown-option");
        option.setAttribute("slot", "lol-uikit-dropdown-option");
        option.innerText = name;
        option.onclick = async () => {
          document.getElementById("elaina-bg").classList.add("webm-hidden");
          document.getElementById("elaina-static-bg").classList.add("webm-hidden");
          ElainaData.set("wallpaper-index", ElainaData.get("Wallpaper-list").indexOf(name));
          await wallpaperController.changeBG(name);
        };
        bgDropdown.appendChild(option);
      }
      bgDropdown.querySelectorAll("lol-uikit-dropdown-option").forEach((option) => {
        option.toggleAttribute("selected", option.innerText === name);
      });
      document.getElementById("elaina-bg").classList.add("webm-hidden");
      document.getElementById("elaina-static-bg").classList.add("webm-hidden");
      ElainaData.set("wallpaper-index", list.indexOf(name));
      await wallpaperController.changeBG(name);
      addBgName.value = "";
      addBgName.placeholder = "Paste the file, type its name";
      addBgName.hidden = true;
    });
'''

ADD_WALLPAPER_CSS = '''#add-bg {
    position: relative !important;
    width: 21px !important;
    height: 21px !important;
    margin-left: 7px;
    margin-top: 11px;
    border: 2px solid #8c8263 !important;
    border-radius: 50% !important;
    background-color: black !important;
    color: #cdbe91;
    font: bold 17px/21px sans-serif;
    text-align: center;
    cursor: pointer;
    pointer-events: auto;
}

#add-bg:hover {
    color: #f0e6d2;
    border-color: #c8aa6e !important;
}

#add-bg-name {
    width: 190px;
    height: 23px;
    margin-left: 7px;
    margin-top: 10px;
    padding: 0 6px;
    background: #010a13e6;
    border: 1px solid #785a28;
    color: #f0e6d2;
    font-size: 12px;
    pointer-events: auto;
}

#add-bg-name[hidden] {
    display: none;
}

#bg-size-hint {
    margin-top: 4px;
    color: #a09b8c;
    font-size: 11px;
    letter-spacing: 0.5px;
}

'''

LUST_PANEL_JS = '''function Settings(context) {
  ElainaData.set("settingsChangenumber", 0);
  mountLustPanelTabs();
  applyLustColors();
}

// Lust: the Lust panel (the LUST item in the top navigation) opens on CUSTOMIZE,
// the hub for status, colors, theme and plugin settings. LUST keeps Rose's own.
const LUST_PANEL_TABS = [
  { id: "customize", label: "CUSTOMIZE", render: customizeSettings, className: "customize_settings" },
  // Drawn by the LUST-LobbyReveal plugin
  { id: "reveal", label: "LOBBY REVEAL", className: "reveal_settings", reload: false,
    render: async (view) => window.LustReveal && window.LustReveal.renderHub(view) },
  { id: "lust", label: "LUST" }
];

// Lust Offline (lust/offline) takes commands as chat messages to its "Lust Active!" friend.
const LUST_OFFLINE_ID = "41c322a1-b328-495b-a004-5ccd3e45eae8@eu1.pvp.net";
const LUST_OFFLINE_STATUSES = [
  { command: "online", label: "Online" },
  { command: "offline", label: "Offline" },
  { command: "mobile", label: "Mobile" }
];
async function lustOfflineRunning() {
  try {
    const friends = await (await fetch("/lol-chat/v1/friends")).json();
    return friends.some((friend) => String(friend.pid || friend.id || "").startsWith(LUST_OFFLINE_ID.split("@")[0]));
  } catch {
    return false;
  }
}
async function lustOfflineStatus() {
  try {
    const messages = await (await fetch(`/lol-chat/v1/conversations/${encodeURIComponent(LUST_OFFLINE_ID)}/messages`)).json();
    for (const message of [...messages].reverse()) {
      const match = /appearing (online|offline|mobile)/i.exec(message.body || "");
      if (match)
        return match[1].toLowerCase();
    }
  } catch {}
  return "";
}
async function sendLustOffline(command) {
  const url = `/lol-chat/v1/conversations/${encodeURIComponent(LUST_OFFLINE_ID)}/messages`;
  const post = () => fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body: command, type: "chat" })
  });
  let response = await post();
  if (!response.ok) {
    await fetch("/lol-chat/v1/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: LUST_OFFLINE_ID, type: "chat" })
    }).catch(() => {});
    response = await post();
  }
  return response.ok;
}
function lustSection(view, title) {
  const section = document.createElement("div");
  section.className = "lust-hub-section";
  const heading = document.createElement("div");
  heading.className = "lust-hub-title";
  heading.textContent = title;
  // The theme's settings prepend into the box they get, so that box is below the title.
  const body = document.createElement("div");
  section.append(heading, body);
  view.appendChild(section);
  return body;
}
async function statusSection(section) {
  const row = document.createElement("div");
  row.className = "lust-status-row";
  const note = document.createElement("div");
  note.className = "lust-customize-state";
  section.append(row, note);
  if (!await lustOfflineRunning()) {
    note.textContent = "Lust Offline isn't running: restart League from Lust to appear offline.";
    return;
  }
  let current = await lustOfflineStatus() || localStorage.getItem("lust-offline-status") || "offline";
  const buttons = LUST_OFFLINE_STATUSES.map(({ command, label }) => {
    const button = document.createElement("lol-uikit-flat-button");
    button.textContent = label;
    button.addEventListener("click", async () => {
      if (!await sendLustOffline(command)) {
        note.textContent = "Couldn't reach Lust Offline.";
        return;
      }
      current = command;
      try {
        localStorage.setItem("lust-offline-status", command);
      } catch {}
      show();
    });
    row.appendChild(button);
    return { command, button };
  });
  const show = () => {
    buttons.forEach(({ command, button }) => button.classList.toggle("lust-status-active", command === current));
    note.textContent = `Friends see you as ${current}.`;
  };
  show();
}

// Text colors players pick in the CUSTOMIZE tab. Empty means League's own color.
const LUST_COLORS = [
  { key: "lust-color-names", label: "Summoner names",
    selector: "span.player-name__force-locale-text-direction" },
  { key: "lust-color-lobby-names", label: "Lobby names",
    selector: ".parties-player-name, .v2-banner-component .player-name, .player-slot__summoner-name" },
  { key: "lust-color-lobby-header", label: "Lobby header",
    selector: ".lobby-header-description, .lobby-header-separator, .lobby-header-details" },
  { key: "lust-color-queue", label: "Queue (finding match)",
    selector: ".parties-game-search-header-text, .parties-status-card-header-text, .parties-game-search-elapsed, .parties-game-search-status, .parties-status-card-info" }
];
function applyLustColors() {
  let style = document.getElementById("lust-custom-colors");
  if (!style) {
    style = document.createElement("style");
    style.id = "lust-custom-colors";
    document.head.appendChild(style);
  }
  style.textContent = LUST_COLORS
    .filter((item) => ElainaData.get(item.key))
    .map((item) => `${item.selector} { color: ${utils.sanitizeColor(ElainaData.get(item.key))} !important; }`)
    .join("\\n");
}
async function customizeSettings(view) {
  await statusSection(lustSection(view, "Status"));
  colorSection(lustSection(view, "Colors"));
  await themeSettings(lustSection(view, "Theme"));
  await pluginsSettings(lustSection(view, "Plugins"));
}
function colorSection(section) {
  const list = document.createElement("div");
  list.className = "lust-customize";
  LUST_COLORS.forEach((item) => {
    const row = document.createElement("div");
    row.className = "lust-customize-row";
    const label = document.createElement("span");
    label.textContent = item.label;
    const picker = document.createElement("input");
    picker.type = "color";
    picker.value = ElainaData.get(item.key) || "#f0e6d2";
    const state = document.createElement("span");
    state.className = "lust-customize-state";
    const showState = () => {
      state.textContent = ElainaData.get(item.key) ? ElainaData.get(item.key) : "League default";
    };
    picker.addEventListener("input", () => {
      ElainaData.set(item.key, picker.value);
      showState();
      applyLustColors();
    });
    const reset = document.createElement("lol-uikit-flat-button");
    reset.textContent = "Default";
    reset.addEventListener("click", () => {
      ElainaData.set(item.key, "");
      picker.value = "#f0e6d2";
      showState();
      applyLustColors();
    });
    showState();
    row.append(label, picker, state, reset);
    list.appendChild(row);
  });
  section.appendChild(list);
}
const LUST_PANEL_CSS = `
  .lust-panel-tabs { display: flex; width: 100%; margin: 4px 0 12px; border-bottom: 1px solid #785a2866; }
  .lust-panel-tab { flex: 1; padding: 6px 0; text-align: center; cursor: pointer; color: #a09b8c;
    font: 700 12px "Beaufort for LOL", serif; letter-spacing: 1px; border-bottom: 2px solid transparent; }
  .lust-panel-tab:hover { color: #f0e6d2; }
  .lust-panel-tab.active { color: #f0e6d2; border-bottom-color: #c8aa6e; }
  [data-lust-tab]:not([data-lust-tab="lust"]) > :not(.lust-keep) { display: none !important; }
  .lust-panel-view { display: none !important; width: 100%; height: 60vh; }
  [data-lust-tab="customize"] > .lust-panel-view[data-tab="customize"],
  [data-lust-tab="reveal"] > .lust-panel-view[data-tab="reveal"] { display: block !important; }
  .lust-panel-view[data-tab="reveal"] { height: auto; }
  #lust-settings-panel[data-lust-tab="customize"] #lust-settings-flyout,
  #lust-settings-panel[data-lust-tab="reveal"] #lust-settings-flyout { min-width: 560px !important; max-width: 560px !important; }
  .lust-panel-reload { display: block; width: 220px; margin: 14px auto 6px; }
  .lust-hub-section { margin-bottom: 18px; }
  .lust-hub-title { margin: 0 0 8px; padding-bottom: 4px; border-bottom: 1px solid #785a2866; color: #f0e6d2;
    font: 700 13px "Beaufort for LOL", serif; letter-spacing: 1px; text-transform: uppercase; }
  .lust-status-row { display: flex; gap: 8px; margin-bottom: 6px; }
  .lust-status-row lol-uikit-flat-button { flex: 1; }
  .lust-status-row .lust-status-active { filter: brightness(1.35); outline: 1px solid #c8aa6e; }
  .lust-customize { display: flex; flex-direction: column; gap: 10px; padding: 4px 2px 8px; }
  .lust-customize-row { display: grid; grid-template-columns: 1fr 36px 96px 80px; align-items: center; gap: 8px;
    color: #cdbe91; font: 13px "Beaufort for LOL", serif; }
  .lust-customize-row input[type="color"] { width: 36px; height: 24px; padding: 0; border: 1px solid #785a28;
    background: none; cursor: pointer; }
  .lust-customize-state { color: #a09b8c; font-size: 11px; }
`;
function addLustPanelTabs(panel) {
  const links = panel.querySelector(".settings-links");
  const form = links?.parentElement;
  if (!form || form.querySelector(".lust-panel-tabs"))
    return !!form;
  links.querySelectorAll("a").forEach((link) => {
    if (/discord\\.com|ko-fi\\.com/.test(link.href))
      link.remove();
  });
  form.firstElementChild?.classList.add("lust-keep");
  const tabBar = document.createElement("div");
  tabBar.className = "lust-panel-tabs lust-keep";
  form.firstElementChild ? form.firstElementChild.after(tabBar) : form.prepend(tabBar);
  let anchor = tabBar;
  const select = async (tab) => {
    form.dataset.lustTab = tab.id;
    panel.dataset.lustTab = tab.id;
    tabBar.querySelectorAll(".lust-panel-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === tab.id);
    });
    const view = form.querySelector(`.lust-panel-view[data-tab="${tab.id}"]`);
    if (view && !view.dataset.rendered) {
      view.dataset.rendered = "true";
      await tab.render(view);
      if (tab.reload === false)
        return;
      const reload = document.createElement("lol-uikit-flat-button");
      reload.className = "lust-panel-reload";
      reload.textContent = "Reload client to apply";
      reload.addEventListener("click", () => window.restartClient());
      view.appendChild(reload);
    }
  };
  LUST_PANEL_TABS.forEach((tab) => {
    const button = document.createElement("div");
    button.className = "lust-panel-tab";
    button.dataset.tab = tab.id;
    button.textContent = tab.label;
    button.addEventListener("click", () => select(tab));
    tabBar.appendChild(button);
    if (tab.render) {
      const view = document.createElement("lol-uikit-scrollable");
      view.className = `${tab.className} lust-panel-view lust-keep`;
      view.dataset.tab = tab.id;
      anchor.after(view);
      anchor = view;
    }
  });
  select(LUST_PANEL_TABS[0]);
  return true;
}
function mountLustPanelTabs() {
  const style = document.createElement("style");
  style.textContent = LUST_PANEL_CSS;
  document.head.appendChild(style);
  new MutationObserver(() => {
    const panel = document.getElementById("lust-settings-panel");
    if (!panel || panel.dataset.lustTabsPending)
      return;
    panel.dataset.lustTabsPending = "true";
    let tries = 0;
    const attempt = () => {
      if (!document.body.contains(panel))
        return;
      if (!addLustPanelTabs(panel) && ++tries < 40)
        setTimeout(attempt, 100);
    };
    attempt();
  }).observe(document.body, { childList: true });
}
'''


def checkbox(locale, element_id, key):
    """A settings checkbox exactly as the theme builds it, for removing it."""
    return f'''      UI.createCheckBox(
        `${{await getString("theme-settings.{locale}")}}`,
        "{element_id}",
        "{element_id}box",
        () => {{
          restartAfterChange("{element_id}", "{key}");
        }},
        true,
        "{key}"
      ),
'''


# (file, old, new): exact replacements applied before renaming. Each must match.
PATCHES = [
    # Settings move from the client settings window into the Lust panel.
    ("index.js",
     'function Settings(context) {\n  ElainaData.set("settingsChangenumber", 0);\n  settingsUtils(context, structure);\n}\n',
     LUST_PANEL_JS),
    # No automation that plays for the player: auto find queue and honor skip.
    ("index.js", "  AutoQueue(context);\n  skipHonor(context);\n", ""),
    ("index.js", "        await queueSection(),\n", ""),
    # No fake mastery score or rank sent to friends.
    ("index.js",
     '      if (ElainaData.get("Custom-mastery-score"))\n        customProfile.customMasteryScore();\n', ""),
    ("index.js",
     '      if (ElainaData.get("Custom-rank")) {\n        window.setTimeout(async () => {\n'
     '          customProfile.customRank();\n          window.customRank = customProfile.customRank;\n'
     '        }, 1e4);\n      }\n', ""),
    # Name colors come from the CUSTOMIZE tab now, League's own until a player picks one.
    ("index.js",
     '    if (ElainaData.get("change-nickname-color"))\n      addCss.customNicknameColor();',
     '    if (false)\n      addCss.customNicknameColor();'),
    # No "Invite all" button or friend-group dropdown in the lobby.
    ("index.js",
     '    if (ElainaData$1.get("Enable-Invite-Fr"))\n      inviteAllFriends.main();',
     '    if (false)\n      inviteAllFriends.main();'),
    ("index.js",
     '''    br(),
    UI.createCheckBox(
      `${await getString("plugins-settings.enable-invite-fr")}`,
      "invfr",
      "invfrbox",
      () => {
        restartAfterChange("invfr", "Enable-Invite-Fr");
      },
      true,
      "Enable-Invite-Fr"
    )
  ]);''', "  ]);"),
    ("config/datastoreDefault.js", '"Enable-Invite-Fr"              : true,',
     '"Enable-Invite-Fr"              : false,'),
    # Appearing offline is Lust Offline's job (the chat proxy), not the status dot.
    ("index.js", "    const offlineMode = new OfflineMode();\n    offlineMode.main();\n", ""),
    # The gear opens the client settings directly, not the theme's own menu first.
    ("index.js",
     '    if (ElainaData.get("Old-League-Loader-Settings")) {\n      while (!manager())',
     '    if (false) {\n      while (!manager())'),
    ("index.js",
     '''    UI.createCheckBox(
      `${await getString("plugins-settings.old-ll-settings")}`,
      "oldll",
      "oldllbox",
      () => {
        restartAfterChange("oldll", "Old-League-Loader-Settings");
      },
      true,
      "Old-League-Loader-Settings"
    ),
    br(),
''', ""),
    # Honor, trophy, emblem, ticker and hover card show the client's own art.
    ("index.js",
     'key: "Custom-Emblem",\n          css: "emblem.css",',
     'key: "Custom-Emblem",\n          css: "null.css",'),
    ("index.js",
     'key: "Custom-Ticker",\n          css: "ticker.css",',
     'key: "Custom-Ticker",\n          css: "null.css",'),
    ("index.js",
     'key: "Custom-Trophy",\n          css: "trophy.css",',
     'key: "Custom-Trophy",\n          css: "null.css",'),
    ("index.js",
     "    const customTickerIcon = new CustomTickerIcon();\n    customTickerIcon.main();\n", ""),
    ("index.js",
     '    if (ElainaData.get("Custom-Hover-card-backdrop")) {\n      const customHoverCardBackdrop',
     '    if (false) {\n      const customHoverCardBackdrop'),
    ("index.js",
     '    if (ElainaData.get("Custom-Emblem")) {\n      const customEmblemIcon',
     '    if (false) {\n      const customEmblemIcon'),
    ("index.js", checkbox("custom-emblem", "cusemi", "Custom-Emblem") + "      br(),\n", ""),
    ("index.js", checkbox("custom-trophy", "custrophy", "Custom-Trophy") + "      br(),\n", ""),
    ("index.js", checkbox("custom-ticker", "custick", "Custom-Ticker") + "      br()\n", ""),
    ("index.js", checkbox("custom-hover-card-backdrop", "cushvbdrop", "Custom-Hover-card-backdrop"), ""),
    ("config/datastoreDefault.js", '"Custom-Hover-card-backdrop"\t: true,',
     '"Custom-Hover-card-backdrop"\t: false,'),
    ("config/datastoreDefault.js", '"Custom-Emblem"                 : true,',
     '"Custom-Emblem"                 : false,'),
    ("config/datastoreDefault.js", '"Custom-Trophy"                 : true,',
     '"Custom-Trophy"                 : false,'),
    ("config/datastoreDefault.js", '"Custom-Ticker"                 : true,',
     '"Custom-Ticker"                 : false,'),
    # Default wallpaper/audio are Lust's own files.
    ("index.js",
     '"Wallpaper-list": ["elaina1.webm", "elaina2.jpg"],',
     '"Wallpaper-list": ["lust-wallpaper.webm", "lust-dark.jpg", "lust-wallpaper.jpg"],'),
    ("index.js",
     '"Audio-list": ["Laur - その花は世界を紡ぐ.flac", "Laur - Mellifluous.flac"],',
     '"Audio-list": ["lust-silence.wav"],'),
    # Fill the window with wallpapers of any aspect ratio instead of letterboxing.
    ("assets/styles/themes/theme-wallpapers.css",
     "#elaina-bg {\n\twidth:100%;\n\theight: 100%;\n",
     "#elaina-bg {\n\twidth:100%;\n\theight: 100%;\n\tobject-fit: cover;\n"),
    ("assets/styles/themes/theme-wallpapers.css",
     "#elaina-static-bg {\n\twidth:100%;\n",
     "#elaina-static-bg {\n\twidth:100%;\n\theight: 100%;\n\tobject-fit: cover;\n"),
    # No button that hides the top-right nav icons.
    ("index.js",
     'if (ElainaData.get("enable-hide-top-navbar-friendlist-button")) {\n      hideTopNavbarButton.addHideButton();',
     'if (false) {\n      hideTopNavbarButton.addHideButton();'),
    ("config/datastoreDefault.js",
     '"enable-hide-top-navbar-friendlist-button" : true,',
     '"enable-hide-top-navbar-friendlist-button" : false,'),
    # RP and Blue Essence keep League's own icons, whatever was saved before.
    ("index.js",
     'key: "Custom-RP-Icon",\n          css: "riotpoint.css",',
     'key: "Custom-RP-Icon",\n          css: "null.css",'),
    ("index.js",
     'key: "Custom-BE-Icon",\n          css: "blueessence.css",',
     'key: "Custom-BE-Icon",\n          css: "null.css",'),
    ("index.js",
     '''      UI.createCheckBox(
        `${await getString("theme-settings.custom-rp-icon")}`,
        "cusrpi",
        "cusrpibox",
        () => {
          restartAfterChange("cusrpi", "Custom-RP-Icon");
        },
        true,
        "Custom-RP-Icon"
      ),
      br(),
      UI.createCheckBox(
        `${await getString("theme-settings.custom-be-icon")}`,
        "cusbei",
        "cusbeibox",
        () => {
          restartAfterChange("cusbei", "Custom-BE-Icon");
        },
        true,
        "Custom-BE-Icon"
      ),
      br(),
''', ""),
    # The profile shows the real rank emblem, rank name and banner.
    ("index.js",
     'key: "Custom-Clash-banner",\n          css: "clashbanner.css",',
     'key: "Custom-Clash-banner",\n          css: "null.css",'),
    ("index.js",
     'key: "Custom-Rank-Icon",\n          css: "rank.css",',
     'key: "Custom-Rank-Icon",\n          css: "null.css",'),
    ("index.js",
     '''      UI.createCheckBox(
        `${await getString("theme-settings.custom-rank-icon")}`,
        "cusranki",
        "cusrankibox",
        () => {
          restartAfterChange("cusranki", "Custom-Rank-Icon");
        },
        true,
        "Custom-Rank-Icon"
      ),
      br(),
''', ""),
    ("index.js",
     '''      UI.createCheckBox(
        `${await getString("theme-settings.custom-clash-banner")}`,
        "cusclassb",
        "cusclassbbox",
        () => {
          restartAfterChange("cusclassb", "Custom-Clash-banner");
        },
        true,
        "Custom-Clash-banner"
      ),
      br(),
''', ""),
    ("index.js",
     '    if (ElainaData.get("custom-rank-name"))\n      customProfile.CustomProfileRankName();',
     '    if (false)\n      customProfile.CustomProfileRankName();'),
    ("index.js",
     '''    UI.createCheckBox(
      `${await getString("theme-settings.custom-rank-name")}`,
      "cusrankname",
      "cusranknamebox",
      () => {
        restartAfterChange("cusrankname", "custom-rank-name");
      },
      true,
      "custom-rank-name"
    ),
    br(),
    UI.createSearchBox("Rank-line1"),
    UI.createSearchBox("Rank-line2"),
    br(),
''', ""),
    # Real summoner icon, border and regalia banner.
    ("index.js",
     'key: "Custom-Avatar",\n          css: "avatar.css",',
     'key: "Custom-Avatar",\n          css: "null.css",'),
    ("index.js",
     '    if (ElainaData.get("Custom-Avatar")) {\n      customAvatar.main();',
     '    if (false) {\n      customAvatar.main();'),
    ("index.js",
     '    if (ElainaData.get("Custom-Border")) {\n      const customBorder',
     '    if (false) {\n      const customBorder'),
    ("index.js",
     '    if (ElainaData.get("Custom-Regalia-Banner")) {\n      const customBanner',
     '    if (false) {\n      const customBanner'),
    ("index.js",
     '''      UI.createCheckBox(
        `${await getString("theme-settings.custom-avatar")}`,
        "cusav",
        "cusavbox",
        () => {
          restartAfterChange("cusav", "Custom-Avatar");
        },
        true,
        "Custom-Avatar"
      ),
      br(),
      UI.createCheckBox(
        `${await getString("theme-settings.custom-border")}`,
        "cusbor",
        "cusborbox",
        () => {
          restartAfterChange("cusbor", "Custom-Border");
        },
        true,
        "Custom-Border"
      ),
      br(),
      UI.createCheckBox(
        `${await getString("theme-settings.custom-regalia-banner")}`,
        "cusregabnr",
        "cusregabnrbox",
        () => {
          restartAfterChange("cusregabnr", "Custom-Regalia-Banner");
        },
        true,
        "Custom-Regalia-Banner"
      ),
      br(),
      UI.createRow("Custom-banner-row", [
        createBannerDropdown()
      ]),
''', ""),
    ("config/datastoreDefault.js", '"Custom-Avatar"                 : true,',
     '"Custom-Avatar"                 : false,'),
    ("config/datastoreDefault.js", '"Custom-Border"\t                : true,',
     '"Custom-Border"\t                : false,'),
    ("config/datastoreDefault.js", '"Custom-Regalia-Banner"         : true,',
     '"Custom-Regalia-Banner"         : false,'),
    ("config/datastoreDefault.js", '"custom-rank-name"              : true,',
     '"custom-rank-name"              : false,'),
    ("config/datastoreDefault.js", '"Custom-Rank-Icon"              : true,',
     '"Custom-Rank-Icon"              : false,'),
    ("config/datastoreDefault.js", '"Custom-Clash-banner"\t\t\t: true,',
     '"Custom-Clash-banner"\t\t\t: false,'),
    ("config/datastoreDefault.js", '"Custom-RP-Icon"                : true,',
     '"Custom-RP-Icon"                : false,'),
    ("config/datastoreDefault.js", '"Custom-BE-Icon"                : true,',
     '"Custom-BE-Icon"                : false,'),
    # Saved wallpaper lists still get Lust's default wallpapers.
    ("index.js",
     '  setDefaultData(defaultData, false);\n}',
     '  setDefaultData(defaultData, false);\n'
     '  const wallpapers = ElainaData.get("Wallpaper-list") || [];\n'
     '  for (const name of defaultData["Wallpaper-list"]) {\n'
     '    if (!wallpapers.includes(name)) wallpapers.push(name);\n'
     '  }\n'
     '  ElainaData.set("Wallpaper-list", wallpapers);\n}'),
    # The real summoner level shows instead of a custom one.
    ("index.js",
     '      if (ElainaData$1.get("custom-summoner-lv"))\n        customSummonerLv.main();',
     '      if (false)\n        customSummonerLv.main();'),
    ("index.js",
     '''    UI.createCheckBox(
      `${await getString("theme-settings.custom-summoner-lv")}`,
      "cussumlv",
      "cussumlvbox",
      () => {
        restartAfterChange("cussumlv", "custom-summoner-lv");
      },
      true,
      "custom-summoner-lv"
    ),
    br(),
    UI.createSearchBox("custom-summoner-lv-number"),
    br(),
''', ""),
    ("config/datastoreDefault.js", '"custom-summoner-lv"            : true,',
     '"custom-summoner-lv"            : false,'),
    # "+" next to the wallpaper pause button: opens the wallpapers folder, then
    # takes the pasted file's name (Pengu 1.1.6 can't list folders) and adds it.
    ("index.js", "    pauseBg.append(pauseBgIcon);\n    progressBar.append(progress);\n",
     "    pauseBg.append(pauseBgIcon);\n" + ADD_WALLPAPER_JS + "    progressBar.append(progress);\n"),
    ("index.js", "      newBgChange.append(bgDropdown);\n",
     "      const sizeHint = document.createElement(\"div\");\n"
     "      sizeHint.id = \"bg-size-hint\";\n"
     "      sizeHint.textContent = \"16:9 Size Preferred\";\n"
     "      newBgChange.append(bgDropdown, sizeHint);\n"),
    ("assets/styles/themes/theme-background-controllers.css", "#pause-bg:hover {",
     ADD_WALLPAPER_CSS + "#pause-bg:hover {"),
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


# (file, start, end): text cut from start up to end, for blocks too long to quote.
CUTS = [
    # Fake mastery score and rank sent to friends: removed with their settings.
    ("index.js",
     '      UI.createCheckBox(\n        `${await getString("plugins-settings.custom-mastery-score")}`,',
     '      UI.createCheckBox(\n        `${await getString("plugins-settings.custom-challenge-crystal")}`,'),
    # The theme's own nickname color settings (replaced by the CUSTOMIZE tab).
    ("index.js",
     '    UI.createCheckBox(\n      `${await getString("theme-settings.change-nickname-color")}`,',
     '    UI.createCheckBox(\n      `${await getString("theme-settings.hide-theme-usage-time")}`,'),
]


def apply_patches(root):
    for rel, start, end in CUTS:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        a = text.find(start)
        b = text.find(end, a + 1) if a >= 0 else -1
        if a < 0 or b < 0 or text.count(start) != 1:
            sys.exit(f"[theme] cut not found in {rel}: {start[:70]!r}")
        path.write_text(text[:a] + text[b:], encoding="utf-8")

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

    for name in ("lust-wallpaper.webm", "lust-dark.jpg"):
        shutil.copy2(HERE / "art" / name, bgs / "wallpapers" / name)
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
