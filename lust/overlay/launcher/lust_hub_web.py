"""The desktop hub's page (served by launcher/lust_hub_server.py, shown by lust_hub_shell.py)."""

from __future__ import annotations

import json

# Line icons in Lucide's style (24px grid, 2px stroke)
# League's L in a ring, in hextech gold and blue: the LoL tab's mark
LOL_MARK = (
    '<svg class="lol-mark" viewBox="0 0 24 24" aria-hidden="true">'
    '<defs>'
    '<linearGradient id="hx-gold" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#f0e6d2"/><stop offset=".45" stop-color="#c8aa6e"/>'
    '<stop offset="1" stop-color="#785a28"/></linearGradient>'
    '<linearGradient id="hx-blue" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#cdfafa"/><stop offset=".5" stop-color="#0ac8b9"/>'
    '<stop offset="1" stop-color="#005a82"/></linearGradient>'
    '</defs>'
    '<circle cx="13.2" cy="12" r="8.3" fill="none" stroke="url(#hx-blue)" stroke-width="1.3" opacity=".85"/>'
    '<path d="M4.6 3.4h5.6l-1.1 1.3v12.9h8.3l1.9-2.4-.95 5.2H4.3l1.5-1.7V4.7z" '
    'fill="url(#hx-gold)" stroke="#3c2a12" stroke-width=".35" stroke-linejoin="round"/>'
    '</svg>'
)

