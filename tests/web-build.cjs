const assert = require('node:assert/strict');
const vm = require('node:vm');
const {compile} = require('../scripts/compile-tv-web.cjs');
const acorn = require('acorn');

(async () => {
  const source = {
    'index.html': '<html><head><title>Test</title></head><body><script src="app.js"></script><script>const inline = () => 7; window.inlineResult = inline();</script></body></html>',
    'app.js': 'const app = {title: "Test"}; window.result = [app].findIndex(x => x?.title === "Test"); window.copy = Object.assign({}, app); window.includes = [1, 2].includes(2);',
    'style.css': '.viewport {position:absolute;inset:0;color:#1234}',
    'apps.js': 'window.TV_APPS = {apps: []};'
  };
  const output = await compile(source);
  acorn.parse(output['app.js'], {ecmaVersion: 5});
  assert(output['index.html'].indexOf('src="compat-polyfills.js"') < output['index.html'].indexOf('src="app.js"'), 'polyfills must run before all app scripts');
  const context = vm.createContext({setTimeout, clearTimeout});
  vm.runInContext('window=this; delete Array.prototype.findIndex; delete Array.prototype.includes; delete Object.assign;', context);
  vm.runInContext(output['compat-polyfills.js'], context);
  vm.runInContext(output['app.js'], context);
  assert.equal(context.result, 0);
  assert.equal(context.copy.title, 'Test');
  assert.equal(context.includes, true);
  const inline = output['index.html'].match(/<script>([\s\S]*?)<\/script>/)[1];
  acorn.parse(inline, {ecmaVersion: 5});
  vm.runInContext(inline, context);
  assert.equal(context.inlineResult, 7, 'inline companion scripts must also be transpiled');
  assert(!/\binset\s*:/.test(output['style.css']));
  for (const edge of ['top', 'right', 'bottom', 'left']) assert(output['style.css'].includes(edge + ':0'), edge + ' must be explicit');
  assert.equal(source['app.js'].slice(0, 5), 'const', 'compilation must not mutate source inputs');
  const webkit = await compile({'style.css': '.row{display:flex;align-items:center;justify-content:space-between;transform:translateX(20px);transition:transform .2s}'});
  assert.match(webkit['style.css'], /display:\s*-webkit-flex/, 'webOS 2 WebKit needs prefixed flex');
  assert.match(webkit['style.css'], /-webkit-transform:\s*translateX\(20px\)/, 'webOS 2 WebKit needs prefixed transforms');
  const repeated = await compile(output);
  assert.equal((repeated['index.html'].match(/src="compat-polyfills.js"/g) || []).length, 1, 'packaging twice must not inject polyfills twice');
  await assert.rejects(() => compile({'style.css': '.row{display:flex;gap:12px}'}), /flexbox-gap|gap/, 'untransformed flex gap must block packaging');
  await assert.rejects(() => compile({'style.css': '.row{display:grid;grid-template-columns:1fr 1fr}'}), /css-grid|Grid/, 'unsupported grid must not silently reach the TV');
  await assert.rejects(() => compile({'index.html': '<head><style>.row{display:flex;gap:12px}</style></head>'}), /flexbox-gap|gap/, 'style elements must pass the same CSS gate');
  await assert.rejects(() => compile({'index.html': '<head></head><body style="display:grid"></body>'}), /css-grid|Grid/, 'style attributes must pass the same CSS gate');
  const styled = await compile({'index.html': '<head></head><body style="position:absolute;inset:0"></body>'});
  assert(!/inset\s*:/.test(styled['index.html']), 'inline inset must be transformed');
  await assert.rejects(() => compile({'style.css': '.text{overflow-wrap:anywhere}'}), /anywhere/, 'unsupported values missed by doiuse must also fail');
  await assert.rejects(() => compile({'style.css': '.row{overflow:clip}'}), /css-overflow|overflow/, 'overflow exception must not allow newer values');
  await assert.rejects(() => compile({'style.css': '@font-face{font-family:Outfit;src:url(outfit.ttf);font-weight:100 900}'}), /font-weight.*static/, 'variable font ranges must not reach legacy engines');
  console.log('PASS ES5 scripts and inline scripts, missing built-ins, physical CSS offsets, polyfill ordering and idempotent HTML');
})().catch(error => {console.error(error); process.exitCode = 1;});
