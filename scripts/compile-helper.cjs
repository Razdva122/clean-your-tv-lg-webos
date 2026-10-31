// Build-time Node only. Helper itself targets the TV's Node 0.10 runtime.
const fs = require('node:fs');
const path = require('node:path');
const babel = require('@babel/core');
const acorn = require('acorn');

function compile(files) {
  const output = {...files};
  for (const [name, source] of Object.entries(files)) {
    if (!name.endsWith('.js')) continue;
    // Always transform: an ES5 parse alone accepts block function declarations
    // that Node 0.12 still rejects inside strict try/catch blocks.
    let code = babel.transformSync(source, {
      filename: name, configFile: false, babelrc: false, sourceType: 'script',
      presets: [[require.resolve('@babel/preset-env'), {
        targets: {node: '0.10'}, forceAllTransforms: true, modules: false, useBuiltIns: false
      }]]
    }).code;
    // Every app/service entry point initializes its own process before imports.
    if (!name.includes('/')) code = "'use strict';\nrequire('./compat-runtime');\n" + code;
    acorn.parse(code, {ecmaVersion: 5});
    output[name] = code + '\n';
  }
  // Node 0.12's Buffer constructor refers to global.Buffer internally. Replacing
  // that constructor recurses; add the safe-buffer methods to the original.
  output['compat-runtime.js'] = `'use strict';
require('./compat-polyfills');
var buffer = require('buffer').Buffer, safe = require('./compat-buffer').Buffer;
['from','alloc','allocUnsafe','allocUnsafeSlow'].forEach(function(name){if(!buffer[name])buffer[name]=safe[name];});
// Node 0.12 nextTick does not forward callback arguments (added in Node 1.8).
if(Number(process.versions.node.split('.')[0])===0){
 var tick=process.nextTick;
 process.nextTick=function(callback){
  var args=Array.prototype.slice.call(arguments,1);
  tick(function(){callback.apply(null,args);});
 };
}
`;
  output['compat-polyfills.js'] = fs.readFileSync(require.resolve('core-js-bundle/minified.js'), 'utf8');
  output['compat-buffer.js'] = fs.readFileSync(require.resolve('safe-buffer'), 'utf8');
  for (const name of ['compat-runtime.js', 'compat-polyfills.js', 'compat-buffer.js']) acorn.parse(output[name], {ecmaVersion: 5});
  output['compat-LICENSE.txt'] = ['core-js-bundle/LICENSE', 'safe-buffer/LICENSE', '@babel/core/LICENSE']
    .map(name => fs.readFileSync(path.join(path.dirname(require.resolve(name.split('/LICENSE')[0] + '/package.json')), 'LICENSE'), 'utf8')).join('\n');
  return output;
}
exports.compile = compile;
if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => input += chunk);
  process.stdin.on('end', () => {
    try { process.stdout.write(JSON.stringify(compile(JSON.parse(input)))); }
    catch (error) { console.error(error.stack); process.exitCode = 1; }
  });
}
