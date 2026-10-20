/**
 * @name Lust-LobbyReveal
 * @author Lust Team
 * @description Shows champ select teammates' Riot IDs, ranks and mains, with op.gg links
 * @link https://github.com/steele123/reveal
 */
(function initLobbyReveal() {
  const LOG_PREFIX = "[Lust-LobbyReveal]";
  const PANEL_ID = "lust-lobby-reveal";
  const POSITION_KEY = "lust-lobby-reveal-position";

  const ROLE_LABELS = {
    top: "TOP",
    jungle: "JGL",
    middle: "MID",
    bottom: "ADC",
    utility: "SUP",
  };

  const SETTINGS_KEY = "lust-lobby-reveal-settings";
  const DEFAULT_SETTINGS = { provider: "opgg", click: "opgg", autoOpen: false, autoOpenDelay: 6 };
  // Multi-search sites: label and the payload field with the team's link.
  const PROVIDERS = {
    opgg: { label: "OP.GG", field: "multiUrl" },
    porofessor: { label: "Porofessor", field: "poroUrl" },
    ugg: { label: "U.GG", field: "uggUrl" },
  };
  const CLICK_ACTIONS = {
    opgg: "Open OP.GG profile",
    ugg: "Open U.GG profile",
    porofessor: "Open Porofessor",
    details: "Show details",
  };
  const AUTO_OPEN_DELAYS = [0, 3, 6, 10];

  // Turkish for this plugin's own texts; other languages go through LUST-I18n
  const TR = {
    "Open OP.GG profile": "OP.GG profilini aç",
    "Open U.GG profile": "U.GG profilini aç",
    "Open Porofessor": "Porofessor'u aç",
    "Show details": "Ayrıntıları göster",
    "Placements": "Yerleştirme",
    "Unranked": "Derecesiz",
    "Drag to move · double-click to reset": "Taşımak için sürükle · sıfırlamak için çift tıkla",
    "Show": "Göster",
    "Hide": "Gizle",
    "Waiting for teammates...": "Takım arkadaşları bekleniyor...",
    "COPY": "KOPYALA",
    "Copy Riot ID": "Riot ID'yi kopyala",
    "{id} on {site}": "{site} üzerinde {id}",
    "Multi {site}": "Toplu {site}",
    "Loading...": "Yükleniyor...",
    "{name} · Mastery {level} · {points} pts": "{name} · Ustalık {level} · {points} puan",
    "Lobby Reveal": "Lobby Reveal",
    "Multi-search": "Toplu arama",
    "The team button in champ select": "Şampiyon seçimindeki takım butonu",
    "Clicking a player": "Oyuncuya tıklayınca",
    "What a teammate's name does": "Takım arkadaşının adına tıklayınca ne olacağı",
    "Open lookup automatically": "Aramayı otomatik aç",
    "Waits for all five names, up to the delay": "Beş ismin hepsini bekler, en fazla seçilen süre kadar",
    "{seconds} sec": "{seconds} sn",
    "Dodge": "Dodge",
    "Click again to dodge": "Dodge için tekrar tıkla",
    "Dodging...": "Dodge atılıyor...",
    "Couldn't dodge": "Dodge atılamadı",
    "Leave champ select without restarting the client (the usual dodge penalty applies)":
      "Client'ı yeniden başlatmadan şampiyon seçiminden çık (normal dodge cezası uygulanır)",
  };

  function tr(text, vars) {
    const i18n = window.LustI18n;
    let out = i18n && i18n.language === "tr" && TR[text] ? TR[text] : i18n ? i18n.t(text) : text;
    if (vars) out = out.replace(/\{(\w+)\}/g, (match, key) => (key in vars ? String(vars[key]) : match));
    return out;
  }


  const MAINS_PER_PLAYER = 3;

  const CSS_RULES = `
    /* Lust: a quiet glass card, one purple accent */
    #${PANEL_ID} {
      position: fixed;
      right: 16px;
      bottom: 92px;
      z-index: 99999;
      width: 296px;
      padding: 12px 12px 10px;
      background: rgba(9, 12, 20, 0.86);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
      font-family: "Spiegel", "Arial", sans-serif;
      color: #d8d4cc;
      user-select: none;
    }

    #${PANEL_ID}[hidden] {
      display: none;
    }

    #${PANEL_ID} .lust-reveal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin: 0 2px 8px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: #8d8a95;
      text-transform: uppercase;
      cursor: move;
    }

    #${PANEL_ID} .lust-reveal-head > span:first-child::before {
      content: "";
      display: inline-block;
      width: 6px;
      height: 6px;
      margin-right: 8px;
      border-radius: 50%;
      background: #a78bfa;
      box-shadow: 0 0 8px #a78bfa;
      vertical-align: 1px;
    }

    #${PANEL_ID} .lust-reveal-toggle {
      cursor: pointer;
      color: #6f6c78;
      font-size: 12px;
      padding: 2px 4px;
      border-radius: 6px;
    }

    #${PANEL_ID} .lust-reveal-toggle:hover {
      color: #f0eef5;
      background: rgba(255, 255, 255, 0.06);
    }

    #${PANEL_ID}.collapsed .lust-reveal-body {
      display: none;
    }

    #${PANEL_ID}.collapsed .lust-reveal-head {
      margin-bottom: 0;
    }

    #${PANEL_ID} .lust-reveal-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 6px;
      border-radius: 10px;
      font-size: 12px;
      transition: background 0.12s;
    }

    #${PANEL_ID} .lust-reveal-row:hover {
      background: rgba(255, 255, 255, 0.045);
    }

    #${PANEL_ID} .lust-reveal-icon {
      flex: 0 0 30px;
      width: 30px;
      height: 30px;
      border-radius: 9px;
      background: #1a1d27;
    }

    #${PANEL_ID} .lust-reveal-info {
      flex: 1 1 auto;
      min-width: 0;
    }

    #${PANEL_ID} .lust-reveal-line {
      display: flex;
      align-items: center;
      gap: 5px;
      min-width: 0;
    }

    #${PANEL_ID} .lust-reveal-role {
      flex: 0 0 auto;
      padding: 0 4px;
      border-radius: 4px;
      background: rgba(167, 139, 250, 0.14);
      font-size: 9px;
      font-weight: 700;
      line-height: 14px;
      color: #c4b5fd;
    }

    #${PANEL_ID} .lust-reveal-name {
      flex: 1 1 auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
      color: #f0eef5;
      text-decoration: none;
    }

    #${PANEL_ID} .lust-reveal-name:hover {
      color: #c4b5fd;
    }

    #${PANEL_ID} .lust-reveal-tag {
      font-weight: 400;
      color: #6f6c78;
    }

    #${PANEL_ID} .lust-reveal-stats {
      margin-top: 2px;
      font-size: 11px;
      color: #8d8a95;
      white-space: nowrap;
    }

    #${PANEL_ID} .lust-reveal-crest {
      width: 14px;
      height: 14px;
    }

    #${PANEL_ID} .lust-reveal-tier {
      color: #b9b5c2;
    }

    #${PANEL_ID} .lust-reveal-mains {
      display: flex;
      gap: 3px;
      margin-left: auto;
    }

    #${PANEL_ID} .lust-reveal-main {
      width: 18px;
      height: 18px;
      border-radius: 5px;
    }

    /* Shown on the row under the mouse only */
    #${PANEL_ID} .lust-reveal-copy {
      flex: 0 0 auto;
      cursor: pointer;
      padding: 0 5px;
      border-radius: 5px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: #8d8a95;
      opacity: 0;
      transition: opacity 0.12s;
    }

    #${PANEL_ID} .lust-reveal-row:hover .lust-reveal-copy {
      opacity: 1;
    }

    #${PANEL_ID} .lust-reveal-copy:hover {
      color: #f0eef5;
      background: rgba(255, 255, 255, 0.08);
    }

    #${PANEL_ID} .lust-reveal-links {
      display: flex;
      gap: 6px;
      margin-top: 10px;
    }

    #${PANEL_ID} .lust-reveal-multi {
      flex: 1 1 0;
      display: block;
      padding: 7px 0;
      border-radius: 10px;
      text-align: center;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      text-decoration: none;
      color: #ede9fe;
      background: rgba(167, 139, 250, 0.16);
      border: 1px solid rgba(167, 139, 250, 0.35);
      transition: background 0.12s, border-color 0.12s;
    }

    #${PANEL_ID} .lust-reveal-multi:hover {
      background: rgba(167, 139, 250, 0.28);
      border-color: #a78bfa;
    }

    #${PANEL_ID} .lust-reveal-also {
      margin-top: 7px;
      text-align: center;
      font-size: 10px;
      color: #6f6c78;
    }

    #${PANEL_ID} .lust-reveal-also a {
      margin: 0 5px;
      color: #8d8a95;
      text-decoration: none;
    }

    #${PANEL_ID} .lust-reveal-also a:hover {
      color: #f0eef5;
    }

    /* Small and tucked to the right so it isn't hit by accident */
    #${PANEL_ID} .lust-reveal-dodge {
      display: table;
      margin: 6px 0 0 auto;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #6f6c78;
      cursor: pointer;
    }

    #${PANEL_ID} .lust-reveal-dodge:hover {
      color: #f0eef5;
      background: rgba(255, 255, 255, 0.06);
    }

    #${PANEL_ID} .lust-reveal-dodge.armed {
      color: #fff;
      background: rgba(232, 64, 87, 0.85);
    }

    #${PANEL_ID} .lust-reveal-details {
      margin: 0 6px 6px 46px;
      font-size: 11px;
      line-height: 1.5;
      color: #8d8a95;
    }

    #${PANEL_ID} .lust-reveal-empty {
      padding: 6px;
      font-size: 12px;
      color: #6f6c78;
    }
  `;

  const HUB_CSS = `
    .lust-rv-hub {
      position: relative;
      overflow: hidden;
      padding: 18px 18px 16px;
      border: 1px solid #785a28;
      background:
        radial-gradient(120% 90% at 100% 0%, rgba(10, 200, 185, 0.16), transparent 55%),
        radial-gradient(90% 80% at 0% 100%, rgba(139, 92, 246, 0.18), transparent 60%),
        linear-gradient(160deg, #0d1a2b 0%, #010a13 70%);
      box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.55);
      font-family: "Spiegel", "Arial", sans-serif;
      color: #cdbe91;
    }

    .lust-rv-hub::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(135deg, rgba(200, 170, 110, 0.035) 0 1px, transparent 1px 9px);
    }

    .lust-rv-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 14px;
      font: 700 16px "Beaufort for LOL", serif;
      letter-spacing: 1px;
      color: #f0e6d2;
      text-transform: uppercase;
    }

    .lust-rv-field {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 0;
      border-top: 1px solid rgba(120, 90, 40, 0.35);
    }

    .lust-rv-label {
      font-size: 13px;
      color: #f0e6d2;
    }

    .lust-rv-hint {
      display: block;
      margin-top: 2px;
      font-size: 11px;
      color: #7e7a70;
    }

    .lust-rv-hub select {
      min-width: 170px;
      padding: 6px 8px;
      border: 1px solid #785a28;
      background: #010a13;
      color: #cdbe91;
      font: 13px "Spiegel", "Arial", sans-serif;
      outline: none;
    }

    .lust-rv-hub select.small {
      min-width: 0;
      width: 80px;
      margin-right: 10px;
    }

    .lust-rv-switch {
      position: relative;
      flex: 0 0 auto;
      width: 38px;
      height: 20px;
      border: 1px solid #785a28;
      border-radius: 10px;
      background: #1e2328;
      cursor: pointer;
      transition: background 0.2s;
    }

    .lust-rv-switch::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #a09b8c;
      transition: transform 0.2s, background 0.2s;
    }

    .lust-rv-switch.on {
      background: #0a3a40;
      border-color: #0ac8b9;
    }

    .lust-rv-switch.on::after {
      transform: translateX(18px);
      background: #0ac8b9;
    }
  `;

  let panel = null;
  let collapsed = false;
  let settings = loadSettings();
  // puuids whose details row is open, for the "Show details" click action
  const expanded = new Set();
  let autoOpen = { done: false, timer: null };
  // Dodge needs a second click within this long; the box redraws meanwhile, so it's kept here
  const DODGE_CONFIRM_MS = 3000;
  let dodgeArmedUntil = 0;
  let dodgeState = "";

  // The client's own champ select quit (as reveal does it): the usual dodge penalty applies.
  function dodgeButton() {
    const button = el("div", "lust-reveal-dodge");
    const armed = Date.now() < dodgeArmedUntil;
    button.classList.toggle("armed", armed);
    button.textContent = dodgeState || tr(armed ? "Click again to dodge" : "Dodge");
    button.title = tr("Leave champ select without restarting the client (the usual dodge penalty applies)");
    button.addEventListener("click", async () => {
      if (dodgeState) return;
      if (Date.now() >= dodgeArmedUntil) {
        dodgeArmedUntil = Date.now() + DODGE_CONFIRM_MS;
        queueRender();
        setTimeout(queueRender, DODGE_CONFIRM_MS + 50);
        return;
      }
      dodgeArmedUntil = 0;
      dodgeState = tr("Dodging...");
      queueRender();
      try {
        const response = await fetch(
          '/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&args=["","teambuilder-draft","quitV2",""]',
          { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
        );
        if (!response.ok) throw new Error(String(response.status));
        dodgeState = "";
      } catch (err) {
        log("warn", "Dodge failed:", err.message);
        dodgeState = tr("Couldn't dodge");
        setTimeout(() => {
          dodgeState = "";
          queueRender();
        }, 2500);
      }
      queueRender();
    });
    return button;
  }

  function loadSettings() {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") };
    } catch {
      return { ...DEFAULT_SETTINGS };
    }
  }

  function saveSettings(changes) {
    settings = { ...settings, ...changes };
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch {}
    queueRender();
  }

  let lastData = null;
  let renderQueued = false;
  let championNames = null;
  // Teammate details by puuid, filled in from the client's own APIs as they arrive.
  const stats = new Map();

  function log(level, ...args) {
    (console[level] || console.log)(LOG_PREFIX, ...args);
  }

  function waitForBridge() {
    return new Promise((resolve, reject) => {
      const timeout = 10000;
      const interval = 50;
      let elapsed = 0;
      const check = () => {
        if (window.__lustBridge) return resolve(window.__lustBridge);
        elapsed += interval;
        if (elapsed >= timeout) return reject(new Error("Bridge not available"));
        setTimeout(check, interval);
      };
      check();
    });
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // ---- Teammate details (rank, mains, profile icon) ----

  async function lcuGet(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`${path} -> ${response.status}`);
    return response.json();
  }

  function loadChampionNames() {
    if (!championNames) {
      championNames = lcuGet("/lol-game-data/assets/v1/champion-summary.json")
        .then((list) => new Map(list.filter((c) => c.id > 0).map((c) => [c.id, c.name])))
        .catch(() => new Map());
    }
    return championNames;
  }

  function parseRank(rankedStats) {
    const solo = (rankedStats && rankedStats.queueMap && rankedStats.queueMap.RANKED_SOLO_5x5) || {};
    const tier = solo.tier && solo.tier !== "NONE" ? solo.tier : "UNRANKED";
    const division = solo.division && solo.division !== "NA" ? solo.division : "";
    return {
      tier,
      division: tier === "UNRANKED" ? "" : division,
      leaguePoints: solo.leaguePoints || 0,
      provisional: !!solo.isProvisional,
    };
  }

  function topMains(mastery, names) {
    return (Array.isArray(mastery) ? mastery : [])
      .filter((entry) => entry.championPoints > 0)
      .sort((a, b) => b.championPoints - a.championPoints)
      .slice(0, MAINS_PER_PLAYER)
      .map((entry) => ({
        championId: entry.championId,
        name: names.get(entry.championId) || `Champion ${entry.championId}`,
        level: entry.championLevel || 0,
        points: entry.championPoints,
      }));
  }

  function loadStats(puuid) {
    if (!puuid || stats.has(puuid)) return;
    const entry = {};
    stats.set(puuid, entry);
    const settle = (key, promise) =>
      promise.then((value) => {
        entry[key] = value;
        queueRender();
      }, () => {});
    settle("rank", lcuGet(`/lol-ranked/v1/ranked-stats/${puuid}`).then(parseRank));
    settle("iconId", lcuGet(`/lol-summoner/v2/summoners/puuid/${puuid}`).then((s) => s.profileIconId));
    settle("mains", Promise.all([
      lcuGet(`/lol-champion-mastery/v1/${puuid}/champion-mastery`),
      loadChampionNames(),
    ]).then(([mastery, names]) => topMains(mastery, names)));
  }

  function formatTier(rank) {
    if (rank.tier === "UNRANKED") return tr(rank.provisional ? "Placements" : "Unranked");
    const name = rank.tier.charAt(0) + rank.tier.slice(1).toLowerCase();
    return `${name}${rank.division ? ` ${rank.division}` : ""} · ${rank.leaguePoints} LP`;
  }

  function statsLine(entry) {
    const line = el("div", "lust-reveal-line lust-reveal-stats");
    if (entry.rank) {
      const crest = el("img", "lust-reveal-crest");
      crest.src = `/fe/lol-static-assets/images/ranked-mini-crests/${entry.rank.tier.toLowerCase()}.svg`;
      line.appendChild(crest);
      line.appendChild(el("span", "lust-reveal-tier", formatTier(entry.rank)));
    }
    if (entry.mains && entry.mains.length) {
      const mains = el("span", "lust-reveal-mains");
      for (const main of entry.mains) {
        const icon = el("img", "lust-reveal-main");
        icon.src = `/lol-game-data/assets/v1/champion-icons/${main.championId}.png`;
        icon.title = tr("{name} · Mastery {level} · {points} pts", { name: main.name, level: main.level, points: main.points.toLocaleString() });
        mains.appendChild(icon);
      }
      line.appendChild(mains);
    }
    return line;
  }

  // ---- Panel ----

  function ensurePanel() {
    if (panel && document.body.contains(panel)) return panel;
    panel = el("div");
    panel.id = PANEL_ID;
    panel.hidden = true;
    if (collapsed) panel.classList.add("collapsed");
    document.body.appendChild(panel);
    return panel;
  }

  function savedPosition() {
    try {
      const saved = JSON.parse(localStorage.getItem(POSITION_KEY) || "null");
      return saved && Number.isFinite(saved.left) && Number.isFinite(saved.top) ? saved : null;
    } catch {
      return null;
    }
  }

  function clampToWindow(left, top) {
    const rect = panel.getBoundingClientRect();
    return {
      left: Math.min(Math.max(0, left), Math.max(0, window.innerWidth - rect.width)),
      top: Math.min(Math.max(0, top), Math.max(0, window.innerHeight - rect.height)),
    };
  }

  // Where the player dragged it; otherwise in the bottom-right corner (CSS), above the
  // chat buttons so they stay clickable.
  function placePanel() {
    if (!panel || panel.hidden) return;
    const saved = savedPosition();
    if (saved) {
      const { left, top } = clampToWindow(saved.left, saved.top);
      Object.assign(panel.style, { left: `${left}px`, top: `${top}px`, right: "auto", bottom: "auto" });
      return;
    }
    Object.assign(panel.style, { left: "", top: "", right: "", bottom: "" });
  }

  function makeDraggable(handle) {
    handle.title = tr("Drag to move · double-click to reset");
    handle.addEventListener("dblclick", () => {
      try {
        localStorage.removeItem(POSITION_KEY);
      } catch {}
      placePanel();
    });
    handle.addEventListener("mousedown", (event) => {
      if (event.button !== 0 || event.target.closest(".lust-reveal-toggle")) return;
      event.preventDefault();
      const start = panel.getBoundingClientRect();
      const offsetX = event.clientX - start.left;
      const offsetY = event.clientY - start.top;
      const move = (e) => {
        const { left, top } = clampToWindow(e.clientX - offsetX, e.clientY - offsetY);
        Object.assign(panel.style, { left: `${left}px`, top: `${top}px`, right: "auto", bottom: "auto" });
      };
      const up = () => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
        const rect = panel.getBoundingClientRect();
        try {
          localStorage.setItem(POSITION_KEY, JSON.stringify({ left: rect.left, top: rect.top }));
        } catch {}
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
    });
  }

  function copyText(text, node) {
    const done = () => {
      const previous = node.textContent;
      node.textContent = "✓";
      setTimeout(() => (node.textContent = previous), 900);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, () => {});
    }
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => {
      renderQueued = false;
      render(lastData);
    });
  }

  function render(data) {
    lastData = data;
    const root = ensurePanel();
    if (!data || !data.active) {
      root.hidden = true;
      root.replaceChildren();
      stats.clear();
      expanded.clear();
      resetAutoOpen();
      return;
    }

    const players = Array.isArray(data.players) ? data.players : [];
    players.forEach((player) => loadStats(player.puuid));
    root.replaceChildren();

    const head = el("div", "lust-reveal-head");
    head.appendChild(el("span", "", "Reveal"));
    const toggle = el("span", "lust-reveal-toggle", collapsed ? "▴" : "▾");
    toggle.title = tr(collapsed ? "Show" : "Hide");
    toggle.addEventListener("click", () => {
      collapsed = !collapsed;
      root.classList.toggle("collapsed", collapsed);
      toggle.textContent = collapsed ? "▴" : "▾";
      toggle.title = tr(collapsed ? "Show" : "Hide");
    });
    head.appendChild(toggle);
    makeDraggable(head);
    root.appendChild(head);

    const body = el("div", "lust-reveal-body");
    if (!players.length) {
      body.appendChild(el("div", "lust-reveal-empty", tr("Waiting for teammates...")));
    }
    for (const player of players) {
      const entry = stats.get(player.puuid) || {};
      const row = el("div", "lust-reveal-row");

      const icon = el("img", "lust-reveal-icon");
      if (entry.iconId !== undefined) icon.src = `/lol-game-data/assets/v1/profile-icons/${entry.iconId}.jpg`;
      row.appendChild(icon);

      const info = el("div", "lust-reveal-info");
      const top = el("div", "lust-reveal-line");
      const role = ROLE_LABELS[player.position];
      if (role) top.appendChild(el("span", "lust-reveal-role", role));

      const profileSites = {
        opgg: [player.opggUrl, "op.gg"],
        ugg: [player.uggUrl, "u.gg"],
        porofessor: [player.poroUrl, "Porofessor"],
      };
      const [profileUrl, siteName] = profileSites[settings.click] || ["", ""];
      const name = el(profileUrl || settings.click === "details" ? "a" : "span", "lust-reveal-name");
      name.appendChild(document.createTextNode(player.gameName || ""));
      if (player.gameTag) name.appendChild(el("span", "lust-reveal-tag", `#${player.gameTag}`));
      if (profileUrl) {
        name.href = profileUrl;
        name.target = "_blank";
        name.rel = "noreferrer";
        name.title = tr("{id} on {site}", { id: player.riotId, site: siteName });
      } else if (settings.click === "details") {
        name.href = "#";
        name.title = tr("Show details");
        name.addEventListener("click", (event) => {
          event.preventDefault();
          if (expanded.has(player.puuid)) expanded.delete(player.puuid);
          else expanded.add(player.puuid);
          queueRender();
        });
      }
      top.appendChild(name);

      const copy = el("span", "lust-reveal-copy", tr("COPY"));
      copy.title = tr("Copy Riot ID");
      copy.addEventListener("click", () => copyText(player.riotId || "", copy));
      top.appendChild(copy);
      info.appendChild(top);
      info.appendChild(statsLine(entry));
      row.appendChild(info);

      body.appendChild(row);
      if (settings.click === "details" && expanded.has(player.puuid)) {
        body.appendChild(detailsBlock(entry));
      }
    }

    // The chosen multi-search site as the button, the others as small links below.
    const chosen = PROVIDERS[settings.provider] ? settings.provider : "opgg";
    if (data[PROVIDERS[chosen].field]) {
      const links = el("div", "lust-reveal-links");
      const main = el("a", "lust-reveal-multi", tr("Multi {site}", { site: PROVIDERS[chosen].label }));
      main.href = data[PROVIDERS[chosen].field];
      main.target = "_blank";
      main.rel = "noreferrer";
      links.appendChild(main);
      body.appendChild(links);
    }
    const also = el("div", "lust-reveal-also");
    for (const [key, provider] of Object.entries(PROVIDERS)) {
      if (key === chosen || !data[provider.field]) continue;
      const link = el("a", "", provider.label);
      link.href = data[provider.field];
      link.target = "_blank";
      link.rel = "noreferrer";
      also.appendChild(link);
    }
    if (also.childElementCount) body.appendChild(also);
    body.appendChild(dodgeButton());
    root.appendChild(body);
    root.hidden = false;
    placePanel();
    scheduleAutoOpen(data, players.length);
  }

  function detailsBlock(entry) {
    const block = el("div", "lust-reveal-details");
    const lines = [];
    if (entry.rank) lines.push(formatTier(entry.rank));
    for (const main of entry.mains || []) {
      lines.push(tr("{name} · Mastery {level} · {points} pts", { name: main.name, level: main.level, points: main.points.toLocaleString() }));
    }
    block.textContent = lines.length ? lines.join("\n") : tr("Loading...");
    block.style.whiteSpace = "pre-line";
    return block;
  }

  function openUrl(url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.click();
  }

  // Once per champ select: open the multi-search when all five names are in or the
  // delay runs out, if the player turned that on.
  function scheduleAutoOpen(data, count) {
    if (autoOpen.done || !settings.autoOpen) return;
    const open = () => {
      const latest = lastData || data;
      const url = latest[PROVIDERS[settings.provider] ? PROVIDERS[settings.provider].field : "multiUrl"];
      if (!url || autoOpen.done) return;
      autoOpen.done = true;
      clearTimeout(autoOpen.timer);
      openUrl(url);
    };
    if (count >= 5) open();
    else if (!autoOpen.timer) autoOpen.timer = setTimeout(open, settings.autoOpenDelay * 1000);
  }

  function resetAutoOpen() {
    clearTimeout(autoOpen.timer);
    autoOpen = { done: false, timer: null };
  }

  // ---- Hub (LOBBY REVEAL tab in the Lust panel) ----

  function selectField(options, value, onChange, className) {
    const select = el("select", className);
    for (const [key, label] of Object.entries(options)) {
      const option = el("option", "", label);
      option.value = key;
      select.appendChild(option);
    }
    select.value = String(value);
    select.addEventListener("change", () => onChange(select.value));
    return select;
  }

  function hubField(label, hint, control) {
    const row = el("div", "lust-rv-field");
    const text = el("div");
    text.appendChild(el("span", "lust-rv-label", label));
    if (hint) text.appendChild(el("span", "lust-rv-hint", hint));
    row.append(text, control);
    return row;
  }

  function renderHub(view) {
    if (!document.getElementById("lust-rv-hub-style")) {
      const style = el("style");
      style.id = "lust-rv-hub-style";
      style.textContent = HUB_CSS;
      document.head.appendChild(style);
    }
    const hub = el("div", "lust-rv-hub");
    const title = el("div", "lust-rv-title");
    title.append(el("span", "", tr("Lobby Reveal")));
    hub.appendChild(title);

    const providerLabels = Object.fromEntries(Object.entries(PROVIDERS).map(([key, p]) => [key, p.label]));
    hub.appendChild(hubField(tr("Multi-search"), tr("The team button in champ select"),
      selectField(providerLabels, settings.provider, (provider) => saveSettings({ provider }))));
    hub.appendChild(hubField(tr("Clicking a player"), tr("What a teammate's name does"),
      selectField(Object.fromEntries(Object.entries(CLICK_ACTIONS).map(([key, label]) => [key, tr(label)])), settings.click, (click) => saveSettings({ click }))));

    const autoControl = el("div");
    autoControl.style.display = "flex";
    autoControl.style.alignItems = "center";
    const delays = Object.fromEntries(AUTO_OPEN_DELAYS.map((s) => [s, tr("{seconds} sec", { seconds: s })]));
    autoControl.appendChild(selectField(delays, settings.autoOpenDelay,
      (delay) => saveSettings({ autoOpenDelay: Number(delay) }), "small"));
    const toggle = el("div", `lust-rv-switch${settings.autoOpen ? " on" : ""}`);
    toggle.addEventListener("click", () => {
      saveSettings({ autoOpen: !settings.autoOpen });
      toggle.classList.toggle("on", settings.autoOpen);
    });
    autoControl.appendChild(toggle);
    hub.appendChild(hubField(tr("Open lookup automatically"), tr("Waits for all five names, up to the delay"), autoControl));

    view.appendChild(hub);
  }

  window.LustReveal = { renderHub };

  function handlePhaseChange(data) {
    // FINALIZATION is the end of champ select once every pick is locked: keep the box
    if (data && data.phase && data.phase !== "ChampSelect" && data.phase !== "FINALIZATION") render(null);
  }

  async function init() {
    if (!document.body || !document.head) {
      setTimeout(init, 250);
      return;
    }

    const style = el("style");
    style.textContent = CSS_RULES;
    document.head.appendChild(style);

    let bridge;
    try {
      bridge = await waitForBridge();
    } catch (err) {
      log("warn", "Bridge unavailable, lobby reveal disabled:", err.message);
      return;
    }

    bridge.subscribe("lobby-reveal", render);
    bridge.subscribe("phase-change", handlePhaseChange);
    bridge.onDisconnect(() => render(null));
    // Keeps a dragged panel inside the window when the client is resized.
    setInterval(placePanel, 500);
    if (window.LustI18n) window.LustI18n.onChange(() => queueRender());
    log("info", "Lobby reveal ready");
  }

  init();
})();
