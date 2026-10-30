/* Host-only author compiler. It never loads code or fetches data from a theme. */
const postcss = require('postcss');
const parseValue = require('postcss-value-parser');
const crypto = require('node:crypto');
const policy = require('../launcher/theme-policy.js');
const compat = require('../scripts/compile-tv-web.cjs');
function error(code, field) {
  const e = new Error(code + ': theme.css ' + field);
  e.code = code;
  e.field = field;
  throw e;
}
function color(raw) {
  const names = {
    transparent: [0, 0, 0, 0],
    black: [0, 0, 0, 1],
    white: [255, 255, 255, 1],
    red: [255, 0, 0, 1],
    blue: [0, 0, 255, 1],
    green: [0, 128, 0, 1],
    yellow: [255, 255, 0, 1],
    gray: [128, 128, 128, 1]
  };
  if (names[raw]) return {
    type: 'color',
    rgba: names[raw].slice()
  };
  let m = /^#([a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})$/i.exec(raw);
  if (m) {
    let h = m[1];
    if (h.length < 5) h = h.split('').map(x => x + x).join('');
    return {
      type: 'color',
      rgba: [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1]
    };
  }
  m = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*(\d*\.?\d+))?\s*\)$/i.exec(raw);
  if (m) return {
    type: 'color',
    rgba: [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]]
  };
  error('css-value', 'color: use hex or rgba()');
}
function split(raw, divider) {
  const nodes = parseValue(raw).nodes;
  const out = [''];
  for (const n of nodes) {
    if (n.type === 'div' && n.value === divider) out.push('');else out[out.length - 1] += parseValue.stringify(n);
  }
  return out.map(x => x.trim());
}
function scalar(raw) {
  if (raw === '0') return 0;
  if (!/^-?(?:\d+|\d*\.\d+)px$/.test(raw)) error('css-value', 'length: use px');
  return parseFloat(raw);
}
function typed(raw, family, assets) {
  if (family === 'iconScale') { const m = /^scale\((\d+(?:\.\d+)?)\)$/.exec(raw); if (!m) error('css-value', 'icon scale'); return {type: 'scale', amount: Number(m[1])}; }
  if (family === 'filter') {
    if (raw === 'none') return {type: 'filter', functions: []};
    const nodes = parseValue(raw).nodes.filter(n => n.type !== 'space');
    if (!nodes.length || nodes.some(n => n.type !== 'function' || n.nodes.length !== 1 || n.nodes[0].type !== 'word' || !/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(n.nodes[0].value))) error('css-value', 'filter');
    return {type: 'filter', functions: nodes.map(n => ({name: n.value, amount: Number(n.nodes[0].value)}))};
  }
  if (family === 'color') return color(raw);
  if (family === 'length' || family === 'fontSize') return {
    type: 'length',
    unit: 'px',
    value: scalar(raw)
  };
  if (family === 'image') {
    const url = /^url\(\s*(["']?)([a-zA-Z0-9_./-]+)\1\s*\)$/.exec(raw);
    if (url) {
      const asset = assets.find(a => a.path === url[2] || a.id === url[2]);
      if (!asset) error('asset-invalid', 'unlisted image');
      return {
        type: 'asset',
        id: asset.id
      };
    }
    const gradient = /^linear-gradient\((.*)\)$/.exec(raw);
    if (gradient) {
      const args = split(gradient[1], ',');
      const angle = args.shift();
      if (!/^\d+(?:\.\d+)?deg$/.test(angle)) error('css-value', 'gradient angle: use deg');
      return {
        type: 'gradient',
        angle: parseFloat(angle),
        stops: args.map((s, i) => {
          const m = /^(.*?)\s+(\d+(?:\.\d+)?)%$/.exec(s);
          return {
            color: color(m ? m[1] : s),
            position: m ? +m[2] : 100 * i / (args.length - 1)
          };
        })
      };
    }
    error('css-value', 'background-image: use a listed asset or linear-gradient');
  }
  if (family === 'shadow' || family === 'textShadow') return {
    type: 'shadow',
    items: split(raw, ',').map(s => {
      const nodes = parseValue(s).nodes.filter(n => n.type !== 'space');
      if (nodes.length < 4 || nodes.length > 5) error('css-value', 'shadow');
      const vals = nodes.map(n => parseValue.stringify(n));
      return {
        x: scalar(vals[0]),
        y: scalar(vals[1]),
        blur: scalar(vals[2]),
        spread: vals.length === 5 ? scalar(vals[3]) : 0,
        color: color(vals[vals.length - 1])
      };
    })
  };
  if (family === 'transition') {
    const a = raw.split(/\s+/);
    if (a.length !== 3 || !/^\d+(?:\.\d+)?m?s$/.test(a[1])) error('css-value', 'transition: use property duration easing');
    return {
      type: 'transition',
      property: a[0],
      duration: parseFloat(a[1]) * (a[1].endsWith('ms') ? 1 : 1000),
      easing: a[2]
    };
  }
  return {
    type: 'keyword',
    value: raw
  };
}
function selector(raw) {
  if (!/^\.ctv-[a-z-]+(?:\.is-[a-z-]+)*(?:\s+\.ctv-[a-z-]+(?:\.is-[a-z-]+)*)*$/.test(raw)) error('css-selector', 'use public part/state classes');
  return raw.split(/\s+/).map(s => {
    const a = s.split('.').slice(1);
    return {
      part: a.shift().slice(4),
      states: a.map(x => x.slice(3))
    };
  });
}
async function compileThemeCss(css, options = {}) {
  if (typeof css !== 'string' || Buffer.byteLength(css) > policy.limits.sourceBytes) error('css-budget', 'source size');
  let tree;
  try {
    tree = postcss.parse(css, {
      from: 'theme.css'
    });
  } catch (e) {
    error('css-value', 'line ' + (e.line || 1) + ': invalid CSS syntax');
  }
  const variables = Object.create(null);
  tree.walkAtRules(a => error('css-property', '@' + a.name + ' is unsupported'));
  tree.walkDecls(d => {
    if (d.important || /[\\\u0000-\u0008]/.test(d.value) || /[\\]/.test(d.prop)) error('css-value', 'line ' + d.source.start.line + ' ' + d.prop);
  });
  tree.walkRules(r => {
    if (r.selector === ':root') {
      r.nodes.forEach(d => {
        if (d.type !== 'decl' || !/^--[a-z][a-z0-9-]*$/.test(d.prop) || variables[d.prop] !== undefined) error('css-property', 'variables');
        variables[d.prop] = d.value;
      });
      r.remove();
    }
  });
  const expandedVariables = Object.create(null);
  let expansionBytes = 0, expansionWork = 0;
  function resolve(v, stack = []) {
    expansionWork += Buffer.byteLength(v);
    if (expansionWork > policy.limits.variableExpansionWork) error('css-budget', 'variable expansion work');
    const chunks = [], pattern = /var\(\s*(--[a-z][a-z0-9-]*)\s*\)/g;
    let offset = 0, match;
    function append(text) {
      const size = Buffer.byteLength(text);
      if (size > policy.limits.variableExpansionBytes - expansionBytes) error('css-budget', 'expanded variable bytes');
      expansionBytes += size;
      chunks.push(text);
    }
    while ((match = pattern.exec(v))) {
      append(v.slice(offset, match.index));
      const key = match[1];
      if (stack.includes(key) || variables[key] === undefined || stack.length > 16) error('css-value', 'unresolved/cyclic variable');
      if (expandedVariables[key] === undefined) expandedVariables[key] = resolve(variables[key], stack.concat(key));
      append(expandedVariables[key]);
      offset = pattern.lastIndex;
    }
    append(v.slice(offset));
    return chunks.join('');
  }
  const bundle = {
    schemaVersion: 1,
    rules: []
  };
  tree.nodes.forEach(r => {
    if (r.type === 'comment') return;
    if (r.type !== 'rule') error('css-selector', 'nested syntax');
    const declarations = [];
    r.nodes.forEach(d => {
      if (d.type === 'comment') return;
      if (d.type !== 'decl') error('css-property', 'nested syntax');
      if (!Object.hasOwn(policy.properties, d.prop)) error('css-property', 'line ' + d.source.start.line + ' ' + d.prop);
      const raw = resolve(d.value);
      if (/var\(|[\\]/.test(raw)) error('css-value', d.prop);
      declarations.push({
        property: d.prop,
        value: typed(raw, policy.properties[d.prop], options.assets || [])
      });
    });
    r.selector.split(',').map(x => x.trim()).forEach(s => bundle.rules.push({
      selector: selector(s),
      declarations
    }));
  });
  policy.validateRules(bundle);
  const handles = {};
  // Compatibility checks exercise URL syntax, never duplicate source image bytes.
  (options.assets || []).forEach(a => handles[a.id] = 'data:' + a.mediaType + ';base64,AA==');
  const output = policy.compileRules(bundle, handles);
  try {
    // Screen blending is a separately gated optional capability, not a Chromium 38 promise.
    // All other typed output still uses the unchanged compatibility checker.
    const legacy = {schemaVersion: 1, rules: bundle.rules.map(r => ({...r, declarations: r.declarations.filter(d => d.property !== 'mix-blend-mode' && d.property !== 'isolation')}))};
    await compat.stylesheet(policy.compileRules(legacy, handles), 'theme.css');
  } catch (_) {
    error('css-value', 'unsupported Chromium 38 feature; use API 1 properties');
  }
  return {
    bundle,
    css: output
  };
}
function hash(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}
function imageInfo(data, mediaType, wallpaper = false) {
  if (data.length > 2097152) error('asset-invalid', 'image size');
  let width, height;
  if (mediaType === 'image/png') {
    if (data.length < 45 || data.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') error('asset-invalid', 'PNG signature');
    let offset = 8,
      ended = false,
      hasData = false;
    while (offset + 12 <= data.length) {
      const size = data.readUInt32BE(offset),
        kind = data.toString('ascii', offset + 4, offset + 8);
      if (size > data.length - offset - 12) error('asset-invalid', 'PNG chunk');
      if (offset === 8) {
        if (kind !== 'IHDR' || size !== 13) error('asset-invalid', 'PNG header');
        width = data.readUInt32BE(offset + 8);
        height = data.readUInt32BE(offset + 12);
      }
      if (kind === 'acTL') error('asset-invalid', 'animated PNG');
      if (kind === 'IDAT') hasData = true;
      offset += size + 12;
      if (kind === 'IEND') {
        ended = size === 0;
        break;
      }
    }
    if (!ended || !hasData || offset !== data.length) error('asset-invalid', 'PNG structure');
  } else if (mediaType === 'image/jpeg') {
    if (data.length < 4 || data[0] !== 255 || data[1] !== 216 || data[data.length - 2] !== 255 || data[data.length - 1] !== 217) error('asset-invalid', 'JPEG signature');
    let offset = 2;
    while (offset + 4 <= data.length) {
      if (data[offset++] !== 255) error('asset-invalid', 'JPEG marker');
      while (data[offset] === 255) offset++;
      const marker = data[offset++];
      if (marker === 218) break;
      const size = data.readUInt16BE(offset);
      if (size < 2 || offset + size > data.length) error('asset-invalid', 'JPEG segment');
      if ([192, 193, 194].includes(marker)) {
        if (size < 8) error('asset-invalid', 'JPEG frame');
        height = data.readUInt16BE(offset + 3);
        width = data.readUInt16BE(offset + 5);
      }
      offset += size;
    }
  } else if (mediaType === 'image/webp') {
    if (data.length < 30 || data.toString('ascii', 0, 4) !== 'RIFF' || data.toString('ascii', 8, 12) !== 'WEBP' || data.readUInt32LE(4) + 8 !== data.length) error('asset-invalid', 'WebP signature');
    const kind = data.toString('ascii', 12, 16);
    if (kind === 'VP8X') {
      if (data[20] & 2) error('asset-invalid', 'animated WebP');
      width = 1 + data.readUIntLE(24, 3);
      height = 1 + data.readUIntLE(27, 3);
    } else if (kind === 'VP8 ') {
      if (data.subarray(23, 26).toString('hex') !== '9d012a') error('asset-invalid', 'WebP frame');
      width = data.readUInt16LE(26) & 16383;
      height = data.readUInt16LE(28) & 16383;
    } else if (kind === 'VP8L') {
      if (data[20] !== 47) error('asset-invalid', 'WebP frame');
      const bits = data.readUInt32LE(21);
      width = (bits & 16383) + 1;
      height = (bits >>> 14 & 16383) + 1;
    }
  }
  if (!width || !height || width > (wallpaper ? 3840 : 1920) || height > (wallpaper ? 2160 : 1080)) error('asset-invalid', 'image dimensions');
  return {
    width,
    height
  };
}
async function compileSource(input) {
  const source = JSON.parse(JSON.stringify(input.manifest));
  const assets = (input.assets || []).map(a => {
    const data = Buffer.from(a.data);
    const info = imageInfo(data, a.mediaType, !!source.defaults && a.id === source.defaults.wallpaperAssetId);
    if (a.width !== undefined && a.width !== info.width || a.height !== undefined && a.height !== info.height) error('asset-invalid', 'image metadata');
    return {
      id: a.id,
      path: a.path,
      mediaType: a.mediaType,
      width: info.width,
      height: info.height,
      data,
      size: data.length,
      sha256: hash(data)
    };
  });
  const documents = (input.documents || []).map(d => {
    const data = Buffer.from(d.data);
    return {
      path: d.path,
      data,
      size: data.length,
      sha256: hash(data)
    };
  });
  const compiled = await compileThemeCss(input.css, {
    assets
  });
  const ruleBytes = Buffer.from(JSON.stringify(compiled.bundle) + '\n');
  source.schemaVersion = 1;
  source.themeApiVersion = 1;
  source.source = input.source || source.source;
  source.requires = {
    minimumHomeVersion: input.minimumHomeVersion || '0.0.0',
    capabilities: compiled.bundle.rules.some(r => r.declarations.some(d => d.property === 'filter' || d.property === 'mix-blend-mode' || d.property === 'isolation' || d.property === 'transform' || d.property === 'overflow')) ? ['modern-icon-css-v1'] : []
  };
  source.layout = Object.assign({
    preset: 'dock-grid',
    columns: 5,
    spacingScale: 1,
    textScale: 1,
    focusScale: 1.1
  }, source.layout);
  if (Object.hasOwn(source.layout, 'ribbon')) source.requires.capabilities.push('ribbon-layout-v1');
  if (compiled.bundle.rules.some(r => r.declarations.some(d => d.property === 'transform')) && (source.layout.preset !== 'scenic-grid' || source.layout.columns > 5 || source.layout.allowColumnOverride !== false)) error('layout-invalid', 'icon scale requires fixed scenic-grid with at most five columns');
  source.defaults = Object.assign({
    wallpaperAssetId: null,
    dim: .3,
    accent: '#00aaff'
  }, source.defaults);
  source.rules = {
    path: 'rules.json',
    size: ruleBytes.length,
    sha256: hash(ruleBytes)
  };
  source.assets = assets.map(({
    data,
    ...a
  }) => a);
  source.documents = documents.map(({
    data,
    ...d
  }) => d);
  const normalized = policy.validateManifest(source);
  source.layout = normalized.layout;
  return {
    manifest: source,
    rules: compiled.bundle,
    assets,
    documents,
    report: {
      themeApiVersion: 1,
      ruleCount: compiled.bundle.rules.length,
      manifestSha256: hash(JSON.stringify(source) + '\n')
    }
  };
}
module.exports = {
  compileSource,
  compileThemeCss,
  imageInfo
};
