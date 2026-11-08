'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync('root-edition/service/app-inventory.js', 'utf8');
const folder = '/media/cryptofs/apps/usr/palm/applications/fixture';
function png(size) {
  const data = Buffer.alloc(size);
  Buffer.from('89504e470d0a1a0a', 'hex').copy(data);
  return data;
}
function app(id, extra = {}) {
  return { id, title: id, folderPath: folder, icon: 'icon.png', ...extra };
}
async function read(apps, files = {}, priorityIds) {
  const reads = [];
  const sandbox = {
    module: { exports: {} },
    require(name) {
      if (name !== 'fs') return require(name);
      return {
        realpathSync(file) {
          return files[file]?.real || file;
        },
        statSync(file) {
          const entry = files[file] || {};
          return {
            isFile: () => entry.regular !== false,
            size: entry.size ?? (entry.data || png(32768)).length
          };
        },
        readFileSync(file) {
          reads.push(file);
          if (files[file]?.error) throw Error('unreadable');
          return files[file]?.data || png(32768);
        }
      };
    }
  };
  vm.runInNewContext(source, sandbox);
  const result = await sandbox.module.exports(
    (file, args, options, callback) =>
      callback(null, JSON.stringify({ returnValue: true, apps })),
    () => 0,
    priorityIds
  );
  return { apps: JSON.parse(JSON.stringify(result)), reads };
}
test('late pinned icons receive the budget first without changing catalog order or bounds', async () => {
  const catalog = Array.from({ length: 151 }, (_, i) => app('app' + i));
  const result = await read(catalog, {}, ['app145', 'app150']);
  assert.deepEqual(
    result.apps.map((a) => a.id),
    catalog.map((a) => a.id)
  );
  assert(result.apps[145].icon, 'pinned app at position 146 gets its icon');
  assert(result.apps[150].icon, 'the next pinned app also gets its icon');
  assert.equal(result.apps.filter((a) => a.icon).length, 16);
  assert.equal(
    result.apps[14].icon,
    '',
    'unprioritized icons use only the remainder'
  );
  const limited = await read(
    catalog,
    {},
    Array.from({ length: 17 }, (_, i) => 'app' + (150 - i))
  );
  assert(limited.apps[150].icon);
  assert.equal(
    limited.apps[134].icon,
    '',
    'priority order still respects the total budget'
  );
  assert.equal(limited.reads.length, 16);
  const hidden = await read([app('hidden', { hidden: true }), ...catalog], {}, [
    'hidden',
    'absent',
    'app145'
  ]);
  assert.equal(hidden.apps[0].icon, '');
  assert(hidden.apps[146].icon);
});
test('priority IDs are bounded metadata and cannot supply commands or paths', async () => {
  for (const priority of [
    null,
    {},
    'app',
    [12],
    [''],
    ['x'.repeat(257)],
    Array(201).fill('app')
  ]) {
    await assert.rejects(
      read([app('app')], {}, priority),
      /invalid-icon-priority/
    );
  }
  assert.deepEqual(
    await read([app('app')], {}, ['/etc/private.png']),
    await read([app('app')])
  );
});
test('hidden catalog entries cannot consume visible icon budget, including the hidden tuner exception', async () => {
  const catalog = [
    ...Array.from({ length: 129 }, (_, i) =>
      app('hidden' + i, i % 2 ? { hidden: true } : { visible: false })
    ),
    ...Array.from({ length: 15 }, (_, i) => app('visible' + i)),
    app('com.webos.app.livetv', { hidden: true, visible: false })
  ];
  const result = await read(catalog);
  assert.equal(result.apps.length, 145, 'retain catalog metadata and order');
  assert(result.apps.slice(0, 129).every((a) => a.hidden && a.icon === ''));
  assert(
    result.apps
      .slice(129)
      .every(
        (a) =>
          !a.hidden &&
          a.icon === 'data:image/png;base64,' + png(32768).toString('base64')
      )
  );
  assert.equal(result.reads.length, 16);
});
test('visible selection is deterministic, bounded, and tries smaller variants with the remaining budget', async () => {
  const catalog = [
    ...Array.from({ length: 15 }, (_, i) => app('visible' + i)),
    app('partial', { icon: 'partial.png' }),
    app('smaller', { extraLargeIcon: 'icon.png', icon: 'small.png' }),
    app('exhausted')
  ];
  const files = {
    [path.join(folder, 'partial.png')]: { data: png(32760) },
    [path.join(folder, 'small.png')]: { data: png(8) }
  };
  const first = await read(catalog, files);
  assert.equal(first.apps.filter((a) => a.icon).length, 17);
  assert.equal(
    first.apps[16].icon,
    'data:image/png;base64,' + png(8).toString('base64')
  );
  assert.equal(first.apps[17].icon, '');
  assert.equal(
    first.apps.reduce(
      (sum, a) =>
        sum + (a.icon ? Buffer.from(a.icon.split(',')[1], 'base64').length : 0),
      0
    ),
    524288
  );
  assert.deepEqual(await read(catalog, files), first);
  assert.equal(
    (await read(Array.from({ length: 201 }, (_, i) => app('app' + i)))).apps
      .length,
    200
  );
});
test('system-app originals are admitted only within the exact lexical and resolved application roots', async () => {
  const system = '/media/system/apps/usr/palm/applications/fixture';
  const accepted = await read([app('system', { folderPath: system })]);
  assert(accepted.apps[0].icon.startsWith('data:image/png;base64,'));
  for (const candidate of [
    '/media/system/apps/usr/palm/applications-other/fixture/icon.png',
    '/media/system/apps/usr/palm/services/fixture/icon.png',
    '/media/system/apps/usr/palm/applications/../../private.png',
    '/etc/private.png'
  ]) {
    const denied = await read([
      app('denied', { folderPath: system, icon: candidate })
    ]);
    assert.equal(denied.apps[0].icon, '', candidate);
    assert.deepEqual(denied.reads, []);
    const symlink = await read([app('symlink', { folderPath: system })], {
      [system + '/icon.png']: { real: path.resolve(candidate) }
    });
    assert.equal(symlink.apps[0].icon, '', 'resolved path: ' + candidate);
    assert.deepEqual(symlink.reads, []);
  }
});
test('invalid or unavailable originals fall back without spending the visible budget', async () => {
  for (const entry of [
    { data: Buffer.alloc(0) },
    { data: png(32769) },
    { regular: false },
    { data: Buffer.from('not an image') },
    { size: 9, data: png(8) },
    { error: true }
  ]) {
    const result = await read(
      [
        app('invalid', { icon: 'invalid.png' }),
        ...Array.from({ length: 16 }, (_, i) => app('visible' + i))
      ],
      { [folder + '/invalid.png']: entry }
    );
    assert.equal(result.apps[0].icon, '');
    assert.equal(result.apps.filter((a) => a.icon).length, 16);
  }
});
