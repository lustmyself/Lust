"""The desktop hub's page (served by launcher/lust_hub_server.py, shown by lust_hub_shell.py)."""

from __future__ import annotations

import json

# Line icons in Lucide's style (24px grid, 2px stroke)
ICONS = {
    "lol": '<rect x="2" y="6" width="20" height="12" rx="4"/><path d="M6 12h4M8 10v4"/><circle cx="15.5" cy="11" r="1"/><circle cx="18" cy="13.5" r="1"/>',
    "spotify": '<circle cx="12" cy="12" r="10"/><path d="M7.5 10c3-1 6.5-.8 9 .8M8 13.3c2.4-.7 5-.5 7 .7M8.6 16.3c1.8-.4 3.7-.3 5.3.5"/>',
    "play": '<polygon points="7 4 20 12 7 20 7 4"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "log": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v5h6M8 13h8M8 17h8M8 9h2"/>',
    "power": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
    "restart": '<path d="M3 12a9 9 0 1 0 9-9 9.8 9.8 0 0 0-6.7 2.7L3 8"/><path d="M3 3v5h5"/>',
    "close": '<path d="M18 6 6 18M6 6l12 12"/>',
    "min": '<path d="M5 12h14"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "sync": '<path d="M21 12a9 9 0 0 1-15 6.7L3 16M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
}

