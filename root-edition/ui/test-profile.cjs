const assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
const path = __dirname + '/root-profile-data.js';
assert(
  fs.existsSync(path),
  'Root-specific bounded profile validator is missing'
);
const data = require(path),
  icon = 'data:image/png;base64,YWJj';
const profile = {
  schema: 1,
  inventory: {
    apps: [{ id: 'app.one', title: 'One', icon }],
    inputs: [{ appId: 'hdmi.one', label: 'Console' }]
  },
  config: {
    columns: 5,
    dockApps: ['app.one'],
    hiddenApps: [],
    liveTvApp: 'tv'
  },
  settings: { 'tvhome.order': '{"dock":"app.one","ids":["app.one"]}' }
};
assert.deepStrictEqual(data.validate(profile), profile);
const translatedProfile = JSON.parse(JSON.stringify(profile));
translatedProfile.settings['tvhome.language'] = 'ko';
assert.deepStrictEqual(data.validate(translatedProfile), translatedProfile);
assert.throws(() =>
  data.validate({ ...profile, settings: { 'tvhome.language': 'unsupported' } })
);
for (const mutate of [
  (p) => (p.renewal = {}),
  (p) => (p.config.extra = true),
  (p) => (p.inventory.apps[0].icon = 'icons/missing.png'),
  (p) => p.inventory.apps.push(p.inventory.apps[0]),
  (p) => (p.config.hiddenApps = ['x', 'x']),
  (p) => (p.inventory.inputs[0].path = '/tmp'),
  (p) => (p.inventory.apps[0].title = 'я'.repeat(129)),
  (p) => (p.inventory.apps[0].icon = 'data:image/png;base64,YQ='),
  (p) => (p.settings['tvhome.order'] = 'broken'),
  (p) => (p.settings['tvhome.order'] = '{"dock":"","ids":["same","same"]}'),
  (p) => (p.inventory.apps[0].iconColor = ''),
  (p) => (p.inventory.apps[0].iconColor = ['#123456'])
]) {
  const p = JSON.parse(JSON.stringify(profile));
  mutate(p);
  assert.throws(() => data.validate(p));
}
const tick = () => new Promise((r) => setImmediate(r));
function harness({
  restore = null,
  saved = null,
  tiles = ['app.one'],
  version = '0.0.1',
  packaged = profile.inventory,
  unavailable = false,
  memory = new Map(),
  iconStatus = 200,
  i18n = false
} = {}) {
  const calls = [],
    scripts = [],
    errors = [];
  if (saved !== null)
    memory.set(
      data.key,
      typeof saved === 'string' ? saved : JSON.stringify(saved)
    );
  const storage = {
    getItem: (k) => (memory.has(k) ? memory.get(k) : null),
    setItem: (k, v) => memory.set(k, v),
    removeItem: (k) => memory.delete(k)
  };
  const window = {
    AppLibrary: require('../../launcher/app-library.js'),
    ROOT_VERSION: version,
    RootProfileData: data,
    TV_APPS: packaged,
    CONFIG: profile.config,
    RootUpdates: {
      rpc: async (method, payload) => {
        calls.push([method, payload]);
        if (unavailable) throw Error('not provisioned');
        return restore;
      },
      open: (o) => errors.push(o),
      confirmLaunch: (t) => calls.push(['confirmLaunch', t])
    }
  };
  if (i18n) {
    window.HomeI18n = {
      preference: () => memory.get('tvhome.language') || 'auto',
      refresh() {},
      t: (s) => s
    };
    window.location = {
      reload() {
        calls.push(['reload', memory.get('tvhome.root.restored.v1')]);
      }
    };
  }
  const document = {
    body: {
      appendChild: (s) => {
        scripts.push(s);
      }
    },
    createElement: () => ({}),
    querySelectorAll: (selector) =>
      (selector.includes('[data-app-id]') ? tiles : tiles.concat([null])).map(
        (id) => ({ getAttribute: () => id })
      )
  };
  const ctx = {
    window,
    document,
    localStorage: storage,
    Promise,
    setTimeout,
    clearTimeout,
    XMLHttpRequest: class {
      open(method, url) {
        assert.strictEqual(method, 'GET');
        assert.strictEqual(url, 'icons/one.png');
      }
      send() {
        this.status = iconStatus;
        this.response = { size: 3 };
        this.onload();
      }
    },
    FileReader: class {
      readAsDataURL() {
        this.result = icon;
        this.onload();
      }
    }
  };
  vm.runInNewContext(
    fs.readFileSync(__dirname + '/root-profile.js', 'utf8'),
    ctx
  );
  return { window, calls, scripts, errors, memory };
}
(async () => {
  for (const [before, after] of [
    ['ru', 'ko'],
    ['en', 'cs'],
    ['cs', 'auto'],
    ['en', 'auto'],
    ['auto', 'en']
  ]) {
    const languageProfile = JSON.parse(JSON.stringify(profile));
    languageProfile.settings['tvhome.language'] = after;
    const memory = new Map([['tvhome.language', before]]),
      restore = {
        profile: languageProfile,
        transaction: 'language-change',
        version: '0.0.1',
        phase: 'verifying'
      };
    let changed = harness({ restore, memory, i18n: true });
    await tick();
    assert.deepStrictEqual(
      changed.calls.filter((c) => c[0] === 'reload'),
      [['reload', 'language-change:0.0.1']],
      'changed preference reloads only after restore marker is durable'
    );
    assert.strictEqual(
      changed.scripts.length,
      0,
      'must not render launcher before reload'
    );
    changed = harness({ restore, memory, i18n: true });
    await tick();
    assert(
      !changed.calls.some((c) => c[0] === 'reload'),
      'restored marker prevents a reload loop'
    );
    assert.strictEqual(changed.scripts.length, 1);
  }
  const unchangedMemory = new Map([['tvhome.language', 'ko']]);
  const unchanged = harness({
    restore: {
      profile: translatedProfile,
      transaction: 'unchanged',
      version: '0.0.1',
      phase: 'complete'
    },
    memory: unchangedMemory,
    i18n: true
  });
  await tick();
  assert(!unchanged.calls.some((c) => c[0] === 'reload'));
  assert.strictEqual(unchanged.scripts.length, 1);
  let localized = harness({
    restore: {
      profile: translatedProfile,
      transaction: 'lang',
      version: '0.0.1',
      phase: 'complete'
    }
  });
  await tick();
  assert.strictEqual(localized.memory.get('tvhome.language'), 'ko');
  assert.strictEqual(
    (await localized.window.RootProfile.capture()).settings['tvhome.language'],
    'ko'
  );
  localized.memory.set('tvhome.language', 'ru');
  localized = harness({
    memory: localized.memory,
    restore: {
      profile: translatedProfile,
      transaction: 'lang',
      version: '0.0.1',
      phase: 'complete'
    }
  });
  await tick();
  assert.strictEqual(localized.memory.get('tvhome.language'), 'ru');
  let h = harness({
    restore: {
      profile,
      transaction: 'tx',
      version: '0.0.1',
      phase: 'verifying'
    }
  });
  await tick();
  assert.strictEqual(h.scripts.length, 1);
  assert.deepStrictEqual(h.window.TV_APPS, profile.inventory);
  assert.strictEqual(
    h.memory.get('tvhome.order'),
    profile.settings['tvhome.order']
  );
  h.window.RootLauncherRendered = true;
  h.scripts[0].onload();
  await tick();
  assert.deepStrictEqual(
    h.calls.map((x) => x[0]),
    ['restoreProfile', 'ready', 'confirm']
  );
  assert.strictEqual(h.calls[1][1].transaction, 'tx');
  assert.strictEqual(h.calls[1][1].version, '0.0.1');
  const captured = await h.window.RootProfile.capture();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(captured)), profile);
  assert.strictEqual(h.calls.length, 3);
  const legacyAppearance = new Map([
    ['tvhome.columns.v1', '{"version":1,"columns":4}'],
    ['tvhome.theme.choice.v1', '{"id":"builtin:alpine","title":"Alpine"}'],
    ['tvhome.theme.trial.v1', '{"kind":"trial"}'],
    [
      'tvhome.wallpaper.preferences.v1',
      '[{"id":"builtin:alpine","quality":"image","dim":0.4}]'
    ]
  ]);
  harness({
    restore: {
      profile,
      transaction: 'legacy-appearance',
      version: '0.0.1',
      phase: 'verifying'
    },
    memory: legacyAppearance
  });
  await tick();
  for (const key of [
    'tvhome.columns.v1',
    'tvhome.theme.choice.v1',
    'tvhome.theme.trial.v1',
    'tvhome.wallpaper.preferences.v1'
  ])
    assert(
      !legacyAppearance.has(key),
      'legacy Root restore still resets appearance to Classic'
    );
  // Effective Alpine geometry must never be captured as an explicit legacy choice.
  const captureHost = harness({ packaged: profile.inventory });
  await tick();
  captureHost.window.CONFIG = JSON.parse(JSON.stringify(profile.config));
  const captureStorage = {
    getItem: (k) =>
      captureHost.memory.has(k) ? captureHost.memory.get(k) : null,
    setItem: (k, v) => captureHost.memory.set(k, v),
    removeItem: (k) => captureHost.memory.delete(k)
  };
  const layout = require('../../launcher/home-layout.js').create(
    captureStorage,
    captureHost.window.CONFIG,
    data
  );
  layout.setThemeLayout({
    preset: 'scenic-grid',
    columns: 8,
    allowColumnOverride: false,
    spacingScale: 1,
    textScale: 1,
    focusScale: 1.1
  });
  const automaticCapture = await captureHost.window.RootProfile.capture();
  assert.strictEqual(
    automaticCapture.config.columns,
    5,
    'profile capture stores By theme, not Alpine effective eight'
  );
  const captureReload = harness({ saved: automaticCapture });
  await tick();
  const restoredLayout = require('../../launcher/home-layout.js').create(
    {
      getItem: (k) =>
        captureReload.memory.has(k) ? captureReload.memory.get(k) : null
    },
    captureReload.window.CONFIG,
    data
  );
  restoredLayout.setThemeLayout({
    preset: 'channel-list',
    columns: 1,
    spacingScale: 1,
    textScale: 1,
    focusScale: 1.1
  });
  assert.strictEqual(
    restoredLayout.state().columns,
    1,
    'profile reload permits Channel default'
  );
  layout.setThemeLayout({
    preset: 'channel-list',
    columns: 1,
    spacingScale: 1,
    textScale: 1,
    focusScale: 1.1
  });
  layout.setColumns(4);
  assert.strictEqual(
    (await captureHost.window.RootProfile.capture()).config.columns,
    4,
    'explicit column choice remains in Root backup'
  );
  layout.setColumns(null);
  assert.strictEqual(
    (await captureHost.window.RootProfile.capture()).config.columns,
    5,
    'By theme reset removes stale effective value from Root backup'
  );
  const layoutMemory = new Map([
    [
      'tvhome.layout',
      JSON.stringify({
        version: 1,
        ids: ['app.one'],
        hidden: ['app.one'],
        catalog: profile.inventory.apps
      })
    ]
  ]);
  h = harness({
    restore: {
      profile,
      transaction: 'layout',
      version: '0.0.1',
      phase: 'verifying'
    },
    memory: layoutMemory,
    tiles: []
  });
  await tick();
  h.window.RootLauncherRendered = true;
  h.scripts[0].onload();
  await tick();
  assert(
    h.calls.some((x) => x[0] === 'ready'),
    'saved layout visibility must match the launcher model'
  );
  h = harness({
    restore: {
      profile,
      transaction: 'tx',
      version: '0.0.1',
      phase: 'verifying'
    },
    tiles: ['wrong']
  });
  await tick();
  h.window.RootLauncherRendered = true;
  h.scripts[0].onload();
  await tick();
  assert(!h.calls.some((x) => x[0] === 'ready'));
  assert(h.errors.length);
  h = harness({
    restore: {
      profile,
      transaction: 'tx',
      version: '0.0.2',
      phase: 'verifying'
    }
  });
  await tick();
  assert.strictEqual(h.scripts.length, 0);
  assert(h.errors.length);
  h = harness({ saved: '{broken' });
  await tick();
  assert.strictEqual(h.scripts.length, 0);
  assert(h.errors.length);
  h = harness({ packaged: { apps: [], inputs: [] }, unavailable: true });
  await tick();
  assert.strictEqual(h.scripts.length, 0);
  assert(h.errors.length);
  h = harness({ restore: null, packaged: { apps: [], inputs: [] } });
  await tick();
  assert.strictEqual(h.scripts.length, 1);
  h.scripts[0].onload();
  await tick();
  assert(!h.calls.some((x) => x[0] === 'ready'));
  const empty = JSON.parse(JSON.stringify(profile));
  empty.config.hiddenApps = ['app.one'];
  h = harness({
    restore: {
      profile: empty,
      transaction: 'empty',
      version: '0.0.1',
      phase: 'verifying'
    },
    tiles: []
  });
  await tick();
  h.scripts[0].onload();
  await tick();
  assert(!h.calls.some((x) => x[0] === 'ready'));
  assert(h.errors.length);
  h = harness({
    restore: {
      profile: empty,
      transaction: 'empty',
      version: '0.0.1',
      phase: 'verifying'
    },
    tiles: []
  });
  await tick();
  h.window.RootLauncherRendered = true;
  h.scripts[0].onload();
  await tick();
  assert(h.calls.some((x) => x[0] === 'ready'));
  h = harness({
    restore: {
      profile,
      transaction: 'rollback',
      version: '0.0.1',
      phase: 'verifying-rollback'
    }
  });
  await tick();
  h.window.RootLauncherRendered = true;
  h.scripts[0].onload();
  await tick();
  assert(h.calls.some((x) => x[0] === 'ready'));
  assert(!h.calls.some((x) => x[0] === 'confirm'));
  h = harness({
    restore: {
      profile,
      transaction: 'stable',
      version: '0.0.1',
      phase: 'complete'
    }
  });
  await tick();
  const memory = h.memory;
  memory.set('tvhome.order', '{"dock":"app.one","ids":[]}');
  h = harness({
    memory,
    restore: {
      profile,
      transaction: 'stable',
      version: '0.0.1',
      phase: 'complete'
    }
  });
  await tick();
  assert.strictEqual(memory.get('tvhome.order'), '{"dock":"app.one","ids":[]}');
  memory.delete(data.key);
  h = harness({
    memory,
    restore: {
      profile,
      transaction: 'stable',
      version: '0.0.1',
      phase: 'complete'
    }
  });
  await tick();
  assert.strictEqual(
    memory.get('tvhome.order'),
    profile.settings['tvhome.order']
  );
  const abortedMemory = new Map([
    [data.key, JSON.stringify(profile)],
    ['tvhome.order', '{"dock":"app.one","ids":[]}']
  ]);
  h = harness({
    memory: abortedMemory,
    restore: {
      profile,
      transaction: 'aborted',
      version: '0.0.1',
      phase: 'aborted'
    }
  });
  await tick();
  assert.strictEqual(
    abortedMemory.get('tvhome.order'),
    '{"dock":"app.one","ids":[]}'
  );
  const packaged = JSON.parse(JSON.stringify(profile.inventory));
  // Fresh discovery commonly supplies an empty optional color. Capture must
  // omit noncanonical cosmetic metadata without weakening stored-profile reads.
  for (const color of ['', 'red', '#123', '#12GG56', null, ['#123456']]) {
    const discovered = JSON.parse(JSON.stringify(profile.inventory));
    discovered.apps[0].iconColor = color;
    const fresh = harness({ packaged: discovered });
    await tick();
    const captured = await fresh.window.RootProfile.capture({ system: true });
    assert(!Object.hasOwn(captured.inventory.apps[0], 'iconColor'));
    assert.deepStrictEqual(fresh.window.TV_APPS.apps[0].iconColor, color);
    data.validate(captured);
  }
  const colored = JSON.parse(JSON.stringify(profile.inventory));
  colored.apps[0].iconColor = '#12aBcF';
  const validColor = harness({ packaged: colored });
  await tick();
  assert.strictEqual(
    (await validColor.window.RootProfile.capture()).inventory.apps[0].iconColor,
    '#12aBcF'
  );
  packaged.apps[0].icon = 'icons/one.png';
  h = harness({ packaged });
  await tick();
  assert.strictEqual(
    (await h.window.RootProfile.capture()).inventory.apps[0].icon,
    icon
  );
  assert.deepStrictEqual(
    h.calls.map((x) => x[0]),
    ['restoreProfile']
  );
  h = harness({ packaged, iconStatus: 404 });
  await tick();
  await assert.rejects(h.window.RootProfile.capture(), /missing/);
  assert.deepStrictEqual(
    h.calls.map((x) => x[0]),
    ['restoreProfile']
  );
  console.log(
    'PASS Root strict profile capture, restore before launcher, exact tiles/version, corrupt and unavailable backup, legitimate empty grid'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
