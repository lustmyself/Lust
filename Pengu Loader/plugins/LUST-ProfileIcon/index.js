/**
 * @name Lust-ProfileIcon
 * @author Lust Team
 * @description Shows the profile icon picked in the Lust hub as your own, on your screen only
 */

// Riot only takes an icon the account owns, so nothing is sent anywhere: the client's data
// binding (what its pages read from the local API, first answers and live updates alike) is
// hooked, and wherever it describes this player the icon id becomes the chosen one. The
// client then draws that icon from its own files. Everyone else sees the real icon.

const LOG_PREFIX = "[Lust-ProfileIcon]";
const STORE_KEY = "lust-profile-icon";
const POLL_MS = 4000;
// Where the client reads the player's own icon from
const WATCHED = ["/lol-summoner/", "/lol-chat/v1/me", "/lol-lobby/", "/lol-hovercard/", "/lol-regalia/"];
const ICON_KEYS = ["profileIconId", "summonerIconId", "icon"];
const MAX_DEPTH = 6;

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
  if (typeof content.puuid === "string" && content.puuid) me.puuid = content.puuid;
  if (content.summonerId != null) me.summonerId = String(content.summonerId);
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

function setIcon(value) {
  const next = Number.isInteger(value) && value >= 0 ? value : 0;
  if (next === iconId) return;
  iconId = next;
  storeSet(next);
  log(next ? `showing icon ${next}` : "showing the account's own icon");
  refresh();
}

async function findMe() {
  for (let tries = 0; tries < 120 && !me.puuid; tries++) {
    try {
      const response = await fetch("/lol-summoner/v1/current-summoner");
      if (response.ok) {
        learn("/lol-summoner/v1/current-summoner", await response.json());
        if (me.puuid) {
          refresh();
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
  findMe();
  followHub();
}