PAGE = r"""<!doctype html>
<html lang="tr" translate="no">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<title>Lust</title>
<style>
  :root { --bg: #16141f; --rail: #100e17; --card: #211e2d; --card2: #292537; --line: #2e2a3d; --text: #f0eef5;
    --sub: #a3a0ad; --faint: #6c6878; --accent: #a78bfa; --accent2: #db2777; --green: #4ade80; --amber: #f5b14c;
    --red: #f87171; --yellow: #f2c94c; }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); overflow: hidden;
    font: 13px/1.45 "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; user-select: none; }
  body { display: flex; }
  svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  /* Side rail: icon tiles that grow under the mouse */
  .rail { width: 76px; background: var(--rail); display: flex; flex-direction: column; align-items: center;
    gap: 14px; padding: 18px 0; border-right: 1px solid #1c1926; }
  .logo { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center;
    background: linear-gradient(135deg, #7c3aed, #db2777); font: 800 20px Georgia, serif; color: #fff;
    box-shadow: 0 6px 18px rgba(124, 58, 237, .35); margin-bottom: 6px; }
  .tab { position: relative; width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center;
    background: #1d1a29; color: var(--sub); cursor: pointer;
    transition: transform .18s cubic-bezier(.3, 1.6, .5, 1), background .15s, color .15s; }
  .tab:hover { transform: scale(1.18); background: #2a2540; color: var(--text); }
  .tab.active { background: linear-gradient(135deg, #7c3aed, #a78bfa); color: #fff; box-shadow: 0 6px 16px rgba(124, 58, 237, .4); }
  /* Each tab in its own color: LoL in League's hextech teal, Spotify in its green */
  .tab[data-page="lol"] { color: #0ac8b9; background: rgba(10, 200, 185, .12); }
  .tab[data-page="spotify"] { color: #1db954; background: rgba(29, 185, 84, .12); }
  .tab[data-page="lol"]:hover { background: rgba(10, 200, 185, .22); color: #5ff3e6; }
  .tab[data-page="spotify"]:hover { background: rgba(29, 185, 84, .22); color: #4ade80; }
  .tab[data-page="lol"].active { background: linear-gradient(135deg, #0397ab, #0ac8b9); color: #fff; box-shadow: 0 6px 16px rgba(10, 200, 185, .4); }
  .tab[data-page="spotify"].active { background: linear-gradient(135deg, #12873d, #1ed760); color: #fff; box-shadow: 0 6px 16px rgba(29, 185, 84, .4); }
  .tab::after { content: attr(data-label); position: absolute; left: 58px; padding: 5px 10px; border-radius: 8px;
    background: #2a2540; color: var(--text); font-size: 12px; white-space: nowrap; opacity: 0; pointer-events: none;
    transform: translateX(-6px); transition: .15s; }
  .tab:hover::after { opacity: 1; transform: none; }
  .rail .spacer { flex: 1; }
  .rail .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--amber); box-shadow: 0 0 10px currentColor; }

  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .top { height: 52px; display: flex; align-items: center; gap: 10px; padding: 0 12px 0 26px; }
  .top h1 { margin: 0; font-size: 17px; font-weight: 600; }
  .pill { padding: 3px 10px; border-radius: 99px; background: var(--card); border: 1px solid var(--line); color: var(--sub); font-size: 11px; }
  .top .grow { flex: 1; align-self: stretch; }
  .win { width: 36px; height: 30px; border-radius: 8px; display: grid; place-items: center; color: var(--sub); cursor: pointer; }
  .win:hover { background: #2a2540; color: var(--text); }
  .win.x:hover { background: #c42b4a; color: #fff; }
  .win svg { width: 16px; height: 16px; }
  .page { flex: 1; overflow-y: auto; padding: 4px 26px 22px; display: none; }
  .page.active { display: block; animation: rise .25s ease; }
  @keyframes rise { from { opacity: 0; transform: translateY(6px); } }
  .page::-webkit-scrollbar { width: 8px; } .page::-webkit-scrollbar-thumb { background: #2e2a3d; border-radius: 8px; }

  .hero { border-radius: 18px; padding: 20px 22px; color: #fff; position: relative; overflow: hidden;
    background: linear-gradient(120deg, #7c3aed 0%, #a21caf 55%, #db2777 100%); }
  .hero::after { content: ""; position: absolute; width: 240px; height: 240px; right: -60px; top: -90px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 255, 255, .25), transparent 70%); }
  .hero small { opacity: .85; font-size: 12px; }
  .hero h2 { margin: 2px 0 4px; font-size: 24px; font-weight: 600; }
  .hero p { margin: 0; opacity: .9; font-size: 12px; }
  .bar { margin-top: 14px; height: 8px; border-radius: 9px; background: rgba(255, 255, 255, .22); overflow: hidden; }
  .bar > i { display: block; height: 100%; width: 0; border-radius: 9px; background: #fff; transition: width .4s; }
  .bar.busy > i { width: 30%; animation: busy 1.3s ease-in-out infinite; }
  @keyframes busy { from { margin-left: -30%; } to { margin-left: 100%; } }
  .hint { margin: 14px 2px; color: var(--yellow); font-weight: 700; font-size: 13.5px; }

  .grid { display: grid; gap: 10px; }
  .g3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .card { background: var(--card); border-radius: 14px; padding: 13px 14px; border: 1px solid transparent; }
  .tile { display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background .15s, transform .15s, border-color .15s; }
  .tile:hover { background: var(--card2); transform: translateY(-2px); border-color: var(--line); }
  .tile.off { opacity: .45; pointer-events: none; }
  .ico { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; background: #2c2840; color: var(--accent); flex: none; }
  .tile.danger .ico { background: #3a1d26; color: var(--red); }
  .tile.danger b { color: var(--red); }
  .t b { display: block; font-size: 13px; font-weight: 600; }
  .t span { color: var(--sub); font-size: 11.5px; }
  .tile .end { margin-left: auto; width: 8px; height: 8px; border-radius: 50%; background: var(--faint); }
  .section { margin: 16px 2px 8px; color: var(--faint); font-size: 11.5px; font-weight: 600; letter-spacing: .4px; text-transform: uppercase; }

  .appear { display: flex; align-items: center; gap: 12px; }
  .seg { margin-left: auto; display: flex; background: #15131e; border: 1px solid var(--line); border-radius: 99px; padding: 3px; }
  .seg button { border: 0; background: none; color: var(--sub); font: inherit; font-weight: 600; padding: 7px 16px; border-radius: 99px; cursor: pointer; }
  .seg button:hover:not(:disabled) { color: var(--text); }
  .seg button.on { background: var(--accent); color: #15111f; }
  .seg button:disabled { opacity: .4; cursor: default; }

  .rose { margin-top: 12px; display: flex; align-items: center; gap: 12px; border-color: #7f1d1d; background: #2c1719; }
  .rose .ico { background: #3a1d26; color: var(--red); }
  .rose .t span { display: block; max-width: 560px; }
  .btn.danger { background: #c42b4a; color: #fff; }
  .prompt { margin-top: 12px; display: flex; align-items: center; gap: 12px; border-color: var(--accent); background: #2a2340; }
  .btn { border: 0; font: inherit; font-weight: 600; padding: 9px 18px; border-radius: 99px; cursor: pointer; background: #2c2840; color: var(--text); }
  .btn:hover { filter: brightness(1.15); }
  .btn.primary { background: var(--accent); color: #15111f; }
  .btn:disabled { opacity: .45; cursor: default; filter: none; }

  .ver { display: flex; gap: 16px; align-items: center; margin-top: 10px; }
  .ver .mark { width: 64px; height: 64px; border-radius: 16px; display: grid; place-items: center; flex: none;
    background: linear-gradient(135deg, #2a2340, #3b2a55); color: var(--accent); font: 800 26px Georgia, serif; }
  .ver ul { margin: 6px 0 0; padding-left: 16px; color: var(--sub); font-size: 11.5px; }
  .round { margin-left: auto; width: 52px; height: 52px; border-radius: 50%; border: 0; display: grid; place-items: center; flex: none;
    background: var(--accent); color: #15111f; cursor: pointer; box-shadow: 0 6px 18px rgba(167, 139, 250, .35); transition: transform .15s; }
  .round:hover { transform: scale(1.08); }
  .round:disabled { opacity: .4; cursor: default; transform: none; }

  .themes { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  .theme { background: var(--card); border-radius: 14px; padding: 7px 7px 10px; cursor: pointer; border: 2px solid transparent;
    transition: transform .15s, border-color .15s; }
  .theme:hover { transform: translateY(-3px) scale(1.02); }
  .theme.on { border-color: var(--accent); }
  .shot { aspect-ratio: 16 / 9; border-radius: 9px; background-size: cover; background-position: top left; position: relative; overflow: hidden; }
  .shot.mock::before { content: ""; position: absolute; left: 5%; top: 7%; bottom: 22%; width: 22%; border-radius: 4px; background: var(--panel); }
  .shot.mock::after { content: ""; position: absolute; left: 5%; right: 5%; bottom: 7%; height: 10%; border-radius: 4px; background: var(--panel); }
  .shot.mock i { position: absolute; left: 31%; top: 14%; width: 34%; height: 8%; border-radius: 3px; background: var(--acc); }
  .shot.mock b { position: absolute; left: 31%; top: 32%; width: 64%; height: 36%; border-radius: 4px;
    background: linear-gradient(90deg, var(--panel) 0 30%, transparent 30% 35%, var(--panel) 35% 65%, transparent 65% 70%, var(--panel) 70%); }
  .theme span { display: block; margin: 7px 3px 0; font-size: 12px; font-weight: 600; color: var(--sub); }
  .theme.on span { color: var(--text); }
  .sticky { position: sticky; bottom: -22px; margin: 14px -26px -22px; padding: 12px 26px 16px; display: flex; gap: 10px;
    background: linear-gradient(transparent, var(--bg) 30%); }
  .sticky .btn { flex: 1; padding: 12px; }
  .note { color: var(--faint); font-size: 11px; margin-top: 10px; }

  #toast { position: fixed; left: 50%; bottom: 22px; transform: translate(-50%, 20px); opacity: 0; transition: .25s;
    background: #2a2540; border: 1px solid #4b3f73; color: var(--text); padding: 10px 18px; border-radius: 99px; max-width: 80%; pointer-events: none; }
  #toast.show { opacity: 1; transform: translate(-50%, 0); }
  #lost { position: fixed; inset: 0; display: none; place-items: center; background: rgba(16, 14, 23, .9); color: var(--sub); }
</style>
</head>
<body>
<nav class="rail">
  <div class="logo">L</div>
  <div class="tab active" data-page="lol" data-label="LoL">__lol__</div>
  <div class="tab" data-page="spotify" data-label="Spotify">__spotify__</div>
  <div class="spacer"></div>
  <div class="dot" id="dot" title=""></div>
</nav>
<div class="main">
  <header class="top pywebview-drag-region">
    <h1 id="title">LoL</h1><span class="pill">__VERSION__</span>
    <div class="grow pywebview-drag-region"></div>
    <div class="win" id="w-min" title="Küçült">__min__</div>
    <div class="win x" id="w-close" title="Kapat">__close__</div>
  </header>

  <section class="page active" id="page-lol">
    <div class="hero">
      <small id="h-small">Hoş geldin</small>
      <h2 id="h-title">Lust başlıyor</h2>
      <p id="h-sub"></p>
      <div class="bar busy" id="h-bar"><i></i></div>
    </div>
    <div class="hint">Oyun ayarlarınızı LoL istemcisindeki LUST sekmesine tıklayarak ayarlayabilirsiniz.</div>
    <div class="card rose" id="rose" hidden>
      <div class="ico">__close__</div>
      <div class="t"><b>Rose da kurulu</b><span>İkisi aynı anda çalışınca LoL'de Rose'un gül simgesi çıkar ve çakışırlar. Lust, Rose'un yaptığı her şeyi zaten yapıyor.</span></div>
      <button class="btn danger" style="margin-left:auto" data-act="rose_uninstall">Rose'u kaldır</button>
    </div>
    <div class="card prompt" id="prompt" hidden>
      <div class="t"><b id="q-title"></b><span id="q-body"></span></div>
      <button class="btn primary" style="margin-left:auto" data-act="prompt" data-body='{"accept":true}'>Kur</button>
      <button class="btn" data-act="prompt" data-body='{"accept":false}'>Şimdi değil</button>
    </div>
    <div class="card appear" style="margin-top:12px">
      <div class="ico">__user__</div>
      <div class="t"><b>Görün</b><span id="ap-sub"></span></div>
      <div class="seg" id="seg">
        <button data-status="online">Çevrimiçi</button><button data-status="offline">Çevrimdışı</button><button data-status="mobile">Mobil</button>
      </div>
    </div>
    <div class="section">Hızlı işlemler</div>
    <div class="grid g3">
      <div class="card tile" id="a-league" data-act="league"><div class="ico">__play__</div><div class="t"><b id="a-league-t">League'i aç</b><span>Lust Offline üzerinden</span></div></div>
      <div class="card tile" data-act="mods"><div class="ico">__folder__</div><div class="t"><b>Mod klasörü</b><span>Gezginde aç</span></div></div>
      <div class="card tile" data-act="log"><div class="ico">__log__</div><div class="t"><b>Logu kopyala</b><span>Discord'a yapıştır</span></div></div>
      <div class="card tile" data-act="autostart"><div class="ico">__power__</div><div class="t"><b>Windows ile başlat</b><span id="auto-sub"></span></div><i class="end" id="auto-dot"></i></div>
      <div class="card tile" id="a-restart" data-act="restart"><div class="ico">__restart__</div><div class="t"><b>Yeniden başlat</b><span>Lust'ı yeniden başlat</span></div></div>
      <div class="card tile danger" id="a-quit"><div class="ico">__close__</div><div class="t"><b id="quit-t">Lust'ı kapat</b><span>Tamamen kapat</span></div></div>
    </div>
    <div class="card ver">
      <div class="mark">L</div>
      <div class="t"><b>Lust __VERSION__</b><span id="v-sub"></span><ul id="news"></ul></div>
      <button class="round" id="v-btn" title="">__sync__</button>
    </div>
  </section>

  <section class="page" id="page-spotify">
    <div class="grid g2">
      <div class="card tile" style="cursor:default"><div class="ico">__spotify__</div><div class="t"><b>Spotify</b><span id="sp-sub"></span></div><i class="end" id="sp-dot"></i></div>
      <div class="card tile" data-act="spotify_auto"><div class="ico">__sync__</div><div class="t"><b>Otomatik uygula</b><span>Spotify güncellenince</span></div><i class="end" id="sp-auto"></i></div>
    </div>
    <div class="section">Tema</div>
    <div class="themes" id="themes"></div>
    <div class="note">Spicetify ile çalışır. Spotify'ın Microsoft Store sürümü desteklenmez; spotify.com'dan indirilen sürüm gerekir.</div>
    <div class="sticky">
      <button class="btn primary" id="sp-apply">Temayı uygula</button>
      <button class="btn" id="sp-restore">Orijinale döndür</button>
    </div>
  </section>
</div>
<div id="toast"></div>
<div id="lost">Lust yeniden başlıyor…</div>
<script>
const TOKEN = __TOKEN__;
const THEMES = __THEMES__;
const $ = (id) => document.getElementById(id);
let state = null, toastId = null, quitArmed = 0, choice = null, newsKey = "", failures = 0;

async function api(path, body) {
  const r = await fetch(path, { method: body ? "POST" : "GET", headers: { "X-Lust-Hub": TOKEN, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined });
  if (r.status === 403) { location.reload(); throw new Error("stale"); }
  return r.json();
}
const act = (name, body = {}) => api(`/api/action/${name}`, body).then(() => setTimeout(poll, 250)).catch(() => {});

function showToast(text) {
  $("toast").textContent = text; $("toast").classList.add("show");
  clearTimeout(showToast.t); showToast.t = setTimeout(() => $("toast").classList.remove("show"), 3800);
}
function ago(s) {
  if (!s) return "henüz yok";
  const m = Math.floor((Date.now() / 1000 - s) / 60);
  return m < 1 ? "az önce" : `${m} dk önce`;
}
const STATUS = { online: "Çevrimiçi", offline: "Çevrimdışı", mobile: "Mobil" };

function buildThemes() {
  $("themes").replaceChildren(...THEMES.map((t) => {
    const card = document.createElement("div");
    card.className = "theme"; card.dataset.key = t.key;
    const shot = document.createElement("div");
    shot.className = "shot" + (t.preview ? "" : " mock");
    shot.style.background = t.bg;
    if (t.preview) {
      const img = new Image();
      img.onload = () => { shot.style.backgroundImage = `url(${img.src})`; };
      img.src = `/preview/${t.key}.png`;
    } else {
      const light = parseInt(t.bg.slice(1, 3), 16) + parseInt(t.bg.slice(3, 5), 16) + parseInt(t.bg.slice(5, 7), 16) > 450;
      shot.style.setProperty("--panel", light ? "rgba(0,0,0,.12)" : "rgba(255,255,255,.08)");
      shot.style.setProperty("--acc", t.accent);
      shot.append(document.createElement("i"), document.createElement("b"));
    }
    const label = document.createElement("span"); label.textContent = t.label;
    card.append(shot, label);
    card.addEventListener("click", () => { choice = t.key; drawThemes(); });
    return card;
  }));
}
function drawThemes() {
  document.querySelectorAll(".theme").forEach((c) => c.classList.toggle("on", c.dataset.key === choice));
}

function render(s) {
  state = s;
  const starting = s.phase !== "ready";
  const ready = s.running && s.ready;
  $("dot").style.background = ready ? "var(--green)" : "var(--amber)";
  $("dot").style.color = ready ? "var(--green)" : "var(--amber)";
  $("dot").title = ready ? "Hazır" : "Başlıyor";
  const off = s.offline || {};
  const bits = [s.league ? "League açık" : "League kapalı", s.ready ? "Skinler hazır" : "Skinler hazırlanıyor"];
  if (off.running) bits.push(STATUS[off.status] || "Çevrimiçi");
  $("h-small").textContent = starting ? (s.detail || "Hazırlanıyor") : "Hoş geldin";
  $("h-title").textContent = starting ? (s.status || "Lust başlıyor") : (ready ? "Lust hazır" : "Lust hazırlanıyor");
  $("h-sub").textContent = starting ? (s.transfer || bits.join(" · ")) : bits.join(" · ");
  const busy = s.progress === null || s.progress === undefined;
  $("h-bar").hidden = !starting;
  $("h-bar").classList.toggle("busy", busy);
  $("h-bar").firstElementChild.style.width = busy ? "" : `${s.progress}%`;

  $("rose").hidden = !(s.rose && s.rose.installed);
  $("prompt").hidden = !s.prompt;
  if (s.prompt) {
    $("q-title").textContent = `Lust ${s.prompt.version} kurulmaya hazır`;
    $("q-body").textContent = `Sendeki sürüm ${s.prompt.current}. Şimdi kurulsun mu?`;
  }
  $("ap-sub").textContent = off.running ? (STATUS[off.status] || "Çevrimiçi") : "Seçmek için League'i buradan aç";
  document.querySelectorAll("#seg button").forEach((b) => {
    b.disabled = !off.running || starting;
    b.classList.toggle("on", !!off.running && off.status === b.dataset.status);
  });
  $("a-league").classList.toggle("off", s.league);
  $("a-league-t").textContent = s.league ? "League açık" : "League'i aç";
  $("auto-sub").textContent = s.autostart ? "Açık" : "Kapalı";
  $("auto-dot").style.background = s.autostart ? "var(--accent)" : "var(--faint)";
  $("a-restart").classList.toggle("off", !s.running);
  $("quit-t").textContent = Date.now() - quitArmed < 3000 ? "Tekrar tıkla" : "Lust'ı kapat";

  $("v-sub").textContent = s.update_available ? `Yeni sürüm ${s.latest}` : `Güncel · son kontrol ${ago(s.checked_at)}`;
  $("v-sub").style.color = s.update_available ? "var(--accent)" : "";
  $("v-btn").innerHTML = s.update_available ? ICON_DOWNLOAD : ICON_SYNC;
  $("v-btn").title = s.update_available ? "Güncelle" : "Şimdi kontrol et";
  $("v-btn").disabled = starting;
  const items = ((s.news || {}).items || []).slice(0, 3);
  if (JSON.stringify(items) !== newsKey) {
    newsKey = JSON.stringify(items);
    $("news").replaceChildren(...items.map((x) => { const li = document.createElement("li"); li.textContent = x; return li; }));
  }

  const sp = s.spotify || {};
  const label = (THEMES.find((t) => t.key === sp.theme) || {}).label || "Orijinal";
  $("sp-sub").textContent = sp.installed ? `${sp.version || ""} · ${sp.busy ? "Uygulanıyor…" : "Tema: " + label}` :
    (sp.store ? "Store sürümü desteklenmez" : "Bulunamadı");
  $("sp-dot").style.background = !sp.installed ? "var(--red)" : sp.busy ? "var(--amber)" : "var(--green)";
  $("sp-auto").style.background = sp.auto ? "var(--accent)" : "var(--faint)";
  if (!choice) { choice = sp.theme || "luminous"; drawThemes(); }
  $("sp-apply").disabled = $("sp-restore").disabled = !sp.installed || !!sp.busy;

  if (s.toast && s.toast.id !== toastId) {
    if (toastId !== null) showToast(s.toast.text);
    toastId = s.toast.id;
  }
  if (toastId === null) toastId = 0;
  if (s.prompt) showPage("lol");
}

async function poll() {
  try { render(await api("/api/state")); failures = 0; $("lost").style.display = "none"; }
  catch (e) { if (++failures >= 3) $("lost").style.display = "grid"; }
}
function showPage(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.page === name));
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
  $("title").textContent = name === "lol" ? "LoL" : "Spotify";
}

const ICON_SYNC = `__sync__`, ICON_DOWNLOAD = `__download__`;
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showPage(t.dataset.page)));
document.querySelectorAll("[data-act]").forEach((el) => el.addEventListener("click", () =>
  act(el.dataset.act, el.dataset.body ? JSON.parse(el.dataset.body) : {})));
document.querySelectorAll("#seg button").forEach((b) => b.addEventListener("click", () => act("status", { value: b.dataset.status })));
$("a-quit").addEventListener("click", () => {
  if (Date.now() - quitArmed < 3000) { act("quit"); return; }
  quitArmed = Date.now(); state && render(state); setTimeout(() => state && render(state), 3100);
});
$("v-btn").addEventListener("click", () => act(state && state.update_available ? "update" : "check"));
$("sp-apply").addEventListener("click", () => act("spotify_apply", { theme: choice }));
$("sp-restore").addEventListener("click", () => act("spotify_apply", { theme: "original" }));
const shell = () => window.pywebview && window.pywebview.api;
$("w-min").addEventListener("click", () => shell() && shell().minimize());
$("w-close").addEventListener("click", () => shell() ? shell().close() : window.close());
document.addEventListener("contextmenu", (e) => e.preventDefault());
buildThemes();
poll();
setInterval(poll, 800);
</script>
</body>
</html>
"""


def _svg(path: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


def render(token: str, version: str, themes: list) -> str:
    page = PAGE.replace("__TOKEN__", json.dumps(token)).replace("__VERSION__", version)
    page = page.replace("__THEMES__", json.dumps(themes, ensure_ascii=False))
    for name, path in ICONS.items():
        page = page.replace(f"__{name}__", _svg(path))
    return page
