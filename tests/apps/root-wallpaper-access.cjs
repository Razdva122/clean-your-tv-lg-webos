'use strict';
// LS2 freezes provided method groups when the service registers its category.
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const source = fs.readFileSync('root-edition/service/service.js', 'utf8');
for (const failure of [false, true]) {
  const calls = [];
  vm.runInNewContext(source, {
    __dirname: '/private/service',
    process: { getuid: () => 0 },
    Promise,
    require(name) {
      if (name === 'child_process')
        return {
          execFile() {
            throw Error('Unexpected runtime operation');
          },
          execFileSync(command, args) {
            calls.push(['prepare', command, args]);
            if (failure) throw Error('Permission conflict');
            return Buffer.from('{}');
          }
        };
      if (name === '/var/lib/clean-your-tv-root/python_boot.js')
        return { command: () => '/usr/bin/python3' };
      if (name === 'webos-service')
        return function () {
          calls.push(['connect']);
          this.register = (method) => calls.push(['register', method]);
        };
      if (name === './handlers') {
        const handlers = () => ({ status() {}, restore() {} });
        handlers.audio = () => ({});
        return handlers;
      }
      if (name === './presentation-context') return () => ({});
      if (name === './app-inventory') return { inputHandler: () => () => {} };
      if (name === './weather') return require('../../renewal-service/weather');
      if (name === './theme-receiver')
        return require('../../theme-receiver/register');
      if (name === './c1-lease') return () => {};
      throw Error('Unexpected module: ' + name);
    }
  });
  assert.equal(
    calls[0][0],
    'prepare',
    'attach fixed wallpaper APIs before the LS2 connection/category caches groups'
  );
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0].slice(1))), [
    '/usr/bin/python3',
    ['/var/lib/clean-your-tv-root/runtime/cli.py', 'provision-wallpaper-access']
  ]);
  assert(
    calls.some((call) => call[0] === 'register' && call[1] === 'restore'),
    'permission failure must preserve recovery methods'
  );
}
console.log(
  'PASS Root wallpaper grant ordering and recovery on permission failure'
);
