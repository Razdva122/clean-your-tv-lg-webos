'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs'),
  path = require('node:path'),
  vm = require('node:vm');

// Node 8 has require('url').URL, but no global URL. Exercise both real modules.
for (const file of [
  'updater-service/transport.js',
  'root-edition/updater/fetch.js'
]) {
  const filename = path.resolve(file);
  const context = {
    require: require('node:module').createRequire(filename),
    module: { exports: {} },
    __dirname: path.dirname(filename),
    URL: undefined,
    Buffer,
    console,
    setTimeout,
    clearTimeout
  };
  vm.runInNewContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  const transport = context.module.exports;
  assert.equal(
    transport.allowed(
      'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/update.json'
    ),
    true,
    file
  );
  for (const url of [
    'http://github.com/Razdva122/clean-your-tv-lg-webos/releases/foo',
    'https://github.com/other/project/releases/foo',
    'https://user@github.com/Razdva122/clean-your-tv-lg-webos/releases/foo'
  ]) {
    assert.equal(transport.allowed(url), false, url);
  }
}
console.log('PASS updater URL policy works without global URL');
