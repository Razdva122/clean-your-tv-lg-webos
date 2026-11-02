// Compile classic webOS scripts separately: bundling their UMD wrappers would
// change their globals. A single ES5 core-js bundle runs before all app scripts.
const fs = require('node:fs');
const path = require('node:path');
const babel = require('@babel/core');
const acorn = require('acorn');
const postcss = require('postcss');
const presetEnv = require('postcss-preset-env');
const doiuse = require('doiuse');
const html = require('parse5');
const targets = require('../package.json').browserslist;
const root = path.resolve(__dirname, '..');
const polyfillsName = 'compat-polyfills.js';

function javascript(code, filename) {
  // Already-compatible scripts keep their bytes and global-script semantics.
  try { acorn.parse(code, {ecmaVersion: 5}); return code; } catch (_) {}
  const output = babel.transformSync(code, {
    filename, cwd: root, configFile: false, babelrc: false, sourceType: 'script',
    presets: [[require.resolve('@babel/preset-env'), {
      targets, forceAllTransforms: true, modules: false, useBuiltIns: false, bugfixes: true
    }]]
  }).code;
  acorn.parse(output, {ecmaVersion: 5});
  return output + '\n';
}

async function stylesheet(code, filename) {
  // webOS 2 uses WebKit 538.2: emit its prefixed flex/transform/animation forms.
  // Safari 8 supplies the prefix profile, not a claim of complete TV API support.
  const transformed = await postcss([presetEnv({browsers: targets.concat('Safari 8'), stage: 3, preserve: false,
    features: {'logical-properties-and-values': true, 'hexadecimal-alpha-notation': true}})]).process(code, {from: filename, map: false});
  const unsupported = [];
  transformed.root.walkDecls(/^(overflow-wrap|word-wrap)$/, declaration => {
    if (declaration.value === 'anywhere') unsupported.push(filename + ': ' + declaration.prop + ': anywhere requires a legacy break-word value');
  });
  transformed.root.walkAtRules(/^font-face$/i, face => {
    face.walkDecls(/^font-weight$/i, declaration => {
      if (/\s/.test(declaration.value.trim())) unsupported.push(filename + ': font-weight ranges require static font faces for legacy engines');
    });
  });
  await postcss([doiuse({browsers: targets, onFeatureUsage: usage => {
    // doiuse groups legacy overflow values with newer clip/overlay features.
    // Only the four original values are accepted, not the entire feature family.
    if (usage.feature === 'css-overflow' && /^overflow(?:-[xy])?$/.test(usage.usage.prop) &&
        /^(auto|hidden|scroll|visible)$/.test(usage.usage.value)) return;
    // CSS1 scalar decorations predate the modern multi-value shorthand.
    if (usage.feature === 'mdn-text-decoration-shorthand' && usage.usage.prop === 'text-decoration' &&
        /^(none|underline)$/.test(usage.usage.value)) return;
    unsupported.push(usage.message);
  }})])
    .process(transformed.css, {from: filename, map: false});
  if (unsupported.length) throw Error(filename + ': unsupported CSS after PostCSS:\n' + unsupported.join('\n'));
  return transformed.css;
}

async function document(code, filename) {
  const tree = html.parse(code);
  let head, hasPolyfills = false;
  async function visit(node) {
    if (node.tagName === 'head') head = node;
    const attrs = node.attrs || [];
    const source = attrs.find(attr => attr.name === 'src');
    if (node.tagName === 'script' && source && source.value === polyfillsName) hasPolyfills = true;
    if (node.tagName === 'style') {
      for (const text of node.childNodes) text.value = await stylesheet(text.value, filename + '.style.css');
    }
    for (const attr of attrs) {
      if (attr.name === 'style') {
        const css = await stylesheet('.inline{' + attr.value + '}', filename + '.attribute.css');
        attr.value = postcss.parse(css).first.nodes.map(node => node.toString()).join(';');
      }
    }
    if (node.tagName === 'script' && !source) {
      const type = attrs.find(attr => attr.name === 'type');
      if (type && type.value === 'module') throw Error(filename + ': use classic scripts, not unbundled ES modules');
      if (!type || /^(text|application)\/javascript$/.test(type.value)) {
        for (const text of node.childNodes) text.value = javascript(text.value, filename + '.inline.js');
      }
    }
    for (const child of node.childNodes || []) await visit(child);
    if (node.content) await visit(node.content);
  }
  await visit(tree);
  if (!hasPolyfills) {
    const script = html.parseFragment('<script src="' + polyfillsName + '"></script>').childNodes[0];
    script.parentNode = head;
    head.childNodes.unshift(script);
  }
  return html.serialize(tree);
}

async function compile(files) {
  const output = {...files};
  for (const [name, code] of Object.entries(files)) {
    if (name === polyfillsName) continue;
    if (name.endsWith('.js')) output[name] = javascript(code, name);
    if (name.endsWith('.css')) output[name] = await stylesheet(code, name);
    if (name.endsWith('.html')) output[name] = await document(code, name);
  }
  if (Object.keys(files).some(name => name.endsWith('.html'))) {
    output[polyfillsName] = fs.readFileSync(require.resolve('core-js-bundle/minified.js'), 'utf8');
    acorn.parse(output[polyfillsName], {ecmaVersion: 5});
    output['compat-LICENSE.txt'] = fs.readFileSync(require.resolve('core-js-bundle/LICENSE'), 'utf8') + '\n' +
      fs.readFileSync(path.join(path.dirname(require.resolve('@babel/core/package.json')), 'LICENSE'), 'utf8');
  }
  return output;
}

exports.compile = compile;
exports.stylesheet = stylesheet;
if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => input += chunk);
  process.stdin.on('end', () => compile(JSON.parse(input)).then(output => process.stdout.write(JSON.stringify(output)))
    .catch(error => {console.error(error.message); process.exitCode = 1;}));
}
