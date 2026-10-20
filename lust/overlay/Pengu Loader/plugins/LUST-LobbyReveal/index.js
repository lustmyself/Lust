/**
 * @name Lust-LobbyReveal
 * @author Lust Team
 * @description Shows champ select teammates' Riot IDs, ranks, recent form and mains, with op.gg links
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

  const SOLO_DUO_QUEUE_ID = 420;
  const RECENT_GAMES = 20;
  // Below this many recent games a win rate is noise, so show the record instead.
  const MIN_GAMES_FOR_WIN_RATE = 10;
  const MAINS_PER_PLAYER = 3;

  const CSS_RULES = `
    #${PANEL_ID} {
      position: fixed;
      right: 14px;
      bottom: 14px;
      z-index: 99999;
      width: 300px;
      padding: 10px 12px 12px;
      background: rgba(1, 10, 19, 0.92);
      border: 1px solid #785a28;
      box-shadow: 0 0 12px rgba(0, 0, 0, 0.7);
      font-family: "Beaufort for LOL", serif;
      color: #cdbe91;
      user-select: none;
    }

    #${PANEL_ID}[hidden] {
      display: none;
    }

    #${PANEL_ID} .lust-reveal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 1px;
      color: #f0e6d2;
      text-transform: uppercase;
      cursor: move;
    }

    #${PANEL_ID} .lust-reveal-toggle {
      cursor: pointer;
      color: #a09b8c;
      font-size: 14px;
      padding: 0 2px;
    }

    #${PANEL_ID} .lust-reveal-toggle:hover {
      color: #f0e6d2;
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
      gap: 8px;
      padding: 4px 0;
      font-family: "Spiegel", "Arial", sans-serif;
      font-size: 12px;
    }

    #${PANEL_ID} .lust-reveal-icon {
      flex: 0 0 30px;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      border: 1px solid #785a28;
      background: #1e2328;
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
      font-size: 10px;
      font-weight: 700;
      color: #a09b8c;
    }

    #${PANEL_ID} .lust-reveal-name {
      flex: 1 1 auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #f0e6d2;
      text-decoration: none;
    }

    #${PANEL_ID} .lust-reveal-name:hover {
      color: #c8aa6e;
      text-decoration: underline;
    }

    #${PANEL_ID} .lust-reveal-tag {
      color: #7e7a70;
    }

    #${PANEL_ID} .lust-reveal-stats {
      margin-top: 2px;
      font-size: 11px;
      color: #a09b8c;
      white-space: nowrap;
    }

    #${PANEL_ID} .lust-reveal-crest {
      width: 16px;
      height: 16px;
    }

    #${PANEL_ID} .lust-reveal-tier {
      color: #cdbe91;
    }

    #${PANEL_ID} .lust-reveal-mains {
      display: flex;
      gap: 2px;
      margin-left: auto;
    }

    #${PANEL_ID} .lust-reveal-main {
      width: 18px;
      height: 18px;
      border: 1px solid #3c3c41;
    }

    #${PANEL_ID} .lust-reveal-copy {
      flex: 0 0 auto;
      cursor: pointer;
      font-size: 10px;
      color: #7e7a70;
    }

    #${PANEL_ID} .lust-reveal-copy:hover {
      color: #f0e6d2;
    }

    #${PANEL_ID} .lust-reveal-links {
      display: flex;
      gap: 6px;
      margin-top: 10px;
    }

    #${PANEL_ID} .lust-reveal-multi {
      flex: 1 1 0;
      display: block;
      padding: 6px 0;
      text-align: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      text-decoration: none;
      color: #cdfafa;
      background: linear-gradient(#1e2328, #1e2328) padding-box,
        linear-gradient(#0ac8b9, #0397ab) border-box;
      border: 2px solid transparent;
    }

    #${PANEL_ID} .lust-reveal-multi:hover {
      color: #f0e6d2;
      box-shadow: 0 0 8px rgba(10, 200, 185, 0.6);
    }

    #${PANEL_ID} .lust-reveal-empty {
      font-family: "Spiegel", "Arial", sans-serif;
      font-size: 12px;
      color: #7e7a70;
    }
  `;

  let panel = null;
  let collapsed = false;
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

  // ---- Teammate details (rank, recent form, mains, profile icon) ----

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

  // League reports other players' season losses as 0, so the win rate comes from
  // their recent Solo/Duo games instead. Each game lists only the requested player.
  function parseRecentForm(history) {
    const form = { wins: 0, losses: 0 };
    const games = (history && history.games && history.games.games) || [];
    for (const game of games) {
      if (game.queueId !== SOLO_DUO_QUEUE_ID) continue;
      const win = game.participants && game.participants[0] && game.participants[0].stats
        ? game.participants[0].stats.win
        : undefined;
      if (win === true) form.wins += 1;
      else if (win === false) form.losses += 1;
    }
    return form;
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
    settle("recent", lcuGet(
      `/lol-match-history/v1/products/lol/${puuid}/matches?begIndex=0&endIndex=${RECENT_GAMES - 1}`
    ).then(parseRecentForm));
    settle("iconId", lcuGet(`/lol-summoner/v2/summoners/puuid/${puuid}`).then((s) => s.profileIconId));
    settle("mains", Promise.all([
      lcuGet(`/lol-champion-mastery/v1/${puuid}/champion-mastery`),
      loadChampionNames(),
    ]).then(([mastery, names]) => topMains(mastery, names)));
  }

  function formatTier(rank) {
    if (rank.tier === "UNRANKED") return rank.provisional ? "Placements" : "Unranked";
    const name = rank.tier.charAt(0) + rank.tier.slice(1).toLowerCase();
    return `${name}${rank.division ? ` ${rank.division}` : ""} · ${rank.leaguePoints} LP`;
  }

  function formatRecentForm(recent) {
    const games = recent ? recent.wins + recent.losses : 0;
    if (!games) return "";
    if (games < MIN_GAMES_FOR_WIN_RATE) return `${recent.wins}W ${recent.losses}L`;
    return `${Math.round((recent.wins / games) * 100)}%`;
  }

  function statsLine(entry) {
    const line = el("div", "lust-reveal-line lust-reveal-stats");
    if (entry.rank) {
      const crest = el("img", "lust-reveal-crest");
      crest.src = `/fe/lol-static-assets/images/ranked-mini-crests/${entry.rank.tier.toLowerCase()}.svg`;
      line.appendChild(crest);
      line.appendChild(el("span", "lust-reveal-tier", formatTier(entry.rank)));
    }
    const form = formatRecentForm(entry.recent);
    if (form) {
      const recent = el("span", "", `· ${form}`);
      recent.title = `Last ${entry.recent.wins + entry.recent.losses} Solo/Duo games: ${entry.recent.wins}W ${entry.recent.losses}L`;
      line.appendChild(recent);
    }
    if (entry.mains && entry.mains.length) {
      const mains = el("span", "lust-reveal-mains");
      for (const main of entry.mains) {
        const icon = el("img", "lust-reveal-main");
        icon.src = `/lol-game-data/assets/v1/champion-icons/${main.championId}.png`;
        icon.title = `${main.name} · Mastery ${main.level} · ${main.points.toLocaleString()} pts`;
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

  // Where the player dragged it; otherwise just above the Custom Mods button so the
  // chat buttons in the corner stay clickable.
  function placePanel() {
    if (!panel || panel.hidden) return;
    const saved = savedPosition();
    if (saved) {
      const { left, top } = clampToWindow(saved.left, saved.top);
      Object.assign(panel.style, { left: `${left}px`, top: `${top}px`, right: "auto", bottom: "auto" });
      return;
    }
    Object.assign(panel.style, { left: "", top: "" });
    const button = document.querySelector(".lust-custom-wheel-button");
    const rect = button && button.getBoundingClientRect();
    if (!rect || !rect.height) {
      Object.assign(panel.style, { right: "", bottom: "" });
      return;
    }
    panel.style.right = `${Math.max(0, Math.round(window.innerWidth - rect.right))}px`;
    panel.style.bottom = `${Math.round(window.innerHeight - rect.top + 8)}px`;
  }

  function makeDraggable(handle) {
    handle.title = "Drag to move · double-click to reset";
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
      return;
    }

    const players = Array.isArray(data.players) ? data.players : [];
    players.forEach((player) => loadStats(player.puuid));
    root.replaceChildren();

    const head = el("div", "lust-reveal-head");
    head.appendChild(el("span", "", `Lobby (${players.length})`));
    const toggle = el("span", "lust-reveal-toggle", collapsed ? "▴" : "▾");
    toggle.title = collapsed ? "Show" : "Hide";
    toggle.addEventListener("click", () => {
      collapsed = !collapsed;
      root.classList.toggle("collapsed", collapsed);
      toggle.textContent = collapsed ? "▴" : "▾";
      toggle.title = collapsed ? "Show" : "Hide";
    });
    head.appendChild(toggle);
    makeDraggable(head);
    root.appendChild(head);

    const body = el("div", "lust-reveal-body");
    if (!players.length) {
      body.appendChild(el("div", "lust-reveal-empty", "Waiting for teammates..."));
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

      const name = el(player.opggUrl ? "a" : "span", "lust-reveal-name");
      name.appendChild(document.createTextNode(player.gameName || ""));
      if (player.gameTag) name.appendChild(el("span", "lust-reveal-tag", `#${player.gameTag}`));
      if (player.opggUrl) {
        name.href = player.opggUrl;
        name.target = "_blank";
        name.rel = "noreferrer";
        name.title = `${player.riotId} on op.gg`;
      }
      top.appendChild(name);

      const copy = el("span", "lust-reveal-copy", "COPY");
      copy.title = "Copy Riot ID";
      copy.addEventListener("click", () => copyText(player.riotId || "", copy));
      top.appendChild(copy);
      info.appendChild(top);
      info.appendChild(statsLine(entry));
      row.appendChild(info);

      body.appendChild(row);
    }

    const links = el("div", "lust-reveal-links");
    for (const [url, label, title] of [
      [data.multiUrl, "OP.GG", "Multi-search the team on op.gg"],
      [data.poroUrl, "Porofessor", "The team's pre-game page on Porofessor"],
    ]) {
      if (!url) continue;
      const link = el("a", "lust-reveal-multi", label);
      link.href = url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.title = title;
      links.appendChild(link);
    }
    if (links.childElementCount) body.appendChild(links);
    root.appendChild(body);
    root.hidden = false;
    placePanel();
  }

  function handlePhaseChange(data) {
    if (data && data.phase && data.phase !== "ChampSelect") render(null);
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
    // The Custom Mods button can appear or move after the panel does.
    setInterval(placePanel, 500);
    log("info", "Lobby reveal ready");
  }

  init();
})();
