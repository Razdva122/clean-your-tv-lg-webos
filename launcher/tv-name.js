/* Upgrade-safe names and verified primary launch-point title updates. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomeName = factory(root);
})(this, function (root) {
  'use strict';
  var KEY = 'tvhome.name';
  function normalize(value) {
    if (typeof value !== 'string') throw Error('Invalid TV name');
    value = value.replace(/^\s+|\s+$/g, '') || 'Home';
    if (value.normalize) value = value.normalize('NFC');
    var pairs = /[\ud800-\udbff][\udc00-\udfff]/g;
    if (
      value.replace(pairs, 'x').length > 48 ||
      /[\u0000-\u001f\u007f-\u009f\u00ad\u061c\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]/.test(
        value
      ) ||
      /[\ud800-\udfff]/.test(value.replace(pairs, ''))
    )
      throw Error('Invalid TV name');
    return value;
  }
  function create(storage, seed) {
    var initial;
    try {
      initial = normalize(seed || 'Home');
    } catch (_) {
      initial = 'Home';
    }
    function get() {
      try {
        var saved = storage.getItem(KEY);
        return saved === null ? initial : normalize(saved);
      } catch (_) {
        return initial;
      }
    }
    // A legacy installation has no name key. Do not touch its other settings.
    try {
      if (storage.getItem(KEY) === null) storage.setItem(KEY, initial);
    } catch (_) {}
    return {
      get: get,
      set: function (value) {
        value = normalize(value);
        storage.setItem(KEY, value);
        if (storage.getItem(KEY) !== value) throw Error('Name not saved');
        return value;
      }
    };
  }
  function primary(reply, app) {
    if (
      !reply ||
      reply.returnValue !== true ||
      !Array.isArray(reply.launchPoints) ||
      reply.launchPoints.length > 300
    )
      return null;
    var matches = reply.launchPoints.filter(function (point) {
      return (
        point &&
        point.id === app &&
        typeof point.launchPointId === 'string' &&
        point.launchPointId.length > 0 &&
        point.launchPointId.length <= 256 &&
        (point.launchPointId === app ||
          point.launchPointId === app + '_default' ||
          point.default === true ||
          point.type === 'default')
      );
    });
    return matches.length === 1 && typeof matches[0].title === 'string'
      ? matches[0]
      : null;
  }
  function rename(call, app, value, done) {
    value = normalize(value);
    var uri = 'luna://com.webos.applicationManager/';
    call(uri + 'listLaunchPoints', {}, function (reply) {
      var before = primary(reply, app);
      if (!before) {
        done(false);
        return;
      }
      function verify() {
        call(uri + 'listLaunchPoints', {}, function (result) {
          var after = primary(result, app);
          done(
            !!after &&
              after.launchPointId === before.launchPointId &&
              after.title === value
          );
        });
      }
      if (before.title === value) {
        verify();
        return;
      }
      call(
        uri + 'updateLaunchPoint',
        { launchPointId: before.launchPointId, title: value },
        function (result) {
          if (!result || result.returnValue !== true) {
            done(false);
            return;
          }
          verify();
        }
      );
    });
  }
  function callSystem(uri, payload, done) {
    var bridge,
      finished = false,
      timer;
    function finish(reply) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (bridge)
        try {
          bridge.cancel();
        } catch (_) {}
      done(reply);
    }
    timer = setTimeout(function () {
      finish(null);
    }, 8000);
    try {
      bridge = new root.PalmServiceBridge();
      bridge.onservicecallback = function (raw) {
        var reply;
        try {
          reply = JSON.parse(raw);
        } catch (_) {
          reply = null;
        }
        finish(reply);
      };
      bridge.call(uri, JSON.stringify(payload));
    } catch (_) {
      finish(null);
    }
  }
  var storage;
  if (root)
    try {
      storage = root.localStorage;
    } catch (_) {}
  var model = root ? create(storage, root.CYTV_TV_NAME || 'Home') : null;
  function t(text) {
    return root.HomeI18n ? root.HomeI18n.t(text) : text;
  }
  function refresh() {
    var name = model.get();
    root.document.title = name;
    return name;
  }
  function mountSettings(groups) {
    var group =
      groups.filter(function (item) {
        return item.id === 'home';
      })[0] || groups[0];
    if (!group) return;
    var document = root.document,
      box = document.createElement('div'),
      label = document.createElement('label'),
      input = document.createElement('input'),
      save = document.createElement('button'),
      reset = document.createElement('button'),
      description = document.createElement('p'),
      status = document.createElement('p');
    box.className = 'tv-name-settings';
    label.htmlFor = input.id = 'homeTvName';
    input.type = 'text';
    input.maxLength = 96;
    input.value = model.get();
    save.type = reset.type = 'button';
    status.setAttribute('role', 'status');
    function labels() {
      label.setAttribute('data-i18n', 'TV name');
      save.setAttribute('data-i18n', 'Save name');
      reset.setAttribute('data-i18n', 'Reset to Home');
      description.setAttribute(
        'data-i18n',
        'Saves the Home name and tries to update the existing LG launcher title without reinstalling.'
      );
      label.textContent = t('TV name');
      save.textContent = t('Save name');
      reset.textContent = t('Reset to Home');
      description.textContent = t(
        'Saves the Home name and tries to update the existing LG launcher title without reinstalling.'
      );
    }
    function commit(value) {
      try {
        value = normalize(value);
      } catch (_) {
        status.textContent = t(
          'Use up to 48 characters without control characters.'
        );
        return;
      }
      try {
        input.value = model.set(value);
        refresh();
        save.disabled = reset.disabled = true;
        var app = document.querySelector('script[src="root-settings.js"]')
          ? 'com.cleanyourtv.root.preview'
          : 'com.gathin.tvhome';
        rename(callSystem, app, value, function (verified) {
          save.disabled = reset.disabled = false;
          status.textContent = t(
            verified
              ? 'TV name saved.'
              : 'Name saved in Home. LG startup title could not be verified.'
          );
        });
      } catch (_) {
        status.textContent = t(
          'Could not save TV name. Check available storage and try again.'
        );
      }
    }
    save.onclick = function () {
      commit(input.value);
    };
    reset.onclick = function () {
      commit('Home');
    };
    [label, input, save, reset, description, status].forEach(
      function (element) {
        box.appendChild(element);
      }
    );
    labels();
    group.elements.push(box);
  }
  if (root && root.document) {
    refresh();
  }
  return {
    key: KEY,
    normalize: normalize,
    primary: primary,
    rename: rename,
    create: create,
    refresh: refresh,
    mountSettings: mountSettings
  };
});
