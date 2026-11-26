/* Device-local System update snapshot for the Home origin's own settings and stores. */
(function (root) {
  'use strict';
  var limit = 3 * 1024 * 1024,
    sizeMessage =
      'The backup is too large. To update, remove a downloaded theme or personal wallpaper you no longer need.',
    trialMessage = 'Finish or cancel your theme preview before updating.';
  var keys = [
    'tvhome.clockFormat',
    'tvhome.columns.v1',
    'tvhome.inputs.preview.v1',
    'tvhome.installer.settings.v1',
    'tvhome.language',
    'tvhome.layout',
    'tvhome.name',
    'tvhome.no-root-connection.v1',
    'tvhome.order',
    'tvhome.theme.choice.v1',
    'tvhome.usage.v1',
    'tvhome.wallpaper.preferences.v1',
    'tvhome.weather.v1'
  ];
  function fail() {
    throw Error('Invalid system update backup');
  }
  function tooLarge() {
    throw Error(sizeMessage);
  }
  function bytes(value) {
    return unescape(encodeURIComponent(value)).length;
  }
  function object(v) {
    return v && typeof v === 'object' && !Array.isArray(v);
  }
  function fields(v, names) {
    var required = names.split(' ');
    if (
      !object(v) ||
      Object.keys(v).length !== required.length ||
      required.some(function (key) {
        return !Object.prototype.hasOwnProperty.call(v, key);
      })
    )
      fail();
  }
  function checkEnvelopeBudget(value, budget, depth) {
    if (budget < 0) tooLarge();
    if (typeof value === 'string') {
      if (value.length > budget) tooLarge();
      return budget - value.length;
    }
    if (
      value === null ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    )
      return budget;
    if (depth > 5 || typeof value !== 'object') fail();
    var names = Object.keys(value);
    if (names.length > 128) fail();
    names.forEach(function (key) {
      budget = checkEnvelopeBudget(value[key], budget - key.length, depth + 1);
    });
    return budget;
  }
  function equal(a, b) {
    function sorted(k, v) {
      if (!object(v)) return v;
      var out = Object.create(null);
      Object.keys(v)
        .sort()
        .forEach(function (key) {
          out[key] = v[key];
        });
      return out;
    }
    return JSON.stringify(a, sorted) === JSON.stringify(b, sorted);
  }
  function local() {
    var state = {};
    keys.forEach(function (key) {
      var v = root.localStorage.getItem(key);
      if (v !== null) state[key] = v;
    });
    validateLocal(state);
    return state;
  }
  function validateLocal(state) {
    if (!object(state)) fail();
    Object.keys(state).forEach(function (key) {
      var v = state[key];
      if (keys.indexOf(key) < 0 || typeof v !== 'string') fail();
      if (bytes(v) > (key === 'tvhome.layout' ? 1024 * 1024 : 65536))
        tooLarge();
    });
  }
  function base64(value, budget) {
    if (
      !(value instanceof Uint8Array || value instanceof ArrayBuffer) ||
      !value.byteLength
    )
      fail();
    if (value.byteLength > budget) tooLarge();
    var a = new Uint8Array(value),
      raw = '';
    for (var i = 0; i < a.length; i += 2048)
      raw += String.fromCharCode.apply(null, a.subarray(i, i + 2048));
    return root.btoa(raw);
  }
  function theme(pack, budget) {
    var out = {
      digest: pack.digest,
      descriptor: base64(pack.descriptor, Math.min(budget, 65536)),
      files: {}
    };
    budget -= out.descriptor.length;
    var names = Object.keys(pack.files);
    if (names.length > 128) fail();
    names.forEach(function (name) {
      root.ThemeData.path(name);
      if (['__proto__', 'prototype', 'constructor'].indexOf(name) >= 0) fail();
      out.files[name] = base64(pack.files[name], Math.floor((budget * 3) / 4));
      budget -= out.files[name].length;
    });
    return out;
  }
  function version() {
    return root.ThemeData.request('appinfo.json', 65536, true).then(
      function (raw) {
        var app = JSON.parse(root.ThemeData.decode(raw));
        return app.themeEngineVersion || app.version;
      }
    );
  }
  function inspect(state, homeVersion) {
    fields(state, 'schema local themes wallpapers');
    if (
      state.schema !== 1 ||
      bytes(JSON.stringify(state)) > limit ||
      !Array.isArray(state.themes) ||
      state.themes.length > 8 ||
      !Array.isArray(state.wallpapers) ||
      state.wallpapers.length > 8
    )
      fail();
    validateLocal(state.local);
    var selection = Object.prototype.hasOwnProperty.call(
      state.local,
      'tvhome.theme.choice.v1'
    )
      ? JSON.parse(state.local['tvhome.theme.choice.v1'])
      : null;
    var selectedFound = false;
    var seen = [],
      packs = state.themes.map(function (item) {
        fields(item, 'descriptor digest files');
        if (
          seen.indexOf(item.digest) >= 0 ||
          !object(item.files) ||
          Object.keys(item.files).length > 128
        )
          fail();
        seen.push(item.digest);
        var pack = root.ThemeData.unpackEnvelope(
          { schemaVersion: 1, descriptor: item.descriptor, files: item.files },
          homeVersion
        );
        if (pack.digest !== item.digest) fail();
        var parsed = root.ThemeData.verify(pack, homeVersion);
        pack.size = parsed.size;
        if (
          selection &&
          selection.id === parsed.manifest.id &&
          selection.digest === pack.digest
        )
          selectedFound = true;
        return pack;
      });
    if (
      selection &&
      (typeof selection.id !== 'string' ||
        (selection.id.indexOf('github:') === 0 && !selectedFound))
    )
      fail();
    root.PersonalWallpaper.validateProfileRecords(state.wallpapers);
    return packs;
  }
  function read() {
    var state = { schema: 1, local: local(), themes: [], wallpapers: [] };
    var budget = limit - bytes(JSON.stringify(state));
    function add(list, value) {
      budget -= bytes(JSON.stringify(value)) + 1;
      if (list.length >= 8 || budget < 0) tooLarge();
      list.push(value);
    }
    return root.ThemeStore.readProfileRecords(function (key, pack) {
      if (key !== pack.digest) fail();
      add(state.themes, theme(pack, budget));
    })
      .then(function () {
        return root.PersonalWallpaper.readProfileRecords(function (key, value) {
          // Reject large stored videos before allocating a second serialized copy.
          checkEnvelopeBudget(value, budget, 0);
          add(state.wallpapers, { key: key, value: value });
        });
      })
      .then(function () {
        return state;
      });
  }
  function capture() {
    return Promise.resolve()
      .then(function () {
        if (root.localStorage.getItem('tvhome.theme.trial.v1') !== null)
          throw Error(trialMessage);
        return read();
      })
      .then(function (state) {
        return (state.themes.length ? version() : Promise.resolve(null)).then(
          function (v) {
            inspect(state, v);
            return state;
          }
        );
      })
      .catch(function (error) {
        if (error.message === sizeMessage || error.message === trialMessage)
          throw error;
        throw Error(
          'Could not save your complete profile. Nothing was installed.'
        );
      });
  }
  function restore(state) {
    return (
      state && Array.isArray(state.themes) && state.themes.length
        ? version()
        : Promise.resolve(null)
    )
      .then(function (v) {
        var packs = inspect(state, v);
        return root.ThemeStore.replaceProfileRecords(packs);
      })
      .then(function () {
        return root.PersonalWallpaper.replaceProfileRecords(state.wallpapers);
      })
      .then(function () {
        keys.forEach(function (key) {
          if (Object.prototype.hasOwnProperty.call(state.local, key))
            root.localStorage.setItem(key, state.local[key]);
          else root.localStorage.removeItem(key);
        });
        root.localStorage.removeItem('tvhome.theme.trial.v1');
        return verify(state);
      });
  }
  function verify(state) {
    return read().then(function (actual) {
      if (!equal(actual, state)) throw Error('Local profile readback failed');
    });
  }
  function resume(restored, id, marker, data, saved) {
    var profile = {},
      state = restored.profile.browserState;
    Object.keys(restored.profile).forEach(function (key) {
      if (key !== 'browserState') profile[key] = restored.profile[key];
    });
    profile = data.validate(profile);
    if (!state) throw Error('Invalid system update backup');
    if (saved && root.localStorage.getItem(marker) === id) {
      var pending =
        ['verifying', 'verifying-rollback'].indexOf(restored.phase) >= 0;
      return (pending ? verify(state) : Promise.resolve()).then(function () {
        return saved;
      });
    }
    return restore(state).then(function () {
      var raw = JSON.stringify(profile);
      root.localStorage.setItem(data.key, raw);
      if (root.localStorage.getItem(data.key) !== raw)
        throw Error('Local profile readback failed');
      root.localStorage.setItem(marker, id);
      if (root.localStorage.getItem(marker) !== id)
        throw Error('Local profile readback failed');
      // Settings modules may have initialized against empty storage before the backup arrived.
      root.location.reload();
      return null;
    });
  }
  root.HomeBrowserProfile = {
    capture: capture,
    restore: restore,
    resume: resume
  };
})(this);
