(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.RootProfileData = factory();
})(this, function () {
  'use strict';
  var LIMIT = 4 * 1024 * 1024,
    KEY = 'tvhome.root.profile.v1';
  function bytes(value) {
    return unescape(encodeURIComponent(value)).length;
  }
  function fields(value, required, optional) {
    if (
      !value ||
      Array.isArray(value) ||
      typeof value !== 'object' ||
      required.some(function (k) {
        return !Object.prototype.hasOwnProperty.call(value, k);
      }) ||
      Object.keys(value).some(function (k) {
        return required.concat(optional || []).indexOf(k) < 0;
      })
    )
      throw Error('Invalid profile fields');
  }
  function text(value, max, empty) {
    if (
      typeof value !== 'string' ||
      (!empty && !value) ||
      value.indexOf('\0') >= 0 ||
      bytes(value) > (max || 256)
    )
      throw Error('Invalid profile text');
  }
  function ids(value) {
    if (!Array.isArray(value) || value.length > 200)
      throw Error('Invalid app IDs');
    value.forEach(function (id, i) {
      text(id);
      if (value.indexOf(id) !== i) throw Error('Duplicate app ID');
    });
  }
  function validate(value) {
    if (bytes(JSON.stringify(value)) > LIMIT)
      throw Error('Profile exceeds 4 MiB');
    fields(value, ['schema', 'inventory', 'config', 'settings']);
    if (value.schema !== 1) throw Error('Invalid profile schema');
    fields(value.inventory, ['apps', 'inputs']);
    ['apps', 'inputs'].forEach(function (key, index) {
      var entries = value.inventory[key],
        seen = [];
      if (!Array.isArray(entries) || entries.length > (index ? 100 : 200))
        throw Error('Inventory too large');
      entries.forEach(function (entry) {
        fields(
          entry,
          index ? ['appId', 'label'] : ['id', 'title', 'icon'],
          index ? [] : ['iconColor']
        );
        var id = index ? entry.appId : entry.id;
        text(id);
        text(index ? entry.label : entry.title);
        if (seen.indexOf(id) >= 0) throw Error('Duplicate inventory ID');
        seen.push(id);
        if (!index) {
          var icon = entry.icon;
          if (
            typeof icon !== 'string' ||
            bytes(icon) > 256 * 1024 ||
            !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(
              icon
            ) ||
            icon.split(',')[1].length % 4 !== 0
          )
            throw Error('Invalid embedded icon');
          if (
            entry.iconColor !== undefined &&
            (typeof entry.iconColor !== 'string' ||
              !/^#[0-9a-fA-F]{6}$/.test(entry.iconColor))
          )
            throw Error('Invalid icon color');
        }
      });
    });
    fields(value.config, ['columns', 'dockApps', 'hiddenApps'], ['liveTvApp']);
    if (
      !Number.isInteger(value.config.columns) ||
      value.config.columns < 1 ||
      value.config.columns > 8
    )
      throw Error('Invalid columns');
    ids(value.config.dockApps);
    ids(value.config.hiddenApps);
    if (value.config.liveTvApp !== undefined)
      text(value.config.liveTvApp, 256, true);
    fields(
      value.settings,
      [],
      ['tvhome.order', 'tvhome.language', 'tvhome.layout', 'tvhome.name']
    );
    if (value.settings['tvhome.name'] !== undefined) {
      text(value.settings['tvhome.name'], 192, true);
      if (
        !value.settings['tvhome.name'].length ||
        value.settings['tvhome.name'].replace(
          /[\ud800-\udbff][\udc00-\udfff]/g,
          'x'
        ).length > 48 ||
        /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u206f]/.test(
          value.settings['tvhome.name']
        )
      )
        throw Error('Invalid TV name');
    }
    if (
      value.settings['tvhome.language'] !== undefined &&
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
      ].indexOf(value.settings['tvhome.language']) < 0
    )
      throw Error('Invalid language preference');
    if (value.settings['tvhome.order'] !== undefined) {
      text(value.settings['tvhome.order'], LIMIT, true);
      var order = JSON.parse(value.settings['tvhome.order']);
      fields(order, ['dock', 'ids']);
      text(order.dock, 65536, true);
      ids(order.ids);
    }
    if (value.settings['tvhome.layout'] !== undefined) {
      text(value.settings['tvhome.layout'], LIMIT, true);
      var layout = JSON.parse(value.settings['tvhome.layout']);
      fields(layout, ['version', 'ids', 'hidden', 'catalog'], ['showAddApp']);
      if (
        layout.showAddApp !== undefined &&
        typeof layout.showAddApp !== 'boolean'
      )
        throw Error('Invalid Add app visibility');
      if (
        layout.version !== 1 ||
        !Array.isArray(layout.catalog) ||
        layout.catalog.length > 200
      )
        throw Error('Invalid profile fields');
      ids(layout.ids);
      ids(layout.hidden);
      var seen = [];
      layout.catalog.forEach(function (app) {
        fields(app, ['id', 'title', 'icon'], ['iconColor']);
        text(app.id);
        text(app.title);
        text(app.icon, 256 * 1024, true);
        if (app.iconColor !== undefined) text(app.iconColor, 256, true);
        if (seen.indexOf(app.id) >= 0) throw Error('Duplicate inventory ID');
        seen.push(app.id);
      });
    }
    return JSON.parse(JSON.stringify(value));
  }
  return { key: KEY, validate: validate };
});
