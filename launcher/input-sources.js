/* TV input sources: live EIM status over the captured inventory, plus the Inputs shelf and preview preferences. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.InputSources = factory();
}(this, function () {
  'use strict';
  var PREVIEW_KEY = 'tvhome.inputs.preview.v1',
    // Native external video may ignore element mute or switch HDR.
    PREVIEW_DEFAULT = true,
    STATUS_URI = 'luna://com.webos.service.eim/getAllInputStatus',
    // The installer registers Home as an EIM input so the TV can return to it; it is not a source.
    HOME_APPS = ['com.gathin.tvhome', 'com.local.nativehome'],
    LIMIT = 100;
  function text(value, max) {
    return typeof value === 'string' && value.trim() ? value.trim().slice(0, max) : null;
  }
  // The webOS external-input video source for an HDMI port; other ports have no preview.
  function source(appId, id) {
    var match = /^com\.webos\.app\.hdmi([1-9])$/.exec(appId || '') || /^HDMI_([1-9])$/.exec(id || '');
    return match ? 'ext://hdmi:' + match[1] : null;
  }
  // Icon family from the user's input label or the device's own HDMI name.
  function classify(label, deviceName) {
    var name = ((label || '') + ' ' + (deviceName || '')).toLowerCase();
    if (/playstation|\bps[345]\b|xbox|nintendo|\bswitch\b|steam/.test(name)) return 'game';
    if (/apple ?tv|chromecast|fire ?tv|fire ?stick|shield|roku|google ?tv/.test(name)) return 'stream';
    if (/\bpc\b|computer|\bmac\b|macbook|mac mini|laptop/.test(name)) return 'pc';
    return 'hdmi';
  }
  function fromInventory(inputs) {
    var seen = Object.create(null);
    return (Array.isArray(inputs) ? inputs : []).filter(function (input) {
      var appId = input && text(input.appId, 256);
      if (!appId || seen[appId] || HOME_APPS.indexOf(appId) >= 0) return false;
      seen[appId] = true; return true;
    }).slice(0, LIMIT).map(function (input) {
      var appId = text(input.appId, 256), label = text(input.label, 256) || appId;
      return {appId: appId, label: label, deviceName: null, connected: null, kind: classify(label, null), source: source(appId, null)};
    });
  }
  // Field names follow webOS EIM replies; anything unexpected keeps the inventory.
  // Other app-registered inputs (MVPD_*) are not sources either.
  function fromStatus(reply) {
    if (!reply || reply.returnValue === false || !Array.isArray(reply.devices)) return null;
    var seen = Object.create(null);
    var devices = reply.devices.filter(function (device) {
      var appId = device && text(device.appId, 256);
      if (!appId || seen[appId] || HOME_APPS.indexOf(appId) >= 0 || /^MVPD_/.test(text(device.id, 256) || '')) return false;
      seen[appId] = true; return true;
    }).slice(0, LIMIT).map(function (device) {
      return {appId: text(device.appId, 256), label: text(device.label, 256), id: text(device.id, 256),
        deviceName: text(device.deviceName, 256) || text(device.spdProductDescription, 256),
        connected: typeof device.connected === 'boolean' ? device.connected : null};
    });
    return devices.length ? devices : null;
  }
  // Live status overlays the captured inventory: its order and entries stay, the TV's
  // newer label, device name and connection state apply, and uncaptured ports follow.
  function merge(inventory, devices) {
    if (!devices) return inventory;
    var status = Object.create(null), known = Object.create(null);
    devices.forEach(function (device) { status[device.appId] = device; });
    function entry(base, device) {
      var label = device.label || base.label || device.id || device.appId, deviceName = device.deviceName;
      if (deviceName && deviceName.toLowerCase() === label.toLowerCase()) deviceName = null;
      return {appId: device.appId, label: label, deviceName: deviceName, connected: device.connected,
        kind: classify(label, deviceName), source: source(device.appId, device.id) || base.source || null};
    }
    var merged = inventory.map(function (input) {
      known[input.appId] = true;
      return status[input.appId] ? entry(input, status[input.appId]) : input;
    });
    devices.forEach(function (device) { if (!known[device.appId]) merged.push(entry({}, device)); });
    return merged.slice(0, LIMIT);
  }
  function create(options) {
    options = options || {};
    var listeners = [],
      started = false,
      pending = false,
      snapshot = options.root === true,
      fallback = false,
      devices = null;
    // The inventory is read on demand: a profile restore can replace it after startup.
    function inventory() {
      return fromInventory(typeof options.inventory === 'function' ? options.inventory() : options.inventory);
    }
    function list() { return merge(inventory(), devices); }
    function reply(result) {
      var before = JSON.stringify(list());
      devices = fromStatus(result);
      var next = list();
      if (JSON.stringify(next) !== before) listeners.slice().forEach(function (listener) { listener(next.slice()); });
    }
    function read() {
      if (pending || typeof options.call !== 'function') return;
      var oneShot = snapshot || fallback, completed = false;
      pending = oneShot;
      function receive(result) {
        if (oneShot) {
          if (completed) return;
          completed = true; pending = false; reply(result);
        } else if (!fallback) {
          // A denied WebApp EIM call does not imply the paired Helper cannot read inputs.
          if (result && result.returnValue === false && result.errorCode === -1) {
            fallback = true; read();
          } else reply(result);
        }
      }
      try {
        options.call(snapshot ? 'luna://com.cleanyourtv.root.preview.service/listApps' :
          fallback ? 'luna://com.gathin.tvhome.renewal/inputStatus' : STATUS_URI,
          snapshot ? {inputs:true} : fallback ? {} : {subscribe:true}, receive, oneShot ? 10000 : undefined);
      } catch (_) { receive(null); }
    }
    return {
      // Starts once; until a valid reply arrives the inventory shows without status.
      start: function () {
        if (started || typeof options.call !== 'function') return;
        started = true;
        read();
      },
      // Broker snapshots refresh only for explicit foreground interactions.
      refresh: function () { if (started && (snapshot || fallback)) read(); },
      list: list,
      live: function () { return !!devices; },
      onchange: function (listener) { if (typeof listener === 'function') listeners.push(listener); }
    };
  }
  function previewEnabled(storage) {
    try {
      var saved = JSON.parse(storage.getItem(PREVIEW_KEY));
      return saved && saved.version === 1 && typeof saved.enabled === 'boolean' ? saved.enabled : PREVIEW_DEFAULT;
    } catch (_) { return PREVIEW_DEFAULT; }
  }
  function setPreviewEnabled(storage, enabled) {
    if (typeof enabled !== 'boolean') throw Error('invalid-input-preview-setting');
    storage.setItem(PREVIEW_KEY, JSON.stringify({version: 1, enabled: enabled}));
    return enabled;
  }
  return {previewKey: PREVIEW_KEY, statusUri: STATUS_URI, classify: classify, source: source, create: create,
    previewEnabled: previewEnabled, setPreviewEnabled: setPreviewEnabled};
}));
