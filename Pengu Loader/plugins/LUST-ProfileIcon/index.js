/**
 * @name Lust-ProfileIcon
 * @author Lust Team
 * @description Shows the profile icon picked in the Lust hub as your own, on your screen only
 */

// Riot only takes an icon the account owns, so nothing is sent anywhere: the client's data
// binding (what its pages read from the local API, first answers and live updates alike) is
// hooked, and wherever it describes this player the icon id becomes the chosen one. The
// client then draws that icon from its own files. Everyone else sees the real icon.
// The profile page and the lobby draw their crest (regalia) from their own requests, so
// there the crest's icon gets a stylesheet with the chosen icon instead.

const LOG_PREFIX = "[Lust-ProfileIcon]";
const STORE_KEY = "lust-profile-icon";
const POLL_MS = 4000;
// Where the client reads the player's own icon from
const WATCHED = ["/lol-summoner/", "/lol-chat/v1/me", "/lol-lobby/", "/lol-hovercard/", "/lol-regalia/"];
const ICON_KEYS = ["profileIconId", "summonerIconId", "icon"];
const MAX_DEPTH = 6;
// Crests that show a player: the profile page, lobby slots, hover cards, the identity editor
const REGALIA_HOSTS = [
  "lol-regalia-profile-v2-element",
  "lol-regalia-parties-v2-element",
  "lol-regalia-hovercard-v2-element",
  "lol-regalia-identity-customizer-element",
  "lol-regalia-crest-v2-element",
];
const STYLE_ID = "lust-profile-icon";
const RETRY_MS = [0, 150, 500, 1500, 4000];

let iconId = 0;
const me = { puuid: "", summonerId: "" };
// Each hooked cache, with the last real content of the endpoints about this player, so a new
// choice can be shown at once by passing that content through again
const caches = new Map();

function log(...args) {
  console.log(LOG_PREFIX, ...args);
}

function storeGet() {
  try {
    const value = window.DataStore?.get(STORE_KEY);
    return Number.isInteger(value) && value >= 0 ? value : 0;
  } catch {
    return 0;
  }
}

function storeSet(value) {
  try {
    window.DataStore?.set(STORE_KEY, value);
  } catch {
    // only a convenience for the next start
  }
}

function watched(endpoint) {
  return typeof endpoint === "string" && WATCHED.some((prefix) => endpoint.startsWith(prefix));
}

function isMine(obj) {
  if (me.puuid && obj.puuid === me.puuid) return true;
  return !!me.summonerId && obj.summonerId != null && String(obj.summonerId) === me.summonerId;
}

function learn(endpoint, content) {
  if (endpoint !== "/lol-summoner/v1/current-summoner" || !content || typeof content !== "object") return;
  const before = me.puuid + "/" + me.summonerId;
  if (typeof content.puuid === "string" && content.puuid) me.puuid = content.puuid;
  if (content.summonerId != null) me.summonerId = String(content.summonerId);
  if (before !== me.puuid + "/" + me.summonerId) setTimeout(restyleHosts, 0);
}

// The content with this player's icon swapped; the same object when nothing is about them.
// result.mine tells whether anything in it was about them (worth keeping for a later change).
function rewrite(value, result, depth = 0) {
  if (!value || typeof value !== "object" || depth > MAX_DEPTH) return value;
  if (Array.isArray(value)) {
    let copy = null;
    value.forEach((item, i) => {
      const next = rewrite(item, result, depth + 1);
      if (next !== item) {
        copy = copy || value.slice();
        copy[i] = next;
      }
    });
    return copy || value;
  }
  let copy = null;
  if (isMine(value)) {
    result.mine = true;
    if (iconId > 0) {
      for (const key of ICON_KEYS) {
        if (typeof value[key] === "number" && value[key] !== iconId) {
          copy = copy || { ...value };
          copy[key] = iconId;
        }
      }
    }
  }
  for (const key of Object.keys(value)) {
    const item = value[key];
    if (!item || typeof item !== "object") continue;
    const next = rewrite(item, result, depth + 1);
    if (next !== item) {
      copy = copy || { ...value };
      copy[key] = next;
    }
  }
  return copy || value;
}

function hookCache(cache) {
  if (!cache || caches.has(cache) || typeof cache._triggerResourceObservers !== "function") return;
  const kept = new Map();
  caches.set(cache, kept);
  const original = cache._triggerResourceObservers;
  cache._triggerResourceObservers = function (endpoint, content, error) {
    if (watched(endpoint) && content && typeof content === "object") {
      try {
        learn(endpoint, content);
        const result = { mine: false };
        const next = rewrite(content, result);
        if (result.mine) kept.set(endpoint, content);
        else kept.delete(endpoint);
        content = next;
      } catch (e) {
        log("rewrite failed", e);
      }
    }
    return original.apply(this, [endpoint, content, error]);
  };
}

// Show a new choice everywhere the client already drew the player
function refresh() {
  for (const [cache, kept] of caches) {
    for (const [endpoint, content] of kept) {
      try {
        cache._triggerResourceObservers(endpoint, content, undefined);
      } catch (e) {
        log("refresh failed", endpoint, e);
      }
    }
  }
}

