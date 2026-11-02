/**
 * @name Lust-ChromaPreview
 * @author Lust Team
 * @description Big chroma preview: see every chroma of a skin large before picking one
 */
(function initChromaPreview() {
  const LOG_PREFIX = "[Lust-ChromaPreview]";
  const PANEL_ID = "lu-chroma-panel-container"; // LUST-ChromaWheel's chroma flyout
  const VIEW_ID = "lust-chroma-preview";
  const OPEN_CLASS = "lust-cp-open";

  // Turkish for this plugin's own texts; other languages go through LUST-I18n
  const TR = {
    "Big preview": "Büyük önizleme",
    Chromas: "Chromalar",
    Default: "Varsayılan",
    Selected: "Seçili",
    "Pick this chroma": "Bu chroma'yı seç",
    "Already selected": "Zaten seçili",
    Close: "Kapat",
    "← → browse · Enter pick · Esc close": "← → gez · Enter seç · Esc kapat",
  };

  function tr(text) {
    const i18n = window.LustI18n;
    return i18n && i18n.language === "tr" && TR[text] ? TR[text] : i18n ? i18n.t(text) : text;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  const CSS_RULES = `
    #${PANEL_ID} .lust-cp-open {
      position: absolute;
      top: 8px;
      right: 8px;
      z-index: 3;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: rgba(9, 12, 20, 0.72);
      border: 1px solid rgba(167, 139, 250, 0.35);
      color: #e9e4ff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      pointer-events: all;
      transition: background 0.12s, border-color 0.12s, transform 0.12s;
    }
    #${PANEL_ID} .lust-cp-open:hover {
      background: rgba(124, 92, 255, 0.55);
      border-color: #a78bfa;
      transform: scale(1.06);
    }
    #${PANEL_ID} .lust-cp-open svg { width: 15px; height: 15px; }

    #${VIEW_ID} {
      position: fixed;
      inset: 0;
      z-index: 10001;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(4, 6, 12, 0.74);
      backdrop-filter: blur(6px);
      pointer-events: all;
      font-family: "Spiegel", "Arial", sans-serif;
      color: #d8d4cc;
      user-select: none;
      animation: lust-cp-fade 0.16s ease-out;
    }
    @keyframes lust-cp-fade { from { opacity: 0; } to { opacity: 1; } }

    #${VIEW_ID} .lust-cp-card {
      display: flex;
      width: min(1060px, 92vw);
      height: min(620px, 86vh);
      background: rgba(9, 12, 20, 0.94);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
      overflow: hidden;
      animation: lust-cp-rise 0.2s cubic-bezier(0.2, 0.9, 0.2, 1);
    }
    @keyframes lust-cp-rise { from { transform: translateY(12px) scale(0.985); } to { transform: none; } }

    #${VIEW_ID} .lust-cp-stage {
      position: relative;
      flex: 1 1 auto;
      min-width: 0;
      background-color: #0b0f1a;
      background-size: cover;
      background-position: center;
    }
    #${VIEW_ID} .lust-cp-stage::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse at 50% 58%, var(--lust-cp-glow, rgba(124, 92, 255, 0.35)) 0, transparent 62%),
        linear-gradient(180deg, rgba(9, 12, 20, 0.25) 0, rgba(9, 12, 20, 0.15) 55%, rgba(9, 12, 20, 0.92) 100%);
      transition: background 0.25s;
    }
    #${VIEW_ID} .lust-cp-image {
      position: absolute;
      inset: 18px 70px 96px;
      background-repeat: no-repeat;
      background-size: contain;
      background-position: center bottom;
      filter: drop-shadow(0 18px 24px rgba(0, 0, 0, 0.55));
      animation: lust-cp-swap 0.22s ease-out;
    }
    @keyframes lust-cp-swap { from { opacity: 0.35; transform: translateY(6px); } to { opacity: 1; transform: none; } }

    #${VIEW_ID} .lust-cp-caption {
      position: absolute;
      left: 26px;
      right: 26px;
      bottom: 22px;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
    }
    #${VIEW_ID} .lust-cp-skin {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.6px;
      text-transform: uppercase;
      color: #9a96a8;
    }
    #${VIEW_ID} .lust-cp-name {
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: "Beaufort for LOL", "LoL Display", Georgia, serif;
      font-size: 30px;
      font-weight: 700;
      color: #f4f1fb;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.6);
    }
    #${VIEW_ID} .lust-cp-dot {
      flex: 0 0 auto;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.85);
      box-shadow: 0 0 12px var(--lust-cp-dot, #a78bfa);
      background: var(--lust-cp-dot, #a78bfa);
    }
    #${VIEW_ID} .lust-cp-badge {
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(167, 139, 250, 0.18);
      color: #c4b5fd;
      font-family: "Spiegel", "Arial", sans-serif;
      font-size: 11px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    #${VIEW_ID} .lust-cp-count {
      font-size: 12px;
      color: #8d8a95;
      white-space: nowrap;
    }

    #${VIEW_ID} .lust-cp-arrow {
      position: absolute;
      top: 50%;
      width: 42px;
      height: 42px;
      margin-top: -21px;
      border-radius: 50%;
      background: rgba(9, 12, 20, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #e9e4ff;
      font-size: 22px;
      line-height: 40px;
      text-align: center;
      cursor: pointer;
      transition: background 0.12s, border-color 0.12s;
    }
    #${VIEW_ID} .lust-cp-arrow:hover { background: rgba(124, 92, 255, 0.55); border-color: #a78bfa; }
    #${VIEW_ID} .lust-cp-prev { left: 16px; }
    #${VIEW_ID} .lust-cp-next { right: 16px; }

    #${VIEW_ID} .lust-cp-side {
      flex: 0 0 300px;
      display: flex;
      flex-direction: column;
      border-left: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(13, 16, 26, 0.96);
    }
    #${VIEW_ID} .lust-cp-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 16px 10px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #8d8a95;
    }
    #${VIEW_ID} .lust-cp-head > span:first-child::before {
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
    #${VIEW_ID} .lust-cp-close {
      cursor: pointer;
      color: #6f6c78;
      font-size: 16px;
      line-height: 1;
      padding: 4px 6px;
      border-radius: 6px;
    }
    #${VIEW_ID} .lust-cp-close:hover { color: #f0eef5; background: rgba(255, 255, 255, 0.06); }

    #${VIEW_ID} .lust-cp-grid {
      flex: 1 1 auto;
      overflow-y: auto;
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-auto-rows: 128px;
      gap: 8px;
      padding: 0 12px 12px;
    }
    #${VIEW_ID} .lust-cp-grid::-webkit-scrollbar { width: 6px; }
    #${VIEW_ID} .lust-cp-grid::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.12); border-radius: 3px; }

    #${VIEW_ID} .lust-cp-tile {
      position: relative;
      border-radius: 10px;
      overflow: hidden;
      cursor: pointer;
      background-color: #151a28;
      background-repeat: no-repeat;
      background-size: contain;
      background-position: center 30%;
      border: 1px solid rgba(255, 255, 255, 0.06);
      transition: border-color 0.12s, transform 0.12s;
    }
    #${VIEW_ID} .lust-cp-tile::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, transparent 50%, rgba(9, 12, 20, 0.9) 100%);
    }
    #${VIEW_ID} .lust-cp-tile:hover { border-color: rgba(167, 139, 250, 0.6); transform: translateY(-1px); }
    #${VIEW_ID} .lust-cp-tile.viewing { border-color: #a78bfa; box-shadow: 0 0 0 1px #a78bfa, 0 0 16px rgba(167, 139, 250, 0.35); }
    #${VIEW_ID} .lust-cp-tile-name {
      position: absolute;
      left: 8px;
      right: 8px;
      bottom: 7px;
      z-index: 1;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 700;
      color: #ece9f5;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    #${VIEW_ID} .lust-cp-tile-name i {
      flex: 0 0 auto;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.7);
    }
    #${VIEW_ID} .lust-cp-tile-check {
      position: absolute;
      top: 6px;
      right: 6px;
      z-index: 1;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: #7c5cff;
      color: #fff;
      font-size: 11px;
      line-height: 18px;
      text-align: center;
      box-shadow: 0 0 10px rgba(124, 92, 255, 0.7);
    }

    #${VIEW_ID} .lust-cp-foot {
      padding: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    #${VIEW_ID} .lust-cp-pick {
      width: 100%;
      height: 40px;
      border: 0;
      border-radius: 10px;
      background: linear-gradient(135deg, #7c5cff, #a78bfa);
      color: #fff;
      font-family: inherit;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.5px;
      cursor: pointer;
      box-shadow: 0 6px 18px rgba(124, 92, 255, 0.35);
      transition: filter 0.12s;
    }
    #${VIEW_ID} .lust-cp-pick:hover { filter: brightness(1.1); }
    #${VIEW_ID} .lust-cp-pick[disabled] {
      cursor: default;
      background: rgba(255, 255, 255, 0.06);
      color: #8d8a95;
      box-shadow: none;
      filter: none;
    }
    #${VIEW_ID} .lust-cp-keys {
      margin-top: 8px;
      text-align: center;
      font-size: 10px;
      color: #6f6c78;
    }
  `;

  const EXPAND_ICON =
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5 9 7M2.5 13.5 7 9"/></svg>';

  function injectCSS() {
    if (document.getElementById("lust-chroma-preview-css")) return;
    const style = document.createElement("style");
    style.id = "lust-chroma-preview-css";
    style.textContent = CSS_RULES;
    document.head.appendChild(style);
  }

  // The chroma list LUST-ChromaWheel keeps on its flyout (see lust/sync.py)
  function previewable(panel) {
    const chromas = Array.isArray(panel && panel.__lustChromas) ? panel.__lustChromas : [];
    return chromas
      .map((chroma, index) => ({ chroma, index }))
      .filter(({ chroma }) => chroma && typeof chroma.imagePath === "string" && chroma.imagePath && !chroma.imagePath.includes("://"));
  }

  function colorOf(chroma) {
    const raw = chroma.primaryColor || (chroma.colors && (chroma.colors[1] || chroma.colors[0]));
    if (!raw) return null;
    return raw.startsWith("#") ? raw : `#${raw}`;
  }

  // "Star Guardian Ahri (Ruby)" -> "Ruby"; the base skin is "Default"
  function shortName(chroma) {
    if (!chroma.name || chroma.name === "Default") return tr("Default");
    const match = /\(([^()]+)\)\s*$/.exec(chroma.name);
    return match ? match[1] : chroma.name;
  }

  function closeView() {
    const view = document.getElementById(VIEW_ID);
    if (view) view.remove();
    document.removeEventListener("keydown", onKey, true);
  }

  let keyHandler = null;
  function onKey(event) {
    if (keyHandler) keyHandler(event);
  }

  function openView(panel) {
    const items = previewable(panel);
    if (!items.length) return;
    closeView();

    const skinName = (panel.querySelector(".child-skin-name") || {}).firstChild?.textContent || "";
    const flyoutBg = (panel.querySelector(".chroma-information") || {}).style?.backgroundImage || "";
    let viewing = Math.max(0, items.findIndex(({ chroma }) => chroma.selected));

    const view = document.createElement("div");
    view.id = VIEW_ID;
    view.innerHTML = `
      <div class="lust-cp-card">
        <div class="lust-cp-stage">
          <div class="lust-cp-image"></div>
          <div class="lust-cp-arrow lust-cp-prev">&#8249;</div>
          <div class="lust-cp-arrow lust-cp-next">&#8250;</div>
          <div class="lust-cp-caption">
            <div>
              <div class="lust-cp-skin">${escapeHtml(skinName.replace(/\s*\([^()]*\)\s*$/, ""))}</div>
              <div class="lust-cp-name"><span class="lust-cp-dot"></span><span class="lust-cp-label"></span></div>
            </div>
            <div class="lust-cp-count"></div>
          </div>
        </div>
        <div class="lust-cp-side">
          <div class="lust-cp-head"><span>${escapeHtml(tr("Chromas"))} · ${items.length}</span>
            <span class="lust-cp-close" title="${escapeHtml(tr("Close"))}">&#10005;</span></div>
          <div class="lust-cp-grid"></div>
          <div class="lust-cp-foot">
            <button class="lust-cp-pick"></button>
            <div class="lust-cp-keys">${escapeHtml(tr("← → browse · Enter pick · Esc close"))}</div>
          </div>
        </div>
      </div>`;

    const stage = view.querySelector(".lust-cp-stage");
    if (flyoutBg) stage.style.backgroundImage = flyoutBg;
    const image = view.querySelector(".lust-cp-image");
    const grid = view.querySelector(".lust-cp-grid");
    const pick = view.querySelector(".lust-cp-pick");

    const tiles = items.map(({ chroma }, i) => {
      const tile = document.createElement("div");
      tile.className = "lust-cp-tile";
      tile.style.backgroundImage = `url('${chroma.imagePath}')`;
      const color = colorOf(chroma);
      tile.innerHTML =
        (chroma.selected ? '<div class="lust-cp-tile-check">&#10003;</div>' : "") +
        `<div class="lust-cp-tile-name"><i style="background:${color || "linear-gradient(135deg,#f0e6d2 48%,#be1e37 0,#be1e37 52%,#f0e6d2 0)"}"></i>` +
        `<span>${escapeHtml(shortName(chroma))}</span></div>`;
      tile.addEventListener("mouseenter", () => show(i));
      tile.addEventListener("click", () => show(i));
      tile.addEventListener("dblclick", () => choose(i));
      grid.appendChild(tile);
      return tile;
    });

    function show(i) {
      viewing = (i + items.length) % items.length;
      const { chroma } = items[viewing];
      const color = colorOf(chroma);
      image.style.backgroundImage = `url('${chroma.imagePath}')`;
      image.style.animation = "none";
      void image.offsetWidth; // restart the swap animation
      image.style.animation = "";
      stage.style.setProperty("--lust-cp-glow", color ? `${color}66` : "rgba(124, 92, 255, 0.35)");
      view.querySelector(".lust-cp-dot").style.setProperty("--lust-cp-dot", color || "#f0e6d2");
      view.querySelector(".lust-cp-label").innerHTML =
        escapeHtml(shortName(chroma)) + (chroma.selected ? ` <span class="lust-cp-badge">${escapeHtml(tr("Selected"))}</span>` : "");
      view.querySelector(".lust-cp-count").textContent = `${viewing + 1} / ${items.length}`;
      tiles.forEach((tile, n) => tile.classList.toggle("viewing", n === viewing));
      tiles[viewing].scrollIntoView({ block: "nearest" });
      pick.textContent = chroma.selected ? tr("Already selected") : tr("Pick this chroma");
      pick.disabled = !!chroma.selected;
    }

    // Picking goes through the flyout's own button, so the wheel does what it always does
    function choose(i) {
      const { chroma, index } = items[i];
      if (chroma.selected) return closeView();
      const buttons = panel.querySelectorAll(".chroma-skin-button");
      const button = buttons[index];
      closeView();
      if (button) button.click();
    }

    view.querySelector(".lust-cp-prev").addEventListener("click", () => show(viewing - 1));
    view.querySelector(".lust-cp-next").addEventListener("click", () => show(viewing + 1));
    view.querySelector(".lust-cp-close").addEventListener("click", closeView);
    pick.addEventListener("click", () => choose(viewing));
    view.addEventListener("click", (event) => {
      if (event.target === view) closeView();
    });
    view.addEventListener("wheel", (event) => {
      if (event.target.closest(".lust-cp-grid")) return;
      event.preventDefault();
      show(viewing + (event.deltaY > 0 ? 1 : -1));
    }, { passive: false });

    keyHandler = (event) => {
      if (!document.getElementById(VIEW_ID)) return;
      const keys = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 };
      if (event.key in keys) show(viewing + keys[event.key]);
      else if (event.key === "Enter") choose(viewing);
      else if (event.key === "Escape") closeView();
      else return;
      event.preventDefault();
      event.stopPropagation();
    };
    document.addEventListener("keydown", onKey, true);

    // Inside the flyout's container, so its outside-click check keeps the flyout open
    panel.appendChild(view);
    show(viewing);
  }

  function decorate(panel) {
    const info = panel.querySelector(".chroma-information");
    if (!info || info.querySelector(`.${OPEN_CLASS}`)) return;
    if (previewable(panel).length < 2) return;
    const button = document.createElement("div");
    button.className = OPEN_CLASS;
    button.title = tr("Big preview");
    button.innerHTML = EXPAND_ICON;
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      event.preventDefault();
      openView(panel);
    });
    info.appendChild(button);
    info.addEventListener("dblclick", () => openView(panel));
  }

  function watch() {
    injectCSS();
    const observer = new MutationObserver(() => {
      const panel = document.getElementById(PANEL_ID);
      if (panel) decorate(panel);
      else document.removeEventListener("keydown", onKey, true);
    });
    observer.observe(document.body, { childList: true });
    const panel = document.getElementById(PANEL_ID);
    if (panel) decorate(panel);
    console.log(`${LOG_PREFIX} ready`);
  }

  if (document.body) watch();
  else window.addEventListener("load", watch);
})();
