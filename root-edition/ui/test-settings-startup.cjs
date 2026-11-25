// Real settings module, synthetic LS2; no hardware acceptance.
const assert = require('node:assert/strict'),
  vm = require('node:vm'),
  fs = require('node:fs');
const elements = [],
  listeners = {},
  calls = [],
  pending = [];
let phase = 'active',
  sources = { tv: true, youtube: false },
  delay = false,
  fail = false,
  active = true,
  statusOverride = null;
class Element {
  constructor(tag) {
    this.tag = tag;
    this.attrs = {};
    this.disabled = false;
    this.hidden = false;
    elements.push(this);
  }
  appendChild(child) {
    child.parent = this;
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  removeAttribute(k) {
    delete this.attrs[k];
  }
  focus() {
    document.activeElement = this;
    if (this.onfocus) this.onfocus();
  }
}
const document = {
  body: new Element('body'),
  activeElement: { focus() {} },
  createElement: (tag) => new Element(tag),
  addEventListener: (name, fn) => (listeners[name] = fn)
};
const context = {
  window: {},
  document,
  Promise,
  setTimeout,
  clearTimeout,
  createRootExit: () => () => {
    phase = 'disabled';
    return Promise.resolve();
  },
  PalmServiceBridge: class {
    cancel() {}
    call(uri, raw) {
      const payload = JSON.parse(raw);
      calls.push({ uri, payload });
      const reply = (result) =>
        this.onservicecallback(
          JSON.stringify({
            returnValue: true,
            result: { returnValue: true, result }
          })
        );
      if (payload.startup === 'status') {
        const snapshot = statusOverride || {
          sources: { ...sources },
          active: active && phase === 'active'
        };
        const answer = () =>
          fail
            ? this.onservicecallback(JSON.stringify({ returnValue: false }))
            : reply(snapshot);
        if (delay) pending.push(answer);
        else answer();
      } else if (payload.startup === 'configure') {
        sources = { ...payload.sources };
        reply({ sources: { ...sources }, active: true });
      } else if (uri.endsWith('/status')) reply({ intent: { phase } });
      else if (uri.endsWith('/enable')) {
        phase = 'active';
        reply({});
      }
    }
  }
};
vm.runInNewContext(
  fs.readFileSync(__dirname + '/root-settings.js', 'utf8'),
  context
);
const tick = () => new Promise((resolve) => setImmediate(resolve)),
  panel = context.window.RenewalPanel;
const byText = (text) =>
  elements.find((e) => e.tag === 'button' && e.textContent === text);
const key = (keyCode) =>
  listeners.keydown({
    keyCode,
    preventDefault() {},
    stopImmediatePropagation() {}
  });
(async () => {
  panel.open();
  await tick();
  const tv = byText('LG Channels / Live TV'),
    youtube = byText('YouTube'),
    home = byText('Change Home'),
    visit = byText('Open LG Home');
  assert(tv && youtube, 'both source controls are visible');
  assert(!byText('HDMI'), 'no HDMI startup control');
  assert.deepEqual(
    elements
      .filter(
        (e) =>
          e.tag === 'button' &&
          e.parent.className === 'renewal-actions startup-source-actions'
      )
      .map((e) => e.textContent),
    ['LG Channels / Live TV', 'YouTube']
  );
  assert.equal(tv.attrs['aria-checked'], 'true');
  assert.equal(youtube.attrs['aria-checked'], 'false');
  visit.focus();
  key(39);
  assert.equal(
    document.activeElement,
    tv,
    'source navigation follows visible Home actions'
  );
  youtube.onclick();
  assert(
    tv.disabled && youtube.disabled,
    'writes immediately disable the group'
  );
  await tick();
  const writes = () => calls.filter((c) => c.payload.startup === 'configure');
  assert.deepEqual(JSON.parse(JSON.stringify(writes()[0].payload)), {
    startup: 'configure',
    sources: { tv: true, youtube: true }
  });
  assert.equal(
    youtube.attrs['aria-checked'],
    'true',
    'saved readback controls the switch'
  );
  youtube.focus();
  key(39);
  assert.equal(
    document.activeElement,
    byText('Columns'),
    'remote navigation leaves the two-source group'
  );
  tv.focus();
  phase = 'disabled';
  listeners.webOSRelaunch();
  await tick();
  assert.equal(
    document.activeElement,
    visit,
    'invalidated source focus returns to a visible Home action'
  );
  assert(tv.disabled && youtube.disabled);
  assert.equal(tv.parent.parent.attrs['aria-disabled'], 'true');
  assert(
    elements.some(
      (e) => e.textContent === 'Available when Change Home is on.' && !e.hidden
    )
  );
  const count = writes().length;
  tv.onclick();
  key(13);
  assert.equal(writes().length, count, 'disabled click and Enter cannot write');
  home.focus();
  key(39);
  assert.equal(document.activeElement, visit, 'remote skips disabled sources');
  assert.equal(
    youtube.attrs['aria-checked'],
    'true',
    'Off retains saved choices'
  );
  assert.equal(tv.attrs['aria-checked'], 'true');
  assert(!tv.hidden && !youtube.hidden, 'Off keeps the saved switches visible');
  phase = 'active';
  delay = true;
  listeners.webOSRelaunch();
  assert(tv.disabled);
  tv.onclick();
  assert.equal(writes().length, count);
  await tick();
  pending.shift()();
  await tick();
  assert(!tv.disabled);
  listeners.webOSRelaunch();
  await tick();
  const stale = pending.shift();
  active = false;
  listeners.webOSRelaunch();
  await tick();
  assert.equal(pending.length, 0, 'source reads are single-flight');
  stale();
  await tick();
  assert(tv.disabled, 'stale source status cannot re-enable controls');
  const fresh = pending.shift();
  fresh();
  await tick();
  active = true;
  assert(tv.disabled, 'fresh inactive status stays disabled');
  delay = false;
  fail = true;
  listeners.webOSRelaunch();
  await tick();
  assert(tv.disabled);
  assert(!home.disabled, 'source status failure does not break Home control');
  assert(
    elements.some(
      (e) =>
        e.textContent ===
        'Startup sources unavailable. Reopen Settings to check again.'
    ),
    'source error remains visible after Home status succeeds'
  );
  fail = false;
  listeners.webOSRelaunch();
  await tick();
  assert(!tv.disabled);
  assert.equal(youtube.attrs['aria-checked'], 'true');
  for (const invalid of [
    { sources: { tv: true, youtube: true, hdmi: true }, active: true },
    { sources: { tv: true }, active: true },
    { sources: { tv: true, youtube: 'true' }, active: true },
    { sources: { tv: true, youtube: true }, active: 'true' }
  ]) {
    statusOverride = invalid;
    listeners.webOSRelaunch();
    await tick();
    assert(
      tv.disabled && youtube.disabled,
      'malformed source status cannot enable either switch'
    );
    assert(!home.disabled, 'malformed sources do not disable Home control');
  }
  statusOverride = null;
  listeners.webOSRelaunch();
  await tick();
  assert(!tv.disabled && !youtube.disabled);
  console.log(
    'PASS startup source defaults, exact payload, readback, disabled controls, focus, stale status and failure isolation'
  );
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