// ---- crests drawn outside the data binding ----

const hosts = new Set();

function hostIsMine(host) {
  for (const name of ["puuid", "voice-puuid"]) {
    const value = host.getAttribute(name);
    if (value && me.puuid && value === me.puuid) return true;
  }
  const summonerId = host.getAttribute("summoner-id");
  return !!(summonerId && me.summonerId && summonerId === me.summonerId);
}

function crestRoots(host) {
  const roots = [];
  if (host.shadowRoot) {
    roots.push(host.shadowRoot);
    host.shadowRoot.querySelectorAll("lol-regalia-crest-v2-element").forEach((crest) => {
      if (crest.shadowRoot) roots.push(crest.shadowRoot);
    });
  }
  return roots;
}

function hasIds(host) {
  return ["puuid", "voice-puuid", "summoner-id"].some((name) => host.getAttribute(name));
}

function styleHost(host) {
  // A crest inside a profile or lobby element belongs to that element, which styles it
  if (!hasIds(host)) return;
  const show = iconId > 0 && hostIsMine(host);
  for (const root of crestRoots(host)) {
    let style = root.getElementById ? root.getElementById(STYLE_ID) : root.querySelector(`#${STYLE_ID}`);
    if (!show) {
      if (style) style.remove();
      continue;
    }
    if (!style) {
      style = document.createElement("style");
      style.id = STYLE_ID;
      root.appendChild(style);
    }
    const url = `/lol-game-data/assets/v1/profile-icons/${iconId}.jpg`;
    const css = `.lol-regalia-summoner-icon{background-image:url("${url}")!important}`;
    if (style.textContent !== css) style.textContent = css;
  }
}

function watchHost(host) {
  if (hosts.has(host)) return;
  hosts.add(host);
  // Its shadow roots and ids arrive a little after the element itself
  RETRY_MS.forEach((ms) => setTimeout(() => styleHost(host), ms));
  new MutationObserver(() => styleHost(host))
    .observe(host, { attributes: true, attributeFilter: ["puuid", "voice-puuid", "summoner-id"] });
}

function restyleHosts() {
  for (const host of hosts) {
    if (!host.isConnected) hosts.delete(host);
    else styleHost(host);
  }
}

// Every crest host as it appears, in the page and inside other elements' shadow roots
const observedRoots = new WeakSet();
function scan(root) {
  if (!root || observedRoots.has(root)) return;
  observedRoots.add(root);
  domObserver.observe(root, { childList: true, subtree: true });
  root.querySelectorAll("*").forEach(visit);
}
function visit(element) {
  if (REGALIA_HOSTS.some((selector) => element.matches(selector))) watchHost(element);
  if (element.shadowRoot) scan(element.shadowRoot);
}
const domObserver = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      visit(node);
      node.querySelectorAll("*").forEach(visit);
    });
  }
});

function setIcon(value) {
  const next = Number.isInteger(value) && value >= 0 ? value : 0;
  if (next === iconId) return;
  iconId = next;
  storeSet(next);
  log(next ? `showing icon ${next}` : "showing the account's own icon");
  refresh();
  restyleHosts();
}

async function findMe() {
  for (let tries = 0; tries < 120 && !me.puuid; tries++) {
    try {
      const response = await fetch("/lol-summoner/v1/current-summoner");
      if (response.ok) {
        learn("/lol-summoner/v1/current-summoner", await response.json());
        if (me.puuid) {
          refresh();
          restyleHosts();
          return;
        }
      }
    } catch {
      // the client is still starting
    }
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
}

async function followHub() {
  let bridge = null;
  for (let waited = 0; !bridge && waited < 120000; waited += 250) {
    bridge = window.__lustBridge || null;
    if (!bridge) await new Promise((resolve) => setTimeout(resolve, 250));
  }
  if (!bridge) {
    log("Lust's bridge is not there; keeping the last choice");
    return;
  }
  bridge.subscribe("lust-profile-icon", (message) => setIcon(message && message.iconId));
  const ask = () => {
    if (bridge.ready) bridge.send({ type: "lust-profile-icon" });
  };
  bridge.onReady(ask);
  window.addEventListener("focus", ask);
  setInterval(ask, POLL_MS);
}

export function init(context) {
  iconId = storeGet();
  context.rcp.postInit("rcp-fe-common-libs", async (api) => {
    const originalGetDataBinding = api.getDataBinding;
    api.getDataBinding = async function () {
      const dataBinding = await originalGetDataBinding.apply(this, arguments);
      const hooked = function () {
        const bound = dataBinding.apply(this, arguments);
        hookCache(bound && bound.cache);
        return bound;
      };
      hooked.bindTo = function () {
        const result = dataBinding.bindTo.apply(this, arguments);
        result.dataBinding = hooked;
        return result;
      };
      return hooked;
    };
  });
}

export function load() {
  scan(document);
  findMe();
  followHub();
}
