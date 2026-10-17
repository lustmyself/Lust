/**
 * @name Lust-LobbyReveal
 * @author Lust Team
 * @description Shows champ select teammates' Riot IDs and an op.gg multi-search link
 * @link https://github.com/steele123/reveal
 */
(function initLobbyReveal() {
  const LOG_PREFIX = "[Lust-LobbyReveal]";
  const PANEL_ID = "lust-lobby-reveal";

  const ROLE_LABELS = {
    top: "TOP",
    jungle: "JGL",
    middle: "MID",
    bottom: "ADC",
    utility: "SUP",
  };

  const CSS_RULES = `
    #${PANEL_ID} {
      position: fixed;
      right: 14px;
      bottom: 14px;
      z-index: 99999;
      min-width: 220px;
      max-width: 280px;
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
      gap: 6px;
      padding: 3px 0;
      font-family: "Spiegel", "Arial", sans-serif;
      font-size: 12px;
    }

    #${PANEL_ID} .lust-reveal-role {
      flex: 0 0 30px;
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

    #${PANEL_ID} .lust-reveal-copy {
      flex: 0 0 auto;
      cursor: pointer;
      font-size: 10px;
      color: #7e7a70;
    }

    #${PANEL_ID} .lust-reveal-copy:hover {
      color: #f0e6d2;
    }

    #${PANEL_ID} .lust-reveal-multi {
      display: block;
      margin-top: 10px;
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

  function ensurePanel() {
    if (panel && document.body.contains(panel)) return panel;
    panel = el("div");
    panel.id = PANEL_ID;
    panel.hidden = true;
    if (collapsed) panel.classList.add("collapsed");
    document.body.appendChild(panel);
    return panel;
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

  function render(data) {
    const root = ensurePanel();
    if (!data || !data.active) {
      root.hidden = true;
      root.replaceChildren();
      return;
    }

    const players = Array.isArray(data.players) ? data.players : [];
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
    root.appendChild(head);

    const body = el("div", "lust-reveal-body");
    if (!players.length) {
      body.appendChild(el("div", "lust-reveal-empty", "Waiting for teammates..."));
    }
    for (const player of players) {
      const row = el("div", "lust-reveal-row");
      row.appendChild(el("span", "lust-reveal-role", ROLE_LABELS[player.position] || ""));

      const name = el(player.opggUrl ? "a" : "span", "lust-reveal-name");
      name.appendChild(document.createTextNode(player.gameName || ""));
      if (player.gameTag) name.appendChild(el("span", "lust-reveal-tag", `#${player.gameTag}`));
      if (player.opggUrl) {
        name.href = player.opggUrl;
        name.target = "_blank";
        name.rel = "noreferrer";
        name.title = `${player.riotId} on op.gg`;
      }
      row.appendChild(name);

      const copy = el("span", "lust-reveal-copy", "COPY");
      copy.title = "Copy Riot ID";
      copy.addEventListener("click", () => copyText(player.riotId || "", copy));
      row.appendChild(copy);

      body.appendChild(row);
    }

    if (data.multiUrl) {
      const multi = el("a", "lust-reveal-multi", "Multi OP.GG");
      multi.href = data.multiUrl;
      multi.target = "_blank";
      multi.rel = "noreferrer";
      body.appendChild(multi);
    }
    root.appendChild(body);
    root.hidden = false;
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
    log("info", "Lobby reveal ready");
  }

  init();
})();
