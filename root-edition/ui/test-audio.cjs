const assert = require('node:assert/strict'),
  vm = require('vm'),
  fs = require('fs');
const elements = [],
  listeners = [];
let focused,
  returned = 0,
  held,
  operations = 0;
class E {
  constructor(tag) {
    this.tag = tag;
    this.hidden = false;
    this.disabled = false;
    this.attrs = {};
    elements.push(this);
  }
  appendChild() {}
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  focus() {
    focused = this;
    if (this.onfocus) this.onfocus();
  }
}
const context = {
  window: {},
  document: {
    body: new E('body'),
    createElement: (t) => new E(t),
    addEventListener: (n, f) => listeners.push(f)
  },
  Promise
};
vm.runInNewContext(
  fs.readFileSync(__dirname + '/root-audio.js', 'utf8'),
  context
);
let state = {
  returnValue: true,
  enabled: false,
  observer: false,
  autoSupported: true,
  canRestart: true,
  canRestoreRoute: false,
  needsRestore: false,
  canRestoreSetting: false,
  mode: 'earc',
  last: null
};
function request(uri, payload) {
  if (uri.endsWith('/status') && payload.audio === 'status')
    return Promise.resolve({ ...state });
  assert(uri.endsWith('/enable'));
  assert(['configure', 'recover'].includes(payload.audio));
  operations++;
  return new Promise((resolve) => {
    held = resolve;
  });
}
const tick = () => new Promise((r) => setImmediate(r));
function key(keyCode) {
  for (const f of listeners)
    f({ keyCode, preventDefault() {}, stopImmediatePropagation() {} });
}
(async () => {
  const ui = context.window.RootAudio;
  ui.open(request, () => returned++);
  await tick();
  const buttons = elements.filter((e) => e.tag === 'button');
  const action = buttons[0],
    toggle = buttons[1],
    check = buttons[2],
    back = buttons[3];
  assert.equal(focused, action);
  assert(!action.disabled);
  assert.equal(toggle.attrs['aria-checked'], 'false');
  action.onclick();
  action.onclick();
  assert.equal(operations, 1);
  assert(action.disabled);
  key(461);
  assert.equal(returned, 1);
  ui.open(request, () => returned++);
  await tick();
  assert(action.disabled);
  held({ returnValue: true, result: 'settings-restored' });
  await tick();
  await tick();
  assert(!action.disabled);
  state = { ...state, canRestart: false, autoSupported: false };
  check.onclick();
  await tick();
  assert(action.disabled);
  assert(toggle.disabled);
  assert.equal(toggle.attrs['aria-checked'], 'false');
  state = { ...state, enabled: true };
  check.onclick();
  await tick();
  assert(
    !toggle.disabled,
    'unavailable observer must still allow disabling saved policy'
  );
  state = {
    ...state,
    enabled: false,
    needsRestore: true,
    canRestoreSetting: true
  };
  check.onclick();
  await tick();
  assert(!action.disabled);
  assert.equal(action.textContent, 'Restore saved eARC setting');
  assert(toggle.disabled);
  back.onclick();
  assert.equal(returned, 2);
  console.log(
    'PASS eARC dialog: eligibility, duplicates, Back during operation, reopen, unavailable observer and interrupted setting recovery'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