ICONS = {
    "bolt": '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
    "prev": '<path d="M19 20 9 12l10-8z"/><path d="M5 19V5"/>',
    "next": '<path d="m5 4 10 8-10 8z"/><path d="M19 5v14"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "vol": '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
    "volx": '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="m22 9-6 6M16 9l6 6"/>',
    "gear": '<path d="M12.2 2h-.4a2 2 0 0 0-2 2v.2a2 2 0 0 1-1 1.7l-.4.3a2 2 0 0 1-2 0l-.2-.1a2 2 0 0 0-2.7.7l-.2.4a2 2 0 0 0 .7 2.7l.2.1a2 2 0 0 1 1 1.7v.6a2 2 0 0 1-1 1.7l-.2.1a2 2 0 0 0-.7 2.7l.2.4a2 2 0 0 0 2.7.7l.2-.1a2 2 0 0 1 2 0l.4.3a2 2 0 0 1 1 1.7v.2a2 2 0 0 0 2 2h.4a2 2 0 0 0 2-2v-.2a2 2 0 0 1 1-1.7l.4-.3a2 2 0 0 1 2 0l.2.1a2 2 0 0 0 2.7-.7l.2-.4a2 2 0 0 0-.7-2.7l-.2-.1a2 2 0 0 1-1-1.7v-.6a2 2 0 0 1 1-1.7l.2-.1a2 2 0 0 0 .7-2.7l-.2-.4a2 2 0 0 0-2.7-.7l-.2.1a2 2 0 0 1-2 0l-.4-.3a2 2 0 0 1-1-1.7V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "sparkle": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    "plusbox": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M12 8v8M8 12h8"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/>',
    "shield": '<path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
    "wind": '<path d="M3 8h10a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
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
    "map": '<path d="M9 4 3 6.5v13.5L9 17.5l6 2.5 6-2.5V4l-6 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
    "font": '<path d="M4 7V5h16v2M9 19h6M12 5v14"/>',
    "frame": '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="12" cy="10" r="3"/><path d="M6.5 20a5.5 5.5 0 0 1 11 0"/>',
    "badge": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="10" r="3"/><path d="M6.8 18.4a6 6 0 0 1 10.4 0"/>',
    "back": '<path d="M15 18 9 12l6-6"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "max": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "restore": '<rect x="4" y="8" width="12" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2"/>',
    "brush": '<path d="M9.06 11.9 17.4 3.6a2.1 2.1 0 1 1 3 3l-8.36 8.3"/><path d="M7 14a3 3 0 0 0-3 3c0 1.3-1 2-2 2 1 1.7 3 2 4 2a4 4 0 0 0 4-4 3 3 0 0 0-3-3z"/>',
    "shirt": '<path d="M20.4 3.5 16 2a4 4 0 0 1-8 0L3.6 3.5a2 2 0 0 0-1.3 2.2l.6 3.5a1 1 0 0 0 1 .8H6v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V10h2.2a1 1 0 0 0 1-.8l.6-3.5a2 2 0 0 0-1.4-2.2z"/>',
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
    --red: #f87171; --yellow: #f2c94c; --tint: 167, 139, 250; }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); overflow: hidden;
    font: 13px/1.45 "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; user-select: none; }
  body { display: flex; }
  /* Behind everything: the last champion's splash, blurred and dimmed, under two slow lights
     tinted with that splash's own colour (--tint, set when the splash loads) */
  .ambient { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
  .amb-art { position: absolute; inset: -12%; background-size: cover; background-position: center 25%;
    filter: blur(48px) saturate(1.5) brightness(.8); opacity: 0; transform: scale(1.1); transition: opacity 1.2s ease; }
  .amb-art.on { opacity: .9; }
  .ambient::after { content: ""; position: absolute; inset: 0;
    background: radial-gradient(130% 100% at 65% 10%, rgba(14, 12, 22, .05) 0%, rgba(14, 12, 22, .4) 55%, rgba(12, 10, 18, .8) 100%); }
  .blob { position: absolute; width: 520px; height: 520px; border-radius: 50%; filter: blur(90px); opacity: .5;
    background: radial-gradient(circle, rgba(var(--tint), .9), transparent 65%); transition: background 1.2s ease; }
  .blob.b1 { left: -140px; top: -160px; animation: float1 26s ease-in-out infinite alternate; }
  .blob.b2 { right: -180px; bottom: -220px; opacity: .3;
    background: radial-gradient(circle, rgba(10, 200, 185, .8), transparent 65%); animation: float2 32s ease-in-out infinite alternate; }
  @keyframes float1 { to { transform: translate(180px, 120px) scale(1.15); } }
  @keyframes float2 { to { transform: translate(-160px, -90px) scale(1.1); } }
  .rail, .main { position: relative; z-index: 1; }
  /* The rail sits above the page so a tab's label is never hidden behind it */
  .rail { z-index: 3; }
  svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  /* Side rail: icon tiles that grow under the mouse */
  .rail { width: 76px; background: rgba(13, 11, 20, .62); backdrop-filter: blur(18px); display: flex;
    flex-direction: column; align-items: center; gap: 14px; padding: 18px 0; border-right: 1px solid rgba(255, 255, 255, .05); }
  .tab { position: relative; width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center;
    background: #1d1a29; color: var(--sub); cursor: pointer;
    transition: transform .18s cubic-bezier(.3, 1.6, .5, 1), background .15s, color .15s; }
  .tab:hover { transform: scale(1.18); background: #2a2540; color: var(--text); }
  .tab.active { background: linear-gradient(135deg, #7c3aed, #a78bfa); color: #fff; box-shadow: 0 6px 16px rgba(124, 58, 237, .4); }
  /* Each tab in its own color: LoL in League's hextech teal, Spotify in its green */
  .tab[data-page="lol"] { background: #0a1428; box-shadow: inset 0 0 0 1px rgba(200, 170, 110, .35); }
  .lol-mark { width: 26px; height: 26px; filter: drop-shadow(0 0 4px rgba(10, 200, 185, .25)); }
  .tab[data-page="spotify"] { color: #1db954; background: rgba(29, 185, 84, .12); }
  .tab[data-page="maps"] { color: #5eead4; background: rgba(94, 234, 212, .1); }
  .tab[data-page="maps"]:hover { background: rgba(94, 234, 212, .2); color: #99f6e4; }
  .tab[data-page="maps"].active { background: linear-gradient(135deg, #0f766e, #2dd4bf); color: #04201d; box-shadow: 0 6px 16px rgba(45, 212, 191, .35); }
  .tab[data-page="fonts"] { color: #93c5fd; background: rgba(147, 197, 253, .1); }
  .tab[data-page="fonts"]:hover { background: rgba(147, 197, 253, .2); color: #dbeafe; }
  .tab[data-page="fonts"].active { background: linear-gradient(135deg, #1d4ed8, #60a5fa); color: #06142e; box-shadow: 0 6px 16px rgba(96, 165, 250, .35); }
  .tab[data-page="skins"] { color: #f472b6; background: rgba(244, 114, 182, .1); }
  .tab[data-page="skins"]:hover { background: rgba(244, 114, 182, .2); color: #fbcfe8; }
  .tab[data-page="skins"].active { background: linear-gradient(135deg, #be185d, #f472b6); color: #2a0718; box-shadow: 0 6px 16px rgba(244, 114, 182, .35); }
  .tab[data-page="profile"] { color: #fb923c; background: rgba(251, 146, 60, .1); }
  .tab[data-page="profile"]:hover { background: rgba(251, 146, 60, .2); color: #fed7aa; }
  .tab[data-page="profile"].active { background: linear-gradient(135deg, #c2410c, #fb923c); color: #2a1004; box-shadow: 0 6px 16px rgba(251, 146, 60, .35); }
  .tab[data-page="icon"] { color: #facc15; background: rgba(250, 204, 21, .1); }
  .tab[data-page="icon"]:hover { background: rgba(250, 204, 21, .2); color: #fef08a; }
  .tab[data-page="icon"].active { background: linear-gradient(135deg, #a16207, #facc15); color: #271d02; box-shadow: 0 6px 16px rgba(250, 204, 21, .35); }
  .tab[data-page="settings"] { color: #c8aa6e; background: rgba(200, 170, 110, .1); }
  .tab[data-page="settings"]:hover { background: rgba(200, 170, 110, .2); color: #f0e6d2; }
  .tab[data-page="settings"].active { background: linear-gradient(135deg, #785a28, #c8aa6e); color: #1e2328;
    box-shadow: 0 6px 16px rgba(200, 170, 110, .35); }
  .tab[data-page="settings"]:hover svg { animation: spin 1.2s ease; }
  @keyframes spin { to { transform: rotate(180deg); } }
  .tab[data-page="lol"]:hover { background: #0e1f36; box-shadow: inset 0 0 0 1px rgba(200, 170, 110, .6); }
  .tab[data-page="spotify"]:hover { background: rgba(29, 185, 84, .22); color: #4ade80; }
  .tab[data-page="lol"].active { background: radial-gradient(circle at 50% 40%, #0a323c, #091428 75%);
    box-shadow: inset 0 0 0 1.5px #c8aa6e, 0 6px 18px rgba(10, 200, 185, .35); }
  .tab[data-page="spotify"].active { background: linear-gradient(135deg, #12873d, #1ed760); color: #fff; box-shadow: 0 6px 16px rgba(29, 185, 84, .4); }
  .tab::after { content: attr(data-label); position: absolute; left: 58px; padding: 5px 10px; border-radius: 8px;
    background: #2a2540; color: var(--text); font-size: 12px; white-space: nowrap; opacity: 0; pointer-events: none;
    transform: translateX(-6px); transition: .15s; z-index: 5; box-shadow: 0 6px 18px rgba(0, 0, 0, .45);
    border: 1px solid rgba(255, 255, 255, .08); }
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
  #page-lol.active { display: flex; flex-direction: column; }
  #page-lol > * { flex: none; }
  /* Extra height goes mostly to the splash card, the rest to the quick actions */
  #page-lol > .hero { flex: 2 0 auto; max-height: 48vh; }
  .hero small { display: block; line-height: 1.5; }
  #page-lol > .acts { flex: 1 1 auto; min-height: 194px; max-height: 380px; }
  @keyframes rise { from { opacity: 0; transform: translateY(10px) scale(.985); } }
  .page::-webkit-scrollbar { width: 8px; } .page::-webkit-scrollbar-thumb { background: #2e2a3d; border-radius: 8px; }

  .hero { border-radius: 20px; min-height: 150px; color: #fff; position: relative; overflow: hidden; display: flex;
    align-items: flex-end; gap: 16px; padding: 20px 22px;
    background: #0b0c12; }
  .hero-art { position: absolute; inset: 0; background-size: cover; background-position: center 22%; opacity: 0;
    transform: scale(1.08); transition: opacity .8s ease; animation: drift 24s ease-in-out infinite alternate; }
  .hero-art.on { opacity: 1; }
  .hero { box-shadow: 0 18px 50px rgba(var(--tint), .22), inset 0 0 0 1px rgba(255, 255, 255, .07); transition: box-shadow 1.2s ease; }
  .hero::before { content: ""; position: absolute; inset: 0; z-index: 1;
    background: linear-gradient(90deg, rgba(7, 8, 13, .9) 0%, rgba(7, 8, 13, .55) 42%, rgba(7, 8, 13, .05) 75%),
      linear-gradient(0deg, rgba(7, 8, 13, .55) 0%, transparent 45%); }
  @keyframes drift { from { transform: scale(1.08) translateX(0); } to { transform: scale(1.14) translateX(-2%); } }
  .hero-body, .hero-last { position: relative; z-index: 2; }
  .hero-body { flex: 1; min-width: 0; }
  .hero small { opacity: .8; font-size: 12px; }
  .hero h2 { margin: 2px 0 8px; font-size: 18px; font-weight: 600; letter-spacing: .1px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }
  .hero h2 i { font-style: normal; font-weight: 400; opacity: .6; font-size: inherit; }
  .hero p { margin: 8px 0 0; opacity: .85; font-size: 12px; }
  .hero-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .hero-cut { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 8px; font-size: 11.5px; opacity: .92; }
  .hero-cut .cut { display: inline-flex; align-items: center; gap: 5px; }
  .hero-cut .cut::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--c); box-shadow: 0 0 8px var(--c); }
  .hero-cut .gm { --c: #f87171; } .hero-cut .ch { --c: #facc15; }
  .hero-cut .need { padding: 2px 8px; border-radius: 99px; background: rgba(250, 204, 21, .16); color: #fde68a; font-weight: 600; }
  .cutbar { flex: 1 1 120px; max-width: 220px; height: 6px; border-radius: 99px; background: rgba(255, 255, 255, .12); overflow: hidden; }
  .cutbar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #c8aa6e, #facc15);
    box-shadow: 0 0 10px rgba(250, 204, 21, .6); transition: width .8s cubic-bezier(.2, .8, .2, 1); }
  .chip { padding: 4px 10px; border-radius: 99px; font-size: 11.5px; font-weight: 600; background: rgba(255, 255, 255, .14);
    border: 1px solid rgba(255, 255, 255, .18); backdrop-filter: blur(8px); }
  .chip.rank { background: rgba(var(--tint), .35); border-color: rgba(var(--tint), .6); }
  .hero-last { flex: none; text-align: right; padding: 12px 14px; border-radius: 14px; background: rgba(10, 8, 18, .45);
    border: 1px solid rgba(255, 255, 255, .12); backdrop-filter: blur(10px); }
  .hero-last b { display: block; font-size: 16px; margin: 2px 0; }
  .hero-last span { display: block; font-size: 11.5px; opacity: .85; }
  .hl-result { font-weight: 700; opacity: 1 !important; }
  .hl-result.win { color: #4ade80; } .hl-result.loss { color: #f87171; }

  /* Lust's icons: a purple-to-pink gradient line on a soft tinted tile */
  .ico { background: linear-gradient(135deg, rgba(124, 58, 237, .22), rgba(219, 39, 119, .16)) !important;
    border: 1px solid rgba(167, 139, 250, .22); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .06); }
  .ico svg { stroke: url(#lust-grad); filter: drop-shadow(0 0 6px rgba(167, 139, 250, .35)); }
  .tile.danger .ico svg { stroke: var(--red); filter: none; }

  /* Motion: cards rise in turn, everything answers a press */
  .page.active > * { animation: rise .45s cubic-bezier(.2, .8, .2, 1) both; }
  .page.active > *:nth-child(2) { animation-delay: .05s; } .page.active > *:nth-child(3) { animation-delay: .1s; }
  .page.active > *:nth-child(4) { animation-delay: .15s; } .page.active > *:nth-child(5) { animation-delay: .2s; }
  .page.active > *:nth-child(6) { animation-delay: .25s; } .page.active > *:nth-child(7) { animation-delay: .3s; }
  .grid > .tile { animation: rise .45s cubic-bezier(.2, .8, .2, 1) both; }
  .grid > .tile:nth-child(2) { animation-delay: .06s; } .grid > .tile:nth-child(3) { animation-delay: .12s; }
  .grid > .tile:nth-child(4) { animation-delay: .18s; } .grid > .tile:nth-child(5) { animation-delay: .24s; }
  .grid > .tile:nth-child(6) { animation-delay: .3s; }
  .tile:active, .btn:active, .seg button:active, .theme:active, .auto:active { transform: scale(.96); transition-duration: .06s; }
  .round:active { transform: scale(.9); }
  .tile .ico { transition: transform .25s cubic-bezier(.3, 1.6, .5, 1); }
  .tile:hover .ico { transform: rotate(-6deg) scale(1.08); }
  .switch::after { transition: left .3s cubic-bezier(.3, 1.6, .5, 1), background .15s !important; }
  .seg button { transition: background .2s, color .2s, transform .1s; }
  #toast { transition: opacity .25s, transform .4s cubic-bezier(.3, 1.6, .5, 1) !important; }
  .bar { margin-top: 14px; height: 8px; border-radius: 9px; background: rgba(255, 255, 255, .22); overflow: hidden; }
  .bar > i { display: block; height: 100%; width: 0; border-radius: 9px; background: #fff; transition: width .4s; }
  .bar.busy > i { width: 30%; animation: busy 1.3s ease-in-out infinite; }
  @keyframes busy { from { margin-left: -30%; } to { margin-left: 100%; } }
  .tip { margin-left: 6px; padding: 4px 12px 4px 10px; border-radius: 99px; font-size: 11.5px; color: #d9c79a;
    background: linear-gradient(90deg, rgba(200, 170, 110, .14), rgba(200, 170, 110, .04));
    border: 1px solid rgba(200, 170, 110, .22); white-space: nowrap; display: inline-flex; align-items: center; gap: 7px; }
  .tip::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: #c8aa6e; box-shadow: 0 0 8px #c8aa6e; }
  .tip b { color: #f0e6d2; font-weight: 600; letter-spacing: .4px; }
  .hero { margin-bottom: 14px; }

  .grid { display: grid; gap: 10px; }
  .g3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dismiss { flex: none; width: 30px; height: 30px; margin-left: 4px; border: 0; border-radius: 9px; display: grid; place-items: center;
    background: rgba(255, 255, 255, .05); color: var(--sub); cursor: pointer; transition: background .15s, color .15s; }
  .dismiss:hover { background: rgba(255, 255, 255, .12); color: #fff; }
  .dismiss svg { width: 13px; height: 13px; }
  .card { background: rgba(30, 27, 42, .42); backdrop-filter: blur(16px) saturate(1.2); border-radius: 14px;
    padding: 13px 14px; border: 1px solid rgba(255, 255, 255, .06); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05); }
  .tile { display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background .15s, transform .15s, border-color .15s; }
  .tile:hover { background: rgba(48, 43, 64, .7); transform: translateY(-2px); border-color: rgba(var(--tint), .35);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .06), 0 8px 24px rgba(var(--tint), .12); }
  .tile.off { opacity: .45; pointer-events: none; }
  .ico { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; background: #2c2840; color: var(--accent); flex: none; }
  .tile.danger .ico { background: #3a1d26; color: var(--red); }
  .tile.danger b { color: var(--red); }
  .t b { display: block; font-size: 13px; font-weight: 600; }
  .t span { color: var(--sub); font-size: 11.5px; }
  .tile .end { margin-left: auto; width: 8px; height: 8px; border-radius: 50%; background: var(--faint); }

  /* Quick actions: League's play card, and coloured actions beside it */
  .acts { display: grid; grid-template-columns: 1.15fr 1fr; grid-template-rows: repeat(3, minmax(58px, 1fr)); gap: 10px; }
  .acts > * { animation: rise .45s cubic-bezier(.2, .8, .2, 1) both; }
  .acts > :nth-child(2) { animation-delay: .06s; } .acts > :nth-child(3) { animation-delay: .12s; }
  .acts > :nth-child(4) { animation-delay: .18s; }
  .play { grid-row: span 3; position: relative; overflow: hidden; border-radius: 18px; padding: 20px 22px; cursor: pointer;
    display: flex; flex-direction: column; justify-content: flex-end; gap: 14px;
    background: radial-gradient(120% 120% at 0% 0%, rgba(200, 170, 110, .30), transparent 55%),
      radial-gradient(120% 120% at 100% 100%, rgba(10, 200, 185, .22), transparent 55%), rgba(9, 20, 40, .72);
    border: 1px solid rgba(200, 170, 110, .45); backdrop-filter: blur(16px);
    box-shadow: inset 0 1px 0 rgba(240, 230, 210, .12), 0 10px 30px rgba(0, 0, 0, .25);
    transition: transform .2s cubic-bezier(.3, 1.4, .5, 1), box-shadow .2s, border-color .2s; }
  .play:hover { transform: translateY(-3px); border-color: #c8aa6e;
    box-shadow: inset 0 1px 0 rgba(240, 230, 210, .16), 0 16px 40px rgba(200, 170, 110, .22); }
  .play:active { transform: scale(.98); }
  .play-orb { width: 58px; height: 58px; border-radius: 50%; display: grid; place-items: center;
    background: radial-gradient(circle at 35% 30%, #f0e6d2, #c8aa6e 45%, #785a28);
    box-shadow: 0 0 0 4px rgba(200, 170, 110, .18), 0 8px 22px rgba(200, 170, 110, .45); color: #1e2328;
    transition: transform .25s cubic-bezier(.3, 1.6, .5, 1); }
  .play-orb svg { width: 24px; height: 24px; stroke: #1e2328; fill: #1e2328; margin-left: 3px; }
  .play:hover .play-orb { transform: scale(1.08); }
  .play-t small { display: block; font-size: 11px; letter-spacing: 1.2px; text-transform: uppercase; color: #c8aa6e; }
  .play-t b { display: block; margin: 2px 0 3px; font-size: 22px; font-weight: 700; letter-spacing: .2px; color: #f0e6d2; }
  .play-t span { color: #a09b8c; font-size: 12px; }
  .play-shine { position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(115deg, transparent 35%, rgba(240, 230, 210, .14) 48%, transparent 60%);
    transform: translateX(-100%); }
  .play:hover .play-shine { transform: translateX(100%); transition: transform .9s ease; }
  /* League is already open: a live green state instead of the button */
  .play.live { cursor: default; border-color: rgba(74, 222, 128, .45);
    background: radial-gradient(120% 120% at 0% 0%, rgba(74, 222, 128, .2), transparent 55%),
      radial-gradient(120% 120% at 100% 100%, rgba(10, 200, 185, .2), transparent 55%), rgba(9, 20, 40, .72); }
  .play.live:hover { transform: none; box-shadow: inset 0 1px 0 rgba(240, 230, 210, .12); }
  .play.live .play-orb { background: radial-gradient(circle at 35% 30%, #bbf7d0, #22c55e 50%, #15803d);
    box-shadow: 0 0 0 4px rgba(74, 222, 128, .18); animation: live 2s ease-out infinite; }
  .play.live .play-orb svg { display: none; }
  .play.live .play-orb::after { content: ""; width: 14px; height: 14px; border-radius: 50%; background: #f0fdf4; }
  .play.live .play-t small { color: #4ade80; }
  @keyframes live { 0% { box-shadow: 0 0 0 0 rgba(74, 222, 128, .55); } 100% { box-shadow: 0 0 0 18px rgba(74, 222, 128, 0); } }

  .act { position: relative; overflow: hidden; display: flex; align-items: center; gap: 12px; padding: 0 14px;
    border-radius: 14px; cursor: pointer; background: rgba(30, 27, 42, .42); backdrop-filter: blur(16px) saturate(1.2);
    border: 1px solid rgba(255, 255, 255, .06); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05);
    transition: transform .18s cubic-bezier(.3, 1.4, .5, 1), border-color .18s, box-shadow .18s; }
  .act::before { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .7; transition: opacity .2s;
    background: radial-gradient(90% 140% at 100% 0%, rgba(var(--a), .16), transparent 60%); }
  .act:hover { transform: translateX(3px); border-color: rgba(var(--a), .5); box-shadow: 0 8px 26px rgba(var(--a), .16); }
  .act:hover::before { opacity: 1; }
  .act:active { transform: scale(.97); }
  .act.off { opacity: .45; pointer-events: none; }
  .orb { position: relative; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; flex: none;
    background: radial-gradient(circle at 35% 30%, rgba(var(--a), .45), rgba(var(--a), .12));
    box-shadow: 0 0 14px rgba(var(--a), .3), inset 0 0 0 1px rgba(var(--a), .4); color: rgb(var(--a)); }
  .orb svg { width: 17px; height: 17px; }
  .act:hover .orb { animation: wobble .4s ease; }
  @keyframes wobble { 40% { transform: rotate(-10deg) scale(1.1); } 80% { transform: rotate(4deg); } }
  .act .t { position: relative; flex: 1; min-width: 0; }
  .chev { position: relative; font-style: normal; font-size: 20px; color: rgba(var(--a), .7); transition: transform .2s; }
  .act:hover .chev { transform: translateX(4px); }
  .sw { position: relative; width: 36px; height: 20px; border-radius: 99px; background: rgba(255, 255, 255, .14); flex: none;
    transition: background .2s; }
  .sw::after { content: ""; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%;
    background: #d4d0dc; transition: left .3s cubic-bezier(.3, 1.6, .5, 1), background .2s; }
  .sw.on { background: rgb(var(--a)); box-shadow: 0 0 12px rgba(var(--a), .45); }
  .sw.on::after { left: 19px; background: #fff; }
  /* Close asks again: the card turns red for the second click */
  .act.armed { border-color: rgba(var(--a), .8); background: rgba(127, 29, 29, .45); }
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

  /* Version pill and its panel */
  .ver-pill { display: inline-flex; align-items: center; gap: 7px; cursor: pointer; font: inherit; font-size: 11px;
    color: var(--sub); transition: background .15s, color .15s, border-color .15s; }
  .ver-pill:hover, .ver-pill.open { color: var(--text); border-color: rgba(var(--tint), .45); background: rgba(48, 43, 64, .7); }
  .vdot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px rgba(74, 222, 128, .7); }
  .vdot.new { background: #facc15; animation: vpulse 1.6s ease-out infinite; }
  @keyframes vpulse { 0% { box-shadow: 0 0 0 0 rgba(250, 204, 21, .7); } 100% { box-shadow: 0 0 0 9px rgba(250, 204, 21, 0); } }
  .vpop { position: absolute; z-index: 30; top: 48px; left: 64px; width: 380px; padding: 16px 16px 14px; border-radius: 16px;
    background: rgba(26, 23, 37, .92); backdrop-filter: blur(22px) saturate(1.3); border: 1px solid rgba(255, 255, 255, .08);
    box-shadow: 0 24px 60px rgba(0, 0, 0, .55), inset 0 1px 0 rgba(255, 255, 255, .06);
    transform-origin: 30px -8px; animation: pop .22s cubic-bezier(.2, 1.2, .4, 1); }
  @keyframes pop { from { opacity: 0; transform: translateY(-6px) scale(.96); } }
  .vpop::before { content: ""; position: absolute; top: -6px; left: 28px; width: 12px; height: 12px; transform: rotate(45deg);
    background: rgba(26, 23, 37, .92); border-left: 1px solid rgba(255, 255, 255, .08); border-top: 1px solid rgba(255, 255, 255, .08); }
  .vpop-head b { display: block; font-size: 14px; }
  .vpop-head span { color: var(--sub); font-size: 11.5px; }
  .vpop-k { display: block; margin: 12px 0 4px; font-size: 10.5px; letter-spacing: 1px; text-transform: uppercase; color: var(--faint); }
  .vpop ul { margin: 0; padding-left: 16px; color: var(--sub); font-size: 11.5px; max-height: 150px; overflow-y: auto; }
  .vpop li { margin-bottom: 3px; }
  .vpop-foot { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
  .vpop-foot .auto { margin-left: 0; }
  .vbtn { margin-left: auto; display: inline-flex; align-items: center; gap: 6px; }
  .vbtn svg { width: 15px; height: 15px; }
  .main { position: relative; }
  .round { margin-left: auto; width: 52px; height: 52px; border-radius: 50%; border: 0; display: grid; place-items: center; flex: none;
    background: var(--accent); color: #15111f; cursor: pointer; box-shadow: 0 6px 18px rgba(167, 139, 250, .35); transition: transform .15s; }
  .round:hover { transform: scale(1.08); }
  .round:disabled { opacity: .4; cursor: default; transform: none; }

  .auto { margin-left: auto; display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 12px;
    background: #1d1a29; color: var(--sub); font-size: 12px; font-weight: 600; cursor: pointer; }
  .auto:hover { background: #2a2540; color: var(--text); }
  .switch { position: relative; width: 34px; height: 18px; border-radius: 9px; background: #3c3850; transition: background .15s; }
  .switch::after { content: ""; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%;
    background: #a3a0ad; transition: left .15s, background .15s; }
  .switch.on { background: var(--accent); }
  .switch.on::after { left: 18px; background: #fff; }
  .ver .round { margin-left: 0; }
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
  .maps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
  .mapc { position: relative; background: var(--card); border-radius: 14px; padding: 7px 7px 11px; cursor: pointer;
    border: 2px solid transparent; transition: transform .15s, border-color .15s; }
  .mapc:hover { transform: translateY(-3px) scale(1.02); }
  .mapc.on { border-color: #2dd4bf; box-shadow: 0 8px 22px rgba(45, 212, 191, .18); }
  .mapc .shot { background: linear-gradient(135deg, #12313a, #1c2b1f 60%, #2b2414); display: grid; place-items: center; color: #5eead4; }
  .mapc .shot svg { width: 34px; height: 34px; opacity: .7; }
  .mapc .shot.img svg { display: none; }
  .mapc b { display: block; margin: 8px 3px 0; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mapc span { display: block; margin: 2px 3px 0; color: var(--sub); font-size: 11px; min-height: 14px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mapc .tag { position: absolute; top: 13px; left: 13px; padding: 2px 8px; border-radius: 99px; font-size: 10.5px; font-weight: 700;
    background: #2dd4bf; color: #04201d; }
  .mapc .del { position: absolute; top: 12px; right: 12px; width: 24px; height: 24px; border-radius: 8px; display: grid; place-items: center;
    background: rgba(16, 14, 23, .75); color: var(--sub); opacity: 0; transition: opacity .15s; }
  .mapc:hover .del { opacity: 1; }
  .mapc .del:hover { color: #f87171; }
  .mapc .del svg { width: 13px; height: 13px; }
  .mapc .get { margin: 8px 3px 0; width: calc(100% - 6px); padding: 7px; }
  .fontc .shot { background: linear-gradient(135deg, #10213f, #1b1a3a 60%, #24183a); color: #bfdbfe; font-size: 30px; font-weight: 700;
    letter-spacing: .5px; }
  .fontc.on { border-color: #60a5fa; box-shadow: 0 8px 22px rgba(96, 165, 250, .18); }
  .fontc .tag { background: #60a5fa; color: #06142e; }
  .fontc .tag.lust { left: auto; right: 13px; background: rgba(16, 14, 23, .75); color: #bfdbfe; }
  .fontc:hover .tag.lust { opacity: 0; }
  .drop { margin-top: 12px; border: 1.5px dashed #3a3550; border-radius: 14px; padding: 16px; display: flex; align-items: center; gap: 14px;
    color: var(--sub); font-size: 12px; transition: border-color .15s, background .15s; }
  #font-drop.over { border-color: #60a5fa; background: rgba(96, 165, 250, .07); }
  #font-drop svg { color: #93c5fd; }
  .drop.over { border-color: #2dd4bf; background: rgba(45, 212, 191, .07); color: var(--text); }
  .drop svg { width: 22px; height: 22px; color: #5eead4; flex: none; }
  .drop .btn { margin-left: auto; }
  .empty { color: var(--faint); font-size: 12px; padding: 6px 2px; }
  .walls { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
  .wallc { position: relative; border-radius: 16px; overflow: hidden; cursor: pointer; aspect-ratio: 16 / 9; background: #0d1238;
    border: 2px solid rgba(255, 255, 255, .06); transition: transform .15s, border-color .15s, box-shadow .15s; }
  .wallc:hover { transform: translateY(-3px); border-color: rgba(244, 114, 182, .5); }
  .wallc.on { border-color: #f472b6; box-shadow: 0 10px 28px rgba(244, 114, 182, .3); }
  .wallc img, .wallc video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .wallc .cap { position: absolute; left: 0; right: 0; bottom: 0; padding: 26px 12px 10px; font-size: 12px; font-weight: 600;
    background: linear-gradient(transparent, rgba(5, 7, 26, .85)); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .wallc .tag { position: absolute; top: 10px; left: 10px; padding: 2px 9px; border-radius: 99px; font-size: 10.5px; font-weight: 700;
    background: #f472b6; color: #2a0718; }
  .wallc .kind { position: absolute; top: 10px; right: 10px; padding: 2px 8px; border-radius: 99px; font-size: 10px; font-weight: 700;
    background: rgba(5, 7, 26, .7); color: #fbcfe8; }
  .wallc .del { position: absolute; bottom: 9px; right: 9px; width: 26px; height: 26px; border-radius: 8px; display: grid; place-items: center;
    background: rgba(5, 7, 26, .75); color: var(--sub); opacity: 0; transition: opacity .15s; }
  .wallc:hover .del { opacity: 1; }
  .wallc .del:hover { color: #f87171; }
  .wallc .del svg { width: 13px; height: 13px; }
  .wallc.league { display: grid; place-items: center; background: radial-gradient(circle at 30% 20%, rgba(200, 170, 110, .35), transparent 60%), linear-gradient(135deg, #1b1a0e, #0d1238); }
  .wallc.league svg { width: 64px; height: 64px; }
  #wall-drop.over { border-color: #f472b6; background: rgba(244, 114, 182, .07); }
  #wall-drop svg { color: #f9a8d4; }
  .ht-vid { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity .6s; }
  #tile-wall.vid .ht-vid { opacity: 1; }
  #tile-wall .ht-bg { opacity: 1; animation: none; inset: 0; background: radial-gradient(320px 200px at 85% 25%, rgba(244, 114, 182, .35), transparent 70%), linear-gradient(135deg, #2a1030, #0f1440); }
  #tile-wall .ht-bg.on { background-size: cover; background-position: center; }
  #tile-wall .ht-mark { opacity: .5; }
  /* Custom skins: one row per file, the champion it plays on and its switch */
  .sk-head { display: flex; align-items: center; gap: 10px; margin: 4px 2px 10px; }
  .sk-head .section { margin: 0; }
  .sk-head input { margin-left: auto; width: 190px; background: #1d1a29; border: 1px solid var(--line); border-radius: 99px;
    color: var(--text); font: inherit; font-size: 12px; padding: 7px 14px; outline: none; }
  .sk-head input:focus { border-color: #f472b6; }
  .sk-off { display: none; margin-bottom: 10px; padding: 10px 14px; border-radius: 12px; font-size: 12px;
    background: rgba(245, 177, 76, .1); color: var(--amber); border: 1px solid rgba(245, 177, 76, .25); }
  .sk-off.show { display: block; }
  .skins { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .skr { position: relative; display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 16px;
    background: var(--card); border: 1.5px solid transparent; transition: border-color .15s, transform .15s; }
  .skr:hover { transform: translateY(-2px); }
  .skr.on { border-color: #f472b6; box-shadow: 0 8px 22px rgba(244, 114, 182, .14); }
  .skr .ic { width: 46px; height: 46px; border-radius: 50%; flex: none; background: #2c2840 center / cover;
    display: grid; place-items: center; color: #f472b6; box-shadow: inset 0 0 0 2px rgba(255, 255, 255, .06); }
  .skr.on .ic { box-shadow: 0 0 0 2px #f472b6; }
  .skr .ic.img svg { display: none; }
  .skr .tx { min-width: 0; flex: 1; }
  .skr b { display: block; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .skr span { display: block; color: var(--sub); font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .skr span.bad { color: #f87171; }
  .skr select { display: block; margin-top: 5px; max-width: 100%; background: #2c2840; color: var(--text); border: 1px solid var(--line);
    border-radius: 8px; font: inherit; font-size: 11.5px; padding: 3px 6px; outline: none; cursor: pointer; }
  .skr select.need { border-color: #f472b6; }
  .skr .tick { flex: none; width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; cursor: pointer;
    border: 2px solid rgba(255, 255, 255, .25); color: transparent; transition: background .15s, border-color .15s, box-shadow .15s; }
  .skr .tick svg { width: 16px; height: 16px; stroke-width: 3; }
  .skr .tick:hover { border-color: #f472b6; }
  .skr .tick.on { background: #ec4899; border-color: #ec4899; color: #fff; box-shadow: 0 0 14px rgba(236, 72, 153, .5); }
  .skr .tick.lock { opacity: .35; cursor: default; }
  .sk-hint { color: var(--sub); font-size: 12px; margin: -6px 0 12px; }
  .skr .del { position: absolute; top: -6px; right: -6px; width: 22px; height: 22px; border-radius: 8px; display: grid; place-items: center;
    background: #2c2840; color: var(--sub); opacity: 0; transition: opacity .15s; cursor: pointer; }
  .skr:hover .del { opacity: 1; }
  .skr .del:hover { color: #f87171; }
  .skr .del svg { width: 12px; height: 12px; }
  .skr .st { display: flex; width: fit-content; align-items: center; gap: 6px; margin-top: 4px; font-size: 10.5px; font-weight: 700;
    padding: 2px 8px; border-radius: 99px; }
  .skr .st.ok { background: rgba(74, 222, 128, .12); color: var(--green); }
  .skr .st.untested, .skr .st.old { background: rgba(245, 177, 76, .12); color: var(--amber); }
  .skr .st.crashed { background: rgba(248, 113, 113, .14); color: #f87171; }
  .skr .st a { color: inherit; text-decoration: underline; cursor: pointer; font-weight: 600; }
  .skr.crashed { border-color: rgba(248, 113, 113, .35); }
  /* Profile background: the splash on the profile now, a champion strip and that champion's skins */
  .pf-hero { position: relative; height: 172px; border-radius: 18px; overflow: hidden; background: #1d1a29 center 20% / cover;
    display: flex; align-items: flex-end; padding: 18px 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, .35); }
  .pf-hero::before { content: ""; position: absolute; inset: 0;
    background: linear-gradient(90deg, rgba(14, 12, 22, .92) 0%, rgba(14, 12, 22, .55) 45%, rgba(14, 12, 22, 0) 80%),
      linear-gradient(0deg, rgba(14, 12, 22, .7), transparent 60%); }
  .pf-hero > * { position: relative; }
  .pf-hero small { display: block; color: #fdba74; font-size: 10.5px; font-weight: 700; letter-spacing: .8px; text-transform: uppercase; }
  .pf-hero h2 { margin: 3px 0 8px; font-size: 22px; font-weight: 700; text-shadow: 0 2px 12px rgba(0, 0, 0, .6); }
  .pf-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 600;
    background: rgba(255, 255, 255, .1); color: var(--sub); backdrop-filter: blur(6px); }
  .pf-chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--faint); }
  .pf-chip.on { color: #bbf7d0; } .pf-chip.on::before { background: var(--green); box-shadow: 0 0 8px var(--green); }
  .pf-chip.wait { color: #fde68a; } .pf-chip.wait::before { background: var(--amber); }
  .pf-head { display: flex; align-items: center; gap: 10px; margin: 16px 2px 10px; }
  .pf-head .section { margin: 0; }
  .pf-head input { margin-left: auto; width: 190px; background: #1d1a29; border: 1px solid var(--line); border-radius: 99px;
    color: var(--text); font: inherit; font-size: 12px; padding: 7px 14px; outline: none; }
  .pf-head input:focus { border-color: #fb923c; }
  .champs { display: grid; grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: 8px 6px; max-height: 172px; overflow-y: auto;
    padding: 4px 2px; }
  .chp { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; min-width: 0; }
  .chp i { width: 46px; height: 46px; border-radius: 50%; background: #2c2840 center / cover; box-shadow: inset 0 0 0 2px rgba(255, 255, 255, .06);
    transition: transform .15s, box-shadow .15s; }
  .chp:hover i { transform: scale(1.1); }
  .chp span { font-size: 10.5px; color: var(--sub); max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chp.sel i { box-shadow: 0 0 0 2px #fb923c, 0 4px 14px rgba(251, 146, 60, .4); }
  .chp.sel span { color: #fed7aa; font-weight: 600; }
  .pskins { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  .psk { position: relative; border-radius: 14px; overflow: hidden; cursor: pointer; background: var(--card);
    border: 1.5px solid transparent; transition: transform .15s, border-color .15s; }
  .psk:hover { transform: translateY(-3px); }
  .psk .art { aspect-ratio: 16 / 9; background: linear-gradient(135deg, #2a1f3d, #3a2418) center 20% / cover; }
  .psk b { display: block; padding: 7px 10px 9px; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .psk.on { border-color: #fb923c; box-shadow: 0 8px 22px rgba(251, 146, 60, .2); }
  .psk .tag { position: absolute; top: 8px; left: 8px; padding: 2px 8px; border-radius: 99px; font-size: 10.5px; font-weight: 700;
    background: #fb923c; color: #2a1004; display: none; }
  .psk.on .tag { display: block; }
  .psk .use { position: absolute; inset: 0 0 auto 0; aspect-ratio: 16 / 9; display: grid; place-items: center; opacity: 0;
    background: rgba(14, 12, 22, .45); transition: opacity .15s; font-weight: 700; font-size: 12px; }
  .psk:hover .use { opacity: 1; }
  .psk.on .use { display: none; }
  /* Profile icon: the chosen icon large, then every icon in a searchable grid */
  .ic-hero { position: relative; display: flex; align-items: center; gap: 18px; padding: 18px 20px; border-radius: 18px; overflow: hidden;
    background: #1c1a14; box-shadow: 0 10px 30px rgba(0, 0, 0, .35); }
  .ic-hero::before { content: ""; position: absolute; inset: -40px; background: var(--ic-art, none) center / cover; filter: blur(28px) saturate(1.3);
    opacity: .45; }
  .ic-hero::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(10, 16, 24, .85), rgba(10, 16, 24, .35)); }
  .ic-hero > * { position: relative; z-index: 1; }
  .ic-big { width: 92px; height: 92px; flex: none; border-radius: 50%; background: #2a2618 center / cover;
    box-shadow: 0 0 0 3px #facc15, 0 8px 24px rgba(250, 204, 21, .35); display: grid; place-items: center; color: var(--faint); }
  .ic-big svg { width: 38px; height: 38px; }
  .ic-hero small { display: block; color: #fde047; font-size: 10.5px; font-weight: 700; letter-spacing: .8px; text-transform: uppercase; }
  .ic-hero h2 { margin: 3px 0 8px; font-size: 21px; font-weight: 700; }
  .ic-acts { margin-left: auto; display: flex; flex-direction: column; gap: 8px; align-items: stretch; }
  .ic-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 600;
    background: rgba(255, 255, 255, .1); color: var(--sub); }
  .ic-chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--faint); }
  .ic-chip.on { color: #fef08a; } .ic-chip.on::before { background: #facc15; box-shadow: 0 0 8px #facc15; }
  .ic-head { display: flex; align-items: center; gap: 10px; margin: 16px 2px 10px; }
  .ic-head .section { margin: 0; }
  .ic-head input { margin-left: auto; width: 210px; background: #1d1a29; border: 1px solid var(--line); border-radius: 99px;
    color: var(--text); font: inherit; font-size: 12px; padding: 7px 14px; outline: none; }
  .ic-head input:focus { border-color: #facc15; }
  .icons { display: grid; grid-template-columns: repeat(auto-fill, minmax(64px, 1fr)); gap: 10px; }
  .picon { position: relative; aspect-ratio: 1; border-radius: 14px; cursor: pointer; background: #2a2618 center / cover;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .06); transition: transform .15s, box-shadow .15s; }
  .picon:hover { transform: translateY(-3px) scale(1.04); box-shadow: 0 6px 16px rgba(0, 0, 0, .4); }
  .picon.on { box-shadow: 0 0 0 2.5px #facc15, 0 6px 18px rgba(250, 204, 21, .4); }
  .picon.on::after { content: ""; position: absolute; right: -4px; top: -4px; width: 16px; height: 16px; border-radius: 50%;
    background: #facc15 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23271d02' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 6 9 17l-5-5'/%3E%3C/svg%3E") center / 10px no-repeat; }
  .ic-more { display: block; margin: 14px auto 0; }
  #skin-drop.over { border-color: #f472b6; background: rgba(244, 114, 182, .07); }
  #skin-drop svg { color: #f472b6; }

  #toast { position: fixed; left: 50%; bottom: 22px; transform: translate(-50%, 20px); opacity: 0; transition: .25s;
    background: #2a2540; border: 1px solid #4b3f73; color: var(--text); padding: 10px 18px; border-radius: 99px; max-width: 80%; pointer-events: none; }
  #toast.show { opacity: 1; transform: translate(-50%, 0); }
  #lost { position: fixed; inset: 0; display: none; place-items: center; background: rgba(16, 14, 23, .9); color: var(--sub); }
  /* Settings: big toggle tiles, gold when on */
  .sg-head { display: flex; align-items: center; margin: 4px 0 14px; }
  .sg-tabs { display: flex; gap: 4px; padding: 4px; border-radius: 99px; background: rgba(14, 15, 22, .6);
    border: 1px solid rgba(255, 255, 255, .06); }
  .sg-tabs button { border: 0; background: none; color: var(--sub); font: 600 12.5px inherit; padding: 6px 16px; border-radius: 99px;
    cursor: pointer; transition: background .2s, color .2s; }
  .sg-tabs button:hover { color: var(--text); }
  .sg-tabs button.on { background: rgba(200, 170, 110, .18); color: #f0e6d2; box-shadow: inset 0 0 0 1px rgba(200, 170, 110, .35); }
  .sg-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
  .sg { position: relative; display: flex; align-items: center; gap: 12px; min-height: 62px; padding: 10px 14px; border-radius: 16px;
    cursor: pointer; background: rgba(14, 15, 22, .6); border: 1px solid rgba(255, 255, 255, .06);
    transition: background .25s, border-color .25s, transform .15s cubic-bezier(.3, 1.4, .5, 1), box-shadow .25s;
    animation: rise .4s cubic-bezier(.2, .8, .2, 1) both; }
  .sg:hover { transform: translateY(-2px); border-color: rgba(200, 170, 110, .35); }
  .sg:active { transform: scale(.97); }
  .sg.wide { grid-column: 1 / -1; }
  .sg .si { width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; flex: none;
    background: rgba(255, 255, 255, .07); color: var(--sub); transition: background .25s, color .25s; }
  .sg .si svg { width: 17px; height: 17px; }
  .sg b { display: block; font-size: 13px; font-weight: 600; transition: color .25s; }
  .sg span { color: var(--faint); font-size: 11.5px; transition: color .25s; }
  .sg.on { background: linear-gradient(135deg, #d9bd84, #c8aa6e 55%, #a8884e); border-color: rgba(240, 230, 210, .5);
    box-shadow: 0 8px 24px rgba(200, 170, 110, .25), inset 0 1px 0 rgba(255, 255, 255, .35); }
  .sg.on .si { background: rgba(30, 35, 40, .22); color: #1e2328; }
  .sg.on b { color: #1e2328; } .sg.on span { color: rgba(30, 35, 40, .7); }
  .sg .opt { margin-left: auto; display: flex; gap: 4px; padding: 3px; border-radius: 99px; background: rgba(0, 0, 0, .25); }
  .sg .opt i { font-style: normal; font-size: 11.5px; font-weight: 600; padding: 4px 10px; border-radius: 99px; color: var(--sub); }
  .sg .opt i.on { background: #c8aa6e; color: #1e2328; }
  .sg-grid .sg:nth-child(2) { animation-delay: .03s; } .sg-grid .sg:nth-child(3) { animation-delay: .06s; }
  .sg-grid .sg:nth-child(4) { animation-delay: .09s; } .sg-grid .sg:nth-child(5) { animation-delay: .12s; }
  .sg-grid .sg:nth-child(6) { animation-delay: .15s; } .sg-grid .sg:nth-child(7) { animation-delay: .18s; }
  .sg-grid .sg:nth-child(n+8) { animation-delay: .21s; }
  .sg-foot { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
  .sg-mini { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 14px; cursor: pointer;
    background: rgba(14, 15, 22, .45); border: 1px dashed rgba(255, 255, 255, .1); color: var(--sub); transition: border-color .2s, color .2s; }
  .sg-mini:hover { border-color: rgba(200, 170, 110, .45); color: var(--text); }
  .sg-mini b { display: block; font-size: 12.5px; color: var(--text); } .sg-mini span { font-size: 11px; color: var(--faint); }

  /* Spotify: now playing */
  .np { position: relative; overflow: hidden; display: flex; align-items: center; gap: 16px; padding: 16px 18px;
    border-radius: 20px; background: rgba(14, 15, 22, .6); border: 1px solid rgba(255, 255, 255, .07); margin: 4px 0 6px; }
  .np-bg { position: absolute; inset: -30%; background-size: cover; background-position: center; filter: blur(40px) saturate(1.4);
    opacity: 0; transition: opacity .8s ease; }
  .np-bg.on { opacity: .45; }
  .np::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(10, 10, 16, .55), rgba(10, 10, 16, .75)); }
  .np > :not(.np-bg) { position: relative; z-index: 1; }
  .np-art { width: 88px; height: 88px; border-radius: 12px; flex: none; display: grid; place-items: center; color: #1db954;
    background: #121218 center/cover; box-shadow: 0 10px 28px rgba(0, 0, 0, .45); }
  .np-art svg { width: 34px; height: 34px; }
  .np-art.has svg { display: none; }
  .np-main { flex: 1; min-width: 0; }
  .np-k { display: flex; align-items: center; gap: 6px; font-size: 10.5px; letter-spacing: 1px; text-transform: uppercase; color: #1db954; }
  .np-main b { display: block; margin: 3px 0 1px; font-size: 16px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .np-main > span { display: block; color: var(--sub); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .np-time { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 11px; color: var(--faint); font-variant-numeric: tabular-nums; }
  .np-bar { flex: 1; height: 4px; border-radius: 99px; background: rgba(255, 255, 255, .14); overflow: hidden; }
  .np-bar i { display: block; height: 100%; width: 0; border-radius: inherit; background: #1db954; }
  .np-viz { display: flex; align-items: flex-end; gap: 3px; height: 44px; flex: none; }
  .np-viz i { width: 4px; height: 3px; border-radius: 2px; background: linear-gradient(0deg, #1db954, #6ee7a0); opacity: .9; }
  .np-ctl { display: flex; align-items: center; gap: 6px; flex: none; }
  .np-b { width: 36px; height: 36px; border-radius: 50%; border: 0; display: grid; place-items: center; cursor: pointer;
    background: rgba(255, 255, 255, .08); color: var(--text); transition: background .15s, transform .15s; }
  .np-b:hover { background: rgba(255, 255, 255, .16); transform: scale(1.06); }
  .np-b:active { transform: scale(.94); }
  .np-b svg { width: 16px; height: 16px; }
  .np-play { width: 46px; height: 46px; background: #1db954; color: #0b1a10; }
  .np-play:hover { background: #22d063; }
  .np-play svg { width: 18px; height: 18px; fill: currentColor; }
  .np-b.muted { background: rgba(248, 113, 113, .22); color: #fca5a5; }
  .np.idle .np-ctl, .np.idle .np-viz, .np.idle .np-time { opacity: .35; pointer-events: none; }

  /* Cinematic backdrop (over the ambient styles above) */
  .ambient { background: #07080d; }
  .blob { display: none; }
  .amb-art { inset: 0 0 30% 0; filter: blur(4px) saturate(1.15) brightness(.6); transform: scale(1.03); }
  .amb-art.on { opacity: 1; }
  .ambient::after { background: linear-gradient(180deg, rgba(7, 8, 13, .1) 0%, rgba(7, 8, 13, .65) 45%, #07080d 70%); }
  .rail { background: transparent; backdrop-filter: none; border-right: 1px solid rgba(255, 255, 255, .05); }
  .card, .act { background: rgba(14, 15, 22, .6); }
  /* Settings: the plain hextech backdrop */
  .bd-hextech .amb-art { display: none; }
  .bd-hextech .ambient { background:
      radial-gradient(60% 50% at 0% 0%, rgba(200, 170, 110, .12), transparent 70%),
      radial-gradient(55% 60% at 100% 100%, rgba(10, 200, 185, .11), transparent 70%),
      linear-gradient(160deg, #0b1324 0%, #080d18 55%, #05070d 100%); }
  .bd-hextech .ambient::after { background:
      repeating-linear-gradient(60deg, rgba(200, 170, 110, .03) 0 1px, transparent 1px 26px),
      repeating-linear-gradient(-60deg, rgba(200, 170, 110, .03) 0 1px, transparent 1px 26px); }
  .bd-hextech .card, .bd-hextech .act { background: rgba(16, 24, 40, .6); }
  /* Settings: no animations */
  .calm *, .calm *::before, .calm *::after { animation: none !important; transition: none !important; }

  /* ==== Lust app: navy and violet, a home of nine tiles ==== */
  :root { --bg: #0a0d2c; --card: #161c4e; --card2: #1d245e; --line: #262e70; --text: #f4f5ff; --sub: #aab0dd;
    --faint: #6c72a6; --accent: #8f82ff; --accent2: #f472b6; --tint: 109, 93, 252; }
  html, body { font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; }
  .ambient { background:
      radial-gradient(900px 520px at 12% -12%, rgba(109, 93, 252, .30), transparent 60%),
      radial-gradient(760px 520px at 100% 112%, rgba(56, 189, 248, .14), transparent 60%),
      radial-gradient(620px 420px at 72% 8%, rgba(244, 114, 182, .10), transparent 60%), #070a24; }
  .ambient::after { background: radial-gradient(rgba(255, 255, 255, .045) 1px, transparent 1px) 0 0 / 26px 26px;
    -webkit-mask-image: linear-gradient(#000, transparent 70%); }
  .amb-art.on { opacity: .22; }
  body[data-page="home"] .amb-art { opacity: 0; }
  .card, .act { background: rgba(22, 28, 78, .55); }
  .seg { background: #0d1238; }
  .seg button.on { background: var(--accent); color: #0b0d2a; }
  .btn { background: #232b6b; }
  .btn.primary { background: linear-gradient(135deg, #6d5dfc, #a855f7); color: #fff; }
  .page::-webkit-scrollbar-thumb { background: #262e70; }

  /* Title bar: LUST on the home page, a back button and the page's name elsewhere */
  .top { height: 50px; padding: 0 0 0 22px; gap: 12px; position: relative; z-index: 4; flex: none; }
  .word { font-weight: 800; letter-spacing: .34em; font-size: 12px;
    background: linear-gradient(90deg, #a99dff, #f0abfc); -webkit-background-clip: text; color: transparent; }
  .back { width: 34px; height: 34px; margin-left: -8px; border-radius: 11px; display: grid; place-items: center; cursor: pointer;
    background: rgba(255, 255, 255, .06); border: 1px solid rgba(255, 255, 255, .1); color: var(--text);
    transition: background .15s, transform .15s; }
  .back:hover { background: rgba(109, 93, 252, .45); transform: translateX(-2px); }
  .back svg { width: 18px; height: 18px; }
  .top h1 { font-size: 18px; font-weight: 700; letter-spacing: -.01em; }
  .lg { display: inline-flex; align-items: center; gap: 8px; height: 30px; padding: 0 12px; border-radius: 99px;
    background: rgba(255, 255, 255, .05); border: 1px solid rgba(255, 255, 255, .08); color: var(--sub); font-size: 12px; font-weight: 600; }
  .lg .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--amber); box-shadow: 0 0 10px currentColor; }
  .wins { display: flex; align-self: stretch; }
  .win { width: 46px; height: 50px; border-radius: 0; }
  .win:hover { background: rgba(255, 255, 255, .08); }
  .win svg { width: 15px; height: 15px; }
  .page { padding: 4px 30px 26px; }
  /* Edges to resize the frameless window (off while it fills the screen) */
  .rz { position: fixed; z-index: 30; }
  .rz[data-edge="n"] { top: 0; left: 10px; right: 10px; height: 5px; cursor: ns-resize; }
  .rz[data-edge="s"] { bottom: 0; left: 10px; right: 10px; height: 6px; cursor: ns-resize; }
  .rz[data-edge="e"] { right: 0; top: 10px; bottom: 10px; width: 6px; cursor: ew-resize; }
  .rz[data-edge="w"] { left: 0; top: 10px; bottom: 10px; width: 6px; cursor: ew-resize; }
  .rz[data-edge="ne"] { top: 0; right: 0; width: 12px; height: 12px; cursor: nesw-resize; }
  .rz[data-edge="nw"] { top: 0; left: 0; width: 12px; height: 12px; cursor: nwse-resize; }
  .rz[data-edge="se"] { bottom: 0; right: 0; width: 14px; height: 14px; cursor: nwse-resize; }
  .rz[data-edge="sw"] { bottom: 0; left: 0; width: 14px; height: 14px; cursor: nesw-resize; }
  body.maxed .rz { display: none; }

  /* Home */
  #page-home.active { display: flex; flex-direction: column; }
  #page-home > * { flex: none; }
  .home-head { display: flex; align-items: flex-end; gap: 18px; margin: 4px 2px 16px; }
  .hm-text { min-width: 0; }
  .home-head small { color: var(--sub); font-size: 11.5px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
  .hm-name { margin: 4px 0 0; font-size: 30px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .hm-name b { background: linear-gradient(90deg, #a99dff, #f0abfc); -webkit-background-clip: text; color: transparent; }
  .hm-name i { font-style: normal; color: var(--faint); font-weight: 600; }
  .hm-sub { margin-top: 6px; color: var(--sub); font-size: 13px; min-height: 18px; }
  .hm-seg { margin: 0 0 4px 10px; flex: none; }
  .hm-seg button { padding: 6px 13px; font-size: 12.5px; }
  .hm-play { margin-left: auto; flex: none; display: flex; align-items: center; gap: 12px; height: 52px; padding: 0 22px 0 8px;
    border: 0; border-radius: 16px; cursor: pointer; color: #fff; font: inherit; font-weight: 700; font-size: 14.5px;
    background: linear-gradient(135deg, #6d5dfc, #a855f7); box-shadow: 0 14px 30px -12px rgba(109, 93, 252, .9);
    transition: transform .15s, filter .15s; }
  .hm-play:hover { transform: translateY(-2px); filter: brightness(1.1); }
  .hm-orb { width: 38px; height: 38px; border-radius: 12px; background: rgba(255, 255, 255, .18); display: grid; place-items: center; }
  .hm-orb svg { width: 16px; height: 16px; fill: #fff; stroke: #fff; margin-left: 2px; }
  .hm-play.live { cursor: default; background: rgba(52, 211, 153, .12); color: #6ee7b7; box-shadow: none;
    border: 1px solid rgba(52, 211, 153, .4); }
  .hm-play.live:hover { transform: none; filter: none; }
  .hm-play.live .hm-orb svg { display: none; }
  .hm-play.live .hm-orb::after { content: ""; width: 10px; height: 10px; border-radius: 50%; background: #34d399;
    box-shadow: 0 0 12px #34d399; animation: live 2s ease-out infinite; }
  #page-home > .bar { margin: -6px 2px 14px; background: rgba(255, 255, 255, .1); }
  #page-home > .bar > i { background: linear-gradient(90deg, #6d5dfc, #f472b6); }
  .alerts > .card { margin: 0 0 12px; }
  .alerts:empty { display: none; }
  .hgrid { flex: 1 1 auto !important; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: repeat(3, minmax(150px, 1fr)); gap: 18px; min-height: 500px; }
  .page.active > .hgrid { animation: none; }

  .ht { position: relative; border-radius: 22px; overflow: hidden; cursor: pointer; background: #0f1440;
    border: 1px solid rgba(255, 255, 255, .08); box-shadow: 0 20px 50px -30px rgba(0, 0, 0, .9);
    animation: htin .8s cubic-bezier(.2, .8, .2, 1) both; animation-delay: calc(var(--i) * 80ms + 60ms);
    transition: transform .25s cubic-bezier(.2, .8, .2, 1), box-shadow .25s; }
  @keyframes htin { from { opacity: 0; transform: translateY(26px) scale(.96); filter: blur(6px); } }
  .ht::after { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1px; pointer-events: none;
    background: linear-gradient(135deg, rgba(var(--c), .75), transparent 40%, transparent 70%, rgba(var(--c), .35));
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor;
    opacity: .5; transition: opacity .25s; }
  .ht:hover { transform: translateY(-4px); box-shadow: 0 30px 60px -24px rgba(var(--c), .7); }
  .ht:hover::after { opacity: 1; }
  .ht:active { transform: scale(.98); }
  .ht-bg { position: absolute; inset: -6%; background-size: cover; background-position: 60% 22%; opacity: 0;
    transition: opacity .8s ease; animation: htpan 20s ease-in-out infinite alternate; }
  .ht-bg.on { opacity: .85; }
  @keyframes htpan { from { transform: scale(1.02); } to { transform: scale(1.12) translate(-2%, -2%); } }
  .ht-ov { position: absolute; inset: 0;
    background: linear-gradient(105deg, rgba(9, 12, 40, .95) 0%, rgba(9, 12, 40, .72) 42%, rgba(9, 12, 40, .12) 100%),
      radial-gradient(420px 220px at 0% 100%, rgba(var(--c), .32), transparent 70%); }
  .ht-shine { position: absolute; top: 0; bottom: 0; width: 40%; left: -60%; pointer-events: none;
    background: linear-gradient(100deg, transparent, rgba(255, 255, 255, .08), transparent);
    animation: htshine 8s ease-in-out infinite; animation-delay: calc(var(--i) * 400ms + 1.4s); }
  @keyframes htshine { 0%, 72% { left: -60%; } 100% { left: 130%; } }
  .ht-in { position: relative; height: 100%; padding: 20px 22px; display: flex; flex-direction: column; }
  .ht-orb { width: 56px; height: 56px; border-radius: 17px; display: grid; place-items: center; flex: none; overflow: hidden;
    background: linear-gradient(145deg, rgba(var(--c), .28), rgba(var(--c), .08)); border: 1px solid rgba(var(--c), .45);
    box-shadow: 0 10px 30px -8px rgba(var(--c), .7), inset 0 1px 0 rgba(255, 255, 255, .18);
    animation: htfloat 5s ease-in-out infinite; animation-delay: calc(var(--i) * -600ms); }
  @keyframes htfloat { 50% { transform: translateY(-4px); } }
  .ht-orb svg { width: 30px; height: 30px; overflow: visible; stroke: var(--g); stroke-width: 2.1; fill: none; }
  .ht-orb svg .f { fill: var(--g); fill-opacity: .18; }
  .ht-orb svg .s { fill: var(--g); stroke: none; }
  .ht-orb svg.lol-mark { width: 34px; height: 34px; stroke: none; }
  .ht-orb svg.sp-logo { width: 34px; height: 34px; stroke: none; filter: drop-shadow(0 0 8px rgba(30, 215, 96, .5)); }
  .ht-orb svg.sp-logo path { stroke: #0b0b0b; }
  .ht-orb.art { padding: 0; }
  .ht-art { width: 100%; height: 100%; background: center / cover no-repeat; display: block; }
  .ht .spin { animation: htspin 14s linear infinite; transform-origin: 15px 15px; }
  @keyframes htspin { to { transform: rotate(360deg); } }
  .ht-ttl { margin-top: auto; font-size: 21px; font-weight: 800; letter-spacing: -.02em; }
  .ht-st { margin-top: 4px; color: var(--sub); font-size: 13px; min-height: 19px; padding-right: 50px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ht-st b { color: var(--text); font-weight: 700; }
  .ht-st b.ok { color: #34d399; } .ht-st b.warn { color: #fbbf24; }
  .ht-go { position: absolute; right: 18px; bottom: 18px; width: 38px; height: 38px; border-radius: 12px; display: grid;
    place-items: center; background: rgba(255, 255, 255, .07); border: 1px solid rgba(255, 255, 255, .1); color: var(--sub);
    transition: background .2s, color .2s, transform .2s; }
  .ht-go svg { width: 16px; height: 16px; }
  .ht:hover .ht-go { background: rgb(var(--c)); color: #fff; border-color: transparent; transform: translateX(2px); }
  .ht-glyph { position: absolute; right: 24px; top: 50%; transform: translateY(-62%); font-weight: 800; font-size: 86px;
    letter-spacing: -.04em; line-height: 1; pointer-events: none;
    background: linear-gradient(160deg, rgba(255, 255, 255, .22), rgba(255, 255, 255, .02)); -webkit-background-clip: text; color: transparent; }
  .ht-glyph.gold { background: linear-gradient(160deg, rgba(253, 230, 138, .6), rgba(245, 158, 11, .06)); -webkit-background-clip: text; }
  #tile-patch .ht-bg, #tile-fonts .ht-bg, #tile-auto .ht-bg, #tile-settings .ht-bg, #tile-spotify .ht-bg { opacity: 1; animation: none; inset: 0; }
  #tile-lol .ht-bg { opacity: 1; animation: none; inset: 0; background: radial-gradient(360px 240px at 82% 45%, color-mix(in srgb, var(--tc, #c8aa6e) 42%, transparent), transparent 70%), radial-gradient(260px 200px at 10% 110%, rgba(10, 200, 185, .18), transparent 70%), linear-gradient(135deg, #2a2210, #0f1440); }
  .ht-mark { position: absolute; right: 18px; top: 50%; pointer-events: none; animation: htfloat 6s ease-in-out infinite; }
  .ht-art { position: absolute; inset: 0; background-size: cover; background-position: right 22%; opacity: 0; transition: opacity .6s;
    -webkit-mask-image: linear-gradient(90deg, transparent 10%, #000 58%); mask-image: linear-gradient(90deg, transparent 10%, #000 58%); }
  .ht-art.on { opacity: .9; }
  #tile-lol:hover .ht-art { transform: scale(1.04); }
  .ht-art { transition: opacity .6s, transform .6s; }
  .ht-rank { position: absolute; top: 16px; right: 16px; display: flex; align-items: center; gap: 7px; padding: 5px 11px 5px 9px;
    border-radius: 99px; font-size: 11.5px; font-weight: 700; letter-spacing: .02em; color: #fff;
    background: rgba(8, 10, 30, .62); border: 1px solid color-mix(in srgb, var(--tc, #c8aa6e) 70%, transparent);
    box-shadow: 0 0 18px color-mix(in srgb, var(--tc, #c8aa6e) 35%, transparent); backdrop-filter: blur(6px); }
  .ht-rank::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--tc, #c8aa6e);
    box-shadow: 0 0 8px var(--tc, #c8aa6e); }
  .ht-rank[hidden] { display: none; }
  .ht-mark { width: 150px; height: 150px; margin-top: -88px; opacity: .32; }
  .ht-mark svg { width: 100%; height: 100%; }
  .ht-mark[hidden] { display: none; }
  @keyframes htfloat { 50% { transform: translateY(-6px); } }
  @media (prefers-reduced-motion: reduce) { .ht-mark { animation: none; } }
  #tile-spotify .ht-bg { background: radial-gradient(340px 220px at 88% 70%, rgba(30, 215, 96, .32), transparent 70%), linear-gradient(135deg, #0c2a1a, #0f1440); }
  .ht-sp-big { position: absolute; right: -34px; bottom: -48px; width: 200px; height: 200px; pointer-events: none;
    opacity: .9; filter: drop-shadow(0 10px 40px rgba(30, 215, 96, .35)); }
  .ht.playing .ht-sp-big { animation: sppulse 2.4s ease-in-out infinite; }
  .ht-cover { position: absolute; right: 34px; top: 50%; width: 112px; height: 112px; margin-top: -84px; border-radius: 14px;
    background: #0c2a1a center / cover; box-shadow: 0 18px 40px rgba(0, 0, 0, .55), 0 0 0 1px rgba(255, 255, 255, .08);
    transform: rotate(4deg); opacity: 0; transition: opacity .5s, transform .5s; pointer-events: none; }
  #tile-spotify.cover .ht-cover { opacity: 1; }
  #tile-spotify.cover:hover .ht-cover { transform: rotate(0deg) scale(1.04); }
  #tile-spotify.cover .ht-sp-big { opacity: 0; }
  #tile-spotify.cover .ht-bg { background-size: cover; background-position: center; filter: blur(28px) saturate(1.4) brightness(.55); inset: -40px; }
  #tile-spotify.cover .ht-eq { right: 172px; }
  /* The icon fills the tile: it is square, so the face (upper middle) stays in view */
  #tile-icon.pic .ht-bg { background-size: 72% auto; background-position: right 38%; background-repeat: no-repeat;
    -webkit-mask-image: linear-gradient(90deg, transparent 18%, #000 52%); mask-image: linear-gradient(90deg, transparent 18%, #000 52%); }
  #tile-icon.pic { background: linear-gradient(135deg, #0e2a44, #0f1440); }
  @keyframes sppulse { 50% { transform: scale(1.05); filter: drop-shadow(0 10px 50px rgba(30, 215, 96, .6)); } }
  @media (prefers-reduced-motion: reduce) { .ht-sp-big { animation: none; } }
  #tile-patch .ht-bg { background: radial-gradient(320px 200px at 85% 20%, rgba(245, 158, 11, .45), transparent 70%), linear-gradient(135deg, #3b2a0a, #0f1440); }
  #tile-fonts .ht-bg { background: radial-gradient(380px 220px at 90% 10%, rgba(251, 146, 60, .25), transparent 70%), linear-gradient(135deg, #2a1530, #0f1440); }
  #tile-settings .ht-bg { background: conic-gradient(from 200deg at 80% 30%, rgba(109, 93, 252, .45), rgba(56, 189, 248, .2), rgba(244, 114, 182, .3), rgba(109, 93, 252, .45)); filter: blur(30px); }
  #tile-maps .ht-bg.rift { background-size: 70%; background-position: 115% 30%; background-repeat: no-repeat; opacity: .55; }
  .ht-faces { position: absolute; right: 22px; top: 20px; display: flex; }
  #tile-patch .ht-glyph { transform: translateY(-38%); }
  .ht-faces i { width: 30px; height: 30px; border-radius: 50%; margin-left: -9px; background: #1d245e center / cover;
    border: 2px solid #0d1238; }
  .ht-eq { position: absolute; right: 26px; top: 26px; display: flex; gap: 3px; align-items: flex-end; height: 22px; }
  .ht-eq i { width: 4px; border-radius: 2px; background: #1ed760; animation: hteq 1s ease-in-out infinite; }
  .ht-eq i:nth-child(2) { animation-delay: -.3s; } .ht-eq i:nth-child(3) { animation-delay: -.6s; } .ht-eq i:nth-child(4) { animation-delay: -.15s; }
  @keyframes hteq { 0%, 100% { height: 5px; } 50% { height: 22px; } }
  /* Champ select tile: a small draft board with the ban and pick lists */
  #tile-auto .ht-bg { background:
      repeating-linear-gradient(115deg, rgba(255, 255, 255, .025) 0 1px, transparent 1px 14px),
      radial-gradient(300px 200px at 78% 30%, rgba(244, 63, 94, .28), transparent 70%),
      radial-gradient(240px 180px at 95% 100%, rgba(200, 170, 110, .16), transparent 70%),
      linear-gradient(135deg, #2b0f24, #0f1440); }
  .ht-draft { position: absolute; right: 20px; top: 20px; display: flex; flex-direction: column; gap: 9px; align-items: flex-end; }
  .dr-row { display: flex; align-items: center; gap: 8px; transition: opacity .3s, filter .3s; }
  .dr-row.off { opacity: .35; filter: grayscale(1); }
  .dr-row em { font-style: normal; font-size: 9.5px; font-weight: 800; letter-spacing: .16em; width: 30px; text-align: right; }
  .dr-row.ban em { color: #fb7185; } .dr-row.pick em { color: #e8c983; }
  .dr-row .dr-faces { display: flex; gap: 5px; }
  .dr-row i { position: relative; width: 32px; height: 32px; border-radius: 9px; background: #0d1238 center / 112% no-repeat;
    box-shadow: 0 4px 10px rgba(0, 0, 0, .45); }
  .dr-row.ban i { border: 1.5px solid rgba(244, 63, 94, .75); filter: saturate(.55) brightness(.8); }
  .dr-row.ban i::after { content: ""; position: absolute; inset: 0; border-radius: 8px;
    background: linear-gradient(135deg, transparent 46%, rgba(251, 113, 133, .95) 46% 54%, transparent 54%); }
  .dr-row.pick i { border: 1.5px solid rgba(200, 170, 110, .8); }
  .dr-row.pick i:first-child { width: 38px; height: 38px; border-color: #f0d38a; box-shadow: 0 0 16px rgba(240, 211, 138, .45), 0 4px 10px rgba(0, 0, 0, .45); }
  .dr-row i.empty { background: rgba(255, 255, 255, .04); border-style: dashed; filter: none; }
  .dr-row i.empty::after { display: none; }
  .dr-leds { display: flex; gap: 6px; margin-top: 2px; }
  .dr-leds span { display: inline-flex; align-items: center; gap: 6px; height: 22px; padding: 0 9px; border-radius: 99px; font-size: 10.5px;
    font-weight: 700; color: var(--faint); background: rgba(0, 0, 0, .32); border: 1px solid rgba(255, 255, 255, .08); }
  .dr-leds span::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, .25); }
  .dr-leds span.on { color: #fecdd3; border-color: rgba(244, 63, 94, .45); }
  .dr-leds span.on::before { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
  .ht:hover .dr-row.pick i:first-child { transform: translateY(-2px); }
  .dr-row i { transition: transform .2s; }

  /* Champ select page: Auto Accept, Ban, Pick, Lobby Reveal */
  .au-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .au { display: flex; align-items: center; gap: 14px; padding: 16px 18px; border-radius: 16px; cursor: pointer;
    background: rgba(22, 28, 78, .55); border: 1px solid rgba(255, 255, 255, .07); transition: border-color .2s, background .2s, transform .15s; }
  .au:hover { border-color: rgba(244, 63, 94, .45); transform: translateY(-2px); }
  .au:active { transform: scale(.98); }
  .au-i { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; flex: none;
    background: rgba(244, 63, 94, .1); border: 1px solid rgba(244, 63, 94, .3); color: #fb7185; }
  .au-i svg { width: 20px; height: 20px; }
  .au b { display: block; font-size: 15px; font-weight: 700; }
  .au span { color: var(--sub); font-size: 12px; }
  .au-ck { margin-left: auto; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; flex: none;
    border: 2px solid rgba(255, 255, 255, .18); color: transparent; transition: background .2s, border-color .2s; }
  .au-ck svg { width: 14px; height: 14px; stroke-width: 3; }
  .au.on { border-color: rgba(244, 63, 94, .5); background: linear-gradient(100deg, rgba(244, 63, 94, .14), rgba(22, 28, 78, .55) 60%); }
  .au.on .au-ck { background: #e11d48; border-color: #e11d48; color: #fff; box-shadow: 0 0 14px rgba(244, 63, 94, .55); }
  .au-team { margin-top: 14px; padding: 14px 16px; border-radius: 16px; background: rgba(22, 28, 78, .55); border: 1px solid rgba(255, 255, 255, .07); }
  .au-team-h { display: flex; align-items: center; } .au-team-h .section { margin: 0; } .au-team-h .btn { margin-left: auto; }
  .au-players { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px; margin-top: 10px; }
  .au-pl { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 12px; background: rgba(255, 255, 255, .04); cursor: pointer; }
  .au-pl:hover { background: rgba(255, 255, 255, .09); }
  .au-pl b { font-size: 13px; } .au-pl i { font-style: normal; color: var(--faint); font-size: 12px; }
  .au-pl small { margin-left: auto; color: var(--sub); font-size: 11px; text-transform: capitalize; }
  .au-lists { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 6px; }
  .au-list { position: relative; }
  .au-chips { display: flex; flex-wrap: wrap; gap: 8px; min-height: 42px; }
  .au-chip { display: inline-flex; align-items: center; gap: 8px; height: 38px; padding: 0 6px 0 4px; border-radius: 99px;
    background: rgba(22, 28, 78, .8); border: 1px solid rgba(255, 255, 255, .1); font-weight: 600; }
  .au-chip em { font-style: normal; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
    background: rgba(244, 63, 94, .2); color: #fda4af; font-size: 11px; font-weight: 800; }
  .au-chip img, .au-sug img { width: 30px; height: 30px; border-radius: 50%; }
  .au-chip button { border: 0; background: none; color: var(--faint); cursor: pointer; font-size: 16px; padding: 0 6px; }
  .au-chip button:hover { color: #fb7185; }
  .au-list input { margin-top: 10px; width: 100%; height: 38px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--line);
    background: #0d1238; color: var(--text); font: inherit; outline: none; }
  .au-list input:focus { border-color: var(--accent); }
  .au-sug { position: absolute; left: 0; right: 0; z-index: 6; margin-top: 6px; max-height: 260px; overflow-y: auto; border-radius: 12px;
    background: #121848; border: 1px solid var(--line); box-shadow: 0 20px 40px rgba(0, 0, 0, .5); }
  .au-sug:empty { display: none; }
  .au-sug div { display: flex; align-items: center; gap: 10px; padding: 7px 12px; cursor: pointer; }
  .au-sug div:hover { background: rgba(109, 93, 252, .25); }

  /* Patch notes page */
  .pn-hero { display: flex; align-items: center; gap: 22px; padding: 22px 24px; border-radius: 20px;
    background: radial-gradient(420px 220px at 90% 0%, rgba(245, 158, 11, .35), transparent 70%), linear-gradient(135deg, #2b210d, #141a4a);
    border: 1px solid rgba(253, 230, 138, .25); }
  .pn-ver { font-size: 56px; font-weight: 800; letter-spacing: -.04em; line-height: 1;
    background: linear-gradient(160deg, #fde68a, #f59e0b); -webkit-background-clip: text; color: transparent; }
  .pn-t { min-width: 0; }
  .pn-t small { color: #fde68a; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; font-size: 11px; }
  .pn-t h2 { margin: 4px 0; font-size: 19px; } .pn-t span { color: var(--sub); }
  .pn-hero .btn { margin-left: auto; flex: none; }
  .pn-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
  .pn { display: flex; gap: 12px; padding: 14px; border-radius: 16px; background: rgba(22, 28, 78, .55); border: 1px solid rgba(255, 255, 255, .06); }
  .pn i { width: 46px; height: 46px; border-radius: 50%; flex: none; background: #1d245e center / cover; box-shadow: 0 0 0 2px rgba(245, 158, 11, .45); }
  .pn b { display: block; font-size: 14px; } .pn span { color: var(--sub); font-size: 12px; line-height: 1.45; }

  .client-card { display: flex; align-items: center; gap: 14px; margin: 4px 0 16px;
    background: linear-gradient(100deg, rgba(109, 93, 252, .28), rgba(22, 28, 78, .55) 60%); }
  .client-card .btn { margin-left: auto; flex: none; }
  .client-card .t span { display: block; max-width: 620px; }
  .mods-seg { margin: 0 0 16px; width: max-content; background: rgba(13, 18, 56, .7); }
  .mods-seg button.on { background: linear-gradient(135deg, #6d5dfc, #38bdf8); color: #fff; }
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs><linearGradient id="lust-grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#c4b5fd"/><stop offset=".55" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/>
  </linearGradient><linearGradient id="hg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f9a8d4"/><stop offset="1" stop-color="#e879f9"/></linearGradient><linearGradient id="hg2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6ee7b7"/><stop offset="1" stop-color="#38bdf8"/></linearGradient><linearGradient id="hg3" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fef08a"/><stop offset="1" stop-color="#f59e0b"/></linearGradient><linearGradient id="hg4" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fde68a"/><stop offset="1" stop-color="#fb923c"/></linearGradient><linearGradient id="hg5" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7dd3fc"/><stop offset="1" stop-color="#818cf8"/></linearGradient><linearGradient id="hg6" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f5d0fe"/><stop offset="1" stop-color="#c084fc"/></linearGradient><linearGradient id="hg7" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#86efac"/><stop offset="1" stop-color="#1ed760"/></linearGradient><linearGradient id="hg8" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#c7d2fe"/><stop offset="1" stop-color="#6366f1"/></linearGradient><linearGradient id="hg9" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e0e7ff"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>
</svg>
<div class="ambient" aria-hidden="true"><div class="amb-art" id="amb-art"></div><i class="blob b1"></i><i class="blob b2"></i></div>
<div class="main">
  <header class="top pywebview-drag-region" id="top">
    <button class="back" id="back" title="Ana sayfa (Esc)" hidden>__back__</button>
    <span class="word pywebview-drag-region" id="word">LUST</span>
    <h1 id="title" hidden></h1>
    <button class="pill ver-pill" id="ver-pill" title="Sürüm ve yenilikler"><i class="vdot" id="vdot"></i>__VERSION__</button>
    <div class="grow pywebview-drag-region"></div>
    <span class="lg" id="lg"><i class="dot" id="dot"></i><span id="lg-t">League kapalı</span></span>
    <div class="wins">
      <div class="win" id="w-min" title="Küçült">__min__</div>
      <div class="win" id="w-max" title="Büyüt (çift tık)">__max__</div>
      <div class="win x" id="w-close" title="Kapat">__close__</div>
    </div>
  </header>
  <div class="vpop" id="vpop" hidden>
    <div class="vpop-head"><b>Lust __VERSION__</b><span id="v-sub"></span></div>
    <small class="vpop-k">Yenilikler</small>
    <ul id="news"></ul>
    <div class="vpop-foot">
      <div class="auto" data-act="auto_update" title="Yeni sürümler arka planda iner, League kapalıyken kurulur">
        <span>Otomatik güncelle</span><i class="switch" id="auto-upd"></i>
      </div>
      <button class="btn primary vbtn" id="v-btn"></button>
    </div>
  </div>

  <section class="page active" id="page-home">
    <div class="home-head">
      <div class="hm-text"><small id="hm-hi">Hoş geldin</small><h2 class="hm-name" id="hm-name">Lust başlıyor</h2>
        <div class="hm-sub" id="hm-sub"></div></div>
      <div class="seg status-seg hm-seg" id="hm-seg" title="LoL'de nasıl görüneceğin (Lust Offline)"><button data-status="online">Çevrimiçi</button><button data-status="offline">Çevrimdışı</button><button data-status="mobile">Mobil</button></div>
      <button class="hm-play" id="hm-league" data-act="league"><i class="hm-orb">__play__</i><span id="hm-league-t">League'i aç</span></button>
    </div>
    <div class="bar busy" id="h-bar"><i></i></div>
    <div class="alerts">
    <div class="card rose" id="rose" hidden>
      <div class="ico">__close__</div>
      <div class="t"><b>Rose da kurulu</b><span>İkisi aynı anda çalışınca LoL'de Rose'un gül simgesi çıkar ve çakışırlar. Lust, Rose'un yaptığı her şeyi zaten yapıyor.</span></div>
      <button class="btn danger" style="margin-left:auto" data-act="rose_uninstall">Rose'u kaldır</button>
      <button class="dismiss" data-dismiss="rose" title="Kapat">__close__</button>
    </div>
    <div class="card rose" id="ltk" hidden>
      <div class="ico">__close__</div>
      <div class="t"><b id="ltk-t"></b><span id="ltk-b"></span></div>
      <button class="btn primary" style="margin-left:auto" id="ltk-btn" data-act="patcher_download">İndirme sayfasını aç</button>
      <button class="dismiss" data-dismiss="ltk" title="Kapat">__close__</button>
    </div>
    <div class="card prompt" id="prompt" hidden>
      <div class="t"><b id="q-title"></b><span id="q-body"></span></div>
      <button class="btn primary" style="margin-left:auto" data-act="prompt" data-body='{"accept":true}'>Kur</button>
      <button class="btn" data-act="prompt" data-body='{"accept":false}'>Şimdi değil</button>
    </div>
    </div>
    <div class="hgrid" id="hgrid">
    <div class="ht" data-go="lol" id="tile-lol" style="--i:0;--c:200, 170, 110;--g:url(#hg3)">
      <div class="ht-bg" id="t-lol-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i><i class="ht-art" id="t-lol-art"></i><div class="ht-mark" id="t-lol-mark">__lolbig__</div><span class="ht-rank" id="t-lol-rank" hidden></span>
      <div class="ht-in"><div class="ht-orb art">__lol__</div>
        <b class="ht-ttl">Profil</b><span class="ht-st" id="t-lol"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="skins" id="tile-maps" style="--i:1;--c:52, 211, 153;--g:url(#hg2)">
      <div class="ht-bg" id="t-maps-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><path class="f" d="M4 8l7-3 8 3 7-3v17l-7 3-8-3-7 3z"/><path d="M11 5v17M19 8v17"/><circle class="s" cx="15" cy="13" r="2.4"/></svg></div>
        <b class="ht-ttl">Skinler ve Haritalar</b><span class="ht-st" id="t-maps"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="wallpaper" id="tile-wall" style="--i:2;--c:244, 114, 182;--g:url(#hg6)">
      <div class="ht-bg" id="t-wall-bg"></div><video class="ht-vid" id="t-wall-vid" muted loop playsinline preload="metadata"></video><div class="ht-ov"></div><i class="ht-shine"></i>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><rect class="f" x="3" y="6" width="24" height="17" rx="3"/><path d="m3.5 20 6.5-6.5 4.5 4.5 4-4 7.5 7.5"/><circle class="s" cx="20" cy="11.5" r="2"/><path d="M10 26h10"/></svg></div>
        <b class="ht-ttl">Duvar kağıdı</b><span class="ht-st" id="t-wall"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="fonts" id="tile-fonts" style="--i:3;--c:251, 146, 60;--g:url(#hg4)">
      <div class="ht-bg" id="t-fonts-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i><div class="ht-glyph">Aa 가</div>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><path d="M4 24 11 6l7 18M6.8 17h8.4"/><circle cx="21.5" cy="18.5" r="3.5"/><path d="M25 14v10"/></svg></div>
        <b class="ht-ttl">Fontlar</b><span class="ht-st" id="t-fonts"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="icon" id="tile-icon" style="--i:4;--c:56, 189, 248;--g:url(#hg5)">
      <div class="ht-bg" id="t-icon-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><circle class="f" cx="15" cy="15" r="11"/><circle cx="15" cy="12.5" r="4"/><path d="M8 23.2a8 8 0 0 1 14 0"/></svg></div>
        <b class="ht-ttl">Profil simgesi</b><span class="ht-st" id="t-icon"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="profile" id="tile-profile" style="--i:5;--c:232, 121, 249;--g:url(#hg6)">
      <div class="ht-bg" id="t-profile-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><rect class="f" x="4" y="6" width="22" height="18" rx="3"/><circle class="s" cx="11" cy="12" r="2.2"/><path d="m4.5 21 6-6 4 4 4-5 7 7"/></svg></div>
        <b class="ht-ttl">Profil arka planı</b><span class="ht-st" id="t-profile"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="spotify" id="tile-spotify" style="--i:6;--c:30, 215, 96;--g:url(#hg7)">
      <div class="ht-bg" id="t-spotify-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i><i class="ht-cover" id="t-sp-cover"></i><svg class="ht-sp-big" viewBox="0 0 24 24"><defs><linearGradient id="spg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4ef08a"/><stop offset="1" stop-color="#0f8a3c"/></linearGradient></defs><circle cx="12" cy="12" r="11" fill="url(#spg)" stroke="none" opacity=".5"/><path d="M6.3 9.2c3.8-1.2 8.3-.9 11.6 1.1M6.9 12.5c3.1-.9 6.8-.6 9.5 1M7.5 15.6c2.5-.6 5.1-.4 7.2.8" stroke="#08130d" stroke-opacity=".75" stroke-width="1.9" stroke-linecap="round" fill="none"/></svg><span class="ht-eq" id="t-eq" hidden><i></i><i></i><i></i><i></i></span>
      <div class="ht-in"><div class="ht-orb art"><svg class="sp-logo" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#1ed760" stroke="none"/><path d="M6.3 9.2c3.8-1.2 8.3-.9 11.6 1.1M6.9 12.5c3.1-.9 6.8-.6 9.5 1M7.5 15.6c2.5-.6 5.1-.4 7.2.8" stroke="#0b0b0b" stroke-width="1.9" fill="none"/></svg></div>
        <b class="ht-ttl">Spotify</b><span class="ht-st" id="t-spotify"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="auto" id="tile-auto" style="--i:7;--c:244, 63, 94;--g:url(#hg1)">
      <div class="ht-bg" id="t-auto-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i><div class="ht-draft" id="t-auto-draft"></div>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><path class="f" d="M5 22 3 9l6.5 5L15 5l5.5 9L27 9l-2 13z"/><path d="M6 26h18"/></svg></div>
        <b class="ht-ttl">Champ select</b><span class="ht-st" id="t-auto"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    <div class="ht" data-go="settings" id="tile-settings" style="--i:8;--c:167, 139, 250;--g:url(#hg9)">
      <div class="ht-bg" id="t-settings-bg"></div><div class="ht-ov"></div><i class="ht-shine"></i>
      <div class="ht-in"><div class="ht-orb"><svg viewBox="0 0 30 30"><g class="spin"><circle class="f" cx="15" cy="15" r="8"/><circle cx="15" cy="15" r="3.6"/><path d="M15 3.5v3M15 23.5v3M3.5 15h3M23.5 15h3M6.9 6.9 9 9M21 21l2.1 2.1M6.9 23.1 9 21M21 9l2.1-2.1"/></g></svg></div>
        <b class="ht-ttl">Ayarlar</b><span class="ht-st" id="t-settings"></span></div>
      <div class="ht-go">__arrow__</div>
    </div>
    </div>
  </section>

  <section class="page" id="page-lol">
    <div class="hero" id="hero">
      <div class="hero-art" id="h-art"></div>
      <div class="hero-body">
        <small id="h-small">Hoş geldin</small>
        <h2 id="h-title">Lust başlıyor</h2>
        <div class="hero-chips" id="h-chips"></div>
        <div class="hero-cut" id="h-cut" hidden></div>
        <p id="h-sub"></p>
      </div>
      <div class="hero-last" id="h-last" hidden>
        <small>Son maç</small>
        <b id="hl-champ"></b>
        <span class="hl-result" id="hl-result"></span>
        <span id="hl-meta"></span>
      </div>
    </div>
    <div class="card appear" style="margin-top:12px">
      <div class="ico">__user__</div>
      <div class="t"><b>Görün</b><span id="ap-sub"></span></div>
      <div class="seg status-seg" id="seg">
        <button data-status="online">Çevrimiçi</button><button data-status="offline">Çevrimdışı</button><button data-status="mobile">Mobil</button>
      </div>
    </div>
    <div class="section">Hızlı işlemler</div>
    <div class="acts">
      <div class="play" id="a-league" data-act="league">
        <div class="play-orb">__play__</div>
        <div class="play-t"><small id="a-league-k">Hazır</small><b id="a-league-t">League'i aç</b><span id="a-league-s">Lust Offline üzerinden, skinler hazır</span></div>
        <i class="play-shine"></i>
      </div>
      <div class="act" data-act="autostart" style="--a: 74, 222, 128"><div class="orb">__power__</div>
        <div class="t"><b>Windows ile başlat</b><span id="auto-sub"></span></div><i class="sw" id="auto-sw"></i></div>
      <div class="act" id="a-restart" data-act="restart" style="--a: 167, 139, 250"><div class="orb">__restart__</div>
        <div class="t"><b>Yeniden başlat</b><span>Lust kapanıp açılır</span></div><i class="chev">›</i></div>
      <div class="act" id="a-quit" style="--a: 248, 113, 113"><div class="orb">__close__</div>
        <div class="t"><b id="quit-t">Lust'ı kapat</b><span id="quit-s">Tamamen kapat</span></div><i class="chev">›</i></div>
    </div>
  </section>

  <section class="page" id="page-settings">
    <div class="card client-card">
      <div class="ico">__brush__</div>
      <div class="t"><b>LoL istemcisi ayarları</b><span>Tema, duvar kağıdı, eklentiler, Lobby Reveal ve yedekler LoL'ün içinde açılır.
        LoL'de artık LUST sekmesi yok: buradan aç.</span></div>
      <button class="btn primary" data-act="client_panel">İstemcide aç</button>
    </div>
    <div class="sg-head">
      <div class="sg-tabs" id="sg-tabs">
        <button class="on" data-sg="all">Hepsi</button><button data-sg="game">Oyun</button>
        <button data-sg="app">Uygulama</button><button data-sg="look">Görünüm</button>
      </div>
    </div>
    <div class="sg-grid" id="sg-grid"></div>
    <div class="sg-foot">
      <div class="sg-mini" data-act="clear_cache">__trash__<div><b>Önbelleği temizle</b><span id="sg-cache">Hub'ın tarayıcı önbelleği</span></div></div>
      <div class="sg-mini" data-act="open_data">__folder__<div><b>Lust klasörü</b><span>Ayarlar, skinler, loglar</span></div></div>
    </div>
  </section>

  <section class="page" id="page-wallpaper">
    <div class="section">LoL istemcisinin arka planı · birini seç</div>
    <div class="walls" id="walls"></div>
    <div class="drop" id="wall-drop">__download__<div><b>Duvar kağıdı ekle</b><br>Resim (.jpg, .png, .webp, .gif) veya video (.mp4, .webm) dosyasını buraya sürükle</div>
      <button class="btn" data-act="wallpaper_folder">Klasörü aç</button>
    </div>
    <div class="note" id="wall-note">Seçtiğin duvar kağıdı League açıksa hemen, kapalıysa açılınca uygulanır.</div>
  </section>
  <section class="page" id="page-maps">
    <div class="seg mods-seg"><button data-goto="skins" data-tab="skins">Custom skinler</button><button data-goto="maps" data-tab="maps">Haritalar</button></div>
    <div class="section">Sonraki maçın haritası · bir tane seçilir</div>
    <div class="maps" id="maps"></div>
    <div class="drop" id="drop">__download__<div><b>Harita modu ekle</b><br>.zip, .fantome veya .modpkg dosyasını buraya sürükle</div>
      <button class="btn" data-act="map_folder">Klasörü aç</button>
    </div>
    <div class="section" id="cat-h" hidden>Lust kataloğu</div>
    <div class="maps" id="catalog"></div>
    <div class="note">Seçtiğin harita bir sonraki maçta yüklenir. LoL istemcisindeki LUST panelinin Maps sekmesi de aynı listeyi kullanır.</div>
  </section>

  <section class="page" id="page-fonts">
    <div class="section">Oyunun fontu</div>
    <div class="maps" id="fonts"></div>
    <div class="drop" id="font-drop">__download__<div><b>Font modu ekle</b><br>.zip, .fantome veya .modpkg dosyasını buraya sürükle</div>
      <button class="btn" data-act="font_folder">Klasörü aç</button>
    </div>
    <div class="note">Seçtiğin font bir sonraki maçta yüklenir. LoL istemcisindeki LUST panelinin Fonts sekmesi de aynı listeyi kullanır.</div>
  </section>

  <section class="page" id="page-skins">
    <div class="seg mods-seg"><button data-goto="skins" data-tab="skins">Custom skinler</button><button data-goto="maps" data-tab="maps">Haritalar</button></div>
    <div class="sk-off" id="sk-off">Custom skinler Ayarlar'da kapalı: açık olanlar da oyunda yüklenmez.</div>
    <div class="sk-head"><div class="section" id="sk-count">Custom skinler</div>
      <input id="sk-find" type="search" placeholder="Skin veya şampiyon ara" autocomplete="off"></div>
    <div class="sk-hint">İstediğin kadar skini tikle: her şampiyon için bir skin, oyunda o şampiyonu oynarsan yüklenir.</div>
    <div class="skins" id="skins"></div>
    <div class="drop" id="skin-drop">__download__<div><b>Custom skin ekle</b><br>.zip, .fantome veya .modpkg dosyasını buraya sürükle</div>
      <button class="btn" data-act="skin_folder">Klasörü aç</button>
    </div>
    <div class="note">Açık bir skin, o şampiyonla varsayılan skininde oyuna girince yüklenir; her şampiyonda bir skin açık olabilir. LoL istemcisindeki LUST panelinin Custom skins sekmesi de aynı listeyi kullanır.</div>
  </section>

  <section class="page" id="page-profile">
    <div class="pf-hero" id="pf-hero"><div><small>Profil arka planı</small><h2 id="pf-name">…</h2>
      <span class="pf-chip" id="pf-chip"></span></div></div>
    <div class="pf-head"><div class="section">Şampiyon</div>
      <input id="pf-find" type="search" placeholder="Şampiyon ara" autocomplete="off"></div>
    <div class="champs" id="pf-champs"></div>
    <div class="pf-head"><div class="section" id="pf-skins-title">Skinler</div></div>
    <div class="pskins" id="pf-skins"></div>
    <div class="note">Seçtiğin skin, LoL'deki profilinin (Genel Bakış) arka planı olur; sahip olmadığın skinler de seçilebilir.
      Arka plan Riot'ta kaydedilir, profiline bakan arkadaşların da görür. LoL kapalıyken seçersen açılınca konur.</div>
  </section>

  <section class="page" id="page-icon">
    <div class="ic-hero" id="ic-hero"><div class="ic-big" id="ic-big">__user__</div>
      <div><small>Profil simgesi</small><h2 id="ic-name">…</h2><span class="ic-chip" id="ic-chip"></span></div>
      <div class="ic-acts"><button class="btn" id="ic-reset" hidden>Kendi simgeme dön</button>
        <button class="btn" data-act="clear_tokens" title="Profilindeki meydan okuma tokenlerini kaldırır">Tokenleri kaldır</button></div></div>
    <div class="ic-head"><div class="section" id="ic-count">Simgeler</div>
      <input id="ic-find" type="search" placeholder="Simge ara: ad, yıl, numara" autocomplete="off"></div>
    <div class="icons" id="ic-list"></div>
    <button class="btn ic-more" id="ic-more" hidden>Daha fazla göster</button>
    <div class="note">Seçtiğin simge, sahip olmasan da LoL istemcisinde senin simgen olarak görünür: sağ üstte, profilinde, sohbette ve lobide.
      Bu yalnızca senin ekranında olur; Riot'a gönderilmez, arkadaşların ve diğer oyuncular gerçek simgeni görmeye devam eder.
      "Tokenleri kaldır" ise profilinin altındaki meydan okuma tokenlerini Riot'ta kaldırır; herkes için boş görünür (LoL açık olmalı).</div>
  </section>

  <section class="page" id="page-auto">
    <div class="au-cards">
      <div class="au" data-auto="accept"><i class="au-i"><svg viewBox="0 0 24 24"><path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/></svg></i>
        <div><b>Auto Accept</b><span>Maç bulununca kabul eder</span></div><i class="au-ck">__check__</i></div>
      <div class="au" data-auto="ban"><i class="au-i"><svg viewBox="0 0 24 24"><path d="M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M9.5 17.5 21 6V3h-3L6.5 14.5M11 19l-6-6M8 16l-4 4M5 21l-2-2"/></svg></i>
        <div><b>Auto Ban</b><span>Sıran gelince listedeki ilk boştakini banlar</span></div><i class="au-ck">__check__</i></div>
      <div class="au" data-auto="pick"><i class="au-i"><svg viewBox="0 0 24 24"><path d="M5 19 3 7l5 4 4-7 4 7 5-4-2 12z"/></svg></i>
        <div><b>Auto Pick</b><span>Sıran gelince listedeki ilk boştakini seçer</span></div><i class="au-ck">__check__</i></div>
      <div class="au" data-auto="reveal"><i class="au-i"><svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></i>
        <div><b>Lobby Reveal</b><span>Champ select'te takım arkadaşlarının adları ve op.gg</span></div><i class="au-ck">__check__</i></div>
    </div>
    <div class="au-team" id="au-team" hidden>
      <div class="au-team-h"><div class="section">Takımın</div><button class="btn" id="au-multi">op.gg'de hepsi</button></div>
      <div class="au-players" id="au-players"></div>
    </div>
    <div class="au-lists">
      <div class="au-list" data-list="bans"><div class="section">Ban listesi</div><div class="au-chips" id="au-bans"></div>
        <input type="search" placeholder="Banlanacak şampiyon ekle" autocomplete="off"><div class="au-sug"></div></div>
      <div class="au-list" data-list="picks"><div class="section">Pick listesi</div><div class="au-chips" id="au-picks"></div>
        <input type="search" placeholder="Seçilecek şampiyon ekle" autocomplete="off"><div class="au-sug"></div></div>
    </div>
    <div class="note">Sıra sana gelince listendeki ilk boş şampiyon seçilir; banlanmış, alınmış ya da takım arkadaşının istediği şampiyon atlanır.
      Lust bunları LoL istemcisi üzerinden yapar, League açıkken çalışır.</div>
  </section>

  <section class="page" id="page-patch">
    <div class="pn-hero">
      <div class="pn-ver" id="pn-ver">…</div>
      <div class="pn-t"><small>Yama notları</small><h2 id="pn-title">Yama notları alınıyor…</h2><span id="pn-sub"></span></div>
      <button class="btn primary" data-act="patch_open">Notların tamamı</button>
    </div>
    <div class="section" id="pn-count">Değişen şampiyonlar</div>
    <div class="pn-list" id="pn-list"></div>
    <div class="note">Riot'un yama notlarından (leagueoflegends.com), birkaç saatte bir yenilenir.</div>
  </section>

  <section class="page" id="page-spotify">
    <div class="np" id="np">
      <div class="np-bg" id="np-bg"></div>
      <div class="np-art" id="np-art">__spotify__</div>
      <div class="np-main">
        <small class="np-k" id="np-k">Şimdi çalan</small>
        <b id="np-title">Spotify'da bir şey çalmıyor</b>
        <span id="np-artist">Spotify'ı açıp bir şarkı başlat</span>
        <div class="np-time"><span id="np-pos">0:00</span><div class="np-bar"><i id="np-fill"></i></div><span id="np-dur">0:00</span></div>
      </div>
      <div class="np-viz" id="np-viz" aria-hidden="true"></div>
      <div class="np-ctl">
        <button class="np-b" id="np-prev" title="Önceki">__prev__</button>
        <button class="np-b np-play" id="np-play" title="Oynat / duraklat">__play__</button>
        <button class="np-b" id="np-next" title="Sonraki">__next__</button>
        <button class="np-b" id="np-mute" title="Spotify'ı sessize al">__vol__</button>
      </div>
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
<div class="rz" data-edge="n"></div><div class="rz" data-edge="s"></div><div class="rz" data-edge="e"></div>
<div class="rz" data-edge="w"></div><div class="rz" data-edge="ne"></div><div class="rz" data-edge="nw"></div>
<div class="rz" data-edge="se"></div><div class="rz" data-edge="sw"></div>
<div id="toast"></div>
<div id="lost">Lust yeniden başlıyor…</div>
<script>
const TOKEN = __TOKEN__;
// Warnings closed with their X stay closed until Lust starts again (a new token), and a
// different warning on the same card shows again
let dismissed = {};
try {
  const saved = JSON.parse(localStorage.getItem("lust-dismissed") || "{}");
  if (saved.token === TOKEN) dismissed = saved.keys || {};
} catch (e) { /* storage off: closed warnings come back on the next window */ }
const isDismissed = (card, state) => dismissed[card] === String(state);
function dismiss(card, state) {
  dismissed[card] = String(state);
  try { localStorage.setItem("lust-dismissed", JSON.stringify({ token: TOKEN, keys: dismissed })); } catch (e) { /* see above */ }
}
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
const LTK_TITLE = {
  missing: "LTK patcher eksik",
  locked: "Bu LTK patcher Lust'la çalışmıyor",
  expired: "LTK patcher'ın süresi doldu",
  expiring: "LTK patcher'ın süresi doluyor",
};
const STATUS = { online: "Çevrimiçi", offline: "Çevrimdışı", mobile: "Mobil" };
const ICON = { sparkle: `__sparkle__`, plusbox: `__plusbox__`, users: `__users__`, shield: `__shield__`, power: `__power__`,
  sync: `__sync__`, bolt: `__bolt__`, spotify: `__spotify__`, moon: `__moon__`, play: `__play__`, image: `__image__`, wind: `__wind__`, check: `__check__` };

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

function splashTint(img) {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 32; canvas.height = 18;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, 32, 18);
    const data = ctx.getImageData(0, 0, 32, 18).data;
    const picks = [];
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i + 1], b = data[i + 2];
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      const sat = max ? (max - min) / max : 0;
      if (max > 70) picks.push([sat * max, r, g, b]);
    }
    picks.sort((a, z) => z[0] - a[0]);
    const top = picks.slice(0, Math.max(8, Math.floor(picks.length / 8)));
    if (!top.length) return "";
    const avg = [1, 2, 3].map((k) => Math.round(top.reduce((sum, p) => sum + p[k], 0) / top.length));
    return avg.join(", ");
  } catch (error) {
    return "";
  }
}

// The settings page: [key, group, icon, title, on text, off text, wide, options]
const SETTINGS = [
  ["skins", "game", ICON.sparkle, "Skinler", "Oyunda uygulanır", "Kapalı: League normal açılır"],
  ["custom_skins", "game", ICON.plusbox, "Özel skinler", "Açık olanlar oynar", "Hepsi kapalı"],
  ["lobby_reveal", "game", ICON.users, "Lobby Reveal", "Takım arkadaşları görünür", "Kapalı"],
  ["rose_guard", "game", ICON.shield, "Rose koruması", "Rose açılırsa kapatılır", "Kapalı"],
  ["autostart", "app", ICON.power, "Windows ile başlat", "Açık", "Kapalı"],
  ["auto_update", "app", ICON.sync, "Otomatik güncelleme", "League kapalıyken kurulur", "Yeni sürümde sorulur"],
  ["quiet_start", "app", ICON.moon, "Sessiz başla", "Pencere açılmaz, tepside durur", "Açılışta pencere görünür"],
  ["spotify_auto", "app", ICON.spotify, "Spotify'ı otomatik güncelle", "Spotify güncellenince tema geri gelir", "Tema elle uygulanır"],
  ["launch_league", "app", ICON.play, "League'i Lust ile aç", "Lust açılınca League başlar", "League'i sen açarsın"],
  ["performance_mode", "app", ICON.bolt, "Performans modu", "Maçta Lust dinlenir", "Maçta da her şey çalışır"],
  ["reduce_motion", "look", ICON.wind, "Animasyonları azalt", "Hareketler kapalı", "Hareketler açık"],
  ["backdrop", "look", ICON.image, "Arka plan", "", "", true, [["cinematic", "Sinematik"], ["hextech", "Sade hextech"]]],
];
let sgGroup = "all", sgKey = "";
function settingValue(s, key) {
  if (key === "autostart") return !!s.autostart;
  if (key === "auto_update") return !!s.auto_update;
  if (key === "spotify_auto") return !!(s.spotify || {}).auto;
  const values = s.settings || {};
  const fallback = { performance_mode: true, skins: true, custom_skins: true, lobby_reveal: true, rose_guard: true, quiet_start: false,
    launch_league: true, backdrop: "cinematic", reduce_motion: false };
  return key in values ? values[key] : fallback[key];
}
function drawSettings(s) {
  const key = sgGroup + JSON.stringify(SETTINGS.map(([k]) => settingValue(s, k)));
  if (key === sgKey) return;
  sgKey = key;
  $("sg-grid").replaceChildren(...SETTINGS.filter((x) => sgGroup === "all" || x[1] === sgGroup).map(
    ([k, , icon, title, onText, offText, wide, options]) => {
      const value = settingValue(s, k);
      const tile = document.createElement("div");
      tile.className = "sg" + (options ? "" : (value ? " on" : "")) + (wide ? " wide" : "");
      tile.innerHTML = `<div class="si">${icon}</div><div><b></b><span></span></div>`;
      tile.querySelector("b").textContent = title;
      tile.querySelector("span").textContent = options ? "Hub'ın arkasındaki görüntü" : (value ? onText : offText);
      if (options) {
        const opt = document.createElement("div");
        opt.className = "opt";
        options.forEach(([v, label]) => {
          const i = Object.assign(document.createElement("i"), { textContent: label, className: v === value ? "on" : "" });
          i.addEventListener("click", (e) => { e.stopPropagation(); act("setting", { key: k, value: v }); });
          opt.appendChild(i);
        });
        tile.appendChild(opt);
      } else {
        tile.addEventListener("click", () => act(["autostart", "auto_update", "spotify_auto"].includes(k) ? k : "setting",
          { key: k, value: !value }));
      }
      return tile;
    }));
}

// ---- Spotify: now playing ----
let media = {}, mediaAt = 0, coverShown = -1, level = 0, bars = [];
const ICON_PLAY = `__play__`, ICON_PAUSE = `__pause__`, ICON_VOL = `__vol__`, ICON_VOLX = `__volx__`;
const clock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
function spotifyVisible() {
  return $("page-spotify").classList.contains("active") && !document.hidden && !(state && state.resting);
}
async function pollMedia() {
  if (spotifyVisible()) {
    try { media = await api("/api/media"); mediaAt = Date.now(); drawMedia(); } catch (e) {}
  }
  setTimeout(pollMedia, 1000);
}
async function pollLevel() {
  if (spotifyVisible() && media.playing) {
    try { level = (await api("/api/level")).level || 0; } catch (e) { level = 0; }
  } else {
    level = 0;
  }
  setTimeout(pollLevel, 100);
}
function drawMedia() {
  const on = !!media.available;
  $("np").classList.toggle("idle", !on);
  $("np-k").textContent = !on ? "Şimdi çalan" : media.playing ? "Şimdi çalan" : "Duraklatıldı";
  $("np-title").textContent = on ? media.title || "Bilinmeyen şarkı" : "Spotify'da bir şey çalmıyor";
  $("np-artist").textContent = on ? media.artist || "" : "Spotify'ı açıp bir şarkı başlat";
  $("np-play").innerHTML = media.playing ? ICON_PAUSE : ICON_PLAY;
  $("np-mute").innerHTML = media.muted ? ICON_VOLX : ICON_VOL;
  $("np-mute").classList.toggle("muted", !!media.muted);
  $("np-mute").title = media.muted ? "Sesi aç" : "Spotify'ı sessize al";
  if (on && media.cover !== coverShown) {
    coverShown = media.cover;
    const url = `/cover.jpg?v=${media.cover}`;
    const img = new Image();
    img.onload = () => {
      $("np-art").style.backgroundImage = $("np-bg").style.backgroundImage = `url(${url})`;
      $("np-art").classList.add("has");
      $("np-bg").classList.add("on");
    };
    img.src = url;
  }
}
function tickMedia() {
  // Off the Spotify page (or during a match) nothing moves: check twice a second, draw nothing
  if (!spotifyVisible()) { setTimeout(() => requestAnimationFrame(tickMedia), 500); return; }
  if (media.available) {
    const pos = Math.min(media.duration || 0, (media.position || 0) + (media.playing ? (Date.now() - mediaAt) / 1000 : 0));
    $("np-pos").textContent = clock(pos);
    $("np-dur").textContent = clock(media.duration || 0);
    $("np-fill").style.width = media.duration ? `${(pos * 100) / media.duration}%` : "0%";
  }
  // Bars follow Spotify's sound level, each at its own pace so they move like a spectrum
  const t = Date.now() / 1000;
  bars.forEach((bar, i) => {
    const wave = 0.55 + 0.45 * Math.sin(t * (3 + (i % 5) * 1.3) + i * 1.7);
    const target = media.playing ? Math.min(1, level * 1.6) * wave : 0.04;
    bar.h = bar.h + (target - bar.h) * 0.35;
    bar.el.style.height = `${Math.max(3, Math.round(bar.h * 44))}px`;
  });
  requestAnimationFrame(tickMedia);
}
for (let i = 0; i < 16; i++) {
  const el = document.createElement("i");
  $("np-viz").appendChild(el);
  bars.push({ el, h: 0.04 });
}
const mediaAct = (action) => fetch(`/api/media/${action}`, { method: "POST", headers: { "X-Lust-Hub": TOKEN } })
  .then(() => setTimeout(async () => { try { media = await api("/api/media"); mediaAt = Date.now(); drawMedia(); } catch (e) {} }, 350))
  .catch(() => {});
$("np-prev").addEventListener("click", () => mediaAct("previous"));
$("np-play").addEventListener("click", () => mediaAct("play_pause"));
$("np-next").addEventListener("click", () => mediaAct("next"));
$("np-mute").addEventListener("click", () => mediaAct("mute"));
pollMedia(); pollLevel(); requestAnimationFrame(tickMedia);

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
  const hero = s.hero || {};
  $("h-small").textContent = starting ? (s.detail || "Hazırlanıyor") : (ready ? "Lust hazır · hoş geldin" : "Lust hazırlanıyor");
  if (starting || !hero.name) {
    $("h-title").textContent = starting ? (s.status || "Lust başlıyor") : (ready ? "Lust hazır" : "Lust hazırlanıyor");
  } else {
    $("h-title").replaceChildren(document.createTextNode(hero.name), Object.assign(document.createElement("i"), { textContent: hero.tag ? ` #${hero.tag}` : "" }));
  }
  const chips = [];
  if (!starting && hero.rank) chips.push(["chip rank", hero.rank]);
  if (!starting && (hero.wins || hero.losses)) {
    const total = hero.wins + hero.losses;
    chips.push(["chip", `${hero.wins}G ${hero.losses}M · %${Math.round(hero.wins * 100 / total)}`]);
  }
  if (!starting && hero.level) chips.push(["chip", `Seviye ${hero.level}`]);
  const chipKey = JSON.stringify(chips);
  if ($("h-chips").dataset.key !== chipKey) {
    $("h-chips").dataset.key = chipKey;
    $("h-chips").replaceChildren(...chips.map(([cls, text]) => Object.assign(document.createElement("span"), { className: cls, textContent: text })));
  }
  $("h-sub").textContent = starting ? (s.transfer || bits.join(" · ")) : bits.join(" · ");
  const cut = hero.cutoff;
  $("h-cut").hidden = starting || !cut;
  if (cut) {
    const parts = [["cut gm", `Üstatlık ${cut.grandmaster} LP`], ["cut ch", `Şampiyonluk ${cut.challenger} LP`]];
    const target = hero.tier === "grandmaster" || hero.tier === "challenger" ? cut.challenger : hero.tier === "master" ? cut.grandmaster : 0;
    if (target && hero.lp < target) {
      parts.push(["need", `${hero.tier === "master" ? "Üstatlık" : "Şampiyonluk"} için ${target - hero.lp} LP`]);
      parts.push(["cutbar", Math.max(4, Math.min(100, Math.round(hero.lp * 100 / target)))]);
    }
    const key = JSON.stringify(parts);
    if ($("h-cut").dataset.key !== key) {
      $("h-cut").dataset.key = key;
      $("h-cut").replaceChildren(Object.assign(document.createElement("span"), { textContent: `${cut.region} sınırları:` }),
        ...parts.map(([cls, text]) => {
          const el = document.createElement("span");
          el.className = cls;
          if (cls === "cutbar") {
            const fill = document.createElement("i");
            fill.style.width = "0%";
            el.title = `%${text}`;
            el.appendChild(fill);
            requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = `${text}%`; }));
          } else {
            el.textContent = text;
          }
          return el;
        }));
    }
  }
  const last = hero.last;
  $("h-last").hidden = starting || !last;
  if (last) {
    $("hl-champ").textContent = last.champion;
    $("hl-result").textContent = last.win ? "Galibiyet" : "Mağlubiyet";
    $("hl-result").className = "hl-result " + (last.win ? "win" : "loss");
    $("hl-meta").textContent = `${last.kda} · ${last.queue}`;
  }
  if (hero.image && $("h-art").dataset.image !== String(hero.image)) {
    $("h-art").dataset.image = String(hero.image);
    const img = new Image();
    img.onload = () => {
      $("h-art").style.backgroundImage = `url(${img.src})`;
      $("h-art").classList.add("on");
      $("amb-art").style.backgroundImage = `url(${img.src})`;
      $("amb-art").classList.add("on");
      const tint = splashTint(img);
      if (tint) document.documentElement.style.setProperty("--tint", tint);
    };
    img.src = `/hero.jpg?v=${hero.image}`;
  }
  const busy = s.progress === null || s.progress === undefined;
  $("h-bar").hidden = !starting;
  $("h-bar").classList.toggle("busy", busy);
  $("h-bar").firstElementChild.style.width = busy ? "" : `${s.progress}%`;

  $("rose").hidden = !(s.rose && s.rose.installed) || isDismissed("rose", "installed");
  const ltk = s.patcher || {};
  $("ltk").hidden = !ltk.state || ltk.state === "ok" || isDismissed("ltk", ltk.state);
  if (!$("ltk").hidden) {
    $("ltk-t").textContent = LTK_TITLE[ltk.state] || LTK_TITLE.missing;
    $("ltk-b").textContent = ltk.waiting
      ? "ltk_patcher.zip bekleniyor: İndirilenler'e inince Lust imzasını kontrol edip kendisi kurar."
      : (ltk.state === "expiring"
        ? `Süresi ${ltk.eol} tarihinde doluyor; League'in sonraki güncellemesinden sonra skinler yüklenmez.` +
          (ltk.newer ? " Yeni ltk_patcher.zip hazır." : " Yenisi Rose Discord'unda (#tutorial) paylaşılınca indir.")
        : "Skinler için ltk_patcher.zip gerekli. İndir, Lust onu İndirilenler'de bulup kendisi kurar.");
  }
  $("prompt").hidden = !s.prompt;
  if (s.prompt) {
    $("q-title").textContent = `Lust ${s.prompt.version} kurulmaya hazır`;
    $("q-body").textContent = `Sendeki sürüm ${s.prompt.current}. Şimdi kurulsun mu?`;
  }
  $("ap-sub").textContent = off.running ? (STATUS[off.status] || "Çevrimiçi") : "Seçmek için League'i buradan aç";
  document.querySelectorAll(".status-seg button").forEach((b) => {
    b.disabled = !off.running || starting;
    b.classList.toggle("on", !!off.running && off.status === b.dataset.status);
  });
  $("a-league").classList.toggle("live", !!s.league);
  $("a-league-k").textContent = s.league ? "Canlı" : (s.ready ? "Hazır" : "Hazırlanıyor");
  $("a-league-t").textContent = s.league ? "League açık" : "League'i aç";
  $("a-league-s").textContent = s.league ? (off.running ? "Lust Offline üzerinden bağlı" : "Skinler oyunda uygulanır")
    : "Lust Offline üzerinden, skinler hazır";
  $("auto-sub").textContent = s.autostart ? "Açık" : "Kapalı";
  $("auto-sw").classList.toggle("on", !!s.autostart);
  $("a-restart").classList.toggle("off", !s.running);
  const armed = Date.now() - quitArmed < 3000;
  $("a-quit").classList.toggle("armed", armed);
  $("quit-t").textContent = armed ? "Emin misin?" : "Lust'ı kapat";
  $("quit-s").textContent = armed ? "Kapatmak için tekrar tıkla" : "Tamamen kapat";

  $("v-sub").textContent = s.pending ? `Lust ${s.pending} indirildi · League kapalıyken kurulacak`
    : s.update_available ? `Yeni sürüm ${s.latest}` : `Güncel · son kontrol ${ago(s.checked_at)}`;
  $("auto-upd").classList.toggle("on", !!s.auto_update);
  $("v-sub").style.color = s.update_available ? "var(--accent)" : "";
  $("v-btn").innerHTML = (s.update_available ? ICON_DOWNLOAD : ICON_SYNC) + (s.update_available ? "Güncelle" : "Kontrol et");
  $("vdot").classList.toggle("new", !!(s.update_available || s.pending));
  $("ver-pill").title = s.pending ? `Lust ${s.pending} indirildi` : s.update_available ? `Yeni sürüm ${s.latest}` : "Sürüm ve yenilikler";
  $("v-btn").disabled = starting;
  const items = ((s.news || {}).items || []).slice(0, 6);
  if (JSON.stringify(items) !== newsKey) {
    newsKey = JSON.stringify(items);
    $("news").replaceChildren(...items.map((x) => { const li = document.createElement("li"); li.textContent = x; return li; }));
  }

  drawSettings(s);
  drawHome(s);
  const st = s.settings || {};
  document.body.classList.toggle("bd-hextech", st.backdrop === "hextech");
  document.body.classList.toggle("calm", !!st.reduce_motion || !!s.resting);
  $("sg-cache").textContent = `Hub'ın tarayıcı önbelleği${s.cache_mb ? ` · ${s.cache_mb} MB` : ""}`;
  const sp = s.spotify || {};
  const label = (THEMES.find((t) => t.key === sp.theme) || {}).label || "Orijinal";
  if (!choice) { choice = sp.theme || "luminous"; drawThemes(); }
  $("sp-apply").disabled = $("sp-restore").disabled = !sp.installed || !!sp.busy;

  if (s.toast && s.toast.id !== toastId) {
    if (toastId !== null) showToast(s.toast.text);
    toastId = s.toast.id;
  }
  if (toastId === null) toastId = 0;
  if (s.prompt && page !== "home") showPage("home");
}

async function poll() {
  try { render(await api("/api/state")); failures = 0; $("lost").style.display = "none"; }
  catch (e) { if (++failures >= 3) $("lost").style.display = "grid"; }
}
// ---- pages: the home tiles lead to each one, Esc or the back button comes home ----
const PAGES = { home: "", lol: "Profil", spotify: "Spotify", maps: "Skinler ve Haritalar", fonts: "Fontlar", skins: "Skinler ve Haritalar",
  profile: "Profil arka planı", icon: "Profil simgesi", settings: "Ayarlar", patch: "Patch notes", wallpaper: "Duvar kağıdı", auto: "Champ select" };
let page = "home";
function showPage(name) {
  if (!(name in PAGES)) name = "home";
  page = name;
  document.body.dataset.page = name;
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
  $("title").textContent = PAGES[name];
  $("title").hidden = name === "home";
  $("word").hidden = name !== "home";
  $("back").hidden = name === "home";
  document.querySelectorAll(".mods-seg button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  if (name === "home") { loadTiles(); loadAuto(); }
  if (name === "maps") loadMaps();
  if (name === "fonts") loadFonts();
  if (name === "skins") loadSkins();
  if (name === "profile") loadProfile();
  if (name === "icon") loadIcons();
  if (name === "patch") loadPatch();
  if (name === "wallpaper") loadWalls();
  if (name === "auto") loadAuto();
}
const awake = () => !document.hidden && !(state && state.resting);

// Text with bold parts: ["plain", ["b", "bold", "class"], ...], redrawn only when it changes
function fill(id, parts) {
  const el = $(id);
  const key = JSON.stringify(parts);
  if (el.dataset.key === key) return;
  el.dataset.key = key;
  el.replaceChildren(...parts.map((p) => typeof p === "string" ? document.createTextNode(p)
    : Object.assign(document.createElement(p[0]), { textContent: p[1], className: p[2] || "" })));
}
function setBg(id, url, cls) {
  const el = $(id);
  if (!url) { el.classList.remove("on"); el.dataset.url = ""; return; }
  if (el.dataset.url === String(url)) return;
  el.dataset.url = String(url);
  const img = new Image();
  // A list of urls: the first that loads wins
  const urls = Array.isArray(url) ? url : [url];
  let i = 0;
  img.onload = () => {
    if (el.dataset.url !== String(url)) return;
    el.style.backgroundImage = `url("${urls[i]}")`;
    el.className = el.className.replace(/ rift/g, "") + (cls && i === urls.length - 1 ? ` ${cls}` : "");
    el.classList.add("on");
  };
  img.onerror = () => { if (++i < urls.length && el.dataset.url === String(url)) img.src = urls[i]; };
  img.src = urls[0];
}
function setArt(id, url) {
  const el = $(id);
  if (url && el.dataset.url !== url) { el.dataset.url = url; el.style.backgroundImage = `url("${url}")`; }
}
const greeting = () => {
  const h = new Date().getHours();
  return h < 6 ? "İyi geceler" : h < 12 ? "Günaydın" : h < 18 ? "İyi günler" : h < 22 ? "İyi akşamlar" : "İyi geceler";
};

function drawHome(s) {
  const starting = s.phase !== "ready";
  const hero = s.hero || {};
  $("hm-hi").textContent = starting ? (s.detail || "Lust hazırlanıyor") : greeting();
  fill("hm-name", starting ? [s.status || "Lust başlıyor"]
    : hero.name ? [["b", hero.name], ["i", hero.tag ? ` #${hero.tag}` : ""]] : [["b", "Lust"], " hazır"]);
  const sub = [];
  if (!starting && hero.rank) sub.push(hero.rank);
  if (!starting && (hero.wins || hero.losses)) sub.push(`${hero.wins}G ${hero.losses}M`);
  if (!starting && hero.last) sub.push(`Son maç: ${hero.last.champion} · ${hero.last.win ? "Galibiyet" : "Mağlubiyet"}`);
  $("hm-sub").textContent = starting ? (s.transfer || "") : sub.join(" · ");
  const busy = s.progress === null || s.progress === undefined;
  $("h-bar").hidden = !starting;
  $("h-bar").classList.toggle("busy", busy);
  $("h-bar").firstElementChild.style.width = busy ? "" : `${s.progress}%`;
  $("hm-league").classList.toggle("live", !!s.league);
  $("hm-league-t").textContent = s.league ? "League açık" : "League'i aç";
  $("lg-t").textContent = starting ? "Lust başlıyor" : s.league ? "League açık" : "League kapalı";
  drawTiles();
}

let tiles = {}, auto = null;
const TIER_COLOR = { iron: "#8a7a73", bronze: "#b0703f", silver: "#a9b8c6", gold: "#e0b54a", platinum: "#4fc1b5",
  emerald: "#2ecc71", diamond: "#5b8def", master: "#b14fe0", grandmaster: "#e0453f", challenger: "#f2c94c" };
// Summoner's Rift art from the client's own game mode assets; the minimap if neither loads
const SRU = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/content/src/leagueclient/gamemodeassets/classic_sru/img/";
const RIFT = [SRU + "champ-select-flyout-background.jpg", SRU + "gameflow-background.jpg",
  "https://ddragon.leagueoflegends.com/cdn/6.8.1/img/map/map11.png"];
function drawTiles() {
  const s = state || {}, t = tiles || {}, hero = s.hero || {}, off = s.offline || {};
  // LoL: the welcome card's rank and last match
  const lol = [];
  if (hero.rank) lol.push(["b", hero.rank]);
  if (hero.last) lol.push(`${lol.length ? " · " : ""}Son maç ${hero.last.champion}`);
  if (off.running) lol.push(` · ${STATUS[off.status] || "Çevrimiçi"}`);
  fill("t-lol", lol.length ? lol : [s.league ? "League açık" : "Profilin, rank sınırları ve Lust Offline"]);
  // The last match's champion splash, and the season's win rate in the rank's colour
  const tier = (hero.tier || "").toLowerCase();
  $("tile-lol").style.setProperty("--tc", TIER_COLOR[tier] || "#c8aa6e");
  const games = (hero.wins || 0) + (hero.losses || 0);
  $("t-lol-rank").hidden = !games;
  if (games) $("t-lol-rank").textContent = `%${Math.round(100 * hero.wins / games)} kazanma · ${games} maç`;
  const lolArt = $("t-lol-art"), lolArtUrl = hero.image ? `/hero.jpg?v=${hero.image}` : "";
  if (lolArt.dataset.url !== lolArtUrl) {
    lolArt.dataset.url = lolArtUrl;
    lolArt.classList.remove("on"); $("t-lol-mark").hidden = false;
    if (lolArtUrl) {
      const img = new Image();
      img.onload = () => {
        if (lolArt.dataset.url !== lolArtUrl) return;
        lolArt.style.backgroundImage = `url("${lolArtUrl}")`;
        lolArt.classList.add("on"); $("t-lol-mark").hidden = true;
      };
      img.src = lolArtUrl;
    }
  }
  const mp = t.maps;
  const sk = t.skins || {};
  const mapText = mp && mp.name ? mp.name : "Sihirdar Vadisi";
  fill("t-maps", sk.count ? [["b", `${sk.count} custom skin`], ` · ${sk.on || 0} açık · ${mapText}`] : [["b", mapText], " · custom skin ekle"]);
  if (mp && mp.preview) setBg("t-maps-bg", `/map-preview?id=${encodeURIComponent(mp.id)}`);
  else setBg("t-maps-bg", RIFT, "rift");
  const wl = t.wallpaper;
  fill("t-wall", wl && !wl.league && wl.name ? [["b", wl.name.replace(/\.[^.]+$/, "")], ` · ${wl.count} duvar kağıdı`]
    : [["b", "LoL'ün kendi arka planı"], wl && wl.count ? ` · ${wl.count} duvar kağıdı` : ""]);
  const wurl = wl && !wl.league && wl.name ? `/wallpaper-file?name=${encodeURIComponent(wl.name)}` : "";
  const vid = $("t-wall-vid");
  $("tile-wall").classList.toggle("vid", !!(wurl && wl.video));
  if (wurl && wl.video) {
    if (vid.dataset.url !== wurl) { vid.dataset.url = wurl; vid.src = wurl; vid.play().catch(() => {}); }
    setBg("t-wall-bg", "");
  } else {
    if (vid.dataset.url) { vid.dataset.url = ""; vid.removeAttribute("src"); vid.load(); }
    setBg("t-wall-bg", wurl);
  }
  const ft = t.fonts;
  fill("t-fonts", ft && ft.name ? [["b", ft.name], " · oyun içi yazı tipi"] : [["b", "League'in fontu"], " · oyun içi yazı tipi"]);
  const art = t.art || {};
  const ic = t.icon;
  fill("t-icon", ic && ic.id ? [["b", ic.name || `#${ic.id}`], " · sadece sende görünür"] : ["İstediğin simge, sahip olmasan da"]);
  const pic = (art.icon || {}).picture || "";
  $("tile-icon").classList.toggle("pic", !!pic);
  setBg("t-icon-bg", pic || (art.icon || {}).splash || "");
  const pf = t.profile;
  fill("t-profile", pf && pf.name ? [["b", pf.name], " · profilinde"] : ["Profilinin arka planı, istediğin skin"]);
  setBg("t-profile-bg", (art.profile || {}).splash || "");
  const on = !!media.available;
  fill("t-spotify", on ? [["b", media.title || "Bilinmeyen şarkı"], media.artist ? ` · ${media.artist}` : ""] : ["Spotify'da bir şey çalmıyor"]);
  $("t-eq").hidden = !(on && media.playing);
  $("tile-spotify").classList.toggle("playing", !!(on && media.playing));
  const cover = on && media.cover ? `/cover.jpg?v=${media.cover}` : "";
  $("tile-spotify").classList.toggle("cover", !!cover);
  if (cover && $("t-sp-cover").dataset.url !== cover) {
    $("t-sp-cover").dataset.url = cover;
    $("t-sp-cover").style.backgroundImage = `url("${cover}")`;
    $("t-spotify-bg").style.backgroundImage = `url("${cover}")`;
  } else if (!cover) { $("t-sp-cover").dataset.url = ""; $("t-spotify-bg").style.backgroundImage = ""; }
  const a = auto || {};
  const names = [["accept", "Accept"], ["ban", "Ban"], ["pick", "Pick"]];
  const reveal = !!((a.reveal || {}).on);
  const onCount = names.filter(([k]) => a[k]).length + (reveal ? 1 : 0);
  fill("t-auto", onCount ? [["b", `${onCount}/4 açık`], " · sıra gelince senin yerine"] : ["Auto Accept, Ban, Pick ve Lobby Reveal"]);
  const draftKey = JSON.stringify([a.ban, a.pick, a.accept, reveal, a.bans, a.picks]);
  if ($("t-auto-draft").dataset.key !== draftKey) {
    $("t-auto-draft").dataset.key = draftKey;
    const row = (kind, label, ids, on, slots) => {
      const r = document.createElement("div");
      r.className = `dr-row ${kind}${on ? "" : " off"}`;
      const faces = document.createElement("span");
      faces.className = "dr-faces";
      const list = (ids || []).slice(0, slots);
      for (let n = 0; n < slots; n++) {
        const i = document.createElement("i");
        if (list[n]) i.style.backgroundImage = `url("${CHAMP_ICON(list[n])}")`;
        else i.className = "empty";
        faces.append(i);
      }
      r.append(Object.assign(document.createElement("em"), { textContent: label }), faces);
      return r;
    };
    const leds = document.createElement("div");
    leds.className = "dr-leds";
    leds.append(...[["Accept", a.accept], ["Reveal", reveal]].map(([label, on]) =>
      Object.assign(document.createElement("span"), { textContent: label, className: on ? "on" : "" })));
    $("t-auto-draft").replaceChildren(row("pick", "PICK", a.picks, !!a.pick, 3), row("ban", "BAN", a.bans, !!a.ban, 3), leds);
  }
  const warn = (s.rose && s.rose.installed) || ((s.patcher || {}).state && s.patcher.state !== "ok") || s.update_available;
  fill("t-settings", warn ? [["b", s.update_available ? "Güncelleme hazır" : "Bakman gereken bir şey var", "warn"]]
    : [["b", "✓ Her şey yolunda", "ok"], " · güncelleme, onarım, istemci"]);
}
async function loadTiles() {
  try { tiles = await api("/api/tiles"); } catch (e) { return; }
  drawTiles();
}
setInterval(() => { if (page === "home" && awake()) loadTiles(); }, 6000);
// Spotify's tile follows the song while the home page is open
async function homeMedia() {
  if (page === "home" && awake()) {
    try { media = await api("/api/media"); mediaAt = Date.now(); drawTiles(); } catch (e) {}
  }
  setTimeout(homeMedia, 3000);
}
homeMedia();

// ---- patch notes ----
async function loadPatch() {
  let d;
  try { d = await api("/api/patch"); } catch (e) { return; }
  const champs = d.champions || [];
  $("pn-ver").textContent = d.version || "…";
  $("pn-title").textContent = d.title || (d.loading ? "Patch notes alınıyor…" : "Patch notes alınamadı");
  $("pn-sub").textContent = d.url ? `${champs.length} şampiyon değişti${d.items ? ` · ${d.items} eşya` : ""}`
    : (d.loading ? "" : "İnternet bağlantısını kontrol et, birazdan yeniden denenecek");
  $("pn-count").textContent = champs.length ? `Değişen şampiyonlar · ${champs.length}` : "Değişen şampiyonlar";
  $("pn-list").replaceChildren(...champs.map((c) => {
    const el = document.createElement("div");
    el.className = "pn";
    const face = document.createElement("i");
    if (c.icon) face.style.backgroundImage = `url("${c.icon}")`;
    const text = document.createElement("div");
    text.append(Object.assign(document.createElement("b"), { textContent: c.name }),
      Object.assign(document.createElement("span"), { textContent: c.summary || "Ayrıntılar notların tamamında" }));
    el.append(face, text);
    return el;
  }));
  if (d.loading && page === "patch") setTimeout(() => page === "patch" && loadPatch(), 2500);
}

// ---- champ select: Auto Accept, Ban, Pick and Lobby Reveal ----
async function loadAuto() {
  try { auto = await api("/api/auto"); } catch (e) { return; }
  drawAuto();
  drawTiles();
}
setInterval(() => { if (page === "auto" && awake()) loadAuto(); }, 2000);
function saveAuto(changes) {
  Object.assign(auto, changes);
  drawAuto(); drawTiles();
  act("auto_set", { changes });
}
function drawAuto() {
  if (!auto) return;
  const reveal = auto.reveal || {};
  document.querySelectorAll(".au").forEach((card) => {
    const k = card.dataset.auto;
    card.classList.toggle("on", k === "reveal" ? !!reveal.on : !!auto[k]);
  });
  const names = Object.fromEntries((auto.champions || []).map((c) => [c.id, c.name]));
  [["bans", "au-bans"], ["picks", "au-picks"]].forEach(([key, id]) => {
    const ids = auto[key] || [];
    const sig = JSON.stringify(ids) + Object.keys(names).length;
    if ($(id).dataset.key === sig) return;
    $(id).dataset.key = sig;
    $(id).replaceChildren(...ids.map((cid, n) => {
      const chip = document.createElement("span");
      chip.className = "au-chip";
      const img = Object.assign(document.createElement("img"), { src: CHAMP_ICON(cid), alt: "" });
      const x = Object.assign(document.createElement("button"), { textContent: "×", title: "Çıkar" });
      x.addEventListener("click", () => saveAuto({ [key]: ids.filter((v) => v !== cid) }));
      chip.append(Object.assign(document.createElement("em"), { textContent: n + 1 }), img,
        document.createTextNode(names[cid] || `#${cid}`), x);
      return chip;
    }));
    if (!ids.length) $(id).append(Object.assign(document.createElement("span"), { className: "note", textContent: "Liste boş: aşağıdan şampiyon ekle." }));
  });
  $("au-team").hidden = !(reveal.on && reveal.active && (reveal.players || []).length);
  const team = JSON.stringify(reveal.players || []);
  if ($("au-players").dataset.key !== team) {
    $("au-players").dataset.key = team;
    $("au-players").replaceChildren(...(reveal.players || []).map((p) => {
      const el = document.createElement("div");
      el.className = "au-pl";
      el.append(Object.assign(document.createElement("b"), { textContent: p.gameName || "?" }),
        Object.assign(document.createElement("i"), { textContent: p.gameTag ? `#${p.gameTag}` : "" }),
        Object.assign(document.createElement("small"), { textContent: (p.position || "").toLowerCase() }));
      if (p.opggUrl) el.addEventListener("click", () => act("open_link", { url: p.opggUrl }));
      return el;
    }));
  }
}
document.querySelectorAll(".au").forEach((card) => card.addEventListener("click", () => {
  if (!auto) return;
  const k = card.dataset.auto;
  if (k === "reveal") {
    const on = !(auto.reveal || {}).on;
    auto.reveal = Object.assign({}, auto.reveal, { on });
    drawAuto(); drawTiles();
    act("setting", { key: "lobby_reveal", value: on });
    return;
  }
  saveAuto({ [k]: !auto[k] });
}));
$("au-multi").addEventListener("click", () => auto && auto.reveal && act("open_link", { url: auto.reveal.multiUrl }));
document.querySelectorAll(".au-list").forEach((box) => {
  const key = box.dataset.list, input = box.querySelector("input"), sug = box.querySelector(".au-sug");
  const suggest = () => {
    const find = input.value.trim().toLocaleLowerCase("tr");
    const chosen = (auto && auto[key]) || [];
    const all = ((auto && auto.champions) || []).filter((c) => !chosen.includes(c.id)
      && (!find || c.name.toLocaleLowerCase("tr").includes(find))).slice(0, find ? 30 : 0);
    sug.replaceChildren(...all.map((c) => {
      const row = document.createElement("div");
      row.append(Object.assign(document.createElement("img"), { src: CHAMP_ICON(c.id), alt: "" }), document.createTextNode(c.name));
      row.addEventListener("mousedown", (e) => {
        e.preventDefault();
        if (chosen.length >= (auto.max || 5)) { showToast(`En fazla ${auto.max || 5} şampiyon`); return; }
        saveAuto({ [key]: [...chosen, c.id] });
        input.value = ""; sug.replaceChildren();
      });
      return row;
    }));
  };
  input.addEventListener("input", suggest);
  input.addEventListener("blur", () => setTimeout(() => sug.replaceChildren(), 100));
});

// ---- map skins ----
const ICON_MAP = `__map__`, ICON_TRASH = `__trash__`;
let mapsKey = "";
function mapCard(m, catalogItem) {
  const card = document.createElement("div");
  card.className = "mapc" + (m.selected ? " on" : "");
  const shot = document.createElement("div");
  shot.className = "shot";
  shot.innerHTML = ICON_MAP;
  const src = catalogItem ? m.preview : (m.preview ? `/map-preview?id=${encodeURIComponent(m.id)}` : "");
  if (src) { shot.classList.add("img"); shot.style.backgroundImage = `url("${src}")`; }
  card.appendChild(shot);
  const b = document.createElement("b"); b.textContent = m.name; card.appendChild(b);
  const span = document.createElement("span");
  span.textContent = catalogItem ? (m.author ? `${m.author}` : m.description) : (m.description || (m.id ? "Mod" : "League'in kendi haritası"));
  card.appendChild(span);
  if (m.selected) { const tag = document.createElement("i"); tag.className = "tag"; tag.textContent = "Seçili"; card.appendChild(tag); }
  if (catalogItem) {
    const get = document.createElement("button");
    get.className = "btn get" + (m.installed ? "" : " primary");
    get.textContent = m.installing ? "İndiriliyor…" : m.installed ? "Kurulu" : "İndir";
    get.disabled = m.installed || m.installing;
    get.addEventListener("click", (e) => { e.stopPropagation(); act("map_install", { id: m.id }).then(() => setTimeout(loadMaps, 400)); });
    card.appendChild(get);
  } else {
    card.addEventListener("click", () => act("map_select", { id: m.id || null }).then(() => setTimeout(loadMaps, 300)));
    if (m.id) {
      const del = document.createElement("div");
      del.className = "del"; del.title = "Sil"; del.innerHTML = ICON_TRASH;
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        if (del.dataset.armed && Date.now() - Number(del.dataset.armed) < 3000) {
          act("map_delete", { id: m.id }).then(() => setTimeout(loadMaps, 300));
        } else { del.dataset.armed = Date.now(); showToast("Silmek için tekrar bas"); }
      });
      card.appendChild(del);
    }
  }
  return card;
}
async function loadMaps() {
  let data;
  try { data = await api("/api/maps"); } catch (e) { return; }
  const key = JSON.stringify(data);
  if (key === mapsKey) return;
  mapsKey = key;
  const list = $("maps");
  list.innerHTML = "";
  list.appendChild(mapCard({ id: "", name: "Varsayılan", selected: !data.selected }, false));
  data.installed.forEach((m) => list.appendChild(mapCard(m, false)));
  const cat = $("catalog");
  cat.innerHTML = "";
  $("cat-h").hidden = !data.catalog.length;
  data.catalog.forEach((m) => cat.appendChild(mapCard(m, true)));
}
setInterval(() => { if ($("page-maps").classList.contains("active")) loadMaps(); }, 3000);
// A file dropped anywhere else must not replace the page with it
["dragover", "drop"].forEach((t) => document.addEventListener(t, (e) => e.preventDefault()));
const drop = $("drop");
["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", async (e) => {
  for (const file of e.dataTransfer.files) {
    showToast(`${file.name} ekleniyor…`);
    try {
      const r = await fetch(`/api/maps/upload?name=${encodeURIComponent(file.name)}`,
        { method: "POST", headers: { "X-Lust-Hub": TOKEN }, body: file });
      const out = await r.json();
      if (out.message) showToast(out.message);
    } catch (err) { showToast("Eklenemedi"); }
  }
  mapsKey = ""; loadMaps();
});

// ---- wallpaper ----
let wallsKey = "";
function wallCard(w, data) {
  const card = document.createElement("div");
  const on = w ? !data.league && data.name === w.name : data.league;
  card.className = "wallc" + (on ? " on" : "") + (w ? "" : " league");
  if (!w) {
    card.innerHTML = `__lol__`;
  } else if (w.video) {
    const v = document.createElement("video");
    v.muted = true; v.loop = true; v.playsInline = true; v.preload = "metadata";
    v.src = `/wallpaper-file?name=${encodeURIComponent(w.name)}#t=0.5`;
    card.addEventListener("mouseenter", () => v.play().catch(() => {}));
    card.addEventListener("mouseleave", () => v.pause());
    card.appendChild(v);
    const k = document.createElement("i"); k.className = "kind"; k.textContent = "Video"; card.appendChild(k);
  } else {
    const img = document.createElement("img");
    img.loading = "lazy"; img.src = `/wallpaper-file?name=${encodeURIComponent(w.name)}`;
    card.appendChild(img);
  }
  const cap = document.createElement("div"); cap.className = "cap";
  cap.textContent = w ? w.name : "LoL'ün kendi arka planı";
  card.appendChild(cap);
  if (on) { const tag = document.createElement("i"); tag.className = "tag"; tag.textContent = "Seçili"; card.appendChild(tag); }
  card.addEventListener("click", () => act("wallpaper_set", { name: w ? w.name : null }).then(() => { wallsKey = ""; setTimeout(loadWalls, 300); loadTiles(); }));
  if (w) {
    const del = document.createElement("div");
    del.className = "del"; del.title = "Sil"; del.innerHTML = ICON_TRASH;
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      if (del.dataset.armed && Date.now() - Number(del.dataset.armed) < 3000) {
        act("wallpaper_delete", { name: w.name }).then(() => { wallsKey = ""; setTimeout(loadWalls, 300); });
      } else { del.dataset.armed = Date.now(); showToast("Silmek için tekrar bas"); }
    });
    card.appendChild(del);
  }
  return card;
}
async function loadWalls() {
  let data;
  try { data = await api("/api/wallpapers"); } catch (e) { return; }
  const key = JSON.stringify(data);
  if (key === wallsKey) return;
  wallsKey = key;
  const list = $("walls");
  list.innerHTML = "";
  list.appendChild(wallCard(null, data));
  data.files.forEach((w) => list.appendChild(wallCard(w, data)));
}
setInterval(() => { if ($("page-wallpaper").classList.contains("active")) loadWalls(); }, 4000);
const wallDrop = $("wall-drop");
["dragenter", "dragover"].forEach((t) => wallDrop.addEventListener(t, (e) => { e.preventDefault(); wallDrop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => wallDrop.addEventListener(t, (e) => { e.preventDefault(); wallDrop.classList.remove("over"); }));
wallDrop.addEventListener("drop", async (e) => {
  for (const file of e.dataTransfer.files) {
    showToast(`${file.name} ekleniyor…`);
    try {
      const r = await fetch(`/api/wallpapers/upload?name=${encodeURIComponent(file.name)}`,
        { method: "POST", headers: { "X-Lust-Hub": TOKEN }, body: file });
      const out = await r.json();
      if (out.message) showToast(out.message);
    } catch (err) { showToast("Eklenemedi"); }
  }
  wallsKey = ""; loadWalls();
});

// ---- fonts ----
let fontsKey = "";
function fontCard(f) {
  const card = document.createElement("div");
  card.className = "mapc fontc" + (f.selected ? " on" : "");
  const shot = document.createElement("div");
  shot.className = "shot";
  shot.textContent = f.lust ? "가 Aa" : "Aa";
  card.appendChild(shot);
  const b = document.createElement("b"); b.textContent = f.name; card.appendChild(b);
  const span = document.createElement("span");
  span.textContent = f.description || (f.lust ? "Lust'ın varsayılan fontu" : f.id ? "Mod" : "League'in kendi fontu");
  card.appendChild(span);
  if (f.selected) { const tag = document.createElement("i"); tag.className = "tag"; tag.textContent = "Seçili"; card.appendChild(tag); }
  if (f.lust) { const tag = document.createElement("i"); tag.className = "tag lust"; tag.textContent = "Lust"; card.appendChild(tag); }
  card.addEventListener("click", () => act("font_select", { id: f.id || null }).then(() => setTimeout(loadFonts, 300)));
  if (f.id) {
    const del = document.createElement("div");
    del.className = "del"; del.title = "Sil"; del.innerHTML = ICON_TRASH;
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      if (del.dataset.armed && Date.now() - Number(del.dataset.armed) < 3000) {
        act("font_delete", { id: f.id }).then(() => setTimeout(loadFonts, 300));
      } else { del.dataset.armed = Date.now(); showToast("Silmek için tekrar bas"); }
    });
    card.appendChild(del);
  }
  return card;
}
async function loadFonts() {
  let data;
  try { data = await api("/api/fonts"); } catch (e) { return; }
  const key = JSON.stringify(data);
  if (key === fontsKey) return;
  fontsKey = key;
  const list = $("fonts");
  list.innerHTML = "";
  data.installed.filter((f) => f.lust).forEach((f) => list.appendChild(fontCard(f)));
  list.appendChild(fontCard({ id: "", name: "League", selected: !data.selected }));
  data.installed.filter((f) => !f.lust).forEach((f) => list.appendChild(fontCard(f)));
}
setInterval(() => { if ($("page-fonts").classList.contains("active")) loadFonts(); }, 3000);
const fontDrop = $("font-drop");
["dragenter", "dragover"].forEach((t) => fontDrop.addEventListener(t, (e) => { e.preventDefault(); fontDrop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => fontDrop.addEventListener(t, (e) => { e.preventDefault(); fontDrop.classList.remove("over"); }));
fontDrop.addEventListener("drop", async (e) => {
  for (const file of e.dataTransfer.files) {
    showToast(`${file.name} ekleniyor…`);
    try {
      const r = await fetch(`/api/fonts/upload?name=${encodeURIComponent(file.name)}`,
        { method: "POST", headers: { "X-Lust-Hub": TOKEN }, body: file });
      const out = await r.json();
      if (out.message) showToast(out.message);
    } catch (err) { showToast("Eklenemedi"); }
  }
  fontsKey = ""; loadFonts();
});

// ---- custom skins ----
const ICON_SHIRT = `__shirt__`;
const CHAMP_ICON = (id) => `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/${id}.png`;
let skinsData = null, skinsKey = "";
// [badge, tooltip] for each patch status (pengu/communication/lust_custom_skins.status)
const SKIN_STATUS = {
  ok: ["Bu yamada çalıştı", "Bu League sürümünde oyunu sorunsuz açtı"],
  untested: ["League güncellendi, denenmedi", "Eski yamada çalışıyordu; yeni yamada henüz oynanmadı"],
  old: ["Eski olabilir", "Bu yamadan aylar önce paketlenmiş; oyunu çökertebilir"],
  crashed: ["Bu yamada oyunu çökertti", "Lust bu skini kapattı. Skinin yeni yama için güncellenmiş sürümünü bulup klasöre ekle"],
};
function skinRow(s, champions) {
  const row = document.createElement("div");
  row.className = "skr" + (s.enabled ? " on" : "");
  const ic = document.createElement("div");
  ic.className = "ic"; ic.innerHTML = ICON_SHIRT;
  if (s.championId) { ic.classList.add("img"); ic.style.backgroundImage = `url("${CHAMP_ICON(s.championId)}")`; }
  const tx = document.createElement("div"); tx.className = "tx";
  const b = document.createElement("b"); b.textContent = s.title; b.title = s.name;
  const span = document.createElement("span");
  if (s.broken) { span.className = "bad"; span.textContent = "Bu dosya okunamıyor"; }
  else span.textContent = s.name;
  tx.append(b, span);
  const st = SKIN_STATUS[s.status];
  if (st && !s.broken) {
    const tag = document.createElement("div");
    tag.className = `st ${s.status}`;
    tag.textContent = st[0];
    tag.title = st[1] + (s.made ? ` (paketlenme: ${new Date(s.made * 1000).toLocaleDateString("tr-TR")})` : "");
    if (s.status !== "ok") {
      const a = document.createElement("a");
      a.textContent = "Güncelini ara";
      a.addEventListener("click", () => act("skin_search", { name: s.name }));
      tag.appendChild(a);
    }
    tx.appendChild(tag);
    if (s.status === "crashed") row.classList.add("crashed");
  }
  if (!s.broken) {
    const pick = document.createElement("select");
    pick.className = s.championId ? "" : "need";
    const none = document.createElement("option");
    none.value = "0"; none.textContent = "Şampiyonu seç";
    pick.appendChild(none);
    champions.forEach((c) => {
      const o = document.createElement("option");
      o.value = String(c.id); o.textContent = c.name; o.selected = c.id === s.championId;
      pick.appendChild(o);
    });
    if (s.championId && !champions.some((c) => c.id === s.championId)) {
      const o = document.createElement("option");
      o.value = String(s.championId); o.textContent = s.champion || `#${s.championId}`; o.selected = true;
      pick.appendChild(o);
    }
    pick.addEventListener("change", () => act("skin_champion", { name: s.name, championId: Number(pick.value) }).then(() => setTimeout(loadSkins, 250)));
    tx.appendChild(pick);
  }
  const sw = document.createElement("div");
  sw.className = "tick" + (s.enabled ? " on" : "") + (s.championId ? "" : " lock");
  sw.innerHTML = ICON.check;
  sw.title = s.championId ? (s.enabled ? "Seçili: oyunda bu skin" : "Seç") : "Önce şampiyonu seç";
  sw.addEventListener("click", () => {
    if (!s.championId) { showToast("Önce şampiyonu seç"); return; }
    act("skin_toggle", { name: s.name, enabled: !s.enabled }).then(() => setTimeout(loadSkins, 250));
  });
  const del = document.createElement("div");
  del.className = "del"; del.title = "Sil"; del.innerHTML = ICON_TRASH;
  del.addEventListener("click", () => {
    if (del.dataset.armed && Date.now() - Number(del.dataset.armed) < 3000) {
      act("skin_delete", { name: s.name }).then(() => setTimeout(loadSkins, 250));
    } else { del.dataset.armed = Date.now(); showToast("Silmek için tekrar bas"); }
  });
  row.append(sw, ic, tx, del);
  return row;
}
function drawSkins() {
  if (!skinsData) return;
  const find = $("sk-find").value.trim().toLocaleLowerCase("tr");
  const list = $("skins");
  list.innerHTML = "";
  const on = skinsData.skins.filter((s) => s.enabled).length;
  $("sk-count").textContent = skinsData.skins.length ? `${skinsData.skins.length} custom skin · ${on} açık` : "Custom skinler";
  $("sk-off").classList.toggle("show", !skinsData.on);
  const shown = skinsData.skins.filter((s) => !find || `${s.title} ${s.name} ${s.champion}`.toLocaleLowerCase("tr").includes(find));
  if (!skinsData.skins.length) {
    const e = document.createElement("div"); e.className = "empty";
    e.textContent = "Henüz custom skin yok. Aşağıya bir dosya sürükle ya da klasörü açıp içine kopyala.";
    list.appendChild(e);
  } else if (!shown.length) {
    const e = document.createElement("div"); e.className = "empty"; e.textContent = "Eşleşen skin yok.";
    list.appendChild(e);
  }
  shown.forEach((s) => list.appendChild(skinRow(s, skinsData.champions)));
}
async function loadSkins() {
  let data;
  try { data = await api("/api/skins"); } catch (e) { return; }
  const key = JSON.stringify(data);
  if (key === skinsKey) return;
  skinsKey = key; skinsData = data;
  if (document.activeElement && document.activeElement.tagName === "SELECT" && $("skins").contains(document.activeElement)) return;
  drawSkins();
}
$("sk-find").addEventListener("input", drawSkins);
// Files copied into the folder show up while the page is open
setInterval(() => { if ($("page-skins").classList.contains("active")) loadSkins(); }, 3000);
const skinDrop = $("skin-drop");
["dragenter", "dragover"].forEach((t) => skinDrop.addEventListener(t, (e) => { e.preventDefault(); skinDrop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => skinDrop.addEventListener(t, (e) => { e.preventDefault(); skinDrop.classList.remove("over"); }));
skinDrop.addEventListener("drop", async (e) => {
  for (const file of e.dataTransfer.files) {
    showToast(`${file.name} ekleniyor…`);
    try {
      const r = await fetch(`/api/skins/upload?name=${encodeURIComponent(file.name)}`,
        { method: "POST", headers: { "X-Lust-Hub": TOKEN }, body: file });
      const out = await r.json();
      if (out.message) showToast(out.message);
    } catch (err) { showToast("Eklenemedi"); }
  }
  skinsKey = ""; loadSkins();
});

// ---- profile background ----
let profile = null, pfChampion = 0, pfSkins = [];
const SPLASH = (s) => s && (s.splash || s.tile) ? `url("${s.splash || s.tile}")` : "";
function drawProfileHero() {
  const s = profile.skin;
  $("pf-hero").style.backgroundImage = SPLASH(s);
  $("pf-name").textContent = s ? s.name : (profile.current ? `Skin #${profile.current}` : "Henüz seçilmedi");
  const chip = $("pf-chip");
  chip.className = "pf-chip" + (profile.pending ? " wait" : profile.online ? " on" : "");
  chip.textContent = profile.pending ? "LoL açılınca profiline konacak" : profile.online ? "Şu an profilinde" : "LoL kapalı: seçtiğin, açılınca konur";
}
function drawChampions() {
  const find = $("pf-find").value.trim().toLocaleLowerCase("tr");
  const list = $("pf-champs");
  list.innerHTML = "";
  profile.champions.filter((c) => !find || c.name.toLocaleLowerCase("tr").includes(find)).forEach((c) => {
    const el = document.createElement("div");
    el.className = "chp" + (c.id === pfChampion ? " sel" : "");
    const i = document.createElement("i"); i.style.backgroundImage = `url("${CHAMP_ICON(c.id)}")`;
    const n = document.createElement("span"); n.textContent = c.name;
    el.append(i, n);
    el.addEventListener("click", () => pickChampion(c.id));
    list.appendChild(el);
  });
  if (!list.children.length) {
    const e = document.createElement("div"); e.className = "empty";
    e.textContent = profile.champions.length ? "Eşleşen şampiyon yok." : "Şampiyon listesi alınamadı: internet bağlantısını kontrol et.";
    list.appendChild(e);
  }
}
function drawProfileSkins() {
  const champ = profile.champions.find((c) => c.id === pfChampion);
  $("pf-skins-title").textContent = champ ? `${champ.name} · ${pfSkins.length} skin` : "Skinler";
  const list = $("pf-skins");
  list.innerHTML = "";
  pfSkins.forEach((s) => {
    const card = document.createElement("div");
    card.className = "psk" + (s.id === profile.current ? " on" : "");
    const art = document.createElement("div"); art.className = "art";
    if (s.tile || s.splash) art.style.backgroundImage = `url("${s.tile || s.splash}")`;
    const tag = document.createElement("div"); tag.className = "tag"; tag.textContent = "Profilinde";
    const use = document.createElement("div"); use.className = "use"; use.textContent = "Arka plan yap";
    const b = document.createElement("b"); b.textContent = s.name; b.title = s.name;
    card.append(art, tag, use, b);
    card.addEventListener("click", () => {
      if (s.id === profile.current) return;
      profile.current = s.id; profile.skin = s; drawProfileHero(); drawProfileSkins();
      act("profile_background", { skinId: s.id }).then(() => setTimeout(loadProfile, 600));
    });
    list.appendChild(card);
  });
  if (champ && !pfSkins.length) {
    const e = document.createElement("div"); e.className = "empty"; e.textContent = "Skinler yükleniyor…";
    list.appendChild(e);
  }
}
async function pickChampion(id) {
  pfChampion = id; pfSkins = [];
  drawChampions(); drawProfileSkins();
  let data;
  try { data = await api(`/api/profile/skins?champion=${id}`); } catch (e) { return; }
  if (pfChampion !== id) return;
  pfSkins = data.skins || [];
  if (!pfSkins.length) $("pf-skins").innerHTML = '<div class="empty">Bu şampiyonun skinleri alınamadı.</div>';
  else drawProfileSkins();
}
async function loadProfile() {
  let data;
  try { data = await api("/api/profile"); } catch (e) { return; }
  const first = !profile;
  profile = data;
  drawProfileHero();
  if (first || !pfChampion) {
    const own = profile.current ? Math.floor(profile.current / 1000) : 0;
    const start = profile.champions.find((c) => c.id === own) || profile.champions[0];
    drawChampions();
    if (start) pickChampion(start.id);
    const sel = $("pf-champs").querySelector(".sel");
    if (sel) sel.scrollIntoView({ block: "nearest" });
  } else drawProfileSkins();
}
$("pf-find").addEventListener("input", () => profile && drawChampions());

// ---- profile icon ----
const ICON_IMG = (id) => `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/${id}.jpg`;
const IC_PAGE = 180;
let iconData = null, icShown = IC_PAGE;
function drawIconHero() {
  const id = iconData.chosen, ic = iconData.icon;
  const big = $("ic-big");
  big.style.backgroundImage = id ? `url("${ICON_IMG(id)}")` : "";
  big.querySelector("svg") && (big.querySelector("svg").style.display = id ? "none" : "");
  $("ic-hero").style.setProperty("--ic-art", id ? `url("${ICON_IMG(id)}")` : "none");
  $("ic-name").textContent = id ? (ic ? ic.title : `Simge #${id}`) : "Kendi simgen";
  const chip = $("ic-chip");
  chip.className = "ic-chip" + (id ? " on" : "");
  chip.textContent = id ? `#${id} · LoL'de sadece sen görüyorsun` : "Bir simge seç, LoL'de hemen değişir";
  $("ic-reset").hidden = !id;
}
function drawIcons() {
  const find = $("ic-find").value.trim().toLocaleLowerCase("tr");
  const all = iconData.icons.filter((i) => !find || i.title.toLocaleLowerCase("tr").includes(find)
    || String(i.id) === find || (i.year && String(i.year) === find));
  $("ic-count").textContent = find ? `${all.length} simge bulundu` : `${all.length} simge`;
  const list = $("ic-list");
  list.innerHTML = "";
  all.slice(0, icShown).forEach((i) => {
    const el = document.createElement("div");
    el.className = "picon" + (i.id === iconData.chosen ? " on" : "");
    el.style.backgroundImage = `url("${ICON_IMG(i.id)}")`;
    el.title = `${i.title}${i.year ? ` · ${i.year}` : ""}`;
    el.addEventListener("click", () => pickIcon(i.id));
    list.appendChild(el);
  });
  $("ic-more").hidden = all.length <= icShown;
  if (!all.length) {
    const e = document.createElement("div"); e.className = "empty";
    e.textContent = iconData.icons.length ? "Eşleşen simge yok." : "Simge listesi alınamadı: internet bağlantısını kontrol et.";
    list.appendChild(e);
  }
}
function pickIcon(id) {
  if (id === iconData.chosen) return;
  iconData.chosen = id; iconData.icon = iconData.icons.find((i) => i.id === id) || null;
  drawIconHero(); drawIcons();
  act("profile_icon", { iconId: id });
}
async function loadIcons() {
  let data;
  try { data = await api("/api/icon"); } catch (e) { return; }
  iconData = data;
  drawIconHero(); drawIcons();
}
$("ic-find").addEventListener("input", () => { icShown = IC_PAGE; if (iconData) drawIcons(); });
$("ic-more").addEventListener("click", () => { icShown += IC_PAGE * 2; drawIcons(); });
$("ic-reset").addEventListener("click", () => iconData && pickIcon(0));

const ICON_SYNC = `__sync__`, ICON_DOWNLOAD = `__download__`;
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showPage(t.dataset.page)));
document.querySelectorAll("[data-act]").forEach((el) => el.addEventListener("click", () => {
  if (el.classList.contains("live")) return;
  act(el.dataset.act, el.dataset.body ? JSON.parse(el.dataset.body) : {});
}));
document.querySelectorAll("[data-dismiss]").forEach((b) => b.addEventListener("click", () => {
  const card = b.dataset.dismiss, st = state || {};
  dismiss(card, card === "ltk" ? (st.patcher || {}).state : "installed");
  $(card).hidden = true;
}));
document.querySelectorAll(".status-seg button").forEach((b) => b.addEventListener("click", () => act("status", { value: b.dataset.status })));
$("a-quit").addEventListener("click", () => {
  if (Date.now() - quitArmed < 3000) { act("quit"); return; }
  quitArmed = Date.now(); state && render(state); setTimeout(() => state && render(state), 3100);
});
$("v-btn").addEventListener("click", () => act(state && state.update_available ? "update" : "check"));
document.querySelectorAll("#sg-tabs button").forEach((b) => b.addEventListener("click", () => {
  sgGroup = b.dataset.sg;
  document.querySelectorAll("#sg-tabs button").forEach((x) => x.classList.toggle("on", x === b));
  sgKey = "";
  state && drawSettings(state);
}));
// The version panel opens from the pill and closes on a click elsewhere or Escape
function setVpop(open) {
  $("vpop").hidden = !open;
  $("ver-pill").classList.toggle("open", open);
}
$("ver-pill").addEventListener("click", (e) => { e.stopPropagation(); setVpop($("vpop").hidden); });
$("vpop").addEventListener("click", (e) => e.stopPropagation());
document.addEventListener("click", () => setVpop(false));
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!$("vpop").hidden) { setVpop(false); return; }
  if (page !== "home") showPage("home");
});
// Applying restarts Spotify (and stops the music): a second click confirms
function confirmed(button, idle, run) {
  if (button.dataset.armed && Date.now() - Number(button.dataset.armed) < 4000) {
    delete button.dataset.armed; button.textContent = idle; run(); return;
  }
  button.dataset.armed = Date.now();
  button.textContent = "Spotify yeniden başlayacak, onayla";
  setTimeout(() => { if (button.dataset.armed) { delete button.dataset.armed; button.textContent = idle; } }, 4000);
}
$("sp-apply").addEventListener("click", (e) => confirmed(e.currentTarget, "Temayı uygula", () => act("spotify_apply", { theme: choice })));
$("sp-restore").addEventListener("click", (e) => confirmed(e.currentTarget, "Orijinale döndür", () => act("spotify_apply", { theme: "original" })));
const shell = () => window.pywebview && window.pywebview.api;
$("w-min").addEventListener("click", () => shell() && shell().minimize());
$("w-close").addEventListener("click", () => shell() ? shell().close() : window.close());
// Maximize (button or a double click on the title bar), F11 for full screen, edges to resize
const ICON_MAX = `__max__`, ICON_RESTORE = `__restore__`;
function setMode(mode) {
  document.body.classList.toggle("maxed", mode !== "normal");
  $("w-max").innerHTML = mode === "normal" ? ICON_MAX : ICON_RESTORE;
  $("w-max").title = mode === "normal" ? "Büyüt (çift tık)" : "Eski boyutuna dön";
}
async function windowMode(call) {
  if (!shell()) return;
  try { setMode(await shell()[call]()); } catch (e) {}
}
$("w-max").addEventListener("click", () => windowMode("toggle_maximize"));
$("top").addEventListener("dblclick", (e) => {
  if (!e.target.closest("button, .win, .lg, .vpop")) windowMode("toggle_maximize");
});
document.addEventListener("keydown", (e) => {
  if (e.key === "F11") { e.preventDefault(); windowMode("toggle_fullscreen"); }
});
document.querySelectorAll(".rz").forEach((edge) => edge.addEventListener("mousedown", (e) => {
  if (e.button !== 0 || !shell()) return;
  e.preventDefault();
  shell().begin_resize(edge.dataset.edge);
}));
window.addEventListener("pywebviewready", () => windowMode("mode"));
$("back").addEventListener("click", () => showPage("home"));
document.querySelectorAll(".ht").forEach((t) => t.addEventListener("click", () => showPage(t.dataset.go)));
document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => showPage(b.dataset.goto)));
document.addEventListener("contextmenu", (e) => e.preventDefault());
buildThemes();
showPage("home");
async function pollLoop() {
  await poll();
  setTimeout(pollLoop, state && state.resting ? 5000 : 800);
}
pollLoop();
</script>
</body>
</html>
"""


def _svg(path: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


def render(token: str, version: str, themes: list) -> str:
    page = PAGE.replace("__TOKEN__", json.dumps(token)).replace("__VERSION__", version)
    # The big copy gets its own gradient ids: a hidden copy's ids would blank the small one
    page = page.replace("__lolbig__", LOL_MARK.replace("hx-gold", "hx-gold-b").replace("hx-blue", "hx-blue-b"))
    page = page.replace("__lol__", LOL_MARK)
    page = page.replace("__THEMES__", json.dumps(themes, ensure_ascii=False))
    for name, path in ICONS.items():
        page = page.replace(f"__{name}__", _svg(path))
    return page
