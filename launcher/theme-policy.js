/* Theme API 1: the only serializer permitted to turn external typed data into CSS. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();else root.ThemePolicy = factory();
})(this, function () {
  'use strict';

  var parts = ['home', 'ambient', 'hero', 'header', 'greeting', 'clock', 'period', 'divider', 'date', 'shortcut', 'input-icon', 'network-icon', 'settings-icon', 'dock', 'position', 'focus', 'card', 'icon', 'label', 'library', 'library-panel', 'library-close', 'library-row', 'inputs', 'input-row'];
  var states = ['focused', 'selected', 'moving', 'glyph', 'light', 'dark', 'mid', 'bright', 'wide'];
  var properties = {
    'color': 'color',
    'background-color': 'color',
    'border-color': 'color',
    'outline-color': 'color',
    'background-image': 'image',
    'border-radius': 'length',
    'border-width': 'length',
    'border-style': 'borderStyle',
    'box-shadow': 'shadow',
    'text-shadow': 'textShadow',
    'font-family': 'font',
    'font-size': 'fontSize',
    'font-weight': 'weight',
    'font-style': 'fontStyle',
    'text-transform': 'textTransform',
    'text-decoration': 'textDecoration',
    'letter-spacing': 'length',
    'transition': 'transition',
    'filter': 'filter',
    'mix-blend-mode': 'blendMode',
    'isolation': 'isolation',
    'overflow': 'overflow',
    'transform': 'iconScale'
  };
  var limits = {
    rules: 512,
    declarations: 4096,
    bundleBytes: 131072,
    emittedCssBytes: 262144,
    sourceBytes: 131072,
    variableExpansionBytes: 131072,
    variableExpansionWork: 262144,
    descriptorBytes: 65536,
    assets: 16,
    assetBytes: 2097152,
    totalAssetBytes: 6291456
  };
  // Kept in sync across the standalone HomeLayout and ThemePolicy browser modules.
  function normalizeRibbon(input) {
    var defaults = {left: 112, right: 112, bottom: 162, cardHeight: 128, gap: 24, skewDeg: 0, focusLift: 0, iconScale: 1,
      shortcuts: 'header', edgeNavigation: 'wrap', labels: 'below', showClock: true};
    var bounds = {left: [64, 640], right: [32, 320], bottom: [0, 200], cardHeight: [96, 240], gap: [0, 64], skewDeg: [-18, 18], focusLift: [0, 64], iconScale: [.4, 1]};
    if (!input || typeof input !== 'object' || Array.isArray(input) ||
        Object.getPrototypeOf(input) !== Object.prototype && Object.getPrototypeOf(input) !== null) fail('layout-invalid', 'ribbon');
    Object.keys(input).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(defaults, key)) fail('layout-invalid', 'ribbon');
      var value = input[key], range = bounds[key];
      if (range) {
        if (typeof value !== 'number' || !isFinite(value) || value < range[0] || value > range[1] || key !== 'skewDeg' && key !== 'iconScale' && value % 1) fail('layout-invalid', 'ribbon');
      } else if (key === 'showClock') {
        if (typeof value !== 'boolean') fail('layout-invalid', 'ribbon');
      } else if ((key === 'shortcuts' ? ['header', 'bottom-left'] : key === 'edgeNavigation' ? ['wrap', 'shortcuts'] : ['below', 'focused-above']).indexOf(value) < 0) fail('layout-invalid', 'ribbon');
      defaults[key] = value;
    });
    if (defaults.shortcuts === 'bottom-left' && defaults.left < 340) fail('layout-invalid', 'ribbon');
    if (defaults.labels === 'below' && defaults.bottom < 64) fail('layout-invalid', 'ribbon');
    return defaults;
  }
  function ribbonWidth(ribbon, columns) {
    var margin = Math.abs(Math.tan(ribbon.skewDeg * Math.PI / 180) * (ribbon.cardHeight + ribbon.focusLift));
    var width = 1920 - ribbon.left - ribbon.right - 2 * margin;
    if (Math.min(360, width / columns - ribbon.gap) < 64) fail('layout-invalid', 'ribbon');
    return width;
  }
  function fail(code, field) {
    var e = new Error(code + ': invalid ' + field);
    e.name = 'ThemeError';
    e.code = code;
    e.field = field;
    throw e;
  }
  function object(x, keys, code, field, optional) {
    if (!x || typeof x !== 'object' || Array.isArray(x) || Object.getPrototypeOf(x) !== Object.prototype && Object.getPrototypeOf(x) !== null) fail(code, field);
    Object.keys(x).forEach(function (k) {
      if ((keys.indexOf(k) < 0 && (!optional || optional.indexOf(k) < 0)) || k === 'constructor' || k === '__proto__' || k === 'prototype') fail(code, field);
    });
    keys.forEach(function (k) {
      if (!Object.prototype.hasOwnProperty.call(x, k)) fail(code, field + '.' + k);
    });
  }
  function number(n, min, max, code, field) {
    if (typeof n !== 'number' || !isFinite(n) || n < min || n > max) fail(code, field);
    return n;
  }
  function string(x, max, code, field) {
    if (typeof x !== 'string' || !x.length || x.length > max || /[\u0000-\u001f\u007f]/.test(x)) fail(code, field);
    return x;
  }
  function list(x, max, code, field) {
    if (!Array.isArray(x) || x.length > max) fail(code, field);
    return x;
  }
  function bytes(x) {
    return unescape(encodeURIComponent(JSON.stringify(x))).length;
  }
  function path(x) {
    string(x, 160, 'asset-invalid', 'path');
    if (!/^[a-zA-Z0-9_-]+(?:[./-][a-zA-Z0-9_-]+)*$/.test(x) || /(^|\/)\.\.?($|\/)/.test(x)) fail('asset-invalid', 'path');
    return x;
  }
  function id(x) {
    if (typeof x !== 'string' || !/^(?:builtin:[a-z0-9][a-z0-9-]{0,63}|github:[a-z0-9][a-z0-9-]*\/[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9-]{0,63})$/.test(x)) fail('manifest-invalid', 'id');
    return x;
  }
  function repository(x) {
    if (typeof x !== 'string' || !/^https:\/\/github\.com\/[a-zA-Z0-9][a-zA-Z0-9-]*\/[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(x)) fail('manifest-invalid', 'repository');
    return x;
  }
  function version(x) {
    if (typeof x !== 'string' || !/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(x) || x.length > 64) fail('manifest-invalid', 'version');
  }
  function file(x, max, extra) {
    object(x, ['path', 'size', 'sha256'].concat(extra || []), 'asset-invalid', 'file');
    path(x.path);
    number(x.size, 1, max, 'asset-invalid', 'size');
    if (x.size % 1 || typeof x.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(x.sha256)) fail('asset-invalid', 'hash');
  }
  function validateManifest(m) {
    object(m, ['schemaVersion', 'themeApiVersion', 'id', 'title', 'description', 'author', 'themeVersion', 'source', 'requires', 'layout', 'defaults', 'rules', 'assets', 'documents', 'previewAssetId', 'license'], 'manifest-invalid', 'manifest');
    if (bytes(m) > limits.descriptorBytes) fail('manifest-invalid', 'size');
    if (m.schemaVersion !== 1) fail('manifest-invalid', 'schemaVersion');
    if (m.themeApiVersion !== 1) fail('api-unsupported', 'themeApiVersion');
    id(m.id);
    string(m.title, 100, 'manifest-invalid', 'title');
    string(m.description, 1000, 'manifest-invalid', 'description');
    version(m.themeVersion);
    object(m.author, ['name', 'url'], 'manifest-invalid', 'author');
    string(m.author.name, 100, 'manifest-invalid', 'author.name');
    string(m.author.url, 250, 'manifest-invalid', 'author.url');
    if (!/^https:\/\/[^\s<>"\\]+$/.test(m.author.url)) fail('manifest-invalid', 'author.url');
    object(m.source, ['repository', 'commit'], 'manifest-invalid', 'source');
    repository(m.source.repository);
    if (typeof m.source.commit !== 'string' || !/^[a-f0-9]{40}$/.test(m.source.commit)) fail('manifest-invalid', 'commit');
    if (m.id.indexOf('github:') === 0 && m.id.split(':')[1] !== m.source.repository.slice(19).toLowerCase()) fail('manifest-invalid', 'source.identity');
    object(m.requires, ['minimumHomeVersion', 'capabilities'], 'manifest-invalid', 'requires');
    version(m.requires.minimumHomeVersion);
    list(m.requires.capabilities, 2, 'api-unsupported', 'capabilities').forEach(function (capability, index) { if (['modern-icon-css-v1', 'ribbon-layout-v1'].indexOf(capability) < 0 || m.requires.capabilities.indexOf(capability) !== index) fail('api-unsupported', 'capabilities'); });
    object(m.layout, ['preset', 'columns', 'spacingScale', 'textScale', 'focusScale'], 'layout-invalid', 'layout', ['allowColumnOverride', 'ribbon']);
    if (['dock-grid', 'icon-grid', 'side-grid', 'channel-list', 'scenic-grid'].indexOf(m.layout.preset) < 0) fail('layout-invalid', 'preset');
    if (Object.prototype.hasOwnProperty.call(m.layout, 'allowColumnOverride') && typeof m.layout.allowColumnOverride !== 'boolean') fail('layout-invalid', 'allowColumnOverride');
    number(m.layout.columns, 1, 8, 'layout-invalid', 'columns');
    if (m.layout.columns % 1) fail('layout-invalid', 'columns');
    number(m.layout.spacingScale, .8, 1.2, 'layout-invalid', 'spacingScale');
    number(m.layout.textScale, .9, 1.25, 'layout-invalid', 'textScale');
    number(m.layout.focusScale, 1.05, 1.15, 'layout-invalid', 'focusScale');
    var hasRibbon = Object.prototype.hasOwnProperty.call(m.layout, 'ribbon'), normalizedRibbon;
    if (hasRibbon !== (m.requires.capabilities.indexOf('ribbon-layout-v1') >= 0)) fail('api-unsupported', 'ribbon-layout-v1');
    if (hasRibbon) {
      if (m.layout.preset !== 'scenic-grid' || m.layout.allowColumnOverride !== false) fail('layout-invalid', 'ribbon');
      normalizedRibbon = normalizeRibbon(m.layout.ribbon);
      ribbonWidth(normalizedRibbon, m.layout.columns);
    }
    object(m.defaults, ['wallpaperAssetId', 'dim', 'accent'], 'manifest-invalid', 'defaults');
    number(m.defaults.dim, 0, .85, 'manifest-invalid', 'dim');
    if (typeof m.defaults.accent !== 'string' || !/^#[a-fA-F0-9]{6}$/.test(m.defaults.accent)) fail('manifest-invalid', 'accent');
    file(m.rules, limits.bundleBytes);
    if (!/\.json$/.test(m.rules.path)) fail('asset-invalid', 'rules.path');
    var seen = Object.create(null),
      paths = Object.create(null),
      total = 0;
    paths[m.rules.path] = true;
    list(m.assets, limits.assets, 'asset-invalid', 'assets').forEach(function (a) {
      file(a, limits.assetBytes, ['id', 'mediaType', 'width', 'height']);
      if (typeof a.id !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(a.id) || seen[a.id] || paths[a.path]) fail('asset-invalid', 'asset.id');
      seen[a.id] = a;
      paths[a.path] = true;
      if (['image/png', 'image/jpeg', 'image/webp'].indexOf(a.mediaType) < 0) fail('asset-invalid', 'mediaType');
      var extension = {
        'image/png': /\.png$/i,
        'image/jpeg': /\.jpe?g$/i,
        'image/webp': /\.webp$/i
      };
      if (!extension[a.mediaType].test(a.path)) fail('asset-invalid', 'asset.path');
      number(a.width, 1, a.id === m.defaults.wallpaperAssetId ? 3840 : 1920, 'asset-invalid', 'width');
      number(a.height, 1, a.id === m.defaults.wallpaperAssetId ? 2160 : 1080, 'asset-invalid', 'height');
      if (a.width % 1 || a.height % 1) fail('asset-invalid', 'dimensions');
      total += a.size;
    });
    if (total > limits.totalAssetBytes) fail('asset-invalid', 'total');
    if (typeof m.previewAssetId !== 'string' || m.defaults.wallpaperAssetId !== null && typeof m.defaults.wallpaperAssetId !== 'string') fail('asset-invalid', 'assetId');
    var preview = seen[m.previewAssetId];
    if (!preview || preview.width > 960 || preview.height > 540 || preview.size > 307200) fail('asset-invalid', 'previewAssetId');
    if (m.defaults.wallpaperAssetId !== null && !seen[m.defaults.wallpaperAssetId]) fail('asset-invalid', 'wallpaperAssetId');
    var docs = Object.create(null);
    list(m.documents, 2, 'asset-invalid', 'documents').forEach(function (d) {
      file(d, 32768);
      if (!/\.txt$/i.test(d.path)) fail('asset-invalid', 'documents.path');
      if (paths[d.path]) fail('asset-invalid', 'documents.path');
      paths[d.path] = true;
      docs[d.path] = true;
    });
    object(m.license, ['identifier', 'textPath', 'creditsPath'], 'manifest-invalid', 'license');
    string(m.license.identifier, 100, 'manifest-invalid', 'license.identifier');
    if (!docs[m.license.textPath] || !docs[m.license.creditsPath]) fail('asset-invalid', 'license.documents');
    var result = JSON.parse(JSON.stringify(m));
    if (hasRibbon) result.layout.ribbon = normalizedRibbon;
    return result;
  }
  function decimal(n) {
    return n.toFixed(6).replace(/\.?0+$/, '') || '0';
  }
  function color(v) {
    object(v, ['type', 'rgba'], 'css-value', 'color');
    if (v.type !== 'color') fail('css-value', 'color.type');
    list(v.rgba, 4, 'css-value', 'rgba');
    if (v.rgba.length !== 4) fail('css-value', 'rgba');
    v.rgba.forEach(function (n, i) {
      number(n, 0, i === 3 ? 1 : 255, 'css-value', 'rgba');
      if (i < 3 && n % 1) fail('css-value', 'rgba');
    });
    return 'rgba(' + v.rgba.map(decimal).join(',') + ')';
  }
  function length(v, min, max) {
    object(v, ['type', 'value', 'unit'], 'css-value', 'length');
    if (v.type !== 'length' || v.unit !== 'px') fail('css-value', 'length');
    return decimal(number(v.value, min, max, 'css-value', 'length')) + 'px';
  }
  function value(v, family, handles) {
    if (!v || typeof v !== 'object') fail('css-value', 'value');
    if (family === 'color' && v.type === 'color') return color(v);
    if (family === 'iconScale' && v.type === 'scale') { object(v, ['type', 'amount'], 'css-value', 'icon scale'); return 'scale(' + decimal(number(v.amount, 1, 2, 'css-value', 'icon scale')) + ')'; }
    if (family === 'fontSize' && v.type === 'length') return length(v, 22, 176);
    if (family === 'length' && v.type === 'length') return length(v, 0, 32);
    if (family === 'image' && v.type === 'asset') {
      object(v, ['type', 'id'], 'css-value', 'asset');
      if (typeof v.id !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(v.id)) fail('css-value', 'asset.id');
      if (!handles) return '';
      if (!Object.prototype.hasOwnProperty.call(handles, v.id)) fail('asset-invalid', 'asset.handle');
      var h = handles[v.id];
      if (typeof h === 'string' && h.length > limits.emittedCssBytes) fail('css-budget', 'asset.handle bytes');
      if (typeof h !== 'string' || !/^(?:blob:[a-zA-Z0-9:/._-]+|data:image\/(?:png|jpeg|webp);base64,[a-zA-Z0-9+/=]+)$/.test(h)) fail('asset-invalid', 'asset.handle');
      return 'url("' + h + '")';
    }
    if (family === 'image' && v.type === 'gradient') {
      object(v, ['type', 'angle', 'stops'], 'css-value', 'gradient');
      number(v.angle, 0, 360, 'css-value', 'angle');
      list(v.stops, 8, 'css-value', 'stops');
      if (v.stops.length < 2) fail('css-value', 'stops');
      var last = -1;
      return 'linear-gradient(' + decimal(v.angle) + 'deg,' + v.stops.map(function (s) {
        object(s, ['color', 'position'], 'css-value', 'stop');
        number(s.position, 0, 100, 'css-value', 'position');
        if (s.position < last) fail('css-value', 'position');
        last = s.position;
        return color(s.color) + ' ' + decimal(s.position) + '%';
      }).join(',') + ')';
    }
    if ((family === 'shadow' || family === 'textShadow') && v.type === 'shadow') {
      object(v, ['type', 'items'], 'css-value', 'shadow');
      list(v.items, 3, 'css-value', 'shadow');
      if (!v.items.length) fail('css-value', 'shadow');
      return v.items.map(function (s) {
        object(s, ['x', 'y', 'blur', 'spread', 'color'], 'css-value', 'shadow');
        return decimal(number(s.x, -24, 24, 'css-value', 'x')) + 'px ' + decimal(number(s.y, -24, 24, 'css-value', 'y')) + 'px ' + decimal(number(s.blur, 0, 40, 'css-value', 'blur')) + 'px ' + (family === 'textShadow' ? (number(s.spread, 0, 0, 'css-value', 'spread'), '') : decimal(number(s.spread, 0, 8, 'css-value', 'spread')) + 'px ') + color(s.color);
      }).join(',');
    }
    if (family === 'filter' && v.type === 'filter') {
      object(v, ['type', 'functions'], 'css-value', 'filter');
      list(v.functions, 4, 'css-value', 'filter.functions');
      if (!v.functions.length) return 'none';
      return v.functions.map(function (f) {
        object(f, ['name', 'amount'], 'css-value', 'filter.function');
        if (['grayscale', 'invert', 'brightness', 'contrast'].indexOf(f.name) < 0) fail('css-value', 'filter.name');
        return f.name + '(' + decimal(number(f.amount, 0, f.name === 'contrast' ? 10 : f.name === 'brightness' ? 2 : 1, 'css-value', 'filter.amount')) + ')';
      }).join(' ');
    }
    if (family === 'transition' && v.type === 'transition') {
      object(v, ['type', 'property', 'duration', 'easing'], 'css-value', 'transition');
      if (['color', 'background-color', 'border-color', 'box-shadow'].indexOf(v.property) < 0 || ['ease', 'linear', 'ease-in', 'ease-out', 'ease-in-out'].indexOf(v.easing) < 0) fail('css-value', 'transition');
      return v.property + ' ' + decimal(number(v.duration, 0, 500, 'css-value', 'duration')) + 'ms ' + v.easing;
    }
    var keywords = {
      borderStyle: ['solid', 'none'],
      blendMode: ['normal', 'screen'],
      isolation: ['auto', 'isolate'],
      overflow: ['hidden', 'visible'],
      font: ['sans-serif', 'serif', 'monospace'],
      weight: ['400', '500', '600', '700'],
      fontStyle: ['normal', 'italic'],
      textTransform: ['none', 'uppercase', 'lowercase', 'capitalize'],
      textDecoration: ['none', 'underline']
    };
    if (v.type === 'keyword' && keywords[family]) {
      object(v, ['type', 'value'], 'css-value', 'keyword');
      if (keywords[family].indexOf(v.value) < 0) fail('css-value', 'keyword');
      return v.value;
    }
    fail('css-value', 'type');
  }
  function validateRules(b) {
    object(b, ['schemaVersion', 'rules'], 'css-value', 'bundle');
    if (b.schemaVersion !== 1) fail('api-unsupported', 'rules.schemaVersion');
    if (bytes(b) > limits.bundleBytes) fail('css-budget', 'bytes');
    var count = 0;
    list(b.rules, limits.rules, 'css-budget', 'rules').forEach(function (r) {
      object(r, ['selector', 'declarations'], 'css-selector', 'rule');
      list(r.selector, 3, 'css-selector', 'selector');
      if (!r.selector.length) fail('css-selector', 'selector');
      r.selector.forEach(function (s) {
        object(s, ['part', 'states'], 'css-selector', 'selector');
        if (parts.indexOf(s.part) < 0) fail('css-selector', 'part');
        var used = {};
        list(s.states, 3, 'css-selector', 'states').forEach(function (t) {
          if (states.indexOf(t) < 0 || used[t]) fail('css-selector', 'states');
          used[t] = true;
        });
      });
      var props = {};
      list(r.declarations, 64, 'css-budget', 'declarations').forEach(function (d) {
        object(d, ['property', 'value'], 'css-property', 'declaration');
        if (!Object.prototype.hasOwnProperty.call(properties, d.property) || props[d.property]) fail('css-property', 'property');
        if ((d.property === 'filter' || d.property === 'mix-blend-mode') && r.selector[r.selector.length - 1].part !== 'icon') fail('css-property', 'icon effects scope');
        if (d.property === 'font-size' && ['clock', 'date'].indexOf(r.selector[r.selector.length - 1].part) < 0) fail('css-property', 'clock/date font size scope');
        if (d.property === 'isolation' && r.selector[r.selector.length - 1].part !== 'card') fail('css-property', 'card isolation scope');
        if (d.property === 'overflow' && r.selector[r.selector.length - 1].part !== 'card') fail('css-property', 'card overflow scope');
        if (d.property === 'transform' && (r.selector.length < 2 || r.selector[r.selector.length - 1].part !== 'icon' || r.selector[r.selector.length - 2].part !== 'card')) fail('css-property', 'card icon scale scope');
        props[d.property] = true;
        value(d.value, properties[d.property]);
        count++;
      });
    });
    if (count > limits.declarations) fail('css-budget', 'declarations');
    return JSON.parse(JSON.stringify(b));
  }
  function compileRules(bundle, handles) {
    var chunks = [], used = 0;
    /* Every emitted token is ASCII, so length is also the UTF-8 byte count. */
    function append(text) {
      if (text.length > limits.emittedCssBytes - used) fail('css-budget', 'emitted CSS bytes');
      used += text.length;
      chunks.push(text);
    }
    validateRules(bundle).rules.forEach(function (r, index) {
      if (index) append('\n');
      append('#homeSurface.ctv-home' + (r.selector[0].part === 'home' ? '' : ' ') + r.selector.map(function (s, i) {
        return (i === 0 && s.part === 'home' ? '' : '.ctv-' + s.part) + s.states.map(function (t) {
          return '.is-' + t;
        }).join('');
      }).join(' ') + '{');
      r.declarations.forEach(function (d) {
        append(d.property + ':');
        append(value(d.value, properties[d.property], handles || {}));
        append(';');
      });
      append('}');
    });
    return chunks.join('');
  }
  function validateCollection(c) {
    object(c, ['schemaVersion', 'repository', 'themes'], 'manifest-invalid', 'collection');
    if (c.schemaVersion !== 1 || bytes(c) > 65536) fail('manifest-invalid', 'collection');
    repository(c.repository);
    var seen = {};
    list(c.themes, 64, 'manifest-invalid', 'themes').forEach(function (t) {
      object(t, ['id', 'title', 'themeVersion', 'path', 'sha256'], 'manifest-invalid', 'entry');
      id(t.id);
      if (t.id.indexOf('github:' + c.repository.slice(19).toLowerCase() + ':') !== 0 || seen[t.id]) fail('manifest-invalid', 'entry.id');
      seen[t.id] = true;
      string(t.title, 100, 'manifest-invalid', 'title');
      version(t.themeVersion);
      path(t.path);
      if (typeof t.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(t.sha256)) fail('manifest-invalid', 'sha256');
    });
    return JSON.parse(JSON.stringify(c));
  }
  return {
    schemaVersion: 1,
    themeApiVersion: 1,
    parts: parts,
    states: states,
    properties: properties,
    limits: limits,
    normalizeRibbon: normalizeRibbon,
    validateManifest: validateManifest,
    validateRules: validateRules,
    compileRules: compileRules,
    validateCollection: validateCollection,
    validateBundle: validateRules,
    serializeBundle: compileRules
  };
});
