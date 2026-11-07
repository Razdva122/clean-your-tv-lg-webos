const assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
assert(
  fs.existsSync(__dirname + '/root-updates.js'),
  'Root update dialog is missing'
);
const tick = () => new Promise((r) => setImmediate(r));
function harness({
  recovery = false,
  unavailable = false,
  delayed = false
} = {}) {
  const elements = [],
    listeners = [],
    calls = [],
    timers = [],
    pending = [];
  let now = 0,
    focus = 'previous',
    tx = null,
    captures = 0,
    offer = {
      installed: { version: '0.0.1' },
      candidate: { version: '0.0.2', notes: 'Release notes' },
      canInstall: true
    };
  class E {
    constructor(tag) {
      this.tag = tag;
      this.children = [];
      this.hidden = false;
      this.scrollTop = 0;
      this.clientHeight = 500;
      this.scrollHeight = 2000;
      elements.push(this);
    }
    appendChild(e) {
      this.children.push(e);
      return e;
    }
    setAttribute() {}
    focus() {
      focus = this;
      document.activeElement = this;
      this.focusCount = (this.focusCount || 0) + 1;
      if (this.onfocus) this.onfocus();
    }
    removeChild(e) {
      this.children.splice(this.children.indexOf(e), 1);
    }
  }
  const document = {
    body: new E('body'),
    activeElement: {
      focus() {
        focus = 'previous';
      }
    },
    createElement: (t) => new E(t),
    createTextNode: (text) => ({ textContent: text }),
    addEventListener: (name, f) => listeners.push(f)
  };
  let confirmation;
  const window = {
    HomeI18n: {
      t: (s, p) =>
        String(s).replace(/\{(\w+)\}/g, (_, k) =>
          p && p[k] !== undefined ? p[k] : '{' + k + '}'
        ),
      confirm: (options, accept) => {
        confirmation = { options, accept };
      }
    },
    ROOT_VERSION: '0.0.1',
    RenewalPanel: {
      open() {
        calls.push(['settings']);
      }
    }
  };
  if (!recovery)
    window.RootProfile = {
      capture: async () => {
        captures++;
        return { snapshot: true };
      }
    };
  const context = {
    window,
    document,
    Promise,
    Date: { now: () => now },
    setTimeout: (f, ms) => {
      timers.push({ f, ms });
      return timers.length;
    },
    clearTimeout() {},
    PalmServiceBridge: class {
      cancel() {}
      call(uri, raw) {
        const method = uri.split('/').pop(),
          p = JSON.parse(raw);
        assert(uri.startsWith('luna://com.cleanyourtv.root.updater.service/'));
        calls.push([method, p]);
        let result;
        if (method === 'check') result = offer;
        if (method === 'status') result = tx;
        if (method === 'install')
          result = tx = { id: 'install-tx', phase: 'preparing' };
        if (method === 'confirm')
          result = tx = {
            id: 'new-tx',
            phase: 'complete',
            oldRoute: { active: true }
          };
        if (method === 'reconcile') result = tx;
        if (method === 'rollback')
          result = tx = { id: 'old', phase: 'rolling-back' };
        const reply = () =>
          this.onservicecallback(
            JSON.stringify(
              unavailable
                ? { returnValue: false, errorText: 'Service does not exist' }
                : { returnValue: true, result }
            )
          );
        if (delayed && method === 'status') pending.push(reply);
        else reply();
      }
    }
  };
  if (fs.existsSync(__dirname + '/../../launcher/release-notes.js'))
    vm.runInNewContext(
      fs.readFileSync(__dirname + '/../../launcher/release-notes.js', 'utf8'),
      context
    );
  vm.runInNewContext(
    fs.readFileSync(__dirname + '/root-updates.js', 'utf8'),
    context
  );
  const api = window.RootUpdates;
  const buttons = () => elements.filter((e) => e.tag === 'button' && !e.hidden);
  const button = (label) => buttons().find((b) => b.textContent === label);
  return {
    get confirmation() {
      return confirmation;
    },
    api,
    calls,
    timers,
    elements,
    buttons,
    button,
    resolve: () => pending.splice(0).forEach((f) => f()),
    get focus() {
      return focus;
    },
    get captures() {
      return captures;
    },
    advance: (ms) => (now += ms),
    setTx: (t) => (tx = t),
    setOffer: (o) => (offer = o),
    poll: () =>
      timers
        .filter((t) => t.ms === 1500)
        .at(-1)
        .f(),
    key(code) {
      listeners.forEach((f) =>
        f({ keyCode: code, preventDefault() {}, stopImmediatePropagation() {} })
      );
    }
  };
}
(async () => {
  let h = harness();
  h.api.open();
  await tick();
  assert.strictEqual(h.calls.filter((c) => c[0] === 'check').length, 1);
  assert(!h.button('Try again'));
  assert(h.button('Update'));
  assert(h.button('Update').disabled === false);
  assert.strictEqual(h.captures, 0);
  h.button('Update').onclick();
  await tick();
  assert.equal(h.confirmation.options.action, 'Install update');
  assert.strictEqual(h.captures, 0);
  h.confirmation.accept();
  await tick();
  assert.strictEqual(h.captures, 1);
  assert.strictEqual(h.calls.filter((c) => c[0] === 'install').length, 1);
  h.confirmation.accept();
  await tick();
  assert.strictEqual(h.calls.filter((c) => c[0] === 'install').length, 1);
  h.key(461);
  assert.strictEqual(h.focus, 'previous');
  h = harness({ delayed: true });
  h.setTx({ id: 'new-tx', phase: 'verifying' });
  h.api.open();
  h.resolve();
  await tick();
  assert(!h.button('Confirm working update'));
  const scroll = h.elements.find((e) => e.className === 'update-notes');
  assert(scroll, 'release notes need their own readable scroll area');
  assert(
    scroll.children.includes(
      h.elements.find((e) => e.className === 'root-update-status')
    ),
    'status must share the flexible reading area so long errors cannot move actions'
  );
  h.key(40);
  assert(scroll.scrollTop > 0, 'down reads notes');
  const chosen = h.focus,
    focusCount = chosen.focusCount,
    readPosition = scroll.scrollTop;
  h.poll();
  assert(!chosen.disabled, 'background status must not disable actions');
  h.resolve();
  await tick();
  assert.strictEqual(h.focus, chosen);
  assert.equal(
    scroll.scrollTop,
    readPosition,
    'polling preserves reading position'
  );
  assert.equal(
    chosen.focusCount,
    focusCount,
    'polling must not refocus an existing choice'
  );
  h.poll();
  h.key(38);
  const moved = h.focus;
  h.resolve();
  await tick();
  assert.strictEqual(
    h.focus,
    moved,
    'a choice made during polling must be preserved'
  );
  h = harness({ recovery: true });
  h.setTx({
    id: 'old',
    phase: 'recovery-required',
    installEvidence: { terminal: null }
  });
  h.api.open({ recovery: true });
  await tick();
  assert(!h.button('Update'));
  assert(h.button('Refresh status'));
  assert(!h.button('Roll back'));
  h.key(40);
  assert(!h.focus.disabled);
  h.key(461);
  assert.strictEqual(h.focus, 'previous');
  assert.strictEqual(h.captures, 0);
  h = harness({ recovery: true });
  h.setTx({
    id: 'old',
    phase: 'recovery-required',
    prior: { version: '0.0.1' },
    installEvidence: { terminal: { success: false } }
  });
  h.api.open({ recovery: true });
  await tick();
  assert(h.button('Roll back'));
  h.button('Roll back').onclick();
  await tick();
  assert(!h.calls.some((c) => c[0] === 'rollback'));
  assert.equal(h.confirmation.options.action, 'Restore previous Home');
  h.confirmation.accept();
  await tick();
  assert(h.calls.some((c) => c[0] === 'rollback'));
  assert.strictEqual(h.captures, 0);
  h = harness();
  h.setTx({
    id: 'old',
    phase: 'recovery-required',
    prior: { version: '0.0.1' },
    installEvidence: { terminal: { success: false } }
  });
  h.api.open();
  await tick();
  assert(!h.button('Roll back'));
  h.button('Recovery').onclick();
  await tick();
  assert(h.button('Roll back'));
  assert(
    h.elements.some((e) =>
      String(e.textContent).includes('Rollback version: 0.0.1')
    )
  );
  h.button('Roll back').onclick();
  assert(h.confirmation.options.message.includes('Home 0.0.1'));
  h = harness({ unavailable: true });
  h.api.open();
  await tick();
  assert(
    h.elements.some((e) =>
      String(e.textContent).includes('one-time computer setup')
    )
  );
  h = harness({ delayed: true });
  h.api.open();
  h.key(461);
  assert.strictEqual(h.focus, 'previous');
  h.resolve();
  await tick();
  assert.strictEqual(h.focus, 'previous');
  for (const version of ['0.1.1', '0.1.3', '0.1.10']) {
    h = harness();
    h.setOffer({
      installed: '0.1.3',
      candidate: { version, notes: 'Notes for ' + version },
      canInstall: version === '0.1.10',
      reason: version === '0.1.10' ? 'available' : 'current'
    });
    h.api.open();
    await tick();
    const details = h.elements.find(
      (e) => e.className === 'root-update-details'
    ).textContent;
    assert(details.includes('Installed: 0.1.3'));
    assert.equal(
      details.includes('Available: ' + version),
      version !== '0.1.1'
    );
    const notes = h.elements.find(
      (e) => e.className === 'release-notes-content'
    );
    assert.equal(
      notes._releaseNotesSource.includes('Notes for ' + version),
      version !== '0.1.1'
    );
  }
  h = harness();
  h.api.open();
  await tick();
  h.key(39);
  assert.strictEqual(h.focus, h.button('Recovery'));
  h.key(13);
  await tick();
  assert(
    h.elements.some((e) => e.tag === 'h1' && e.textContent === 'Recovery')
  );
  assert(
    h.elements.some((e) =>
      String(e.textContent).includes(
        'No saved update is available to roll back.'
      )
    )
  );
  assert(!h.button('Update'));
  assert(!h.button('Roll back'));
  assert(!h.calls.some((c) => c[0] === 'reconcile'));
  h.button('Refresh status').onclick();
  await tick();
  assert(h.calls.some((c) => c[0] === 'reconcile'));
  h.key(461);
  assert(h.api.isOpen());
  assert(h.button('Recovery'));
  assert.strictEqual(h.focus, h.button('Recovery'));
  h.key(461);
  assert(!h.api.isOpen());
  h = harness({ recovery: true });
  h.setTx({
    phase: 'recovery-required',
    prior: { version: '0.0.1' },
    installEvidence: { terminal: null }
  });
  h.api.open({ recovery: true });
  await tick();
  assert(
    h.elements.some((e) =>
      String(e.textContent).includes('Rollback version: 0.0.1')
    )
  );
  assert(!h.button('Roll back'));
  for (const recovery of [false, true]) {
    h = harness({ recovery });
    h.setTx({
      phase: 'complete',
      prior: { version: '0.0.1' },
      installEvidence: { terminal: { success: true } },
      rollbackAttempted: false
    });
    h.api.open({ recovery });
    await tick();
    if (!recovery) {
      assert(!h.button('Roll back'));
      h.button('Recovery').onclick();
      await tick();
    }
    assert(h.button('Roll back'));
    assert(!h.button('Roll back').disabled);
    h.button('Roll back').onclick();
    assert(!h.calls.some((c) => c[0] === 'rollback'));
    assert(h.confirmation.options.message.includes('Home 0.0.1'));
    assert(
      h.confirmation.options.message.includes(
        'Settings changed after the update will be lost.'
      )
    );
    h.confirmation.accept();
    await tick();
    assert.equal(h.calls.filter((c) => c[0] === 'rollback').length, 1);
    assert(!h.button('Roll back'));
  }
  h = harness({ delayed: true });
  h.setTx({
    phase: 'verifying',
    error: 'Long translated error '.repeat(60).slice(0, 1024)
  });
  h.api.open();
  h.resolve();
  await tick();
  h.setTx({ phase: 'complete' });
  h.poll();
  h.resolve();
  await tick();
  const settleCount = h.timers.filter((t) => t.ms === 1500).length;
  assert(
    settleCount >= 2,
    'terminal status must continue bounded polling until Home control settles'
  );
  h.setTx({
    phase: 'complete',
    homeResumePhase: 'complete',
    homeResume: { status: 'restored' }
  });
  h.poll();
  h.resolve();
  await tick();
  assert.equal(
    h.timers.filter((t) => t.ms === 1500).length,
    settleCount,
    'settled Home control stops polling'
  );
  h = harness({ delayed: true });
  h.setTx({ phase: 'verifying' });
  h.api.open();
  h.resolve();
  await tick();
  h.setTx({ phase: 'complete' });
  h.poll();
  h.resolve();
  await tick();
  h.advance(16000);
  const beforeDeadline = h.timers.filter((t) => t.ms === 1500).length;
  h.poll();
  h.resolve();
  await tick();
  assert.equal(
    h.timers.filter((t) => t.ms === 1500).length,
    beforeDeadline,
    'settlement polling has a finite deadline'
  );
  h = harness();
  h.setTx({ phase: 'complete' });
  h.api.open();
  await tick();
  assert.equal(
    h.timers.filter((t) => t.ms === 1500).length,
    0,
    'legacy completed transactions must not start settlement polling'
  );
  h = harness({ recovery: true });
  h.setTx({
    phase: 'complete',
    installEvidence: { terminal: { success: true } }
  });
  h.api.open({ recovery: true });
  await tick();
  assert(!h.button('Roll back'), 'no restore without a saved prior version');
  console.log(
    'PASS Root updates explicit install, duplicate prevention, transaction health, status polling, recovery, remote focus and Back'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
