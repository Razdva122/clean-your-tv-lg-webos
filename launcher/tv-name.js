/* Shared, upgrade-safe launcher naming. Never changes system metadata or permissions. */
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
        storage.setItem(KEY, value); // Failed saves leave the accepted value intact.
        return value;
      }
    };
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
        'Saves the launcher name. Apply the same name through the installer to change LG’s startup screen.'
      );
      label.textContent = t('TV name');
      save.textContent = t('Save name');
      reset.textContent = t('Reset to Home');
      description.textContent = t(
        'Saves the launcher name. Apply the same name through the installer to change LG’s startup screen.'
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
        status.textContent = t('TV name saved.');
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
    create: create,
    refresh: refresh,
    mountSettings: mountSettings
  };
});
