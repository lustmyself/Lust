/**
* @name Lust Theme
* @author Lust
* @description Lust theme for Pengu Loader
* @link https://github.com/lustmyself/Lust
* @Nyan Meow~~~
*/
const CONSOLE_STYLE = {
  prefix: "%c Lust ",
  css: "color: #ffffff; background-color: #8b5cf6"
};
const createLogger = (type) => {
  return (message, ...args) => {
    console[type](CONSOLE_STYLE.prefix + "%c " + message, CONSOLE_STYLE.css, "", ...args);
  };
};
const log = createLogger("log");
const warn = createLogger("warn");
const error = createLogger("error");
window.log = log;
window.warn = warn;
window.error = error;

const DATA_FILE_PATH = "./data/LustData.json";
class FSDataMgr {
  cache = {};
  fsContext = null;
  storageMode = "datastore";
  pendingPersist = null;
  persistAgain = false;
  /**
   * Persist the in-memory cache to ./data/LustData.json via context.fs.
   * Writes synchronously (awaited) to guarantee data is saved.
   */
  async persistToFile() {
    if (this.storageMode !== "fs" || !this.fsContext)
      return false;
    try {
      const json = JSON.stringify(this.cache, null, 2);
      const success = await this.fsContext.fs.write(DATA_FILE_PATH, json, { append: false });
      if (!success) {
        error("context.fs.write returned false — data may not be persisted");
      }
      return success;
    } catch (err) {
      error("Failed to persist LustData to file", err);
      return false;
    }
  }
  /**
   * Queue a persist operation; coalesces multiple rapid writes into one.
   */
  queuePersist() {
    if (this.pendingPersist) {
      this.persistAgain = true;
      return this.pendingPersist;
    }
    this.pendingPersist = (async () => {
      let success = true;
      do {
        this.persistAgain = false;
        success = await this.persistToFile();
      } while (this.persistAgain);
      return success;
    })().finally(() => {
      this.pendingPersist = null;
    });
    return this.pendingPersist;
  }
}
class DatastoreMgr {
  /**
   * Gets a value from the Pengu DataStore.
   */
  get(key, fallback = null) {
    const data = window.DataStore.get("LustTheme", {});
    return data.hasOwnProperty(key) ? data[key] : fallback;
  }
  /**
   * Sets a value in the Pengu DataStore.
   */
  set(key, value) {
    const data = window.DataStore.get("LustTheme", {});
    data[key] = value;
    window.DataStore.set("LustTheme", data);
    return data.hasOwnProperty(key);
  }
  /**
   * Checks if a key exists in the Pengu DataStore.
   */
  has(key) {
    const data = window.DataStore.get("LustTheme", {});
    return data.hasOwnProperty(key);
  }
  /**
   * Removes a key from the Pengu DataStore.
   */
  remove(key) {
    const data = window.DataStore.get("LustTheme", {});
    if (data.hasOwnProperty(key)) {
      delete data[key];
      window.DataStore.set("LustTheme", data);
      return true;
    }
    return false;
  }
}
class LustDataClass extends FSDataMgr {
  initialized = false;
  initPromiseResolve = null;
  /** A promise that resolves once LustData has been fully initialized. */
  ready;
  datastoreMgr = new DatastoreMgr();
  constructor() {
    super();
    this.ready = new Promise((resolve) => {
      this.initPromiseResolve = resolve;
    });
  }
  /**
   * Initialize LustData.
   * If context.fs is available, migrate or load data from ./data/LustData.json.
   * Otherwise fall back to Pengu DataStore.
   *
   * **Must be called (and awaited) before any other code uses LustData.**
   */
  async init(context) {
    if (!context || !context.fs) {
      log("context.fs not available — using DataStore mode");
      this.storageMode = "datastore";
      this.initialized = true;
      this.initPromiseResolve?.();
      return;
    }
    this.fsContext = context;
    try {
      await context.fs.mkdir("./data");
      const raw = await context.fs.read(DATA_FILE_PATH);
      if (raw && raw.trim().length > 0) {
        try {
          this.cache = JSON.parse(raw);
          log("LustData loaded from file (fs mode)");
        } catch (parseErr) {
          error("Failed to parse LustData.json, migrating from DataStore", parseErr);
          this.cache = { ...window.DataStore.get("LustTheme", {}) };
        }
      } else {
        const datastoreData = window.DataStore.get("LustTheme", {});
        if (Object.keys(datastoreData).length > 0) {
          this.cache = { ...datastoreData };
          log("Migrated LustData from DataStore to file (fs mode)");
        } else {
          this.cache = {};
          log("Created new LustData file (fs mode)");
        }
      }
      this.storageMode = "fs";
      this.initialized = true;
      await this.persistToFile();
    } catch (err) {
      error("Failed to init LustData in fs mode, falling back to DataStore", err);
      this.storageMode = "datastore";
      this.initialized = true;
    }
    this.initPromiseResolve?.();
  }
  /**
   * Gets a value from the datastore.
   * @param key The key to retrieve.
   * @param fallback The fallback value if the key doesn't exist.
   * @returns The value associated with the key or the fallback.
   */
  get(key, fallback = null) {
    if (!this.initialized) {
      error(`LustData.get("${key}") called before LustData.init()`);
      return fallback;
    }
    if (this.storageMode === "fs") {
      return this.cache.hasOwnProperty(key) ? this.cache[key] : fallback;
    }
    return this.datastoreMgr.get(key, fallback);
  }
  /**
   * Sets a value in the datastore.
   * In fs mode, updates in-memory cache and persists to file immediately.
   * @param key The key to set.
   * @param value The value to associate with the key.
   * @returns True if the key was set successfully, false otherwise.
   */
  set(key, value) {
    if (!this.initialized) {
      error(`LustData.set("${key}") called before LustData.init()`);
      return false;
    }
    if (this.storageMode === "fs") {
      this.cache[key] = value;
      this.queuePersist();
      return true;
    }
    return this.datastoreMgr.set(key, value);
  }
  /**
   * Checks if a key exists in the datastore.
   * @param key The key to check for existence.
   * @returns True if the key exists, false otherwise.
   */
  has(key) {
    if (!this.initialized) {
      error(`LustData.has("${key}") called before LustData.init()`);
      return false;
    }
    if (this.storageMode === "fs") {
      return this.cache.hasOwnProperty(key);
    }
    return this.datastoreMgr.has(key);
  }
  /**
   * Removes a key from the datastore.
   * @param key The key to remove.
   * @returns True if the key was removed, false otherwise.
   */
  remove(key) {
    if (!this.initialized) {
      error(`LustData.remove("${key}") called before LustData.init()`);
      return false;
    }
    if (this.storageMode === "fs") {
      if (this.cache.hasOwnProperty(key)) {
        delete this.cache[key];
        this.queuePersist();
        return true;
      }
      return false;
    }
    return this.datastoreMgr.remove(key);
  }
  /**
   * Restores the default values of the theme in the datastore.
   */
  restoreDefaults() {
    if (this.storageMode === "fs") {
      this.cache = {};
      this.queuePersist();
    } else {
      window.DataStore.set("LustTheme", {});
    }
    window.reloadClient();
  }
  /**
   * Returns the full data object (useful for backup/restore).
   */
  getAll() {
    if (this.storageMode === "fs") {
      return { ...this.cache };
    }
    return window.DataStore.get("LustTheme", {});
  }
  /**
   * Replaces all data at once (useful for restore from backup).
   * @param data The full data object to set.
   */
  setAll(data) {
    if (this.storageMode === "fs") {
      this.cache = { ...data };
      this.queuePersist();
    } else {
      window.DataStore.set("LustTheme", data);
    }
  }
  /** Returns the current storage mode. */
  getStorageMode() {
    return this.storageMode;
  }
  /** Force an immediate flush of cache to file (fs mode only). */
  async flush() {
    await this.queuePersist();
  }
}
const LustData$1 = new LustDataClass();
window.LustData = LustData$1;

let cdnServer = (await import(`//plugins/${getThemeName()}/config/cdnServer.js`)).default;
async function cdnImport(url, errorMsg) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5e3);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (res.status === 200) {
      const serverModule = await import(url);
      return serverModule;
    } else {
      throw new Error();
    }
  } catch (err) {
    clearTimeout(timeoutId);
    error(errorMsg, err);
    window.Toast.error(errorMsg);
  }
}
log(cdnServer["cdn-url"]);
async function initThemeDataCdn() {
  if (LustData.get("Dev-mode")) {
    `//plugins/${getThemeName()}/lust-theme-data/cdninit.js`;
    await cdnImport(`//plugins/${getThemeName()}/lust-theme-data/index.js`, "Failed to load local data");
  } else {
    await cdnImport(`${cdnServer["cdn-url"]}lust-theme-data@${cdnServer["version"]}/index.js`, "Failed to load CDN data");
  }
}

var cachedThemeName = null;
function getThemeNameFromStack() {
  const error = new Error();
  const stackTrace = error.stack;
  const scriptPath = stackTrace?.match(/(?:http|https):\/\/plugins\/[^\s)]+\.js/g)?.find((url) => !url.includes("/@/"));
  if (!scriptPath)
    return null;
  const scopedMatch = scriptPath.match(/\/\/plugins\/(@[^/]+\/[^/?#]+)\//);
  if (scopedMatch)
    return scopedMatch[1];
  const unscopedMatch = scriptPath.match(/\/\/plugins\/([^/?#]+)\//);
  return unscopedMatch ? unscopedMatch[1] : null;
}
function initThemeName(context) {
  if (cachedThemeName)
    return;
  const folderName = context?.meta?.name;
  if (folderName && typeof Pengu !== "undefined" && Array.isArray(Pengu.plugins)) {
    const normalized = Pengu.plugins.map((p) => p.replace(/\\/g, "/"));
    const match = normalized.find((entry) => {
      const segments = entry.split("/");
      const pluginFolder = segments.length >= 2 ? segments[segments.length - 2] : null;
      return pluginFolder === folderName;
    });
    if (match) {
      const lastSlash = match.lastIndexOf("/");
      cachedThemeName = lastSlash > 0 ? match.substring(0, lastSlash) : folderName;
      return;
    }
  }
  cachedThemeName = getThemeNameFromStack();
}
function getThemeName() {
  if (cachedThemeName)
    return cachedThemeName;
  cachedThemeName = getThemeNameFromStack();
  return cachedThemeName;
}
window.getThemeName = getThemeName;
window.cdnImport = cdnImport;

async function importLocale(langCode) {
  const module = await import(`//plugins/${getThemeName()}/locales/${langCode}.js`);
  return module.default;
}
function getClientLocale() {
  const lang = document.querySelector("html")?.lang;
  return lang;
}
function getThemeLocale() {
  const selectedLang = LustData$1.get("Theme-language", "client");
  if (selectedLang && selectedLang !== "client")
    return selectedLang;
  const lustLanguage = window.LustI18n && window.LustI18n.language;
  if (lustLanguage) {
    const locales = { tr: "tr-TR", ru: "ru-RU", vi: "vi-VN", zh: "zh-CN" };
    return locales[lustLanguage.slice(0, 2)] || "default";
  }
  return getClientLocale();
}
async function haveLocaleFile(langCode) {
  try {
    await importLocale(langCode);
    return true;
  } catch {
    return false;
  }
}
async function checkTranslationKey(lang, key) {
  let localeModule;
  if (await haveLocaleFile(lang)) {
    localeModule = await importLocale(lang);
    if (!localeModule[key]) {
      warn(`Missing translation for key: ${key} in locale: ${lang}`);
      localeModule = await importLocale("default");
      if (!localeModule[key]) {
        warn(`Missing translation for key: ${key} in default locale.`);
        return key;
      }
    }
  } else
    localeModule = await importLocale("default");
  return localeModule[key];
}
async function getString$1(key) {
  let result = await checkTranslationKey(getThemeLocale(), key);
  return result;
}
window.getString = getString$1;

let datastore_list = (await import(`//plugins/${getThemeName()}/config/datastoreDefault.js`)).default;
class BackupRestoreData {
  async importData(url) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 7e3);
    try {
      const res = await fetch(url, { signal: controller.signal });
      if (res.status === 200) {
        let Data = await import(url);
        return Data.default;
      } else
        throw new Error();
    } catch (err) {
      let errorMsg = "Can't load default datastore from local: ";
      clearTimeout(timeoutId);
      error(errorMsg, err);
      window.Toast.error(errorMsg);
    }
  }
  setDefaultData(list, restore = false) {
    const data = typeof list === "string" ? JSON.parse(list) : list;
    for (const [key, value] of Object.entries(data)) {
      if (!LustData.has(key)) {
        LustData.set(key, value);
        log(`${key} data restored`);
      } else if (LustData.has(key) && restore) {
        LustData.set(key, value);
        log(`${key} data restored`);
      }
    }
  }
  restore = async (force = false) => {
    if (LustData.get("Lust-Plugins")) {
      this.setDefaultData(datastore_list);
    } else if (!LustData.get("Lust-Plugins") || !LustData.has("Lust-Plugins") || force) {
      let restoreData = new Promise((resolve, reject) => {
        this.setDefaultData(datastore_list);
        setTimeout(async () => {
          resolve();
        }, 5e3);
      });
      window.Toast.promise(restoreData, {
        loading: "Restoring default Lust theme data...",
        success: "Restore complete!",
        error: ""
      });
    }
  };
}
const backupRestoreData = new BackupRestoreData();
const restoreDefaultDataStore = backupRestoreData.restore;
const setDefaultData = backupRestoreData.setDefaultData;

class UPLCore {
  constructor(context) {
    this.Context = context;
  }
}
let Core;
function initCore(context) {
  if (Core != void 0) {
    throw new Error("UPL is already initialized!");
  }
  Core = new UPLCore(context);
}
class Once {
  constructor(callback) {
    this._callback = callback;
  }
  trigger() {
    if (this._callback !== void 0) {
      this._callback();
      this._callback = void 0;
    }
  }
}
let _observer;
const _initOnce$3 = new Once(init$4);
const _entriesCreation = [];
const _entriesDeletion = [];
function matches(element, selector) {
  return Element.prototype.matches.call(element, selector);
}
function observerHandleElement(element, isNew) {
  if (isNew) {
    for (const entry of _entriesCreation) {
      if (matches(element, entry.selector)) {
        entry.callback(element);
      }
    }
  } else {
    for (const entry of _entriesDeletion) {
      if (matches(element, entry.selector)) {
        entry.callback(element);
      }
    }
  }
  for (const child of element.children) {
    observerHandleElement(child, isNew);
  }
  if (element.shadowRoot != null) {
    for (const child of element.shadowRoot.children) {
      observerHandleElement(child, isNew);
    }
    if (isNew) {
      _observer.observe(element.shadowRoot, { attributes: false, childList: true, subtree: true });
    }
  }
}
function observerCallback(mutationsList) {
  for (const mutation of mutationsList) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        observerHandleElement(node, true);
      }
    }
    for (const node of mutation.removedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        observerHandleElement(node, false);
      }
    }
  }
}
function init$4() {
  _observer = new MutationObserver(observerCallback);
  _observer.observe(document, { attributes: false, childList: true, subtree: true });
}
function subscribeToElementCreation(selector, callback) {
  _initOnce$3.trigger();
  _entriesCreation.push({ selector, callback });
}
function subscribeToElementDeletion(selector, callback) {
  _initOnce$3.trigger();
  _entriesDeletion.push({ selector, callback });
}
let loadCallbacks = [];
let loadInitialized = false;
let loadedOnce = false;
function subscribeToLoad(callback) {
  if (!loadInitialized) {
    loadInitialized = true;
    subscribeToElementDeletion(".lol-loading-screen-container", () => {
      if (loadedOnce) {
        return;
      }
      loadedOnce = true;
      for (let callback2 of loadCallbacks) {
        callback2();
      }
    });
  }
  loadCallbacks.push(callback);
}
const observer = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  subscribeToElementCreation,
  subscribeToElementDeletion,
  subscribeToLoad
}, Symbol.toStringTag, { value: "Module" }));
let _xhrHookMap = {};
const _initOnce$2 = new Once(init$3);
function hookPre(path, callback) {
  _initOnce$2.trigger();
  var entry = _xhrHookMap[path];
  if (entry === void 0) {
    _xhrHookMap[path] = { pre_callback: callback, post_callback: void 0 };
  } else {
    _xhrHookMap[path].pre_callback = callback;
  }
}
function hookPost(path, callback) {
  _initOnce$2.trigger();
  var entry = _xhrHookMap[path];
  if (entry === void 0) {
    _xhrHookMap[path] = { pre_callback: void 0, post_callback: callback };
  } else {
    _xhrHookMap[path].post_callback = callback;
  }
}
function hookTextPre(path, callback) {
  hookPre(path, (_, body, original) => {
    if (typeof body !== "string") {
      console.error("UPL: Tried to hook text XHR request but body is not a string!");
      return original(body);
    }
    const _original = (newBody) => {
      original(newBody);
    };
    callback(body, _original);
  });
}
function hookTextPost(path, callback) {
  hookPost(path, (request, original) => {
    if (request.responseType !== "" && request.responseType !== "text") {
      console.error("UPL: Tried to hook text XHR request but response is not a string!");
      return original();
    }
    const _original = (response) => {
      if (request.responseText != response) {
        Object.defineProperty(request, "responseText", {
          writable: true,
          value: response
        });
      }
      original();
    };
    callback(this.responseText, _original);
  });
}
const _xhrOriginalOpen = XMLHttpRequest.prototype.open;
function hookedOpen(_, url) {
  var entry = _xhrHookMap[url.toString()];
  if (entry !== void 0) {
    let originalSend = this.send;
    this.send = function(body) {
      if (body instanceof Document) {
        return originalSend.apply(this, [body]);
      }
      if (entry.pre_callback !== void 0) {
        let original = (content) => {
          body = content;
        };
        entry.pre_callback(this, body || null, original);
      }
      if (entry.post_callback !== void 0) {
        let originalOnReadyStateChanged = this.onreadystatechange;
        this.onreadystatechange = function(ev) {
          if (this.readyState === 4 && entry.post_callback !== void 0) {
            let original = () => {
              originalOnReadyStateChanged.apply(this, [ev]);
            };
            entry.post_callback(this, original);
            return;
          }
          return originalOnReadyStateChanged.apply(this, arguments);
        };
      }
      originalSend.apply(this, [body]);
    };
  }
  _xhrOriginalOpen.apply(this, arguments);
}
function init$3() {
  XMLHttpRequest.prototype.open = hookedOpen;
}
const xhr = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  hookPost,
  hookPre,
  hookTextPost,
  hookTextPre
}, Symbol.toStringTag, { value: "Module" }));
let _wsHookMap = {};
const _initOnce$1 = new Once(init$2);
function hook(endpoint, callback) {
  _initOnce$1.trigger();
  _wsHookMap[endpoint] = callback;
}
function hookText(endpoint, callback) {
  hook(endpoint, (content, original) => {
    if (typeof content !== "string") {
      console.error("UPL: Tried to hook text websocket endpoint but content is not a string!");
      return original(content);
    }
    const _original = (newContent) => {
      original(newContent);
    };
    callback(content, _original);
  });
}
function init$2() {
  let context = Core == null ? void 0 : Core.Context;
  if (context == null) {
    throw new Error("UPL is not initialized!");
  }
  context.rcp.postInit("rcp-fe-common-libs", async (api) => {
    let originalGetDataBinding = api.getDataBinding;
    api.getDataBinding = async function(rcp_name) {
      let originalDataBinding = await originalGetDataBinding.apply(this, arguments);
      let hookedDataBinding = function(basePath, socket) {
        let dataBinding = originalDataBinding.apply(this, arguments);
        let cache = dataBinding.cache;
        let originalTriggerObservers = cache._triggerResourceObservers;
        cache._triggerResourceObservers = function(endpoint, content, error) {
          const callback = _wsHookMap[endpoint];
          if (callback == void 0) {
            return originalTriggerObservers.apply(this, [endpoint, content, error]);
          }
          let original = (content2) => {
            originalTriggerObservers.apply(this, [endpoint, content2, error]);
          };
          return callback(content, original);
        };
        return dataBinding;
      };
      hookedDataBinding.bindTo = function(socket) {
        let result = originalDataBinding.bindTo.apply(this, arguments);
        result.dataBinding = hookedDataBinding;
        return result;
      };
      return Promise.resolve(hookedDataBinding);
    };
  });
}
const ws = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  hook,
  hookText
}, Symbol.toStringTag, { value: "Module" }));
const _entriesName = /* @__PURE__ */ new Map();
const _entriesMatching = [];
const _initOnce = new Once(init$1);
function hookComponentMethodByName(className, methodName, callback) {
  _initOnce.trigger();
  var hookEntry = { method: methodName, callback };
  var entry = _entriesName.get(className);
  if (entry === void 0) {
    _entriesName.set(className, { hooks: [hookEntry], mixins: [] });
  } else {
    entry.hooks.push(hookEntry);
  }
}
function hookComponentMethodByMatching(matcher, methodName, callback) {
  _initOnce.trigger();
  var hookEntry = { method: methodName, callback };
  _entriesMatching.push({ matcher, entry: { hooks: [hookEntry], mixins: [] } });
}
function extendClassByName(className, callback) {
  _initOnce.trigger();
  var entry = _entriesName.get(className);
  if (entry === void 0) {
    _entriesName.set(className, { hooks: [], mixins: [callback] });
  } else {
    entry.mixins.push(callback);
  }
}
function extendClassByMatching(matcher, callback) {
  _initOnce.trigger();
  _entriesMatching.push({ matcher, entry: { hooks: [], mixins: [callback] } });
}
function init$1() {
  let context = Core == null ? void 0 : Core.Context;
  if (context == null) {
    throw new Error("UPL is not initialized!");
  }
  context.rcp.postInit("rcp-fe-ember-libs", async (api) => {
    const originalGetEmber = api.getEmber;
    api.getEmber = function(...args) {
      const result = originalGetEmber.apply(this, args);
      result.then((Ember) => {
        const originalExtend = Ember.Component.extend;
        Ember.Component.extend = function(...args2) {
          let result2 = originalExtend.apply(this, arguments);
          const potentialObjects = args2.filter((x) => typeof x === "object");
          for (const obj of potentialObjects) {
            for (const entry of _entriesMatching) {
              if (entry.matcher(obj)) {
                result2 = handleComponent(Ember, entry.entry, result2);
              }
            }
          }
          const classNames = potentialObjects.filter((x) => x.classNames && Array.isArray(x.classNames)).map((x) => x.classNames.join(" "));
          for (const className of classNames) {
            const entry = _entriesName.get(className);
            if (entry === void 0) {
              continue;
            }
            result2 = handleComponent(Ember, entry, result2);
          }
          return result2;
        };
        return Ember;
      });
      return result;
    };
  });
}
function handleComponent(Ember, entry, result) {
  const proto = result.proto();
  if (proto.__UPL_IS_HOOKED) {
    return result;
  }
  proto.__UPL_IS_HOOKED = true;
  for (const mixin of entry.mixins) {
    result = result.extend(mixin(Ember));
  }
  for (const hook2 of entry.hooks) {
    const original = proto[hook2.method];
    proto[hook2.method] = function(...args) {
      const proxyOriginal = (...args2) => {
        if (original != void 0) {
          return original.apply(this, args2);
        }
      };
      return hook2.callback.call(this, Ember, proxyOriginal, ...args);
    };
  }
  return result;
}
const ember = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  extendClassByMatching,
  extendClassByName,
  hookComponentMethodByMatching,
  hookComponentMethodByName
}, Symbol.toStringTag, { value: "Module" }));
const index = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  ember,
  ws,
  xhr
}, Symbol.toStringTag, { value: "Module" }));
function init$5(penguContext) {
  if (penguContext.rcp === void 0 || typeof penguContext.rcp.preInit != "function" || typeof penguContext.rcp.postInit != "function") {
    throw new Error("context is not a valid Pengu Context!");
  }
  initCore(penguContext);
}

const upl = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
    __proto__: null,
    hooks: index,
    init: init$5,
    observer
}, Symbol.toStringTag, { value: 'Module' }));

const structure = [
  {
    "groupName": "Lust",
    "titleKey": "el_title",
    "titleName": "Lust theme",
    "capitalTitleKey": "el_title_capital",
    "capitalTitleName": "LUST THEME",
    "element": [
      {
        "name": "el-theme-settings",
        "title": "el_theme-settings",
        "titleName": "THEME SETTINGS",
        "class": "theme_settings",
        "id": "LustThemeSettings"
      },
      {
        "name": "el-plugins-settings",
        "title": "el_plugins-settings",
        "titleName": "PLUGINS SETTINGS",
        "class": "plugins_settings",
        "id": "LustPluginsSettings"
      },
      {
        "name": "el-backup-restore-settings",
        "title": "el_backup-restore-settings",
        "titleName": "BACKUP & RESTORE",
        "class": "backup_restore_settings",
        "id": "LustBackupRestoreSettings"
      },
      {
        "name": "el-aboutus-settings",
        "title": "el_aboutus-settings",
        "titleName": "ABOUT US",
        "class": "aboutus_settings",
        "id": "LustAboutUsSettings"
      }
    ]
  }
];

function settingsUtils(context, groupDataArray) {
  log("Loaded settings utils");
  context.rcp.postInit("rcp-fe-lol-settings", async (api) => {
    log("Loaded rcp-fe-lol-settings for Lust's settings");
    window.__RCP_SETTINGS_API = api;
    const emberApi = window.__RCP_EMBER_API;
    const ember = await emberApi.getEmber();
    groupDataArray.forEach((groupData) => {
      const newGroup = {
        name: groupData.groupName,
        titleKey: groupData.titleKey,
        capitalTitleKey: groupData.capitalTitleKey,
        categories: []
      };
      const addCategoryToGroup = (name, title) => {
        newGroup.categories.push({
          name,
          titleKey: title,
          routeName: name,
          group: newGroup,
          loginStatus: true,
          requireLogin: false,
          forceDisabled: false,
          computeds: ember.Object.create({
            disabled: false
          }),
          isEnabled: () => true
        });
      };
      groupData.element.forEach((element) => {
        addCategoryToGroup(element.name, element.title);
      });
      api._modalManager._registeredCategoryGroups.splice(1, 0, newGroup);
      api._modalManager._refreshCategoryGroups();
    });
  });
  context.rcp.postInit("rcp-fe-ember-libs", async (api) => {
    log("Loaded rcp-fe-ember-libs for Lust's settings");
    window.__RCP_EMBER_API = api;
    const ember = await api.getEmber();
    const originalExtend = ember.Router.extend;
    ember.Router.extend = function() {
      const result = originalExtend.apply(this, arguments);
      result.map(function() {
        groupDataArray.forEach((groupData) => {
          groupData.element.forEach((element) => {
            this.route(element.name);
          });
        });
      });
      return result;
    };
  });
  context.rcp.postInit("rcp-fe-lol-l10n", async (api) => {
    log("Loaded rcp-fe-lol-l10n for Lust's settings");
    const tra = api.tra();
    const originalGet = tra.__proto__.get;
    tra.__proto__.get = function(key) {
      if (key.startsWith("el_")) {
        for (const groupData of groupDataArray) {
          if (key === groupData.titleKey) {
            return groupData.titleName;
          } else if (key === groupData.capitalTitleKey) {
            return groupData.capitalTitleName;
          }
          for (const element of groupData.element) {
            if (key === element.title) {
              return element.titleName;
            }
          }
        }
      }
      return originalGet.apply(this, [key]);
    };
  });
  context.rcp.postInit("rcp-fe-ember-libs", async (api) => {
    log("Loaded rcp-fe-ember-libs for Lust's settings");
    window.__RCP_EMBER_API = api;
    const ember = await api.getEmber();
    const originalExtend = ember.Router.extend;
    ember.Router.extend = function() {
      const result = originalExtend.apply(this, arguments);
      result.map(function() {
        groupDataArray.forEach((groupData) => {
          groupData.element.forEach((element) => {
            this.route(element.name);
          });
        });
      });
      return result;
    };
    const factory = await api.getEmberApplicationFactory();
    const originalBuilder = factory.factoryDefinitionBuilder;
    factory.factoryDefinitionBuilder = function() {
      const builder = originalBuilder.apply(this, arguments);
      const originalBuild = builder.build;
      builder.build = function() {
        const name = this.getName();
        if (name === "rcp-fe-lol-settings") {
          window.__SETTINGS_OBJECT = this;
          const addTab = (name2, id, tab) => {
            this.addTemplate(
              name2,
              ember.HTMLBars.template({
                id,
                block: JSON.stringify(tab),
                meta: {}
              })
            );
          };
          const createSettingsTab = (className) => ({
            statements: [
              ["open-element", "lol-uikit-scrollable", []],
              ["static-attr", "class", className],
              ["flush-element"],
              ["close-element"]
            ],
            locals: [],
            named: [],
            yields: [],
            blocks: [],
            hasPartials: false
          });
          groupDataArray.forEach((groupData) => {
            groupData.element.forEach((element) => {
              addTab(
                element.name,
                element.id,
                createSettingsTab(element.class)
              );
            });
          });
        }
        return originalBuild.apply(this, arguments);
      };
      return builder;
    };
  });
}

class ui {
  /**
   * @param text Dòng text hiển thị bên dưới icon Loading
   */
  createLoading = (text) => {
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "settings-loading";
    const loadingImage = document.createElement("img");
    loadingImage.classList.add("settings-loading-image");
    const loadingText = this.createLabel(text, "settings-loading-text");
    loadingDiv.appendChild(loadingImage);
    loadingDiv.appendChild(loadingText);
    return loadingDiv;
  };
  /**
   * Tạo một section trong giao diện cài đặt
   * @param id Id của section
   * @param title Tiêu đề của section
   * @param children Các phần tử con sẽ được thêm vào section này
   * @param show Điều kiện để hiển thị các phần tử con (False = không hiển thị)
   */
  createSection = (id, title, children, show = true) => {
    const content = this.createRow(`${id}-content`, children);
    content.classList.add("theme-settings-section-content");
    const section = this.createRow(id, [
      this.createLabel(title, "", "theme-settings-section-title"),
      content
    ], show);
    section.classList.add("theme-settings-section");
    return section;
  };
  /**
   * Tạo một div trống
   * @param id Id của 1 div trống
   * @param childs Các phần tử con sẽ được thêm vào div này
   * @param show Điều kiện để hiển thị các phần tử con (False = không hiển thị)
   */
  createRow = (id, childs, show = true) => {
    const row = document.createElement("div");
    row.classList.add("lust-theme-settings-row");
    row.id = id;
    if (Array.isArray(childs) && show)
      childs.forEach((el) => row.appendChild(el));
    return row;
  };
  /**
   * Giống với row nhưng có thêm nút để ẩn hiện các phần tử con
   * @param id Id của 1 div có thể ẩn hiện
   * @param childs Các phần tử con sẽ được thêm vào div này
   * @param show Điều kiện để hiển thị các phần tử con (False = không hiển thị)
   */
  createRowHideable = (id, childs, show = true) => {
    const row = document.createElement("div");
    const main = document.createElement("div");
    const hideButtonElement = document.createElement("div");
    const hideButtonIcon = this.createImage(true, "plugins-icons/next_button.png", "lust-theme-settings-row-hide-icon");
    row.classList.add("lust-theme-settings-row-hideable");
    row.id = id;
    hideButtonElement.id = "lust-theme-settings-row-hide-button";
    main.setAttribute("isHiding", "false");
    row.append(hideButtonElement);
    hideButtonElement.append(hideButtonIcon);
    row.append(main);
    if (Array.isArray(childs) && show)
      childs.forEach((el) => main.appendChild(el));
    hideButtonElement.onclick = () => {
      if (main.getAttribute("isHiding") === "false") {
        main.setAttribute("isHiding", "true");
        hideButtonIcon.setAttribute("class", "lust-theme-settings-row-hide-icon-hidden");
      } else {
        main.setAttribute("isHiding", "false");
        hideButtonIcon.setAttribute("class", "lust-theme-settings-row-hide-icon");
      }
    };
    return row;
  };
  /**
   * Tạo một label hoặc text 
   * @param text Nội dung của label
   * @param id Id của label
   * @param cls Class của label, mặc định là "Lust-theme-template-class"
   * @param style Style của label, mặc định là ""
   */
  createLabel = (text, id = "", cls = "Lust-theme-template-class", style = "") => {
    const label = document.createElement("p");
    label.classList.add("lol-settings-window-size-text");
    label.classList.add("lust-theme-settings-text");
    if (cls.trim()) {
      cls.trim().split(/\s+/).forEach((className) => label.classList.add(className));
    }
    label.id = id;
    label.style.cssText = style;
    label.innerText = text;
    return label;
  };
  /**
   * Tạo một thẻ img
   * @param localImage Sử dụng ảnh local hay online, mặc định là true
   * @param image Tên của ảnh hoặc đường dẫn đến ảnh, phụ thuộc vào biến localImage
   * @param cls Class của thẻ img
   * @param id Id của thẻ img, mặc định là ""
   * @param style Style của thẻ img, mặc định là ""
   */
  createImage = (localImage = true, image, cls, id = "", style = "") => {
    const img = document.createElement("img");
    img.setAttribute("src", localImage ? `${datapath$5}assets/icon/${image}` : image);
    img.classList.add(cls);
    img.id = id;
    img.style.cssText = style;
    return img;
  };
  /**
   * Tạo 1 thẻ đường dẫn a
   * @param text Text hiển thị của đường dẫn
   * @param href Đường dẫn đến trang đích
   * @param onClick Hàm sẽ gọi khi người dùng click vào đường dẫn
   * @param id Id của thẻ
   */
  createLink = (text, href, onClick, id = "") => {
    const link = document.createElement("p");
    link.classList.add("lol-settings-code-of-conduct-link");
    link.classList.add("lol-settings-window-size-text");
    const a = document.createElement("a");
    a.innerText = text;
    a.target = "_blank";
    a.href = href;
    a.onclick = onClick || null;
    a.id = id;
    link.append(a);
    return link;
  };
  /**
   * Là sự kết hợp của Image và Link
   * @param localImage Sử dụng ảnh local hay online, mặc định là true
   * @param image Tên của ảnh hoặc đường dẫn đến ảnh, phụ thuộc vào biến localImage
   * @param cls Class của thẻ img
   * @param href Đường dẫn đến trang đích
   * @param onClick Hàm sẽ gọi khi người dùng click vào ảnh
   */
  createImageWithLink = (localImage, image, cls, href, onClick) => {
    const link = this.createLink("", href, onClick);
    link.setAttribute("class", "");
    link.style.margin = "0px";
    const img = this.createImage(localImage, image, cls, "", "");
    link.querySelector("a")?.append(img);
    return link;
  };
  /**
   * Ảnh của những người đóng góp
   * @param localImage Sử dụng ảnh local hay online, mặc định là true
   * @param image Tên của ảnh hoặc đường dẫn đến ảnh, phụ thuộc vào biến localImage
   * @param C_name Tên của người đóng góp
   * @param info Thông tin đóng góp của người đó
   * @param url Đường đẫn đến trang cá nhân của người đó
   */
  createContributor = (localImage, image, C_name, info, url) => {
    const origin = document.createElement("div");
    origin.id = "Contrib";
    const div = document.createElement("div");
    div.style.cssText = "margin-left: 10px;";
    const img = this.createImageWithLink(localImage, image, "contributor-img", url, () => {
    });
    const Name = this.createLabel(C_name, "contributor-name");
    const Info = this.createLabel(info, "", "contributor-info", "margin: 0px");
    origin.append(img);
    origin.append(div);
    div.append(Name);
    div.append(Info);
    return origin;
  };
  /**
   * Tạo một nút
   * @param text Nội dung của nút
   * @param cls Class của nút, mặc định là "Lust-theme-template-class"
   * @param onClick Event sẽ gọi khi người dùng click vào nút
   * @param id Id của nút, mặc định là ""
   * @param style Style của nút, mặc định là ""
   */
  createButton = (text, cls = "Lust-theme-template-class", onClick, id = "", style = "") => {
    const btn = document.createElement("lol-uikit-flat-button-secondary");
    btn.innerText = text;
    btn.onclick = onClick;
    btn.style.cssText = "display: flex;" + style;
    btn.setAttribute("class", cls);
    btn.id = id;
    return btn;
  };
  /**
   * Tạo 1 text box
   * @param Datastore Tến của Datastore, kiểu string
   * @param style Style của text box, mặc định là ""
   * @param onInput Event sẽ gọi khi người dùng nhập vào text box
   */
  createInputElement = (Datastore, style = "", onInput) => {
    const origin = document.createElement("lol-uikit-flat-input");
    const searchbox = document.createElement("input");
    origin.classList.add(Datastore);
    origin.style.cssText = style;
    searchbox.type = "url";
    searchbox.name = "name";
    searchbox.placeholder = LustData.get(Datastore);
    searchbox.oninput = onInput;
    origin.appendChild(searchbox);
    return { origin, searchbox };
  };
  /**
   * Sử dụng createInputElement để tạo một text box với style và onInput mặc định
   * @param Datastore Tên của Datastore, kiểu string
   */
  createSearchBox = (Datastore) => {
    const { origin, searchbox } = this.createInputElement(
      Datastore,
      "margin-bottom: 12px; width: 190px;",
      () => {
        let input = {
          get value() {
            return searchbox.value;
          }
        };
        LustData.set(Datastore, input.value);
      }
    );
    return origin;
  };
  /**
   * Tạo 1 checkbox
   * @param text Nội dung của checkbox
   * @param id Id của parent chứa checkbox
   * @param boxID Id của checkbox
   * @param check Kiểm tra sự thay đổi của checkbox, sẽ gọi hàm này khi người dùng click vào checkbox
   * @param show Có hiển thị checkbox hay không
   * @param Datastore Tên của Datastore, kiểu string
   */
  createCheckBox = (text, id, boxID, check, show, Datastore) => {
    const container = document.createElement("div");
    container.style.width = "fit-content";
    const origin = document.createElement("lol-uikit-flat-checkbox");
    origin.id = id;
    origin.setAttribute("lastDatastore", LustData.get(Datastore));
    const label = document.createElement("label");
    label.textContent = text;
    label.setAttribute("slot", "label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = boxID;
    checkbox.setAttribute("slot", "input");
    if (LustData.get(Datastore)) {
      checkbox.checked = true;
      origin.setAttribute("class", "checked");
    } else {
      checkbox.checked = false;
      origin.setAttribute("class", "");
    }
    checkbox.onclick = () => {
      if (LustData.get(Datastore)) {
        origin.removeAttribute("class");
        checkbox.checked = false;
        LustData.set(Datastore, false);
        check();
      } else {
        origin.setAttribute("class", "checked");
        checkbox.checked = true;
        LustData.set(Datastore, true);
        check();
      }
    };
    if (show) {
      container.appendChild(origin);
      origin.appendChild(checkbox);
      origin.appendChild(label);
      return container;
    } else {
      const blankDiv = document.createElement("div");
      container.appendChild(blankDiv);
      return container;
    }
  };
  /**
   * Tạo 1 thanh kéo (slider) đa năng
   * @param text Nội dung hiển thị
   * @param value Giá trị ban đầu (0-100)
   * @param onChange Hàm gọi khi giá trị thay đổi, nhận value (0-100)
   */
  createSlider = (text, value, onChange) => {
    const div = document.createElement("div");
    const title = document.createElement("div");
    const row = document.createElement("div");
    const origin = document.createElement("lol-uikit-slider");
    const slider = document.createElement("div");
    const sliderbase = document.createElement("div");
    row.setAttribute("class", "lol-settings-sound-row-slider");
    title.setAttribute("class", "lol-settings-sound-title");
    origin.setAttribute("class", "lol-settings-slider");
    origin.setAttribute("value", `${value}`);
    origin.addEventListener("change", () => {
      title.textContent = `${text}: ${origin.value}`;
      onChange?.(Number(origin.value));
    });
    title.textContent = `${text}: ${value}`;
    slider.setAttribute("class", "lol-uikit-slider-wrapper horizontal");
    sliderbase.setAttribute("class", "lol-uikit-slider-base");
    div.appendChild(title);
    div.appendChild(row);
    row.appendChild(origin);
    origin.appendChild(slider);
    slider.appendChild(sliderbase);
    return div;
  };
  /**
   * Tạo một dropdown đa năng
   * @param items Danh sách các option, mỗi option có label (hiển thị) và value (giá trị)
   * @param selectedValue Giá trị được chọn hiện tại
   * @param opts Tùy chọn: title, id, datastoreKey, onChange
   */
  createDropdown = (items, selectedValue, opts = {}) => {
    const origin = document.createElement("div");
    origin.classList.add("Dropdown-div");
    if (opts.id)
      origin.id = opts.id;
    if (opts.datastoreKey) {
      origin.setAttribute("lastDatastore", JSON.stringify(LustData.get(opts.datastoreKey)));
    }
    if (opts.title) {
      const title = this.createLabel(opts.title, "");
      origin.append(title);
    }
    const dropdown = document.createElement("lol-uikit-framed-dropdown");
    dropdown.classList.add("lol-settings-general-dropdown");
    origin.append(dropdown);
    for (const item of items) {
      const el = document.createElement("lol-uikit-dropdown-option");
      el.setAttribute("slot", "lol-uikit-dropdown-option");
      el.innerText = item.label;
      el.onclick = () => {
        if (opts.datastoreKey) {
          LustData.set(opts.datastoreKey, item.value);
        }
        opts.onChange?.(item);
      };
      if (selectedValue == item.value) {
        el.setAttribute("selected", "true");
      }
      dropdown.appendChild(el);
    }
    return origin;
  };
  /**
   * Tạo một input để người dùng có thể tải lên file
   * @param id Id của input
   * @param acceptFile Loại file được chấp nhận, kiểu string
   * @param onChange Hàm sẽ gọi khi người dùng thay đổi file
   */
  fileInput = (id, acceptFile, onChange) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = acceptFile;
    input.id = id;
    input.onchange = onChange;
    input.style.display = "none";
    return input;
  };
  /**
   * Tạo một input để người dùng có thể chọn màu sắc
   * @param id Id của input
   * @param targetDataStore Tên của Datastore, kiểu string
   * @param onChange Hàm sẽ gọi khi người dùng thay đổi màu sắc
   */
  colorPicker = (id, targetDataStore, onChange) => {
    const input = document.createElement("input");
    input.type = "color";
    input.id = id;
    input.value = LustData.get(targetDataStore);
    input.onchange = onChange;
    return input;
  };
  /**
   * Tạo một thanh trượt để điều chỉnh độ mờ của một phần tử
   * @param id Id của thanh trượt
   * @param text Nội dung của thanh trượt
   * @param opacityHexData độ mờ của phần tử dưới dạng HEX, kiểu string
   * @param onChange Hàm sẽ gọi khi người dùng thay đổi giá trị của thanh trượt
   */
  opacitySlider = (id, text, opacityHexData, onChange) => {
    const div = document.createElement("div");
    const title = document.createElement("div");
    const row = document.createElement("div");
    const origin = document.createElement("lol-uikit-slider");
    const slider = document.createElement("div");
    const sliderbase = document.createElement("div");
    row.setAttribute("class", "lol-settings-sound-row-slider");
    title.setAttribute("class", "lol-settings-sound-title");
    title.id = id + "-title";
    origin.id = id;
    origin.setAttribute("class", "lol-settings-slider");
    origin.setAttribute("value", `${parseInt(LustData.get(opacityHexData).slice(0, 2), 16) / 255 * 100}`);
    origin.addEventListener("change", onChange);
    title.textContent = `${text}: ${parseInt(LustData.get(opacityHexData).slice(0, 2), 16) / 255 * 100}%`;
    slider.setAttribute("class", "lol-uikit-slider-wrapper horizontal");
    sliderbase.setAttribute("class", "lol-uikit-slider-base");
    div.appendChild(title);
    div.appendChild(row);
    row.appendChild(origin);
    origin.appendChild(slider);
    slider.appendChild(sliderbase);
    return div;
  };
}
const UI = new ui();

async function stop(time) {
  return await new Promise((resolve) => setTimeout(resolve, time));
}

function addStyleNode(style) {
  const styleElement = document.createElement("style");
  styleElement.appendChild(document.createTextNode(style));
  document.body.appendChild(styleElement);
}

function addStyleNodeWithID(Id, style) {
  const styleElement = document.createElement("style");
  styleElement.id = Id;
  styleElement.appendChild(document.createTextNode(style));
  document.body.appendChild(styleElement);
}

function addFont(folder, font_id, font_family) {
  const fontStyle = document.createElement("style");
  fontStyle.id = font_id;
  fontStyle.appendChild(document.createTextNode(
    `@font-face {font-family: "${utils.escapeCssString(font_family)}"; src: url("${utils.escapeCssString(encodeURI(folder))}")}`
  ));
  document.body.appendChild(fontStyle);
}

function updateImageSrc(oldSrc, newSrc) {
  const originalSrc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  Object.defineProperty(HTMLImageElement.prototype, "src", {
    get: originalSrc.get,
    set: function(value) {
      if (typeof value === "string" && value.includes(oldSrc)) {
        const newLink = newSrc;
        return originalSrc.set.call(this, newLink);
      }
      return originalSrc.set.call(this, value);
    }
  });
}

function CustomCursor(folder, css) {
  const cursor = document.createElement("div");
  cursor.classList.add("cursor");
  cursor.style.background = folder;
  document.addEventListener("mousemove", (e) => {
    cursor.style.transform = `translate3d(calc(${e.clientX}px - 40%), calc(${e.clientY}px - 40%), 0)`;
  });
  let htmlElement = document.querySelector("html");
  htmlElement.appendChild(cursor);
  addStyleNode(css);
}

async function getSummonerID() {
  const response = await fetch("/lol-summoner/v1/current-summoner");
  const data = await response.json();
  return JSON.parse(data.summonerId);
}

async function getPUUID() {
  const response = await fetch("/lol-summoner/v1/current-summoner");
  const data = await response.json();
  return data.puuid;
}

async function subscribe_endpoint$1(endpoint, callback) {
  const getUri = document.querySelector('link[rel="riot:plugins:websocket"]');
  const uri = getUri?.href;
  const ws = new WebSocket(uri, "wamp");
  ws.onopen = () => ws.send(JSON.stringify([5, "OnJsonApiEvent" + endpoint.replace(/\//g, "_")]));
  ws.onmessage = callback;
}

function routineAddCallback(routines, callback, target) {
  routines.push({ callback, target });
}

function mutationObserverAddCallback(mutationCallbacks, callback, target) {
  mutationCallbacks.push({ callback, target });
}

function freezeProperties(object, properties) {
  for (const type in object) {
    if (properties && properties.length && properties.includes(type) || (!properties || !properties.length)) {
      let value = object[type];
      try {
        Object.defineProperty(object, type, {
          configurable: false,
          get: () => value,
          set: (v) => v
        });
      } catch {
      }
    }
  }
}

const _escDiv = document.createElement("div");
function escapeHtml$1(unsafe) {
  if (unsafe === null || unsafe === void 0)
    return "";
  _escDiv.textContent = String(unsafe);
  return _escDiv.innerHTML;
}
function sanitizeColor(value) {
  const str = String(value ?? "");
  if (/^#?[0-9a-fA-F]{3,8}$/.test(str))
    return str;
  return "";
}
function sanitizeFileName(value) {
  return String(value ?? "").replace(/[<>"'&\\\/]/g, "");
}
function escapeCssString(value) {
  return String(value).replace(/["\\\n\r\f]/g, "\\$&");
}
function getSafeGoogleFont(value) {
  const rawValue = String(value ?? "").trim();
  if (!rawValue || rawValue.length > 2048)
    return null;
  try {
    const url = new URL(rawValue);
    if (url.protocol !== "https:")
      return null;
    if (url.hostname !== "fonts.googleapis.com")
      return null;
    if (url.pathname !== "/css" && url.pathname !== "/css2")
      return null;
    if (url.username || url.password || url.hash)
      return null;
    if (!url.searchParams.has("family"))
      return null;
    const family = url.searchParams.get("family")?.split(":")[0].trim();
    if (!family || !/^[\w\s-]{1,80}$/.test(family))
      return null;
    return { url, family };
  } catch {
    return null;
  }
}

let pvp_net_id, summoner_id, phase;
const routines = [];
const mutationCallbacks = [];
const updateUserPvpNetInfos = async (message) => {
  const data = JSON.parse(message.data)[2].data;
  if (data) {
    pvp_net_id = data.id;
    summoner_id = data.summonerId;
  }
};
const updatePhaseCallback = async (message) => {
  phase = JSON.parse(message.data)[2].data;
};
window.addEventListener("load", () => {
  subscribe_endpoint$1("/lol-gameflow/v1/gameflow-phase", updatePhaseCallback);
  subscribe_endpoint$1("/lol-chat/v1/me", updateUserPvpNetInfos);
  setInterval(() => {
    routines.forEach((routine) => routine.callback());
  }, 1e3);
  const observer = new MutationObserver((mutationsList) => {
    for (const mutation of mutationsList) {
      for (const addedNode of mutation.addedNodes) {
        if (addedNode.nodeType === Node.ELEMENT_NODE && addedNode.classList) {
          for (const addedNodeClass of addedNode.classList) {
            for (const obj of mutationCallbacks) {
              if (obj.target.indexOf(addedNodeClass) !== -1 || obj.target.indexOf("*") !== -1) {
                obj.callback(addedNode);
              }
            }
          }
        }
      }
    }
  });
  observer.observe(document, { attributes: true, childList: true, subtree: true });
});
class Utils {
  get phase() {
    return phase;
  }
  set phase(value) {
    phase = value;
  }
  get summoner_id() {
    return summoner_id;
  }
  set summoner_id(value) {
    summoner_id = value;
  }
  get pvp_net_id() {
    return pvp_net_id;
  }
  set pvp_net_id(value) {
    pvp_net_id = value;
  }
  subscribe_endpoint = subscribe_endpoint$1;
  routineAddCallback(callback, target) {
    routineAddCallback(routines, callback, target);
  }
  mutationObserverAddCallback(callback, target) {
    mutationObserverAddCallback(mutationCallbacks, callback, target);
  }
  addStyleNode = addStyleNode;
  addFont = addFont;
  CustomCursor = CustomCursor;
  getSummonerID = getSummonerID;
  getPUUID = getPUUID;
  addStyleNodeWithID = addStyleNodeWithID;
  freezeProperties = freezeProperties;
  stop = stop;
  updateImageSrc = updateImageSrc;
  sanitizeColor = sanitizeColor;
  sanitizeFileName = sanitizeFileName;
  escapeHtml = escapeHtml$1;
  escapeCssString = escapeCssString;
  getSafeGoogleFont = getSafeGoogleFont;
}
const utils = new Utils();

const datapath$7 = `//plugins/${getThemeName()}/`;
const iconFolder$3 = `${datapath$7}assets/icon/`;
const bgFolder$1 = `${datapath$7}assets/backgrounds/`;
let addedBackgrounds = false;
let navbarContentList = [];
let haveNewContent = 0;
(await import(`//plugins/${getThemeName()}/config/cdnServer.js`)).default;
const defaultData = {
  "Wallpaper-list": ["lust-wallpaper.webm", "lust-dark.jpg", "lust-wallpaper.jpg"],
  "Audio-list": ["lust-silence.wav"],
  "wallpaper-index": 0,
  "audio-index": 0,
  "wallpaper-volume": 0,
  "audio-volume": 0.1,
  "mute-audio": false,
  "Playback-speed": 100,
  "Audio-currentTime": 0,
  "Wallpaper-currentTime": 0,
  "WallpaperAudio-timeUpdate": 3e3
};
function initHomepageData() {
  LustData.set("Font-folder", `${datapath$7}assets/fonts/`);
  LustData.set("Plugin-folder-name", getThemeName());
  setDefaultData(defaultData, false);
  const wallpapers = LustData.get("Wallpaper-list") || [];
  for (const name of defaultData["Wallpaper-list"]) {
    if (!wallpapers.includes(name)) wallpapers.push(name);
  }
  LustData.set("Wallpaper-list", wallpapers);
}
async function updateSummonerIdentity() {
  const summonerID = await utils.getSummonerID();
  const PUUID = await utils.getPUUID();
  LustData.set("Summoner-ID", summonerID);
  LustData.set("PUUID", PUUID);
  log(`%cCurrent summonerID: %c${summonerID}`, "color: #e4c2b3", "color: #0070ff");
  log(`%cCurrent PUUID: %c${PUUID}`, "color: #e4c2b3", "color: #0070ff");
}
class ChangeHomePageTabs {
  // Hide or show tab from homepage
  hideShowTab = (data, obj, name) => {
    if (data) {
      try {
        const element = document.querySelector(obj);
        if (element) {
          element.style.display = "none";
          log(`${name} tab deleted`);
        } else {
          warn(`Element not found for ${name}`);
        }
      } catch (error2) {
        error2(`Error hiding ${name} tab:`, error2);
      }
    } else {
      try {
        document.querySelector(obj).style.display = "block";
      } catch (err) {
        error(`This client doesn't have ${name} tab`, err);
      }
    }
  };
  applyHideAndShowTFTtab = () => {
    this.hideShowTab(LustData.get("hide-tft-match-history"), 'lol-uikit-navigation-bar a[href="/match-history"]', "TFT match history");
    this.hideShowTab(LustData.get("hide-tft-news"), 'lol-uikit-navigation-bar a[href="/news"]', "TFT news");
    this.hideShowTab(LustData.get("hide-tft-rotational-shop"), 'lol-uikit-navigation-bar a[href="/rotational-shop"]', "TFT rotational shop");
    this.hideShowTab(LustData.get("hide-tft-troves"), 'lol-uikit-navigation-bar a[href="/troves"]', "TFT troves");
    this.hideShowTab(LustData.get("hide-tft-battle-pass"), 'lol-uikit-navigation-bar a[href="/battle-pass"]', "TFT battle pass");
    this.hideShowTab(LustData.get("hide-tft-home"), 'lol-uikit-navigation-bar a[href="/home"]', "TFT home");
  };
  deleteNavbarTab = () => {
    const intervalId = window.setInterval(() => {
      const overviewTab = document.querySelector('lol-uikit-navigation-item[item-id="overview"]');
      const TFThome = document.querySelector('lol-uikit-navigation-bar a[href="/home"]');
      if (overviewTab || TFThome) {
        window.clearInterval(intervalId);
        this.applyHideAndShowTFTtab();
      }
    }, 1e3);
  };
}
const changeHomePageTabs = new ChangeHomePageTabs();
class WallpaperController {
  wallpaperPlayPause = () => {
    const lustBg = document.getElementById("lust-bg");
    switch (LustData.get("pause-wallpaper") % 2) {
      case 1:
        lustBg.play();
        break;
      default:
        lustBg.pause();
        break;
    }
  };
  playPauseSetIcon = (elem = document.querySelector(".pause-bg-icon")) => {
    const pauseBgIcon = elem;
    if (!pauseBgIcon)
      return;
    pauseBgIcon.setAttribute("src", `${iconFolder$3}plugins-icons/${LustData.get("pause-wallpaper") % 2 === 0 ? "play_button" : "pause_button"}.png`);
  };
  loadBG = (BG) => {
    const lustBg = document.getElementById("lust-bg");
    const lustStaticBg = document.getElementById("lust-static-bg");
    lustBg.pause();
    lustBg.removeAttribute("src");
    while (lustBg.firstChild) {
      lustBg.removeChild(lustBg.firstChild);
    }
    lustBg.load();
    requestAnimationFrame(() => {
      lustBg.src = `${bgFolder$1}wallpapers/${BG}`;
      lustBg.playbackRate = LustData.get("Playback-speed") / 100;
      lustStaticBg.src = `${bgFolder$1}wallpapers/${BG}`;
      if (LustData.get("pause-wallpaper") % 2 === 1) {
        lustBg.play();
      } else {
        lustBg.pause();
      }
    });
  };
  changeBG = async (BG) => {
    const lustBg = document.getElementById("lust-bg");
    const lustStaticBg = document.getElementById("lust-static-bg");
    log(`Now playing %c${BG}`, "color: #0070ff");
    setTimeout(() => {
      this.loadBG(BG);
      lustBg.classList.remove("webm-hidden");
      lustStaticBg.classList.remove("webm-hidden");
    }, 500);
    this.wallpaperSlider(BG);
  };
  nextWallpaper = async () => {
    const lustBg = document.getElementById("lust-bg");
    lustBg.classList.add("webm-hidden");
    const lustStaticBg = document.getElementById("lust-static-bg");
    lustStaticBg.classList.add("webm-hidden");
    LustData.set("wallpaper-index", LustData.get("wallpaper-index") + 1);
    if (LustData.get("wallpaper-index") > LustData.get("Wallpaper-list").length - 1) {
      LustData.set("wallpaper-index", 0);
    }
    await this.changeBG(LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]);
  };
  prevWallpaper = async () => {
    const lustBg = document.getElementById("lust-bg");
    lustBg.classList.add("webm-hidden");
    const lustStaticBg = document.getElementById("lust-static-bg");
    lustStaticBg.classList.add("webm-hidden");
    LustData.set("wallpaper-index", LustData.get("wallpaper-index") - 1);
    if (LustData.get("wallpaper-index") < 0) {
      LustData.set("wallpaper-index", LustData.get("Wallpaper-list").length - 1);
    }
    await this.changeBG(LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]);
  };
  checkBGType = (wallpaper) => {
    const imageRegex = /\.(jpg|jpeg|png|gif|bmp|webp|ico)$/i;
    const videoRegex = /\.(mp4|webm|mkv|mov|avi|wmv|3gp|m4v)$/i;
    if (imageRegex.test(wallpaper)) {
      return 0;
    } else if (videoRegex.test(wallpaper)) {
      return 1;
    }
  };
  slideshowTimeoutId = null;
  wallpaperSlider = (wallpaper) => {
    if (this.slideshowTimeoutId !== null) {
      window.clearTimeout(this.slideshowTimeoutId);
      this.slideshowTimeoutId = null;
    }
    if (LustData.get("wallpaper-slideshow") && this.checkBGType(wallpaper) == 0) {
      this.slideshowTimeoutId = window.setTimeout(() => {
        this.slideshowTimeoutId = null;
        this.nextWallpaper();
      }, LustData.get("wallpaper-change-slide-time"));
    }
  };
}
const wallpaperController = new WallpaperController();
class AudioController {
  audioPlayPause = () => {
    const audio = document.getElementById("bg-audio");
    switch (LustData.get("pause-audio") % 2) {
      case 1:
        audio.play();
        break;
      default:
        audio.pause();
        break;
    }
    this.changeSongName();
  };
  playPauseSetIconAudio = (elem = document.querySelector(".pause-audio-icon")) => {
    const pauseAudioIcon = elem;
    if (!pauseAudioIcon)
      return;
    pauseAudioIcon.setAttribute("src", `${iconFolder$3}plugins-icons/${LustData.get("pause-audio") % 2 === 0 ? "play_button" : "pause_button"}.png`);
  };
  audioMute = () => {
    const audio = document.getElementById("bg-audio");
    const wallpaperAudio = document.getElementById("lust-bg");
    const isMuted = LustData.get("mute-audio");
    wallpaperAudio.muted = isMuted;
    audio.muted = isMuted;
    log(`%caudio and wallpaper mute: %c${isMuted}`, "", isMuted ? "color: #00ff44" : "color: red");
  };
  muteSetIconAudio = (elem = document.querySelector(".mute-audio-icon")) => {
    const muteAudioIcon = elem;
    if (!muteAudioIcon)
      return;
    muteAudioIcon.setAttribute("src", `${iconFolder$3}plugins-icons/${LustData.get("mute-audio") ? "mute" : "audio"}.png`);
  };
  setAudioLoopIcon = (elem = document.querySelector(".audio-loop-icon")) => {
    const iconElement = elem;
    if (!iconElement)
      return;
    iconElement.setAttribute("src", `${iconFolder$3}plugins-icons/${LustData.get("audio-loop") ? "rotating-arrow" : "unrotating-arrow"}.png`);
  };
  toggleAudioLoop = () => {
    const audio = document.getElementById("bg-audio");
    function handleAudioEnded() {
      audio.pause();
      audio.load();
    }
    if (LustData.get("audio-loop")) {
      audio.removeEventListener("ended", this.nextSong);
      audio.addEventListener("ended", handleAudioEnded);
    } else {
      audio.removeEventListener("ended", handleAudioEnded);
      audio.addEventListener("ended", this.nextSong);
      this.changeSongName();
    }
  };
  loadSong = (song) => {
    const audio = document.getElementById("bg-audio");
    audio.src = `${bgFolder$1}audio/${song}`;
  };
  updateAudio = async (song) => {
    this.loadSong(song);
    this.audioPlayPause();
    this.changeSongName();
    log(`Now playing %c${song}`, "color: #0070ff");
  };
  nextSong = async () => {
    LustData.set("audio-index", LustData.get("audio-index") + 1);
    if (LustData.get("audio-index") > LustData.get("Audio-list").length - 1) {
      LustData.set("audio-index", 0);
    }
    await this.updateAudio(LustData.get("Audio-list")[LustData.get("audio-index")]);
  };
  prevSong = async () => {
    LustData.set("audio-index", LustData.get("audio-index") - 1);
    if (LustData.get("audio-index") < 0) {
      LustData.set("audio-index", LustData.get("Audio-list").length - 1);
    }
    await this.updateAudio(LustData.get("Audio-list")[LustData.get("audio-index")]);
  };
  changeSongName = () => {
    let currentSong = LustData.get("Audio-list")[LustData.get("audio-index")];
    let songNameText = document.querySelector(".audio-name-bar > p");
    if (songNameText) {
      if (LustData.get("pause-audio") % 2 === 0) {
        songNameText.innerHTML = `Paused: <br/>${utils.escapeHtml(currentSong)}`;
      } else
        songNameText.innerHTML = `Now playing: <br/>${utils.escapeHtml(currentSong)}`;
    }
  };
}
const audioController = new AudioController();
class MainController {
  backgroundControllerClickHandler = null;
  createElementWithClass = (tag, className) => {
    const element = document.createElement(tag);
    if (className)
      element.classList.add(className);
    return element;
  };
  createElementWithId = (tag, id) => {
    const element = document.createElement(tag);
    if (id)
      element.id = id;
    return element;
  };
  createIcon = (className, src) => {
    const icon = this.createElementWithClass("img", className);
    if (src)
      icon.setAttribute("src", src);
    return icon;
  };
  makeDraggable = (element) => {
    let startX = 0, startY = 0;
    let startLeft = 0, startTop = 0;
    let isDragging = false;
    let wasDragged = false;
    element.addEventListener("click", (e) => {
      if (wasDragged) {
        e.stopPropagation();
        e.preventDefault();
        wasDragged = false;
      }
    }, true);
    element.addEventListener("mousedown", (e) => {
      const target = e.target;
      if (target.closest("input"))
        return;
      startX = e.clientX;
      startY = e.clientY;
      const computed = getComputedStyle(element);
      startLeft = parseInt(computed.left) || 0;
      startTop = parseInt(computed.top) || 0;
      isDragging = false;
      const onMouseMove = (e2) => {
        const dx = e2.clientX - startX;
        const dy = e2.clientY - startY;
        if (!isDragging && Math.abs(dx) + Math.abs(dy) > 5) {
          isDragging = true;
        }
        if (isDragging) {
          let newLeft = startLeft + dx;
          let newTop = startTop + dy;
          element.style.left = `${newLeft}px`;
          element.style.top = `${newTop}px`;
          element.style.bottom = "auto";
          const elemRect = element.getBoundingClientRect();
          if (elemRect.left < 0)
            newLeft -= elemRect.left;
          if (elemRect.top < 0)
            newTop -= elemRect.top;
          if (elemRect.right > window.innerWidth)
            newLeft -= elemRect.right - window.innerWidth;
          if (elemRect.bottom > window.innerHeight)
            newTop -= elemRect.bottom - window.innerHeight;
          element.style.left = `${newLeft}px`;
          element.style.top = `${newTop}px`;
          e2.preventDefault();
        }
      };
      const onMouseUp = () => {
        if (isDragging) {
          wasDragged = true;
        }
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      };
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    });
  };
  // Delete controllers
  deleteController = () => {
    if (this.backgroundControllerClickHandler) {
      document.removeEventListener("click", this.backgroundControllerClickHandler);
      this.backgroundControllerClickHandler = null;
    }
    document.querySelector(".webm-bottom-buttons-container-hovered")?.remove();
    document.querySelector(".webm-bottom-buttons-container")?.remove();
    document.querySelector(".wallpaper-controls")?.remove();
  };
  createMainController = () => {
    const container = this.createElementWithClass("div", "webm-bottom-buttons-container");
    if (LustData.get("disable-theme-audio"))
      container.style.display = "none";
    const musicControlsMain = this.createElementWithClass("div", "music-controls-main");
    const musicControls = this.createElementWithClass("div", "music-controls");
    const pauseAudio = this.createElementWithId("div", "pause-audio");
    const nextAudio = this.createElementWithId("div", "next-audio");
    const prevAudio = this.createElementWithId("div", "prev-audio");
    const muteAudio = this.createElementWithId("div", "mute-audio");
    const audioLoop = this.createElementWithId("div", "audio-loop");
    const pauseAudioIcon = this.createIcon("pause-audio-icon", `${iconFolder$3}plugins-icons/pause-audio.png`);
    const nextAudioIcon = this.createIcon("next-audio-icon", `${iconFolder$3}plugins-icons/next-audio.png`);
    const prevAudioIcon = this.createIcon("prev-audio-icon", `${iconFolder$3}plugins-icons/prev-audio.png`);
    const muteAudioIcon = this.createIcon("mute-audio-icon", `${iconFolder$3}plugins-icons/mute-audio.png`);
    const audioLoopIcon = this.createIcon("audio-loop-icon", `${iconFolder$3}plugins-icons/audio-loop.png`);
    const wallpaperControls = this.createElementWithClass("div", "wallpaper-controls");
    if (LustData.get("disable-theme-wallpaper"))
      wallpaperControls.style.display = "none";
    const pauseBg = this.createElementWithId("div", "pause-bg");
    const nextBg = this.createElementWithId("div", "next-bg");
    const prevBg = this.createElementWithId("div", "prev-bg");
    const pauseBgIcon = this.createIcon("pause-bg-icon", `${iconFolder$3}plugins-icons/pause-bg.png`);
    const nextBgIcon = this.createIcon("next-bg-icon", `${iconFolder$3}plugins-icons/next_button.png`);
    const prevBgIcon = this.createIcon("prev-bg-icon", `${iconFolder$3}plugins-icons/prev_button.png`);
    const bgDropdown = this.createElementWithId("lol-uikit-framed-dropdown", "bgdropdown");
    const progressBar = this.createElementWithClass("div", "theme-audio-progress-bar");
    const progress = this.createElementWithClass("div", "progress-status");
    const audioNameBar = this.createElementWithClass("div", "audio-name-bar");
    const audioName = this.createElementWithId("p", "audio-name");
    const volumeSliderContainer = this.createElementWithClass("div", "volume-slider-container");
    const volumeSlider = this.createElementWithClass("input", "volume-slider");
    volumeSlider.type = "range";
    volumeSlider.min = "0";
    volumeSlider.max = "100";
    volumeSlider.value = LustData.get("audio-volume") * 100;
    volumeSlider.classList.add("volume-slider");
    const muteUnmuteButton = this.createElementWithClass("div", "mute-unmute-button");
    const muteUnmuteIcon = this.createIcon("mute-unmute-icon", `${iconFolder$3}plugins-icons/${LustData.get("mute-audio") ? "mute" : "audio"}.png`);
    audioController.playPauseSetIconAudio(pauseAudioIcon);
    audioController.muteSetIconAudio(muteAudioIcon);
    audioController.setAudioLoopIcon(audioLoopIcon);
    wallpaperController.playPauseSetIcon(pauseBgIcon);
    LustData.get("pause-audio") % 2 === 0 ? audioName.innerHTML = `Paused: <br/>${utils.escapeHtml(LustData.get("Audio-list")[LustData.get("audio-index")])}` : audioName.innerHTML = `Now playing: <br/>${utils.escapeHtml(LustData.get("Audio-list")[LustData.get("audio-index")])}`;
    muteUnmuteButton.appendChild(muteUnmuteIcon);
    volumeSliderContainer.appendChild(volumeSlider);
    volumeSliderContainer.appendChild(muteUnmuteButton);
    musicControlsMain.appendChild(volumeSliderContainer);
    musicControlsMain.append(audioNameBar, musicControls);
    musicControls.append(muteAudio, prevAudio, pauseAudio, nextAudio, audioLoop);
    muteAudio.append(muteAudioIcon);
    pauseAudio.append(pauseAudioIcon);
    prevAudio.append(prevAudioIcon);
    nextAudio.append(nextAudioIcon);
    audioLoop.append(audioLoopIcon);
    audioNameBar.append(audioName);
    if (LustData.get("old-prev/next-button")) {
      wallpaperControls.append(prevBg, pauseBg, nextBg);
      nextBg.append(nextBgIcon);
      prevBg.append(prevBgIcon);
    } else {
      const newBgChange = document.createElement("div");
      newBgChange.id = "newbgchange";
      const sizeHint = document.createElement("div");
      sizeHint.id = "bg-size-hint";
      sizeHint.textContent = lustTr("16:9 Size Preferred");
      newBgChange.append(bgDropdown, sizeHint);
      wallpaperControls.append(newBgChange, pauseBg);
      LustData.get("Wallpaper-list").forEach((opt, id) => {
        const el = document.createElement("lol-uikit-dropdown-option");
        el.setAttribute("slot", "lol-uikit-dropdown-option");
        el.innerText = opt;
        el.onclick = async () => {
          const lustBg = document.getElementById("lust-bg");
          lustBg.classList.add("webm-hidden");
          const lustStaticBg = document.getElementById("lust-static-bg");
          lustStaticBg.classList.add("webm-hidden");
          LustData.set("wallpaper-index", id);
          await wallpaperController.changeBG(LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]);
        };
        if (LustData.get("wallpaper-index") === id) {
          el.setAttribute("selected", "true");
        }
        bgDropdown.appendChild(el);
      });
    }
    pauseBg.append(pauseBgIcon);
    const addBg = this.createElementWithId("div", "add-bg");
    addBg.textContent = "+";
    addBg.title = lustTr("Add wallpaper");
    // Lust: + opens the wallpapers folder and watches it; a file copied in shows up
    // in the list and becomes the wallpaper, no file name to type
    const addBgName = this.createElementWithId("div", "add-bg-name");
    addBgName.hidden = true;
    wallpaperControls.append(addBg, addBgName);
    const addOption = (name) => {
      const option = document.createElement("lol-uikit-dropdown-option");
      option.setAttribute("slot", "lol-uikit-dropdown-option");
      option.innerText = name;
      option.onclick = async () => {
        document.getElementById("lust-bg").classList.add("webm-hidden");
        document.getElementById("lust-static-bg").classList.add("webm-hidden");
        LustData.set("wallpaper-index", LustData.get("Wallpaper-list").indexOf(name));
        await wallpaperController.changeBG(name);
      };
      bgDropdown.appendChild(option);
    };
    const useWallpaper = async (name) => {
      bgDropdown.querySelectorAll("lol-uikit-dropdown-option").forEach((option) => {
        option.toggleAttribute("selected", option.innerText === name);
      });
      document.getElementById("lust-bg").classList.add("webm-hidden");
      document.getElementById("lust-static-bg").classList.add("webm-hidden");
      LustData.set("wallpaper-index", LustData.get("Wallpaper-list").indexOf(name));
      await wallpaperController.changeBG(name);
    };
    let watching = null;
    addBg.addEventListener("click", async () => {
      const first = await lustAssets("wallpaper", "list");
      if (first.error) {
        addBgName.textContent = first.error;
        addBgName.hidden = false;
        return;
      }
      lustAssets("wallpaper", "open");
      const known = new Set(first.files || []);
      // Files already in the folder but not in the list yet (copied in before) are added too
      for (const name of first.files || []) {
        const list = LustData.get("Wallpaper-list") || [];
        if (!list.includes(name)) {
          LustData.set("Wallpaper-list", [...list, name]);
          addOption(name);
        }
      }
      addBgName.textContent = lustTr("Copy your picture or video into the folder that opened");
      addBgName.hidden = false;
      clearInterval(watching);
      const until = Date.now() + 3 * 60 * 1000;
      watching = setInterval(async () => {
        if (Date.now() > until) {
          clearInterval(watching);
          addBgName.hidden = true;
          return;
        }
        const reply = await lustAssets("wallpaper", "list");
        const added = (reply.files || []).filter((name) => !known.has(name));
        if (!added.length) return;
        clearInterval(watching);
        const list = LustData.get("Wallpaper-list") || [];
        for (const name of added) {
          if (!list.includes(name)) {
            list.push(name);
            addOption(name);
          }
        }
        LustData.set("Wallpaper-list", list);
        await useWallpaper(added[added.length - 1]);
        addBgName.textContent = lustTr("{name} is your wallpaper", { name: added[added.length - 1] });
        setTimeout(() => { addBgName.hidden = true; }, 4000);
      }, 2000);
    });
    progressBar.append(progress);
    container.append(musicControlsMain, progressBar);
    const showContainer = document.querySelector(".rcp-fe-lol-home");
    const showContainerNew = document.querySelector("#activity-center");
    if (showContainer) {
      showContainer.append(container, wallpaperControls);
    } else if (showContainerNew) {
      showContainerNew.append(container, wallpaperControls);
    } else {
      error("Could not find the container '#activity-center' or '.rcp-fe-lol-home' to append controls.");
    }
    volumeSlider.addEventListener("input", () => {
      const volumeValue = volumeSlider.value / 100;
      LustData.set("audio-volume", volumeValue);
      const audio2 = document.getElementById("bg-audio");
      audio2.volume = volumeValue;
      if (volumeValue === 0) {
        LustData.set("mute-audio", true);
        audio2.muted = true;
        audioController.muteSetIconAudio();
        muteUnmuteIcon.setAttribute("src", `${iconFolder$3}plugins-icons/mute.png`);
      } else {
        LustData.set("mute-audio", false);
        audio2.muted = false;
        audioController.muteSetIconAudio();
        muteUnmuteIcon.setAttribute("src", `${iconFolder$3}plugins-icons/audio.png`);
      }
    });
    muteUnmuteButton.addEventListener("click", () => {
      const isMuted = !LustData.get("mute-audio");
      LustData.set("mute-audio", isMuted);
      audioController.audioMute();
      audioController.muteSetIconAudio();
      muteUnmuteIcon.setAttribute("src", `${iconFolder$3}plugins-icons/${isMuted ? "mute" : "audio"}.png`);
      const audio2 = document.getElementById("bg-audio");
      if (isMuted) {
        volumeSlider.value = 0;
        audio2.volume = 0;
      } else {
        volumeSlider.value = LustData.get("audio-volume") * 100;
        audio2.volume = LustData.get("audio-volume");
      }
    });
    muteAudio.addEventListener("click", () => {
      if (volumeSliderContainer.style.display === "flex") {
        volumeSliderContainer.style.display = "none";
      } else {
        volumeSliderContainer.style.display = "flex";
      }
    });
    this.backgroundControllerClickHandler = (event) => {
      if (!muteAudio.contains(event.target) && !volumeSliderContainer.contains(event.target)) {
        volumeSliderContainer.style.display = "none";
      }
    };
    document.addEventListener("click", this.backgroundControllerClickHandler);
    const audio = document.getElementById("bg-audio");
    if (audio) {
      progress.style.width = audio && audio.duration ? `${audio.currentTime / audio.duration * 100 + 1}%` : "0%";
      audio.addEventListener("timeupdate", () => {
        progress.style.width = audio.duration ? `${audio.currentTime / audio.duration * 100 + 1}%` : "0%";
      });
    }
    container.addEventListener("click", async (event) => {
      if (event.target.closest("#pause-audio")) {
        LustData.set("pause-audio", LustData.get("pause-audio") + 1);
        audioController.audioPlayPause();
        audioController.playPauseSetIconAudio();
        audioController.changeSongName();
      }
      if (event.target.closest("#next-audio")) {
        await audioController.nextSong();
        audioController.changeSongName();
      }
      if (event.target.closest("#prev-audio")) {
        await audioController.prevSong();
        audioController.changeSongName();
      }
      if (event.target.closest("#audio-loop")) {
        LustData.set("audio-loop", !LustData.get("audio-loop"));
        audioController.toggleAudioLoop();
        audioController.setAudioLoopIcon();
      }
    });
    wallpaperControls.addEventListener("click", (event) => {
      if (event.target.closest("#pause-bg")) {
        LustData.set("pause-wallpaper", LustData.get("pause-wallpaper") + 1);
        wallpaperController.wallpaperPlayPause();
        wallpaperController.playPauseSetIcon();
      }
      if (event.target.closest("#next-bg")) {
        LustData.set("NextBg_Count", LustData.get("NextBg_Count") + 1);
        wallpaperController.nextWallpaper();
        if (LustData.get("NextBg_Count") >= 69 && LustData.get("NSFW-Content")) {
          LustData.set("NextBg_Count", 0);
        }
      }
      if (event.target.closest("#prev-bg")) {
        wallpaperController.prevWallpaper();
      }
    });
    this.makeDraggable(container);
    this.makeDraggable(wallpaperControls);
    if (!LustData.get("hide-homepage-navbar")) {
      container.style.transform = `translateX(212px)`;
      wallpaperControls.style.transform = `translateX(212px)`;
    }
  };
}
const mainController = new MainController();
class HideNavbarButton {
  checkNewContent = () => {
    if (!LustData.has("navbar-content"))
      LustData.set("navbar-content", []);
    let navbarContent = document.querySelectorAll(".activity-center__tab_content");
    navbarContent.forEach((element) => {
      const labelElement = element.querySelector(".activity-center__tab_label_display");
      if (labelElement && labelElement.innerText) {
        navbarContentList.push(labelElement.innerText);
      }
    });
    let set = new Set(LustData.get("navbar-content"));
    let set2 = new Set(navbarContentList);
    for (const element of navbarContentList) {
      if (!set.has(element)) {
        haveNewContent++;
      }
    }
    for (const element of LustData.get("navbar-content")) {
      if (!set2.has(element)) {
        haveNewContent++;
      }
    }
  };
  createHideButton = () => {
    const hideButton = document.createElement("div");
    const hideButtonIcon = document.createElement("img");
    const navbar = document.querySelector(".activity-center__tabs_container");
    const newContent = document.createElement("div");
    hideButton.setAttribute("class", "hide-navbar-button");
    hideButtonIcon.setAttribute("class", "hide-navbar-button-icon");
    newContent.setAttribute("class", "navbar-have-new-content");
    if (navbar) {
      navbar.appendChild(hideButton);
      hideButton.append(hideButtonIcon);
      hideButton.append(newContent);
    }
    if (haveNewContent > 0) {
      newContent.style.display = "block";
    }
    hideButton.addEventListener("click", () => {
      if (LustData.get("hide-homepage-navbar")) {
        LustData.set("hide-homepage-navbar", false);
      } else {
        LustData.set("hide-homepage-navbar", true);
      }
      this.hideShowNavBar();
      this.changeHomePageStyle();
      LustData.set("navbar-content", navbarContentList);
      newContent.style.display = "none";
    });
  };
  hideShowNavBar = () => {
    const navPersistent = document.querySelector(".activity-center__persistent-tab");
    const navScrollable = document.querySelector(".activity-center__tabs_scrollable");
    const navFooter = document.querySelector(".activity-center__tabs_footer");
    const navDivider = document.querySelector(".activity-center__tabs_section-divider");
    const hideButton = document.querySelector(".hide-navbar-button");
    const hideButtonIcon = document.querySelector(".hide-navbar-button-icon");
    if (LustData.get("hide-homepage-navbar")) {
      if (navPersistent)
        navPersistent.style.cssText = `transform: translateX(-212px); pointer-events: none;`;
      if (navScrollable)
        navScrollable.style.cssText = `transform: translateX(-212px); pointer-events: none;`;
      if (navFooter)
        navFooter.style.cssText = `transform: translateX(-212px); pointer-events: none;`;
      if (navDivider)
        navDivider.style.cssText = `transform: translateX(-212px); pointer-events: none;`;
      if (hideButton)
        hideButton.style.cssText = `transform: translateX(0px);`;
      if (hideButtonIcon)
        hideButtonIcon.setAttribute("src", `${iconFolder$3}plugins-icons/next_button.png`);
    } else {
      if (navPersistent)
        navPersistent.style.cssText = `transform: translateX(0px); pointer-events: auto;`;
      if (navScrollable)
        navScrollable.style.cssText = `transform: translateX(0px); pointer-events: auto;`;
      if (navFooter)
        navFooter.style.cssText = `transform: translateX(0px); pointer-events: auto;`;
      if (navDivider)
        navDivider.style.cssText = `transform: translateX(0px); pointer-events: auto;`;
      if (hideButton)
        hideButton.style.cssText = `transform: translateX(212px);`;
      if (hideButtonIcon)
        hideButtonIcon.setAttribute("src", `${iconFolder$3}plugins-icons/prev_button.png`);
    }
  };
  changeHomePageStyle = () => {
    const wallpaperController2 = document.querySelector(".wallpaper-controls");
    const audioController2 = document.querySelector(".webm-bottom-buttons-container");
    const activityCenter = document.querySelector("#activity-center > main");
    const activityCenterChinese = document.querySelector(".managed-iframe-wrapper > iframe");
    if (LustData.get("hide-homepage-navbar")) {
      if (activityCenter)
        activityCenter.style.cssText = `opacity: 0 !important; pointer-events: none !important;`;
      if (activityCenterChinese)
        activityCenterChinese.style.cssText = `opacity: 0; pointer-events: none;`;
      if (wallpaperController2)
        wallpaperController2.style.transform = `translateX(0px)`;
      if (audioController2)
        audioController2.style.transform = `translateX(0px)`;
    } else {
      if (activityCenter)
        activityCenter.style.cssText = `opacity: 1 !important; pointer-events: auto !important;`;
      if (activityCenterChinese)
        activityCenterChinese.style.cssText = `opacity: 1; pointer-events: auto;`;
      if (wallpaperController2)
        wallpaperController2.style.transform = `translateX(212px)`;
      if (audioController2)
        audioController2.style.transform = `translateX(212px)`;
    }
  };
  addHideButton = () => {
    observer.subscribeToElementCreation(".activity-center__tabs_footer", (element) => {
      if (document.querySelector(".hide-navbar-button"))
        return;
      try {
        let button = document.getElementsByClassName("hide-navbar-button");
        if (button.length > 1) {
          for (let i = 0; i < button.length; i++) {
            button[i].remove();
          }
        }
      } catch {
      }
      this.checkNewContent();
      this.createHideButton();
      this.hideShowNavBar();
    });
    observer.subscribeToElementCreation("#activity-center > main div", (element) => {
      this.changeHomePageStyle();
    });
    observer.subscribeToElementCreation(".activity-center-default-activity", (element) => {
      this.changeHomePageStyle();
    });
  };
}
const hideNavbarButton = new HideNavbarButton();
class HideTopNavbarButton {
  createHideButton = () => {
    const hideButton = document.createElement("div");
    const hideButtonIcon = document.createElement("img");
    const topNavbar = document.querySelector(".right-nav-menu");
    hideButton.setAttribute("class", "hide-top-navbar");
    hideButtonIcon.setAttribute("class", "hide-top-navbar-icon");
    if (topNavbar) {
      topNavbar.prepend(hideButton);
      hideButton.append(hideButtonIcon);
    }
    this.changeButtonIcon(LustData.get("hide-top-navbar"));
    hideButton.addEventListener("click", () => {
      if (LustData.get("hide-top-navbar")) {
        LustData.set("hide-top-navbar", false);
      } else {
        LustData.set("hide-top-navbar", true);
      }
      this.hideShowTopNavBar();
    });
  };
  changeButtonIcon = (isHidden) => {
    const hideButtonIcon = document.querySelector(".hide-top-navbar-icon");
    if (isHidden) {
      hideButtonIcon.setAttribute("src", `${iconFolder$3}plugins-icons/prev_button.png`);
    } else {
      hideButtonIcon.setAttribute("src", `${iconFolder$3}plugins-icons/next_button.png`);
    }
  };
  hideShowTopNavBar = () => {
    const navItem = document.querySelectorAll(".right-nav-menu > .main-navigation-menu-item");
    const verticalRule = document.querySelectorAll(".right-nav-vertical-rule");
    const walletBadge = document.querySelector(".wallet-and-badges");
    const hideButton = document.querySelector(".hide-top-navbar");
    try {
      let isHidden = LustData.get("hide-top-navbar");
      if (isHidden) {
        let nav = document.querySelector(".right-nav-menu");
        let navWidth = nav ? nav.offsetWidth : 0;
        if (hideButton) {
          hideButton.style.cssText = `transform: translateX(${navWidth - 40}px);`;
        }
        for (let i = 0; i < navItem.length; i++) {
          navItem[i].style.cssText = `
                        transform: translateX(${navWidth - 40}px);
                        opacity: 0;
                        pointer-events: none;
                    `;
          utils.freezeProperties(navItem[i].style, ["transform"]);
        }
        for (let i = 0; i < verticalRule.length; i++) {
          verticalRule[i].style.cssText = `
                        transform: translateX(${navWidth - 40}px);
                        opacity: 0;
                        pointer-events: none;
                    `;
          utils.freezeProperties(verticalRule[i].style, ["transform"]);
        }
        if (walletBadge) {
          walletBadge.style.cssText = `
                        transform: translateX(${navWidth - 40}px);
                        opacity: 0;
                        pointer-events: none;
                    `;
        }
      } else {
        if (hideButton) {
          hideButton.style.cssText = `transform: translateX(0px);`;
        }
        for (let i = 0; i < navItem.length; i++) {
          navItem[i].style.cssText = `
                        transform: translateX(0px);
                        opacity: 1;
                        pointer-events: auto;
                    `;
        }
        for (let i = 0; i < verticalRule.length; i++) {
          verticalRule[i].style.cssText = `
                        transform: translateX(0px);
                        opacity: 1;
                        pointer-events: auto;
                    `;
        }
        if (walletBadge) {
          walletBadge.style.cssText = `
                        transform: translateX(0px);
                        opacity: 1;
                        pointer-events: auto;
                    `;
        }
      }
      this.changeButtonIcon(isHidden);
    } catch (err) {
      error("Can't find top navigation bar", err);
    }
  };
  addHideButton = () => {
    observer.subscribeToElementCreation(".right-nav-menu > .main-navigation-menu-item", (element) => {
      if (document.querySelector(".hide-top-navbar"))
        return;
      try {
        let button = document.getElementsByClassName("hide-top-navbar");
        if (button.length > 1) {
          for (let i = 0; i < button.length; i++) {
            button[i].remove();
          }
        }
      } catch {
      }
      this.createHideButton();
      window.setTimeout(() => {
        this.hideShowTopNavBar();
      }, 2e3);
    });
  };
}
const hideTopNavbarButton = new HideTopNavbarButton();
class WallpaperAndAudio {
  videoAbortController = null;
  audioAbortController = null;
  // Add Wallpaper and Audio to client
  addWallpaperElement = () => {
    const video = document.createElement("video");
    video.id = "lust-bg";
    document.body.prepend(video);
  };
  addImageWallpaperElement = () => {
    const imgWallpaper = document.createElement("img");
    imgWallpaper.id = "lust-static-bg";
    document.body.prepend(imgWallpaper);
  };
  addAudioElement = () => {
    const audio = document.createElement("audio");
    audio.id = "bg-audio";
    document.body.prepend(audio);
  };
  setWallpaperElement = () => {
    if (!LustData.get("disable-theme-wallpaper")) {
      if (LustData.get("wallpaper-index") > LustData.get("Wallpaper-list").length - 1) {
        LustData.set("wallpaper-index", 0);
      }
      if (this.videoAbortController) {
        this.videoAbortController.abort();
      }
      this.videoAbortController = new AbortController();
      const videoSignal = this.videoAbortController.signal;
      const video = document.getElementById("lust-bg");
      video.autoplay = true;
      video.volume = LustData.get("wallpaper-volume");
      video.muted = LustData.get("mute-audio");
      video.currentTime = LustData.get("Wallpaper-currentTime");
      video.src = `${bgFolder$1}wallpapers/${LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]}`;
      video.playbackRate = LustData.get("Playback-speed") / 100;
      video.preload = "metadata";
      video.setAttribute("disablePictureInPicture", "");
      let savedTime = false;
      video.addEventListener("timeupdate", () => {
        if (!savedTime && parseInt(video.currentTime) % (LustData.get("WallpaperAudio-timeUpdate") / 1e3) == 0) {
          savedTime = true;
          LustData.set("Wallpaper-currentTime", parseInt(video.currentTime));
        } else
          savedTime = false;
      }, { signal: videoSignal });
      if (LustData.get("wallpaper-slideshow")) {
        video.loop = false;
        video.addEventListener("ended", () => {
          wallpaperController.nextWallpaper();
        }, { signal: videoSignal });
      } else
        video.loop = true;
    }
  };
  setImageWallpaperElement = () => {
    if (!LustData.get("disable-theme-wallpaper")) {
      const imgWallpaper = document.getElementById("lust-static-bg");
      imgWallpaper.preload = "metadata";
      imgWallpaper.src = `${bgFolder$1}wallpapers/${LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]}`;
      wallpaperController.wallpaperSlider(LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]);
    }
  };
  setAudioElement = () => {
    if (!LustData.get("disable-theme-audio")) {
      if (LustData.get("audio-index") > LustData.get("Audio-list").length - 1) {
        LustData.set("audio-index", 0);
      }
      if (this.audioAbortController) {
        this.audioAbortController.abort();
      }
      this.audioAbortController = new AbortController();
      const audioSignal = this.audioAbortController.signal;
      const audio = document.getElementById("bg-audio");
      audio.autoplay = true;
      audio.src = `${bgFolder$1}audio/${LustData.get("Audio-list")[LustData.get("audio-index")]}`;
      audio.volume = LustData.get("audio-volume");
      audio.muted = LustData.get("mute-audio");
      audio.currentTime = LustData.get("Audio-currentTime");
      audio.preload = "metadata";
      let savedTime = false;
      audio.addEventListener("timeupdate", () => {
        if (!savedTime && parseInt(audio.currentTime) % (LustData.get("WallpaperAudio-timeUpdate") / 1e3) == 0) {
          savedTime = true;
          LustData.set("Audio-currentTime", parseInt(audio.currentTime));
        } else
          savedTime = false;
      }, { signal: audioSignal });
      audioController.toggleAudioLoop();
      audio.addEventListener("error", () => audio.load(), { signal: audioSignal });
    }
  };
  loadWallpaperAndMusic() {
    const initializeUI = () => {
      if (document.querySelector(".rcp-fe-lol-home") || document.querySelector(".rcp-fe-lol-activity-center")) {
        log("Load wallpaper and audio");
        this.setWallpaperElement();
        this.setImageWallpaperElement();
        this.setAudioElement();
        utils.subscribe_endpoint("/lol-gameflow/v1/gameflow-phase", (message) => {
          const phase = JSON.parse(message["data"])[2]["data"];
          log(phase);
          if (phase === "GameStart" || phase === "InProgress") {
            if (LustData.get("turnoff-audio-ingame")) {
              const video = document.getElementById("lust-bg");
              const audio = document.getElementById("bg-audio");
              video.pause();
              audio.pause();
            }
          } else {
            wallpaperController.wallpaperPlayPause();
            audioController.audioPlayPause();
          }
        });
        changeHomePageTabs.deleteNavbarTab();
        clearInterval(initializationInterval);
      }
    };
    const initializationInterval = setInterval(initializeUI, 2e3);
  }
  logDebuggingInfo = () => {
    const loopWallCss = LustData.get("audio-loop") ? "color: #00ff44" : "color: red";
    const muteCss = LustData.get("mute-audio") ? "color: #00ff44" : "color: red";
    const pauseWall = LustData.get("pause-wallpaper") % 2 === 0 ? "color: #00ff44" : "color: red";
    const pauseAudio = LustData.get("pause-audio") % 2 === 0 ? "color: #00ff44" : "color: red";
    const lustBg = document.getElementById("lust-bg");
    log(`%cNow playing %c${LustData.get("Wallpaper-list")[LustData.get("wallpaper-index")]} %cand %c${LustData.get("Audio-list")[LustData.get("audio-index")]}`, "color: #e4c2b3", "color: #0070ff", "color: #e4c2b3", "color: #0070ff");
    log(`%ccurrent wallpaper status: pause: %c${LustData.get("pause-wallpaper") % 2 === 0}%c, play/pause-time: %c${LustData.get("pause-wallpaper")}%c, mute: %c${LustData.get("mute-audio")}%c, loop: %c${lustBg.loop}%c, volume: %c${LustData.get("wallpaper-volume") * 100}%`, "color: #e4c2b3", pauseWall, "color: #e4c2b3", "color: #0070ff", "color: #e4c2b3", muteCss, "color: #e4c2b3", "color: #00ff44", "color: #e4c2b3", "color: #0070ff");
    log(`%ccurrent audio status: pause: %c${LustData.get("pause-audio") % 2 === 0}%c, play/pause-time: %c${LustData.get("pause-audio")}%c, mute: %c${LustData.get("mute-audio")}%c, loop: %c${LustData.get("audio-loop")}%c, volume: %c${LustData.get("audio-volume") * 100}%`, "color: #e4c2b3", pauseAudio, "color: #e4c2b3", "color: #0070ff", "color: #e4c2b3", muteCss, "color: #e4c2b3", loopWallCss, "color: #e4c2b3", "color: #0070ff");
  };
}
const wallpaperAndAudio = new WallpaperAndAudio();
class AddHomePage {
  setActivityCenterMusicStatus = async (bool) => {
    let body = {
      "schemaVersion": 5,
      "data": {
        "clientAmbienceMusicEnabled": bool
      }
    };
    await fetch("/lol-settings/v1/local/lol-audio", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
  };
  pageListenner = async (node) => {
    const pagename = node.getAttribute("data-screen-name");
    const isOtherPage = ![
      "rcp-fe-lol-home-main",
      "window-controls",
      "rcp-fe-lol-navigation-screen",
      "social",
      "rcp-fe-lol-activity-center-main"
    ].includes(pagename);
    if (!isOtherPage) {
      if (!addedBackgrounds) {
        addedBackgrounds = true;
        wallpaperAndAudio.loadWallpaperAndMusic();
        wallpaperAndAudio.logDebuggingInfo();
        observer.subscribeToElementCreation(".tft-sub-nav-container span", (element) => {
          changeHomePageTabs.deleteNavbarTab();
        });
      }
      if (!document.querySelector(".webm-bottom-buttons-container") && !document.querySelector(".webm-bottom-buttons-container-hovered")) {
        mainController.deleteController();
        mainController.createMainController();
        document.querySelector(".webm-bottom-buttons-container")?.setAttribute("class", "webm-bottom-buttons-container-hovered");
        window.setTimeout(() => {
          document.querySelector(".webm-bottom-buttons-container-hovered")?.setAttribute("class", "webm-bottom-buttons-container");
        }, 6e3);
        hideNavbarButton.hideShowNavBar();
        hideNavbarButton.changeHomePageStyle();
      }
      changeHomePageTabs.deleteNavbarTab();
    } else if (isOtherPage && document.querySelector(".webm-bottom-buttons-container") && pagename != "rcp-fe-lol-info-hub") {
      mainController.deleteController();
      this.setActivityCenterMusicStatus(true);
    }
    if (!isOtherPage || pagename === "rcp-fe-lol-postgame" || pagename === "rcp-fe-lol-info-hub") {
      this.setActivityCenterMusicStatus(false);
    }
  };
}
const addHomePage = new AddHomePage();
class WindowEffects {
  effectsWithColor = /* @__PURE__ */ new Set(["transparent", "blurbehind", "acrylic", "unified"]);
  normalizeColorBase = (color) => /^#[0-9a-f]{6}$/i.test(color) ? color : "#ffffff";
  normalizeAlpha = (alpha) => /^[0-9a-f]{2}$/i.test(alpha) ? alpha.toLowerCase() : "00";
  normalizeEffectName = (effect) => {
    const validEffects = ["transparent", "blurbehind", "acrylic", "unified", "mica", "vibrancy"];
    return validEffects.includes(effect) ? effect : "transparent";
  };
  normalizeWindowEffect = () => {
    const name = this.normalizeEffectName(LustData.get("window-effect-name"));
    const colorBase = this.normalizeColorBase(LustData.get("window-effect-color-base"));
    const alpha = this.normalizeAlpha(LustData.get("window-effect-alpha"));
    const color = `${colorBase}${alpha}`;
    const material = LustData.get("window-effect-material") || "none";
    if (LustData.get("window-effect-color") !== color) {
      LustData.set("window-effect-color", color);
    }
    return { name, color, material };
  };
  buildWindowEffectOptions = (effect = this.normalizeWindowEffect()) => {
    const options = {};
    if (this.effectsWithColor.has(effect.name)) {
      options.color = effect.color;
    }
    if ((effect.name === "mica" || effect.name === "vibrancy") && effect.material && effect.material !== "none") {
      options.material = effect.material;
    }
    return options;
  };
  applyWindowEffect = () => {
    if (!window.Effect)
      return;
    if (!LustData.get("disable-theme-wallpaper")) {
      window.Effect.clear();
      return;
    }
    const effect = this.normalizeWindowEffect();
    const options = this.buildWindowEffectOptions(effect);
    if (Object.keys(options).length > 0) {
      window.Effect.apply(effect.name, options);
    } else {
      window.Effect.apply(effect.name);
    }
  };
  setSettingsVisibility = () => {
    const row = document.getElementById("window-effects-settings");
    if (!row)
      return;
    row.style.display = LustData.get("disable-theme-wallpaper") ? "" : "none";
  };
}
const windowEffects = new WindowEffects();
class HomePage {
  main = () => {
    initHomepageData();
    windowEffects.applyWindowEffect();
    window.setTimeout(updateSummonerIdentity, 7e3);
    log("Add wallpaper and audio");
    wallpaperAndAudio.addWallpaperElement();
    wallpaperAndAudio.addImageWallpaperElement();
    wallpaperAndAudio.addAudioElement();
    utils.mutationObserverAddCallback(addHomePage.pageListenner, ["screen-root"]);
    hideNavbarButton.addHideButton();
    if (false) {
      hideTopNavbarButton.addHideButton();
    }
  };
}
const del_webm_buttons = mainController.deleteController;
const create_webm_buttons = mainController.createMainController;
const applyHideAndShowTFTtab = changeHomePageTabs.applyHideAndShowTFTtab;
const setWallpaper = wallpaperAndAudio.setWallpaperElement;
const setImageWallpaper = wallpaperAndAudio.setImageWallpaperElement;
const setAudio = wallpaperAndAudio.setAudioElement;
const hideShowNavBar = hideNavbarButton.hideShowNavBar;
const changeHomePageStyle = hideNavbarButton.changeHomePageStyle;
const wallpaperPlayPause = wallpaperController.wallpaperPlayPause;
const audioPlayPause = audioController.audioPlayPause;
const applyWindowEffect = windowEffects.applyWindowEffect;
const setWindowEffectsSettingsVisibility = windowEffects.setSettingsVisibility;

async function infoSection() {
  const themeLanguageOptions = [
    { label: await getString("theme-settings.theme-language-client"), value: "client" },
    { label: "English", value: "default" },
    { label: "Tiếng Việt", value: "vi-VN" },
    { label: "Русский", value: "ru-RU" },
    { label: "中文", value: "zh-CN" },
    { label: "Türkçe", value: "tr-TR" }
  ];
  return [
    UI.createRow("Info", [
      UI.createRow("Info-div", [
        UI.createLink(
          "Lust",
          "https://github.com/lustmyself/Lust",
          () => {
          },
          "theme-link"
        ),
        UI.createLabel(
          `*${await getString("settings.note")}: ${await getString("settings.note-1")}`,
          ""
        )
      ]),
      UI.createImage(true, "logo.png", "theme-settings-logo")
    ]),
    UI.createCheckBox(
      `${await getString("theme-settings.allowtrackingdata")}`,
      "trackData",
      "trackDatabox",
      () => {
        restartAfterChange("trackData", "AllowTrackingData");
      },
      true,
      "AllowTrackingData"
    ),
    UI.createDropdown(
      themeLanguageOptions,
      LustData.get("Theme-language"),
      {
        title: await getString("theme-settings.theme-language"),
        id: "theme-language-dropdown",
        datastoreKey: "Theme-language",
        onChange: () => {
          restartAfterChange("theme-language-dropdown", "Theme-language");
        }
      }
    )
  ];
}

const fileRegex = {
  Wallpaper: /\.(png|jpg|jpeg|gif|bmp|webp|ico|mp4|webm|mkv|mov|avi|wmv|3gp|m4v)$/,
  Audio: /\.(mp3|flac|ogg|wav|aac)$/,
  Font: /\.(ttf|otf|woff|woff2)$/,
  Banner: /\.(png|jpg|jpeg|gif|bmp|webp|ico)$/
};

const assetLocaleKeys = {
  wallpaper: "theme-settings.wallpaper",
  audio: "theme-settings.audio",
  banner: "theme-settings.banner",
  font: "theme-settings.font"
};
const assetMessageLocaleKeys = {
  wallpaper: {
    invalid: "theme-settings.invalid-wallpaper-format",
    added: "theme-settings.wallpaper-added",
    alreadyAdded: "theme-settings.wallpaper-already-added",
    deleted: "theme-settings.wallpaper-deleted",
    notExist: "theme-settings.wallpaper-not-exist"
  },
  audio: {
    invalid: "theme-settings.invalid-audio-format",
    added: "theme-settings.audio-added",
    alreadyAdded: "theme-settings.audio-already-added",
    deleted: "theme-settings.audio-deleted",
    notExist: "theme-settings.audio-not-exist"
  },
  banner: {
    invalid: "theme-settings.invalid-banner-format",
    added: "theme-settings.banner-added",
    alreadyAdded: "theme-settings.banner-already-added",
    deleted: "theme-settings.banner-deleted",
    notExist: "theme-settings.banner-not-exist"
  },
  font: {
    invalid: "theme-settings.invalid-font-format",
    added: "theme-settings.font-added",
    alreadyAdded: "theme-settings.font-already-added",
    deleted: "theme-settings.font-deleted",
    notExist: "theme-settings.font-not-exist"
  }
};
// Lust: the asset library shows each folder's files (Lust lists them over the
// bridge, since Pengu 1.1.6 plugins can't), Add opens the folder, x deletes a file,
// and files dropped on a row are copied into its folder.
const LUST_ASSET_CHUNK = 512 * 1024;
const lustAssetWaiters = new Map();
let lustAssetRequests = 0;
let lustAssetsSubscribed = false;
function lustAssets(kind, action, extra = {}) {
  const bridge = window.__lustBridge;
  if (!bridge) return Promise.resolve({ error: lustTr("Lust isn't connected"), files: null });
  if (!lustAssetsSubscribed) {
    lustAssetsSubscribed = true;
    bridge.subscribe("lust-assets", (reply) => {
      const waiter = lustAssetWaiters.get(reply && reply.requestId);
      if (waiter) {
        lustAssetWaiters.delete(reply.requestId);
        waiter(reply);
      }
    });
  }
  const requestId = `${Date.now()}-${++lustAssetRequests}`;
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      lustAssetWaiters.delete(requestId);
      resolve({ error: lustTr("Lust didn't answer"), files: null });
    }, 15000);
    lustAssetWaiters.set(requestId, (reply) => {
      clearTimeout(timer);
      resolve(reply);
    });
    bridge.send({ type: "lust-assets", kind, action, requestId, ...extra });
  });
}
function lustBlobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}
async function uploadLustAsset(kind, file) {
  const total = Math.max(1, Math.ceil(file.size / LUST_ASSET_CHUNK));
  for (let index = 0; index < total; index++) {
    const data = await lustBlobToBase64(file.slice(index * LUST_ASSET_CHUNK, (index + 1) * LUST_ASSET_CHUNK));
    const reply = await lustAssets(kind, "save", { name: file.name, index, total, data });
    if (reply.error) return reply;
  }
  return lustAssets(kind, "list");
}
// Keeps the theme's list in the folder's order of discovery: known files first.
function syncLustAssetList(dataKey, files) {
  const current = LustData.get(dataKey) || [];
  const next = current.filter((name) => files.includes(name)).concat(files.filter((name) => !current.includes(name)));
  LustData.set(dataKey, next);
  if (dataKey === "Wallpaper-list" && LustData.get("wallpaper-index") >= next.length)
    LustData.set("wallpaper-index", 0);
  if (dataKey === "Audio-list" && LustData.get("audio-index") >= next.length)
    LustData.set("audio-index", 0);
  return next;
}
async function createFileListRow(type, dataKey, inputKey, regex) {
  // The theme needs at least one wallpaper and one audio file
  const keepOne = type === "wallpaper" || type === "audio";
  const row = document.createElement("div");
  row.className = "lust-asset-row";
  const head = document.createElement("div");
  head.className = "lust-asset-head";
  const title = document.createElement("span");
  title.textContent = await getString(assetLocaleKeys[type]);
  const add = document.createElement("lol-uikit-flat-button");
  add.textContent = lustTr("Add");
  add.addEventListener("click", () => lustAssets(type, "open"));
  head.append(title, add);
  const list = document.createElement("div");
  list.className = "lust-asset-list";
  const hint = document.createElement("div");
  hint.className = "lust-asset-hint";
  row.append(head, list, hint);
  const idleHint = lustTr("Drop files here, or Add to open the folder");
  let names = LustData.get(dataKey) || [];
  const show = (files, error) => {
    if (Array.isArray(files))
      names = syncLustAssetList(dataKey, files);
    list.replaceChildren(...names.map((name) => {
      const chip = document.createElement("span");
      chip.className = "lust-asset-chip";
      chip.textContent = name;
      const remove = document.createElement("span");
      remove.className = "lust-asset-remove";
      remove.textContent = "\u00d7";
      remove.title = lustTr("Delete");
      remove.addEventListener("click", async () => {
        if (keepOne && names.length <= 1) {
          hint.textContent = lustTr("Keep at least one");
          return;
        }
        const reply = await lustAssets(type, "delete", { name });
        show(reply.files, reply.error);
      });
      chip.appendChild(remove);
      return chip;
    }));
    hint.textContent = error || idleHint;
    hint.classList.toggle("error", !!error);
  };
  show(null, "");
  row.addEventListener("dragover", (event) => {
    event.preventDefault();
    row.classList.add("dragging");
  });
  row.addEventListener("dragleave", () => row.classList.remove("dragging"));
  row.addEventListener("drop", async (event) => {
    event.preventDefault();
    row.classList.remove("dragging");
    for (const file of Array.from(event.dataTransfer.files || [])) {
      if (!regex.test(file.name.toLowerCase())) {
        show(null, lustTr("{name} isn't a {type} file", { name: file.name, type: title.textContent.toLowerCase() }));
        continue;
      }
      hint.textContent = lustTr("Adding {name}...", { name: file.name });
      const reply = await uploadLustAsset(type, file);
      show(reply.files, reply.error);
    }
  });
  // Files pasted into the folder show up when the player comes back to the client
  const refresh = async () => {
    if (!document.body.contains(row)) {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
      return;
    }
    const reply = await lustAssets(type, "list");
    if (Array.isArray(reply.files)) show(reply.files, reply.error);
  };
  const timer = setInterval(refresh, 4000);
  window.addEventListener("focus", refresh);
  setTimeout(refresh, 0);
  return [row];
}
async function assetLibrarySection() {
  return UI.createSection("theme-settings-asset-library", await getString("theme-settings.settings-section-asset-library"), [
    ...await createFileListRow("wallpaper", "Wallpaper-list", "manual-wallpaper-name", fileRegex.Wallpaper),
    ...await createFileListRow("audio", "Audio-list", "manual-audio-name", fileRegex.Audio),
    ...await createFileListRow("banner", "Banner-list", "manual-banner-name", fileRegex.Banner),
    ...await createFileListRow("font", "Font-list", "manual-font-name", fileRegex.Font)
  ]);
}

const windowEffectList = {
  "window-effect-name": [
    { name: "transparent", id: "transparent" },
    { name: "blurbehind", id: "blurbehind" },
    { name: "acrylic", id: "acrylic" },
    { name: "unified", id: "unified" },
    { name: "mica", id: "mica" },
    { name: "vibrancy", id: "vibrancy" }
  ],
  "window-effect-material": [
    { name: "none", id: "none" },
    { name: "auto", id: "auto" },
    { name: "mica", id: "mica" },
    { name: "acrylic", id: "acrylic" },
    { name: "tabbed", id: "tabbed" },
    { name: "appearance-based", id: "appearance-based" },
    { name: "light", id: "light" },
    { name: "dark", id: "dark" },
    { name: "titlebar", id: "titlebar" },
    { name: "selection", id: "selection" },
    { name: "menu", id: "menu" },
    { name: "popover", id: "popover" },
    { name: "sidebar", id: "sidebar" },
    { name: "header", id: "header" },
    { name: "sheet", id: "sheet" },
    { name: "window", id: "window" },
    { name: "hud-window", id: "hud-window" },
    { name: "fullscreen-ui", id: "fullscreen-ui" },
    { name: "tooltip", id: "tooltip" },
    { name: "content-background", id: "content-background" },
    { name: "under-window-background", id: "under-window-background" },
    { name: "under-page-background", id: "under-page-background" }
  ]
};

function createSpeedInput(Datastore) {
  const { origin, searchbox } = UI.createInputElement(
    Datastore,
    "margin-bottom: 12px; width: 190px;",
    async () => {
      let input = {
        get value() {
          return searchbox.value;
        }
      };
      let speedCheck = document.getElementById("speed-check");
      if (input.value >= 6.25 && input.value <= 300) {
        LustData.set(Datastore, input.value);
        speedCheck.textContent = "";
        speedCheck.style.color = "";
      } else {
        speedCheck.textContent = await getString("theme-settings.speed-check-deny");
        speedCheck.style.color = "red";
      }
      let bg = document.getElementById("lust-bg");
      bg.playbackRate = LustData.get("Playback-speed") / 100;
    }
  );
  return origin;
}
async function windowEffectsRow() {
  return UI.createRow("window-effects-settings", [
    UI.createLabel(await getString("theme-settings.window-effects"), "", "theme-settings-subsection-title"),
    UI.createRow("window-effect-main-row", [
      UI.createDropdown(
        windowEffectList["window-effect-name"].map((o) => ({ label: o.name, value: o.id })),
        LustData.get("window-effect-name"),
        {
          title: await getString("theme-settings.window-effect-name"),
          id: "window-effect-name-dropdown",
          datastoreKey: "window-effect-name",
          onChange: () => applyWindowEffect()
        }
      ),
      UI.createRow("window-effect-color-row", [
        UI.createLabel(await getString("theme-settings.window-effect-color"), ""),
        UI.colorPicker("window-effect-color-picker", "window-effect-color-base", () => {
          const input = document.getElementById("window-effect-color-picker");
          const label = document.getElementById("window-effect-color-text");
          if (!input)
            return;
          LustData.set("window-effect-color-base", input.value);
          LustData.set("window-effect-color", input.value + LustData.get("window-effect-alpha"));
          if (label)
            label.textContent = LustData.get("window-effect-color");
          applyWindowEffect();
        }),
        UI.createLabel(LustData.get("window-effect-color"), "window-effect-color-text")
      ])
    ]),
    UI.opacitySlider("window-effect-opacity", await getString("theme-settings.opacity"), "window-effect-alpha", async () => {
      const slider = document.getElementById("window-effect-opacity");
      const title = document.getElementById("window-effect-opacity-title");
      const label = document.getElementById("window-effect-color-text");
      if (!slider)
        return;
      LustData.set("window-effect-alpha", Math.round(slider.value / 100 * 255).toString(16).padStart(2, "0"));
      LustData.set("window-effect-color", LustData.get("window-effect-color-base") + LustData.get("window-effect-alpha"));
      if (title)
        title.textContent = `${await getString("theme-settings.opacity")}: ${slider.value}%`;
      if (label)
        label.textContent = LustData.get("window-effect-color");
      applyWindowEffect();
    }),
    UI.createDropdown(
      windowEffectList["window-effect-material"].map((o) => ({ label: o.name, value: o.id })),
      LustData.get("window-effect-material"),
      {
        title: await getString("theme-settings.window-effect-material"),
        id: "window-effect-material-dropdown",
        datastoreKey: "window-effect-material",
        onChange: () => applyWindowEffect()
      }
    )
  ], true);
}
async function wallpaperSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-wallpaper", await getString("theme-settings.settings-section-wallpaper"), [
    UI.createButton(await getString("theme-settings.open-background-folder"), "open-background-folder", () => {
      window.openPluginsFolder(`${LustData.get("Plugin-folder-name")}/assets/backgrounds`);
    }),
    UI.createLabel(await getString("theme-settings.wallpaperaudio-timeupdate"), ""),
    UI.createSearchBox("WallpaperAudio-timeUpdate"),
    br(),
    UI.createSlider(
      await getString("theme-settings.wallpaper-volume"),
      LustData.get("wallpaper-volume") * 100,
      (value) => {
        const audio = document.getElementById("lust-bg");
        if (audio)
          audio.volume = value / 100;
        LustData.set("wallpaper-volume", value / 100);
      }
    ),
    UI.createRow("changePlaybackRow", [
      UI.createLabel(await getString("theme-settings.wallpaper-speed"), ""),
      createSpeedInput("Playback-speed"),
      UI.createLabel("%", "playback-percent")
    ]),
    UI.createLabel("", "speed-check"),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.old-prev-next-button")}`,
      "oldpnb",
      "oldpnbbox",
      () => {
        del_webm_buttons();
        create_webm_buttons();
      },
      true,
      "old-prev/next-button"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.wallpaper-slideshow")}`,
      "wallpaperSlide",
      "wallpaperSlidebox",
      () => {
        restartAfterChange("wallpaperSlide", "wallpaper-slideshow");
      },
      true,
      "wallpaper-slideshow"
    ),
    UI.createRow("slideTimeRow", [
      UI.createLabel(await getString("theme-settings.change-slide-delay"), ""),
      UI.createSearchBox("wallpaper-change-slide-time")
    ]),
    UI.createCheckBox(
      `${await getString("theme-settings.disable-theme-wallpaper")}`,
      "disablethemewallpaper",
      "disablethemewallpaperbox",
      () => {
        let wallpaperController = document.querySelector(".wallpaper-controls");
        let video = document.getElementById("lust-bg");
        let imgWallpaper = document.getElementById("lust-static-bg");
        if (!LustData.get("disable-theme-wallpaper")) {
          setWallpaper();
          setImageWallpaper();
          wallpaperPlayPause();
          if (wallpaperController)
            wallpaperController.style.display = "flex";
        } else {
          if (video)
            video.src = "";
          if (imgWallpaper)
            imgWallpaper.src = "";
          if (wallpaperController)
            wallpaperController.style.display = "none";
        }
        setWindowEffectsSettingsVisibility();
        applyWindowEffect();
      },
      true,
      "disable-theme-wallpaper"
    ),
    await windowEffectsRow()
  ]);
}

async function audioSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-audio", await getString("theme-settings.settings-section-audio"), [
    UI.createSlider(
      await getString("theme-settings.music-volume"),
      LustData.get("audio-volume") * 100,
      (value) => {
        const audio = document.getElementById("bg-audio");
        if (audio)
          audio.volume = value / 100;
        LustData.set("audio-volume", value / 100);
      }
    ),
    UI.createCheckBox(
      `${await getString("theme-settings.turnoff-audio-ingame")}`,
      "offaudio",
      "offaudiobox",
      () => {
      },
      true,
      "turnoff-audio-ingame"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.disable-theme-audio")}`,
      "disablethemeaudio",
      "disablethemeaudiobox",
      () => {
        let audioController = document.querySelector(".webm-bottom-buttons-container");
        let audio = document.getElementById("bg-audio");
        if (!LustData.get("disable-theme-audio")) {
          setAudio();
          audioPlayPause();
          if (audioController)
            audioController.style.display = "flex";
        } else {
          if (audio)
            audio.src = "";
          if (audioController)
            audioController.style.display = "none";
        }
      },
      true,
      "disable-theme-audio"
    )
  ]);
}

async function updatesSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-updates", await getString("theme-settings.settings-section-updates"), [
    UI.createCheckBox(
      `${await getString("theme-settings.prevent-manual-update")}`,
      "prvtup",
      "prvtupbox",
      () => {
      },
      true,
      "prevent-manual-update"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.holiday-message")}`,
      "holiday",
      "holidaybox",
      () => {
        restartAfterChange("holiday", "holiday-message");
      },
      true,
      "holiday-message"
    )
  ]);
}

async function customAssetsSection() {
  const br = () => document.createElement("br");
  function createBannerDropdown() {
    const items = LustData.get("Banner-list").map((b) => ({
      label: b,
      value: b
    }));
    return UI.createDropdown(items, LustData.get("CurrentBanner"), {
      datastoreKey: "CurrentBanner"
    });
  }
  return UI.createSection("theme-settings-custom-assets", await getString("theme-settings.settings-section-custom-assets"), [
    UI.createCheckBox(
      await getString("theme-settings.sync-user-icons"),
      "syncusericons",
      "syncusericonsbox",
      () => {
        restartAfterChange("syncusericons", "sync-user-icons");
      },
      true,
      "sync-user-icons"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.custom-icon")}`,
      "cusicon",
      "cusiconbox",
      () => {
        restartAfterChange("cusicon", "Custom-Icon");
      },
      true,
      "Custom-Icon"
    ),
    UI.createRowHideable("Custom-icon-list", [
      br(),
      UI.createCheckBox(
        `${await getString("theme-settings.custom-loading-icon")}`,
        "cusloadicon",
        "cusloadiconbox",
        () => {
          restartAfterChange("cusloadicon", "Custom-Loading-Icon");
        },
        true,
        "Custom-Loading-Icon"
      ),
      br(),
      br(),
      UI.createCheckBox(
        `${await getString("theme-settings.custom-gamemode-icon")}`,
        "cusgameicon",
        "cusgameiconbox",
        () => {
          restartAfterChange("cusgameicon", "Custom-Gamemode-Icon");
        },
        true,
        "Custom-Gamemode-Icon"
      ),
      br(),
    ]),
    UI.createCheckBox(
      `${await getString("theme-settings.animate-loading")}`,
      "aniload",
      "aniloadbox",
      () => {
      },
      true,
      "animate-loading"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.custom-runes-bg")}`,
      "rsbg",
      "rsbgbox",
      () => {
        restartAfterChange("rsbg", "Runes-BG");
      },
      true,
      "Runes-BG"
    ),
    br(),
    UI.createCheckBox(
      await getString("theme-settings.custom-champs-image"),
      "cuschampimg",
      "cuschampimgbox",
      () => {
        restartAfterChange("cuschampimg", "custom-champs-image");
      },
      true,
      "custom-champs-image"
    )
  ]);
}

async function interfaceSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-interface", await getString("theme-settings.settings-section-interface"), [
    UI.createCheckBox(
      `${await getString("theme-settings.hide-homepage-navbar")}`,
      "homenav",
      "homenavbox",
      () => {
        hideShowNavBar();
        changeHomePageStyle();
      },
      true,
      "hide-homepage-navbar"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.enable-hide-top-navbar-friendlist-button")}`,
      "hidetopnavfriend",
      "hidetopnavfriendbox",
      () => {
        restartAfterChange("hidetopnavfriend", "enable-hide-top-navbar-friendlist-button");
      },
      true,
      "enable-hide-top-navbar-friendlist-button"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.sidebar-transparent")}`,
      "sbt",
      "sbtbox",
      () => {
        restartAfterChange("sbt", "sidebar-transparent");
      },
      true,
      "sidebar-transparent"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.lobby-transparent-filter")}`,
      "ltf",
      "ltfbox",
      () => {
        restartAfterChange("ltf", "lobby-transparent-filter");
      },
      true,
      "lobby-transparent-filter"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.settings-dialogs-transparent")}`,
      "stdiat",
      "stdiatbox",
      () => {
        restartAfterChange("stdiat", "settings-dialogs-transparent");
      },
      true,
      "settings-dialogs-transparent"
    ),
    br(),
    UI.createCheckBox(
      await getString("theme-settings.hide-profile-background"),
      "hideprfbg",
      "hideprfbgbox",
      () => {
        restartAfterChange("hideprfbg", "hide-profile-background");
      },
      true,
      "hide-profile-background"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-champions-splash-art")}`,
      "hidechampart",
      "hidechampartbox",
      () => {
        restartAfterChange("hidechampart", "hide-champions-splash-art");
      },
      true,
      "hide-champions-splash-art"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-vertical-lines")}`,
      "hidevl",
      "hidevlbox",
      () => {
        restartAfterChange("hidevl", "hide-vertical-lines");
      },
      true,
      "hide-vertical-lines"
    )
  ]);
}

let icdata$3 = (await import(`//plugins/${getThemeName()}/config/icons.js`)).default;
let datapath$6 = `//plugins/${getThemeName()}/`;
let iconFolder$2 = `${datapath$6}assets/icon/`;
let bgFolder = `${datapath$6}assets/backgrounds/`;
class AddCss {
  cssVar = () => {
    utils.addStyleNode(
      /*css*/
      `
			:root {
				--classic_def: url("${iconFolder$2}gamemodes/${icdata$3["classic_def"]}");
				--classic_act: url("${iconFolder$2}gamemodes/${icdata$3["classic_act"]}");
				--aram_def: url("${iconFolder$2}gamemodes/${icdata$3["aram_def"]}");
				--aram_act: url("${iconFolder$2}gamemodes/${icdata$3["aram_act"]}");
				--tft_def: url("${iconFolder$2}gamemodes/${icdata$3["tft_def"]}");
				--tft_act: url("${iconFolder$2}gamemodes/${icdata$3["tft_act"]}");
				--cherry_def: url("${iconFolder$2}gamemodes/${icdata$3["cherry_def"]}");
				--cherry_act: url("${iconFolder$2}gamemodes/${icdata$3["cherry_act"]}");
				--brawl_def: url("${iconFolder$2}gamemodes/${icdata$3["brawl_def"]}");
				--brawl_act: url("${iconFolder$2}gamemodes/${icdata$3["brawl_act"]}");

				--pri8000: url("${bgFolder}runes/${icdata$3["Precision"]}");
				--pri8100: url("${bgFolder}runes/${icdata$3["Domination"]}");
				--pri8200: url("${bgFolder}runes/${icdata$3["Sorcery"]}");
				--pri8300: url("${bgFolder}runes/${icdata$3["Inspiration"]}");
				--pri8400: url("${bgFolder}runes/${icdata$3["Resolve"]}");

				--Loading: url("${iconFolder$2}${icdata$3["Loading"]}");
				--Avatar: url("${iconFolder$2}${icdata$3["Avatar"]}");
				--RP-Icon: url("${iconFolder$2}${icdata$3["RP-icon"]}");
				--BE-Icon: url("${iconFolder$2}${icdata$3["BE-icon"]}");
				--Rank-Icon: url("${iconFolder$2}${icdata$3["Rank-icon"]}");
				--Clash-banner: url("${iconFolder$2}${icdata$3["Class-banner"]}");
				--Ticker: url("${iconFolder$2}${icdata$3["Ticker"]}");
				--Trophy: url("${iconFolder$2}${icdata$3["Trophy"]}");
				--Border: url("${iconFolder$2}${icdata$3["Border"]}");
				--LustFly: url("${iconFolder$2}${icdata$3["Animation-logo"]}");
				--LustStatic: url("${iconFolder$2}${icdata$3["Static-logo"]}");
				--Hover-card-backdrop: url("${iconFolder$2}${icdata$3["Hover-card"]}");
			}
		`
    );
  };
  mainThemeCss = () => {
    utils.addStyleNode(
      `
			@import url("${datapath$6}assets/styles/themes/lust.css");
			@font-face {
				font-family: 'Lust';
				src: url('${datapath$6}assets/fonts/beaufortforlol-bold.ttf')
			}`
    );
  };
  componentsCss = () => {
    let cssImports = "";
    let addonCssList = {
      "componentsCss": [
        {
          key: "hide-vertical-lines",
          css: "hide-vertical-lines.css",
          altCss: "null.css"
        },
        {
          key: "aram-only",
          css: "aram-only.css",
          altCss: "null.css"
        },
        {
          key: "hide-champions-splash-art",
          css: "hide-champs-splash-art.css",
          altCss: "null.css"
        },
        {
          key: "hide-profile-background",
          css: "hide-profile-background.css",
          altCss: "null.css"
        },
        {
          key: "animate-loading",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "custom-navbar-css",
          css: "customNavbar.css",
          altCss: "null.css"
        },
        {
          key: "lobby-transparent-filter",
          css: "lobby-transparent-filter.css",
          altCss: "null.css"
        },
        {
          key: "sidebar-transparent",
          css: "sidebar-transparent.css",
          altCss: "sidebar-color.css"
        }
      ],
      "iconCss": [
        {
          key: "Custom-Avatar",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-RP-Icon",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Clash-banner",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-BE-Icon",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Rank-Icon",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Emblem",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Ticker",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Trophy",
          css: "null.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Gamemode-Icon",
          css: "gamemodes.css",
          altCss: "null.css"
        },
        {
          key: "Custom-Loading-Icon",
          css: "null.css",
          altCss: "null.css"
        }
      ]
    };
    for (const groupKey in addonCssList) {
      addonCssList[groupKey].forEach(({ key, css, altCss }) => {
        let cssPath = LustData.get(key) ? css : altCss;
        if (cssPath && groupKey == "iconCss" && LustData.get("Custom-Icon") || cssPath && groupKey == "componentsCss") {
          cssImports += `@import url("${datapath$6}assets/styles/components/${cssPath}");
`;
        }
      });
    }
    utils.addStyleNode(cssImports);
  };
  customFont = () => {
    document.getElementById("Custom-font")?.remove();
    if (!LustData.get("lust-default-font-reset")) {
      LustData.set("lust-default-font-reset", true);
      LustData.set("Custom-Font", false);
    }
    if (!LustData.get("Custom-Font")) {
      return;
    }
    if (LustData.get("Custom-Font-Google")) {
      const googleFont = utils.getSafeGoogleFont(LustData.get("Google-Font-Url"));
      if (!googleFont)
        return;
      utils.addStyleNodeWithID(
        "Custom-font",
        /*css*/
        `
				@import url("${utils.escapeCssString(googleFont.url.toString())}");
				:root {
					--font-display: "${utils.escapeCssString(googleFont.family)}", 'LoL Display', 'Lust', 'Times New Roman', Times, Baskerville, Georgia, serif !important;
					--font-body: "${utils.escapeCssString(googleFont.family)}", 'LoL Body', 'Lust', Arial, 'Helvetica Neue', Helvetica, sans-serif !important;
				}
			`
      );
      return;
    }
    utils.addFont(`${datapath$6}assets/fonts/${LustData.get("CurrentFont")}`, "Custom-font", "Custom");
  };
  customCursor = () => {
    utils.CustomCursor(`url("${iconFolder$2}${icdata$3["Mouse-cursor"]}")`, `@import url("${datapath$6}assets/styles/components/cursor.css")`);
  };
  customNicknameColor = () => {
    utils.addStyleNodeWithID(
      "nickname-color-css",
      /*css*/
      `
			span.player-name__force-locale-text-direction, #nickname-color-preview {
				color: ${utils.sanitizeColor(LustData.get("nickname-color-with-opacity"))};
			}
		`
    );
  };
}
const addCss = new AddCss();
class LoadCss {
  main = () => {
    addCss.mainThemeCss();
    addCss.componentsCss();
    addCss.cssVar();
    if (LustData.get("Custom-Font"))
      addCss.customFont();
    if (LustData.get("Custom-Cursor"))
      addCss.customCursor();
    if (false)
      addCss.customNicknameColor();
  };
}

function syncExclusiveFontMode(mode) {
  LustData.set("Custom-Font-Local", mode === "local");
  LustData.set("Custom-Font-Google", mode === "google");
  const localBox = document.getElementById("cusfontlocalbox");
  const googleBox = document.getElementById("cusfontgooglebox");
  const localOrigin = document.getElementById("cusfontlocal");
  const googleOrigin = document.getElementById("cusfontgoogle");
  if (localBox)
    localBox.checked = mode === "local";
  if (googleBox)
    googleBox.checked = mode === "google";
  if (localOrigin)
    localOrigin.classList.toggle("checked", mode === "local");
  if (googleOrigin)
    googleOrigin.classList.toggle("checked", mode === "google");
}
function createFontDropdown() {
  const items = LustData.get("Font-list").map((f) => ({
    label: f,
    value: f
  }));
  return UI.createDropdown(items, LustData.get("CurrentFont"), {
    datastoreKey: "CurrentFont",
    onChange: (item) => {
      if (LustData.get("Custom-Font") && !LustData.get("Custom-Font-Google")) {
        document.querySelector("#Custom-font")?.remove();
        utils.addFont(LustData.get("Font-folder") + item.value, "Custom-font", "Custom");
        log("Font changed to: " + item.value);
      }
    }
  });
}
async function customFontSection() {
  const br = () => document.createElement("br");
  if (LustData.get("Custom-Font-Local") === LustData.get("Custom-Font-Google")) {
    syncExclusiveFontMode("local");
  }
  const googleFontInput = UI.createInputElement(
    "Google-Font-Url",
    "margin-bottom: 12px; width: 420px; max-width: 100%;",
    async () => {
      LustData.set("Google-Font-Url", googleFontInput.searchbox.value.trim());
      addCss.customFont();
    }
  );
  googleFontInput.searchbox.value = LustData.get("Google-Font-Url") || "";
  googleFontInput.searchbox.placeholder = "https://fonts.googleapis.com/css2?family=Roboto&display=swap";
  const localFontRow = UI.createRow("custom-font-local-row", [
    createFontDropdown()
  ]);
  const googleFontRow = UI.createRow("custom-font-google-row", [
    UI.createLabel(await getString("theme-settings.google-font-url"), ""),
    googleFontInput.origin
  ]);
  const updateVisibility = () => {
    localFontRow.style.display = LustData.get("Custom-Font-Local") ? "" : "none";
    googleFontRow.style.display = LustData.get("Custom-Font-Google") ? "" : "none";
  };
  updateVisibility();
  return [
    UI.createCheckBox(
      await getString("theme-settings.custom-font"),
      "cusfont",
      "cusfontbox",
      async () => {
        addCss.customFont();
      },
      true,
      "Custom-Font"
    ),
    br(),
    UI.createRow("custom-font-mode-row", [
      UI.createCheckBox(
        await getString("theme-settings.custom-font-local"),
        "cusfontlocal",
        "cusfontlocalbox",
        async () => {
          syncExclusiveFontMode("local");
          updateVisibility();
          addCss.customFont();
        },
        true,
        "Custom-Font-Local"
      ),
      UI.createCheckBox(
        await getString("theme-settings.custom-font-google"),
        "cusfontgoogle",
        "cusfontgooglebox",
        async () => {
          syncExclusiveFontMode("google");
          updateVisibility();
          addCss.customFont();
        },
        true,
        "Custom-Font-Google"
      )
    ]),
    br(),
    localFontRow,
    googleFontRow,
    br()
  ];
}

async function profileSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-profile", await getString("theme-settings.settings-section-profile"), [
    UI.createRow("Custom-Curency", [
      UI.createRow("custom-rp", [
        UI.createCheckBox(
          `${await getString("theme-settings.custom-rp")}`,
          "cusrp",
          "cusrpbox",
          () => {
            restartAfterChange("cusrp", "custom-rp");
          },
          true,
          "custom-rp"
        ),
        br(),
        UI.createSearchBox("RP-data")
      ]),
      UI.createRow("custom-be", [
        UI.createCheckBox(
          `${await getString("theme-settings.custom-be")}`,
          "cusbe",
          "cusbebox",
          () => {
            restartAfterChange("cusbe", "custom-be");
          },
          true,
          "custom-be"
        ),
        br(),
        UI.createSearchBox("BE")
      ])
    ]),
    br(),
    ...await customFontSection(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-theme-usage-time")}`,
      "hideusetime",
      "hideusetimebox",
      () => {
      },
      true,
      "hide-theme-usage-time"
    )
  ]);
}

async function gameTabsSection() {
  const br = () => document.createElement("br");
  return UI.createSection("theme-settings-game-tabs", await getString("theme-settings.settings-section-game-tabs"), [
    UI.createCheckBox(
      `${await getString("theme-settings.hide-summoner-rift-5v5")}`,
      "hidesr5v5tab",
      "hidesr5v5tabbox",
      () => {
        restartAfterChange("hidesr5v5tab", "hide-summoner-rift-5v5");
      },
      true,
      "hide-summoner-rift-5v5"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-aram")}`,
      "hidearamtab",
      "hidearamtabbox",
      () => {
        restartAfterChange("hidearamtab", "hide-aram");
      },
      true,
      "hide-aram"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-arena")}`,
      "hidearenatab",
      "hidearenatabbox",
      () => {
        restartAfterChange("hidearenatab", "hide-arena");
      },
      true,
      "hide-arena"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-custom-game-section")}`,
      "hidecustomtab",
      "hidecustomtabbox",
      () => {
        restartAfterChange("hidecustomtab", "hide-custom-game-section");
      },
      true,
      "hide-custom-game-section"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft")}`,
      "hidetfttab",
      "hidetfttabbox",
      () => {
        restartAfterChange("hidetfttab", "hide-tft");
      },
      true,
      "hide-tft"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-match-history")}`,
      "hidetftmhtab",
      "hidetftmhtabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-match-history"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-news")}`,
      "hidetftntab",
      "hidetftntabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-news"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-rotational-shop")}`,
      "hidetftrstab",
      "hidetftrstabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-rotational-shop"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-troves")}`,
      "hidetfttrovestab",
      "hidetfttrovestabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-troves"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-battle-pass")}`,
      "hidetftbattletab",
      "hidetftbattletabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-battle-pass"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("theme-settings.hide-tft-home")}`,
      "hidetfthometab",
      "hidetfthometabbox",
      () => {
        applyHideAndShowTFTtab();
      },
      true,
      "hide-tft-home"
    )
  ]);
}

async function nsfwSection() {
  return document.createElement("div");
  return UI.createCheckBox(
    `${await getString("theme-settings.nsfw-content")}`,
    "nsfw",
    "nsfwbox",
    () => {
    },
    true,
    "NSFW-Content"
  );
}

async function themeSettings(panel) {
  const loading = UI.createRow("loading", [
    UI.createLoading(await getString("common.settings-loading"))
  ]);
  panel.appendChild(loading);
  try {
    panel.prepend(
      UI.createRow("theme-settings-root", [
        ...await infoSection(),
        await assetLibrarySection(),
        await wallpaperSection(),
        await audioSection(),
        await updatesSection(),
        await customAssetsSection(),
        await interfaceSection(),
        await profileSection(),
        await gameTabsSection(),
        await nsfwSection()
      ])
    );
    let hideButtons = document.querySelectorAll("#lust-theme-settings-row-hide-button");
    hideButtons.forEach((button) => {
      button.click();
    });
    setWindowEffectsSettingsVisibility();
  } catch (err) {
    error("Error loading theme settings:", err);
  } finally {
    loading.remove();
  }
}

async function pluginsInfoSection() {
  return [
    UI.createRow("Info", [
      UI.createRow("Info-div", [
        UI.createLink(
          "Lust",
          "https://github.com/lustmyself/Lust",
          () => {
          },
          "theme-link"
        ),
        UI.createLabel(
          `*${await getString("settings.note")}: ${await getString("settings.note-1")}`,
          ""
        )
      ]),
      UI.createImage(true, "logo.png", "plugins-settings-logo")
    ]),
    UI.createLabel(
      `${await getString("plugins-settings.plugins-settings")}`,
      "",
      "theme-settings-section-title"
    )
  ];
}

async function coreSection() {
  const br = () => document.createElement("br");
  return UI.createSection("plugins-settings-core", await getString("plugins-settings.settings-section-plugin-core"), [
    UI.createCheckBox(
      `${await getString("plugins-settings.auto-accept-button")}`,
      "autoacceptbutton",
      "autoacceptbuttonbox",
      () => {
        if (!LustData.get("auto_accept_button")) {
          document.getElementById("autoAcceptQueueButton")?.remove();
          document.getElementById("autoAcceptDelayInput")?.remove();
        }
      },
      true,
      "auto_accept_button"
    ),
  ]);
}

async function queueSection() {
  const queueList = LustData.get("queueList");
  const gamemodeItems = (queueList["Gamemode"] || []).map((o) => ({
    label: o.description,
    value: o.queueId
  }));
  return UI.createSection("plugins-settings-queue", await getString("plugins-settings.settings-section-plugin-queue"), [
    UI.createCheckBox(
      `${await getString("plugins-settings.auto-find-queue")}`,
      "autoq",
      "autoqbox",
      () => {
        restartAfterChange("autoq", "Auto-Find-Queue");
      },
      true,
      "Auto-Find-Queue"
    ),
    UI.createRow("Q-Delay", [
      UI.createRow("Create-Delay", [
        UI.createLabel(`${await getString("plugins-settings.create-delay")}`, "Create-Delay-Text"),
        UI.createSearchBox("Create-Delay")
      ]),
      UI.createRow("Find-Delay", [
        UI.createLabel(`${await getString("plugins-settings.find-delay")}`, "Find-Delay-Text"),
        UI.createSearchBox("Find-Delay")
      ])
    ]),
    UI.createDropdown(gamemodeItems, LustData.get("Gamemode"), {
      title: await getString("plugins-settings.gamemode"),
      datastoreKey: "Gamemode"
    })
  ]);
}

const rankList = async () => {
  return {
    "Ranked Queue ID": [
      {
        "id": 0,
        "name": `${await getString("rank.ranked-solo-5vs5")}`,
        "Option": "RANKED_SOLO_5x5"
      },
      {
        "id": 1,
        "name": `${await getString("rank.ranked-flex-summoners-rift")}`,
        "Option": "RANKED_FLEX_SR"
      },
      {
        "id": 2,
        "name": `${await getString("rank.ranked-flex-tt")}`,
        "Option": "RANKED_FLEX_TT"
      },
      {
        "id": 3,
        "name": `${await getString("rank.ranked-tft")}`,
        "Option": "RANKED_TFT"
      },
      {
        "id": 4,
        "name": `${await getString("rank.ranked-tft-turbo")}`,
        "Option": "RANKED_TFT_TURBO"
      },
      {
        "id": 5,
        "name": `${await getString("rank.ranked-tft-double-up")}`,
        "Option": "RANKED_TFT_DOUBLE_UP"
      },
      {
        "id": 6,
        "name": `${await getString("rank.ranked-tft-pairs")}`,
        "Option": "RANKED_TFT_PAIRS"
      },
      {
        "id": 7,
        "name": `${await getString("rank.arena")}`,
        "Option": "CHERRY"
      }
    ],
    "Ranked Tier ID": [
      {
        "id": 0,
        "name": `${await getString("rank.iron")}`,
        "Option": "IRON"
      },
      {
        "id": 1,
        "name": `${await getString("rank.bronze")}`,
        "Option": "BRONZE"
      },
      {
        "id": 2,
        "name": `${await getString("rank.silver")}`,
        "Option": "SILVER"
      },
      {
        "id": 3,
        "name": `${await getString("rank.gold")}`,
        "Option": "GOLD"
      },
      {
        "id": 4,
        "name": `${await getString("rank.platinum")}`,
        "Option": "PLATINUM"
      },
      {
        "id": 5,
        "name": `${await getString("rank.diamond")}`,
        "Option": "DIAMOND"
      },
      {
        "id": 6,
        "name": `${await getString("rank.emerald")}`,
        "Option": "EMERALD"
      },
      {
        "id": 7,
        "name": `${await getString("rank.master")}`,
        "Option": "MASTER"
      },
      {
        "id": 8,
        "name": `${await getString("rank.grand-master")}`,
        "Option": "GRANDMASTER"
      },
      {
        "id": 9,
        "name": `${await getString("rank.challenger")}`,
        "Option": "CHALLENGER"
      }
    ],
    "Ranked Division ID": [
      {
        "id": 0,
        "name": "I"
      },
      {
        "id": 1,
        "name": "II"
      },
      {
        "id": 2,
        "name": "III"
      },
      {
        "id": 3,
        "name": "IV"
      }
    ]
  };
};

async function pluginsProfileSection() {
  const br = () => document.createElement("br");
  const rank = await rankList();
  const rankDropdown = (key, title) => {
    const items = (rank[key] || []).map((o) => ({ label: o.name, value: o.id }));
    return UI.createDropdown(items, LustData.get(key), {
      title,
      datastoreKey: key
    });
  };
  return UI.createSection("plugins-settings-profile", await getString("plugins-settings.settings-section-plugin-profile"), [
    UI.createCheckBox(
      await getString("plugins-settings.invisible-banner"),
      "invbanner",
      "invbannerbox",
      () => {
        restartAfterChange("invbanner", "invisible_banner");
      },
      true,
      "invisible_banner"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("plugins-settings.custom-profile-hover")}`,
      "cusprf",
      "cusprfbox",
      () => {
        restartAfterChange("cusprf", "Custom-profile-hover");
      },
      true,
      "Custom-profile-hover"
    ),
    UI.createRowHideable("customprf", [
      br(),
      UI.createCheckBox(
        `${await getString("plugins-settings.custom-challenge-crystal")}`,
        "cuschalcry",
        "cuschalcrybox",
        () => {
          restartAfterChange("cuschalcry", "Custom-challenge-crystal");
        },
        true,
        "Custom-challenge-crystal"
      ),
      br(),
      UI.createRow("customchallengecrystal", [
        rankDropdown("Ranked Tier ID", await getString("plugins-settings.challenge-rank")),
        UI.createLabel(`${await getString("plugins-settings.challenge-point")}`, "challenge-point-Text"),
        UI.createSearchBox("Challenge-Points")
      ]),
      UI.createCheckBox(
        `${await getString("plugins-settings.custom-status")}`,
        "cussta",
        "cusstabox",
        () => {
          if (LustData.get("Custom-Status")) {
            if (window.confirm("This may cause some issues with the client's chat, are you sure you want to enable this plugins?")) {
              restartAfterChange("cussta", "Custom-Status");
            } else {
              let box = document.getElementById("cusstabox");
              if (box)
                box.checked = false;
              LustData.set("Custom-Status", false);
            }
          } else {
            restartAfterChange("cussta", "Custom-Status");
          }
        },
        true,
        "Custom-Status"
      ),
      br(),
      UI.createRow("customstatus", [
        UI.createCheckBox(
          `${await getString("plugins-settings.custom-status-local")}`,
          "cussta-local",
          "cussta-localbox",
          () => {
            restartAfterChange("cussta-local", "Custom-Status-Local");
          },
          true,
          "Custom-Status-Local"
        ),
        UI.createLabel(`${await getString("plugins-settings.status-delay")}`, ""),
        UI.createSearchBox("status-delay")
      ])
    ]),
    UI.createRow("namespoof", [
      UI.createCheckBox(
        `${await getString("plugins-settings.name-spoofer")}`,
        "namespf",
        "namespfbox",
        () => {
          restartAfterChange("namespf", "Name-Spoofer");
        },
        true,
        "Name-Spoofer"
      ),
      br(),
      UI.createSearchBox("Spoof-name")
    ])
  ]);
}

async function developerSection() {
  const br = () => document.createElement("br");
  return UI.createSection("plugins-settings-developer", await getString("plugins-settings.settings-section-plugin-developer"), [
    UI.createCheckBox(
      `${await getString("plugins-settings.debug-mode")}`,
      "debug",
      "debugbox",
      () => {
        restartAfterChange("debug", "Debug-mode");
      },
      LustData.get("Dev-button"),
      "Debug-mode"
    ),
    br(),
    UI.createCheckBox(
      `${await getString("plugins-settings.developer-mode")}`,
      "devbutton",
      "devbuttonbox",
      () => {
        restartAfterChange("devbutton", "Dev-mode");
        if (!LustData.get("Dev-mode")) ; else {
          window.alert("You just turned on developer mode \nIf you are not a developer, please turn it off right now \nOtherwise the whole theme will not work properly");
        }
      },
      LustData.get("Dev-button"),
      "Dev-mode"
    )
  ], LustData.get("Dev-button"));
}

async function pluginsSettings(panel) {
  const loading = UI.createRow("loading", [
    UI.createLoading(await getString("common.settings-loading"))
  ]);
  panel.appendChild(loading);
  try {
    panel.prepend(
      UI.createRow("plugins-settings-root", [
        ...await pluginsInfoSection(),
        await coreSection(),
        await pluginsProfileSection(),
        await developerSection()
      ])
    );
    let hideButtons = document.querySelectorAll("#lust-theme-settings-row-hide-button");
    hideButtons.forEach((button) => {
      button.click();
    });
  } catch (err) {
    error("Error loading theme settings:", err);
  } finally {
    loading.remove();
  }
}

async function manualBackupSection() {
  await utils.getSummonerID();
  return [
    UI.createLabel(await getString("backup-restore.manual-backup-restore"), ""),
    document.createElement("br"),
    UI.createRow("manualRestoreBackupSystemInfo", [
      UI.createRow("manualRestoreBackup", [
        UI.createButton(await getString("backup-restore.backup-data"), "ManualBackup", async () => {
          let datastore_list = (await import(`//plugins/${window.getThemeName()}/config/datastoreDefault.js`)).default;
          LustData.set("last-backup-time", /* @__PURE__ */ new Date());
          let sumID = await utils.getSummonerID();
          let keys = Object.keys(datastore_list);
          let mirage = datastore_list;
          keys.forEach((key) => {
            mirage[key] = LustData.get(key);
          });
          let blob = new Blob([JSON.stringify(mirage)], { type: "application/json" });
          let a = document.getElementById("downloadBackup");
          a.href = URL.createObjectURL(blob);
          a.download = `LustTheme-${sumID}.json`;
          a.click();
          a.href = "";
        }),
        document.createElement("br"),
        UI.createRow("RestoreRow", [
          UI.createButton(await getString("backup-restore.restore-data"), "ManualRestore", () => {
            document.getElementById("manualRestoreInput")?.click();
          }),
          UI.createLabel("", "restoreFileInfo")
        ]),
        UI.fileInput("manualRestoreInput", ".json", async (event) => {
          const file = event.target.files[0];
          let text = document.getElementById("restoreFileInfo");
          if (file && file.type === "application/json") {
            const reader = new FileReader();
            reader.onload = async (e) => {
              text.textContent = await getString("backup-restore.manual-restore-inprogress");
              text.style.color = "#e4c2b3";
              try {
                const json = JSON.parse(e.target.result);
                let restoreData = new Promise((resolve, reject) => {
                  setTimeout(async () => {
                    try {
                      await setDefaultData(json, true);
                      resolve();
                      window.setTimeout(() => window.restartClient(), 2e3);
                    } catch {
                      reject();
                      log(`Datastore file not found, avoid restoring`);
                    }
                  }, 5e3);
                });
                window.Toast.promise(restoreData, {
                  loading: "Restoring Datastore...",
                  success: "Restore complete!",
                  error: "Error while restoring data, check console for more info!"
                });
              } catch {
                text.textContent = await getString("backup-restore.invalid-json");
                text.style.color = "red";
              }
            };
            reader.readAsText(file);
          } else {
            text.textContent = await getString("backup-restore.json-file-only");
            text.style.color = "red";
          }
        }),
        UI.createLink("", ``, () => {
        }, "downloadBackup")
      ]),
      UI.createRow("currentSystemInfo", [
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.os")}: ${LustData.get("System-Info")["OSVersion"]}` : "", "systemInfo-Os"),
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.cpu")}: ${LustData.get("System-Info")["CPUName"]}` : "", "systemInfo-Cpu"),
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.core")}: ${LustData.get("System-Info")["CoreCount"]}` : "", "systemInfo-Core"),
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.ram")}: ${Math.round(LustData.get("System-Info")["PhysicalMemory"] / 1024 ** 3)} GB` : "", "systemInfo-Mem"),
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.gpu")}: ${LustData.get("System-Info")["GPUName"]}` : "", "systemInfo-Gpu"),
        UI.createLabel(LustData.get("Dev-mode") ? `${await getString("backup-restore.vram")}: ${Math.round(LustData.get("System-Info")["GPUMemory"] / 1024 ** 3)} GB` : "", "systemInfo-Vram")
      ])
    ])
  ];
}

const getSystemInfo = async () => {
  if (LustData.get("Dev-mode")) {
    let systemInfo = await (await fetch("/performance/v1/system-info")).json();
    LustData.set("System-Info", systemInfo);
  }
};
async function CheckBackupFile() {
  const restoreButton = document.querySelector(".restore-data-button");
  const deleteButton = document.querySelector(".delete-data-button");
  const checkText = document.getElementById("datastore-cloud-checking");
  const backupInfo = document.getElementById("backupInfo");
  const lastbackup = document.querySelector("#backupSystemInfo > #systemInfo-LastBackup");
  const os = document.querySelector("#backupSystemInfo > #systemInfo-Os");
  const cpu = document.querySelector("#backupSystemInfo > #systemInfo-Cpu");
  const core = document.querySelector("#backupSystemInfo > #systemInfo-Core");
  const mem = document.querySelector("#backupSystemInfo > #systemInfo-Mem");
  const gpu = document.querySelector("#backupSystemInfo > #systemInfo-Gpu");
  const vram = document.querySelector("#backupSystemInfo > #systemInfo-Vram");
  try {
    checkText.textContent = `${await getString("backup-restore.loading")}...`;
    checkText.style.color = "#a09b8c";
    let checkFile = await window.lustthemeApi.readBackup(LustData.get("LustTheme-Token"), LustData.get("Summoner-ID"));
    if (checkFile.data != null && Object.keys(checkFile.data).length > 0 && checkFile.success) {
      log("You have backup file on cloud, ready to restore it.");
      restoreButton.style.visibility = "visible";
      deleteButton.style.visibility = "visible";
      checkText.style.color = "green";
      checkText.textContent = `${await getString("backup-restore.check-backup-success")}`;
      backupInfo.style.visibility = "visible";
      let backupData = typeof checkFile.data === "string" ? JSON.parse(checkFile.data) : checkFile.data;
      lastbackup.textContent = `${await getString("backup-restore.last-backup")}: ${backupData["last-backup-time"]}`;
      if (LustData.get("Dev-mode")) {
        try {
          os.textContent = `${await getString("backup-restore.os")}: ${backupData["System-Info"]["OSVersion"]}`;
          cpu.textContent = `${await getString("backup-restore.cpu")}: ${backupData["System-Info"]["CPUName"]}`;
          core.textContent = `${await getString("backup-restore.core")}: ${backupData["System-Info"]["CoreCount"]}`;
          mem.textContent = `${await getString("backup-restore.ram")}: ${Math.round(backupData["System-Info"]["PhysicalMemory"] / 1024 ** 3)} GB`;
          gpu.textContent = `${await getString("backup-restore.gpu")}: ${backupData["System-Info"]["GPUName"]}`;
          vram.textContent = `${await getString("backup-restore.vram")}: ${Math.round(backupData["System-Info"]["GPUMemory"] / 1024 ** 3)} GB`;
        } catch (err) {
          warn("Error while getting system data:", err);
        }
      }
    } else {
      log("You don't have backup file on cloud yet.");
      restoreButton.style.visibility = "hidden";
      deleteButton.style.visibility = "hidden";
      checkText.style.color = "yellow";
      checkText.textContent = `${await getString("backup-restore.check-backup-error")}`;
      backupInfo.style.visibility = "hidden";
    }
  } catch (err) {
    log("Cloud server is sleep, try backup/restore later. Detail:", err);
    restoreButton.style.visibility = "hidden";
    deleteButton.style.visibility = "hidden";
    checkText.style.color = "red";
    checkText.textContent = `${await getString("backup-restore.check-backup-servererror")}`;
    backupInfo.style.visibility = "hidden";
  }
}
async function cloudBackupSection() {
  const summonerID = await utils.getSummonerID();
  await getSystemInfo();
  const elements = [
    UI.createCheckBox(
      `${await getString("backup-restore.backup-datastore")}`,
      "bakdata",
      "bakdatabox",
      async () => {
        if (LustData.get("backup-datastore")) {
          await CheckBackupFile();
        }
      },
      true,
      "backup-datastore"
    ),
    UI.createLabel(`${await getString("backup-restore.loading")}...`, "datastore-cloud-checking"),
    document.createElement("br"),
    UI.createRow("restoreAndDeleteData", [
      UI.createButton(`${await getString("backup-restore.restore-data")}`, "restore-data-button", () => {
        let restoreData = new Promise(async (resolve, reject) => {
          try {
            let cloud = await window.lustthemeApi.readBackup(LustData.get("LustTheme-Token"), summonerID);
            if (cloud.success) {
              await setDefaultData(cloud.data, true);
              resolve();
              window.setTimeout(() => window.restartClient(), 2e3);
            }
          } catch {
            reject();
            log(`Datastore file not found, avoid restoring`);
          }
        });
        window.Toast.promise(restoreData, {
          loading: "Restoring Datastore...",
          success: "Restore complete!",
          error: "Error while restoring data, check console for more info!"
        });
      }),
      UI.createButton(`${await getString("backup-restore.delete-data")}`, "delete-data-button", async () => {
        try {
          await window.lustthemeApi.deleteBackup(LustData.get("LustTheme-Token"), summonerID);
          log("Datastore file deleted from cloud");
          await new Promise((r) => setTimeout(r, 1e3));
        } catch (err) {
          error("Error deleting datastore file from cloud:", err);
        } finally {
          await CheckBackupFile();
        }
      })
    ], true),
    UI.createRow("backupInfo", [
      UI.createLabel(await getString("backup-restore.backupinfo"), ""),
      UI.createRow("backupSystemInfo", [
        UI.createLabel("", "systemInfo-LastBackup"),
        UI.createLabel("", "systemInfo-Os"),
        UI.createLabel("", "systemInfo-Cpu"),
        UI.createLabel("", "systemInfo-Core"),
        UI.createLabel("", "systemInfo-Mem"),
        UI.createLabel("", "systemInfo-Gpu"),
        UI.createLabel("", "systemInfo-Vram")
      ])
    ])
  ];
  return {
    elements,
    postSetup: () => CheckBackupFile()
  };
}

async function backuprestoretab(panel) {
  const loading = UI.createRow("loading", [
    UI.createLoading(await getString("common.settings-loading"))
  ]);
  panel.appendChild(loading);
  try {
    const cloud = { elements: [], postSetup: async () => {} };
    panel.prepend(
      UI.createRow("", [
        ...await manualBackupSection(),
        ...cloud.elements
      ])
    );
    await cloud.postSetup();
  } catch (err) {
    error("Error loading theme settings:", err);
  } finally {
    loading.remove();
  }
}

async function aboutustab(panel) {
  panel.prepend(
    UI.createRow("", [
      UI.createRow("Developer", [
        UI.createRow("dev-avatar", [
          UI.createRow("dev-div", [
            UI.createImageWithLink(true, "logo.png", "dev_ava", "https://github.com/lustmyself/Lust", () => {
            }),
            UI.createLabel("Lust", "first_line_lust"),
            UI.createLabel("github.com/lustmyself/Lust", "")
          ])
        ])
      ])
    ])
  );
}

const datapath$5 = `//plugins/${getThemeName()}/`;
function getSettingsBackdrop() {
  const settingsApp = document.querySelector(".rcp-fe-lol-settings");
  const backdrop = settingsApp?.previousElementSibling;
  if (backdrop?.matches("lol-uikit-full-page-backdrop.backdrop"))
    return backdrop;
  return null;
}
function makeSettingsBackdropTransparent() {
  const backdrop = getSettingsBackdrop();
  if (!backdrop)
    return;
  backdrop.style.setProperty("background", "transparent", "important");
  backdrop.setAttribute("data-lust-settings-backdrop", "true");
}
function makeSettingsDraggable() {
  const frame = document.querySelector("lol-uikit-dialog-frame.lol-settings-container");
  const handle = frame?.querySelector(".lol-settings-title-bar");
  if (!frame || !handle)
    return;
  if (frame.hasAttribute("data-lust-settings-draggable")) {
    makeSettingsBackdropTransparent();
    return;
  }
  let dragging = false;
  let pointerId = 0;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;
  const getFrameRect = () => frame.getBoundingClientRect();
  const onPointerMove = (event) => {
    if (!dragging || event.pointerId !== pointerId)
      return;
    const rect = getFrameRect();
    const nextLeft = Math.min(Math.max(startLeft + event.clientX - startX, 0), window.innerWidth - rect.width);
    const nextTop = Math.min(Math.max(startTop + event.clientY - startY, 0), window.innerHeight - rect.height);
    frame.style.left = `${nextLeft}px`;
    frame.style.top = `${nextTop}px`;
  };
  const onPointerUp = (event) => {
    if (!dragging || event.pointerId !== pointerId)
      return;
    dragging = false;
    handle.releasePointerCapture?.(pointerId);
    handle.style.cursor = "grab";
    document.removeEventListener("pointermove", onPointerMove);
    document.removeEventListener("pointerup", onPointerUp);
    document.removeEventListener("pointercancel", onPointerUp);
  };
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0)
      return;
    const target = event.target;
    if (target?.closest("button, input, textarea, select, lol-uikit-flat-button-secondary"))
      return;
    const rect = getFrameRect();
    dragging = true;
    pointerId = event.pointerId;
    startX = event.clientX;
    startY = event.clientY;
    startLeft = rect.left;
    startTop = rect.top;
    frame.style.position = "fixed";
    frame.style.left = `${rect.left}px`;
    frame.style.top = `${rect.top}px`;
    frame.style.right = "auto";
    frame.style.bottom = "auto";
    frame.style.margin = "0";
    handle.style.cursor = "grabbing";
    handle.setPointerCapture?.(pointerId);
    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", onPointerUp);
    document.addEventListener("pointercancel", onPointerUp);
    event.preventDefault();
  });
  handle.style.cursor = "grab";
  frame.setAttribute("data-lust-settings-draggable", "true");
  makeSettingsBackdropTransparent();
}
async function restartAfterChange(el, data) {
  const element = document.getElementById(el);
  const lastdata = element?.getAttribute("lastdatastore");
  const currentData = JSON.stringify(LustData.get(data));
  const wasChanged = element?.getAttribute("restart-change-active") === "true";
  const isChanged = lastdata !== currentData;
  const settingsChangeNumber = LustData.get("settingsChangenumber") || 0;
  if (isChanged && !wasChanged) {
    LustData.set("settingsChangenumber", settingsChangeNumber + 1);
    element?.setAttribute("restart-change-active", "true");
  } else if (!isChanged && wasChanged) {
    LustData.set("settingsChangenumber", Math.max(settingsChangeNumber - 1, 0));
    element?.setAttribute("restart-change-active", "false");
  }
  if (!document.querySelector("#restartAfterChangeButton") && LustData.get("settingsChangenumber") > 0) {
    let target = document.querySelector(".lol-settings-footer.ember-view");
    let a = document.createElement("lol-uikit-flat-button-group");
    let b = document.createElement("lol-uikit-flat-button");
    a.setAttribute("type", "window-popup");
    a.classList.add("lol-settings-close-container");
    a.style.cssText = "margin-left: 10px";
    a.id = "restartAfterChangeButton";
    b.classList.add("lol-settings-close-button");
    b.style.cssText = "width: 150px;";
    b.textContent = await getString("settings.restart-client");
    b.id = "restartAfterChange";
    b.addEventListener("click", () => {
      if (LustData.get("backup-datastore")) {
        try {
          writeBackupData();
        } catch (err) {
          error("Server is down rightnow", err);
        }
        window.setTimeout(() => {
          window.restartClient();
        }, 3e3);
      } else
        window.restartClient();
    });
    target?.append(a);
    a.append(b);
  } else if (LustData.get("settingsChangenumber") == 0) {
    document.querySelector("#restartAfterChangeButton")?.remove();
  }
}
async function writeBackupData() {
  let datastore_list = (await import(`${datapath$5}config/datastoreDefault.js`)).default;
  LustData.set("last-backup-time", /* @__PURE__ */ new Date());
  let keys = Object.keys(datastore_list);
  let mirage = datastore_list;
  keys.forEach((key) => {
    mirage[key] = LustData.get(key);
  });
  await window.lustthemeApi.writeBackup(LustData.get("LustTheme-Token"), LustData.get("Summoner-ID"), mirage);
}
window.addEventListener("load", async () => {
  observer.subscribeToElementCreation(".app-controls-button.app-controls-close", (element) => {
    element.addEventListener("click", async () => {
      if (LustData.get("backup-datastore")) {
        await writeBackupData();
      }
    });
  });
  observer.subscribeToElementCreation(".plugins-settings-logo", (element) => {
    element.addEventListener("click", () => {
      LustData.set("Active-dev-button", LustData.get("Active-dev-button") + 1);
      if (LustData.get("Active-dev-button") == 20) {
        LustData.set("Dev-button", true);
        log("Developer mode button has appeared !");
      } else if (LustData.get("Active-dev-button") > 20) {
        LustData.set("Dev-button", true);
        log("You already become developer !");
      }
    });
  });
  const interval = setInterval(() => {
    const manager = document.getElementById("lol-uikit-layer-manager-wrapper");
    if (manager) {
      clearInterval(interval);
      makeSettingsDraggable();
      new MutationObserver((mutations) => {
        makeSettingsDraggable();
        const plugin = document.querySelector("lol-uikit-scrollable.plugins_settings");
        const theme = document.querySelector("lol-uikit-scrollable.theme_settings");
        const backupandrestore = document.querySelector("lol-uikit-scrollable.backup_restore_settings");
        const aboutus = document.querySelector("lol-uikit-scrollable.aboutus_settings");
        if (theme && mutations.some((record) => Array.from(record.addedNodes).includes(theme))) {
          themeSettings(theme);
        } else if (plugin && mutations.some((record) => Array.from(record.addedNodes).includes(plugin))) {
          pluginsSettings(plugin);
        } else if (backupandrestore && mutations.some((record) => Array.from(record.addedNodes).includes(backupandrestore))) {
          backuprestoretab(backupandrestore);
        } else if (aboutus && mutations.some((record) => Array.from(record.addedNodes).includes(aboutus))) {
          aboutustab(aboutus);
        }
      }).observe(manager, {
        childList: true,
        subtree: true
      });
    }
  }, 500);
});
// Turkish for Lust's own texts in the panel; other languages go through LUST-I18n
const LUST_TR = {
  "CUSTOMIZE": "ÖZELLEŞTİR",
  "Status": "Durum",
  "Colors": "Renkler",
  "Theme": "Tema",
  "Plugins": "Eklentiler",
  "Online": "Çevrimiçi",
  "Offline": "Çevrimdışı",
  "Mobile": "Mobil",
  "online": "çevrimiçi",
  "offline": "çevrimdışı",
  "mobile": "mobil",
  "Friends see you as {status}.": "Arkadaşların seni {status} görüyor.",
  "Lust Offline isn't running: close League and open it again to appear offline.":
    "Lust Offline çalışmıyor: çevrimdışı görünmek için League'i kapatıp yeniden aç.",
  "Couldn't reach Lust Offline.": "Lust Offline'a ulaşılamadı.",
  "Summoner names": "Sihirdar adları",
  "Lobby names": "Lobi adları",
  "Lobby header": "Lobi başlığı",
  "Queue (finding match)": "Sıra (maç aranıyor)",
  "League default": "League varsayılanı",
  "Default": "Varsayılan",
  "Reload client to apply": "Uygulamak için istemciyi yenile",
  "Add wallpaper": "Duvar kağıdı ekle",
  "Paste the file, type its name": "Dosyayı yapıştır, adını yaz",
  "Copy your picture or video into the folder that opened": "Resmini ya da videonu açılan klasöre kopyala",
  "{name} is your wallpaper": "{name} artık duvar kağıdın",
  "Not a video or image file name": "Video ya da resim dosyası adı değil",
  "{name} is not in the folder": "{name} klasörde yok",
  "16:9 Size Preferred": "16:9 boyut önerilir",
  "Add": "Ekle",
  "Delete": "Sil",
  "Drop files here, or Add to open the folder": "Dosyaları buraya bırak ya da klasörü açmak için Ekle'ye bas",
  "Keep at least one": "En az bir tane kalmalı",
  "{name} isn't a {type} file": "{name} bir {type} dosyası değil",
  "Adding {name}...": "{name} ekleniyor...",
  "Lust isn't connected": "Lust bağlı değil",
  "Lust didn't answer": "Lust cevap vermedi",
  "What's new in Lust {version}": "Lust {version} yenilikleri",
  "Got it": "Tamam",
  "Backup": "Yedek",
  "Keep your settings in a file, or bring them from another PC.": "Ayarlarını bir dosyada sakla ya da başka bir bilgisayardan getir.",
  "Export settings": "Ayarları dışa aktar",
  "Import settings": "Ayarları içe aktar",
  "Saved as Lust-settings.json": "Lust-settings.json olarak kaydedildi",
  "Settings imported, reloading the client...": "Ayarlar içe aktarıldı, istemci yenileniyor...",
  "That isn't a Lust settings file.": "Bu bir Lust ayar dosyası değil.",
  "Appearance": "Görünüm",
  "Wallpaper": "Duvar kağıdı",
  "Lobby Reveal": "Lobby Reveal",
  "Lust core": "Lust çekirdeği",
  "Advanced": "Gelişmiş",
  "Close": "Kapat",
  "Injection, the League path, custom mods and troubleshooting live in Lust's core settings.":
    "Enjeksiyon, League yolu, özel modlar ve sorun giderme Lust'un çekirdek ayarlarında.",
  "Open core settings": "Çekirdek ayarlarını aç",
  "Custom skins": "Özel skinler",
  "Open the custom skins folder": "Özel skin klasörünü aç",
  "Press + and paste your custom skin files (.zip, .fantome, .modpkg) into the folder that opens, or drop them here. A skin that is on plays when you go into a game with that champion's default skin.":
    "+'ya bas ve açılan klasöre özel skin dosyalarını (.zip, .fantome, .modpkg) yapıştır ya da buraya sürükle. Açık olan skin, o şampiyonla default skinde oyuna girince oynar.",
  "No custom skins yet.": "Henüz özel skin yok.",
  "This file can't be read": "Bu dosya okunamıyor",
  "Pick the champion": "Şampiyonu seç",
  "Change the champion": "Şampiyonu değiştir",
  "Welcome": "Hoş geldin",
  "Unranked": "Derecesiz",
  "Iron": "Demir", "Bronze": "Bronz", "Silver": "Gümüş", "Gold": "Altın", "Platinum": "Platin", "Emerald": "Zümrüt",
  "Diamond": "Elmas", "Master": "Ustalık", "Grandmaster": "Üstatlık", "Challenger": "Şampiyonluk",
  "Ranked Solo/Duo": "Dereceli Tek/Çift", "Ranked Flex": "Dereceli Esnek", "Normal": "Normal", "Quickplay": "Hızlı Oyun",
  "Match": "Maç", "Last match": "Son maç", "Victory": "Galibiyet", "Defeat": "Mağlubiyet", "W": "G", "L": "M",
  "Level {level}": "Seviye {level}",
  "{region} cutoffs:": "{region} sınırları:",
  "{lp} LP to {rank}": "{rank} için {lp} LP",
  "Lust is ready": "Lust hazır",
  "Your status, look, skins and plugins, all in one place.": "Durumun, görünümün, skinlerin ve eklentilerin tek yerde.",
  "On": "Açık",
  "Off": "Kapalı"
};
function lustTr(text, vars) {
  const i18n = window.LustI18n;
  let out = i18n && i18n.language === "tr" && LUST_TR[text] ? LUST_TR[text] : i18n ? i18n.t(text) : text;
  if (vars) out = out.replace(/\{(\w+)\}/g, (match, key) => (key in vars ? String(vars[key]) : match));
  return out;
}

function Settings(context) {
  LustData.set("settingsChangenumber", 0);
  mountLustHub();
  applyLustColors();
}

// Lust: the LUST item in the top navigation opens the Lust hub, a centered window
// with tabs down the side. Rose's own settings stay in Rose's panel, opened from
// the last tab. Theme sections are the theme's own, sorted into the tabs.
async function lustThemeSections(page, sections) {
  for (const build of sections) {
    const built = await build();
    (Array.isArray(built) ? built : [built]).forEach((node) => node && page.appendChild(node));
  }
  // The theme starts its foldable rows folded; only this page's, not every page's
  page.querySelectorAll("#lust-theme-settings-row-hide-button").forEach((button) => button.click());
}
const LUST_HUB_TABS = [
  { id: "status", label: "Status", icon: "status", render: async (page) => {
    lustHero(page);
    await newsCard(page);
    await statusSection(lustSection(page, lustTr("Status")));
  } },
  { id: "look", label: "Appearance", icon: "look", reload: true, render: async (page) => {
    colorSection(lustSection(page, lustTr("Colors")));
    await lustThemeSections(page, [infoSection, interfaceSection, profileSection, customAssetsSection, gameTabsSection]);
    if (typeof setWindowEffectsSettingsVisibility === "function") setWindowEffectsSettingsVisibility();
  } },
  { id: "wallpaper", label: "Wallpaper", icon: "wallpaper", reload: true, render: (page) =>
    lustThemeSections(page, [assetLibrarySection, wallpaperSection, audioSection]) },
  { id: "skins", label: "Custom skins", icon: "skins", render: (page) => customSkinsTab(page) },
  { id: "plugins", label: "Plugins", icon: "plugins", reload: true, render: async (page) => {
    await lustThemeSections(page, [coreSection, pluginsProfileSection]);
    const more = document.createElement("details");
    more.className = "lust-hub-advanced";
    const summary = document.createElement("summary");
    summary.textContent = lustTr("Advanced");
    more.appendChild(summary);
    page.appendChild(more);
    await lustThemeSections(more, [updatesSection, developerSection]);
  } },
  // Drawn by the LUST-LobbyReveal plugin
  { id: "reveal", label: "Lobby Reveal", icon: "reveal", render: async (page) =>
    window.LustReveal && window.LustReveal.renderHub(page) },
  { id: "backup", label: "Backup", icon: "backup", render: (page) => backupSection(lustSection(page, lustTr("Backup"))) },
  { id: "core", label: "Lust core", icon: "core", render: (page) => coreTab(lustSection(page, lustTr("Lust core"))) },
];
// Small line icons for the side tabs, drawn in the tab's text color
const LUST_HUB_ICONS = {
  status: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
  look: '<path d="M12 3a9 9 0 1 0 0 18c1 0 1.5-.8 1.5-1.6 0-1.4-1.2-1.6-1.2-2.9 0-1 .8-1.5 1.8-1.5H17a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="14.5" cy="7" r="1"/>',
  wallpaper: '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 16l5-5 4 4 3-3 6 6"/><circle cx="16" cy="9" r="1.5"/>',
  plugins: '<path d="M9 3h6v4a2 2 0 1 1 0 4v2h4v6h-6v-2a2 2 0 1 0-4 0v2H3v-6h2a2 2 0 1 0 0-4H3V7h6z"/>',
  reveal: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14.2c3 .3 5.5 2.6 5.5 5.8"/>',
  skins: '<path d="M12 3l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.3 6.8 19l1-5.8-4.2-4.1 5.8-.8z"/>',
  backup: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
  core: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
};
function lustHubIcon(name) {
  return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${LUST_HUB_ICONS[name] || ""}</svg>`;
}
// Lust: custom skins. + opens Lust's "custom skins" folder (files are copied and pasted in),
// files dropped on the tab are sent to Lust, and each skin is switched on or off. A
// switched-on skin plays when its champion goes into a game with the default skin.
const lustSkinWaiters = new Map();
let lustSkinRequests = 0;
let lustSkinsSubscribed = false;
function lustCustomSkins(action, extra = {}) {
  const bridge = window.__lustBridge;
  if (!bridge) return Promise.resolve({ error: lustTr("Lust isn't connected"), skins: null });
  if (!lustSkinsSubscribed) {
    lustSkinsSubscribed = true;
    bridge.subscribe("lust-custom-skins", (reply) => {
      const waiter = lustSkinWaiters.get(reply && reply.requestId);
      if (waiter) {
        lustSkinWaiters.delete(reply.requestId);
        waiter(reply);
      }
    });
  }
  const requestId = `${Date.now()}-${++lustSkinRequests}`;
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      lustSkinWaiters.delete(requestId);
      resolve({ error: lustTr("Lust didn't answer"), skins: null });
    }, 20000);
    lustSkinWaiters.set(requestId, (reply) => {
      clearTimeout(timer);
      resolve(reply);
    });
    bridge.send({ type: "lust-custom-skins", action, requestId, ...extra });
  });
}
let lustChampionList = null;
async function lustChampions() {
  if (lustChampionList && lustChampionList.length) return lustChampionList;
  try {
    const all = await (await fetch("/lol-game-data/assets/v1/champion-summary.json")).json();
    lustChampionList = all.filter((champion) => champion.id > 0).sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    lustChampionList = [];
  }
  return lustChampionList;
}
async function customSkinsTab(page) {
  const section = lustSection(page, lustTr("Custom skins"));
  const head = document.createElement("div");
  head.className = "lust-skins-head";
  const add = document.createElement("div");
  add.className = "lust-skins-add";
  add.textContent = "+";
  add.title = lustTr("Open the custom skins folder");
  add.addEventListener("click", () => lustCustomSkins("open"));
  const help = document.createElement("div");
  help.className = "lust-skins-help";
  help.textContent = lustTr("Press + and paste your custom skin files (.zip, .fantome, .modpkg) into the folder that opens, or drop them here. A skin that is on plays when you go into a game with that champion's default skin.");
  head.append(add, help);
  const hint = document.createElement("div");
  hint.className = "lust-asset-hint";
  const list = document.createElement("div");
  list.className = "lust-skins-list";
  section.append(head, hint, list);
  const champions = await lustChampions();
  const byId = new Map(champions.map((champion) => [champion.id, champion]));
  const byAlias = new Map(champions.map((champion) => [String(champion.alias).toLowerCase(), champion]));
  let shownKey = "";
  const say = (text, error) => {
    hint.textContent = text || "";
    hint.classList.toggle("error", Boolean(error && text));
  };
  const show = (skins) => {
    if (!Array.isArray(skins)) return;
    const key = JSON.stringify(skins);
    if (key === shownKey) return;
    shownKey = key;
    if (!skins.length) {
      const empty = document.createElement("div");
      empty.className = "lust-skins-empty";
      empty.textContent = lustTr("No custom skins yet.");
      list.replaceChildren(empty);
      return;
    }
    list.replaceChildren(...skins.map((skin) => {
      const champion = byId.get(skin.championId);
      const row = document.createElement("div");
      row.className = "lust-skin-row" + (skin.enabled ? " on" : "");
      const icon = document.createElement("div");
      icon.className = "lust-skin-icon";
      if (champion) {
        icon.style.backgroundImage = `url(/lol-game-data/assets/v1/champion-icons/${champion.id}.png)`;
        icon.classList.add("changeable");
        icon.title = lustTr("Change the champion");
        icon.addEventListener("click", async () => {
          const reply = await lustCustomSkins("set", { name: skin.name, championId: 0 });
          say(reply.error, true);
          show(reply.skins);
        });
      }
      const text = document.createElement("div");
      text.className = "lust-skin-text";
      const title = document.createElement("div");
      title.className = "lust-skin-title";
      title.textContent = skin.title;
      const sub = document.createElement("div");
      sub.className = "lust-skin-sub";
      sub.textContent = skin.broken ? lustTr("This file can't be read") : `${champion ? champion.name + " · " : ""}${skin.name}`;
      text.append(title, sub);
      row.append(icon, text);
      if (!champion && !skin.broken) {
        const pick = document.createElement("select");
        pick.className = "lust-skin-pick";
        const none = document.createElement("option");
        none.value = "";
        none.textContent = lustTr("Pick the champion");
        pick.appendChild(none);
        champions.forEach((option) => {
          const item = document.createElement("option");
          item.value = String(option.id);
          item.textContent = option.name;
          pick.appendChild(item);
        });
        pick.addEventListener("change", async () => {
          if (!pick.value) return;
          const reply = await lustCustomSkins("set", { name: skin.name, championId: Number(pick.value) });
          say(reply.error, true);
          show(reply.skins);
        });
        row.appendChild(pick);
      }
      const toggle = document.createElement("div");
      toggle.className = "lust-skin-toggle" + (skin.enabled ? " on" : "") + (champion ? "" : " off-limits");
      toggle.title = champion ? lustTr(skin.enabled ? "On" : "Off") : lustTr("Pick the champion");
      toggle.addEventListener("click", async () => {
        if (!champion) return;
        const reply = await lustCustomSkins("set", { name: skin.name, enabled: !skin.enabled });
        say(reply.error, true);
        show(reply.skins);
      });
      row.appendChild(toggle);
      return row;
    }));
  };
  let busy = false;
  const refresh = async () => {
    if (busy) return;
    const reply = await lustCustomSkins("list");
    if (reply.error) {
      say(reply.error, true);
      return;
    }
    // A skin whose WAD names its champion gets that champion by itself
    for (const skin of reply.skins || []) {
      if (skin.championId || skin.broken || skin.auto === false) continue;
      const match = (skin.wads || []).map((wad) => byAlias.get(wad)).find(Boolean);
      if (match) {
        const set = await lustCustomSkins("set", { name: skin.name, championId: match.id });
        if (Array.isArray(set.skins)) reply.skins = set.skins;
      }
    }
    show(reply.skins);
  };
  // Files copied into the folder show up while the tab is open
  const timer = setInterval(() => {
    if (!document.body.contains(page)) { clearInterval(timer); return; }
    if (page.classList.contains("active")) refresh();
  }, 2500);
  section.addEventListener("dragover", (event) => {
    event.preventDefault();
    section.parentElement.classList.add("dragging");
  });
  section.addEventListener("dragleave", () => section.parentElement.classList.remove("dragging"));
  section.addEventListener("drop", async (event) => {
    event.preventDefault();
    section.parentElement.classList.remove("dragging");
    busy = true;
    for (const file of [...((event.dataTransfer && event.dataTransfer.files) || [])]) {
      say(lustTr("Adding {name}...", { name: file.name }));
      const total = Math.max(1, Math.ceil(file.size / LUST_ASSET_CHUNK));
      let error = "";
      for (let index = 0; index < total && !error; index++) {
        const data = await lustBlobToBase64(file.slice(index * LUST_ASSET_CHUNK, (index + 1) * LUST_ASSET_CHUNK));
        error = (await lustCustomSkins("chunk", { name: file.name, index, total, data })).error;
      }
      say(error, true);
    }
    busy = false;
    refresh();
  });
  await refresh();
}
// The welcome card on top of the Status tab: the player, their rank and their
// last match, on that champion's splash art. Read from the client, kept for next time.
const LUST_TIERS = { IRON: "Iron", BRONZE: "Bronze", SILVER: "Silver", GOLD: "Gold", PLATINUM: "Platinum",
  EMERALD: "Emerald", DIAMOND: "Diamond", MASTER: "Master", GRANDMASTER: "Grandmaster", CHALLENGER: "Challenger" };
const LUST_QUEUES = { 420: "Ranked Solo/Duo", 440: "Ranked Flex", 400: "Normal", 430: "Normal", 490: "Quickplay",
  480: "Quickplay", 450: "ARAM", 1700: "Arena", 1900: "URF", 900: "URF" };
// The server's Challenger and Grandmaster cutoffs, read by Lust from replays.lol
let lustCutoffWaiter = null;
function lustCutoffs(region) {
  const bridge = window.__lustBridge;
  if (!bridge || !region) return Promise.resolve(null);
  if (!lustCutoffs.subscribed) {
    lustCutoffs.subscribed = true;
    bridge.subscribe("lust-cutoffs", (reply) => lustCutoffWaiter && lustCutoffWaiter(reply));
  }
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), 15000);
    lustCutoffWaiter = (reply) => { clearTimeout(timer); resolve(reply && reply.cutoff); };
    bridge.send({ type: "lust-cutoffs", region, requestId: String(Date.now()) });
  });
}
async function lustHeroData() {
  const get = async (path) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(path);
    return response.json();
  };
  const summoner = await get("/lol-summoner/v1/current-summoner");
  const data = { name: summoner.gameName || summoner.displayName || "", tag: summoner.tagLine || "",
    level: summoner.summonerLevel || 0 };
  try {
    const solo = ((await get("/lol-ranked/v1/current-ranked-stats")).queueMap || {}).RANKED_SOLO_5x5 || {};
    const tier = solo.tier && solo.tier !== "NONE" ? solo.tier : "";
    let rank = tier ? lustTr(LUST_TIERS[tier] || tier) : lustTr("Unranked");
    if (tier && solo.division && solo.division !== "NA" && !["MASTER", "GRANDMASTER", "CHALLENGER"].includes(tier)) rank += ` ${solo.division}`;
    if (tier) rank += ` · ${solo.leaguePoints || 0} LP`;
    Object.assign(data, { rank, wins: solo.wins || 0, losses: solo.losses || 0, lp: solo.leaguePoints || 0,
      tier: tier.toLowerCase() });
  } catch (error) {}
  try {
    data.cutoff = await lustCutoffs((await get("/riotclient/region-locale")).region);
  } catch (error) {}
  try {
    const games = ((await get("/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=1")).games || {}).games || [];
    if (games.length) {
      const player = games[0].participants[0];
      const stats = player.stats || {};
      const champion = await get(`/lol-game-data/assets/v1/champions/${player.championId}.json`);
      const skin = (champion.skins || [])[0] || {};
      data.last = { champion: champion.name || "", win: !!stats.win, kda: `${stats.kills || 0}/${stats.deaths || 0}/${stats.assists || 0}`,
        queue: lustTr(LUST_QUEUES[games[0].queueId] || "Match"), splash: skin.uncenteredSplashPath || skin.splashPath || "" };
    }
  } catch (error) {}
  return data;
}
function lustHeroFill(hero, data) {
  const make = (tag, cls, text) => Object.assign(document.createElement(tag), { className: cls, textContent: text });
  const body = make("div", "lust-hero-body", "");
  body.appendChild(make("small", "", lustTr("Lust is ready") + " · " + lustTr("Welcome")));
  const title = make("b", "", data && data.name ? data.name : lustTr("Lust is ready"));
  if (data && data.tag) title.appendChild(make("i", "", ` #${data.tag}`));
  body.appendChild(title);
  const chips = make("div", "lust-hero-chips", "");
  if (data && data.rank) chips.appendChild(make("span", "lust-chip rank", data.rank));
  if (data && (data.wins || data.losses)) {
    const total = data.wins + data.losses;
    chips.appendChild(make("span", "lust-chip", `${data.wins}${lustTr("W")} ${data.losses}${lustTr("L")} · %${Math.round(data.wins * 100 / total)}`));
  }
  if (data && data.level) chips.appendChild(make("span", "lust-chip", lustTr("Level {level}", { level: data.level })));
  if (chips.childElementCount) body.appendChild(chips);
  else body.appendChild(make("span", "", lustTr("Your status, look, skins and plugins, all in one place.")));
  const cut = data && data.cutoff;
  if (cut) {
    const row = make("div", "lust-hero-cut", "");
    row.append(make("span", "", lustTr("{region} cutoffs:", { region: cut.region })),
      make("span", "lust-cut gm", `${lustTr("Grandmaster")} ${cut.grandmaster} LP`),
      make("span", "lust-cut ch", `${lustTr("Challenger")} ${cut.challenger} LP`));
    const apex = data.tier === "grandmaster" || data.tier === "challenger";
    const target = apex ? cut.challenger : data.tier === "master" ? cut.grandmaster : 0;
    if (target && data.lp < target) {
      row.appendChild(make("span", "lust-cut-need",
        lustTr("{lp} LP to {rank}", { lp: target - data.lp, rank: lustTr(apex ? "Challenger" : "Grandmaster") })));
    }
    body.appendChild(row);
  }
  const parts = [body];
  if (data && data.last) {
    const last = make("div", "lust-hero-last", "");
    last.append(make("small", "", lustTr("Last match")), make("b", "", data.last.champion),
      make("span", "lust-hero-result " + (data.last.win ? "win" : "loss"), lustTr(data.last.win ? "Victory" : "Defeat")),
      make("span", "", `${data.last.kda} · ${data.last.queue}`));
    parts.push(last);
  }
  const art = make("div", "lust-hero-art", "");
  if (data && data.last && data.last.splash) {
    const img = new Image();
    img.onload = () => { art.style.backgroundImage = `url("${img.src}")`; art.classList.add("on"); };
    img.src = data.last.splash;
  }
  hero.replaceChildren(art, ...parts);
}
function lustHero(page) {
  const hero = document.createElement("div");
  hero.className = "lust-hero";
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem("lust-hero") || "null"); } catch (error) {}
  lustHeroFill(hero, saved);
  page.appendChild(hero);
  lustHeroData().then((data) => {
    try { localStorage.setItem("lust-hero", JSON.stringify(data)); } catch (error) {}
    if (document.body.contains(hero) && JSON.stringify(data) !== JSON.stringify(saved)) lustHeroFill(hero, data);
  }).catch(() => {});
}
// Rose's own settings (injection, game path, mods) keep their panel.
function coreTab(section) {
  const note = document.createElement("div");
  note.className = "lust-customize-state";
  note.textContent = lustTr("Injection, the League path, custom mods and troubleshooting live in Lust's core settings.");
  const open = document.createElement("lol-uikit-flat-button");
  open.className = "lust-hub-primary";
  open.textContent = lustTr("Open core settings");
  open.addEventListener("click", () => {
    closeLustHub();
    const navItem = document.querySelector("lol-uikit-navigation-item.menu_item_Golden");
    window.dispatchEvent(new CustomEvent("lust-open-settings", { detail: { navItem, lustCore: true } }));
  });
  section.append(note, open);
}

// Lust Offline (lust/offline) takes commands as chat messages to its "Lust Active!" friend.
const LUST_OFFLINE_ID = "41c322a1-b328-495b-a004-5ccd3e45eae8@eu1.pvp.net";
const LUST_OFFLINE_STATUSES = [
  { command: "online", label: "Online", color: "#0acf83" },
  { command: "offline", label: "Offline", color: "#9a9a9a" },
  { command: "mobile", label: "Mobile", color: "#e8a33a" }
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
    note.textContent = lustTr("Lust Offline isn't running: close League and open it again to appear offline.");
    return;
  }
  let current = await lustOfflineStatus() || localStorage.getItem("lust-offline-status") || "offline";
  const buttons = LUST_OFFLINE_STATUSES.map(({ command, label, color }) => {
    const button = document.createElement("lol-uikit-flat-button");
    button.style.setProperty("--lust-status", color);
    const dot = document.createElement("span");
    dot.className = "lust-status-dot";
    button.append(dot, document.createTextNode(lustTr(label)));
    button.addEventListener("click", async () => {
      if (!await sendLustOffline(command)) {
        note.textContent = lustTr("Couldn't reach Lust Offline.");
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
    note.textContent = lustTr("Friends see you as {status}.", { status: lustTr(current) });
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
    .filter((item) => LustData.get(item.key))
    .map((item) => `${item.selector} { color: ${utils.sanitizeColor(LustData.get(item.key))} !important; }`)
    .join("\n");
}
// What changed in this version (LUST-News/whats-new.json), shown once per version.
async function newsCard(view) {
  let news;
  try {
    news = await (await fetch("//plugins/LUST-News/whats-new.json")).json();
  } catch {
    return;
  }
  let seen = "";
  try {
    seen = localStorage.getItem("lust-news-seen") || "";
  } catch {}
  if (!news || !news.version || seen === news.version)
    return;
  const language = window.LustI18n && window.LustI18n.language === "tr" ? "tr" : "en";
  const items = news[language] || news.en || [];
  const card = document.createElement("div");
  card.className = "lust-news";
  const title = document.createElement("div");
  title.className = "lust-news-title";
  title.textContent = lustTr("What's new in Lust {version}", { version: news.version });
  const list = document.createElement("ul");
  items.forEach((item) => {
    const entry = document.createElement("li");
    entry.textContent = item;
    list.appendChild(entry);
  });
  const done = document.createElement("lol-uikit-flat-button");
  done.textContent = lustTr("Got it");
  done.addEventListener("click", () => {
    try {
      localStorage.setItem("lust-news-seen", news.version);
    } catch {}
    card.remove();
  });
  card.append(title, list, done);
  view.appendChild(card);
}
// Every theme setting plus the lust-* ones other plugins keep in localStorage
// (Lobby Reveal's choices and box position), in one file to take to another PC.
function exportLustSettings() {
  const local = {};
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("lust-"))
        local[key] = localStorage.getItem(key);
    }
  } catch {}
  const backup = { app: "Lust", format: 1, saved: new Date().toISOString(), theme: LustData.getAll(), local };
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" }));
  link.download = "Lust-settings.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 10000);
}
function backupSection(section) {
  const row = document.createElement("div");
  row.className = "lust-status-row";
  const note = document.createElement("div");
  note.className = "lust-customize-state";
  note.textContent = lustTr("Keep your settings in a file, or bring them from another PC.");
  const save = document.createElement("lol-uikit-flat-button");
  save.textContent = lustTr("Export settings");
  save.addEventListener("click", () => {
    exportLustSettings();
    note.textContent = lustTr("Saved as Lust-settings.json");
  });
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json,application/json";
  input.style.display = "none";
  input.addEventListener("change", async () => {
    const file = input.files && input.files[0];
    input.value = "";
    if (!file) return;
    try {
      const backup = JSON.parse(await file.text());
      if (!backup || backup.app !== "Lust" || typeof backup.theme !== "object")
        throw new Error("not a Lust settings file");
      LustData.setAll(backup.theme);
      if (LustData.flush) await LustData.flush();
      for (const [key, value] of Object.entries(backup.local || {})) {
        if (key.startsWith("lust-") && typeof value === "string") {
          try {
            localStorage.setItem(key, value);
          } catch {}
        }
      }
      note.textContent = lustTr("Settings imported, reloading the client...");
      setTimeout(() => window.restartClient(), 1500);
    } catch {
      note.textContent = lustTr("That isn't a Lust settings file.");
    }
  });
  const load = document.createElement("lol-uikit-flat-button");
  load.textContent = lustTr("Import settings");
  load.addEventListener("click", () => input.click());
  row.append(save, load, input);
  section.append(row, note);
}
function colorSection(section) {
  const list = document.createElement("div");
  list.className = "lust-customize";
  LUST_COLORS.forEach((item) => {
    const row = document.createElement("div");
    row.className = "lust-customize-row";
    const label = document.createElement("span");
    label.textContent = lustTr(item.label);
    const picker = document.createElement("input");
    picker.type = "color";
    picker.value = LustData.get(item.key) || "#f0e6d2";
    const state = document.createElement("span");
    state.className = "lust-customize-state";
    const showState = () => {
      state.textContent = LustData.get(item.key) ? LustData.get(item.key) : lustTr("League default");
    };
    picker.addEventListener("input", () => {
      LustData.set(item.key, picker.value);
      showState();
      applyLustColors();
    });
    const reset = document.createElement("lol-uikit-flat-button");
    reset.textContent = lustTr("Default");
    reset.addEventListener("click", () => {
      LustData.set(item.key, "");
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
  #lust-hub-backdrop { position: fixed; inset: 0; z-index: 10050; display: flex; align-items: center;
    justify-content: center; background: rgba(1, 4, 9, .62); }
  #lust-hub { display: flex; width: min(860px, 92vw); height: min(600px, 86vh); background: #010a13;
    border: 1px solid #785a28; border-top: 2px solid #a78bfa; box-shadow: 0 12px 40px rgba(0, 0, 0, .6);
    color: #cdbe91; font-family: "Spiegel", "Arial", sans-serif; }
  .lust-hub-side { flex: 0 0 190px; display: flex; flex-direction: column; padding: 16px 0;
    background: #0a0f1a; border-right: 1px solid #785a2866; }
  .lust-hub-logo { padding: 0 18px 14px; color: #a78bfa; font: 700 18px "Beaufort for LOL", serif; letter-spacing: 3px; }
  .lust-hub-tab { display: flex; align-items: center; gap: 10px; padding: 10px 18px; cursor: pointer; color: #a09b8c;
    font-size: 13px; border-left: 2px solid transparent; }
  .lust-hub-tab svg { color: #6f6a60; flex: 0 0 auto; }
  .lust-hub-tab:hover { color: #f0e6d2; background: #ffffff08; }
  .lust-hub-tab.active { color: #f0e6d2; background: #8b5cf61f; border-left-color: #a78bfa; }
  .lust-hub-tab.active svg { color: #a78bfa; }
  .lust-hub-version { margin-top: auto; padding: 0 18px; color: #5b5a56; font-size: 11px; }
  .lust-hub-main { position: relative; flex: 1; min-width: 0; overflow-y: auto; padding: 20px 26px 24px; }
  .lust-hub-main::-webkit-scrollbar { width: 6px; }
  .lust-hub-main::-webkit-scrollbar-thumb { background: #785a28; }
  .lust-hub-close { position: absolute; top: 12px; right: 14px; cursor: pointer; color: #7e7a70; font-size: 18px; line-height: 1; }
  .lust-hub-close:hover { color: #f0e6d2; }
  .lust-hub-page { display: none; }
  .lust-hub-page.active { display: block; }
  .lust-hub-primary { display: inline-block; margin-top: 12px; min-width: 200px; }
  .lust-panel-reload { display: block; width: 220px; margin: 18px 0 4px; }
  .lust-hub-advanced { margin-top: 14px; border-top: 1px solid #785a2840; padding-top: 10px; }
  .lust-hub-advanced > summary { cursor: pointer; color: #7e7a70; font-size: 12px; letter-spacing: .5px; }
  .lust-hub-advanced > summary:hover { color: #cdbe91; }
  /* The theme's own sections, drawn in the hub's style */
  #lust-hub .theme-settings-section { margin: 0 0 18px; padding: 0; border: 0; background: none; }
  #lust-hub .theme-settings-section-title { display: block; margin: 0 0 10px; padding: 0 0 6px;
    border-bottom: 1px solid #785a2866; color: #f0e6d2; font: 700 13px "Beaufort for LOL", serif;
    letter-spacing: 1px; text-transform: uppercase; }
  #lust-hub .theme-settings-section-content { display: flex; flex-direction: column; gap: 6px; }
  #lust-hub lol-uikit-flat-checkbox { margin: 2px 0; }
  #lust-hub .lust-theme-settings-row { color: #cdbe91; font-size: 13px; }
  #lust-hub p, #lust-hub label { color: #cdbe91; }
  #lust-hub .lust-reveal-hub, #lust-hub .lust-rv-hub { margin: 0; }
  .lust-hub-section { margin-bottom: 18px; }
  .lust-hub-title { margin: 0 0 8px; padding-bottom: 4px; border-bottom: 1px solid #785a2866; color: #f0e6d2;
    font: 700 13px "Beaufort for LOL", serif; letter-spacing: 1px; text-transform: uppercase; }
  .lust-status-row { display: flex; gap: 8px; margin-bottom: 6px; }
  .lust-status-row lol-uikit-flat-button { flex: 1; }
  .lust-status-row .lust-status-active { filter: brightness(1.25); outline: 1px solid var(--lust-status, #c8aa6e); }
  .lust-status-dot { display: inline-block; width: 8px; height: 8px; margin-right: 8px; border-radius: 50%;
    vertical-align: 1px; background: var(--lust-status, #9a9a9a); }
  .lust-news { margin: 0 0 18px; padding: 12px 14px; border: 1px solid #c8aa6e;
    background: linear-gradient(160deg, #1b1430 0%, #010a13 80%); color: #cdbe91; font-size: 12px; }
  .lust-news-title { margin-bottom: 6px; color: #f0e6d2; font: 700 14px "Beaufort for LOL", serif; letter-spacing: 1px; }
  .lust-news ul { margin: 0 0 10px; padding-left: 18px; line-height: 1.6; }
  .lust-news lol-uikit-flat-button { width: 120px; }
  .lust-asset-row { margin: 10px 0; padding: 10px; border: 1px dashed #785a2866; transition: border-color .15s, background .15s; }
  .lust-asset-row.dragging { border-color: #c8aa6e; background: #c8aa6e14; }
  .lust-asset-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
    color: #f0e6d2; font: 700 13px "Beaufort for LOL", serif; }
  .lust-asset-head lol-uikit-flat-button { width: 110px; }
  .lust-asset-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .lust-asset-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 4px 3px 8px;
    border: 1px solid #3c3c41; background: #1e2328; color: #cdbe91; font-size: 12px; }
  .lust-asset-remove { cursor: pointer; padding: 0 4px; color: #a09b8c; font-size: 14px; line-height: 1; }
  .lust-asset-remove:hover { color: #e84057; }
  .lust-asset-hint { margin-top: 8px; color: #7e7a70; font-size: 11px; }
  .lust-asset-hint.error { color: #e84057; }
  .lust-hub-section.dragging { outline: 1px dashed #a78bfa; outline-offset: 6px; }
  .lust-skins-head { display: flex; align-items: center; gap: 14px; margin: 4px 0 10px; }
  .lust-skins-add { flex: 0 0 auto; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px;
    border: 1px solid #a78bfa; border-radius: 50%; color: #a78bfa; font: 300 28px/1 "Spiegel", "Arial", sans-serif;
    cursor: pointer; transition: background .15s, color .15s; }
  .lust-skins-add:hover { background: #a78bfa; color: #010a13; }
  .lust-skins-help { color: #a09b8c; font-size: 12px; line-height: 1.5; }
  .lust-skins-list { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
  .lust-skins-empty { padding: 18px; border: 1px dashed #785a2866; color: #7e7a70; font-size: 12px; text-align: center; }
  .lust-skin-row { display: flex; align-items: center; gap: 12px; padding: 8px 10px; border: 1px solid #1e2328; background: #0a0f1a; }
  .lust-skin-row.on { border-color: #a78bfa80; background: #8b5cf614; }
  .lust-skin-icon { flex: 0 0 36px; height: 36px; border: 1px solid #785a28; background: #1e2328 center / cover no-repeat; }
  .lust-skin-icon.changeable { cursor: pointer; }
  .lust-skin-icon.changeable:hover { border-color: #a78bfa; }
  .lust-skin-text { flex: 1; min-width: 0; }
  .lust-skin-title { color: #f0e6d2; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lust-skin-sub { color: #7e7a70; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lust-skin-pick { background: #1e2328; color: #cdbe91; border: 1px solid #785a28; padding: 4px; font-size: 12px; max-width: 150px; }
  .lust-skin-toggle { position: relative; flex: 0 0 38px; height: 20px; border-radius: 10px; background: #3c3c41; cursor: pointer;
    transition: background .15s; }
  .lust-skin-toggle::after { content: ""; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%;
    background: #a09b8c; transition: left .15s, background .15s; }
  .lust-skin-toggle.on { background: #a78bfa; }
  .lust-skin-toggle.on::after { left: 21px; background: #f0e6d2; }
  .lust-skin-toggle.off-limits { opacity: .4; cursor: default; }
  /* Lust hub, app style: an icon rail whose tiles grow under the mouse, rounded cards */
  #lust-hub { width: min(920px, 94vw); background: #16141f; border: 1px solid #2e2a3d; border-radius: 20px;
    overflow: hidden; box-shadow: 0 24px 60px rgba(0, 0, 0, .6); }
  .lust-hub-side { flex: 0 0 76px; align-items: center; gap: 12px; padding: 18px 0; background: #100e17; border-right: 1px solid #1c1926; }
  .lust-hub-logo { width: 44px; height: 44px; padding: 0; margin-bottom: 6px; border-radius: 14px; display: grid; place-items: center;
    background: linear-gradient(135deg, #7c3aed, #db2777); color: #fff; font: 800 20px Georgia, serif; letter-spacing: 0;
    box-shadow: 0 6px 18px rgba(124, 58, 237, .35); }
  .lust-hub-tab { position: relative; width: 44px; height: 44px; padding: 0; justify-content: center; border-left: 0; border-radius: 13px;
    background: #1d1a29; color: #a3a0ad; transition: transform .18s cubic-bezier(.3, 1.6, .5, 1), background .15s, color .15s; }
  .lust-hub-tab svg { width: 20px; height: 20px; color: inherit; }
  .lust-hub-tab:hover { transform: scale(1.18); background: #2a2540; color: #f0eef5; }
  .lust-hub-tab.active { background: linear-gradient(135deg, #7c3aed, #a78bfa); color: #fff; border-left-color: transparent;
    box-shadow: 0 6px 16px rgba(124, 58, 237, .4); }
  .lust-hub-tab.active svg { color: #fff; }
  .lust-hub-tab::after { content: attr(data-label); position: absolute; left: 56px; top: 50%; padding: 5px 10px; border-radius: 8px;
    background: #2a2540; color: #f0eef5; font-size: 12px; white-space: nowrap; opacity: 0; pointer-events: none; z-index: 5;
    transform: translate(-6px, -50%); transition: .15s; }
  .lust-hub-tab:hover::after { opacity: 1; transform: translate(0, -50%); }
  .lust-hub-main { background: #16141f; padding: 16px 26px 24px; }
  .lust-hub-main::-webkit-scrollbar-thumb { background: #2e2a3d; border-radius: 8px; }
  .lust-hub-heading { display: flex; align-items: center; gap: 10px; margin: 0 0 14px; color: #f0eef5; font: 600 17px "Spiegel", "Arial", sans-serif; }
  .lust-hub-version { margin: 0; padding: 3px 10px; border-radius: 99px; background: #211e2d; border: 1px solid #2e2a3d; color: #a3a0ad; font-size: 11px; font-weight: 400; }
  .lust-hub-close { top: 16px; right: 18px; width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; }
  .lust-hub-close:hover { background: #c42b4a; color: #fff; }
  .lust-hero { position: relative; overflow: hidden; margin-bottom: 14px; padding: 18px 20px; min-height: 120px; border-radius: 18px;
    color: #fff; display: flex; align-items: flex-end; gap: 14px;
    background: linear-gradient(120deg, #7c3aed 0%, #a21caf 55%, #db2777 100%); }
  .lust-hero-art { position: absolute; inset: 0; background-size: cover; background-position: center 22%; opacity: 0;
    transition: opacity .8s ease; animation: lust-drift 24s ease-in-out infinite alternate; }
  .lust-hero-art.on { opacity: 1; }
  .lust-hero::before { content: ""; position: absolute; inset: 0; z-index: 1;
    background: linear-gradient(90deg, rgba(22, 14, 40, .92) 0%, rgba(60, 20, 90, .55) 55%, rgba(219, 39, 119, .25) 100%); }
  @keyframes lust-drift { from { transform: scale(1.08); } to { transform: scale(1.14) translateX(-2%); } }
  .lust-hero-body, .lust-hero-last { position: relative; z-index: 2; }
  .lust-hero-body { flex: 1; min-width: 0; }
  .lust-hero small { display: block; opacity: .8; font-size: 12px; }
  .lust-hero b { display: block; margin: 2px 0 8px; font: 700 24px "Spiegel", "Arial", sans-serif; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }
  .lust-hero b i { font-style: normal; font-weight: 400; opacity: .6; font-size: 17px; }
  .lust-hero span { opacity: .9; font-size: 12px; }
  .lust-hero-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .lust-hero-cut { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 8px; font-size: 11.5px; }
  .lust-cut { display: inline-flex; align-items: center; gap: 5px; }
  .lust-cut::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--c); box-shadow: 0 0 8px var(--c); }
  .lust-cut.gm { --c: #f87171; } .lust-cut.ch { --c: #facc15; }
  .lust-cut-need { padding: 2px 8px; border-radius: 99px; background: rgba(250, 204, 21, .16); color: #fde68a; font-weight: 600;
    opacity: 1 !important; }
  .lust-chip { padding: 4px 10px; border-radius: 99px; font-size: 11.5px; font-weight: 600; opacity: 1 !important;
    background: rgba(255, 255, 255, .14); border: 1px solid rgba(255, 255, 255, .18); }
  .lust-chip.rank { background: linear-gradient(135deg, rgba(167, 139, 250, .5), rgba(219, 39, 119, .45)); }
  .lust-hero-last { flex: none; text-align: right; padding: 10px 14px; border-radius: 14px; background: rgba(10, 8, 18, .5);
    border: 1px solid rgba(255, 255, 255, .12); }
  .lust-hero-last b { font-size: 16px; margin: 2px 0; }
  .lust-hero-last span { display: block; font-size: 11.5px; }
  .lust-hero-result { font-weight: 700; } .lust-hero-result.win { color: #4ade80; } .lust-hero-result.loss { color: #f87171; }
  /* Lust's icons: a purple-to-pink gradient line */
  .lust-hub-tab:not(.active) svg { stroke: url(#lust-grad); filter: drop-shadow(0 0 5px rgba(167, 139, 250, .35)); }
  .lust-hub-tab:active { transform: scale(.92); transition-duration: .06s; }
  /* Motion: cards rise in turn */
  @keyframes lust-rise { from { opacity: 0; transform: translateY(10px) scale(.985); } }
  .lust-hub-page.active > * { animation: lust-rise .45s cubic-bezier(.2, .8, .2, 1) both; }
  .lust-hub-page.active > *:nth-child(2) { animation-delay: .05s; } .lust-hub-page.active > *:nth-child(3) { animation-delay: .1s; }
  .lust-hub-page.active > *:nth-child(4) { animation-delay: .15s; } .lust-hub-page.active > *:nth-child(5) { animation-delay: .2s; }
  .lust-hub-page.active > *:nth-child(n+6) { animation-delay: .25s; }
  .lust-skin-toggle::after { transition: left .3s cubic-bezier(.3, 1.6, .5, 1), background .15s; }
  #lust-hub lol-uikit-flat-button:active { transform: scale(.96); }
  .lust-hub-section, #lust-hub .theme-settings-section { margin: 0 0 12px; padding: 14px 16px; border-radius: 14px;
    background: #211e2d; border: 1px solid transparent; }
  .lust-hub-title, #lust-hub .theme-settings-section-title { border-bottom: 0; padding-bottom: 0; margin-bottom: 10px;
    color: #a3a0ad; font: 600 11.5px "Spiegel", "Arial", sans-serif; letter-spacing: .5px; }
  .lust-news { border-radius: 14px; border-color: #4b3f73; background: #2a2340; }
  .lust-skin-row { border-radius: 12px; background: #1d1a29; border-color: transparent; transition: transform .15s, background .15s; }
  .lust-skin-row:hover { transform: translateY(-2px); background: #262236; }
  .lust-asset-row { border-radius: 12px; border-color: #2e2a3d; }
  .lust-hub-advanced { border-top: 0; }
  .lust-customize { display: flex; flex-direction: column; gap: 10px; padding: 4px 2px 8px; }
  .lust-customize-row { display: grid; grid-template-columns: 1fr 36px 96px 80px; align-items: center; gap: 8px;
    color: #cdbe91; font: 13px "Beaufort for LOL", serif; }
  .lust-customize-row input[type="color"] { width: 36px; height: 24px; padding: 0; border: 1px solid #785a28;
    background: none; cursor: pointer; }
  .lust-customize-state { color: #a09b8c; font-size: 11px; }
`;
let lustHubTab = "status";
function closeLustHub() {
  document.getElementById("lust-hub-backdrop")?.remove();
  document.querySelector("lol-uikit-navigation-item.menu_item_Golden")?.removeAttribute("active");
}
function openLustHub() {
  if (document.getElementById("lust-hub-backdrop"))
    return;
  const backdrop = document.createElement("div");
  backdrop.id = "lust-hub-backdrop";
  backdrop.addEventListener("mousedown", (event) => {
    if (event.target === backdrop) closeLustHub();
  });
  const hub = document.createElement("div");
  hub.id = "lust-hub";
  const side = document.createElement("div");
  side.className = "lust-hub-side";
  const logo = document.createElement("div");
  logo.className = "lust-hub-logo";
  logo.textContent = "L";
  side.appendChild(logo);
  const main = document.createElement("div");
  main.className = "lust-hub-main";
  const close = document.createElement("div");
  close.className = "lust-hub-close";
  close.textContent = "\u00d7";
  close.title = lustTr("Close");
  close.addEventListener("click", closeLustHub);
  main.appendChild(close);
  // The page's title and Lust's version above every tab
  const heading = document.createElement("div");
  heading.className = "lust-hub-heading";
  const headingTitle = document.createElement("span");
  const version = document.createElement("span");
  version.className = "lust-hub-version";
  heading.append(headingTitle, version);
  main.appendChild(heading);
  const select = async (tab) => {
    lustHubTab = tab.id;
    headingTitle.textContent = lustTr(tab.label);
    side.querySelectorAll(".lust-hub-tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === tab.id));
    main.querySelectorAll(".lust-hub-page").forEach((page) => page.classList.toggle("active", page.dataset.tab === tab.id));
    main.scrollTop = 0;
    const page = main.querySelector(`.lust-hub-page[data-tab="${tab.id}"]`);
    if (page.dataset.rendered) return;
    page.dataset.rendered = "true";
    try {
      await tab.render(page);
    } catch (err) {
      error(`Lust hub: ${tab.id} failed`, err);
    }
    if (tab.reload) {
      const reload = document.createElement("lol-uikit-flat-button");
      reload.className = "lust-panel-reload";
      reload.textContent = lustTr("Reload client to apply");
      reload.addEventListener("click", () => window.restartClient());
      page.appendChild(reload);
    }
  };
  LUST_HUB_TABS.forEach((tab) => {
    const item = document.createElement("div");
    item.className = "lust-hub-tab";
    item.dataset.tab = tab.id;
    item.innerHTML = lustHubIcon(tab.icon);
    item.dataset.label = lustTr(tab.label);
    item.addEventListener("click", () => select(tab));
    side.appendChild(item);
    const page = document.createElement("div");
    page.className = "lust-hub-page";
    page.dataset.tab = tab.id;
    main.appendChild(page);
  });
  fetch("//plugins/LUST-News/whats-new.json").then((r) => r.json()).then((news) => {
    version.textContent = `Lust ${news.version}`;
  }).catch(() => {});
  hub.append(side, main);
  backdrop.appendChild(hub);
  document.body.appendChild(backdrop);
  document.querySelector("lol-uikit-navigation-item.menu_item_Golden")?.setAttribute("active", "true");
  select(LUST_HUB_TABS.find((tab) => tab.id === lustHubTab) || LUST_HUB_TABS[0]);
}
// Rose's panel, now opened only for core settings: drop its Discord and Ko-Fi links.
function cleanRosePanel(panel) {
  const links = panel.querySelector(".settings-links");
  if (!links) return false;
  links.querySelectorAll("a").forEach((link) => {
    if (/discord\.com|ko-fi\.com/.test(link.href)) link.remove();
  });
  return true;
}
function mountLustHub() {
  const style = document.createElement("style");
  style.textContent = LUST_PANEL_CSS;
  document.head.appendChild(style);
  const defs = document.createElement("div");
  defs.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
  defs.innerHTML = '<svg width="0" height="0" aria-hidden="true"><defs><linearGradient id="lust-grad" x1="0" y1="0" x2="1" y2="1">'
    + '<stop offset="0" stop-color="#c4b5fd"/><stop offset=".55" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/>'
    + '</linearGradient></defs></svg>';
  document.body.appendChild(defs);
  // A click on LUST opens the hub. Caught on the way down, before LUST-UI's own
  // listener on the nav item; with Rose's panel open the click goes through to close it.
  document.addEventListener("click", (event) => {
    const navItem = event.target.closest && event.target.closest("lol-uikit-navigation-item.menu_item_Golden");
    if (!navItem || document.getElementById("lust-settings-panel")) return;
    event.stopPropagation();
    event.preventDefault();
    if (document.getElementById("lust-hub-backdrop")) closeLustHub();
    else openLustHub();
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.getElementById("lust-hub-backdrop")) closeLustHub();
  });
  new MutationObserver(() => {
    const panel = document.getElementById("lust-settings-panel");
    if (!panel || panel.dataset.lustCleaned) return;
    panel.dataset.lustCleaned = "true";
    let tries = 0;
    const attempt = () => {
      if (document.body.contains(panel) && !cleanRosePanel(panel) && ++tries < 40) setTimeout(attempt, 100);
    };
    attempt();
  }).observe(document.body, { childList: true });
}
window.writeBackupData = writeBackupData;

function transparentLobby(context) {
  context.socket.observe("/lol-gameflow/v1/gameflow-phase", async (data) => {
    if (data["data"] == "Matchmaking") {
      let a = document.getElementsByClassName("placeholder-invited-container");
      for (let i = 0; i < a.length; i++) {
        let div = document.createElement("div");
        div.classList.add("placeholder-invited-image");
        a[i].querySelector(".placeholder-invited-video").remove();
        a[i].append(div);
      }
    }
  });
}

let autoQueue = false;
async function getQueueList() {
  const queueData = await (await fetch("/lol-game-queues/v1/queues")).json();
  const invalidIds = [700, 720, 1110, 2010, 2020, 2e3];
  const queueList = queueData.filter((queue) => queue.queueAvailability === "Available" && !invalidIds.includes(queue.id)).map((queue) => ({ queueId: queue.id, description: queue.name })).sort((a, b) => a.queueId - b.queueId);
  LustData.set("queueList", { Gamemode: queueList });
}
async function createQueue(data) {
  await fetch("/lol-lobby/v2/lobby", {
    method: "POST",
    body: JSON.stringify({ queueId: data }),
    headers: {
      "Content-Type": "application/json"
    }
  });
}
async function matchMaking() {
  await fetch("/lol-lobby/v2/lobby/matchmaking/search", {
    method: "POST"
  });
}
function AutoQueue(context) {
  context.socket.observe("/lol-gameflow/v1/gameflow-phase", async (data) => {
    const gamePhase = data.data;
    if (LustData.get("Auto-Find-Queue")) {
      switch (gamePhase) {
        case "EndOfGame": {
          autoQueue = true;
          let delay = LustData.get("Create-Delay") / 1e3;
          log(`Auto Queue will start in %c${delay}%c seconds`, "color: #blue;", "");
          let countDown = new Promise((resolve, reject) => {
            setTimeout(async () => {
              resolve();
              if (!LustData.get("aram-only"))
                await createQueue(LustData.get("Gamemode"));
              else
                await createQueue(450);
            }, delay * 1e3);
          });
          Toast.promise(countDown, {
            loading: `Auto Queue will start in ${delay} seconds`,
            success: "Queue created!!",
            error: ""
          });
          break;
        }
        case "Lobby": {
          if (autoQueue) {
            let delay = LustData.get("Find-Delay") / 1e3;
            let countDown = new Promise((resolve, reject) => {
              setTimeout(async () => {
                resolve();
                await matchMaking();
              }, delay * 1e3);
            });
            Toast.promise(countDown, {
              loading: `Matching game will start in ${delay} seconds`,
              success: "",
              error: ""
            });
          }
          break;
        }
        case "Matchmaking": {
          autoQueue = false;
          break;
        }
        case "ChampSelect": {
          autoQueue = true;
          break;
        }
        case "None": {
          autoQueue = false;
          log("Auto Queue stopped");
          break;
        }
        default:
          log(`Unexpected game phase: %c${gamePhase}`, "color: #e4c2b3;");
      }
    }
  });
}
observer.subscribeToElementCreation(".rcp-fe-lol-activity-center", (element) => {
  if (element) {
    getQueueList();
    log("Queue list refreshed.");
  }
});

var m = class {
    constructor(o) {
        this.Context = o;
    }
};

var p;
function D(t) {
    if (p != null) throw new Error("UPL is already initialized!")
    p = new m(t);
}

var d = class {
    constructor(o) {
        this._callback = o;
    }
    trigger() {
        this._callback !== void 0 && (this._callback(), (this._callback = void 0));
    }
};
var f = {},
P = new d(A);

function E(t, o) {
    P.trigger();
    var e = f[t];
    e === void 0 ? (f[t] = { pre_callback: o, post_callback: void 0 }) : (f[t].pre_callback = o);
}
function M(t, o) {
    P.trigger();
    var e = f[t];
    e === void 0 ? (f[t] = { pre_callback: void 0, post_callback: o }) : (f[t].post_callback = o);
}
function I(t, o) {
    E(t, (e, i, n) => {
        if (typeof i != "string") return console.error("UPL: Tried to hook text XHR request but body is not a string!"), n(i);
        o(i, (c) => {
            n(c);
        });
    });
}

function U(t, o) {
    M(t, (e, i) => {
        if (e.responseType !== "" && e.responseType !== "text") return console.error("UPL: Tried to hook text XHR request but response is not a string!"), i();
        let n = (r) => {
            e.responseText != r && Object.defineProperty(e, "responseText", { writable: !0, value: r }), i();
        };
        o(this.responseText, n);
    });
}
var $ = XMLHttpRequest.prototype.open;

function X(t, o) {
    var e = f[o.toString()];
    if (e !== void 0) {
        let i = this.send;
        this.send = function (n) {
            if (n instanceof Document) return i.apply(this, [n]);
            if (e.pre_callback !== void 0) {
                let r = (c) => {
                    n = c;
                };
                e.pre_callback(this, n || null, r);
            }
            if (e.post_callback !== void 0) {
                let r = this.onreadystatechange;
                this.onreadystatechange = function (c) {
                    if (this.readyState === 4 && e.post_callback !== void 0) {
                        let l = () => {
                            r.apply(this, [c]);
                        };
                        e.post_callback(this, l);
                        return;
                    }
                    return r.apply(this, arguments);
                };
            }
            i.apply(this, [n]);
        };
    }
    $.apply(this, arguments);
}

function A() {
    XMLHttpRequest.prototype.open = X;
}

var G = Object.freeze(Object.defineProperty({ __proto__: null, hookPost: M, hookPre: E, hookTextPost: U, hookTextPre: I }, Symbol.toStringTag, { value: "Module" })),
C = {},
K = new d(F);

function S(t, o) {
    K.trigger(), (C[t] = o);
}

function q(t, o) {
    S(t, (e, i) => {
        if (typeof e != "string") return console.error("UPL: Tried to hook text websocket endpoint but content is not a string!"), i(e);
        o(e, (r) => {
            i(r);
        });
    });
}

function F() {
    let t = p?.Context;
    if (t == null) throw new Error("UPL is not initialized!");
    t.rcp.postInit("rcp-fe-common-libs", async (o) => {
        let e = o.getDataBinding;
        o.getDataBinding = async function (i) {
            let n = await e.apply(this, arguments),
                r = function (c, l) {
                    let a = n.apply(this, arguments),
                        h = a.cache,
                        b = h._triggerResourceObservers;
                    return (
                        (h._triggerResourceObservers = function (s, u, x) {
                            let O = C[s];
                            return O == null
                                ? b.apply(this, [s, u, x])
                                : O(u, (B) => {
                                    b.apply(this, [s, B, x]);
                                });
                        }),
                        a
                    );
                };
            return (
                (r.bindTo = function (c) {
                    let l = n.bindTo.apply(this, arguments);
                    return (l.dataBinding = r), l;
                }),
                Promise.resolve(r)
            );
        };
    });
}

var J = Object.freeze(Object.defineProperty({ __proto__: null, hook: S, hookText: q }, Symbol.toStringTag, { value: "Module" })),
g = new Map(),
v = [],
y = new d(Z);

function Q(t, o, e) {
    y.trigger();
    var i = { method: o, callback: e },
        n = g.get(t);
    n === void 0 ? g.set(t, { hooks: [i], mixins: [] }) : n.hooks.push(i);
}

function V(t, o, e) {
    y.trigger();
    var i = { method: o, callback: e };
    v.push({ matcher: t, entry: { hooks: [i], mixins: [] } });
}

function W(t, o) {
    y.trigger();
    var e = g.get(t);
    e === void 0 ? g.set(t, { hooks: [], mixins: [o] }) : e.mixins.push(o);
}

function Y(t, o) {
    y.trigger(), v.push({ matcher: t, entry: { hooks: [], mixins: [o] } });
}

function Z() {
    let t = p?.Context;
    if (t == null) throw new Error("UPL is not initialized!");
    t.rcp.postInit("rcp-fe-ember-libs", async (o) => {
        let e = o.getEmber;
        o.getEmber = function (...i) {
            let n = e.apply(this, i);
            return (
                n.then((r) => {
                    let c = r.Component.extend;
                    return (
                        (r.Component.extend = function (...l) {
                            let a = c.apply(this, arguments),
                                h = l.filter((s) => typeof s == "object");
                            for (let s of h) for (let u of v) u.matcher(s) && (a = w(r, u.entry, a));
                            let b = h.filter((s) => s.classNames && Array.isArray(s.classNames)).map((s) => s.classNames.join(" "));
                            for (let s of b) {
                                let u = g.get(s);
                                u !== void 0 && (a = w(r, u, a));
                            }
                            return a;
                        }),
                        r
                    );
                }),
                n
            );
        };
    });
}

function w(t, o, e) {
    let i = e.proto();
    if (i.__UPL_IS_HOOKED) return e;
    i.__UPL_IS_HOOKED = !0;
    for (let n of o.mixins) e = e.extend(n(t));
    for (let n of o.hooks) {
        let r = i[n.method];
        i[n.method] = function (...c) {
            let l = (...a) => {
                if (r != null) return r.apply(this, a);
            };
            return n.callback.call(this, t, l, ...c);
        };
    }
    return e;
}

var tt = Object.freeze(Object.defineProperty({ __proto__: null, extendClassByMatching: Y, extendClassByName: W, hookComponentMethodByMatching: V, hookComponentMethodByName: Q }, Symbol.toStringTag, { value: "Module" })),
j = Object.freeze(Object.defineProperty({ __proto__: null, ember: tt, ws: J, xhr: G }, Symbol.toStringTag, { value: "Module" }));

function L(t) {
    if (t.rcp === void 0 || typeof t.rcp.preInit != "function" || typeof t.rcp.postInit != "function") throw new Error("context is not a valid Pengu Context!");
    D(t);
}

/**
 * @wiki Automatically skips the post-game honor voting screen when Auto Queue is enabled. Instantly submits the honor ballot so you go straight back to the lobby without having to manually honor a player.
 * @author Lust
 * @settings Auto-Find-Queue
 */
function skipHonor(context) {
    if (LustData.get("Auto-Find-Queue")) {
        L(context),
        j.ember.extendClassByMatching(
            (o) => o.baseClassName === "honor-vote-ceremony-v3",
            () => ({
                beginTransition: function () {
                    this.set("selectionChosen", !0),
                        (this._beginTransitionTimer = null),
                        this.runTask(function () {
                            this.submitBallot();
                        }, 0);
                },
                willRender: function () {
                    this.send("submitSelection");
                },
            })
        );
    }
}

class FileSystem {
  isContextFSExist = true;
  context = null;
  currentWallpaperList = [];
  currentAudioList = [];
  currentBannerList = [];
  currentFontList = [];
  read = async (path) => {
    return await this.context?.fs.read(path);
  };
  write = async (path, content, enableAppendMode = false) => {
    return await this.context?.fs.write(path, content, { append: enableAppendMode }) ?? false;
  };
  mkdir = async (path) => {
    return await this.context?.fs.mkdir(path) ?? false;
  };
  stat = async (path) => {
    return await this.context?.fs.stat(path);
  };
  ls = async (path) => {
    return await this.context?.fs.ls(path);
  };
  rm = async (path, options) => {
    return await this.context?.fs.rm(path, options) ?? 0;
  };
  init = async (context) => {
    if (!context.fs) {
      error("context.fs is missing");
      this.isContextFSExist = false;
      this.context = null;
      window.refreshLists = async () => {
      };
      window.isContextFSExist = this.isContextFSExist;
      return;
    }
    this.isContextFSExist = true;
    this.context = context;
    await this.mkdir("./data");
    const readFile = (path) => this.read(path);
    window.lustReadFile = readFile;
    const writeFile = (path, content, enableAppendMode) => this.write(path, content, enableAppendMode);
    window.lustWriteFile = writeFile;
    const mkdir = (path) => this.mkdir(path);
    window.lustMkdir = mkdir;
    const stat = (path) => this.stat(path);
    window.lustStat = stat;
    const ls = (path) => this.ls(path);
    window.lustLs = ls;
    const rm = (path, options) => this.rm(path, options);
    window.lustRm = rm;
    const globalRefreshLists = () => this.refreshLists();
    window.refreshLists = globalRefreshLists;
    window.isContextFSExist = this.isContextFSExist;
  };
  refreshLists = async () => {
    const wallpaper = await this.ls("./assets/backgrounds/wallpapers") ?? [];
    const audio = await this.ls("./assets/backgrounds/audio") ?? [];
    const banner = await this.ls("./assets/icon/regalia-banners") ?? [];
    const font = await this.ls("./assets/fonts") ?? [];
    const dataLists = {
      Wallpaper: wallpaper,
      Audio: audio,
      Banner: banner,
      Font: font
    };
    const filteredLists = Object.keys(fileRegex).reduce((acc, key) => {
      acc[key] = dataLists[key].filter((file) => fileRegex[key].test(file));
      return acc;
    }, {});
    Object.entries(filteredLists).forEach(([key, list]) => {
      const prevList = key === "Wallpaper" ? this.currentWallpaperList : key === "Audio" ? this.currentAudioList : key === "Banner" ? this.currentBannerList : key === "Font" ? this.currentFontList : [];
      if (LustData && JSON.stringify(prevList) !== JSON.stringify(list)) {
        log(`List changed for ${key}`);
        LustData.set(`${key}-list`, list);
        del_webm_buttons();
        create_webm_buttons();
      }
      if (key === "Audio")
        this.currentAudioList = list;
      else if (key === "Wallpaper")
        this.currentWallpaperList = list;
      else if (key === "Banner")
        this.currentBannerList = list;
      else if (key === "Font")
        this.currentFontList = list;
    });
  };
}
const fileSystem = new FileSystem();

const LocalKey = 20260515450;

const updateTypeLocaleKeys = {
  Auto: "common.auto-update",
  Manual: "common.manual-update",
  New: "common.new-update"
};
class CheckUpdate {
  cdnUpdate = null;
  cdnServer = null;
  cdnKey = LocalKey;
  fetchCdnData = async () => {
    this.cdnServer = (await import(`//plugins/${getThemeName()}/config/cdnServer.js`)).default;
    const cdnUrl = `${this.cdnServer["cdn-url"]}lust-theme-data@${this.cdnServer["version"]}`;
    const localUrl = `//plugins/${getThemeName()}/lust-theme-data`;
    try {
      let updateModule;
      if (LustData.get("Dev-mode")) {
        updateModule = await cdnImport(`${localUrl}/src/update/update.js`, "Can't load update data");
        log("%cRunning Lust theme - %cDev version", "color: #e4c2b3", "color: red");
      } else {
        updateModule = await cdnImport(`${cdnUrl}/src/update/update.js`, "Can't load update data");
        log("%cRunning Lust theme - %cStable version", "color: #e4c2b3", "color: #00ff44");
      }
      this.cdnUpdate = updateModule.default;
      this.cdnKey = updateModule.default.key;
    } catch {
      this.cdnKey = LocalKey;
      log("%cRunning Lust theme - %cChecking version error", "color: #e4c2b3", "color:rgb(229, 255, 0)");
      warn("Failed to load CDN update data, skipping update check");
    }
    if (this.cdnKey === LocalKey) {
      try {
        if (!LustData.get("Change-CDN-version")) {
          const response = await fetch(`${cdnUrl}/package.json`);
          const { version: cdnVersion } = await response.json();
          LustData.set("Cdn-version", cdnVersion);
        }
      } catch (err) {
        error("Can't get theme version", err);
      }
    }
  };
  determineUpdateAction = (cdn) => {
    const keySame = LocalKey === cdn.key;
    const updateType = cdn["update-type"];
    if (keySame) {
      if (updateType === "New")
        return "changelog-new";
      return "changelog";
    }
    if (!keySame && updateType === "Manual")
      return "force-update";
    return "none";
  };
  escapeHtml = (text) => {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  };
  createCheckbox = (text, datastoreName) => {
    const container = document.createElement("div");
    container.style.width = "fit-content";
    container.style.marginLeft = "18px";
    const origin = document.createElement("lol-uikit-flat-checkbox");
    const checkbox = document.createElement("input");
    const label = document.createElement("label");
    checkbox.type = "checkbox";
    checkbox.id = "update-checkbox-input";
    checkbox.setAttribute("slot", "input");
    if (LustData.get(datastoreName)) {
      checkbox.checked = true;
      origin.setAttribute("class", "checked");
    }
    checkbox.onclick = () => {
      const current = LustData.get(datastoreName);
      LustData.set(datastoreName, !current);
      checkbox.checked = !current;
      origin.setAttribute("class", !current ? "checked" : "");
    };
    label.innerHTML = text;
    label.setAttribute("slot", "label");
    origin.appendChild(checkbox);
    origin.appendChild(label);
    container.appendChild(origin);
    return container;
  };
  waitForManager = async () => {
    const getManager = () => document.getElementById("lol-uikit-layer-manager-wrapper");
    while (!getManager())
      await new Promise((r) => setTimeout(r, 200));
    return getManager();
  };
  setupCloseButton = () => {
    const interval = window.setInterval(() => {
      try {
        const frame = document.querySelector("#Lust-Update lol-uikit-dialog-frame");
        const closeButton = frame?.shadowRoot?.querySelector(
          "div.lol-uikit-dialog-frame-close-button > lol-uikit-close-button"
        );
        if (closeButton) {
          closeButton.addEventListener("click", () => {
            document.getElementById("Lust-Update").hidden = true;
          });
          window.clearInterval(interval);
        }
      } catch {
      }
    }, 500);
  };
  showChangelogDialog = async (cdn, showDownload) => {
    const manager = await this.waitForManager();
    const closeText = await getString("preset-settings.close");
    const downloadText = await getString("preset-settings.download");
    const changelogHtml = cdn.text.map((t) => `<p class="Lust-Update">${this.escapeHtml(t)}</p>`).join("");
    const root = document.createElement("div");
    root.innerHTML = `
			<div class="modal" style="position: absolute; inset: 0px; z-index: 8500;" id="Lust-Update">
				<lol-uikit-full-page-backdrop class="backdrop" style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px;"></lol-uikit-full-page-backdrop>
				<div class="dialog-confirm" style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px;">
					<lol-uikit-dialog-frame class="dialog-frame" orientation="bottom" close-button="false">
						<div class="dialog-content">
							<lol-uikit-content-block class="app-controls-exit-dialog" type="dialog-small" style="width: 500px;" id="lust-update-text">
								<h5>Lust - ${await getString(updateTypeLocaleKeys[cdn["update-type"]])} ${this.escapeHtml(cdn.version)}</h5>
								<hr class="heading-spacer" />
								${changelogHtml}
							</lol-uikit-content-block>
						</div>
						<lol-uikit-flat-button-group type="dialog-frame" id="update-button-group">
						</lol-uikit-flat-button-group>
					</lol-uikit-dialog-frame>
				</div>
			</div>
		`;
    const buttonGroup = root.querySelector("#update-button-group");
    const closeBtn = document.createElement("lol-uikit-flat-button");
    closeBtn.setAttribute("tabindex", "1");
    closeBtn.className = "button-decline";
    closeBtn.textContent = closeText;
    closeBtn.addEventListener("click", () => {
      document.getElementById("Lust-Update").hidden = true;
    });
    buttonGroup.appendChild(closeBtn);
    if (showDownload) {
      const downloadBtn = document.createElement("lol-uikit-flat-button");
      downloadBtn.setAttribute("tabindex", "1");
      downloadBtn.style.marginLeft = "10px";
      downloadBtn.textContent = downloadText;
      downloadBtn.addEventListener("click", () => {
        window.open(`https://github.com/lustmyself/Lust/releases`);
      });
      buttonGroup.appendChild(downloadBtn);
    }
    manager.prepend(root);
    this.setupCloseButton();
  };
  showForceUpdateDialog = async (cdn) => {
    const manager = await this.waitForManager();
    const downloadText = await getString("preset-settings.download");
    const preventText = await getString("theme-settings.prevent-manual-update");
    const root = document.createElement("div");
    root.innerHTML = `
			<div class="modal" style="position: absolute; inset: 0px; z-index: 8500;" id="Lust-Update">
				<lol-uikit-full-page-backdrop class="backdrop" style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px;"></lol-uikit-full-page-backdrop>
				<div class="dialog-confirm" style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px;">
					<lol-uikit-dialog-frame class="dialog-frame" orientation="bottom" close-button="false">
						<div class="dialog-content">
							<lol-uikit-content-block class="app-controls-exit-dialog" type="dialog-small" style="width: 520px;">
								<h5>Lust - ${await getString(updateTypeLocaleKeys[cdn["update-type"]])} </h5>
								<hr class="heading-spacer" />
								<hr class="heading-spacer" />
								<p class="Lust-Update" style="text-align: center">${await getString("common.update-available-1")}</p>
								<p class="Lust-Update" style="text-align: center">${await getString("common.update-available-2")}</p>
								<hr class="heading-spacer" />
								<p class="Lust-Update" style="text-align: center">Meow ~~~</p>
								<div id="force-update-checkbox"></div>
							</lol-uikit-content-block>
						</div>
						<lol-uikit-flat-button-group type="dialog-frame">
						</lol-uikit-flat-button-group>
					</lol-uikit-dialog-frame>
				</div>
			</div>
		`;
    const checkboxContainer = root.querySelector("#force-update-checkbox");
    checkboxContainer.appendChild(this.createCheckbox(preventText, "prevent-manual-update"));
    const buttonGroup = root.querySelector("lol-uikit-flat-button-group");
    const downloadBtn = document.createElement("lol-uikit-flat-button");
    downloadBtn.setAttribute("tabindex", "1");
    downloadBtn.textContent = downloadText;
    downloadBtn.addEventListener("click", () => {
      window.open(`https://github.com/lustmyself/Lust/releases`);
    });
    buttonGroup.appendChild(downloadBtn);
    manager.prepend(root);
    this.setupCloseButton();
  };
  main = async () => {
    log(`%cChecking theme version...`, "color: #e4c2b3");
    await this.fetchCdnData();
    try {
      if (!this.cdnUpdate) {
        warn("No CDN update data available, skipping update check");
        return;
      }
      const cdn = this.cdnUpdate;
      const localVersion = LustData.get("Theme-version") || "";
      if (!localVersion) {
        LustData.set("Theme-version", cdn.version);
        log(`%cFirst install detected, saved version: ${cdn.version}`, "color: #e4c2b3");
      }
      const action = this.determineUpdateAction(cdn);
      log(`%cLocal  : %cv${LustData.get("Theme-version")} (key: ${LocalKey})`, "color: #e4c2b3", "color: #00ff44");
      log(`%cCDN    : %cv${cdn.version} (key: ${cdn.key}, type: ${cdn["update-type"]})`, "color: #e4c2b3", "color: #00ff44");
      log(`%cAction : %c${action}`, "color: #e4c2b3", "color: #00ff44");
      switch (action) {
        case "changelog":
        case "changelog-new": {
          if (LustData.get("changelog-shown-version") === cdn.version) {
            log(`%cChangelog already shown for v${cdn.version}`, "color: #e4c2b3");
            window.Toast.success("Latest release now");
            return;
          }
          window.Toast.success(`New changelog available: v${cdn.version}`);
          window.addEventListener("load", async () => {
            await this.showChangelogDialog(cdn, action === "changelog-new");
            LustData.set("changelog-shown-version", cdn.version);
            LustData.set("Theme-version", cdn.version);
            log(`%cChangelog displayed for v${cdn.version}`, "color: #e4c2b3");
          });
          break;
        }
        case "force-update": {
          if (LustData.get("prevent-manual-update")) {
            log(`%cManual update notification disabled by user`, "color: #e4c2b3");
            return;
          }
          window.Toast.error("New theme manual update available");
          window.addEventListener("load", async () => {
            await this.showForceUpdateDialog(cdn);
            log(`%cForce update notification displayed`, "color: #e4c2b3");
          });
          break;
        }
        case "none":
        default: {
          log(`%cNo update action required`, "color: #e4c2b3");
          let checkVersion = new Promise((resolve) => {
            setTimeout(() => resolve(), 2e3);
          });
          window.Toast.promise(checkVersion, {
            loading: "Checking theme version...",
            success: "Latest release now",
            error: "Version check failed"
          });
          break;
        }
      }
    } catch (err) {
      error("Update check failed", err);
    }
  };
}

class RemoveGamemode {
  /**
   * Removes a DOM node if it exists.
   * @param obj The selector for the DOM node to remove.
   */
  removeNode(obj) {
    try {
      document.querySelector(obj)?.remove();
    } catch (err) {
      error(`Can not remove ${obj}:`, err);
    }
  }
  removeSR5v5 = () => {
    this.removeNode("div[data-game-mode='CLASSIC']");
    this.removeNode("div[data-game-mode='SWIFTPLAY']");
    this.removeNode("lol-uikit-navigation-item[data-category='kVersusAI']");
    this.removeNode("lol-uikit-navigation-item[data-category='kTraining']");
  };
  removeTFT = () => {
    this.removeNode("div[data-game-mode='TFT']");
  };
  removeTFTNavbar = () => {
    this.removeNode(".menu_item_navbar_tft");
    observer.subscribeToElementCreation(".menu_item_navbar_tft", (element) => {
      element.remove();
    });
  };
  removeAram = () => {
    this.removeNode("div[data-game-mode='ARAM']");
  };
  removeArena = () => {
    this.removeNode("div[data-game-mode='CHERRY']");
  };
  removeCustomGameSection = () => {
    this.removeNode("lol-uikit-navigation-item[data-category='CreateCustom']");
    this.removeNode("lol-uikit-navigation-item[data-category='JoinCustom']");
  };
  removeGamemodes = () => {
    if (LustData.get("hide-summoner-rift-5v5"))
      this.removeSR5v5();
    if (LustData.get("hide-tft"))
      this.removeTFT();
    if (LustData.get("hide-aram"))
      this.removeAram();
    if (LustData.get("hide-arena"))
      this.removeArena();
    if (LustData.get("hide-custom-game-section"))
      this.removeCustomGameSection();
  };
  main = () => {
    if (LustData.get("hide-tft"))
      this.removeTFTNavbar();
    observer.subscribeToElementCreation(".game-type-card", (element) => {
      this.removeGamemodes();
    });
    observer.subscribeToElementCreation(".parties-game-type-select-wrapper", (element) => {
      this.removeGamemodes();
      element.querySelector("div:nth-child(2) div[class=parties-game-type-upper-half]").click();
    });
  };
}

async function requestChallengeCrystal() {
  const rank = await rankList();
  return {
    "lol": {
      "challengePoints": `${LustData.get("Challenge-Points")}`,
      "challengeCrystalLevel": `${rank["Ranked Tier ID"][LustData.get("challengeCrystalLevel")]["Option"]}`
    }
  };
}
async function requestRank() {
  const rank = await rankList();
  return {
    "lol": {
      "rankedLeagueQueue": rank["Ranked Queue ID"][LustData.get("Ranked Queue ID")]["Option"],
      "rankedLeagueTier": rank["Ranked Tier ID"][LustData.get("Ranked Tier ID")]["Option"],
      "rankedLeagueDivision": rank["Ranked Division ID"][LustData.get("Ranked Division ID")]["name"]
    }
  };
}
function requestMasteryScore() {
  return {
    "lol": {
      "masteryScore": `${LustData.get("Mastery-Score")}`
    }
  };
}
class CustomProfile {
  async request(method, endpoint, { headers = {}, body = {} } = {}) {
    const requestOptions = {
      method,
      headers: {
        ...headers,
        "accept": "application/json",
        "content-type": "application/json"
      }
    };
    if (method !== "GET" && method !== "HEAD") {
      requestOptions.body = JSON.stringify(body);
    }
    return await fetch(endpoint, requestOptions);
  }
  async getPlayerPreferences() {
    const endpoint = "/lol-challenges/v1/summary-player-data/local-player";
    const response = await this.request("GET", endpoint);
    const responseData = await response.json();
    const playerPreferences = { challengeIds: [] };
    playerPreferences.challengeIds = responseData.topChallenges.map((badgeChallenge) => badgeChallenge.id);
    if (responseData.title.itemId !== -1) {
      playerPreferences.title = `${responseData.title.itemId}`;
    }
    if (responseData.bannerId) {
      playerPreferences.bannerAccent = responseData.bannerId;
    }
    return playerPreferences;
  }
  async updatePlayerPreferences(playerPreferences) {
    const endpoint = "/lol-challenges/v1/update-player-preferences";
    return await this.request("POST", endpoint, { body: playerPreferences });
  }
  async setupInvisibleBanner() {
    const bannerContainer = document.querySelector("div > lol-regalia-profile-v2-element")?.shadowRoot?.querySelector("div > lol-regalia-banner-v2-element")?.shadowRoot?.querySelector("div");
    if (!bannerContainer || bannerContainer.hasAttribute("invisible-banner-setup")) {
      return;
    }
    bannerContainer.setAttribute("invisible-banner-setup", "true");
    bannerContainer.addEventListener("mouseenter", () => {
      bannerContainer.style.opacity = "0.5";
    });
    bannerContainer.addEventListener("mouseleave", () => {
      bannerContainer.style.opacity = "1";
    });
    bannerContainer.addEventListener("click", async () => {
      const playerPreferences = await this.getPlayerPreferences();
      playerPreferences.bannerAccent = playerPreferences.bannerAccent === "2" ? "1" : "2";
      await this.updatePlayerPreferences(playerPreferences);
    });
  }
  async setupBadgesFunctions() {
    const badgesContainer = document.querySelector("div > div.challenge-banner-token-container");
    if (!badgesContainer || badgesContainer.hasAttribute("copy-badges-setup")) {
      return;
    }
    badgesContainer.setAttribute("copy-badges-setup", "true");
    badgesContainer.addEventListener("mouseenter", () => {
      badgesContainer.style.opacity = "0.5";
    });
    badgesContainer.addEventListener("mouseleave", () => {
      badgesContainer.style.opacity = "1";
    });
    badgesContainer.addEventListener("click", async () => {
      const playerPreferences = await this.getPlayerPreferences();
      if (!playerPreferences.challengeIds.length) {
        console.debug(`The player does not have a defined badge.`);
        return;
      }
      const firstBadge = playerPreferences.challengeIds[0];
      playerPreferences.challengeIds = Array(3).fill(firstBadge);
      await this.updatePlayerPreferences(playerPreferences);
    });
    badgesContainer.addEventListener("contextmenu", async () => {
      const playerPreferences = await this.getPlayerPreferences();
      if (!playerPreferences.challengeIds.length) {
        console.debug(`The player badges are already empty.`);
        return;
      }
      playerPreferences.challengeIds = [];
      await this.updatePlayerPreferences(playerPreferences);
    });
  }
  customMasteryScore = () => {
    observer.subscribeToElementCreation("#lol-uikit-tooltip-root", async (element) => {
      try {
        let checkID = element.querySelector(`lol-regalia-hovercard-v2-element`)?.getAttribute("summoner-id");
        if (checkID == LustData.get("Summoner-ID")) {
          let GetMStext = document.querySelector("#hover-card-header > div.hover-card-header-left > span.hover-card-mastery-score");
          let MStext = GetMStext.innerText;
          let checkMS = MStext.includes(`${LustData.get("Mastery-Score")}`);
          if (!checkMS && LustData.get("Custom-mastery-score")) {
            await this.request("PUT", "/lol-chat/v1/me", { body: requestMasteryScore() });
          }
        }
      } catch {
      }
    });
    observer.subscribeToElementCreation(".collection-totals", (element) => {
      let a = element.querySelector(".total-owned.total-count.ember-view");
      if (a) {
        a.innerText = `${LustData.get("Mastery-Score")}`;
        utils.freezeProperties(a, ["innerText"]);
      }
    });
    observer.subscribeToElementCreation(".style-profile-champion-mastery-score", (element) => {
      element.innerText = `${LustData.get("Mastery-Score")}`;
      utils.freezeProperties(element, ["innerText"]);
    });
    window.setTimeout(async () => {
      if (LustData.get("Custom-rank")) {
        await this.request("PUT", "/lol-chat/v1/me", { body: await requestRank() });
      }
    }, 1e4);
  };
  customChallengeCrystal = () => {
    observer.subscribeToElementCreation("#lol-uikit-tooltip-root", async (element) => {
      try {
        let checkID = element.querySelector(`lol-regalia-hovercard-v2-element`)?.getAttribute("summoner-id");
        if (checkID == LustData.get("Summoner-ID")) {
          let fix = window.setInterval(async () => {
            let getCPtext = element.querySelector(".hover-card-challenge-crystal");
            let CPtext = getCPtext?.innerText;
            let checkCP = CPtext?.includes(`${LustData.get("Challenge-Points")}`);
            if (!checkCP && LustData.get("Custom-challenge-crystal")) {
              await this.request("PUT", "/lol-chat/v1/me", { body: await requestChallengeCrystal() });
            }
          }, 100);
          window.setTimeout(() => {
            window.clearInterval(fix);
          }, 3e3);
        }
      } catch {
      }
    });
    observer.subscribeToElementCreation(".crystal-wrapper", async (element) => {
      const rank = await rankList();
      let a = element.querySelector(".contents > div:nth-child(1)");
      let b = element.querySelector(".total-points");
      let level = element.querySelector(".level");
      a?.setAttribute("class", `crystal-image ${rank["Ranked Tier ID"][LustData.get("Ranked Tier ID")]["Option"]}`);
      if (b)
        b.innerText = `${LustData.get("Challenge-Points")}`;
      if (level)
        level.innerText = rank["Ranked Tier ID"][LustData.get("Ranked Tier ID")]["Option"].toLowerCase();
    });
    window.setTimeout(async () => {
      if (LustData.get("Custom-challenge-crystal")) {
        await this.request("PUT", "/lol-chat/v1/me", { body: await requestChallengeCrystal() });
      }
    }, 1e4);
  };
  customRank = async () => {
    await this.request("PUT", "/lol-chat/v1/me", { body: await requestRank() });
  };
  CustomProfileRankName = () => {
    observer.subscribeToElementCreation(
      ".style-profile-ranked-component.ember-view .style-profile-emblem-header-title",
      (element) => element.textContent = LustData.get("Rank-line1")
    );
    observer.subscribeToElementCreation(
      ".style-profile-emblem-subheader-ranked > div",
      (element) => element.textContent = LustData.get("Rank-line2")
    );
  };
  customBagde = () => {
    utils.routineAddCallback(() => this.setupBadgesFunctions(), [".rcp-fe-lol-profiles-main"]);
  };
  invisibleBanner = () => {
    utils.routineAddCallback(() => this.setupInvisibleBanner(), [".rcp-fe-lol-profiles-main"]);
  };
}

const filters$1 = (await import(`//plugins/${getThemeName()}/config/filters.js`)).default;
class CustomRunesBackground {
  removeOtherImage = () => {
    let remove = (element) => {
      element.remove();
    };
    observer.subscribeToElementCreation(".aux", remove);
    observer.subscribeToElementCreation("#splash", remove);
    observer.subscribeToElementCreation("#construct", remove);
    observer.subscribeToElementCreation("#keystone", remove);
  };
  changeRunesBackground = () => {
    observer.subscribeToElementCreation(".perks-construct-minspec", (element) => {
      window.setInterval(() => {
        element.style.cssText = `
                    top: 0px; 
                    left: 0px; 
                    filter: ${filters$1["Runes"]}; 
                    background-image: var(--pri${element.getAttribute("primary")})
                `;
      }, 100);
    });
  };
}

let filters = (await import(`//plugins/${getThemeName()}/config/filters.js`)).default;
class CustomGameSearchCard {
  DisplayNone = (element) => {
    element.style.display = "none";
  };
  restyleGamesearchCard = () => {
    observer.subscribeToElementCreation(
      ".parties-game-info-panel-bg-container",
      (element) => element.hidden = true
    );
    observer.subscribeToElementCreation(
      ".parties-game-search-status",
      (element) => element.style.cssText = `
				border: 1px solid #8c8263; 
				border-radius: 10px; 
				margin-top: 1px
			`
    );
    observer.subscribeToElementCreation(
      ".parties-game-search-header",
      (element) => element.style.cssText = `height: 28px;`
    );
    observer.subscribeToElementCreation(".parties-game-search-divider", this.DisplayNone);
    observer.subscribeToElementCreation(
      ".parties-game-search-map",
      (element) => element.style.cssText = `
				filter: ${filters["PartiesStatusCard"]};
			`
    );
    observer.subscribeToElementCreation(".parties-status-card-bg-container", this.DisplayNone);
    observer.subscribeToElementCreation(
      ".parties-status-card",
      (element) => element.style.background = "transparent"
    );
    observer.subscribeToElementCreation(
      ".parties-status-card-header",
      (element) => element.style.cssText = `
				visibility: hidden;
				height: 14px;
			`
    );
    observer.subscribeToElementCreation(
      ".parties-status-card-body",
      (element) => element.style.cssText = `
				margin-top: -23px; 
				padding: 10px 5px 10px 10px; 
				border: 1px solid #8c8263; 
				border-radius: 10px
			`
    );
    observer.subscribeToElementCreation(
      ".parties-status-card-map",
      (element) => element.style.cssText = `
				margin: -3px 10px 0 0;
				filter: ${filters["PartiesStatusCard"]};
			`
    );
    observer.subscribeToElementCreation(".parties-game-invite-heading-text", (element) => {
      element.hidden = true;
    });
  };
}

class TransparentSettingsDialogs {
  applyStyle = () => {
    const style = "var(--Settings-and-Dialog-frame-color)";
    observer.subscribeToElementCreation("lol-uikit-full-page-backdrop", (element) => {
      try {
        let a = element.querySelector("lol-uikit-dialog-frame").shadowRoot.querySelector("div");
        a.style.background = style;
        utils.freezeProperties(a.style, ["background"]);
      } catch {
      }
      try {
        let b = element.querySelector("lol-uikit-dialog-frame > div");
        b.style.background = style;
        utils.freezeProperties(b.style, ["background"]);
      } catch {
      }
      try {
        let a = document.getElementsByClassName("dialog-frame");
        for (let i = 0; i < a.length; i++) {
          let b = a[i].shadowRoot.querySelector("div");
          b.style.background = style;
        }
      } catch {
      }
      try {
        let c = element.querySelector("lol-regalia-identity-customizer-element").shadowRoot.querySelector("lol-regalia-banner-v2-element");
        c.remove();
      } catch {
      }
      try {
        let obj = document.querySelector(".lol-settings-container");
        let a = obj.shadowRoot.querySelector("div");
        obj.style.background = style;
        a.style.background = style;
        utils.freezeProperties(obj.style, ["background"]);
        utils.freezeProperties(a.style, ["background"]);
      } catch {
      }
    });
  };
}

const icdata$2 = (await import(`//plugins/${getThemeName()}/config/icons.js`)).default;
const datapath$4 = `//plugins/${getThemeName()}/`;
const iconFolder$1 = `${datapath$4}assets/icon/`;
const syncIconsType = ["avatar", "border", "banner", "emblem", "hoverCardBackdrop"];
const syncIconsDir = "./data/icons";
const hashesFile = "./data/icons/hashes.json";
const hashMetaFile = "./data/icons/hash-meta.json";
const cacheTTLms = 30 * 24 * 60 * 60 * 1e3;
const maxCacheKeys = 2500;
const onDemandCooldown = 2 * 60 * 1e3;
let storageMode = "memory";
let hashCache = {};
let hashTouchedAt = {};
let friendIconList = [];
let syncTargets = [];
const visibleUserNameTargets = /* @__PURE__ */ new Map();
const inFlightUserSync = /* @__PURE__ */ new Map();
const failedUserSyncUntil = {};
function normalizeDisplayName(name) {
  return typeof name === "string" ? name.normalize("NFKC").replace(/\s+/g, " ").trim().toLocaleLowerCase() : "";
}
function resolveSyncedUserTargetByDisplayName(name) {
  return visibleUserNameTargets.get(normalizeDisplayName(name)) || null;
}
class SyncUserIcons {
  getIconFolder() {
    return iconFolder$1;
  }
  getIconData() {
    return icdata$2;
  }
  getOwnIconMap() {
    const currentBanner = LustData.get("CurrentBanner");
    return [
      { url: `${iconFolder$1}${icdata$2["Avatar"]}`, type: "avatar" },
      { url: `${iconFolder$1}${icdata$2["Border"]}`, type: "border" },
      { url: `${iconFolder$1}Regalia-Banners/${currentBanner}`, type: "banner" },
      { url: `${iconFolder$1}${icdata$2["Hover-card"]}`, type: "hoverCardBackdrop" },
      { url: `${iconFolder$1}${icdata$2["Honor"]}`, type: "emblem" }
    ];
  }
  async computeFileHash(url) {
    try {
      const res = await fetch(url);
      if (!res.ok)
        return null;
      const buf = await res.arrayBuffer();
      const hash = await crypto.subtle.digest("SHA-256", buf);
      return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("");
    } catch (err) {
      error("Failed to compute file hash:", err);
      return null;
    }
  }
  async runLimited(tasks, limit = 16) {
    let index = 0;
    const workers = Array.from({ length: Math.min(limit, tasks.length) }, async () => {
      while (index < tasks.length) {
        const task = tasks[index++];
        await task();
      }
    });
    await Promise.all(workers);
  }
  async safeFetchJson(url) {
    try {
      const response = await fetch(url);
      if (!response.ok)
        return null;
      return await response.json();
    } catch {
      return null;
    }
  }
  addSyncTarget(targets, summonerId, puuid) {
    const numericSummonerId = Number(summonerId);
    if (!Number.isFinite(numericSummonerId) || numericSummonerId <= 0)
      return;
    const ownSummonerId = Number(LustData.get("Summoner-ID"));
    if (ownSummonerId && numericSummonerId === ownSummonerId)
      return;
    const key = String(numericSummonerId);
    const existing = targets.get(key);
    const normalizedPuuid = typeof puuid === "string" ? puuid : "";
    if (!existing) {
      targets.set(key, { summonerId: numericSummonerId, puuid: normalizedPuuid });
    } else if (!existing.puuid && normalizedPuuid) {
      existing.puuid = normalizedPuuid;
    }
  }
  getElementSyncTarget(element) {
    if (!element)
      return null;
    const summonerId = element.getAttribute("summoner-id");
    if (!summonerId)
      return null;
    const puuid = element.getAttribute("puuid") || element.getAttribute("voice-puuid") || "";
    const numericSummonerId = Number(summonerId);
    if (!Number.isFinite(numericSummonerId) || numericSummonerId <= 0)
      return null;
    return { summonerId: numericSummonerId, puuid };
  }
  addVisibleUserNameTarget(friend) {
    const summonerId = Number(friend?.summonerId);
    if (!Number.isFinite(summonerId) || summonerId <= 0)
      return;
    const target = {
      summonerId,
      puuid: typeof friend?.puuid === "string" ? friend.puuid : ""
    };
    const candidateNames = [
      friend?.gameName,
      friend?.name,
      friend?.summonerName,
      friend?.displayName,
      friend?.nick,
      friend?.lol?.gameName
    ];
    for (const candidate of candidateNames) {
      const normalized = normalizeDisplayName(candidate);
      if (normalized)
        visibleUserNameTargets.set(normalized, target);
    }
  }
  markCacheKey(key) {
    hashTouchedAt[key] = Date.now();
  }
  mergeIconEntries(entries) {
    for (const entry of entries) {
      const index = friendIconList.findIndex((current) => String(current.summonerID) === String(entry.summonerID));
      if (index >= 0)
        friendIconList[index] = entry;
      else
        friendIconList.push(entry);
    }
  }
  hasSyncedEntry(summonerId) {
    return friendIconList.some((entry) => String(entry.summonerID) === String(summonerId));
  }
  isOnDemandSyncBlocked(summonerId) {
    const blockedUntil = failedUserSyncUntil[String(summonerId)] || 0;
    return blockedUntil > Date.now();
  }
  markOnDemandSyncFailed(targets) {
    const retryAfter = Date.now() + onDemandCooldown;
    for (const target of targets) {
      failedUserSyncUntil[String(target.summonerId)] = retryAfter;
    }
  }
  clearOnDemandSyncFailure(targets) {
    for (const target of targets) {
      delete failedUserSyncUntil[String(target.summonerId)];
    }
  }
  async saveHashes() {
    if (storageMode !== "fs")
      return;
    try {
      await fileSystem.write(hashesFile, JSON.stringify(hashCache, null, 2), false);
    } catch (err) {
      error("Failed to save icon hashes:", err);
    }
  }
  async saveHashMeta() {
    if (storageMode !== "fs")
      return;
    try {
      await fileSystem.write(hashMetaFile, JSON.stringify(hashTouchedAt, null, 2), false);
    } catch (err) {
      error("Failed to save icon hash metadata:", err);
    }
  }
  async cleanupIconCache() {
    if (storageMode !== "fs")
      return false;
    const now = Date.now();
    const keys = Object.keys(hashCache);
    const staleKeys = keys.filter((key) => {
      const touchedAt = hashTouchedAt[key] || now;
      if (!hashTouchedAt[key])
        hashTouchedAt[key] = now;
      return now - touchedAt > cacheTTLms;
    });
    const remainingKeys = keys.filter((key) => !staleKeys.includes(key)).sort((a, b) => (hashTouchedAt[a] || now) - (hashTouchedAt[b] || now));
    const overflowKeys = remainingKeys.length > maxCacheKeys ? remainingKeys.slice(0, remainingKeys.length - maxCacheKeys) : [];
    const deleteKeys = [.../* @__PURE__ */ new Set([...staleKeys, ...overflowKeys])];
    for (const key of deleteKeys) {
      const [summonerId, type] = key.split(":");
      delete hashCache[key];
      delete hashTouchedAt[key];
      if (summonerId && type)
        await this.deleteIconFromFs(Number(summonerId), type);
    }
    return deleteKeys.length > 0;
  }
  async saveIconToFs(summonerId, type, dataUri) {
    if (storageMode !== "fs")
      return;
    try {
      const dir = `${syncIconsDir}/${summonerId}`;
      await fileSystem.mkdir(dir);
      await fileSystem.write(`${dir}/${type}`, dataUri, false);
    } catch (err) {
      error(`Failed to save icon ${type} for ${summonerId}:`, err);
    }
  }
  async loadIconFromFs(summonerId, type) {
    if (storageMode !== "fs")
      return null;
    try {
      const content = await fileSystem.read(`${syncIconsDir}/${summonerId}/${type}`);
      return content || null;
    } catch {
      return null;
    }
  }
  async deleteIconFromFs(summonerId, type) {
    if (storageMode !== "fs")
      return;
    try {
      await fileSystem.rm(`${syncIconsDir}/${summonerId}/${type}`, { recursive: false });
    } catch {
    }
  }
  /** Initialize icon storage after FileSystem.init(context) has resolved window.isContextFSExist. */
  async init() {
    if (window.isContextFSExist) {
      storageMode = "fs";
      await fileSystem.mkdir(syncIconsDir);
      const raw = await fileSystem.read(hashesFile);
      if (raw && raw.trim().length > 0) {
        try {
          hashCache = JSON.parse(raw);
        } catch {
          hashCache = {};
        }
      }
      const rawMeta = await fileSystem.read(hashMetaFile);
      if (rawMeta && rawMeta.trim().length > 0) {
        try {
          hashTouchedAt = JSON.parse(rawMeta);
        } catch {
          hashTouchedAt = {};
        }
      }
      log("SyncUserIcons initialized in fs mode");
    } else {
      storageMode = "memory";
      log("SyncUserIcons initialized in memory mode (filesystem unavailable)");
    }
  }
  async uploadIcon(icon, iconType) {
    const response = await fetch(icon);
    if (!response.ok)
      error(`Failed to fetch icon: ${icon}`);
    const blob = await response.blob();
    const mimeToExt = {
      "image/png": ".png",
      "image/jpeg": ".jpg",
      "image/webp": ".webp",
      "image/gif": ".gif"
    };
    log("Uploading " + icon);
    const ext = mimeToExt[blob.type] || ".png";
    const file = new File([blob], iconType + ext, { type: blob.type });
    try {
      await window.lustthemeApi.uploadImage(
        LustData.get("LustTheme-Token"),
        LustData.get("Summoner-ID"),
        iconType,
        file
      );
    } catch (err) {
      error(`Failed to upload icon of type ${iconType}: `, err);
    }
  }
  async syncOwnIcons(summonerID) {
    const iconMap = this.getOwnIconMap();
    if (typeof window.lustthemeApi.getImageHashes !== "function") {
      warn("getImageHashes not available, uploading own icons without hash check");
      await Promise.all(iconMap.map(({ url, type }) => this.uploadIcon(url, type)));
      return;
    }
    const [localHashes, serverHashes] = await Promise.all([
      Promise.all(iconMap.map(async ({ type, url }) => ({
        type,
        hash: await this.computeFileHash(url)
      }))),
      window.lustthemeApi.getImageHashes(summonerID, iconMap.map((icon) => icon.type))
    ]);
    if (!serverHashes) {
      warn("getImageHashes failed, uploading own icons without hash check");
      await Promise.all(iconMap.map(({ url, type }) => this.uploadIcon(url, type)));
      return;
    }
    await Promise.all(iconMap.map(async ({ url, type }) => {
      const localHash = localHashes.find((item) => item.type === type)?.hash || null;
      const serverHash = serverHashes[type] || null;
      if (!localHash || !serverHash || localHash !== serverHash) {
        log(`Icon "${type}" changed, uploading...`);
        await this.uploadIcon(url, type);
      } else {
        log(`Icon "${type}" unchanged, skipping upload`);
      }
    }));
  }
  async collectSyncTargets() {
    const targets = /* @__PURE__ */ new Map();
    const friends = await this.safeFetchJson("/lol-chat/v1/friends");
    if (Array.isArray(friends)) {
      for (const friend of friends) {
        this.addSyncTarget(targets, friend?.summonerId, friend?.puuid);
        this.addVisibleUserNameTarget(friend);
      }
    }
    const lobby = await this.safeFetchJson("/lol-lobby/v2/lobby");
    const lobbyMembers = lobby?.members || lobby?.partyMembers || [];
    if (Array.isArray(lobbyMembers)) {
      for (const member of lobbyMembers) {
        this.addSyncTarget(targets, member?.summonerId, member?.puuid);
      }
    }
    const champSelect = await this.safeFetchJson("/lol-champ-select/v1/session");
    const champSelectPlayers = [
      ...Array.isArray(champSelect?.myTeam) ? champSelect.myTeam : [],
      ...Array.isArray(champSelect?.theirTeam) ? champSelect.theirTeam : [],
      ...Array.isArray(champSelect?.benchChampions) ? champSelect.benchChampions : []
    ];
    for (const player of champSelectPlayers) {
      this.addSyncTarget(targets, player?.summonerId, player?.puuid);
    }
    document.querySelectorAll("[summoner-id], [puuid], [voice-puuid]").forEach((element) => {
      const target = this.getElementSyncTarget(element);
      if (target)
        this.addSyncTarget(targets, target.summonerId, target.puuid);
    });
    const conversationElements = Array.from(document.querySelectorAll(".conversation.chat"));
    await this.runLimited(conversationElements.map((element) => async () => {
      const conversationId = element.getAttribute("data-id");
      if (!conversationId)
        return;
      const chatInfo = await this.safeFetchJson(`/lol-chat/v1/conversations/${conversationId}`);
      if (!chatInfo?.gameName || !chatInfo?.gameTag)
        return;
      const encodedName = encodeURIComponent(`${chatInfo.gameName}#${chatInfo.gameTag}`);
      const summoner = await this.safeFetchJson(`/lol-summoner/v1/summoners/?name=${encodedName}`);
      this.addSyncTarget(targets, summoner?.summonerId, summoner?.puuid || chatInfo?.puuid);
    }), 4);
    syncTargets = Array.from(targets.values());
    return syncTargets;
  }
  /** memory mode: batch endpoint, in-memory data URIs (old Pengu fallback) */
  async syncUsersIconsMemory(targets, replaceList = true) {
    let entries = [];
    try {
      if (typeof window.lustthemeApi.getUsersImage === "function") {
        entries = await window.lustthemeApi.getUsersImage(targets);
      } else {
        entries = await window.lustthemeApi.getFriendsImage(targets);
      }
    } catch (err) {
      warn(`getUsersImage failed: ${err.message}`);
    }
    if (replaceList)
      friendIconList = entries;
    else
      this.mergeIconEntries(entries);
  }
  /** fs mode: one batch diff request, then read unchanged icons from local cache */
  async syncUsersIconsFs(targets, replaceList = true) {
    const stats = {
      serverMs: 0,
      cacheMs: 0,
      saveMs: 0,
      patches: 0,
      cacheReads: 0,
      updatedIcons: 0,
      deletedIcons: 0
    };
    if (!window.lustthemeApi) {
      warn("lustthemeApi not available, skipping user icon sync");
      return stats;
    }
    if (typeof window.lustthemeApi.syncUsersIcons !== "function" && typeof window.lustthemeApi.syncFriendsIcons !== "function") {
      warn("syncUsersIcons not available, falling back to getUsersImage");
      const serverStart2 = performance.now();
      await this.syncUsersIconsMemory(targets, replaceList);
      stats.serverMs = Math.round(performance.now() - serverStart2);
      return stats;
    }
    const serverStart = performance.now();
    let serverPatches = null;
    try {
      serverPatches = typeof window.lustthemeApi.syncUsersIcons === "function" ? await window.lustthemeApi.syncUsersIcons(targets, hashCache) : await window.lustthemeApi.syncFriendsIcons(targets, hashCache);
    } catch (err) {
      warn(`syncUsersIcons failed: ${err.message}`);
    }
    stats.serverMs = Math.round(performance.now() - serverStart);
    if (!serverPatches) {
      warn("syncUsersIcons failed, falling back to getUsersImage");
      const fallbackStart = performance.now();
      try {
        await this.syncUsersIconsMemory(targets, replaceList);
      } catch (err) {
        warn(`getUsersImage fallback failed: ${err.message}`);
      }
      stats.serverMs += Math.round(performance.now() - fallbackStart);
      return stats;
    }
    const patchBySummonerId = /* @__PURE__ */ new Map();
    for (const patch of serverPatches) {
      patchBySummonerId.set(String(patch.summonerID), patch);
    }
    stats.patches = patchBySummonerId.size;
    const syncedEntries = [];
    let hashesChanged = await this.cleanupIconCache();
    let hashMetaChanged = hashesChanged;
    const cacheReadTasks = [];
    const writeTasks = [];
    for (const target of targets) {
      const icons = {};
      const patch = patchBySummonerId.get(String(target.summonerId));
      const changedIcons = patch?.icons || {};
      for (const type of syncIconsType) {
        const key = `${target.summonerId}:${type}`;
        if (Object.prototype.hasOwnProperty.call(changedIcons, type)) {
          const update = changedIcons[type];
          if (update?.data && update.hash) {
            hashCache[key] = update.hash;
            this.markCacheKey(key);
            icons[type] = update.data;
            stats.updatedIcons++;
            writeTasks.push(() => this.saveIconToFs(target.summonerId, type, update.data));
          } else {
            delete hashCache[key];
            delete hashTouchedAt[key];
            icons[type] = null;
            stats.deletedIcons++;
            writeTasks.push(() => this.deleteIconFromFs(target.summonerId, type));
          }
          hashesChanged = true;
          hashMetaChanged = true;
          continue;
        }
        if (hashCache[key]) {
          this.markCacheKey(key);
          hashMetaChanged = true;
          stats.cacheReads++;
          cacheReadTasks.push(async () => {
            const cached = await this.loadIconFromFs(target.summonerId, type);
            if (cached) {
              icons[type] = cached;
            } else {
              delete hashCache[key];
              delete hashTouchedAt[key];
              icons[type] = null;
              hashesChanged = true;
              hashMetaChanged = true;
            }
          });
        } else {
          icons[type] = null;
        }
      }
      syncedEntries.push({
        summonerID: target.summonerId,
        puuid: target.puuid || "",
        icon: icons
      });
    }
    const cacheStart = performance.now();
    await this.runLimited(cacheReadTasks);
    stats.cacheMs = Math.round(performance.now() - cacheStart);
    const saveStart = performance.now();
    await this.runLimited(writeTasks, 8);
    if (hashesChanged)
      await this.saveHashes();
    if (hashMetaChanged)
      await this.saveHashMeta();
    stats.saveMs = Math.round(performance.now() - saveStart);
    if (replaceList)
      friendIconList = syncedEntries;
    else
      this.mergeIconEntries(syncedEntries);
    return stats;
  }
  async getFriendsIcons() {
    const totalStart = performance.now();
    const targetListStart = performance.now();
    const targets = await this.collectSyncTargets();
    const targetListMs = Math.round(performance.now() - targetListStart);
    if (targets.length === 0) {
      log("No visible users found, skipping icon sync");
      return;
    }
    let stats = null;
    if (storageMode === "fs") {
      stats = await this.syncUsersIconsFs(targets);
    } else {
      await this.syncUsersIconsMemory(targets);
    }
    const totalMs = Math.round(performance.now() - totalStart);
    if (stats) {
      log(
        `User icon sync finished in ${totalMs}ms (${targets.length} visible users, ${storageMode} mode)
(targets=${targetListMs}ms, server=${stats.serverMs}ms, cache=${stats.cacheMs}ms, save=${stats.saveMs}ms, patches=${stats.patches}, reads=${stats.cacheReads}, updated=${stats.updatedIcons}, deleted=${stats.deletedIcons})`
      );
    } else {
      log(`User icon sync finished in ${totalMs}ms (${targets.length} visible users, ${storageMode} mode; targets=${targetListMs}ms)`);
    }
    if (LustData.get("Dev-mode"))
      log("Synced user icons: ", friendIconList);
  }
  async requestUserIconSync(targets, reason = "visible-user") {
    if (!LustData.get("sync-user-icons"))
      return;
    if (!window.lustthemeApi || !Array.isArray(targets) || targets.length === 0)
      return;
    const deduped = /* @__PURE__ */ new Map();
    for (const target of targets) {
      this.addSyncTarget(deduped, target?.summonerId, target?.puuid);
    }
    const requestTargets = Array.from(deduped.values()).filter((target) => !this.hasSyncedEntry(target.summonerId)).filter((target) => !this.isOnDemandSyncBlocked(target.summonerId));
    const existingSyncs = requestTargets.map((target) => inFlightUserSync.get(String(target.summonerId))).filter((promise) => Boolean(promise));
    const newRequestTargets = requestTargets.filter((target) => !inFlightUserSync.has(String(target.summonerId)));
    if (newRequestTargets.length === 0) {
      await Promise.allSettled(existingSyncs);
      return;
    }
    const syncPromise = (async () => {
      if (storageMode === "fs")
        await this.syncUsersIconsFs(newRequestTargets, false);
      else
        await this.syncUsersIconsMemory(newRequestTargets, false);
      const missingEntries = newRequestTargets.filter((target) => !this.hasSyncedEntry(target.summonerId));
      if (missingEntries.length > 0) {
        this.markOnDemandSyncFailed(missingEntries);
      } else {
        this.clearOnDemandSyncFailure(newRequestTargets);
      }
    })();
    for (const target of newRequestTargets) {
      inFlightUserSync.set(String(target.summonerId), syncPromise);
    }
    try {
      await Promise.allSettled([...existingSyncs, syncPromise]);
    } finally {
      for (const target of newRequestTargets) {
        inFlightUserSync.delete(String(target.summonerId));
      }
    }
    if (LustData.get("Dev-mode")) {
      log(`On-demand icon sync complete (${newRequestTargets.length} users, reason=${reason})`);
    }
  }
  async ensureUserIcons(target, reason = "visible-user") {
    if (!target?.summonerId)
      return;
    if (this.hasSyncedEntry(target.summonerId))
      return;
    if (this.isOnDemandSyncBlocked(target.summonerId))
      return;
    await this.requestUserIconSync([target], reason);
  }
  /**
   * Download friend icons and upload own icons with hash comparison.
   */
  async syncIconsWithHashCheck() {
    if (!LustData.get("sync-user-icons"))
      return;
    const summonerID = LustData.get("Summoner-ID");
    const token = LustData.get("LustTheme-Token");
    if (!summonerID || !token) {
      error("Missing summonerID or token, skipping icon sync");
      return;
    }
    await window.Toast.promise(this.getFriendsIcons(), {
      loading: "Syncing user icons...",
      success: "Sync complete!",
      error: "Error while syncing user icons, check console for more info!"
    });
    await this.syncOwnIcons(summonerID);
    const conversationChat = document.querySelectorAll(".conversation.chat");
    for (let i = 0; i < conversationChat.length; i++) {
      customAvatar.changeConversationChatAvatar(conversationChat[i]);
    }
    const chatHeaders = document.querySelectorAll("header.chat-header");
    for (let i = 0; i < chatHeaders.length; i++) {
      customAvatar.applyChatHeaderAvatar(chatHeaders[i]);
    }
    const socialRosterMembers = document.querySelectorAll(".lol-social-roster-member");
    for (let i = 0; i < socialRosterMembers.length; i++) {
      customAvatar.applySocialRosterAvatar(socialRosterMembers[i]);
    }
  }
  async main() {
    await this.syncIconsWithHashCheck();
  }
}
const syncUserIcons = new SyncUserIcons();
window.syncUserIcons = syncUserIcons;

const icdata$1 = (await import(`//plugins/${getThemeName()}/config/icons.js`)).default;
const datapath$3 = `//plugins/${getThemeName()}/`;
const iconFolder = `${datapath$3}assets/icon/`;
const activeRegaliaWatchers = /* @__PURE__ */ new WeakMap();
const activeSocialRosterWatchers = /* @__PURE__ */ new WeakMap();
const activeChatHeaderWatchers = /* @__PURE__ */ new WeakMap();
const activeIdentityTooltipWatchers = /* @__PURE__ */ new WeakMap();
const chatNameTargetCache = /* @__PURE__ */ new Map();
let lastIdentityTooltipTarget = null;
let lastIdentityTooltipTargetAt = 0;
let identityTooltipHoverListenerStarted = false;
function findSyncedUserIcon(summonerId, type) {
  const entry = friendIconList.find((x) => String(x.summonerID) === String(summonerId));
  return entry?.icon?.[type] || null;
}
async function ensureSyncedElementIcons(element, reason) {
  const summonerId = Number(element?.getAttribute("summoner-id"));
  if (!Number.isFinite(summonerId) || summonerId <= 0)
    return;
  if (String(summonerId) === String(LustData.get("Summoner-ID")))
    return;
  if (friendIconList.some((x) => String(x.summonerID) === String(summonerId)))
    return;
  await window.syncUserIcons?.ensureUserIcons({
    summonerId,
    puuid: element.getAttribute("puuid") || element.getAttribute("voice-puuid") || ""
  }, reason);
}
function findSyncedUserTargetFromElement(element) {
  if (!element)
    return null;
  const summonerId = Number(element.getAttribute("summoner-id"));
  if (Number.isFinite(summonerId) && summonerId > 0) {
    return {
      summonerId,
      puuid: element.getAttribute("puuid") || element.getAttribute("voice-puuid") || ""
    };
  }
  const puuid = element.getAttribute("puuid") || element.getAttribute("voice-puuid") || "";
  if (puuid) {
    const entry = friendIconList.find((item) => item.puuid === puuid);
    if (entry?.summonerID) {
      return {
        summonerId: Number(entry.summonerID),
        puuid
      };
    }
    if (puuid === LustData.get("PUUID")) {
      const ownSummonerId = Number(LustData.get("Summoner-ID"));
      if (Number.isFinite(ownSummonerId) && ownSummonerId > 0) {
        return {
          summonerId: ownSummonerId,
          puuid
        };
      }
    }
  }
  return null;
}
function getOwnAvatarUrl() {
  return `${iconFolder}${icdata$1["Avatar"]}`;
}
function getNestedShadowRoots(element) {
  const roots = [];
  const visitRoot = (root) => {
    const nodes = Array.from(root.querySelectorAll("*"));
    for (const node of nodes) {
      const shadowRoot = node.shadowRoot;
      if (shadowRoot && !roots.includes(shadowRoot)) {
        roots.push(shadowRoot);
        visitRoot(shadowRoot);
      }
    }
  };
  if (element.shadowRoot) {
    roots.push(element.shadowRoot);
    visitRoot(element.shadowRoot);
  }
  return roots;
}
function watchRegaliaElement(element, key, apply) {
  if (!element)
    return;
  let activeKeys = activeRegaliaWatchers.get(element);
  if (!activeKeys) {
    activeKeys = /* @__PURE__ */ new Set();
    activeRegaliaWatchers.set(element, activeKeys);
  }
  if (activeKeys.has(key))
    return;
  activeKeys.add(key);
  const startedAt = Date.now();
  const observers = [];
  const observedRoots = /* @__PURE__ */ new Set();
  let attempts = 0;
  let stopped = false;
  let debounceTimer = null;
  let quietTimer = null;
  const stop = () => {
    if (stopped)
      return;
    stopped = true;
    if (debounceTimer !== null)
      window.clearTimeout(debounceTimer);
    if (quietTimer !== null)
      window.clearTimeout(quietTimer);
    observers.forEach((observer) => observer.disconnect());
    activeKeys?.delete(key);
  };
  const scheduleStopAfterQuiet = () => {
    if (quietTimer !== null)
      window.clearTimeout(quietTimer);
    const elapsed = Date.now() - startedAt;
    const waitMs = Math.max(700, 2500 - elapsed);
    quietTimer = window.setTimeout(stop, waitMs);
  };
  const observeRoots = () => {
    for (const root of getNestedShadowRoots(element)) {
      if (observedRoots.has(root))
        continue;
      observedRoots.add(root);
      const observer = new MutationObserver(scheduleRun);
      observer.observe(root, { attributes: true, childList: true, subtree: true });
      observers.push(observer);
    }
  };
  const run = async () => {
    if (stopped || !element.isConnected) {
      stop();
      return;
    }
    attempts++;
    observeRoots();
    let applied = false;
    try {
      applied = await apply();
    } catch (err) {
      if (LustData.get("Dev-mode"))
        warn(`Regalia ${key} apply failed:`, err);
    }
    observeRoots();
    if (applied)
      scheduleStopAfterQuiet();
    if (Date.now() - startedAt >= 4e3 || attempts >= 20)
      stop();
  };
  function scheduleRun() {
    if (stopped)
      return;
    if (quietTimer !== null) {
      window.clearTimeout(quietTimer);
      quietTimer = null;
    }
    if (debounceTimer !== null)
      window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(run, 50);
  }
  const hostObserver = new MutationObserver(scheduleRun);
  hostObserver.observe(element, { attributes: true, childList: true, subtree: false });
  observers.push(hostObserver);
  void run();
}
class CustomTickerIcon {
  tickerCss(element, defaults) {
    Object.entries(defaults).forEach(([key, value]) => {
      element.shadowRoot.querySelector(key).style.cssText = value;
    });
  }
  main = () => {
    observer.subscribeToElementCreation("lol-uikit-flyout-frame", (element) => {
      this.tickerCss(
        element,
        {
          ".border": "display: none;",
          ".sub-border": "display: none;",
          ".caret": "display: none;",
          ".lol-uikit-flyout-frame": "background-color: black; border-radius: 10px;"
        }
      );
    });
  };
}
class CustomAvatar {
  startIdentityTooltipHoverTracking() {
    if (identityTooltipHoverListenerStarted)
      return;
    identityTooltipHoverListenerStarted = true;
    document.addEventListener("pointerover", (event) => {
      const path = event.composedPath();
      for (const pathItem of path) {
        if (!(pathItem instanceof Element))
          continue;
        const target = findSyncedUserTargetFromElement(pathItem);
        if (!target)
          continue;
        lastIdentityTooltipTarget = target;
        lastIdentityTooltipTargetAt = Date.now();
        return;
      }
    }, true);
  }
  applyAvatarBackground(iconElement, backgroundImage) {
    if (!iconElement)
      return false;
    iconElement.style.backgroundImage = backgroundImage;
    utils.freezeProperties(iconElement.style, ["backgroundImage"]);
    return true;
  }
  getRegaliaSummonerIcon(element) {
    if (element?.shadowRoot?.querySelector(".lol-regalia-summoner-icon")) {
      return element.shadowRoot.querySelector(".lol-regalia-summoner-icon");
    }
    return element?.shadowRoot?.querySelector("lol-regalia-crest-v2-element")?.shadowRoot?.querySelector(".lol-regalia-summoner-icon") || null;
  }
  changeAvatar = (iconElement) => {
    return this.applyAvatarBackground(iconElement, "var(--Avatar)");
  };
  changeFriendAvatar = async (element, iconElement) => {
    let summonerID = element.getAttribute("summoner-id");
    if (summonerID === null || summonerID === void 0 || summonerID === "") {
      element.setAttribute("summoner-id", friendIconList.find((x) => x.puuid == element.getAttribute("puuid"))?.summonerID || friendIconList.find((x) => x.puuid == element.getAttribute("voice-puuid"))?.summonerID || null);
    }
    await ensureSyncedElementIcons(element, "avatar");
    const avatar = findSyncedUserIcon(element.getAttribute("summoner-id"), "avatar");
    if (avatar) {
      return this.applyAvatarBackground(iconElement, `url(${avatar})`);
    }
    return false;
  };
  changeConversationChatAvatar = async (element) => {
    let chatDataID = element.getAttribute("data-id");
    let chatInfo = await (await fetch(`/lol-chat/v1/conversations/${chatDataID}`)).json();
    let summonerID = (await (await fetch(`/lol-summoner/v1/summoners/?name=${chatInfo.gameName}%23${chatInfo.gameTag}`)).json()).summonerId;
    await window.syncUserIcons?.ensureUserIcons({ summonerId: Number(summonerID), puuid: "" }, "conversation-chat");
    const avatar = findSyncedUserIcon(summonerID, "avatar");
    if (avatar) {
      let icon = element.querySelector(".icon-image");
      icon.src = `${avatar}`;
      utils.freezeProperties(icon, ["src"]);
    }
  };
  getChatHeaderNameTarget(headerElement) {
    const playerName = headerElement.querySelector("lol-uikit-player-name[game-name][tag-line]");
    const gameName = playerName?.getAttribute("game-name") || "";
    const tagLine = playerName?.getAttribute("tag-line") || "";
    if (!gameName || !tagLine)
      return null;
    return { gameName, tagLine };
  }
  async resolveChatHeaderTarget(headerElement) {
    const nameTarget = this.getChatHeaderNameTarget(headerElement);
    if (!nameTarget)
      return null;
    const cacheKey = `${nameTarget.gameName}#${nameTarget.tagLine}`.toLocaleLowerCase();
    if (chatNameTargetCache.has(cacheKey))
      return chatNameTargetCache.get(cacheKey) || null;
    try {
      const encodedName = encodeURIComponent(`${nameTarget.gameName}#${nameTarget.tagLine}`);
      const summoner = await fetch(`/lol-summoner/v1/summoners/?name=${encodedName}`).then((res) => res.ok ? res.json() : null);
      const summonerId = Number(summoner?.summonerId);
      if (!Number.isFinite(summonerId) || summonerId <= 0) {
        chatNameTargetCache.set(cacheKey, null);
        return null;
      }
      const target = {
        summonerId,
        puuid: typeof summoner?.puuid === "string" ? summoner.puuid : ""
      };
      chatNameTargetCache.set(cacheKey, target);
      return target;
    } catch {
      return null;
    }
  }
  applyChatHeaderAvatar = async (headerElement) => {
    const target = await this.resolveChatHeaderTarget(headerElement);
    if (!target)
      return false;
    await window.syncUserIcons?.ensureUserIcons(target, "chat-header");
    const avatar = findSyncedUserIcon(target.summonerId, "avatar");
    const icon = headerElement.querySelector("lol-social-avatar.avatar .icon-image");
    if (!avatar || !icon)
      return false;
    icon.src = avatar;
    return true;
  };
  watchChatHeaderAvatar = (headerElement) => {
    if (!headerElement || activeChatHeaderWatchers.has(headerElement))
      return;
    let debounceTimer = null;
    const apply = () => {
      if (debounceTimer !== null)
        window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(async () => {
        if (!headerElement.isConnected) {
          observer.disconnect();
          activeChatHeaderWatchers.delete(headerElement);
          return;
        }
        await this.applyChatHeaderAvatar(headerElement);
      }, 50);
    };
    const observer = new MutationObserver(apply);
    observer.observe(headerElement, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true
    });
    activeChatHeaderWatchers.set(headerElement, observer);
    void this.applyChatHeaderAvatar(headerElement);
  };
  getTooltipAvatarImage(tooltipRoot) {
    const avatarIcon = tooltipRoot.querySelector(".icon-identity-tooltip-component lol-social-avatar-icon");
    return avatarIcon?.shadowRoot?.querySelector("img");
  }
  getIdentityTooltipTarget() {
    if (!lastIdentityTooltipTarget || Date.now() - lastIdentityTooltipTargetAt > 5e3)
      return null;
    return lastIdentityTooltipTarget;
  }
  applyIdentityTooltipAvatar = async (tooltipRoot) => {
    const target = this.getIdentityTooltipTarget();
    if (!target)
      return false;
    const icon = this.getTooltipAvatarImage(tooltipRoot);
    if (!icon)
      return false;
    let avatar = null;
    if (String(target.summonerId) === String(LustData.get("Summoner-ID"))) {
      avatar = getOwnAvatarUrl();
    } else {
      await window.syncUserIcons?.ensureUserIcons(target, "identity-tooltip-avatar");
      avatar = findSyncedUserIcon(target.summonerId, "avatar");
    }
    if (!avatar)
      return false;
    icon.src = avatar;
    return true;
  };
  watchIdentityTooltipAvatar = (tooltipRoot) => {
    if (!tooltipRoot || activeIdentityTooltipWatchers.has(tooltipRoot))
      return;
    let debounceTimer = null;
    const apply = () => {
      if (debounceTimer !== null)
        window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(async () => {
        if (!tooltipRoot.isConnected) {
          observer.disconnect();
          activeIdentityTooltipWatchers.delete(tooltipRoot);
          return;
        }
        await this.applyIdentityTooltipAvatar(tooltipRoot);
      }, 40);
    };
    const observer = new MutationObserver(apply);
    observer.observe(tooltipRoot, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true
    });
    activeIdentityTooltipWatchers.set(tooltipRoot, observer);
    apply();
  };
  applySocialRosterAvatar = async (memberElement) => {
    const memberName = memberElement.querySelector(".member-name")?.textContent || "";
    const target = resolveSyncedUserTargetByDisplayName(memberName);
    if (!target)
      return false;
    await window.syncUserIcons?.ensureUserIcons(target, "social-roster-member");
    const avatar = findSyncedUserIcon(target.summonerId, "avatar");
    const icon = memberElement.querySelector(".lol-social-avatar .icon-image");
    if (!avatar || !icon)
      return false;
    icon.src = avatar;
    return true;
  };
  watchSocialRosterMember = (memberElement) => {
    if (!memberElement || activeSocialRosterWatchers.has(memberElement))
      return;
    let debounceTimer = null;
    const apply = () => {
      if (debounceTimer !== null)
        window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(async () => {
        if (!memberElement.isConnected) {
          observer.disconnect();
          activeSocialRosterWatchers.delete(memberElement);
          return;
        }
        await this.applySocialRosterAvatar(memberElement);
      }, 50);
    };
    const observer = new MutationObserver(apply);
    observer.observe(memberElement, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true
    });
    activeSocialRosterWatchers.set(memberElement, observer);
    void this.applySocialRosterAvatar(memberElement);
  };
  applyCustomAvatar = async (parentElement) => {
    const iconElement = this.getRegaliaSummonerIcon(parentElement);
    if (!parentElement || !iconElement)
      return false;
    if (parentElement.getAttribute("summoner-id") == LustData.get("Summoner-ID") || parentElement.getAttribute("puuid") == LustData.get("PUUID") || parentElement.getAttribute("voice-puuid") == LustData.get("PUUID")) {
      return this.changeAvatar(iconElement);
    } else {
      return await this.changeFriendAvatar(parentElement, iconElement);
    }
  };
  watchCustomAvatar = (element) => {
    watchRegaliaElement(element, "avatar", () => this.applyCustomAvatar(element));
  };
  async main() {
    this.startIdentityTooltipHoverTracking();
    observer.subscribeToElementCreation(".hover-card-info-container", (element) => {
      element.style.background = "#1a1c21";
    });
    observer.subscribeToElementCreation(`lol-regalia-hovercard-v2-element`, async (element) => {
      this.watchCustomAvatar(element);
    });
    observer.subscribeToElementCreation("lol-regalia-identity-customizer-element", async (element) => {
      this.watchCustomAvatar(element);
    });
    observer.subscribeToElementCreation("lol-regalia-parties-v2-element", async (element) => {
      this.watchCustomAvatar(element);
    });
    observer.subscribeToElementCreation(".player-slot__crest-wrapper > lol-regalia-crest-v2-element", async (element) => {
      this.watchCustomAvatar(element);
    });
    observer.subscribeToElementCreation("lol-regalia-profile-v2-element", async (element) => {
      this.watchCustomAvatar(element);
    });
    observer.subscribeToElementCreation(".conversation.chat", async (element) => {
      await this.changeConversationChatAvatar(element);
    });
    observer.subscribeToElementCreation("header.chat-header", (element) => {
      this.watchChatHeaderAvatar(element);
    });
    observer.subscribeToElementCreation("#lol-uikit-tooltip-root", (element) => {
      this.watchIdentityTooltipAvatar(element);
    });
    observer.subscribeToElementCreation(".lol-social-roster-member", (element) => {
      this.watchSocialRosterMember(element);
    });
  }
}
const customAvatar = new CustomAvatar();
class CustomBorder {
  getBorderTargets(element) {
    let regaliaCrest = element.shadowRoot.querySelector("lol-regalia-crest-v2-element");
    if (!regaliaCrest?.shadowRoot)
      return null;
    let levelRing = regaliaCrest.shadowRoot.querySelector("lol-uikit-themed-level-ring-v2");
    let leverBorder = levelRing?.shadowRoot?.querySelector("div");
    let rankBorder = regaliaCrest.shadowRoot.querySelector(".lol-regalia-ranked-border-container");
    let rankNumber = regaliaCrest.shadowRoot.querySelector(".lol-regalia-rank-division-wrapper");
    let rankBorderAnimate = regaliaCrest.shadowRoot.querySelector("uikit-video");
    let rankBorderWingAnimate = regaliaCrest.shadowRoot.querySelector("lol-uikit-lottie[class='regalia-crest-wing']");
    if (!leverBorder || !rankBorder || !rankNumber || !rankBorderAnimate || !rankBorderWingAnimate)
      return null;
    return { leverBorder, rankBorder, rankNumber, rankBorderAnimate, rankBorderWingAnimate };
  }
  applyBorderTargets(targets, backgroundImage) {
    if (!targets)
      return false;
    targets.leverBorder.style.cssText = `
			background-image: ${backgroundImage};
			display: block;
		`;
    utils.freezeProperties(targets.leverBorder.style, ["backgroundImage", "display"]);
    targets.rankBorder.style.display = "none";
    targets.rankNumber.style.display = "none";
    targets.rankBorderAnimate.style.display = "none";
    targets.rankBorderWingAnimate.style.display = "none";
    return true;
  }
  changeBorder = (element) => {
    return this.applyBorderTargets(this.getBorderTargets(element), "var(--Border)");
  };
  changeFriendBorder = async (element) => {
    await ensureSyncedElementIcons(element, "border");
    const border = findSyncedUserIcon(element.getAttribute("summoner-id"), "border");
    if (border) {
      return this.applyBorderTargets(this.getBorderTargets(element), `url(${border})`);
    }
    return false;
  };
  applyCustomBorder = async (element) => {
    if (element.getAttribute("summoner-id") == LustData.get("Summoner-ID")) {
      return this.changeBorder(element);
    } else {
      return await this.changeFriendBorder(element);
    }
  };
  watchCustomBorder = (element) => {
    watchRegaliaElement(element, "border", () => this.applyCustomBorder(element));
  };
  async main() {
    observer.subscribeToElementCreation(`lol-regalia-hovercard-v2-element`, async (element) => {
      this.watchCustomBorder(element);
    });
    observer.subscribeToElementCreation("lol-regalia-parties-v2-element", async (element) => {
      this.watchCustomBorder(element);
    });
    observer.subscribeToElementCreation("lol-regalia-profile-v2-element", async (element) => {
      this.watchCustomBorder(element);
    });
    observer.subscribeToElementCreation("lol-regalia-identity-customizer-element", async (element) => {
      this.watchCustomBorder(element);
    });
  }
}
class CustomBanner {
  getBannerImage(element) {
    return element?.shadowRoot?.querySelector("lol-regalia-banner-v2-element")?.shadowRoot?.querySelector(".regalia-banner-asset-static-image") || null;
  }
  changeBanner = (banner) => {
    if (!banner)
      return false;
    banner.src = `${iconFolder}Regalia-Banners/${LustData.get("CurrentBanner")}`;
    utils.freezeProperties(banner, ["src"]);
    return true;
  };
  changeFriendBanner = async (element, banner) => {
    if (!banner)
      return false;
    await ensureSyncedElementIcons(element, "banner");
    const syncedBanner = findSyncedUserIcon(element.getAttribute("summoner-id"), "banner");
    if (syncedBanner) {
      banner.src = `${syncedBanner}`;
      utils.freezeProperties(banner, ["src"]);
      return true;
    }
    return false;
  };
  applyCustomBanner = async (element) => {
    let banner = this.getBannerImage(element);
    if (element.getAttribute("summoner-id") == LustData.get("Summoner-ID")) {
      return this.changeBanner(banner);
    } else {
      return await this.changeFriendBanner(element, banner);
    }
  };
  watchCustomBanner = (element) => {
    watchRegaliaElement(element, "banner", () => this.applyCustomBanner(element));
  };
  async main() {
    observer.subscribeToElementCreation("lol-regalia-parties-v2-element", async (element) => {
      this.watchCustomBanner(element);
    });
    observer.subscribeToElementCreation("lol-regalia-identity-customizer-element", async (element) => {
      this.watchCustomBanner(element);
    });
    observer.subscribeToElementCreation("lol-regalia-profile-v2-element", async (element) => {
      this.watchCustomBanner(element);
    });
  }
}
class CustomHoverCardBackdrop {
  changeHoverCardBackdrop = () => {
    let hoverCardBackdrop = document.querySelector("#hover-card-backdrop");
    if (hoverCardBackdrop) {
      hoverCardBackdrop.style.backgroundImage = "var(--Hover-card-backdrop)";
      return true;
    }
    return false;
  };
  changeFriendHoverCardBackdrop = async (hovercard) => {
    if (!hovercard)
      return false;
    await ensureSyncedElementIcons(hovercard, "hover-card-backdrop");
    const backdrop = findSyncedUserIcon(hovercard.getAttribute("summoner-id"), "hoverCardBackdrop");
    if (backdrop) {
      let hoverCardBackdrop = document.querySelector("#hover-card-backdrop");
      if (hoverCardBackdrop) {
        hoverCardBackdrop.style.backgroundImage = `url(${backdrop})`;
        return true;
      }
    }
    return false;
  };
  changeFriendProfileBackground = async (element) => {
    await ensureSyncedElementIcons(element, "profile-background");
    const backdrop = findSyncedUserIcon(element.getAttribute("summoner-id"), "hoverCardBackdrop");
    if (backdrop) {
      let profileBackground = document.querySelectorAll(".style-profile-masked-image .lol-uikit-background-switcher-image");
      if (profileBackground.length === 0)
        return false;
      profileBackground.forEach((bg) => {
        bg.src = `${backdrop}`;
        bg.style.height = "100%";
        utils.freezeProperties(bg, ["src", "style.height"]);
      });
      return true;
    }
    return false;
  };
  applyCustomHoverCardBackdrop = async (element) => {
    let hovercard = element.querySelector("lol-regalia-hovercard-v2-element");
    if (!hovercard)
      return false;
    if (hovercard.getAttribute("summoner-id") == LustData.get("Summoner-ID")) {
      return this.changeHoverCardBackdrop();
    } else {
      return await this.changeFriendHoverCardBackdrop(hovercard);
    }
  };
  applyCustomBackgroundFriendProfile = async (element) => {
    if (element.getAttribute("summoner-id") != LustData.get("Summoner-ID")) {
      return await this.changeFriendProfileBackground(element);
    }
    return false;
  };
  watchCustomHoverCardBackdrop = (element) => {
    watchRegaliaElement(element, "hover-card-backdrop", () => this.applyCustomHoverCardBackdrop(element));
  };
  watchCustomBackgroundFriendProfile = (element) => {
    watchRegaliaElement(element, "profile-background", () => this.applyCustomBackgroundFriendProfile(element));
  };
  async main() {
    observer.subscribeToElementCreation("#lol-uikit-tooltip-root", async (element) => {
      this.watchCustomHoverCardBackdrop(element);
    });
    observer.subscribeToElementCreation("lol-regalia-profile-v2-element", async (element) => {
      this.watchCustomBackgroundFriendProfile(element);
    });
  }
}
class CustomGamemodeIcon {
  gameModeIcon_active(obj, name) {
    try {
      let a = document.querySelector(`${obj} lol-uikit-video-state[state='active'] lol-uikit-video`);
      a.setAttribute("src", `${iconFolder}gamemodes/${name}`);
      a.querySelector("video").setAttribute("src", `${iconFolder}gamemodes/${name}`);
    } catch {
    }
  }
  main = () => {
    observer.subscribeToElementCreation("lol-uikit-video-group", (element) => {
      this.gameModeIcon_active("div[data-game-mode='CLASSIC']", icdata$1["classic_video"]);
      this.gameModeIcon_active("div[data-game-mode='TFT']", icdata$1["tft_video"]);
      this.gameModeIcon_active("div[data-game-mode='ARAM']", icdata$1["aram_video"]);
      this.gameModeIcon_active("div[data-game-mode='CHERRY']", icdata$1["cherry_video"]);
      this.gameModeIcon_active("div[data-game-mode='BRAWL']", icdata$1["brawl_video"]);
      this.gameModeIcon_active('div[data-map-id="11"]', icdata$1["classic_video"]);
      this.gameModeIcon_active('div[data-map-id="12"]', icdata$1["aram_video"]);
      this.gameModeIcon_active("div[data-game-mode='PRACTICETOOL']", icdata$1["classic_video"]);
    });
  };
}
class CustomEmblemIcon {
  changeEmblemIcon = (element) => {
    element.setAttribute("src", `${iconFolder}${icdata$1["Honor"]}`);
    element.style.visibility = "visible";
    utils.freezeProperties(element, ["src"]);
  };
  main = () => {
    observer.subscribeToElementCreation(".style-profile-honor-icon-v3", (element) => {
      this.changeEmblemIcon(element);
    });
  };
}
class CustomLoadingIcon {
  storeInterval = null;
  storeLoadingIcon = () => {
    observer.subscribeToElementCreation("#rcp-fe-lol-store-iframe", (element) => {
      log("Store page.");
      if (this.storeInterval !== null) {
        window.clearInterval(this.storeInterval);
        this.storeInterval = null;
      }
      this.storeInterval = window.setInterval(() => {
        let storeIframe = element.querySelector("iframe");
        if (storeIframe) {
          let storeDoc = storeIframe.contentDocument || storeIframe.contentWindow.document;
          let loadingIcon = null;
          if (loadingIcon) {
            loadingIcon.style.cssText = `
							width: 190px;
							height: 190px;
							background-image: unset;
							background-size: unset;
							content: url("${iconFolder}${icdata$1["Loading"]}");
							-webkit-animation-iteration-count: unset;
							-webkit-animation-duration: unset;
							-webkit-animation-timing-function: unset;
							animation-iteration-count: unset;
							animation-duration: unset;
							animation-timing-function: unset;
						`;
          }
        }
      }, 300);
    });
    observer.subscribeToElementDeletion("#rcp-fe-lol-store-iframe", () => {
      log("Store page deleted.");
      if (this.storeInterval !== null) {
        window.clearInterval(this.storeInterval);
        this.storeInterval = null;
      }
    });
  };
  main() {
    this.storeLoadingIcon();
  }
}
class CustomIcon {
  main() {
    if (false) {
      customAvatar.main();
    }
    if (false) {
      const customBorder = new CustomBorder();
      customBorder.main();
    }
    if (false) {
      const customBanner = new CustomBanner();
      customBanner.main();
    }
    if (false) {
      const customHoverCardBackdrop = new CustomHoverCardBackdrop();
      customHoverCardBackdrop.main();
    }
    if (LustData.get("Custom-Gamemode-Icon")) {
      const customGamemodeIcon = new CustomGamemodeIcon();
      customGamemodeIcon.main();
    }
    if (LustData.get("Custom-Loading-Icon")) {
      const customLoadingIcon = new CustomLoadingIcon();
      customLoadingIcon.main();
    }
    if (false) {
      const customEmblemIcon = new CustomEmblemIcon();
      customEmblemIcon.main();
    }
  }
}

class HideFriendList {
  createSidebarBackground = () => {
    const sidebarBG = document.createElement("div");
    sidebarBG.setAttribute("class", "sidebar-background");
    const sideBar = document.querySelector(".rcp-fe-viewport-sidebar > .screen-root");
    sideBar?.prepend(sidebarBG);
  };
  createButton = () => {
    const friendsActionbar = document.querySelector("#rcp-fe-viewport-root");
    const buttonDiv = document.createElement("div");
    const button = document.createElement("img");
    buttonDiv.setAttribute("class", "hideFriendslist");
    buttonDiv.addEventListener("click", () => {
      if (LustData.get("HideFriendList")) {
        LustData.set("HideFriendList", false);
      } else {
        LustData.set("HideFriendList", true);
      }
      this.buttonShowHideFriendlist(LustData.get("HideFriendList"));
      this.showHideFriendslist(LustData.get("HideFriendList"));
    });
    friendsActionbar?.append(buttonDiv);
    buttonDiv.append(button);
  };
  buttonShowHideFriendlist = (hide) => {
    const buttonDiv = document.querySelector(".hideFriendslist");
    const button = document.querySelector(".hideFriendslist > img");
    if (!hide) {
      button?.setAttribute("src", `//plugins/${getThemeName()}/assets/icon/plugins-icons/next_button.png`);
      buttonDiv.style.cssText = `transform: translateX(0px);`;
    } else {
      buttonDiv.style.cssText = `transform: translateX(225px);`;
      button?.setAttribute("src", `//plugins/${getThemeName()}/assets/icon/plugins-icons/prev_button.png`);
    }
  };
  showHideFriendslist = (hide) => {
    const elements = [
      ".lol-social-lower-pane-container",
      ".sidebar-background",
      ".alpha-version-panel",
      "lol-parties-game-info-panel",
      ".clash-social-persistent.ember-view",
      ".watermark"
    ];
    let translateValue = hide ? "225px" : "0px";
    elements.forEach((element) => {
      if (document.querySelector(element)) {
        document.querySelector(element).style.cssText = `transform: translateX(${translateValue});`;
      } else {
        error(`Get error while changing style for ${element}, but it will not affect entire theme.`);
      }
    });
    this.centerViewport(hide);
  };
  centerViewport = (hide) => {
    if (!hide) {
      try {
        document.querySelector("#centerViewport")?.remove();
      } catch {
      }
      utils.addStyleNodeWithID("centerViewport", `
                div[data-screen-name=social] > .social-plugin-home > .ember-view {
                    height: 100% !important;
                }
                .parties-game-type-select-wrapper.ember-view,
                .parties-custom-game-setup.ember-view ,
                .custom-game-list.ember-view,
                .v2-footer-component.ember-view,
                .parties-point-eligibility-custom.ember-view,
                .custom-game-teams.ember-view,
                .arrow-footer.ember-view > div,
                .parties-invite-dropzone,
                .party-members-container,
                .tft-cards-container,
                .tft-footer-container.ember-view,
                .multiteam-lobby-root__scrollable-wrapper,
                .career-postgame-progression-component, 
                .postgame-root-component .postgame-footer,
                .career-postgame-sub-navigation-component,
                .postgame-root-component .postgame-progression-lottie-outline,
                .scoreboard-root-content-container,
                .emote-wheel-wrapper-v2,
                .emote-root-component .nav-container,
                .emote-delete-slot,
                .emote-reaction-wrapper  {
                    transform: translateX(0px) !important;
                }
            `);
    } else {
      try {
        document.querySelector("#centerViewport")?.remove();
      } catch {
      }
      utils.addStyleNodeWithID("centerViewport", `
                div[data-screen-name=social] > .social-plugin-home > .ember-view {
                    height: 0% !important;
                }
                .parties-game-type-select-wrapper.ember-view,
                .parties-custom-game-setup.ember-view ,
                .custom-game-list.ember-view,
                .v2-footer-component.ember-view,
                .parties-point-eligibility-custom.ember-view,
                .custom-game-teams.ember-view,
                .arrow-footer.ember-view > div,
                .parties-invite-dropzone,
                .party-members-container,
                .tft-cards-container,
                .tft-footer-container.ember-view,
                .multiteam-lobby-root__scrollable-wrapper,
                .career-postgame-progression-component, 
                .postgame-root-component .postgame-footer,
                .career-postgame-sub-navigation-component,
                .postgame-root-component .postgame-progression-lottie-outline,
                .scoreboard-root-content-container,
                .emote-wheel-wrapper-v2,
                .emote-root-component .nav-container,
                .emote-delete-slot,
                .emote-reaction-wrapper  {
                    transform: translateX(113px) !important;
                }
            `);
    }
  };
  showHideButton = () => {
    let pageListenner = async (node) => {
      const pagename = node.getAttribute("data-screen-name");
      const isOtherPage = !["rcp-fe-lol-champ-select"].includes(pagename);
      if (pagename === "rcp-fe-lol-champ-select") {
        try {
          let button = document.querySelector(".hideFriendslist");
          button.style.display = "none";
        } catch {
        }
      } else if (isOtherPage && document.querySelector(".hideFriendslist")) {
        try {
          let button = document.querySelector(".hideFriendslist");
          button.style.display = "block";
        } catch {
        }
      }
    };
    utils.mutationObserverAddCallback(pageListenner, ["screen-root"]);
  };
  main = () => {
    this.showHideButton();
    observer.subscribeToElementCreation(".actions-bar > .buttons", (element) => {
      if (document.querySelector(".sidebar-background"))
        return;
      try {
        let bg = document.getElementsByClassName("sidebar-background");
        if (bg.length > 1) {
          for (let i = 0; i < bg.length; i++) {
            bg[i].remove();
          }
        }
      } catch {
      }
      this.createSidebarBackground();
    });
    observer.subscribeToElementCreation(".sidebar-background", (element) => {
      if (document.querySelector(".hideFriendslist"))
        return;
      try {
        let button = document.getElementsByClassName("hideFriendslist");
        if (button.length > 1) {
          for (let i = 0; i < button.length; i++) {
            button[i].remove();
          }
        }
      } catch {
      }
      if (LustData.get("enable-hide-top-navbar-friendlist-button")) {
        this.createButton();
        this.buttonShowHideFriendlist(LustData.get("HideFriendList"));
        this.showHideFriendslist(LustData.get("HideFriendList"));
      }
    });
  };
}

let datapath$2 = `//plugins/${getThemeName()}/`;
let bgInterval;
const list = (await cdnImport(`${datapath$2}config/champsBgList.js`, "Can't import custom champion data")).default;
class CustomChampsBg {
  updateDefaultSkinThumbnails(selector, img) {
    const elements = document.querySelectorAll(selector);
    elements.forEach((element) => {
      const defaultSkinThumbnail = element.querySelector("div");
      if (defaultSkinThumbnail && defaultSkinThumbnail.style.backgroundImage.includes("tile_0")) {
        defaultSkinThumbnail.style.backgroundImage = img;
      }
    });
  }
  customOnCollectionTab = () => {
    for (const item of list) {
      const firstDefaultFilename = item.first_default_filename;
      const firstDefaultFilenameLower = firstDefaultFilename.toLowerCase();
      const secondDefaultFilename = item.second_default_filename;
      const secondDefaultFilenameLower = secondDefaultFilename.toLowerCase();
      const baseURL = `/lol-game-data/assets/ASSETS/Characters`;
      const imagesBase = `${baseURL}/${firstDefaultFilename}/Skins/Base/Images`;
      const customImage = `${datapath$2}assets/champs/${item.image}`;
      const customPreviewImage = `${datapath$2}assets/champs/${item.image_preview}`;
      for (const charDir of [firstDefaultFilename, firstDefaultFilenameLower]) {
        for (const filename of ["LoadScreen", "Loadscreen"]) {
          utils.updateImageSrc(`${baseURL}/${charDir}/Skins/Base/${firstDefaultFilename}${filename}.jpg`, customPreviewImage);
          utils.updateImageSrc(`${baseURL}/${charDir}/Skins/Base/${firstDefaultFilename}${filename}_0.jpg`, customPreviewImage);
          utils.updateImageSrc(`${baseURL}/${charDir}/Skins/Base/${firstDefaultFilename}${filename}_0.${secondDefaultFilename}.jpg`, customPreviewImage);
        }
      }
      for (const name of [firstDefaultFilename, firstDefaultFilenameLower]) {
        for (const type of ["centered", "uncentered"]) {
          utils.updateImageSrc(`${imagesBase}/${name}_splash_${type}_0.jpg`, customImage);
          utils.updateImageSrc(`${imagesBase}/${name}_splash_${type}_0.${secondDefaultFilename}.jpg`, customImage);
          utils.updateImageSrc(`${imagesBase}/${name}_splash_${type}_0.${secondDefaultFilenameLower}.jpg`, customImage);
        }
      }
    }
  };
  customOnCollectionTabLoop = () => {
    const thumbnails = document.getElementsByClassName("champion-thumbnail");
    const nameContainers = document.getElementsByClassName("champion-name-container");
    for (let i = 0; i < thumbnails.length; i++) {
      const nameContainer = nameContainers[i];
      if (!nameContainer)
        continue;
      const championNameElement = nameContainer.querySelector(".champion-name");
      if (!championNameElement)
        continue;
      const cleanName = championNameElement.innerText.replace(/\s+/g, "").toLowerCase();
      const champData = list.find(
        (champ) => cleanName === champ.default_champion_name.replace(/\s+/g, "").toLowerCase() || cleanName === champ.replace_name.replace(/\s+/g, "").toLowerCase()
      );
      if (champData) {
        if (!nameContainer.querySelector("#champion-name-replace")) {
          let newName = document.createElement("p");
          newName.classList.add("champion-name");
          newName.id = "champion-name-replace";
          newName.innerText = champData.replace_name;
          nameContainer.append(newName);
          championNameElement.style.display = "none";
          log(`Replaced ${champData.default_champion_name} with ${champData.replace_name}`);
        }
      } else {
        const replacedName = nameContainer.querySelector("#champion-name-replace");
        if (replacedName) {
          championNameElement.style.removeProperty("display");
          replacedName.remove();
          log(`Restored ${championNameElement.innerText}`);
        }
      }
    }
    const champNameWhenHoverInCollection = document.querySelectorAll(".name-progress-container .champion-name");
    champNameWhenHoverInCollection.forEach((champName) => {
      const champData = list.find(
        (champ) => champName.textContent?.replace(/\s+/g, "").toLowerCase() === champ.default_champion_name.replace(/\s+/g, "").toLowerCase() || champName.textContent?.replace(/\s+/g, "").toLowerCase() === champ.replace_name.replace(/\s+/g, "").toLowerCase()
      );
      if (champData) {
        champName.textContent = champData.replace_name;
      }
    });
  };
  customOnProfileTabLoop = () => {
    const profileMasteryIcons = document.querySelectorAll(".style-profile-champion-icon-masked img");
    profileMasteryIcons.forEach((profileMasteryIcon) => {
      const champData = list.find(
        (champ) => profileMasteryIcon.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        profileMasteryIcon.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    const profileMasteryChampTitles = document.querySelectorAll(".profile-lcm-tooltip-contents-title");
    profileMasteryChampTitles.forEach((profileMasteryChampTitle) => {
      const champData = list.find(
        (champ) => profileMasteryChampTitle.textContent?.replace(/\s+/g, "").toLowerCase() === champ.default_champion_name.replace(/\s+/g, "").toLowerCase() || profileMasteryChampTitle.textContent?.replace(/\s+/g, "").toLowerCase() === champ.replace_name.replace(/\s+/g, "").toLowerCase()
      );
      if (champData) {
        profileMasteryChampTitle.textContent = champData.replace_name;
      }
    });
    const profileEternalsIcons = document.querySelectorAll(".profile-eternals-champion-icon");
    profileEternalsIcons.forEach((profileEternalIcon) => {
      const champData = list.find(
        (champ) => profileEternalIcon.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        profileEternalIcon.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
  };
  customOnChampionSelectLoop = () => {
    const champSelectList = document.querySelectorAll(".champion-grid-champion-thumbnail");
    champSelectList.forEach((thumbnail) => {
      const img = thumbnail.querySelector("img");
      if (!img)
        return;
      const champData = list.find(
        (champ) => img.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        img.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
  };
  customOnLootTab = () => {
    observer.subscribeToElementCreation(".loot-item-visual-container", (element) => {
      for (let i = 0; i < list.length; i++) {
        let champIcon = element.querySelector(".icon").style.backgroundImage;
        if (champIcon.match(/Characters\/([^\/]+)\//)?.[1].toLowerCase() == list[i]["default_champion_name"].toLowerCase() || champIcon.match(/Characters\/([^\/]+)\//)?.[1].toLowerCase() == list[i]["replace_name"].toLowerCase()) {
          champIcon = `url(${datapath$2}assets/champs/${list[i]["image_thumbnail"]})`;
        }
      }
    });
  };
  customOnLootTabLoop = () => {
    document.querySelectorAll(".loot-item-tooltip-hero");
  };
  customChampionDetailsPage = () => {
    observer.subscribeToElementCreation(".lockup-champion-name", (element) => {
      bgInterval = window.setInterval(() => {
        for (let j = 0; j < list.length; j++) {
          if (element.textContent.replace(/\n\s*/g, "") == list[j]["default_champion_name"] || element.textContent.replace(/\n\s*/g, "") == list[j]["replace_name"]) {
            element.textContent = list[j]["replace_name"];
            element.parentNode.querySelector(".lockup-champion-title").textContent = list[j]["replace_sub_name"];
            let overview = document.querySelector("lol-uikit-section[section-id='cdp_overview'] .cdp-backdrop-img");
            if (overview) {
              let bio = document.querySelector(".cdp-overview-short-bio");
              if (bio && list[j]["lore"] != "") {
                bio.innerHTML = list[j]["lore"];
              }
              overview.style.cssText = `left: ${list[j]["css-left"]}`;
            }
            let mastery = document.querySelector("lol-uikit-section[section-id='cdp_mastery'] .cdp-backdrop-img");
            if (mastery) {
              mastery.style.cssText = `left: ${list[j]["css-left"]}`;
            }
            let progression = document.querySelector("lol-uikit-section[section-id='cdp_progression'] .cdp-backdrop-img");
            if (progression) {
              progression.style.cssText = `left: ${list[j]["css-left"]}`;
            }
            let skinName = document.querySelector(".champion-skin-name.skin-name");
            if (document.querySelector(".cdp-skins-section.ember-view > lol-uikit-section-controller[selected-item='skin_0']")) {
              if (skinName)
                skinName.textContent = list[j]["replace_name"];
            }
            this.updateDefaultSkinThumbnails(".carousel-track-container .buffer-wrapper", `url(${datapath$2}assets/champs/${list[j]["image_thumbnail"]})`);
            this.updateDefaultSkinThumbnails(".carousel-track-container .thumbnail-wrapper", `url(${datapath$2}assets/champs/${list[j]["image_thumbnail"]})`);
          }
        }
      }, 100);
    });
    observer.subscribeToElementDeletion(".lockup-champion-name", (element) => {
      window.clearInterval(bgInterval);
      log("cleared Interval!");
    });
  };
  customOnMatchHistoryTab = () => {
    observer.subscribeToElementCreation(".player-history-champion-pic", (element) => {
      const champData = list.find(
        (champ) => element.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".recent-champ-img", (element) => {
      const champData = list.find(
        (champ) => element.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".match-details-team-list", (element) => {
      const champIcons = element.querySelectorAll(".player-history-champion-pic");
      champIcons.forEach((champIcon) => {
        champIcon.style.width = "128px";
      });
    });
    observer.subscribeToElementCreation(".map-champ-toggle-img", (element) => {
      const champData = list.find(
        (champ) => element.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".team-avatar-img", (element) => {
      const champData = list.find(
        (champ) => element.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".tick.team-blue", (element) => {
      const champData = list.find(
        (champ) => element.querySelector(".avatar")?.getAttribute("href")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.querySelector(".avatar")?.setAttribute("href", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".tick.team-red", (element) => {
      const champData = list.find(
        (champ) => element.querySelector(".avatar")?.getAttribute("href")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.querySelector(".avatar")?.setAttribute("href", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    observer.subscribeToElementCreation(".runes-player-stats", (element) => {
      const champData = list.find(
        (champ) => element.querySelector(".champion-pic")?.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        element.querySelector(".champion-pic")?.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
  };
  customOnMatchHistoryTabLoop = () => {
    const champNameWhenHoverInRecentPlayedChamps = document.querySelectorAll("lol-uikit-champion-mastery-tooltip");
    champNameWhenHoverInRecentPlayedChamps.forEach((champName) => {
      const champData = list.find(
        (champ) => champName.getAttribute("name")?.replace(/\s+/g, "").toLowerCase() === champ.default_champion_name.replace(/\s+/g, "").toLowerCase() || champName.getAttribute("name")?.replace(/\s+/g, "").toLowerCase() === champ.replace_name.replace(/\s+/g, "").toLowerCase()
      );
      if (champData) {
        let nameElement = champName.shadowRoot;
        if (nameElement) {
          nameElement.querySelector(".name").textContent = champData.replace_name;
        }
      }
    });
    const champIconsWhenHoverInMatchEvent = document.querySelectorAll(".match-details-event-tooltip .event-tooltip-icon-champion .event-tooltip-icon-img");
    champIconsWhenHoverInMatchEvent.forEach((champIcon) => {
      const champData = list.find(
        (champ) => champIcon.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        champIcon.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    const champIconsWhenHoverInMatchMapEvent = document.querySelectorAll(".match-details-map-event-tooltip .map-event-tooltip-icon .map-event-tooltip-icon-img");
    champIconsWhenHoverInMatchMapEvent.forEach((champIcon) => {
      const champData = list.find(
        (champ) => champIcon.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        champIcon.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
  };
  customOnCustomGameTeamLoop = () => {
    const botIcon = document.querySelectorAll(".custom-member-bot-icon-img");
    botIcon.forEach((thumbnail) => {
      const champData = list.find(
        (champ) => thumbnail.getAttribute("src")?.includes(champ.default_icon_id.toString())
      );
      if (champData) {
        thumbnail.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
      }
    });
    const botName = document.querySelectorAll(".custom-bot-champion-name");
    botName.forEach((name) => {
      const champData = list.find(
        (champ) => name.textContent?.replace(/\s+/g, "").toLowerCase() === champ.default_champion_name.replace(/\s+/g, "").toLowerCase() || name.textContent?.replace(/\s+/g, "").toLowerCase() === champ.replace_name.replace(/\s+/g, "").toLowerCase()
      );
      if (champData) {
        name.textContent = champData.replace_name;
      }
    });
  };
  main = () => {
    this.customOnCollectionTab();
    this.customOnLootTab();
    this.customChampionDetailsPage();
    this.customOnMatchHistoryTab();
    window.setInterval(() => {
      this.customOnChampionSelectLoop();
      this.customOnCollectionTabLoop();
      this.customOnProfileTabLoop();
      this.customOnLootTabLoop();
      this.customOnMatchHistoryTabLoop();
      this.customOnCustomGameTeamLoop();
      const champSetRow = document.querySelectorAll(".champion-set-row .champion-border");
      champSetRow.forEach((border) => {
        const img = border.querySelector("img");
        if (!img)
          return;
        const champData = list.find(
          (champ) => img.getAttribute("src")?.includes(champ.default_icon_id.toString())
        );
        if (champData) {
          img.setAttribute("src", `${datapath$2}assets/champs/${champData.image_thumbnail}`);
        }
      });
    }, 100);
  };
}

observer.subscribeToElementCreation(".parallax-layer-container", (element) => element.style.backgroundImage = "");
class ApplyUI {
  main = async () => {
    const homePage = new HomePage();
    homePage.main();
    const removeGamemode = new RemoveGamemode();
    removeGamemode.main();
    const customProfile = new CustomProfile();
    customProfile.customBagde();
    if (LustData.get("invisible_banner")) {
      customProfile.invisibleBanner();
    }
    if (LustData.get("Custom-profile-hover")) {
      if (LustData.get("Custom-challenge-crystal"))
        customProfile.customChallengeCrystal();
    }
    if (false)
      customProfile.CustomProfileRankName();
    if (LustData.get("Runes-BG")) {
      const customRunesBackground = new CustomRunesBackground();
      customRunesBackground.removeOtherImage();
      customRunesBackground.changeRunesBackground();
    }
    if (LustData.get("new-gamesearch-queue")) {
      const customgameSearchCard = new CustomGameSearchCard();
      customgameSearchCard.restyleGamesearchCard();
    }
    if (LustData.get("settings-dialogs-transparent")) {
      const transparentSettingsDialogs = new TransparentSettingsDialogs();
      transparentSettingsDialogs.applyStyle();
    }
    if (LustData.get("Custom-Icon")) {
      const customIcon = new CustomIcon();
      customIcon.main();
    }
    const hideFriendslist = new HideFriendList();
    hideFriendslist.main();
    if (LustData.get("custom-champs-image")) {
      const customChampsBg = new CustomChampsBg();
      customChampsBg.main();
    }
  };
}

let filtersData = (await cdnImport(`//plugins/${getThemeName()}/config/filters.js`, "Can't import filters data")).default;
class Filters {
  filtersDataMap = {
    "rcp-fe-lol-yourshop": "Yourshop",
    "rcp-fe-lol-home-main": "Homepage",
    "rcp-fe-lol-activity-center-main": "Homepage",
    "rcp-fe-lol-champ-select": "Champ-select",
    "rcp-fe-lol-store": "Store",
    "rcp-fe-lol-collections": "Collections",
    "rcp-fe-lol-profiles-main": "Profiles",
    "rcp-fe-lol-parties": "Parties",
    "rcp-fe-lol-loot": "Loot",
    "rcp-fe-lol-clash-full": "Clash",
    "rcp-fe-lol-postgame": "Postgame",
    "rcp-fe-lol-event-hub": "EventShop",
    "rcp-fe-lol-tft": "TFT"
  };
  addFilterCss = () => {
    utils.addStyleNode(
      /*css*/
      `
			:root {
				--play-button-filter: ${filtersData["PlayButton"]};
				--find-match-button: ${filtersData["find-match-button"]};
				--PartiesStatusCard: ${filtersData["PartiesStatusCard"]};
			}
		`
    );
  };
  addBackgroundFilter = async (node) => {
    let pagename = "";
    let previous_page = "";
    const lustBg = document.getElementById("lust-bg");
    const lustStaticBg = document.getElementById("lust-static-bg");
    const brightness_modifiers = Object.keys(this.filtersDataMap);
    pagename = node?.getAttribute("data-screen-name");
    log(`%c${pagename}`, "color: #e4c2b3");
    if (lustBg && lustStaticBg) {
      if (this.filtersDataMap[pagename]) {
        lustBg.style.filter = filtersData[this.filtersDataMap[pagename]];
        lustStaticBg.style.filter = filtersData[this.filtersDataMap[pagename]];
      } else if (brightness_modifiers.indexOf(previous_page) !== -1) {
        lustBg.style.filter = filtersData["Homepage"];
        lustStaticBg.style.filter = filtersData["Homepage"];
      }
      if (previous_page !== pagename) {
        previous_page = pagename;
      }
    } else {
      log(`Cannot set the filter`);
    }
  };
  main = () => {
    this.addFilterCss();
    utils.mutationObserverAddCallback(this.addBackgroundFilter, ["screen-root"]);
    utils.subscribe_endpoint("/lol-gameflow/v1/gameflow-phase", (message) => {
      let phase = JSON.parse(message["data"])[2]["data"];
      if (phase == "GameStart" || phase == "InProgress") {
        const lustBg = document.getElementById("lust-bg");
        lustBg.style.filter = filtersData["Gamestart"];
      }
    });
  };
}

var commonjsGlobal = typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : typeof global !== 'undefined' ? global : typeof self !== 'undefined' ? self : {};

var lib = {};

var core = {};

(function (exports) {
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.h = exports._render = exports.hydrate = exports.render = exports.appendChildren = exports.strToHash = exports.removeAllChildNodes = exports.tick = exports.isSSR = void 0;

	const isSSR = () => typeof _nano !== 'undefined' && _nano.isSSR === true;
	exports.isSSR = isSSR;
	/** Creates a new Microtask using Promise() */
	exports.tick = Promise.prototype.then.bind(Promise.resolve());
	const removeAllChildNodes = (parent) => {
	    while (parent.firstChild) {
	        parent.removeChild(parent.firstChild);
	    }
	};
	exports.removeAllChildNodes = removeAllChildNodes;
	// https://stackoverflow.com/a/7616484/12656855
	const strToHash = (s) => {
	    let hash = 0;
	    for (let i = 0; i < s.length; i++) {
	        const chr = s.charCodeAt(i);
	        hash = (hash << 5) - hash + chr;
	        hash |= 0; // Convert to 32bit integer
	    }
	    return Math.abs(hash).toString(32);
	};
	exports.strToHash = strToHash;
	const appendChildren = (element, children, escape = true) => {
	    // if the child is an html element
	    if (!Array.isArray(children)) {
	        (0, exports.appendChildren)(element, [children], escape);
	        return;
	    }
	    // htmlCollection to array
	    if (typeof children === 'object')
	        children = Array.prototype.slice.call(children);
	    children.forEach(child => {
	        // if child is an array of children, append them instead
	        if (Array.isArray(child))
	            (0, exports.appendChildren)(element, child, escape);
	        else {
	            // render the component
	            const c = (0, exports._render)(child);
	            if (typeof c !== 'undefined') {
	                // if c is an array of children, append them instead
	                if (Array.isArray(c))
	                    (0, exports.appendChildren)(element, c, escape);
	                // apply the component to parent element
	                else {
	                    if ((0, exports.isSSR)() && !escape)
	                        element.appendChild(c.nodeType == null ? c.toString() : c);
	                    else
	                        element.appendChild(c.nodeType == null ? document.createTextNode(c.toString()) : c);
	                }
	            }
	        }
	    });
	};
	exports.appendChildren = appendChildren;
	/**
	 * A simple component for rendering SVGs
	 */
	const SVG = (props) => {
	    const child = props.children[0];
	    const attrs = child.attributes;
	    if ((0, exports.isSSR)())
	        return child;
	    const svg = hNS('svg');
	    for (let i = attrs.length - 1; i >= 0; i--) {
	        svg.setAttribute(attrs[i].name, attrs[i].value);
	    }
	    svg.innerHTML = child.innerHTML;
	    return svg;
	};
	/** Returns the populated parent if available else  one child or an array of children */
	const render = (component, parent = null, removeChildNodes = true) => {
	    let el = (0, exports._render)(component);
	    if (Array.isArray(el)) {
	        el = el.map(e => (0, exports._render)(e));
	        if (el.length === 1)
	            el = el[0];
	    }
	    if (parent) {
	        if (removeChildNodes)
	            (0, exports.removeAllChildNodes)(parent);
	        // if parent and child are the same, we replace the parent instead of appending to it
	        if (el && parent.id && parent.id === el.id && parent.parentElement) {
	            parent.parentElement.replaceChild(el, parent);
	        }
	        else {
	            // append element(s) to the parent
	            if (Array.isArray(el))
	                el.forEach((e) => {
	                    (0, exports.appendChildren)(parent, (0, exports._render)(e));
	                    //parent.appendChild(_render(e))
	                });
	            else
	                (0, exports.appendChildren)(parent, (0, exports._render)(el));
	        }
	        return parent;
	    }
	    // returning one child or an array of children
	    else {
	        if ((0, exports.isSSR)() && !Array.isArray(el))
	            return [el];
	        return el;
	    }
	};
	exports.render = render;
	exports.hydrate = exports.render;
	const _render = (comp) => {
	    // null, false, undefined
	    if (comp === null || comp === false || typeof comp === 'undefined')
	        return [];
	    // string, number
	    if (typeof comp === 'string' || typeof comp === 'number')
	        return comp.toString();
	    // SVGElement
	    if (comp.tagName && comp.tagName.toLowerCase() === 'svg')
	        return SVG({ children: [comp] });
	    // HTMLElement
	    if (comp.tagName)
	        return comp;
	    // TEXTNode (Node.TEXT_NODE === 3)
	    if (comp && comp.nodeType === 3)
	        return comp;
	    // Class Component
	    if (comp && comp.component && comp.component.isClass)
	        return renderClassComponent(comp);
	    // Class Component (Uninitialized)
	    if (comp.isClass)
	        return renderClassComponent({ component: comp, props: {} });
	    // Functional Component
	    if (comp.component && typeof comp.component === 'function')
	        return renderFunctionalComponent(comp);
	    // Array (render each child and return the array) (is probably a fragment)
	    if (Array.isArray(comp))
	        return comp.map(c => (0, exports._render)(c)).flat();
	    // function
	    if (typeof comp === 'function' && !comp.isClass)
	        return (0, exports._render)(comp());
	    // if component is a HTMLElement (rare case)
	    if (comp.component && comp.component.tagName && typeof comp.component.tagName === 'string')
	        return (0, exports._render)(comp.component);
	    // (rare case)
	    if (Array.isArray(comp.component))
	        return (0, exports._render)(comp.component);
	    // (rare case)
	    if (comp.component)
	        return (0, exports._render)(comp.component);
	    // object
	    if (typeof comp === 'object')
	        return [];
	    console.warn('Something unexpected happened with:', comp);
	};
	exports._render = _render;
	const renderFunctionalComponent = (fncComp) => {
	    const { component, props } = fncComp;
	    return (0, exports._render)(component(props));
	};
	const renderClassComponent = (classComp) => {
	    const { component, props } = classComp;
	    // calc hash
	    const hash = (0, exports.strToHash)(component.toString());
	    // make hash accessible in constructor, without passing it to it
	    component.prototype._getHash = () => hash;
	    const Component = new component(props);
	    if (!(0, exports.isSSR)())
	        Component.willMount();
	    let el = Component.render();
	    el = (0, exports._render)(el);
	    Component.elements = el;
	    // pass the component instance as ref
	    if (props && props.ref)
	        props.ref(Component);
	    if (!(0, exports.isSSR)())
	        (0, exports.tick)(() => {
	            Component._didMount();
	        });
	    return el;
	};
	const hNS = (tag) => document.createElementNS('http://www.w3.org/2000/svg', tag);
	// https://stackoverflow.com/a/42405694/12656855
	const h = (tagNameOrComponent, props = {}, ...children) => {
	    // if children is passed as props, merge with ...children
	    if (props && props.children) {
	        if (Array.isArray(children)) {
	            if (Array.isArray(props.children))
	                children = [...props.children, ...children];
	            else
	                children.push(props.children);
	        }
	        else {
	            if (Array.isArray(props.children))
	                children = props.children;
	            else
	                children = [props.children];
	        }
	    }
	    // render WebComponent in SSR
	    if ((0, exports.isSSR)() && _nano.ssrTricks.isWebComponent(tagNameOrComponent)) {
	        const element = _nano.ssrTricks.renderWebComponent(tagNameOrComponent, props, children, exports._render);
	        if (element === null)
	            return `ERROR: "<${tagNameOrComponent} />"`;
	        else
	            return element;
	    }
	    // if tagNameOrComponent is a component
	    if (typeof tagNameOrComponent !== 'string')
	        return { component: tagNameOrComponent, props: Object.assign(Object.assign({}, props), { children: children }) };
	    // custom message if document is not defined in SSR
	    try {
	        if ((0, exports.isSSR)() && typeof tagNameOrComponent === 'string' && !document)
	            throw new Error('document is not defined');
	    }
	    catch (err) {
	        console.log('ERROR:', err.message, '\n > Please read: https://github.com/nanojsx/nano/issues/106');
	    }
	    let ref;
	    const element = tagNameOrComponent === 'svg'
	        ? hNS('svg')
	        : document.createElement(tagNameOrComponent);
	    // check if the element includes the event (for example 'oninput')
	    const isEvent = (el, p) => {
	        // check if the event begins with 'on'
	        if (0 !== p.indexOf('on'))
	            return false;
	        // we return true if SSR, since otherwise it will get rendered
	        if (el._ssr)
	            return true;
	        // check if the event is present in the element as object (null) or as function
	        return typeof el[p] === 'object' || typeof el[p] === 'function';
	    };
	    for (const p in props) {
	        // https://stackoverflow.com/a/45205645/12656855
	        // style object to style string
	        if (p === 'style' && typeof props[p] === 'object') {
	            const styles = Object.keys(props[p])
	                .map(k => `${k}:${props[p][k]}`)
	                .join(';')
	                .replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
	            props[p] = `${styles};`;
	        }
	        // handel ref
	        if (p === 'ref')
	            ref = props[p];
	        // handle events
	        else if (isEvent(element, p.toLowerCase()))
	            element.addEventListener(p.toLowerCase().substring(2), (e) => props[p](e));
	        // dangerouslySetInnerHTML
	        else if (p === 'dangerouslySetInnerHTML' && props[p].__html) {
	            if (!(0, exports.isSSR)()) {
	                const fragment = document.createElement('fragment');
	                fragment.innerHTML = props[p].__html;
	                element.appendChild(fragment);
	            }
	            else {
	                element.innerHTML = props[p].__html;
	            }
	        }
	        // modern dangerouslySetInnerHTML
	        else if (p === 'innerHTML' && props[p].__dangerousHtml) {
	            if (!(0, exports.isSSR)()) {
	                const fragment = document.createElement('fragment');
	                fragment.innerHTML = props[p].__dangerousHtml;
	                element.appendChild(fragment);
	            }
	            else {
	                element.innerHTML = props[p].__dangerousHtml;
	            }
	        }
	        // className
	        else if (/^className$/i.test(p))
	            element.setAttribute('class', props[p]);
	        // setAttribute
	        else if (typeof props[p] !== 'undefined')
	            element.setAttribute(p, props[p]);
	    }
	    // these tags should not be escaped by default (in ssr)
	    const escape = !['noscript', 'script', 'style'].includes(tagNameOrComponent);
	    (0, exports.appendChildren)(element, children, escape);
	    if (ref)
	        ref(element);
	    return element;
	};
	exports.h = h;
	
} (core));

var component = {};

var helpers = {};

var version = {};

Object.defineProperty(version, "__esModule", { value: true });
version.VERSION = void 0;
// THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.
version.VERSION = '0.1.0';

Object.defineProperty(helpers, "__esModule", { value: true });
helpers.printVersion = helpers.escapeHtml = helpers.onNodeRemove = helpers.detectSSR = helpers.nodeToString = helpers.task = void 0;
const version_js_1 = version;
/** Creates a new Task using setTimeout() */
const task = (task) => setTimeout(task, 0);
helpers.task = task;
const nodeToString = (node) => {
    const tmpNode = document.createElement('div');
    tmpNode.appendChild(node.cloneNode(true));
    return tmpNode.innerHTML;
};
helpers.nodeToString = nodeToString;
const detectSSR = () => {
    // @ts-ignore
    const isDeno = typeof Deno !== 'undefined';
    const hasWindow = typeof window !== 'undefined' ? true : false;
    return (typeof _nano !== 'undefined' && _nano.isSSR) || isDeno || !hasWindow;
};
helpers.detectSSR = detectSSR;
function isDescendant(desc, root) {
    // @ts-ignore
    return !!desc && (desc === root || isDescendant(desc.parentNode, root));
}
// https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver
const onNodeRemove = (element, callback) => {
    let observer = new MutationObserver(mutationsList => {
        mutationsList.forEach(mutation => {
            mutation.removedNodes.forEach(removed => {
                if (isDescendant(element, removed)) {
                    callback();
                    if (observer) {
                        // allow garbage collection
                        observer.disconnect();
                        // @ts-ignore
                        observer = undefined;
                    }
                }
            });
        });
    });
    observer.observe(document, {
        childList: true,
        subtree: true
    });
    return observer;
};
helpers.onNodeRemove = onNodeRemove;
// https://stackoverflow.com/a/6234804
const escapeHtml = (unsafe) => {
    if (unsafe && typeof unsafe === 'string')
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    return unsafe;
};
helpers.escapeHtml = escapeHtml;
const printVersion = () => {
    const info = `Powered by nano JSX v${version_js_1.VERSION}`;
    console.log(`%c %c %c %c %c ${info} %c http://nanojsx.io`, 'background: #ff0000', 'background: #ffff00', 'background: #00ff00', 'background: #00ffff', 'color: #fff; background: #000000;', 'background: none');
};
helpers.printVersion = printVersion;

var state = {};

(function (exports) {
	Object.defineProperty(exports, "__esModule", { value: true });
	exports._clearState = exports._state = void 0;
	/** Holds the state of the whole application. */
	exports._state = new Map();
	/** Clears the state of the whole application. */
	const _clearState = () => {
	    exports._state.clear();
	};
	exports._clearState = _clearState;
	
} (state));

Object.defineProperty(component, "__esModule", { value: true });
component.Component = void 0;
const helpers_js_1$1 = helpers;
const core_js_1$a = core;
const state_js_1 = state;
class Component {
    constructor(props) {
        this._elements = [];
        this._skipUnmount = false;
        this._hasUnmounted = false;
        this.props = props || {};
        this.id = this._getHash();
    }
    static get isClass() {
        return true;
    }
    get isClass() {
        return true;
    }
    setState(state, shouldUpdate = false) {
        const isObject = typeof state === 'object' && state !== null;
        // if state is an object, we merge the objects
        if (isObject && this.state !== undefined)
            this.state = Object.assign(Object.assign({}, this.state), state);
        // else, we just overwrite it
        else
            this.state = state;
        if (shouldUpdate)
            this.update();
    }
    set state(state) {
        state_js_1._state.set(this.id, state);
    }
    get state() {
        return state_js_1._state.get(this.id);
    }
    set initState(state) {
        if (this.state === undefined)
            this.state = state;
    }
    /** Returns all currently rendered node elements */
    get elements() {
        return this._elements || [];
    }
    set elements(elements) {
        if (!Array.isArray(elements))
            elements = [elements];
        elements.forEach(element => {
            this._elements.push(element);
        });
    }
    _addNodeRemoveListener() {
        // check if didUnmount is unused
        if (/^[^{]+{\s+}$/gm.test(this.didUnmount.toString()))
            return;
        // listen if the root elements gets removed
        (0, helpers_js_1$1.onNodeRemove)(this.elements[0], () => {
            if (!this._skipUnmount)
                this._didUnmount();
        });
    }
    // @ts-ignore
    _didMount() {
        this._addNodeRemoveListener();
        this.didMount();
    }
    _willUpdate() {
        this.willUpdate();
    }
    _didUpdate() {
        this.didUpdate();
    }
    _didUnmount() {
        if (this._hasUnmounted)
            return;
        this.didUnmount();
        this._hasUnmounted = true;
    }
    willMount() { }
    didMount() { }
    willUpdate() { }
    didUpdate() { }
    didUnmount() { }
    render(_update) { }
    /** Will forceRender the component */
    update(update) {
        this._skipUnmount = true;
        this._willUpdate();
        // get all current rendered node elements
        const oldElements = [...this.elements];
        // clear
        this._elements = [];
        let el = this.render(update);
        el = (0, core_js_1$a._render)(el);
        this.elements = el;
        // console.log('old: ', oldElements)
        // console.log('new: ', this.elements)
        // get valid parent node
        const parent = oldElements[0].parentElement;
        // make sure we have a parent
        if (!parent)
            console.warn('Component needs a parent element to get updated!');
        // add all new node elements
        this.elements.forEach((child) => {
            if (parent)
                parent.insertBefore(child, oldElements[0]);
        });
        // remove all elements
        oldElements.forEach((child) => {
            // wee keep the element if it is the same, for example if passed as a child
            if (!this.elements.includes(child)) {
                child.remove();
                // @ts-ignore
                child = null;
            }
        });
        // listen for node removal
        this._addNodeRemoveListener();
        // @ts-ignore
        (0, core_js_1$a.tick)(() => {
            this._skipUnmount = false;
            if (!this.elements[0].isConnected)
                this._didUnmount();
            else
                this._didUpdate();
        });
    }
    _getHash() { }
}
component.Component = Component;

var components = {};

var helmet = {};

Object.defineProperty(helmet, "__esModule", { value: true });
helmet.Helmet = void 0;
const component_js_1$5 = component;
const core_js_1$9 = core;
class Attributes extends Map {
    toString() {
        let string = '';
        for (const [key, value] of this)
            string += ` ${key}="${value}"`;
        return string.trim();
    }
}
class Helmet extends component_js_1$5.Component {
    static SSR(body) {
        var _a, _b;
        const reg = /(<helmet\b[^>]*>)((.|\r|\n)*?)(<\/helmet>)/gm;
        // collect all elements
        const head = [];
        const footer = [];
        const attributes = {
            html: new Attributes(),
            body: new Attributes()
        };
        // get what's in the head
        if (typeof document !== 'undefined' && document.head) {
            let children = [];
            children = [].slice.call(document.head.children);
            for (let i = 0; i < children.length; i++) {
                // check if the same element already exists
                if (head.indexOf(children[i]) === -1) {
                    head.push(children[i]);
                }
            }
        }
        let result;
        while ((result = reg.exec(body)) !== null) {
            const first = result[1];
            let second = result[2];
            const regHTML = /<html\s([^>]+)><\/html>/gm;
            const regBody = /<body\s([^>]+)><\/body>/gm;
            const regAttr = /(\w+)="([^"]+)"/gm;
            let res = null;
            // extract html attributes
            (_a = body.match(regHTML)) === null || _a === void 0 ? void 0 : _a.forEach(h => {
                second = second.replace(h, '');
                while ((res = regAttr.exec(h)) !== null) {
                    attributes.html.set(res[1], res[2]);
                }
            });
            // extract body attributes
            (_b = body.match(regBody)) === null || _b === void 0 ? void 0 : _b.forEach(b => {
                second = second.replace(b, '');
                while ((res = regAttr.exec(b)) !== null) {
                    attributes.body.set(res[1], res[2]);
                }
            });
            const toHead = first.includes('data-placement="head"');
            // do not add an element if it already exists
            if (toHead && !head.includes(second))
                head.push(second);
            else if (!toHead && !footer.includes(second))
                footer.push(second);
        }
        // clean the body from all matches
        const cleanBody = body.replace(reg, '');
        return {
            body: cleanBody,
            head: head,
            footer: footer,
            attributes
        };
    }
    didMount() {
        this.props.children.forEach((element) => {
            var _a, _b, _c, _d;
            // return if it is not an html element
            if (!(element instanceof HTMLElement))
                return;
            const parent = this.props.footer ? document.body : document.head;
            const tag = element.tagName;
            let attrs = [];
            // get the inner text
            attrs.push(element.innerText);
            // get all attributes
            for (let attr = 0; attr < element.attributes.length; attr++) {
                attrs.push((_a = element.attributes.item(attr)) === null || _a === void 0 ? void 0 : _a.name.toLowerCase());
                attrs.push((_b = element.attributes.item(attr)) === null || _b === void 0 ? void 0 : _b.value.toLowerCase());
            }
            // handle special tags
            if (tag === 'HTML' || tag === 'BODY') {
                const htmlTag = document.getElementsByTagName(tag)[0];
                for (let attr = 1; attr < attrs.length; attr += 2) {
                    htmlTag.setAttribute(attrs[attr], attrs[attr + 1]);
                }
                return;
            }
            else if (tag === 'TITLE') {
                const titleTags = document.getElementsByTagName('TITLE');
                if (titleTags.length > 0) {
                    const e = element;
                    titleTags[0].text = e.text;
                }
                else {
                    const titleTag = (0, core_js_1$9.h)('title', null, element.innerHTML);
                    (0, core_js_1$9.appendChildren)(parent, [titleTag], false);
                }
                return;
            }
            // check if the element already exists
            let exists = false;
            attrs = attrs.sort();
            const el = document.getElementsByTagName(tag);
            for (let i = 0; i < el.length; i++) {
                let attrs2 = [];
                // get the inner text
                attrs2.push(el[i].innerText);
                for (let attr = 0; attr < el[i].attributes.length; attr++) {
                    attrs2.push((_c = el[i].attributes.item(attr)) === null || _c === void 0 ? void 0 : _c.name.toLowerCase());
                    attrs2.push((_d = el[i].attributes.item(attr)) === null || _d === void 0 ? void 0 : _d.value.toLowerCase());
                }
                attrs2 = attrs2.sort();
                if (attrs.length > 0 && attrs2.length > 0 && JSON.stringify(attrs) === JSON.stringify(attrs2))
                    exists = true;
            }
            // add to dom
            if (!exists)
                (0, core_js_1$9.appendChildren)(parent, [element], false);
        });
    }
    render() {
        const placement = this.props.footer ? 'footer' : 'head';
        if ((0, core_js_1$9.isSSR)())
            return (0, core_js_1$9.h)('helmet', { 'data-ssr': true, 'data-placement': placement }, this.props.children);
        else
            return [];
    }
}
helmet.Helmet = Helmet;

var img = {};

var __rest$3 = (commonjsGlobal && commonjsGlobal.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
Object.defineProperty(img, "__esModule", { value: true });
img.Img = void 0;
const component_js_1$4 = component;
const core_js_1$8 = core;
/**
 * A useful Image component
 * Add <Img lazy ..., to lazy load the img source
 * Add <Img width="100" height="100" ..., to specify img element's size.
 * Add <Img placeholder="src or element" ...., to prepare placeholder for img.
 */
class Img extends component_js_1$4.Component {
    constructor(props) {
        super(props);
        const { src, key } = props;
        // id has to be unique
        this.id = `${(0, core_js_1$8.strToHash)(src)}-${(0, core_js_1$8.strToHash)(JSON.stringify(props))}`;
        if (key)
            this.id += `key-${key}`;
        // this could also be done in willMount()
        if (!this.state)
            this.setState({ isLoaded: false, image: undefined });
    }
    didMount() {
        const _a = this.props, { lazy = true, placeholder, children, key, ref } = _a, rest = __rest$3(_a, ["lazy", "placeholder", "children", "key", "ref"]);
        if (typeof lazy === 'boolean' && lazy === false)
            return;
        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    observer.disconnect();
                    this.state.image = (0, core_js_1$8.h)('img', Object.assign({}, rest));
                    if (this.state.image.complete) {
                        this.state.isLoaded = true;
                        this.update();
                    }
                    else {
                        this.state.image.onload = () => {
                            this.state.isLoaded = true;
                            this.update();
                        };
                    }
                }
            });
        }, { threshold: [0, 1] });
        observer.observe(this.elements[0]);
    }
    render() {
        const _a = this.props, { src, placeholder, children, lazy = true, key, ref } = _a, rest = __rest$3(_a, ["src", "placeholder", "children", "lazy", "key", "ref"]);
        // return the img tag if not lazy loaded
        if (typeof lazy === 'boolean' && lazy === false) {
            this.state.image = (0, core_js_1$8.h)('img', Object.assign({ src }, rest));
            return this.state.image;
        }
        // if it is visible and loaded, show the image
        if (this.state.isLoaded) {
            return this.state.image;
            // if the placeholder is an image src
        }
        else if (placeholder && typeof placeholder === 'string') {
            return (0, core_js_1$8.h)('img', Object.assign({ src: placeholder }, rest));
            // if the placeholder is an JSX element
        }
        else if (placeholder && typeof placeholder === 'function') {
            return placeholder();
        }
        else {
            // render a simple box
            const style = {};
            if (rest.width)
                style.width = `${rest.width}px`;
            if (rest.height)
                style.height = `${rest.height}px`;
            const others = __rest$3(rest, ["width", "height"]);
            return (0, core_js_1$8.h)('div', Object.assign({ style }, others));
        }
    }
}
img.Img = Img;

var link = {};

var fragment = {};

Object.defineProperty(fragment, "__esModule", { value: true });
fragment.Fragment = void 0;
const Fragment = (props) => {
    return props.children;
};
fragment.Fragment = Fragment;

var __rest$2 = (commonjsGlobal && commonjsGlobal.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
Object.defineProperty(link, "__esModule", { value: true });
link.Link = void 0;
const component_js_1$3 = component;
const helmet_js_1$1 = helmet;
const core_js_1$7 = core;
const fragment_js_1$1 = fragment;
/**
 * A simple Link component
 * Add <Link prefetch ..., to prefetch the html document
 * Add <Link prefetch="hover" ..., to prefetch the html document on hovering over the link element.
 */
class Link extends component_js_1$3.Component {
    prefetchOnHover() {
        this.elements[0].addEventListener('mouseover', () => this.addPrefetch(), { once: true });
    }
    prefetchOnVisible() {
        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    observer.disconnect();
                    this.addPrefetch();
                }
            });
        }, { threshold: [0, 1] });
        observer.observe(this.elements[0]);
    }
    addPrefetch() {
        let doesAlreadyExist = false;
        // check if it is already on the dom
        const links = document.getElementsByTagName('link');
        for (let i = 0; i < links.length; i++) {
            // if it is not already on the dom, add it
            if (links[i].getAttribute('rel') === 'prefetch' && links[i].getAttribute('href') === this.props.href) {
                doesAlreadyExist = true;
            }
        }
        if (!doesAlreadyExist) {
            const prefetch = (0, core_js_1$7.h)('link', { rel: 'prefetch', href: this.props.href, as: 'document' });
            document.head.appendChild(prefetch);
        }
    }
    didMount() {
        const { href, prefetch, delay = 0, back = false } = this.props;
        if (back)
            this.elements[0].addEventListener('click', (e) => {
                e.preventDefault();
                const target = e.target;
                if (target.href === document.referrer)
                    window.history.back();
                else
                    window.location.href = target.href;
            });
        if (delay > 0)
            this.elements[0].addEventListener('click', (e) => {
                e.preventDefault();
                setTimeout(() => (window.location.href = href), delay);
            });
        if (prefetch) {
            if (prefetch === 'hover')
                this.prefetchOnHover();
            else if (prefetch === 'visible')
                this.prefetchOnVisible();
            else
                this.addPrefetch();
        }
    }
    render() {
        // separate children and prefetch from props
        const _a = this.props, { children, prefetch, back, ref } = _a, rest = __rest$2(_a, ["children", "prefetch", "back", "ref"]);
        // some warning messages
        if (!this.props.href)
            console.warn('Please add "href" to <Link>');
        if (children.length !== 1)
            console.warn('Please add ONE child to <Link> (<Link>child</Link>)');
        const a = (0, core_js_1$7.h)('a', Object.assign({}, rest), ...children);
        // if ssr
        if (prefetch === true && !(typeof window !== 'undefined' && window.document)) {
            // <link rel="prefetch" href="/index.html" as="document"></link>
            const link = (0, core_js_1$7.h)('link', { rel: 'prefetch', href: this.props.href, as: 'document' });
            const helmet = (0, core_js_1$7.h)(helmet_js_1$1.Helmet, null, link);
            return (0, core_js_1$7.h)(fragment_js_1$1.Fragment, null, [helmet, a]);
        }
        // if not ssr
        else {
            return a;
        }
    }
}
link.Link = Link;

var router = {};

(function (exports) {
	// inspired by https://codesandbox.io/s/build-own-react-router-v4-mpslz
	var __rest = (commonjsGlobal && commonjsGlobal.__rest) || function (s, e) {
	    var t = {};
	    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
	        t[p] = s[p];
	    if (s != null && typeof Object.getOwnPropertySymbols === "function")
	        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
	            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
	                t[p[i]] = s[p[i]];
	        }
	    return t;
	};
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.parseParamsFromPath = exports.Listener = exports.Link = exports.to = exports.Route = exports.Routes = exports.Switch = exports.matchPath = void 0;
	const component_js_1 = component;
	const core_js_1 = core;
	const instances = [];
	const register = (comp) => instances.push(comp);
	const unregister = (comp) => instances.splice(instances.indexOf(comp), 1);
	const historyPush = (path) => {
	    window.history.pushState({}, '', path);
	    instances.forEach(instance => instance.handleChanges());
	    window.dispatchEvent(new Event('pushstate'));
	};
	const historyReplace = (path) => {
	    window.history.replaceState({}, '', path);
	    instances.forEach(instance => instance.handleChanges());
	    window.dispatchEvent(new Event('replacestate'));
	};
	const matchPath = (pathname, options) => {
	    const { exact = false, regex } = options;
	    let { path } = options;
	    if (!path) {
	        return {
	            path: null,
	            url: pathname,
	            isExact: true,
	            params: {}
	        };
	    }
	    let match;
	    let params = {};
	    // path with params
	    if (path.includes('/:')) {
	        const pathArr = path.split('/');
	        const pathnameArr = pathname.split('/');
	        pathArr.forEach((p, i) => {
	            if (/^:/.test(p)) {
	                const key = p.slice(1);
	                const value = pathnameArr[i];
	                // if a regex is provided, check it it matches
	                if (regex && regex[key]) {
	                    const regexMatch = regex[key].test(value);
	                    if (!regexMatch)
	                        return null;
	                }
	                params = Object.assign(Object.assign({}, params), { [key]: value });
	                pathArr[i] = pathnameArr[i];
	            }
	        });
	        path = pathArr.join('/');
	    }
	    // catch all
	    if (path === '*')
	        match = [pathname];
	    // regular path
	    if (!match)
	        match = new RegExp(`^${path}`).exec(pathname);
	    if (!match)
	        return null;
	    const url = match[0];
	    const isExact = pathname === url;
	    if (exact && !isExact)
	        return null;
	    return {
	        path,
	        url,
	        isExact,
	        params
	    };
	};
	exports.matchPath = matchPath;
	class Switch extends component_js_1.Component {
	    constructor() {
	        super(...arguments);
	        this.index = 0;
	        this.path = '';
	        this.match = { index: -1, path: '' };
	    }
	    didMount() {
	        window.addEventListener('popstate', this.handleChanges.bind(this));
	        register(this);
	    }
	    didUnmount() {
	        window.removeEventListener('popstate', this.handleChanges.bind(this));
	        unregister(this);
	    }
	    handleChanges() {
	        this.findChild();
	        if (this.shouldUpdate())
	            this.update();
	    }
	    findChild() {
	        this.match = { index: -1, path: '' };
	        // flatten children
	        this.props.children = this.props.children.flat();
	        for (let i = 0; i < this.props.children.length; i++) {
	            const child = this.props.children[i];
	            const { path, exact, regex } = child.props;
	            const match = (0, exports.matchPath)((0, core_js_1.isSSR)() ? _nano.location.pathname : window.location.pathname, {
	                path,
	                exact,
	                regex
	            });
	            if (match) {
	                this.match.index = i;
	                this.match.path = path;
	                return;
	            }
	        }
	    }
	    shouldUpdate() {
	        return this.path !== this.match.path || this.index !== this.match.index;
	    }
	    render() {
	        this.findChild();
	        const child = this.props.children[this.match.index];
	        if (this.match.index === -1) {
	            this.path = '';
	            this.index = 0;
	        }
	        if (child) {
	            const { path } = child.props;
	            this.path = path;
	            this.index = this.match.index;
	            const el = (0, core_js_1._render)(child);
	            return (0, core_js_1.h)('div', {}, (0, core_js_1._render)(el));
	        }
	        else if (this.props.fallback) {
	            return (0, core_js_1.h)('div', {}, (0, core_js_1._render)(this.props.fallback));
	        }
	        else {
	            return (0, core_js_1.h)('div', {}, 'not found');
	        }
	    }
	}
	exports.Switch = Switch;
	// alias for <Switch />
	class Routes extends Switch {
	}
	exports.Routes = Routes;
	const Route = ({ path, regex, children }) => {
	    // lookup pathname and parameters
	    const pathname = (0, core_js_1.isSSR)() ? _nano.location.pathname : window.location.pathname;
	    const params = (0, exports.parseParamsFromPath)(path);
	    // pass the route as props to the children
	    children.forEach((child) => {
	        if (child.props)
	            child.props = Object.assign(Object.assign({}, child.props), { route: { path, regex, pathname, params } });
	    });
	    return children;
	};
	exports.Route = Route;
	const to = (to, replace = false) => {
	    replace ? historyReplace(to) : historyPush(to);
	};
	exports.to = to;
	const Link = (_a) => {
	    var { to, replace, children } = _a, rest = __rest(_a, ["to", "replace", "children"]);
	    const handleClick = (event) => {
	        event.preventDefault();
	        replace ? historyReplace(to) : historyPush(to);
	    };
	    return (0, core_js_1.h)('a', Object.assign({ href: to, onClick: (e) => handleClick(e) }, rest), children);
	};
	exports.Link = Link;
	class CListener {
	    constructor() {
	        this._listeners = new Map();
	        if ((0, core_js_1.isSSR)())
	            return;
	        this._route = window.location.pathname;
	        const event = () => {
	            const newRoute = window.location.pathname;
	            this._listeners.forEach(fnc => {
	                fnc(newRoute, this._route);
	            });
	            this._route = newRoute;
	        };
	        window.addEventListener('pushstate', event);
	        window.addEventListener('replacestate', event);
	    }
	    use() {
	        const id = Math.random().toString(36).substring(2);
	        return {
	            subscribe: (fnc) => {
	                this._listeners.set(id, fnc);
	            },
	            cancel: () => {
	                if (this._listeners.has(id))
	                    this._listeners.delete(id);
	            }
	        };
	    }
	}
	let listener;
	const Listener = () => {
	    if (!listener)
	        listener = new CListener();
	    return listener;
	};
	exports.Listener = Listener;
	/** Pass "this.props.route.path" to it. */
	const parseParamsFromPath = (path) => {
	    let params = {};
	    const _pathname = (0, core_js_1.isSSR)() ? _nano.location.pathname.split('/') : window.location.pathname.split('/');
	    path.split('/').forEach((p, i) => {
	        if (p.startsWith(':'))
	            params = Object.assign(Object.assign({}, params), { [p.slice(1)]: _pathname[i] });
	    });
	    return params;
	};
	exports.parseParamsFromPath = parseParamsFromPath;
	
} (router));

var suspense = {};

var __awaiter = (commonjsGlobal && commonjsGlobal.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __rest$1 = (commonjsGlobal && commonjsGlobal.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
Object.defineProperty(suspense, "__esModule", { value: true });
suspense.Suspense = void 0;
const component_js_1$2 = component;
const core_js_1$6 = core;
class Suspense extends component_js_1$2.Component {
    constructor(props) {
        super(props);
        this.ready = false;
        // get props promises in ...rest
        const _a = this.props, rest = __rest$1(_a, ["children", "fallback", "cache"]);
        // stringify ...rest
        const str = JSON.stringify(rest, function (_key, val) {
            if (typeof val === 'function')
                return `${val}`; // implicitly `toString` it
            return val;
        });
        // create unique id based on ...rest
        this.id = (0, core_js_1$6.strToHash)(JSON.stringify(str));
    }
    didMount() {
        return __awaiter(this, void 0, void 0, function* () {
            // get props promises in ...rest
            const _a = this.props, { children, fallback, cache = false } = _a, rest = __rest$1(_a, ["children", "fallback", "cache"]);
            // set initial state to []
            if (cache)
                this.initState = {};
            // check if we already cached the results in this.state
            if (this.loadFromCache(cache))
                return;
            // resolve the promises
            const promises = Object.values(rest).map(p => p());
            const resolved = yield Promise.all(promises);
            // prepare data
            const data = this.prepareData(rest, resolved, cache);
            // add data to children
            this.addDataToChildren(data);
            // update the component
            this.ready = true;
            this.update();
        });
    }
    ssr() {
        // get props promises in ...rest
        const _a = this.props, rest = __rest$1(_a, ["children", "fallback", "cache"]);
        // execute the functions
        const functions = Object.values(rest).map(p => p());
        // prepare data
        const data = this.prepareData(rest, functions, false);
        // add data to children
        this.addDataToChildren(data);
    }
    loadFromCache(cache) {
        const hasCachedProps = this.state && cache && Object.keys(this.state).length > 0;
        if (hasCachedProps) {
            this.addDataToChildren(this.state);
            this.ready = true;
        }
        return hasCachedProps;
    }
    prepareData(rest, fnc, cache) {
        const data = Object.keys(rest).reduce((obj, item, index) => {
            if (cache)
                this.state = Object.assign(Object.assign({}, this.state), { [item]: fnc[index] });
            return Object.assign(Object.assign({}, obj), { [item]: fnc[index] });
        }, {});
        return data;
    }
    addDataToChildren(data) {
        // add data as props to children
        this.props.children.forEach((child) => {
            if (child.props)
                child.props = Object.assign(Object.assign({}, child.props), data);
        });
    }
    render() {
        if (!(0, core_js_1$6.isSSR)()) {
            const { cache = false } = this.props;
            this.loadFromCache(cache);
            return !this.ready ? this.props.fallback : this.props.children;
        }
        else {
            this.ssr();
            return this.props.children;
        }
    }
}
suspense.Suspense = Suspense;

var visible = {};

Object.defineProperty(visible, "__esModule", { value: true });
visible.Visible = void 0;
const core_js_1$5 = core;
const component_js_1$1 = component;
class Visible extends component_js_1$1.Component {
    constructor() {
        super(...arguments);
        this.isVisible = false;
    }
    didMount() {
        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    observer.disconnect();
                    this.isVisible = true;
                    this.update();
                }
            });
        }, { threshold: [0, 1] });
        observer.observe(this.elements[0]);
    }
    render() {
        if (!this.isVisible) {
            return (0, core_js_1$5.h)('div', { 'data-visible': false, visibility: 'hidden' });
        }
        else {
            if (this.props.onVisible)
                this.props.onVisible();
            return (0, core_js_1$5.render)(this.props.component || this.props.children[0]);
        }
    }
}
visible.Visible = Visible;

(function (exports) {
	var __createBinding = (commonjsGlobal && commonjsGlobal.__createBinding) || (Object.create ? (function(o, m, k, k2) {
	    if (k2 === undefined) k2 = k;
	    var desc = Object.getOwnPropertyDescriptor(m, k);
	    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
	      desc = { enumerable: true, get: function() { return m[k]; } };
	    }
	    Object.defineProperty(o, k2, desc);
	}) : (function(o, m, k, k2) {
	    if (k2 === undefined) k2 = k;
	    o[k2] = m[k];
	}));
	var __setModuleDefault = (commonjsGlobal && commonjsGlobal.__setModuleDefault) || (Object.create ? (function(o, v) {
	    Object.defineProperty(o, "default", { enumerable: true, value: v });
	}) : function(o, v) {
	    o["default"] = v;
	});
	var __importStar = (commonjsGlobal && commonjsGlobal.__importStar) || function (mod) {
	    if (mod && mod.__esModule) return mod;
	    var result = {};
	    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
	    __setModuleDefault(result, mod);
	    return result;
	};
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.Visible = exports.Suspense = exports.Router = exports.Link = exports.Img = exports.Helmet = void 0;
	var helmet_js_1 = helmet;
	Object.defineProperty(exports, "Helmet", { enumerable: true, get: function () { return helmet_js_1.Helmet; } });
	var img_js_1 = img;
	Object.defineProperty(exports, "Img", { enumerable: true, get: function () { return img_js_1.Img; } });
	var link_js_1 = link;
	Object.defineProperty(exports, "Link", { enumerable: true, get: function () { return link_js_1.Link; } });
	exports.Router = __importStar(router);
	var suspense_js_1 = suspense;
	Object.defineProperty(exports, "Suspense", { enumerable: true, get: function () { return suspense_js_1.Suspense; } });
	var visible_js_1 = visible;
	Object.defineProperty(exports, "Visible", { enumerable: true, get: function () { return visible_js_1.Visible; } });
	
} (components));

var ssr = {};

var regexDom = {};

Object.defineProperty(regexDom, "__esModule", { value: true });
regexDom.documentSSR = regexDom.DocumentSSR = regexDom.HTMLElementSSR = void 0;
const helpers_js_1 = helpers;
class HTMLElementSSR {
    constructor(tag) {
        this.isSelfClosing = false;
        this.nodeType = null;
        this.tagName = tag;
        const selfClosing = [
            'area',
            'base',
            'br',
            'col',
            'embed',
            'hr',
            'img',
            'input',
            'link',
            'meta',
            'param',
            'source',
            'track',
            'wbr'
        ];
        this.nodeType = 1;
        if (selfClosing.indexOf(tag) >= 0) {
            this._ssr = `<${tag} />`;
            this.isSelfClosing = true;
        }
        else {
            this._ssr = `<${tag}></${tag}>`;
        }
    }
    get outerHTML() {
        return this.toString();
    }
    get innerHTML() {
        return this.innerText;
    }
    set innerHTML(text) {
        this.innerText = text;
    }
    get innerText() {
        var _a;
        const reg = /(^<[^>]+>)(.+)?(<\/[a-z0-9]+>$|\/>$)/gm;
        return ((_a = reg.exec(this._ssr)) === null || _a === void 0 ? void 0 : _a[2]) || '';
    }
    set innerText(text) {
        const reg = /(^<[^>]+>)(.+)?(<\/[a-z0-9]+>$|\/>$)/gm;
        const replacer = (_match, p1, _p2, p3) => [p1, text, p3].join('');
        this._ssr = this._ssr.replace(reg, replacer);
    }
    getAttribute(_name) {
        return null;
    }
    get classList() {
        const element = this._ssr;
        const classesRegex = /^<\w+.+(\sclass=")([^"]+)"/gm;
        return {
            add: (name) => {
                this.setAttribute('class', name);
            },
            entries: {
                get length() {
                    const classes = classesRegex.exec(element);
                    if (classes && classes[2])
                        return classes[2].split(' ').length;
                    return 0;
                }
            }
        };
    }
    toString() {
        return this._ssr;
    }
    setAttributeNS(_namespace, name, value) {
        this.setAttribute(name, value);
    }
    setAttribute(name, value) {
        const replacer1 = (_match, p1, p2) => `${p1}${(0, helpers_js_1.escapeHtml)(name)}="${(0, helpers_js_1.escapeHtml)(value)}" ${p2}`;
        const replacer2 = (_match, p1, p2) => `${p1} ${(0, helpers_js_1.escapeHtml)(name)}="${(0, helpers_js_1.escapeHtml)(value)}"${p2}`;
        if (this.isSelfClosing)
            this._ssr = this._ssr.replace(/(^<[a-z0-9]+ )(.+)/gm, replacer1);
        else
            this._ssr = this._ssr.replace(/(^<[^>]+)(.+)/gm, replacer2);
    }
    append(child) {
        this.appendChild(child);
    }
    appendChild(child) {
        const index = this._ssr.lastIndexOf('</');
        this._ssr = this._ssr.substring(0, index) + child + this._ssr.substring(index);
    }
    get children() {
        const reg = /<([a-z0-9]+)((?!<\/\1).)*<\/\1>/gms;
        const array = [];
        let match;
        while ((match = reg.exec(this.innerHTML)) !== null) {
            array.push(match[0].replace(/[\s]+/gm, ' '));
        }
        return array;
    }
    addEventListener(_type, _listener, _options) { }
}
regexDom.HTMLElementSSR = HTMLElementSSR;
class DocumentSSR {
    constructor() {
        this.body = this.createElement('body');
        this.head = this.createElement('head');
    }
    createElement(tag) {
        return new HTMLElementSSR(tag);
    }
    createElementNS(_URI, tag) {
        return this.createElement(tag);
    }
    createTextNode(text) {
        return (0, helpers_js_1.escapeHtml)(text);
    }
    querySelector(_query) {
        return undefined;
    }
}
regexDom.DocumentSSR = DocumentSSR;
const documentSSR = () => {
    return new DocumentSSR();
};
regexDom.documentSSR = documentSSR;

(function (exports) {
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.clearState = exports.renderSSR = exports.initSSR = void 0;
	const core_js_1 = core;
	const regexDom_js_1 = regexDom;
	const state_js_1 = state;
	const helpers_js_1 = helpers;
	// functions that should only be available on the server-side
	const ssrTricks = {
	    isWebComponent: (tagNameOrComponent) => {
	        return (typeof tagNameOrComponent === 'string' &&
	            tagNameOrComponent.includes('-') &&
	            _nano.customElements.has(tagNameOrComponent));
	    },
	    renderWebComponent: (tagNameOrComponent, props, children, _render) => {
	        const customElement = _nano.customElements.get(tagNameOrComponent);
	        const component = _render({ component: customElement, props: Object.assign(Object.assign({}, props), { children: children }) });
	        // get the html tag and the innerText from string
	        // match[1]: HTMLTag
	        // match[2]: innerText
	        const match = component.toString().match(/^<(?<tag>[a-z]+)>(.*)<\/\k<tag>>$/);
	        if (match) {
	            const element = document.createElement(match[1]);
	            element.innerText = match[2];
	            // eslint-disable-next-line no-inner-declarations
	            function replacer(match, p1, _offset, _string) {
	                return match.replace(p1, '');
	            }
	            // remove events like onClick from DOM
	            element.innerText = element.innerText.replace(/<\w+[^>]*(\s(on\w*)="[^"]*")/gm, replacer);
	            return element;
	        }
	        else {
	            return null;
	        }
	    }
	};
	const initGlobalVar = () => {
	    const isSSR = (0, helpers_js_1.detectSSR)() === true ? true : undefined;
	    const location = { pathname: '/' };
	    const document = isSSR ? (0, regexDom_js_1.documentSSR)() : window.document;
	    globalThis._nano = { isSSR, location, document, customElements: new Map(), ssrTricks };
	};
	initGlobalVar();
	const initSSR = (pathname = '/') => {
	    _nano.location = { pathname };
	    globalThis.document = _nano.document = (0, core_js_1.isSSR)() ? (0, regexDom_js_1.documentSSR)() : window.document;
	};
	exports.initSSR = initSSR;
	const renderSSR = (component, options = {}) => {
	    const { pathname, clearState = true } = options;
	    (0, exports.initSSR)(pathname);
	    if (clearState)
	        state_js_1._state.clear();
	    const tmp = (0, core_js_1.render)(component, null, true);
	    if (Array.isArray(tmp))
	        return tmp.join('');
	    else
	        return Array.from(tmp).join('');
	};
	exports.renderSSR = renderSSR;
	const clearState = () => {
	    state_js_1._state.clear();
	};
	exports.clearState = clearState;
	
} (ssr));

var jsx$1 = {};

var htm$1 = {};

var htm = {};

var constants = {};

Object.defineProperty(constants, "__esModule", { value: true });
constants.MINI = void 0;
constants.MINI = false;

var build = {};

(function (exports) {
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.build = exports.evaluate = exports.treeify = void 0;
	const constants_js_1 = constants;
	const MODE_SLASH = 0;
	const MODE_TEXT = 1;
	const MODE_WHITESPACE = 2;
	const MODE_TAGNAME = 3;
	const MODE_COMMENT = 4;
	const MODE_PROP_SET = 5;
	const MODE_PROP_APPEND = 6;
	const CHILD_APPEND = 0;
	const CHILD_RECURSE = 2;
	const TAG_SET = 3;
	const PROPS_ASSIGN = 4;
	const PROP_SET = MODE_PROP_SET;
	const PROP_APPEND = MODE_PROP_APPEND;
	// Turn a result of a build(...) call into a tree that is more
	// convenient to analyze and transform (e.g. Babel plugins).
	// For example:
	// 	treeify(
	//		build'<div href="1${a}" ...${b}><${x} /></div>`,
	//		[X, Y, Z]
	//	)
	// returns:
	// 	{
	// 		tag: 'div',
	//		props: [ { href: ["1", X] },	Y ],
	// 		children: [ { tag: Z, props: [], children: [] } ]
	// 	}
	const treeify = (built, fields) => {
	    const _treeify = (built) => {
	        let tag = '';
	        let currentProps = null;
	        const props = [];
	        const children = [];
	        for (let i = 1; i < built.length; i++) {
	            const type = built[i++];
	            const value = built[i] ? fields[built[i++] - 1] : built[++i];
	            if (type === TAG_SET) {
	                tag = value;
	            }
	            else if (type === PROPS_ASSIGN) {
	                props.push(value);
	                currentProps = null;
	            }
	            else if (type === PROP_SET) {
	                if (!currentProps) {
	                    currentProps = Object.create(null);
	                    props.push(currentProps);
	                }
	                currentProps[built[++i]] = [value];
	            }
	            else if (type === PROP_APPEND) {
	                currentProps[built[++i]].push(value);
	            }
	            else if (type === CHILD_RECURSE) {
	                children.push(_treeify(value));
	            }
	            else if (type === CHILD_APPEND) {
	                children.push(value);
	            }
	        }
	        return { tag, props, children };
	    };
	    const { children } = _treeify(built);
	    return children.length > 1 ? children : children[0];
	};
	exports.treeify = treeify;
	const evaluate = (h, built, fields, args) => {
	    let tmp;
	    // `build()` used the first element of the operation list as
	    // temporary workspace. Now that `build()` is done we can use
	    // that space to track whether the current element is "dynamic"
	    // (i.e. it or any of its descendants depend on dynamic values).
	    built[0] = 0;
	    for (let i = 1; i < built.length; i++) {
	        const type = built[i++];
	        // Set `built[0]`'s appropriate bits if this element depends on a dynamic value.
	        const value = built[i] ? ((built[0] |= type ? 1 : 2), fields[built[i++]]) : built[++i];
	        if (type === TAG_SET) {
	            args[0] = value;
	        }
	        else if (type === PROPS_ASSIGN) {
	            args[1] = Object.assign(args[1] || {}, value);
	        }
	        else if (type === PROP_SET) {
	            (args[1] = args[1] || {})[built[++i]] = value;
	        }
	        else if (type === PROP_APPEND) {
	            args[1][built[++i]] += `${value}`;
	        }
	        else if (type) {
	            // type === CHILD_RECURSE
	            // Set the operation list (including the staticness bits) as
	            // `this` for the `h` call.
	            tmp = h.apply(value, (0, exports.evaluate)(h, value, fields, ['', null]));
	            args.push(tmp);
	            if (value[0]) {
	                // Set the 2nd lowest bit it the child element is dynamic.
	                built[0] |= 2;
	            }
	            else {
	                // Rewrite the operation list in-place if the child element is static.
	                // The currently evaluated piece `CHILD_RECURSE, 0, [...]` becomes
	                // `CHILD_APPEND, 0, tmp`.
	                // Essentially the operation list gets optimized for potential future
	                // re-evaluations.
	                built[i - 2] = CHILD_APPEND;
	                built[i] = tmp;
	            }
	        }
	        else {
	            // type === CHILD_APPEND
	            args.push(value);
	        }
	    }
	    return args;
	};
	exports.evaluate = evaluate;
	const build = function (statics, ...rest) {
	    const fields = [statics, ...rest];
	    // @ts-ignore
	    const h = this;
	    let mode = MODE_TEXT;
	    let buffer = '';
	    let quote = '';
	    let current = [0];
	    let char;
	    let propName;
	    const commit = (field) => {
	        if (mode === MODE_TEXT && (field || (buffer = buffer.replace(/^\s*\n\s*|\s*\n\s*$/g, '')))) {
	            if (constants_js_1.MINI) {
	                current.push(field ? fields[field] : buffer);
	            }
	            else {
	                current.push(CHILD_APPEND, field, buffer);
	            }
	        }
	        else if (mode === MODE_TAGNAME && (field || buffer)) {
	            if (constants_js_1.MINI) {
	                current[1] = field ? fields[field] : buffer;
	            }
	            else {
	                current.push(TAG_SET, field, buffer);
	            }
	            mode = MODE_WHITESPACE;
	        }
	        else if (mode === MODE_WHITESPACE && buffer === '...' && field) {
	            if (constants_js_1.MINI) {
	                current[2] = Object.assign(current[2] || {}, fields[field]);
	            }
	            else {
	                current.push(PROPS_ASSIGN, field, 0);
	            }
	        }
	        else if (mode === MODE_WHITESPACE && buffer && !field) {
	            if (constants_js_1.MINI) {
	                (current[2] = current[2] || {})[buffer] = true;
	            }
	            else {
	                current.push(PROP_SET, 0, true, buffer);
	            }
	        }
	        else if (mode >= MODE_PROP_SET) {
	            if (constants_js_1.MINI) {
	                if (mode === MODE_PROP_SET) {
	                    (current[2] = current[2] || {})[propName] = field
	                        ? buffer
	                            ? buffer + fields[field]
	                            : fields[field]
	                        : buffer;
	                    mode = MODE_PROP_APPEND;
	                }
	                else if (field || buffer) {
	                    current[2][propName] += field ? buffer + fields[field] : buffer;
	                }
	            }
	            else {
	                if (buffer || (!field && mode === MODE_PROP_SET)) {
	                    current.push(mode, 0, buffer, propName);
	                    mode = MODE_PROP_APPEND;
	                }
	                if (field) {
	                    current.push(mode, field, 0, propName);
	                    mode = MODE_PROP_APPEND;
	                }
	            }
	        }
	        buffer = '';
	    };
	    for (let i = 0; i < statics.length; i++) {
	        if (i) {
	            if (mode === MODE_TEXT) {
	                commit();
	            }
	            commit(i);
	        }
	        for (let j = 0; j < statics[i].length; j++) {
	            char = statics[i][j];
	            if (mode === MODE_TEXT) {
	                if (char === '<') {
	                    // commit buffer
	                    commit();
	                    if (constants_js_1.MINI) {
	                        current = [current, '', null];
	                    }
	                    else {
	                        current = [current];
	                    }
	                    mode = MODE_TAGNAME;
	                }
	                else {
	                    buffer += char;
	                }
	            }
	            else if (mode === MODE_COMMENT) {
	                // Ignore everything until the last three characters are '-', '-' and '>'
	                if (buffer === '--' && char === '>') {
	                    mode = MODE_TEXT;
	                    buffer = '';
	                }
	                else {
	                    buffer = char + buffer[0];
	                }
	            }
	            else if (quote) {
	                if (char === quote) {
	                    quote = '';
	                }
	                else {
	                    buffer += char;
	                }
	            }
	            else if (char === '"' || char === "'") {
	                quote = char;
	            }
	            else if (char === '>') {
	                commit();
	                mode = MODE_TEXT;
	            }
	            else if (!mode) ;
	            else if (char === '=') {
	                mode = MODE_PROP_SET;
	                propName = buffer;
	                buffer = '';
	            }
	            else if (char === '/' && (mode < MODE_PROP_SET || statics[i][j + 1] === '>')) {
	                commit();
	                if (mode === MODE_TAGNAME) {
	                    current = current[0];
	                }
	                mode = current;
	                if (constants_js_1.MINI) {
	                    (current = current[0]).push(h(...mode.slice(1)));
	                }
	                else {
	                    (current = current[0]).push(CHILD_RECURSE, 0, mode);
	                }
	                mode = MODE_SLASH;
	            }
	            else if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
	                // <a disabled>
	                commit();
	                mode = MODE_WHITESPACE;
	            }
	            else {
	                buffer += char;
	            }
	            if (mode === MODE_TAGNAME && buffer === '!--') {
	                mode = MODE_COMMENT;
	                current = current[0];
	            }
	        }
	    }
	    commit();
	    if (constants_js_1.MINI) {
	        return current.length > 2 ? current.slice(1) : current[1];
	    }
	    return current;
	};
	exports.build = build;
	
} (build));

/**
 * Copyright 2018 Google Inc. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(htm, "__esModule", { value: true });
const constants_js_1 = constants;
const build_js_1 = build;
const CACHES = new Map();
const regular = function (statics) {
    let tmp = CACHES.get(this);
    if (!tmp) {
        tmp = new Map();
        CACHES.set(this, tmp);
    }
    tmp = (0, build_js_1.evaluate)(this, tmp.get(statics) || (tmp.set(statics, (tmp = (0, build_js_1.build)(statics))), tmp), arguments, []);
    return tmp.length > 1 ? tmp : tmp[0];
};
// export as htm
htm.default = constants_js_1.MINI ? build_js_1.build : regular;

var __importDefault$1 = (commonjsGlobal && commonjsGlobal.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(htm$1, "__esModule", { value: true });
const index_js_1 = __importDefault$1(htm);
htm$1.default = index_js_1.default;

var __importDefault = (commonjsGlobal && commonjsGlobal.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(jsx$1, "__esModule", { value: true });
jsx$1.jsx = void 0;
const core_js_1$4 = core;
const htm_js_1 = __importDefault(htm$1);
const jsx = htm_js_1.default.bind(core_js_1$4.h);
jsx$1.jsx = jsx;

var lazy = {};

Object.defineProperty(lazy, "__esModule", { value: true });
lazy.hydrateLazy = void 0;
const core_js_1$3 = core;
const visible_js_1 = visible;
const hydrateLazy = (component, parent = null, removeChildNodes = true) => {
    const c = (0, core_js_1$3.h)(visible_js_1.Visible, null, component);
    return (0, core_js_1$3.hydrate)(c, parent, removeChildNodes);
};
lazy.hydrateLazy = hydrateLazy;

var store = {};

Object.defineProperty(store, "__esModule", { value: true });
store.Store = void 0;
const core_js_1$2 = core;
class Store {
    /**
     * Create your own Store.
     * @param defaultState Pass the initial State.
     * @param name The name of the Store (only required if you persist the state in localStorage or sessionStorage).
     * @param storage Pass 'memory', 'local' or 'session'.
     */
    constructor(defaultState, name = '', storage = 'memory') {
        this._listeners = new Map();
        if ((0, core_js_1$2.isSSR)())
            storage = 'memory';
        this._id = name;
        this._storage = storage;
        this._state = this._prevState = defaultState;
        if (storage === 'memory' || !storage)
            return;
        const Storage = storage === 'local' ? localStorage : sessionStorage;
        // get/set initial state of Storage
        const item = Storage.getItem(this._id);
        if (item) {
            this._state = this._prevState = JSON.parse(item);
        }
        else
            Storage.setItem(this._id, JSON.stringify(defaultState));
    }
    persist(newState) {
        if (this._storage === 'memory')
            return;
        const Storage = this._storage === 'local' ? localStorage : sessionStorage;
        Storage.setItem(this._id, JSON.stringify(newState));
    }
    /** Clears the state of the whole store. */
    clear() {
        // @ts-ignore
        this._state = this._prevState = undefined;
        if (this._storage === 'local')
            localStorage.removeItem(this._id);
        else if (this._storage === 'session')
            sessionStorage.removeItem(this._id);
    }
    setState(newState) {
        this.state = newState;
    }
    set state(newState) {
        this._prevState = this._state;
        this._state = newState;
        this.persist(newState);
        this._listeners.forEach(fnc => {
            fnc(this._state, this._prevState);
        });
    }
    get state() {
        return this._state;
    }
    use() {
        const id = Math.random().toString(36).substring(2, 9);
        const _this = this;
        return {
            get state() {
                return _this.state;
            },
            setState: (newState) => {
                this.state = newState;
            },
            subscribe: (fnc) => {
                this._listeners.set(id, fnc);
            },
            cancel: () => {
                if (this._listeners.has(id))
                    this._listeners.delete(id);
            }
        };
    }
}
store.Store = Store;

var context = {};

Object.defineProperty(context, "__esModule", { value: true });
context.useContext = context.createContext = void 0;
const createContext = (ctx) => {
    let _ctx = ctx;
    return {
        Provider: (props) => {
            if (props.value)
                _ctx = props.value;
            return props.children;
        },
        Consumer: (props) => {
            return { component: props.children[0](_ctx), props: Object.assign(Object.assign({}, props), { context: _ctx }) };
        },
        get: () => _ctx,
        set: (ctx) => (_ctx = ctx)
    };
};
context.createContext = createContext;
const useContext = (ctx) => {
    const _ctx = ctx;
    if (_ctx && typeof _ctx.get === 'function') {
        return _ctx.get();
    }
};
context.useContext = useContext;

var withStyles$1 = {};

var __rest = (commonjsGlobal && commonjsGlobal.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
Object.defineProperty(withStyles$1, "__esModule", { value: true });
withStyles$1.withStyles = void 0;
const core_js_1$1 = core;
const component_js_1 = component;
const fragment_js_1 = fragment;
const helmet_js_1 = helmet;
const withStyles = (...styles) => (WrappedComponent) => {
    return class extends component_js_1.Component {
        render() {
            const _a = this.props, { children } = _a, rest = __rest(_a, ["children"]);
            const helmets = [];
            styles.forEach(style => {
                var _a;
                if (typeof style === 'string') {
                    helmets.push((0, core_js_1$1.h)(helmet_js_1.Helmet, null, (0, core_js_1$1.h)('style', null, style)));
                }
                else if (typeof style === 'function') {
                    const _style = style();
                    if (typeof _style === 'string') {
                        helmets.push((0, core_js_1$1.h)(helmet_js_1.Helmet, null, (0, core_js_1$1.h)('style', null, _style)));
                    }
                }
                else if (typeof style === 'object') {
                    const _style = (_a = style.toString) === null || _a === void 0 ? void 0 : _a.call(style);
                    if (typeof _style === 'string') {
                        helmets.push((0, core_js_1$1.h)(helmet_js_1.Helmet, null, (0, core_js_1$1.h)('style', null, _style)));
                    }
                }
            });
            const component = children && children.length > 0
                ? (0, core_js_1$1.h)(WrappedComponent, Object.assign({}, rest), children)
                : (0, core_js_1$1.h)(WrappedComponent, Object.assign({}, this.props));
            return (0, core_js_1$1.h)(fragment_js_1.Fragment, null, ...helmets, component);
        }
    };
};
withStyles$1.withStyles = withStyles;

var customElementsMode = {};

Object.defineProperty(customElementsMode, "__esModule", { value: true });
customElementsMode.defineAsCustomElements = void 0;
const core_js_1 = core;
const defineAsCustomElementsSSR = (component, componentName, _publicProps = [], _options = {}) => {
    if (!/^[a-zA-Z0-9]+-[a-zA-Z0-9]+$/.test(componentName))
        console.log(`Error: WebComponent name "${componentName}" is invalid.`);
    else
        _nano.customElements.set(componentName, component);
};
const defineAsCustomElements = function (component, componentName, publicProps, shadow) {
    if ((0, core_js_1.isSSR)()) {
        defineAsCustomElementsSSR(component, componentName, publicProps);
        return;
    }
    customElements.define(componentName, class extends HTMLElement {
        constructor() {
            super();
            if (shadow) {
                this.attachShadow(shadow);
                this.$root = this.shadowRoot;
            }
            else {
                this.$root = this;
            }
            let ref;
            const el = this.buildEl((0, core_js_1._render)({
                component,
                props: {
                    ref: (r) => (ref = r),
                    children: Array.from(this.children).map(c => (0, core_js_1.render)(c))
                }
            }));
            // ------------------------------ first render
            this.component = ref;
            this.isFunctionalComponent = !component.isClass;
            this.functionalComponentsProps = {};
            this.appendEl(el);
            // ------------------------------------------
            if (!this.isFunctionalComponent) {
                this.component.updatePropsValue = (name, value) => {
                    // @ts-ignore
                    if (!this.component.props)
                        this.component.props = {};
                    this.component.props[name] = value;
                    this.component[name] = value;
                };
            }
        }
        static get observedAttributes() {
            return publicProps;
        }
        buildEl(contents) {
            // because nano-jsx update needs parentElement, we need
            // to wrap the element in a div when using shadow mode
            return (0, core_js_1.h)(this.shadowRoot ? 'div' : 'template', null, contents);
        }
        appendEl(el) {
            if (this.shadowRoot) {
                // el.dataset.wcRoot = true
                this.$root.append(el);
            }
            else {
                this.$root.append(...el.childNodes);
            }
        }
        removeChildren() {
            var _a;
            if (this.$root) {
                const children = Array.from((_a = this.$root) === null || _a === void 0 ? void 0 : _a.children) || [];
                for (const el of children) {
                    el.remove();
                }
            }
        }
        attributeChangedCallback(name, _, newValue) {
            if (!this.isFunctionalComponent) {
                this.component.updatePropsValue(name, newValue);
                this.component.update();
            }
            else {
                this.removeChildren();
                this.functionalComponentsProps[name] = newValue;
                const el = this.buildEl((0, core_js_1._render)({
                    component,
                    props: Object.assign({ children: [], ref: (r) => (this.component = r) }, this.functionalComponentsProps)
                }));
                this.appendEl(el);
            }
        }
    });
};
customElementsMode.defineAsCustomElements = defineAsCustomElements;

(function (exports) {
	var __createBinding = (commonjsGlobal && commonjsGlobal.__createBinding) || (Object.create ? (function(o, m, k, k2) {
	    if (k2 === undefined) k2 = k;
	    var desc = Object.getOwnPropertyDescriptor(m, k);
	    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
	      desc = { enumerable: true, get: function() { return m[k]; } };
	    }
	    Object.defineProperty(o, k2, desc);
	}) : (function(o, m, k, k2) {
	    if (k2 === undefined) k2 = k;
	    o[k2] = m[k];
	}));
	var __exportStar = (commonjsGlobal && commonjsGlobal.__exportStar) || function(m, exports) {
	    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
	};
	Object.defineProperty(exports, "__esModule", { value: true });
	exports.VERSION = exports.printVersion = exports.defineAsCustomElements = exports.withStyles = exports.useContext = exports.createContext = exports.Store = exports.Fragment = exports.renderSSR = exports.task = exports.nodeToString = exports.hydrateLazy = exports.jsx = exports.isSSR = exports.Component = exports.tick = exports.hydrate = exports.render = exports.h = void 0;
	// core
	var core_js_1 = core;
	Object.defineProperty(exports, "h", { enumerable: true, get: function () { return core_js_1.h; } });
	Object.defineProperty(exports, "render", { enumerable: true, get: function () { return core_js_1.render; } });
	Object.defineProperty(exports, "hydrate", { enumerable: true, get: function () { return core_js_1.hydrate; } });
	Object.defineProperty(exports, "tick", { enumerable: true, get: function () { return core_js_1.tick; } });
	// component
	var component_js_1 = component;
	Object.defineProperty(exports, "Component", { enumerable: true, get: function () { return component_js_1.Component; } });
	// built-in Components
	__exportStar(components, exports);
	// export some defaults (Nano)
	const core_js_2 = core;
	Object.defineProperty(exports, "isSSR", { enumerable: true, get: function () { return core_js_2.isSSR; } });
	const ssr_js_1 = ssr;
	exports.default = { h: core_js_2.h, render: core_js_2.render, hydrate: core_js_2.hydrate, renderSSR: ssr_js_1.renderSSR, isSSR: core_js_2.isSSR };
	var jsx_js_1 = jsx$1;
	Object.defineProperty(exports, "jsx", { enumerable: true, get: function () { return jsx_js_1.jsx; } });
	var lazy_js_1 = lazy;
	Object.defineProperty(exports, "hydrateLazy", { enumerable: true, get: function () { return lazy_js_1.hydrateLazy; } });
	var helpers_js_1 = helpers;
	Object.defineProperty(exports, "nodeToString", { enumerable: true, get: function () { return helpers_js_1.nodeToString; } });
	Object.defineProperty(exports, "task", { enumerable: true, get: function () { return helpers_js_1.task; } });
	var ssr_js_2 = ssr;
	Object.defineProperty(exports, "renderSSR", { enumerable: true, get: function () { return ssr_js_2.renderSSR; } });
	var fragment_js_1 = fragment;
	Object.defineProperty(exports, "Fragment", { enumerable: true, get: function () { return fragment_js_1.Fragment; } });
	var store_js_1 = store;
	Object.defineProperty(exports, "Store", { enumerable: true, get: function () { return store_js_1.Store; } });
	var context_js_1 = context;
	Object.defineProperty(exports, "createContext", { enumerable: true, get: function () { return context_js_1.createContext; } });
	Object.defineProperty(exports, "useContext", { enumerable: true, get: function () { return context_js_1.useContext; } });
	var withStyles_js_1 = withStyles$1;
	Object.defineProperty(exports, "withStyles", { enumerable: true, get: function () { return withStyles_js_1.withStyles; } });
	var customElementsMode_js_1 = customElementsMode;
	Object.defineProperty(exports, "defineAsCustomElements", { enumerable: true, get: function () { return customElementsMode_js_1.defineAsCustomElements; } });
	// version
	var helpers_js_2 = helpers;
	Object.defineProperty(exports, "printVersion", { enumerable: true, get: function () { return helpers_js_2.printVersion; } });
	var version_js_1 = version;
	Object.defineProperty(exports, "VERSION", { enumerable: true, get: function () { return version_js_1.VERSION; } });
	
} (lib));

const icdata = (await import(`//plugins/${window.getThemeName()}/config/icons.js`)).default;
const datapath$1 = `//plugins/${window.getThemeName()}/`;
function openConfigs() {
  window.openPluginsFolder(`${getThemeName()}/config`);
}
function openAssets() {
  window.openPluginsFolder(`${getThemeName()}/assets`);
}
class ThemePresetSettings {
  createThemeMenu = async (root) => {
    const l_reload_client = await getString("settings.reload-client");
    const l_open_assets = await getString("preset-settings.open-assets");
    const l_open_configs = await getString("preset-settings.open-configs");
    const l_theme_releases = await getString("preset-settings.theme-releases");
    const l_open_settings = await getString("preset-settings.open-settings");
    class LoaderMenu extends lib.Component {
      visible = false;
      frame = null;
      opener = null;
      didMount() {
        this.opener = document.querySelector("div[action=settings]");
        this.opener?.addEventListener("click", (e) => {
          if (!this.visible) {
            e.stopImmediatePropagation();
            this.show(true);
          }
        });
      }
      show(on) {
        this.visible = on;
        this.update();
        if (this.visible) {
          this.frame?.shadowRoot?.querySelector("lol-uikit-close-button")?.addEventListener("click", () => this.show(false));
        }
      }
      showDefaultSettings() {
        this.opener?.click();
        this.show(false);
      }
      render() {
        return lib.jsx`
					<div style="position: absolute; inset: 0px; z-index: 8500" hidden=${!this.visible || void 0}>
						<lol-uikit-full-page-backdrop style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px; background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.8) 93%);" />
						<div class="dialog-confirm" style="display: flex; align-items: center; justify-content: center; position: absolute; inset: 0px">
							<lol-uikit-dialog-frame ref=${(el) => this.frame = el} class="dialog-frame" orientation="bottom" close-button="false">
								<div class="dialog-content">
									<lol-uikit-content-block class="app-controls-exit-dialog" type="dialog-medium" style="position: relative; overflow: hidden">
										<div style="position: absolute; top: 60px">
											<img src="${datapath$1}assets/Icon/Plugins-icons/${icdata["LL_Settings"]}" style="object-fit: cover; width: 290px; transform: scale(2.5); margin-left: 100px; filter: brightness(0.7)">
										</div>
										</div>
										<div style="position: relative">
											<div style="margin-bottom: 24px"> 
												<h4 style="padding: 6px 0">Lust</h4>
											</div>
											<hr class="heading-spacer" />
											<div style="display: flex; flex-direction: column; align-items: center; gap: 12px">
												<lol-uikit-flat-button-secondary style="display:inline-block; width: 250px" onClick=${() => window.restartClient()}>
													${l_reload_client} (Ctrl-Shift-R)
												</lol-uikit-flat-button-secondary>
												<lol-uikit-flat-button-secondary style="display:inline-block; width: 250px" onClick=${() => openAssets()}>
													${l_open_assets}
												</lol-uikit-flat-button-secondary>
												<lol-uikit-flat-button-secondary style="display:inline-block; width: 250px" onClick=${() => openConfigs()}>
													${l_open_configs}
												</lol-uikit-flat-button-secondary>
											</div>
											<hr class="heading-spacer" />
											<p style="padding: 20px 0" class="lol-settings-code-of-conduct-link lol-settings-window-size-text">
												<a href="https://github.com/lustmyself/Lust/releases" target="_blank">${l_theme_releases}</a>
											</p>
										</div>
									</lol-uikit-content-block>
								</div>
								<lol-uikit-flat-button-group type="dialog-frame">
									<lol-uikit-flat-button tabindex="1" class="button-accept" onClick=${() => this.showDefaultSettings()}>${l_open_settings}</lol-uikit-flat-button>
								</lol-uikit-flat-button-group>
							</lol-uikit-dialog-frame>
						</div>
					</div>
				`;
      }
    }
    lib.render(lib.jsx`<${LoaderMenu} />`, root);
  };
  main = async () => {
    const manager = () => document.getElementById("lol-uikit-layer-manager-wrapper");
    const root = document.createElement("div");
    if (false) {
      while (!manager())
        await utils.stop(300);
      await this.createThemeMenu(root);
      manager()?.prepend(root);
    }
  };
}

const text = await (await fetch(`//plugins/${getThemeName()}/config/customStatus.txt`)).text();
class CustomStatus {
  i = 0;
  sendCustomStatus = async () => {
    let statusMessage = JSON.stringify(text);
    statusMessage = statusMessage.replaceAll("\n", "\\n");
    statusMessage = statusMessage.replaceAll("\r", "\\r");
    statusMessage = statusMessage.replaceAll('"', "");
    let MultiStatus = statusMessage.split("\\r\\n(end status)\\r\\n");
    if (this.i == MultiStatus.length - 1) {
      this.i = 0;
    } else {
      this.i++;
    }
    await fetch("/lol-chat/v1/me", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: `{"statusMessage": "${MultiStatus[this.i]}"}`
    });
  };
  sendLocalStatus = async () => {
    const statusCard = document.querySelector(".hover-card-status-message");
    let MultiStatus = text.split("(end status)");
    if (statusCard) {
      if (this.i == MultiStatus.length - 1) {
        this.i = 0;
      } else {
        this.i++;
      }
      statusCard.textContent = MultiStatus[this.i];
    }
  };
  main = () => {
    if (!LustData.get("Custom-Status-Local")) {
      window.setInterval(async () => {
        await this.sendCustomStatus();
      }, LustData.get("status-delay"));
    } else {
      window.setInterval(async () => {
        await this.sendLocalStatus();
      }, LustData.get("status-delay"));
    }
  };
}

let queue_accepted = false;
let player_declined = false;
let auto_accept_timer = null;
const MAX_AUTO_ACCEPT_DELAY = 15e3;
function parseEventData(message) {
  try {
    return JSON.parse(message["data"])[2]["data"];
  } catch {
    return null;
  }
}
class AutoAccept {
  getAutoAcceptDelay() {
    const rawDelay = Number(LustData.get("auto_accept_delay"));
    if (!Number.isFinite(rawDelay) || rawDelay < 0)
      return 0;
    return Math.min(Math.floor(rawDelay), MAX_AUTO_ACCEPT_DELAY);
  }
  clearAutoAcceptTimer() {
    if (auto_accept_timer !== null) {
      window.clearTimeout(auto_accept_timer);
      auto_accept_timer = null;
    }
  }
  autoAcceptQueueButtonSelect() {
    const element = document.getElementById("autoAcceptQueueButton");
    if (element?.hasAttribute("selected")) {
      LustData.set("auto_accept", false);
      element.removeAttribute("selected");
    } else {
      element?.setAttribute("selected", "true");
      LustData.set("auto_accept", true);
    }
  }
  fetch_or_create_champselect_buttons_container() {
    try {
      document.querySelector(".cs-buttons-container")?.remove();
    } catch {
      error("Error while removing old auto accept button");
    }
    const div = document.createElement("div");
    div.className = "cs-buttons-container";
    let nor = document.querySelector(".v2-footer-notifications.ember-view");
    let tft = document.querySelector(".parties-footer-notifications.ember-view");
    if (nor) {
      nor.append(div);
      return div;
    } else if (tft) {
      tft?.append(div);
      return div;
    }
  }
  getReadyCheck = async () => {
    try {
      const response = await fetch("/lol-matchmaking/v1/ready-check");
      if (!response.ok)
        return null;
      return await response.json();
    } catch {
      return null;
    }
  };
  didPlayerDeclineReadyCheck(readyCheck) {
    return readyCheck?.playerResponse === "Declined";
  }
  canAcceptReadyCheck(readyCheck) {
    if (!readyCheck)
      return false;
    if (this.didPlayerDeclineReadyCheck(readyCheck))
      return false;
    if (readyCheck.state && readyCheck.state !== "InProgress")
      return false;
    return readyCheck.playerResponse === "None" || readyCheck.playerResponse === void 0;
  }
  acceptMatchmaking = async () => {
    if (player_declined)
      return;
    const readyCheck = await this.getReadyCheck();
    if (utils.phase != "ReadyCheck" || !LustData.get("auto_accept") || !this.canAcceptReadyCheck(readyCheck))
      return;
    await fetch("/lol-matchmaking/v1/ready-check/accept", { method: "POST" });
  };
  autoAcceptCallback = async (message) => {
    utils.phase = parseEventData(message);
    if (utils.phase == "ReadyCheck" && LustData.get("auto_accept") && !queue_accepted) {
      queue_accepted = true;
      player_declined = false;
      const delay = this.getAutoAcceptDelay();
      this.clearAutoAcceptTimer();
      if (delay > 0) {
        auto_accept_timer = window.setTimeout(async () => {
          auto_accept_timer = null;
          if (utils.phase == "ReadyCheck" && LustData.get("auto_accept")) {
            await this.acceptMatchmaking();
          }
        }, delay);
      } else if (utils.phase == "ReadyCheck" && LustData.get("auto_accept")) {
        await this.acceptMatchmaking();
      }
    } else if (utils.phase != "ReadyCheck") {
      this.clearAutoAcceptTimer();
      queue_accepted = false;
      player_declined = false;
    }
  };
  readyCheckCallback = async (message) => {
    const readyCheck = parseEventData(message);
    if (!readyCheck)
      return;
    if (this.didPlayerDeclineReadyCheck(readyCheck) || readyCheck.state !== "InProgress") {
      player_declined = this.didPlayerDeclineReadyCheck(readyCheck);
      this.clearAutoAcceptTimer();
      queue_accepted = false;
    }
  };
  createButton = async (element) => {
    const newOption = document.createElement("lol-uikit-radio-input-option");
    const container = this.fetch_or_create_champselect_buttons_container();
    const Option2 = document.createElement("div");
    const delayInput = document.createElement("lol-uikit-flat-input");
    const delayInputElement = document.createElement("input");
    newOption.setAttribute("id", "autoAcceptQueueButton");
    newOption.setAttribute("onclick", "window.autoAcceptQueueButtonSelect()");
    Option2.classList.add("auto-accept-button-text");
    Option2.innerHTML = await getString("auto-accept.auto-accept");
    delayInput.id = "autoAcceptDelayInput";
    delayInput.title = await getString("auto-accept.auto-accept-delay");
    delayInput.style.cssText = "width: 82px; margin-left: 8px;";
    delayInputElement.type = "number";
    delayInputElement.min = "0";
    delayInputElement.max = String(MAX_AUTO_ACCEPT_DELAY);
    delayInputElement.step = "100";
    delayInputElement.placeholder = "ms";
    delayInputElement.value = String(this.getAutoAcceptDelay());
    delayInputElement.addEventListener("input", () => {
      const value = Math.min(Math.max(Number(delayInputElement.value) || 0, 0), MAX_AUTO_ACCEPT_DELAY);
      LustData.set("auto_accept_delay", value);
    });
    delayInput.append(delayInputElement);
    if (LustData.get("auto_accept")) {
      newOption.setAttribute("selected", "");
    }
    if (element && !document.getElementById("autoAcceptQueueButton")) {
      if (LustData.get("auto_accept_button")) {
        container?.append(newOption);
        newOption.append(Option2);
        container?.append(delayInput);
      }
    }
  };
  main = (auto_accept_button = true) => {
    window.autoAcceptQueueButtonSelect = this.autoAcceptQueueButtonSelect;
    observer.subscribeToElementCreation(".v2-lobby-root-component.ember-view .v2-footer-notifications.ember-view", async (element) => {
      await this.createButton(element);
    });
    observer.subscribeToElementCreation(".tft-footer-container.ember-view .parties-footer-notifications.ember-view", async (element) => {
      await this.createButton(element);
    });
    if (auto_accept_button) {
      utils.subscribe_endpoint("/lol-gameflow/v1/gameflow-phase", this.autoAcceptCallback);
      utils.subscribe_endpoint("/lol-matchmaking/v1/ready-check", this.readyCheckCallback);
    }
  };
}

class CustomBeRp {
  RP = () => {
    const rpData = `${LustData.get("RP-data")}`;
    let RP = document.querySelector(".currency-rp-top-up-enabled");
    let RPMac = document.querySelector(".currency-rp");
    if (RP) {
      RP.textContent = rpData;
    } else if (RPMac) {
      RPMac.textContent = rpData;
    }
  };
  BE = () => {
    let BE = document.querySelector(".currency-be-component.ember-view");
    if (!BE)
      return;
    BE.innerHTML = /* html */
    `
			<div class="currency-be-icon-container">
				<div class="currency-be-icon-static"></div>
				<lol-uikit-video type="intro" src="/fe/lol-navigation/add-blue-essence.webm" class="animation-add-blue-essence"></lol-uikit-video>
				<lol-uikit-video type="intro" src="/fe/lol-navigation/remove-blue-essence.webm" class="animation-remove-blue-essence"></lol-uikit-video>
			</div>
			${utils.escapeHtml(LustData.get("BE"))}
		`;
  };
}

class CustomSummonerLv {
  customLvOnSidebar = () => {
    const customLv = LustData.get("custom-summoner-lv-number");
    let summonerLevelElement = document.querySelector(".summoner-level");
    if (summonerLevelElement) {
      summonerLevelElement.textContent = customLv;
    }
  };
  customLvOnProfile = () => {
    const customLv = LustData.get("custom-summoner-lv-number");
    let summonerXpRadialNumbers = document.querySelector(".summoner-xp-radial-numbers");
    if (summonerXpRadialNumbers) {
      summonerXpRadialNumbers.textContent = customLv;
    }
  };
  main = () => {
    this.customLvOnSidebar();
    this.customLvOnProfile();
  };
}

let datapath = `//plugins/${getThemeName()}/`;
function AddElement(parent, tag, params = [], classes = [], content = null) {
  let element = document.createElement(tag);
  params.forEach((param) => element.setAttribute(param.name, param.value));
  classes.forEach((className) => element.classList.add(className));
  if (content)
    element.innerHTML = content;
  parent.append(element);
  return element;
}
async function GetLoot() {
  let loot = {
    championShards: [],
    championSkinShards: [],
    shopTokens: [],
    chests: [],
    blueEssence: 0
  };
  await fetch("/lol-loot/v1/player-loot-map").then((response) => response.json()).then((data) => {
    Object.entries(data).forEach((item) => {
      let [key, value] = item;
      if (value.lootId === "CURRENCY_champion")
        loot.blueEssence = value.count;
      if (value.redeemableStatus !== "CHAMPION_NOT_OWNED" || value.upgradeEssenceValue !== 0) {
        if (value.lootId.includes("CHEST") && value.localizedName !== "") {
          loot.chests.push({
            name: value.localizedName,
            id: value.lootId,
            data: value
          });
        }
        if (value.localizedRecipeTitle.includes("Shop")) {
          loot.shopTokens.push({
            name: value.localizedName,
            id: value.lootId,
            data: value
          });
        }
        for (let i = 0; i < value.count; i++) {
          switch (value.displayCategories) {
            case "CHAMPION":
              loot.championShards.push({
                name: value.itemDesc,
                id: value.lootId,
                data: value
              });
              break;
            case "SKIN":
              loot.championSkinShards.push({
                name: value.itemDesc,
                id: value.lootId,
                data: value
              });
              break;
          }
        }
      }
    });
  }).catch((error) => {
    error(error);
  });
  return loot;
}
function Sum(items, prop, propMultiply = null) {
  return items.reduce(function(a, b) {
    let sum = 0;
    if (propMultiply != null)
      sum = a + prop.split(".").reduce((x, c) => x[c], b) * propMultiply.split(".").reduce((x, c) => x[c], b);
    else
      sum = a + prop.split(".").reduce((x, c) => x[c], b);
    return sum;
  }, 0);
}
function AddContextMenu(title, subTitle, items = []) {
  let container = AddElement(document.body, "div", [
    {
      name: "style",
      value: "position: absolute; z-index: 10000; left: 63px; top: 310px;"
    }
  ], ["niice-loot-helper-context-menu"]);
  let contextMenu = AddElement(container, "div", [], ["context-menu", "loot-context-menu", "context-menu-root"]);
  let header = AddElement(contextMenu, "div", [], ["context-menu-header", "disabled"]);
  AddElement(header, "div", [], ["title"], "<h5>" + title + "</h5>");
  AddElement(header, "div", [], [], subTitle);
  AddElement(header, "hr", [], ["separator"]);
  items.forEach((item) => {
    let menuItem = AddElement(contextMenu, "div", [], ["context-menu-item"]);
    if (item.actionIcon != null && item.actionIcon !== "")
      AddElement(menuItem, "div", [{
        name: "style",
        value: 'background-image: url("' + item.actionIcon + '");'
      }], ["action-icon"]);
    AddElement(menuItem, "div", [], [], '<span class="action-name">' + item.title + "</span> " + item.subTitle);
    if (item.essenceIcon != null && item.essenceIcon !== "")
      AddElement(menuItem, "div", [], ["essence-icon", "pull-right"], '<img src="' + item.essenceIcon + '"/>');
    let essenceTextClasses = ["pull-right", "essence-container", "essence-text"];
    if (item.essenceText != null && item.essenceText.toString().includes("-"))
      essenceTextClasses.push("negative-text");
    AddElement(menuItem, "div", [], essenceTextClasses, item.essenceText);
    AddElement(menuItem, "div", [], ["disabled-overlay"]);
    if (item.clickEvent != null)
      menuItem.addEventListener("click", item.clickEvent);
  });
}
function OnClickRefreshButton() {
  try {
    document.querySelectorAll(".loot-category-information").forEach((elem) => {
      elem.remove();
    });
  } catch {
  }
  CreateChapmsInformation();
  CreateSkinsInformation();
}
function OnClickOpenChestsButton() {
  let contextMenu = document.querySelector(".niice-loot-helper-context-menu");
  if (contextMenu != null)
    return;
  GetLoot().then(async (loot) => {
    let items = [];
    loot.chests.forEach(async (chest) => {
      items.push({
        title: `${await getString("loot-helper.open")}`,
        subTitle: chest.name,
        essenceText: chest.data.count,
        clickEvent: async () => {
          if (window.confirm(`${await getString("loot-helper.open-chest-prom")} ` + chest.name + "?")) {
            await fetch("/lol-loot/v1/recipes/" + chest.id + "_OPEN/craft?repeat=" + chest.data.count, {
              method: "POST",
              body: JSON.stringify([chest.id]),
              headers: {
                "Content-Type": "application/json"
              }
            }).then(async (response) => {
              if (response.status === 500) {
                await fetch("/lol-loot/v1/recipes/" + chest.id + "_OPEN/craft?repeat=" + chest.data.count, {
                  method: "POST",
                  body: JSON.stringify([chest.id, "MATERIAL_key"]),
                  headers: {
                    "Content-Type": "application/json"
                  }
                });
              }
            });
          }
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      });
    });
    items.push({
      title: `${await getString("loot-helper.close")}`,
      subTitle: "",
      actionIcon: "",
      essenceIcon: "",
      essenceText: "",
      clickEvent: () => {
        let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
        if (contextMenu2 != null)
          contextMenu2.remove();
      }
    });
    AddContextMenu(`${await getString("loot-helper.materials")}`, `${await getString("loot-helper.open-chest")}`, items);
  });
}
function OnClickBlueEssenceButton() {
  let contextMenu = document.querySelector(".niice-loot-helper-context-menu");
  if (contextMenu != null)
    return;
  GetLoot().then(async (loot) => {
    let keyMaps = {};
    let alreadyOwned = [];
    let duplicates = [];
    loot.championShards.forEach((item) => {
      if (item.data.itemStatus === "OWNED")
        alreadyOwned.push(item);
      let { id } = item;
      keyMaps[id] = keyMaps[id] ?? [];
      keyMaps[id].push(item);
    });
    Object.keys(keyMaps).forEach((key) => {
      if (keyMaps[key].length >= 2) {
        for (let i = 1; i < keyMaps[key].length; i++) {
          duplicates.push(keyMaps[key][i]);
        }
      }
    });
    let upgradableChampions = [];
    let championShards = loot.championShards.sort((a, b) => a.data.upgradeEssenceValue > b.data.upgradeEssenceValue ? 1 : b.data.upgradeEssenceValue > a.data.upgradeEssenceValue ? -1 : 0);
    let blueEssence = loot.blueEssence;
    championShards.forEach((item) => {
      if (item.data.itemStatus === "FREE" && blueEssence >= item.data.upgradeEssenceValue) {
        upgradableChampions.push(item);
        blueEssence -= item.data.upgradeEssenceValue;
      }
    });
    AddContextMenu(`${await getString("loot-helper.be")}`, `${await getString("loot-helper.champ-shards")}`, [
      {
        title: `${await getString("loot-helper.disenchant")}`,
        subTitle: `${await getString("loot-helper.duplicates")}`,
        actionIcon: "/fe/lol-loot/assets/context_menu/disenchant.png",
        essenceIcon: "/fe/lol-loot/assets/context_menu/currency_champion.png",
        essenceText: "+" + Sum(duplicates, "data.disenchantValue"),
        clickEvent: async () => {
          if (window.confirm(`${await getString("loot-helper.dis-dup-prom")}`)) {
            duplicates.forEach(async (item) => {
              await fetch("/lol-loot/v1/recipes/CHAMPION_RENTAL_disenchant/craft?repeat=1", {
                method: "POST",
                body: JSON.stringify([item.id]),
                headers: {
                  "Content-Type": "application/json"
                }
              });
            });
          }
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      },
      {
        title: `${await getString("loot-helper.disenchant")}`,
        subTitle: `${await getString("loot-helper.already-owned")}`,
        actionIcon: "/fe/lol-loot/assets/context_menu/disenchant.png",
        essenceIcon: "/fe/lol-loot/assets/context_menu/currency_champion.png",
        essenceText: "+" + Sum(alreadyOwned, "data.disenchantValue"),
        clickEvent: async () => {
          if (window.confirm(`${await getString("loot-helper.dis-owned-prom")}`)) {
            alreadyOwned.forEach(async (item) => {
              await fetch("/lol-loot/v1/recipes/CHAMPION_RENTAL_disenchant/craft?repeat=1", {
                method: "POST",
                body: JSON.stringify([item.id]),
                headers: {
                  "Content-Type": "application/json"
                }
              });
            });
          }
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      },
      {
        title: `${await getString("loot-helper.disenchant")}`,
        subTitle: `${await getString("loot-helper.all")}`,
        actionIcon: "/fe/lol-loot/assets/context_menu/disenchant.png",
        essenceIcon: "/fe/lol-loot/assets/context_menu/currency_champion.png",
        essenceText: "+" + Sum(loot.championShards, "data.disenchantValue"),
        clickEvent: async () => {
          if (window.confirm(`${await getString("loot-helper.dis-all-prom")}`)) {
            loot.championShards.forEach(async (item) => {
              await fetch("/lol-loot/v1/recipes/CHAMPION_RENTAL_disenchant/craft?repeat=1", {
                method: "POST",
                body: JSON.stringify([item.id]),
                headers: {
                  "Content-Type": "application/json"
                }
              });
            });
          }
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      },
      {
        title: `${await getString("loot-helper.upgrade")}`,
        subTitle: `${await getString("loot-helper.all")}`,
        actionIcon: "/fe/lol-loot/assets/context_menu/upgrade.png",
        essenceIcon: "/fe/lol-loot/assets/context_menu/currency_champion.png",
        essenceText: "-" + Sum(upgradableChampions, "data.upgradeEssenceValue"),
        clickEvent: async () => {
          if (window.confirm(`${await getString("loot-helper.up-all-prom")}`)) {
            upgradableChampions.forEach(async (item) => {
              await fetch("/lol-loot/v1/recipes/CHAMPION_upgrade/craft?repeat=1", {
                method: "POST",
                body: JSON.stringify([item.id, "CURRENCY_champion"]),
                headers: {
                  "Content-Type": "application/json"
                }
              });
            });
          }
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      },
      {
        title: `${await getString("loot-helper.close")}`,
        subTitle: "",
        actionIcon: "",
        essenceIcon: "",
        essenceText: "",
        clickEvent: () => {
          let contextMenu2 = document.querySelector(".niice-loot-helper-context-menu");
          if (contextMenu2 != null)
            contextMenu2.remove();
        }
      }
    ]);
  });
}
function CreateBlueEssenceButton() {
  let tabs = document.querySelector(".loot-display-category-tabs-container");
  if (tabs == null)
    return;
  if (document.querySelector(".blue-essence-button-container") != null)
    return;
  let container = AddElement(tabs, "div", [], ["blue-essence-button-container"]);
  let button = AddElement(container, "div", [], ["blue-essence-button"]);
  button.addEventListener("click", OnClickBlueEssenceButton);
}
function CreateRefreshButton() {
  let tabs = document.querySelector(".loot-display-category-tabs-container");
  if (tabs == null)
    return;
  if (document.querySelector(".refresh-button-container") != null)
    return;
  let container = AddElement(tabs, "div", [], ["refresh-button-container"]);
  let button = AddElement(container, "div", [], ["refresh-button"]);
  button.addEventListener("click", OnClickRefreshButton);
}
function CreateOpenChestsButton() {
  let tabs = document.querySelector(".loot-display-category-tabs-container");
  if (tabs == null)
    return;
  if (document.querySelector(".open-chests-button-container") != null)
    return;
  let container = AddElement(tabs, "div", [], ["open-chests-button-container"]);
  let button = AddElement(container, "div", [], ["open-chests-button"]);
  button.addEventListener("click", OnClickOpenChestsButton);
}
function CreateChapmsInformation() {
  let categories = document.querySelectorAll(".display-category-section");
  if (categories == null || categories.length === 0)
    return;
  if (document.querySelector(".loot-category-information") != null)
    return;
  GetLoot().then(async (loot) => {
    AddElement(categories[1].querySelector(".title-text"), "span", [
      {
        name: "style",
        value: "margin-left: 5px;"
      }
    ], ["loot-category-information"], "(" + loot.championShards.length + " " + await getString("loot-helper.shards") + " | " + await getString("loot-helper.worth") + " " + Sum(loot.championShards, "data.disenchantValue", "data.count") + ' <img style="margin-bottom: -4px;" src="/fe/lol-loot/assets/context_menu/currency_champion.png"/>)');
  });
}
function CreateSkinsInformation() {
  let categories = document.querySelectorAll(".display-category-section");
  if (categories == null || categories.length === 0)
    return;
  if (document.querySelector(".loot-category-information") != null)
    return;
  GetLoot().then(async (loot) => {
    AddElement(categories[2].querySelector(".title-text"), "span", [
      {
        name: "style",
        value: "margin-left: 5px;"
      }
    ], ["loot-category-information"], "(" + loot.championSkinShards.length + " " + await getString("loot-helper.shards") + " | " + await getString("loot-helper.worth") + " " + Sum(loot.championSkinShards, "data.disenchantValue", "data.count") + ' <img style="margin-bottom: -4px;" src="/fe/lol-loot/assets/context_menu/currency_cosmetic.png"/>)');
  });
}
class LootHelper {
  main = () => {
    utils.addStyleNode(
      /*css*/
      `
            @import url("${datapath}assets/styles/components/loothelper.css");
            :root {
                --OC_button:url("${datapath}assets/icon/plugins-icons/button-open-chests.png");
                --BE_button:url("${datapath}assets/icon/plugins-icons/button-blue-essence.png");
                --BE_hover:url("${datapath}assets/icon/plugins-icons/button-blue-essence-hover.png");
                --BE_active:url("${datapath}assets/icon/plugins-icons/button-blue-essence-click.png");
                --rbutton:url("${datapath}assets/icon/plugins-icons/button-refresh.png");
                --rhover:url("${datapath}assets/icon/plugins-icons/button-refresh-hover.png");
                --ractive:url("${datapath}assets/icon/plugins-icons/button-refresh-click.png");
                --OC_hover:url("${datapath}assets/icon/plugins-icons/button-open-chests-hover.png");
                --OC_active:url("${datapath}assets/icon/plugins-icons/button-open-chests-click.png");
            }
        `
    );
    observer.subscribeToElementCreation(".loot-inventory-grid ", (element) => {
      log("%cLoot helper loaded", "color: #e4c2b3");
      OnClickRefreshButton();
      window.setTimeout(() => {
        OnClickRefreshButton();
      }, 2e3);
    });
    observer.subscribeToElementCreation(".loot-display-category-tabs-container", (element) => {
      CreateRefreshButton();
      CreateOpenChestsButton();
      CreateBlueEssenceButton();
    });
    observer.subscribeToElementCreation(".loot-tray.ember-view", (element) => {
      element.setAttribute("style", "margin-top: 0px;");
    });
  };
}

const SELECTORS = `
    .banner-summoner-name,
    .chat-gnt,
    .chat-name,
    .conversation-title,
    .custom-member-name,
    .hover-card-game-name,
    .hover-card-game-tag,
    .hover-card-name,
    .lol-leagues-list-col-3.lol-leagues-list-col,
    .lol-leagues-list-item.me.current.ember-view .rank-standing-row-component,
    .match-details-team-list .player-history-mode,
    .member-name,
    .name-text,
    .prompted-voting-candidate-name,
    .scoreboard-row-player-name,
    .style-profile-search-trail-summoner-name,
    .message-name,
    .system-message,
    .invite-info-name,
    .lol_parties__invite_dialog_name-and-context,
    .chat-name,
    .chat-gnt,
    .message-box-messages-system-message,
    .reform-card-chat-log-name,
    .hover-card-name,
    .hover-card-game-name,
    .hover-card-game-tag,
    .create-panel-summoner-name,
    .create-panel-game-name,
    .player-name__game-name,
    .player-name__force-locale-text-direction
`;
class NameSpoofer {
  updateNames(root = document) {
    const Name = LustData.get("Spoof-name");
    const spoof = LustData.get("Name-Spoofer");
    if (!spoof)
      return;
    const elements = root.querySelectorAll(SELECTORS);
    elements.forEach((element) => {
      if (element.textContent !== Name) {
        element.textContent = Name;
      }
    });
    const systemMessages = root.querySelectorAll(".system-message");
    systemMessages.forEach((sysMessage) => {
      if (sysMessage.textContent !== "🐱‍👤") {
        sysMessage.textContent = "🐱‍👤";
      }
    });
  }
  observeChanges(target) {
    new MutationObserver(() => this.updateNames(target)).observe(target, {
      childList: true,
      subtree: true
    });
  }
  main = () => {
    const manager = document.getElementById("rcp-fe-viewport-root");
    if (manager) {
      this.observeChanges(manager);
    }
    const myMessageBox = document.getElementById("embedded-messages-frame");
    if (myMessageBox && myMessageBox.contentDocument) {
      this.observeChanges(myMessageBox.contentDocument);
    }
    setInterval(this.updateNames, 100);
  };
}

let covert_status = "chat";
class OfflineMode {
  possible_status = ["dnd", "chat", "away", "offline", "mobile"];
  get_status_by_icon() {
    let element = document.querySelector(".availability-icon");
    if (element) {
      for (let elem of this.possible_status) {
        if (element.classList.contains(elem)) {
          return elem;
        }
      }
    }
    return "chat";
  }
  switch_between_status = async () => {
    let status = this.get_status_by_icon();
    let availability = status == "chat" ? "mobile" : status == "mobile" ? "dnd" : status == "dnd" ? "away" : status == "away" ? "offline" : status == "offline" ? "chat" : "chat";
    log(`Changed status to ${availability}`);
    await fetch("/lol-chat/v1/me", {
      "headers": {
        "content-type": "application/json"
      },
      "body": `{"availability":"${availability}"${availability == "offline" || availability == "away" ? `,"lol":{"gameStatus":"outOfGame"}` : availability == "dnd" ? `,"lol":{"gameStatus":"inGame"}` : ``}}`,
      "method": "PUT"
    });
    for (let i = 0; i < this.possible_status.length; i++) {
      document.querySelector(".availability-icon")?.classList.remove(this.possible_status[i]);
    }
    document.querySelector(".availability-icon")?.classList.add(availability);
    covert_status = availability;
  };
  async patchStatus() {
    await fetch("/lol-chat/v1/me", {
      "headers": {
        "content-type": "application/json"
      },
      "body": `{"availability":"${covert_status}","lol":{"gameStatus":"outOfGame"}}`,
      "method": "PUT"
    });
  }
  champSelectPatchStatus = async (message) => {
    let phase = JSON.parse(message["data"])[2]["data"];
    if (phase == "ChampSelect" && (covert_status == "offline" || covert_status == "away")) {
      await this.patchStatus();
    }
  };
  main = () => {
    window.switch_between_status = this.switch_between_status;
    let availabilityButtonMutationObserver = async () => {
      let circle_status = document.querySelector(".availability-hitbox:not(.offline-mode-available), .availability-hitbox:not([onclick])");
      let circle_status_custom = document.querySelectorAll(".availability-hitbox.offline-mode-available");
      if (circle_status) {
        circle_status.classList.add("offline-mode-available");
        circle_status.outerHTML = circle_status.outerHTML;
        document.querySelector(".availability-hitbox")?.setAttribute("onclick", "window.switch_between_status()");
        let status = (await (await fetch("/lol-chat/v1/me")).json()).availability;
        let status_icon = this.get_status_by_icon();
        if (this.get_status_by_icon() !== status) {
          document.querySelector(".availability-icon")?.classList.remove(status_icon);
          document.querySelector(".availability-icon")?.classList.add(status);
        }
      }
      if (covert_status == "offline") {
        await this.patchStatus();
      }
      if (circle_status_custom.length > 1) {
        circle_status_custom.forEach((elem, index) => {
          if (index) {
            elem.remove();
          }
        });
      }
    };
    utils.subscribe_endpoint("/lol-gameflow/v1/gameflow-phase", this.champSelectPatchStatus);
    utils.routineAddCallback(availabilityButtonMutationObserver, ["availability-hitbox", "status-message"]);
  };
}

class InviteAllFriends {
  setDefaultFriendsListData = () => {
    if (!LustData.has("frGroupName")) {
      LustData.set("frGroupName", 0);
    }
    if (!LustData.has("grouplist")) {
      LustData.set("grouplist", []);
    }
    if (!LustData.has("friendslist")) {
      LustData.set("friendslist", []);
    }
  };
  refreshFriendsList = async () => {
    try {
      const [friends, groups] = await Promise.all([
        fetch("/lol-chat/v1/friends").then((res) => res.json()),
        fetch("/lol-chat/v1/friend-groups").then((res) => res.json())
      ]);
      if (LustData.get("grouplist").length !== groups.length || LustData.get("friendslist").length !== friends.length) {
        LustData.set("friendslist", friends.map((friend) => ({
          summonerId: friend.summonerId,
          groupId: friend.groupId,
          availability: friend.availability
        })));
        LustData.set("grouplist", groups.map((group) => ({
          id: group.id,
          name: group.name
        })));
        document.getElementById("inviteAllDiv")?.remove();
        this.addInviteAllButton();
        log("Friends list refreshed.");
      }
    } catch (error) {
      log("Error refreshing friends list:", error);
    }
  };
  addInviteAllButton = async () => {
    if (document.querySelector(".lobby-header-buttons-container") != null) {
      let groupList = { "name": [], "id": [] };
      for (let i = 0; i < LustData.get("grouplist").length; i++) {
        groupList["id"].push(LustData.get("grouplist")[i]["id"]);
        groupList["name"].push(LustData.get("grouplist")[i]["name"]);
      }
      const mainDiv = document.createElement("div");
      mainDiv.id = "inviteAllDiv";
      mainDiv.style.display = "flex";
      let button = document.createElement("lol-uikit-flat-button");
      button.textContent = "Invite all";
      button.onclick = async () => {
        await this.refreshFriendsList();
        let Invited = 0;
        let fakerun = new Promise(() => {
        });
        window.Toast.promise(fakerun, {
          loading: "Inviting all...",
          success: "",
          error: ""
        });
        for (let i = 0; i < LustData.get("friendslist").length; i++) {
          if (LustData.get("frGroupName") == LustData.get("friendslist")[i]["groupId"] && LustData.get("friendslist")[i]["availability"] == "chat") {
            let invite = await fetch("/lol-lobby/v2/lobby/invitations", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify([{ "toSummonerId": LustData.get("friendslist")[i]["summonerId"] }])
            });
            if (invite.status == 200)
              Invited++;
          }
        }
        window.Toast.success(`Invited ${Invited} friends`);
      };
      let div = document.createElement("div");
      div.classList.add("Dropdown-div");
      let dropdown = document.createElement("lol-uikit-framed-dropdown");
      dropdown.classList.add("lol-settings-general-dropdown");
      dropdown.style.cssText = "margin-right: 10px; width: 198px;";
      for (let i = 0; i < groupList["id"].length; i++) {
        let el = document.createElement("lol-uikit-dropdown-option");
        el.setAttribute("slot", "lol-uikit-dropdown-option");
        el.innerText = groupList["name"][i];
        el.onclick = () => {
          LustData.set("frGroupName", groupList["id"][i]);
        };
        if (LustData.get("frGroupName") == groupList["id"][i]) {
          el.setAttribute("selected", "true");
        }
        dropdown.appendChild(el);
      }
      div.append(dropdown);
      mainDiv.append(div, button);
      let gameBar = document.querySelector(".lobby-header-buttons-container");
      if (!document.querySelector("#inviteAllDiv")) {
        gameBar?.insertBefore(mainDiv, gameBar.children[1]);
      }
    }
  };
  main = () => {
    this.setDefaultFriendsListData();
    observer.subscribeToElementCreation(".v2-header-component.ember-view", (element) => {
      this.refreshFriendsList();
      this.addInviteAllButton();
    });
  };
}

class ForceJungLane {
  async forceJungle() {
    await fetch("/lol-champ-select/v1/session/my-selection", {
      "headers": {
        "content-type": "application/json"
      },
      "body": '{"spell1Id":11,"spell2Id":4}',
      "method": "PATCH"
    });
  }
  async forceLane() {
    await fetch("/lol-champ-select/v1/session/my-selection", {
      "headers": {
        "content-type": "application/json"
      },
      "body": '{"spell1Id":7,"spell2Id":4}',
      "method": "PATCH"
    });
  }
  main = () => {
    window.addEventListener("keydown", async (event) => {
      let key = event.key;
      if (event.altKey && key == "j") {
        await this.forceJungle();
      }
      if (event.altKey && key == "l") {
        await this.forceLane();
      }
    });
  };
}

let initialized = false;
async function subscribe_endpoint(endpoint, callback) {
  const getUri = document.querySelector('link[rel="riot:plugins:websocket"]');
  const uri = getUri.href;
  const ws = new WebSocket(uri, "wamp");
  log(uri);
  ws.onopen = () => ws.send(JSON.stringify([5, "OnJsonApiEvent" + endpoint.replace(/\//g, "_")]));
  ws.onmessage = callback;
}
async function fetch_riotclient_credentials() {
  await fetch("/riotclient/command-line-args", {
    "method": "GET"
  }).then((response) => response.json()).then((data) => {
    data.forEach((elem) => {
    });
  });
}
let debugLogEndpoints = async (message) => {
  if (LustData.get("Debug-mode")) {
    console.log(
        JSON.parse(message["data"])[2]["uri"],
        JSON.parse(message["data"])[2]["data"]
      );
  }
};
function initDebug() {
  if (initialized)
    return;
  initialized = true;
  fetch_riotclient_credentials();
  if (LustData.get("Debug-mode")) {
    subscribe_endpoint("", debugLogEndpoints);
  }
}

log("By %cLust", "color: #e4c2b3");
log("%cMeow ~~~", "color: #e4c2b3");
log("Importing theme contents");
async function init(context) {
  log("Resolving theme name");
  initThemeName(context);
  log("Initializing LustData storage");
  await LustData$1.init(context);
  await restoreDefaultDataStore();
  LustData$1.set("start-time", Date.now());
  log("Initializing file system for theme");
  await fileSystem.init(context);
  log("Initializing icon sync storage");
  await syncUserIcons.init();
  log("Initializing theme");
  await initThemeDataCdn();
  initDebug();
  Settings(context);
  transparentLobby(context);
}
class LustTheme {
  async main() {
    const applyUI = new ApplyUI();
    await applyUI.main();
    const filters = new Filters();
    filters.main();
    const loadCss = new LoadCss();
    loadCss.main();
    const themePresetSettings = new ThemePresetSettings();
    themePresetSettings.main();
    const customBeRp = new CustomBeRp();
    const customSummonerLv = new CustomSummonerLv();
    const autoAccept = new AutoAccept();
    autoAccept.main(LustData$1.get("auto_accept_button"));
    const customStatus = new CustomStatus();
    if (LustData$1.get("Custom-Status") && LustData$1.get("Custom-profile-hover"))
      customStatus.main();
    const forceJungleLane = new ForceJungLane();
    forceJungleLane.main();
    const inviteAllFriends = new InviteAllFriends();
    if (false)
      inviteAllFriends.main();
    const lootHelper = new LootHelper();
    if (false)
      lootHelper.main();
    const nameSpoofer = new NameSpoofer();
    nameSpoofer.main();
    window.setInterval(() => {
      if (LustData$1.get("custom-rp"))
        customBeRp.RP();
      if (LustData$1.get("custom-be"))
        customBeRp.BE();
      if (false)
        customSummonerLv.main();
      window.refreshLists();
    }, 1e3);
  }
}
const lustTheme = new LustTheme();
async function load() {
  await lustTheme.main();
  if (LustData$1.get("Dev-mode"))
    window.upl = upl;
}

export { init, load };
