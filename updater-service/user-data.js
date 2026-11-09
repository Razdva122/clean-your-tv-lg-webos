(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomeData = factory();
})(this, function () {
  'use strict';
  var KEY = 'tvhome.profile.v1',
    LIMIT = 4 * 1024 * 1024;
  function validate(s) {
    if (
      !s ||
      s.schema !== 1 ||
      !s.inventory ||
      !Array.isArray(s.inventory.apps) ||
      !Array.isArray(s.inventory.inputs) ||
      !s.config ||
      typeof s.settings !== 'object' ||
      !s.settings
    )
      throw Error('invalid-profile');
    if (
      JSON.stringify(s).length > LIMIT ||
      s.inventory.apps.length > 200 ||
      s.inventory.inputs.length > 100
    )
      throw Error('profile-too-large');
    s.inventory.apps.forEach(function (a) {
      if (
        !a ||
        typeof a.id !== 'string' ||
        !a.id.length ||
        typeof a.title !== 'string' ||
        a.title.length > 256 ||
        typeof a.icon !== 'string' ||
        !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(a.icon)
      )
        throw Error('invalid-app-icon');
    });
    Object.keys(s.settings).forEach(function (k) {
      if (
        (k !== 'tvhome.order' &&
          k !== 'tvhome.layout' &&
          k !== 'tvhome.language' &&
          k !== 'tvhome.name') ||
        typeof s.settings[k] !== 'string'
      )
        throw Error('invalid-settings');
    });
    if (
      s.settings['tvhome.name'] !== undefined &&
      (!s.settings['tvhome.name'].length ||
        s.settings['tvhome.name'].replace(
          /[\ud800-\udbff][\udc00-\udfff]/g,
          'x'
        ).length > 48 ||
        /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u206f]/.test(
          s.settings['tvhome.name']
        ))
    )
      throw Error('invalid-tv-name');
    if (
      s.settings['tvhome.language'] !== undefined &&
      [
        'auto',
        'en',
        'cs',
        'de',
        'es',
        'pt-BR',
        'fr',
        'it',
        'ko',
        'hi',
        'pl',
        'ru'
      ].indexOf(s.settings['tvhome.language']) < 0
    )
      throw Error('invalid-language');
    if (
      !Number.isInteger(s.config.columns) ||
      s.config.columns < 1 ||
      s.config.columns > 8 ||
      !Array.isArray(s.config.dockApps) ||
      !Array.isArray(s.config.hiddenApps)
    )
      throw Error('invalid-config');
    if (s.renewal) {
      if (
        s.renewal.enabled !== false ||
        JSON.stringify(s.renewal).length > 4096
      )
        throw Error('disable-renewal-first');
      var allowed = ['enabled', 'last', 'lastRenewedAt', 'error'];
      if (
        Object.keys(s.renewal).some(function (k) {
          return allowed.indexOf(k) < 0;
        })
      )
        throw Error('invalid-renewal-settings');
    }
    return JSON.parse(JSON.stringify(s));
  }
  function load(storage) {
    var raw = storage.getItem(KEY);
    return raw === null ? null : validate(JSON.parse(raw));
  }
  function save(storage, s) {
    s = validate(s);
    storage.setItem(KEY, JSON.stringify(s));
    return s;
  }
  function apply(storage, s) {
    s = validate(s);
    Object.keys(s.settings).forEach(function (k) {
      storage.setItem(k, s.settings[k]);
    });
    return s;
  }
  return { key: KEY, validate: validate, load: load, save: save, apply: apply };
});
