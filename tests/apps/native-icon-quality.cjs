'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  path = require('node:path'),
  vm = require('node:vm');
const folder = '/media/cryptofs/apps/usr/palm/applications/example.app',
  bytes = Buffer.from('\x89PNG\r\n\x1a\noriginal', 'binary'),
  reads = [];
const content = (p) =>
  p.endsWith('/empty.png')
    ? Buffer.alloc(0)
    : p.endsWith('/corrupt.png')
      ? Buffer.from('not an image')
      : bytes;
const fakeFs = {
  realpathSync: (p) => p,
  statSync: (p) => ({ isFile: () => true, size: content(p).length }),
  readFileSync: (p) => {
    reads.push(p);
    return content(p);
  }
};
const sandbox = {
  module: { exports: {} },
  require: (name) => (name === 'fs' ? fakeFs : require(name))
};
vm.runInNewContext(
  fs.readFileSync('root-edition/service/app-inventory.js', 'utf8'),
  sandbox
);
const query = sandbox.module.exports;
function run(app) {
  return query(
    (file, args, opts, cb) =>
      cb(
        null,
        JSON.stringify({
          returnValue: true,
          apps: [{ id: 'test', title: 'Test', folderPath: folder, ...app }]
        })
      ),
    () => 0
  );
}
const create = require('../../launcher/app-library.js').create;
const store = { getItem: () => null, setItem: () => {} };
const model = create(
  store,
  [{ id: 'test', title: 'Test', icon: 'data:image/png;base64,b2xk' }],
  { columns: 5, dockApps: ['test'] }
);
model.refresh([
  { id: 'test', title: 'Test', icon: 'data:image/png;base64,bGFyZ2U=' }
]);
assert.equal(
  model.visible()[0].icon,
  'data:image/png;base64,bGFyZ2U=',
  'fresh embedded native resource can replace an older cached size'
);
model.refresh([{ id: 'test', title: 'Test', icon: 'http://tv/native.png' }]);
assert.equal(
  model.visible()[0].icon,
  'data:image/png;base64,bGFyZ2U=',
  'raw metadata URLs do not displace usable embedded originals'
);
(async () => {
  await run({
    icon: 'small.png',
    largeIcon: 'large.png',
    extraLargeIcon: 'largest.png'
  });
  assert.equal(
    reads.at(-1),
    folder + '/largest.png',
    'prefer largest original resource'
  );
  await run({
    icon: 'small.png',
    largeIcon: 'large.png',
    extraLargeIcon: '/etc/private.png'
  });
  assert.equal(
    reads.at(-1),
    folder + '/large.png',
    'untrusted absolute path cannot bypass existing boundary'
  );
  await run({ extraLargeIcon: 'empty.png', icon: 'small.png' });
  assert.equal(
    reads.at(-1),
    folder + '/small.png',
    'empty preferred image falls back'
  );
  await run({ extraLargeIcon: 'corrupt.png', icon: 'small.png' });
  assert.equal(
    reads.at(-1),
    folder + '/small.png',
    'corrupt preferred image falls back'
  );
  await run({ miniicon: 'mini.png' });
  assert.equal(
    reads.at(-1),
    folder + '/mini.png',
    'native small fallback remains usable'
  );
  console.log(
    'PASS any-app native icon preference, path boundary and original fallback'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

const remote = create(
  store,
  [{ id: 'remote', title: 'Remote', icon: 'https://tv:3001/resources/old' }],
  { columns: 5, dockApps: ['remote'] }
);
remote.refresh([
  { id: 'remote', title: 'Remote', icon: 'https://tv:3001/resources/fresh' }
]);
assert.equal(
  remote.visible()[0].icon,
  'https://tv:3001/resources/fresh',
  'a fresh resource URL replaces an expiring cached URL'
);
remote.refresh([{ id: 'remote', title: 'Remote' }]);
assert.equal(
  remote.visible()[0].icon,
  'https://tv:3001/resources/fresh',
  'partial metadata does not erase an existing icon'
);

const packaged = create(
  store,
  [{ id: 'local', title: 'Local', icon: 'icons/local.png' }],
  { columns: 5, dockApps: ['local'] }
);
packaged.refresh([
  { id: 'local', title: 'Local', icon: 'https://tv:3001/resources/new' }
]);
assert.equal(
  packaged.visible()[0].icon,
  'icons/local.png',
  'a remote URL cannot replace a durable packaged icon'
);
