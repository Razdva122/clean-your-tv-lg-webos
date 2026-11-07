const assert = require('assert'),
  vm = require('vm'),
  fs = require('fs'),
  crypto = require('crypto'),
  path = require('path');
const keys = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
function signed(home, release, hd = false) {
  const m = {
    schema: 1,
    home,
    release,
    helper: '0.6.13',
    url: `https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/${release}/com.gathin.tvhome_${home}${hd ? '_720p' : ''}_all.ipk`,
    sha256: 'a'.repeat(64),
    notes: 'Test'
  };
  const b = Buffer.from(JSON.stringify(m));
  return {
    payload: b.toString('base64'),
    signature: crypto.sign('RSA-SHA256', b, keys.privateKey).toString('base64')
  };
}
const envelope = signed('1.2.1', 'v0.8.1');
envelope.previous = signed('1.2.0', 'v0.8.0');
const profile = {
  schema: 1,
  inventory: { apps: [], inputs: [] },
  config: { columns: 5, dockApps: [], hiddenApps: [] },
  settings: {}
};
let uhd = true,
  channels = [],
  methods = {},
  disk = {},
  calls = [],
  corrupt = false,
  homeVersion = '1.2.0',
  feed = envelope,
  streamError = false;
const store = {
  read: (n) => {
    if (corrupt && n === 'profile') throw Error('corrupt');
    return disk[n] || null;
  },
  write: (n, v) => {
    disk[n] = JSON.parse(JSON.stringify(v));
  }
};
function Service() {
  this.subscribe = (uri, p) => {
    calls.push({ uri, p });
    return {
      on: (event, cb) => {
        assert.equal(event, 'response');
        setImmediate(() => {
          cb({ payload: { statusText: 'Downloading…' } });
          cb({
            payload: streamError
              ? { returnValue: false, errorText: 'service disconnected' }
              : { returnValue: true, finished: true }
          });
        });
      },
      cancel: () => {}
    };
  };
  this.register = (n, fn) => {
    methods[n] = fn;
  };
  this.call = (uri, p, cb) => {
    calls.push({ uri, p });
    setImmediate(() => {
      if (uri.endsWith('/getSystemInfo'))
        cb({ payload: { returnValue: true, UHD: uhd } });
      else if (uri.endsWith('/checkRoot'))
        cb({ payload: { returnValue: true } });
      else if (uri.endsWith('/getAppInfo'))
        cb({
          payload: {
            returnValue: true,
            appInfo: {
              id: p.id,
              version: p.id === 'com.gathin.tvhome' ? homeVersion : '0.6.13'
            }
          }
        });
      else if (uri.endsWith('/pauseForUpdate'))
        cb({
          payload: {
            returnValue: true,
            state: {
              enabled: false,
              updatePause: { id: p.id, wasEnabled: false, confirmed: true }
            }
          }
        });
      else if (uri.endsWith('/importUpdatePause'))
        cb({
          payload: {
            returnValue: true,
            state: { enabled: false, updatePause: p.receipt }
          }
        });
      else if (uri.endsWith('/resumeAfterUpdate'))
        cb({
          payload: {
            returnValue: true,
            state: { enabled: false, completedUpdate: p.id }
          }
        });
      else if (uri.endsWith('/status'))
        cb({ payload: { returnValue: true, state: { enabled: true } } });
      else if (uri.endsWith('/install')) {
        throw Error('installer requires subscription');
      } else throw Error(uri);
    });
    return { cancel: () => {} };
  };
}
const dir = path.resolve('updater-service');
const context = {
  require: (n) =>
    n === 'webos-service'
      ? Service
      : n === 'fs'
        ? {
            readFileSync: () =>
              keys.publicKey.export({ type: 'spki', format: 'pem' })
          }
        : n === './storage'
          ? () => store
          : n === './transport'
            ? {
                get: async (url) => {
                  channels.push(url);
                  return JSON.stringify(feed);
                }
              }
            : require(path.join(dir, n)),
  __dirname: dir,
  Promise,
  setTimeout,
  clearTimeout
};
vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
function request(name, p = {}, id = 'com.gathin.tvhome') {
  return new Promise((resolve) =>
    methods[name]({
      payload: p,
      ls2Message: { applicationID: () => id },
      respond: resolve
    })
  );
}
(async () => {
  assert.equal((await request('check', {}, 'other.app')).returnValue, false);
  assert.equal(calls.length, 0);
  const offered = await request('check');
  assert.equal(offered.result.canInstall, true);
  assert(channels.at(-1).endsWith('/update.json'));
  for (const invalid of [null, 0, 1, 'TRUE', {}, []]) {
    uhd = invalid;
    const before = channels.length;
    assert.equal((await request('check')).returnValue, false);
    assert.equal(channels.length, before);
    assert.deepEqual(disk, {});
  }
  uhd = false;
  assert.equal(
    (await request('check')).returnValue,
    false,
    'valid FHD signature cannot substitute an HD offer'
  );
  assert(channels.at(-1).endsWith('/update-720p.json'));
  feed = signed('1.2.1', 'v0.8.1', true);
  feed.previous = signed('1.2.0', 'v0.8.0', true);
  assert.equal((await request('check')).result.canInstall, true);
  uhd = true;
  feed = envelope;
  feed = { ...envelope, signature: 'invalid' };
  assert.equal(
    (await request('install', { version: '1.2.1', profile })).returnValue,
    false
  );
  assert.deepEqual(disk, {}, 'bad signature must not write state');
  feed = { ...signed('1.2.2', 'v0.8.2'), previous: envelope.previous };
  assert.equal(
    (await request('install', { version: '1.2.1', profile })).returnValue,
    false
  );
  assert.deepEqual(disk, {}, 'changed release needs a new confirmation');
  feed = envelope;
  corrupt = true;
  assert.equal(
    (await request('install', { version: '1.2.1', profile })).returnValue,
    false
  );
  assert(!calls.some((x) => x.uri.endsWith('/install')));
  corrupt = false;
  vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
  const installed = await request('install', { version: '1.2.1', profile });
  assert.equal(
    installed.returnValue,
    true,
    'enabled Beta should be paused automatically'
  );
  assert.equal(installed.result.status, 'awaiting-launch');
  const args = calls.find((x) => x.uri.endsWith('/install')).p;
  assert.equal(args.id, 'com.gathin.tvhome');
  assert.equal(args.ipkHash, 'a'.repeat(64));
  assert.equal(args.subscribe, true);
  assert.deepEqual(disk.transaction.profile, profile);
  homeVersion = '1.2.1';
  assert.equal(
    (await request('healthy', { version: homeVersion })).result.status,
    'complete'
  );
  const originalTransaction = structuredClone(disk.transaction);
  const originalWrite = store.write;
  store.write = (name, value) => {
    if (name === 'transaction') throw Error('power lost before new journal');
    originalWrite(name, value);
  };
  feed = signed('1.2.2', 'v0.8.2');
  feed.previous = signed('1.2.1', 'v0.8.1');
  const laterProfile = {
    ...profile,
    config: { ...profile.config, columns: 6 }
  };
  assert.equal(
    (await request('install', { version: '1.2.2', profile: laterProfile }))
      .returnValue,
    false
  );
  assert.deepEqual(disk.transaction, originalTransaction);
  assert.deepEqual(
    (await request('restore')).result,
    profile,
    'failed next journal must retain the old rollback snapshot'
  );
  const recovery = await request('restore', { withTransaction: true });
  assert.equal(recovery.result.transaction.id, originalTransaction.id);
  assert.deepEqual(recovery.result.profile, profile);
  store.write = originalWrite;
  feed = envelope;
  assert(
    calls.findIndex((x) => x.uri.endsWith('/importUpdatePause')) <
      calls.findIndex((x) => x.uri.endsWith('/resumeAfterUpdate'))
  );
  assert(
    calls
      .filter((x) => x.uri.endsWith('/getAppInfo'))
      .every((x) => x.uri.startsWith('luna://org.webosbrew.hbchannel.service/'))
  );
  disk = {};
  homeVersion = '1.2.0';
  streamError = true;
  calls = [];
  vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
  const uncertain = await request('install', { version: '1.2.1', profile });
  assert.equal(uncertain.result.status, 'recovery-required');
  assert.equal(
    calls.filter((x) => x.uri.endsWith('/install')).length,
    1,
    'bus error must not start rollback'
  );
  // Home routing belongs to the independent, already running native helper.
  // Exercise the real persisted preference, boot claim and emergency markers;
  // renewal pause/resume must never replay an old Home preference or start it.
  const helperDir = fs.mkdtempSync(
    path.join(require('os').tmpdir(), 'cytv-update-helper-')
  );
  try {
    const createHome = require('../../native/app/home-control'),
      claim = require('../../native/service/boot-state').claim;
    for (const scenario of [
      { name: 'enabled', enabled: true },
      { name: 'disabled', enabled: false },
      {
        name: 'user turns Home off during update',
        enabled: true,
        turnOff: true
      },
      { name: 'emergency stop during update', enabled: true, emergency: true },
      { name: 'helper already stopped', enabled: true, blocked: true }
    ]) {
      for (const name of fs.readdirSync(helperDir))
        fs.unlinkSync(path.join(helperDir, name));
      let applied = [];
      const home = createHome(
        fs,
        helperDir,
        (v) => applied.push(v),
        () => {}
      );
      home.set(scenario.enabled);
      applied = [];
      const boot = { enabled: true, boot: 'boot-current', schema: 3 };
      fs.writeFileSync(
        path.join(helperDir, 'startup-state.json'),
        JSON.stringify(boot)
      );
      if (scenario.blocked)
        fs.writeFileSync(path.join(helperDir, 'blocked'), 'stopped');
      else fs.writeFileSync(path.join(helperDir, 'controller.pid'), '4242');
      const markers = () =>
        Object.fromEntries(
          fs
            .readdirSync(helperDir)
            .map((n) => [n, fs.readFileSync(path.join(helperDir, n), 'utf8')])
        );
      disk = {};
      calls = [];
      homeVersion = '1.2.0';
      streamError = false;
      feed = envelope;
      vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
      let expected = markers();
      assert.equal(
        (await request('install', { version: '1.2.1', profile })).result.status,
        'awaiting-launch',
        scenario.name
      );
      assert.deepEqual(
        markers(),
        expected,
        'installation must leave helper state intact: ' + scenario.name
      );
      if (scenario.turnOff) home.set(false);
      if (scenario.emergency) {
        fs.writeFileSync(path.join(helperDir, 'blocked'), 'stopped');
        fs.unlinkSync(path.join(helperDir, 'controller.pid'));
      }
      expected = markers();
      const appliedBefore = applied.slice();
      homeVersion = '1.2.1';
      // Restart the updater service before startup health and again before rollback.
      vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
      assert.equal(
        (await request('healthy', { version: homeVersion })).result.status,
        'complete',
        scenario.name
      );
      vm.runInNewContext(fs.readFileSync(dir + '/service.js', 'utf8'), context);
      assert.equal(
        (await request('rollback')).result.status,
        'rolled-back',
        scenario.name
      );
      assert.deepEqual(
        markers(),
        expected,
        'health/rollback must preserve latest helper state: ' + scenario.name
      );
      assert.deepEqual(
        applied,
        appliedBefore,
        'updater must not reapply Home routing: ' + scenario.name
      );
      assert.equal(
        home.enabled(),
        scenario.enabled && !scenario.turnOff,
        scenario.name
      );
      assert.equal(
        createHome(
          fs,
          helperDir,
          () => {},
          () => {}
        ).enabled(),
        home.enabled(),
        'persisted routing survives: ' + scenario.name
      );
      const blocked = fs.existsSync(path.join(helperDir, 'blocked'));
      assert.equal(
        claim(boot, 'boot-current', blocked),
        null,
        'no same-boot helper restart: ' + scenario.name
      );
      if (blocked)
        assert.equal(
          claim(boot, 'boot-next', blocked),
          null,
          'emergency stop wins across boots'
        );
      assert(
        calls
          .filter((x) => x.uri.endsWith('/install'))
          .every((x) => x.p.id === 'com.gathin.tvhome')
      );
      assert(
        !calls.some((x) =>
          /\/launch$|\/close$|\/setHomeControl$|\/enable$|\/disable$/.test(
            x.uri
          )
        ),
        'no helper restart or preference RPC'
      );
    }
  } finally {
    fs.rmSync(helperDir, { recursive: true, force: true });
  }
  console.log(
    'PASS No-root Home routing, live helper markers and emergency stop survive update, health, service restart and rollback'
  );
  console.log(
    'PASS service restart, fresh signed offer, changed release rejection, backup and installer wiring'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
