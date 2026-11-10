/* Cosmetic post-install launch parameters. No service or Home-routing controls. */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.CYTVInstallSettings = factory(root);
})(this, function (root) {
  'use strict';
  var marker = 'tvhome.installer.settings.v1',
    names = {
      classic: 'Classic',
      'liquid-glass': 'Liquid Glass',
      ribbon: 'Ribbon'
    },
    listening = false;
  function save(key, value) {
    root.localStorage.setItem(key, value);
    if (root.localStorage.getItem(key) !== value)
      throw Error('Installation settings not saved');
  }
  function apply(params) {
    if (!params || typeof params !== 'object') return false;
    var value = params.cytvSetup;
    if (
      !value ||
      typeof value !== 'object' ||
      Array.isArray(value) ||
      typeof value.id !== 'string' ||
      !/^[a-f0-9]{32}$/.test(value.id) ||
      Object.keys(value).some(function (key) {
        return ['id', 'theme', 'weather', 'tv_name'].indexOf(key) < 0;
      }) ||
      (value.theme !== undefined &&
        ['classic', 'liquid-glass', 'ribbon'].indexOf(value.theme) < 0) ||
      (value.weather !== undefined && typeof value.weather !== 'boolean') ||
      (value.theme === 'ribbon' && value.weather === true)
    )
      return false;
    if (value.tv_name !== undefined) {
      if (!root.HomeName) return false;
      try {
        if (root.HomeName.normalize(value.tv_name) !== value.tv_name)
          return false;
      } catch (_) {
        return false;
      }
    }
    if (root.localStorage.getItem(marker) === value.id) return false;
    // These are the same app-owned preferences used by the TV settings panels.
    if (value.theme !== undefined) {
      save(
        'tvhome.theme.choice.v1',
        JSON.stringify({
          id: 'builtin:' + value.theme,
          title: names[value.theme]
        })
      );
      root.localStorage.removeItem('tvhome.theme.trial.v1');
    }
    if (value.weather !== undefined) {
      var weather = JSON.parse(
        root.localStorage.getItem('tvhome.weather.v1') || '{}'
      );
      if (!weather || typeof weather !== 'object' || Array.isArray(weather))
        throw Error('Weather preferences unavailable');
      weather.enabled = value.weather;
      if (value.weather && !weather.location) weather.mode = 'auto';
      save('tvhome.weather.v1', JSON.stringify(weather));
    }
    if (value.tv_name !== undefined) save('tvhome.name', value.tv_name);
    save(marker, value.id);
    return true;
  }
  function listen(onError) {
    if (listening) return;
    listening = true;
    function receive(event) {
      var params;
      try {
        var raw = event
          ? event.detail
          : root.PalmSystem && root.PalmSystem.launchParams;
        if (raw && raw.params) raw = raw.params;
        if (typeof raw === 'string' && raw.length > 4096) return;
        params = typeof raw === 'string' ? JSON.parse(raw) : raw;
        if (params && params.params) params = params.params;
      } catch (_) {
        return;
      }
      try {
        if (apply(params)) root.location.reload();
      } catch (_) {
        onError();
      }
    }
    root.document.addEventListener('webOSRelaunch', receive);
    receive();
  }
  return { apply: apply, listen: listen };
});
