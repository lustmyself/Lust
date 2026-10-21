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
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs><linearGradient id="lust-grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#c4b5fd"/><stop offset=".55" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/>
  </linearGradient></defs>
</svg>
<div class="ambient" aria-hidden="true"><div class="amb-art" id="amb-art"></div><i class="blob b1"></i><i class="blob b2"></i></div>
<nav class="rail">
  <div class="tab active" data-page="lol" data-label="LoL">__lol__</div>
  <div class="tab" data-page="spotify" data-label="Spotify">__spotify__</div>
  <div class="tab" data-page="settings" data-label="Ayarlar">__gear__</div>
  <div class="spacer"></div>
  <div class="dot" id="dot" title=""></div>
</nav>
<div class="main">
  <header class="top pywebview-drag-region">
    <h1 id="title">LoL</h1><button class="pill ver-pill" id="ver-pill" title="Sürüm ve yenilikler"><i class="vdot" id="vdot"></i>__VERSION__</button>
    <span class="tip" id="tip">Oyun ayarları LoL istemcisinde, üstteki <b>LUST</b> sekmesinde</span>
    <div class="grow pywebview-drag-region"></div>
    <div class="win" id="w-min" title="Küçült">__min__</div>
    <div class="win x" id="w-close" title="Kapat">__close__</div>
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

  <section class="page active" id="page-lol">
    <div class="hero" id="hero">
      <div class="hero-art" id="h-art"></div>
      <div class="hero-body">
        <small id="h-small">Hoş geldin</small>
        <h2 id="h-title">Lust başlıyor</h2>
        <div class="hero-chips" id="h-chips"></div>
        <div class="hero-cut" id="h-cut" hidden></div>
        <p id="h-sub"></p>
        <div class="bar busy" id="h-bar"><i></i></div>
      </div>
      <div class="hero-last" id="h-last" hidden>
        <small>Son maç</small>
        <b id="hl-champ"></b>
        <span class="hl-result" id="hl-result"></span>
        <span id="hl-meta"></span>
      </div>
    </div>
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
const ICON = { sparkle: `__sparkle__`, plusbox: `__plusbox__`, users: `__users__`, shield: `__shield__`, power: `__power__`,
  sync: `__sync__`, spotify: `__spotify__`, moon: `__moon__`, play: `__play__`, image: `__image__`, wind: `__wind__` };

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
  ["reduce_motion", "look", ICON.wind, "Animasyonları azalt", "Hareketler kapalı", "Hareketler açık"],
  ["backdrop", "look", ICON.image, "Arka plan", "", "", true, [["cinematic", "Sinematik"], ["hextech", "Sade hextech"]]],
];
let sgGroup = "all", sgKey = "";
function settingValue(s, key) {
  if (key === "autostart") return !!s.autostart;
  if (key === "auto_update") return !!s.auto_update;
  if (key === "spotify_auto") return !!(s.spotify || {}).auto;
  const values = s.settings || {};
  const fallback = { skins: true, custom_skins: true, lobby_reveal: true, rose_guard: true, quiet_start: false,
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
function spotifyVisible() { return $("page-spotify").classList.contains("active") && !document.hidden; }
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
  const st = s.settings || {};
  document.body.classList.toggle("bd-hextech", st.backdrop === "hextech");
  document.body.classList.toggle("calm", !!st.reduce_motion);
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
  if (s.prompt) showPage("lol");
}

async function poll() {
  try { render(await api("/api/state")); failures = 0; $("lost").style.display = "none"; }
  catch (e) { if (++failures >= 3) $("lost").style.display = "grid"; }
}
function showPage(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.page === name));
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
  $("title").textContent = name === "lol" ? "LoL" : name === "spotify" ? "Spotify" : "Ayarlar";
  $("tip").hidden = name !== "lol";
}

const ICON_SYNC = `__sync__`, ICON_DOWNLOAD = `__download__`;
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showPage(t.dataset.page)));
document.querySelectorAll("[data-act]").forEach((el) => el.addEventListener("click", () => {
  if (el.classList.contains("live")) return;
  act(el.dataset.act, el.dataset.body ? JSON.parse(el.dataset.body) : {});
}));
document.querySelectorAll("#seg button").forEach((b) => b.addEventListener("click", () => act("status", { value: b.dataset.status })));
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
document.addEventListener("keydown", (e) => { if (e.key === "Escape") setVpop(false); });
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
    page = page.replace("__lol__", LOL_MARK)
    page = page.replace("__THEMES__", json.dumps(themes, ensure_ascii=False))
    for name, path in ICONS.items():
        page = page.replace(f"__{name}__", _svg(path))
    return page
