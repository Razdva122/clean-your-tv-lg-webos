// Opt-in host prototype only; runtime admission remains Node 8+.
const {compile} = require('./compile-helper.cjs');
const acorn = require('acorn');

exports.compile = function(files) {
  const compiled = compile(files);
  // Keep compatibility within each existing immutable file path. In particular,
  // nested fetch/policy CLIs and python_boot run without the service entry point.
  // Isolate UMD exports so core-js/safe-buffer cannot replace this module's API.
  const embed = code => '(function(){var module={exports:{}},exports=module.exports;\n' + code + '\nreturn module.exports;}())';
  const runtime = '(function(){if(global.__cytvRootNodePrototypeCompat)return;\n' + embed(compiled['compat-polyfills.js']) + ';\n' +
    compiled['compat-runtime.js'].replace("require('./compat-polyfills');", '')
      .replace("require('./compat-buffer')", embed(compiled['compat-buffer.js'])) +
    "\nvar fs=require('fs'),url=require('url');\n" +
    "if(!fs.constants)fs.constants=require('constants');\n" +
    "if(!url.URL)url.URL=global.URL;\nglobal.__cytvRootNodePrototypeCompat=true;\n}());\n";
  const license = '/* Root Node compatibility prototype: core-js, safe-buffer and Babel.\n' +
    compiled['compat-LICENSE.txt'].replace(/\*\//g, '* /') + '\n*/\n';
  const result = {...files};
  for (const name of Object.keys(files)) {
    if (!name.endsWith('.js')) continue;
    const code = compiled[name].replace("'use strict';\nrequire('./compat-runtime');\n", '');
    result[name] = license + runtime + code;
    acorn.parse(result[name], {ecmaVersion: 5});
  }
  return result;
};
if (require.main === module) {
  let input='';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => input += chunk);
  process.stdin.on('end', () => {
    try {process.stdout.write(JSON.stringify(exports.compile(JSON.parse(input))));}
    catch(error) {console.error(error.stack);process.exitCode=1;}
  });
}
