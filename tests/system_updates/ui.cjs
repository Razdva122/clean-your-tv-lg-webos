'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
function harness(options = {}) {
  const ids = {},
    events = {},
    calls = [],
    timers = new Map();
  let nextTimer = 0,
    confirmation,
    captures = 0,
    pendingCheck;
  const document = {
    activeElement: null,
    hidden: false,
    createElement(tag) {
      const element = {
        tagName: tag,
        hidden: false,
        disabled: false,
        children: [],
        textContent: '',
        scrollTop: 0,
        clientHeight: 400,
        appendChild(child) {
          this.children.push(child);
          return child;
        },
        setAttribute() {},
        addEventListener() {},
        focus() {
          document.activeElement = this;
          if (this.onfocus) this.onfocus();
        },
        click() {
          if (!this.disabled && !this.hidden && this.onclick) this.onclick();
        }
      };
      Object.defineProperty(element, 'id', {
        set(value) {
          ids[value] = element;
        },
        get() {
          return Object.keys(ids).find((key) => ids[key] === element);
        }
      });
      return element;
    },
    addEventListener(name, callback) {
      (events[name] || (events[name] = [])).push(callback);
    }
  };
  document.body = document.createElement('body');
  const offer = {
    edition: options.edition || 'no-root',
    release: 'v1.3.0',
    notes: 'Release notes',
    components: [
      { name: 'home', installed: '1.2.0', version: '1.3.0' },
      { name: 'helper', installed: '1.0.0', version: '1.1.0' }
    ],
    canInstall: options.canInstall !== false,
    reason: options.reason
  };
  let state = null;
  const translated = {};
  const i18n = {
    add(values) {
      for (const locale of Object.keys(values))
        Object.assign(
          translated[locale] || (translated[locale] = {}),
          values[locale]
        );
    },
    ready: (fn) => fn(),
    t: (s, p) =>
      (
        (translated[options.locale] && translated[options.locale][s]) ||
        s
      ).replace(/\{(\w+)\}/g, (_, k) => p[k]),
    confirm: (opts, accept) => {
      confirmation = { opts, accept };
    }
  };
  const window = {
    HomeI18n: i18n,
    HomeReleaseNotes: {
      render: (el, value) => {
        el.textContent = value;
      },
      scroll: (el, step) => {
        el.scrollTop += step * 300;
      }
    }
  };
  if (!options.standalone) {
    if (options.edition === 'root')
      window.RootProfile = {
        capture() {
          captures++;
          return Promise.resolve({ root: true });
        }
      };
    else
      window.HomeProfile = {
        capture(callback) {
          captures++;
          callback(options.captureError ? Error('Unreadable') : null, {
            home: true
          });
        }
      };
  }
  const context = {
    window,
    document,
    Promise,
    Error,
    JSON,
    PalmServiceBridge: function () {
      this.cancel = () => {};
      this.call = (uri, raw) => {
        const method = uri.split('/').pop(),
          payload = JSON.parse(raw);
        calls.push({ uri, method, payload });
        let result = method === 'check' ? offer : state;
        if (method === 'install')
          state = result = {
            id: 'tx',
            edition: offer.edition,
            release: 'v1.3.0',
            phase: 'downloading',
            components: []
          };
        if (method === 'rollback')
          state = result = { id: 'tx', phase: 'rolling-back' };
        if (method === 'check' && options.deferCheck) {
          pendingCheck = () => {
            this.onservicecallback(
              JSON.stringify({ returnValue: true, result: offer })
            );
          };
          return;
        }
        this.onservicecallback(
          JSON.stringify(
            options.unavailable
              ? { returnValue: false, errorText: 'Service does not exist' }
              : options.failure ||
                  (method === 'status' && options.statusFailure) ||
                  (method === 'check' && options.checkFailure)
                ? {
                    returnValue: false,
                    errorText:
                      options.failure ||
                      options.statusFailure ||
                      options.checkFailure
                  }
                : { returnValue: true, result }
          )
        );
      };
    },
    setTimeout(fn, ms) {
      const id = ++nextTimer;
      timers.set(id, { fn, ms });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    }
  };
  context.HomeI18n = i18n;
  if (options.locale)
    vm.runInNewContext(
      fs.readFileSync('launcher/catalogs.js', 'utf8'),
      context
    );
  vm.runInNewContext(
    fs.readFileSync('launcher/system-updates.js', 'utf8'),
    context
  );
  return {
    window,
    document,
    ids,
    calls,
    timers,
    offer,
    translated,
    finishCheck() {
      pendingCheck();
    },
    set checkFailure(value) {
      options.checkFailure = value;
    },
    set statusFailure(value) {
      options.statusFailure = value;
    },
    get confirmation() {
      return confirmation;
    },
    get captures() {
      return captures;
    },
    set state(value) {
      state = value;
    },
    key(code) {
      for (const fn of events.keydown || [])
        fn({
          keyCode: code,
          preventDefault() {},
          stopImmediatePropagation() {}
        });
    },
    async poll() {
      const timer = [...timers.values()].find((t) => t.ms === 1500);
      assert(timer, 'durable state must be polled');
      timers.clear();
      timer.fn();
      await settle();
    }
  };
}
async function settle() {
  for (let i = 0; i < 15; i++) await Promise.resolve();
}
(async () => {
  assert(
    fs.existsSync('launcher/system-updates.js'),
    'shared system update UI must exist'
  );
  for (const edition of ['no-root', 'root']) {
    const h = harness({ edition });
    let closed = 0;
    await h.window.SystemUpdates.open({
      edition,
      onClose() {
        closed++;
      }
    });
    await settle();
    assert(h.ids.systemUpdateVersions.textContent.includes('Home Helper'));
    assert(h.ids.systemUpdateVersions.textContent.includes('1.2.0'));
    assert.equal(h.ids.systemUpdateInstall.disabled, false);
    assert(
      h.calls.every((call) =>
        call.uri.startsWith('luna://com.cleanyourtv.system.updater.service/')
      )
    );
    h.ids.systemUpdateInstall.focus();
    h.key(39);
    assert.equal(h.document.activeElement, h.ids.systemUpdateRecovery);
    h.key(37);
    assert.equal(h.document.activeElement, h.ids.systemUpdateInstall);
    h.ids.systemUpdateInstall.click();
    assert(h.confirmation);
    assert.equal(h.captures, 0);
    assert.equal(h.calls.filter((c) => c.method === 'install').length, 0);
    h.confirmation.accept();
    h.confirmation.accept();
    await settle();
    assert.equal(h.captures, 1);
    const install = h.calls.find((c) => c.method === 'install');
    assert.equal(install.payload.edition, edition);
    assert.equal(install.payload.release, 'v1.3.0');
    assert.equal(
      install.payload.profile[edition === 'root' ? 'root' : 'home'],
      true
    );
    h.ids.systemUpdateBack.focus();
    h.state = { id: 'tx', phase: 'verifying', release: 'v1.3.0' };
    await h.poll();
    assert.equal(
      h.document.activeElement,
      h.ids.systemUpdateBack,
      'polling must preserve remote focus'
    );
    h.key(40);
    assert(h.ids.systemUpdateReading.scrollTop > 0);
    h.key(461);
    assert.equal(closed, 1);
    assert(h.ids.systemUpdates.hidden);
    assert(![...h.timers.values()].some((t) => t.ms === 1500));
  }
  const russian = harness({ locale: 'ru' });
  await russian.window.SystemUpdates.open({ edition: 'no-root' });
  assert.equal(russian.ids.systemUpdateInstall.textContent, 'Обновить всё');
  russian.ids.systemUpdateInstall.click();
  assert.equal(russian.confirmation.opts.title, 'Install system update?');
  assert(!russian.ids.systemUpdateStatus.textContent.includes('signed system'));
  const restoreError = harness();
  await restoreError.window.SystemUpdates.open({
    edition: 'root',
    recovery: true,
    error: 'Profile restoration failed'
  });
  await restoreError.poll();
  assert(
    restoreError.ids.systemUpdateStatus.textContent.includes(
      'Profile restoration failed'
    ),
    'polling must retain profile restoration errors until an explicit refresh'
  );
  restoreError.ids.systemUpdateRecovery.click();
  await settle();
  assert(
    !restoreError.ids.systemUpdateStatus.textContent.includes(
      'Profile restoration failed'
    )
  );
  for (const edition of ['no-root', 'root']) {
    const current = harness({ edition });
    current.offer.components.forEach((c) => {
      c.version = c.installed;
    });
    await current.window.SystemUpdates.open({ edition });
    assert(
      current.ids.systemUpdateInstall.disabled,
      'same component versions from an older supervisor must not offer installation'
    );
    assert(
      current.ids.systemUpdateStatus.textContent.includes(
        'All components are up to date.'
      )
    );
    current.ids.systemUpdateInstall.click();
    assert.equal(current.confirmation, undefined);
  }
  const checking = harness({ deferCheck: true });
  const opening = checking.window.SystemUpdates.open({ edition: 'no-root' });
  await settle();
  assert(
    checking.ids.systemUpdateInstall.disabled,
    'pending availability must not permit installation'
  );
  checking.ids.systemUpdateInstall.click();
  assert.equal(checking.confirmation, undefined);
  checking.finishCheck();
  await opening;
  assert.equal(
    checking.ids.systemUpdateInstall.disabled,
    false,
    'a verified newer offer enables installation after the check'
  );
  const unrooted = harness({ canInstall: false, reason: 'root-required' });
  await unrooted.window.SystemUpdates.open({ edition: 'no-root' });
  assert(unrooted.ids.systemUpdateInstall.disabled);
  assert(
    unrooted.ids.systemUpdateStatus.textContent.includes('computer'),
    'unrooted installation requires the computer update path'
  );
  const migration = harness({
    edition: 'root',
    locale: 'ru',
    canInstall: false,
    reason: 'Infrastructure inventory changed; computer migration required'
  });
  await migration.window.SystemUpdates.open({ edition: 'root' });
  assert(migration.ids.systemUpdateInstall.disabled);
  assert(
    migration.ids.systemUpdateStatus.textContent.includes(
      'миграция с компьютера'
    )
  );
  migration.ids.systemUpdateInstall.click();
  assert(!migration.calls.some((c) => c.method === 'install'));
  const stale = harness();
  await stale.window.SystemUpdates.open({ edition: 'no-root' });
  stale.ids.systemUpdateInstall.click();
  stale.key(461);
  stale.confirmation.accept();
  await settle();
  assert.equal(
    stale.captures,
    0,
    'closed panels must invalidate pending confirmation'
  );
  const broken = harness({ captureError: true });
  await broken.window.SystemUpdates.open({ edition: 'no-root' });
  broken.ids.systemUpdateInstall.click();
  broken.confirmation.accept();
  await settle();
  assert(
    !broken.calls.some((c) => c.method === 'install'),
    'incomplete capture must block installation'
  );
  const standalone = harness({ standalone: true });
  standalone.state = { id: 'old', phase: 'complete', canRollback: true };
  await standalone.window.SystemUpdates.open({
    edition: 'no-root',
    standalone: true,
    recovery: true
  });
  assert(standalone.ids.systemUpdateInstall.disabled);
  assert(!standalone.ids.systemUpdateRollback.disabled);
  standalone.ids.systemUpdateRollback.click();
  assert(
    standalone.confirmation.opts.message.includes('components') &&
      standalone.confirmation.opts.message.includes('Settings changed')
  );
  standalone.confirmation.accept();
  await settle();
  assert(standalone.calls.some((c) => c.method === 'rollback'));
  const resumeFailure = harness();
  resumeFailure.state = {
    id: 'tx',
    phase: 'complete',
    homeResume: { status: 'failed', error: 'route restore rejected' }
  };
  await resumeFailure.window.SystemUpdates.open({ edition: 'root' });
  assert(
    resumeFailure.ids.systemUpdateStatus.textContent.includes(
      'Home control could not be restored automatically'
    ),
    'installation success must not hide Home restoration failure'
  );
  const ambiguous = harness({ standalone: true });
  ambiguous.state = {
    id: 'unknown',
    phase: 'recovery-required',
    canRollback: false
  };
  await ambiguous.window.SystemUpdates.open({
    edition: 'root',
    standalone: true,
    recovery: true
  });
  assert(
    ambiguous.ids.systemUpdateRollback.disabled,
    'unknown installer outcome must not offer rollback'
  );
  const missing = harness({ unavailable: true });
  let fallback = 0;
  await missing.window.SystemUpdates.open({
    edition: 'root',
    fallback() {
      fallback++;
    }
  });
  assert.equal(fallback, 1);
  assert(!missing.ids.systemUpdates || missing.ids.systemUpdates.hidden);
  const failure = harness({ failure: 'Journal is unreadable' });
  let unsafeFallback = 0;
  await failure.window.SystemUpdates.open({
    edition: 'root',
    fallback() {
      unsafeFallback++;
    }
  });
  assert.equal(
    unsafeFallback,
    0,
    'unreadable supervisor cannot activate competing legacy updater'
  );
  const missingCache = harness({ failure: 'Baseline not found' });
  let cacheFallback = 0;
  await missingCache.window.SystemUpdates.open({
    edition: 'root',
    fallback() {
      cacheFallback++;
    }
  });
  assert.equal(
    cacheFallback,
    0,
    'missing data is not evidence that the service is absent'
  );
  const badCheck = harness({
    checkFailure: 'Unknown service in candidate metadata'
  });
  let checkFallback = 0;
  await badCheck.window.SystemUpdates.open({
    edition: 'root',
    fallback() {
      checkFallback++;
    }
  });
  assert.equal(
    checkFallback,
    0,
    'an available supervisor must never fall through to a competing legacy installer'
  );
  const retained = harness({
    checkFailure:
      'Update information could not be verified. Nothing was installed.'
  });
  await retained.window.SystemUpdates.open({ edition: 'root' });
  const checkMessage = retained.ids.systemUpdateStatus.textContent;
  await retained.poll();
  assert.equal(
    retained.ids.systemUpdateStatus.textContent,
    checkMessage,
    'a successful status poll must preserve a failed update check'
  );
  retained.ids.systemUpdateCheck.click();
  await settle();
  assert.equal(
    retained.ids.systemUpdateStatus.textContent,
    checkMessage,
    'a failed explicit retry must retain the failure'
  );
  retained.statusFailure = 'Status unavailable';
  await retained.poll();
  retained.statusFailure = null;
  await retained.poll();
  assert.equal(
    retained.ids.systemUpdateStatus.textContent,
    checkMessage,
    'status recovery must not clear the check failure'
  );
  retained.checkFailure = null;
  retained.ids.systemUpdateCheck.click();
  await settle();
  assert(
    !retained.ids.systemUpdateStatus.textContent.includes(
      'could not be verified'
    ),
    'a successful explicit check clears its failure'
  );
  retained.checkFailure =
    'Update information could not be verified. Nothing was installed.';
  retained.ids.systemUpdateCheck.click();
  await settle();
  assert(
    retained.ids.systemUpdateInstall.disabled,
    'a failed check must disable a previously cached offer'
  );
  await retained.poll();
  assert(retained.ids.systemUpdateInstall.disabled);
  retained.ids.systemUpdateRecovery.click();
  await settle();
  assert(
    retained.ids.systemUpdateStatus.textContent.includes(
      'No previous update is saved for rollback yet.'
    )
  );
  const statusOnly = harness({ statusFailure: 'Status unavailable' });
  await statusOnly.window.SystemUpdates.open({ edition: 'root' });
  assert(
    statusOnly.ids.systemUpdateStatus.textContent.includes('Status unavailable')
  );
  statusOnly.statusFailure = null;
  await statusOnly.poll();
  assert(
    !statusOnly.ids.systemUpdateStatus.textContent.includes(
      'Status unavailable'
    ),
    'successful status refresh clears a status failure'
  );
  const emptyRecovery = harness({ checkFailure: 'Network failure' });
  await emptyRecovery.window.SystemUpdates.open({
    edition: 'root',
    recovery: true
  });
  assert(
    !emptyRecovery.calls.some((call) => call.method === 'check'),
    'recovery open must rely on local status without checking the network'
  );
  assert(
    emptyRecovery.ids.systemUpdateStatus.textContent.includes(
      'No previous update is saved for rollback yet.'
    ),
    'null recovery status needs an explanation'
  );
  assert(emptyRecovery.ids.systemUpdateRollback.disabled);
  assert.equal(
    emptyRecovery.ids.systemUpdateRecovery.textContent,
    'Refresh status'
  );
  emptyRecovery.ids.systemUpdateRecovery.click();
  await settle();
  await emptyRecovery.poll();
  assert(!emptyRecovery.calls.some((call) => call.method === 'check'));
  emptyRecovery.ids.systemUpdateRecovery.focus();
  emptyRecovery.key(39);
  assert.equal(
    emptyRecovery.document.activeElement,
    emptyRecovery.ids.systemUpdateBack
  );
  emptyRecovery.key(37);
  assert.equal(
    emptyRecovery.document.activeElement,
    emptyRecovery.ids.systemUpdateRecovery
  );
  const progress = harness({
    checkFailure: 'CalledProcessError: private policy command'
  });
  progress.state = { id: 'tx', phase: 'installing' };
  await progress.window.SystemUpdates.open({ edition: 'root' });
  assert(
    progress.ids.systemUpdateStatus.textContent.startsWith(
      'Update state: installing.'
    ),
    'a failed offer check must not hide durable installation progress'
  );
  assert(
    progress.ids.systemUpdateStatus.textContent.includes(
      'Update information could not be verified.'
    ),
    'the check failure remains visible beside transaction progress'
  );
  assert(
    !progress.ids.systemUpdateStatus.textContent.includes(
      'Nothing was installed'
    ),
    'a failed check cannot make claims about an existing transaction'
  );
  progress.state = { id: 'tx', phase: 'complete' };
  await progress.poll();
  assert(
    progress.ids.systemUpdateStatus.textContent.startsWith('Update complete.'),
    'completion must replace progress even when the check failure remains'
  );
  assert(
    progress.ids.systemUpdateStatus.textContent.includes(
      'Update information could not be verified.'
    )
  );
  assert(
    !progress.ids.systemUpdateStatus.textContent.includes(
      'Nothing was installed'
    )
  );
  const newMessages = [
    'No previous update is saved for rollback yet.',
    'Update information is not available yet. Try again later.',
    'Could not connect to check for updates. Check your connection and try again.',
    'Update information could not be verified. Nothing was installed.',
    'Could not connect to the update server. Nothing was installed.',
    'Update information is not available yet. Nothing was installed.',
    'Update information could not be verified.',
    'System updater removal is in progress. Continue removal from the computer.'
  ];
  for (const locale of [
    'en',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'zh-Hans',
    'zh-Hant'
  ]) {
    for (const reason of ['feed-unavailable', 'connection-error']) {
      const installed = harness({ locale, canInstall: false, reason });
      installed.offer.release = null;
      installed.offer.notes = '';
      installed.offer.components = [
        { name: 'root', installed: '2.3.4', version: null }
      ];
      await installed.window.SystemUpdates.open({ edition: 'root' });
      assert(installed.ids.systemUpdateVersions.textContent.includes('2.3.4'));
      assert(
        !/undefined|null|→/.test(
          installed.ids.systemUpdateVersions.textContent
        ),
        'installed-only rows must not render a missing available version'
      );
      assert(installed.ids.systemUpdateInstall.disabled);
      assert(
        !installed.ids.systemUpdateStatus.textContent.includes(reason),
        'failure reasons need friendly localized messages'
      );
      for (const source of newMessages)
        assert(
          installed.translated[locale][source],
          locale + ' must translate ' + source
        );
      assert(
        installed.ids.systemUpdateStatus.textContent.includes(
          installed.translated[locale][
            newMessages[reason === 'feed-unavailable' ? 1 : 2]
          ]
        ),
        'the unavailable reason must explain what the user can do'
      );
      assert(
        !installed.ids.systemUpdateStatus.textContent.includes(
          installed.translated[locale]['All components are up to date.']
        ),
        'a missing candidate cannot claim installed components are current'
      );
      if (locale !== 'en')
        for (const source of newMessages)
          assert.notEqual(installed.translated[locale][source], source);
    }
  }
  console.log(
    'PASS shared system UI editions, confirmation/capture, durable polling, recovery, absence fallback and remote navigation'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
