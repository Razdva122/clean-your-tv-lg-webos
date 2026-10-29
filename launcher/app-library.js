/* Persistent screen layout, independent of the TV's installed-app inventory. */
(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AppLibrary = factory();
}(this, function() {
  'use strict';
  var KEY = 'tvhome.layout';
  var internal = ['com.gathin.tvhome','com.local.nativehome','com.cleanyourtv.root.preview','com.cleanyourtv.updater'];
  function unique(ids) { return ids.filter(function(id,i) { return typeof id === 'string' && ids.indexOf(id) === i && internal.indexOf(id) < 0; }); }
  function clean(apps) {
    var seen = Object.create(null);
    return apps.filter(function(a) {
      if (!a || typeof a.id !== 'string' || !a.id || typeof a.title !== 'string' || a.hidden || internal.indexOf(a.id) >= 0 || seen[a.id]) return false;
      seen[a.id] = true; return true;
    }).slice(0,200).map(function(a) {
      return {id:a.id, title:a.title.slice(0,256), icon:typeof a.icon === 'string' ? a.icon : '', iconColor:a.iconColor || a.bgColor || ''};
    });
  }
  function create(storage, inventory, config) {
    var catalog = clean(inventory), hidden = unique(config.hiddenApps || []), ids, saved;
    var fixed = Array.isArray(config.homeApps) ? unique(config.homeApps) : null;
    try {
      saved = JSON.parse(storage.getItem(KEY));
      if (!saved || saved.version !== 1 || !Array.isArray(saved.ids) || !Array.isArray(saved.hidden) || !Array.isArray(saved.catalog)) saved = null;
    } catch (_) { saved = null; }
    if (saved) {
      catalog = clean(catalog.concat(saved.catalog)); hidden = unique(saved.hidden); ids = unique(saved.ids);
    } else {
      var legacy;
      try { legacy = JSON.parse(storage.getItem('tvhome.order')); } catch (_) {}
      var first = legacy && legacy.dock === (config.dockApps || []).join(',') && Array.isArray(legacy.ids) ? legacy.ids : (config.dockApps || []).slice(0, config.columns || 4);
      ids = unique(first.concat(catalog.slice().sort(function(a,b) { return a.title.localeCompare(b.title); }).map(function(a) { return a.id; })));
    }
    function visible() { return (fixed || ids).map(find).filter(function(a) { return a && (fixed !== null || hidden.indexOf(a.id) < 0); }); }
    function find(id) { return catalog.filter(function(a) { return a.id === id; })[0]; }
    function save(nextIds, nextHidden) {
      var state = {version:1, ids:unique(nextIds), hidden:unique(nextHidden), catalog:catalog};
      storage.setItem(KEY, JSON.stringify(state)); // Commit memory only after durable storage succeeds.
      ids = state.ids; hidden = state.hidden;
    }
    return {
      visible:visible,
      hidden:function() { return hidden.slice(); },
      available:function() { var shown = visible().map(function(a) { return a.id; }); return catalog.filter(function(a) { return shown.indexOf(a.id) < 0; }).sort(function(a,b) { return a.title.localeCompare(b.title); }); },
      save:save,
      add:function(id) { if (!find(id)) throw Error('app-unavailable'); save(visible().map(function(a) { return a.id; }).concat(id), hidden.filter(function(h) { return h !== id; })); },
      refresh:function(apps) {
        // TV queries can return only part of the installed inventory. Absence
        // from a response must not erase saved tiles or apps hidden from Home.
        // Preserve packaged icons when the service supplies metadata without an icon.
        var previous = catalog;
        var updates = clean(apps).map(function(a) { var old = previous.filter(function(b) { return b.id === a.id; })[0]; if (old && old.icon) a.icon = old.icon; return a; });
        catalog = clean(updates.concat(previous));
      }
    };
  }
  function installed(callback) {
    var bridge, done = false;
    var timer = setTimeout(function() { finish(null); }, 12000);
    function finish(apps) { if (done) return; done = true; clearTimeout(timer); if (bridge) try { bridge.cancel(); } catch (_) {} callback(apps); }
    try {
      bridge = new PalmServiceBridge();
      bridge.onservicecallback = function(raw) {
        try { var result = JSON.parse(raw); finish(result.returnValue === true && Array.isArray(result.apps) ? clean(result.apps) : null); } catch (_) { finish(null); }
      };
      var root = !!document.querySelector('script[src="root-settings.js"]');
      bridge.call('luna://' + (root ? 'com.cleanyourtv.root.preview.service' : 'com.local.nativehome.service') + '/listApps', '{}');
    } catch (_) { finish(null); }
  }
  return {create:create, installed:installed, key:KEY};
}));
