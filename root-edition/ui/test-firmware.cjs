const assert = require('node:assert/strict'),
  vm = require('vm'),
  fs = require('fs');
const elements = [],
  listeners = {};
let focused,
  returned = 0,
  enabled = false,
  hostsState = 'clear',
  fail = false,
  changed = false,
  hold;
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
  window: { createRootFirmwareControl: require('./root-firmware-control') },
  document: {
    body: new E('body'),
    createElement: (t) => new E(t),
    addEventListener: (n, f) => (listeners[n] = f)
  },
  Promise
};
vm.runInNewContext(
  fs.readFileSync(__dirname + '/root-firmware.js', 'utf8'),
  context
);
const ui = context.window.RootFirmware,
  tick = () => new Promise((r) => setImmediate(r));
function request(uri, payload) {
  if (hold)
    return new Promise((r) => {
      hold = r;
    });
  if (fail)
    return Promise.resolve(
      typeof fail === 'object'
        ? fail
        : { returnValue: false, errorCode: 'unavailable' }
    );
  if (changed && uri.endsWith('/getConfiguration')) enabled = true;
  if (uri.endsWith('/setConfiguration')) {
    assert.equal(typeof payload.blockUpdates, 'boolean');
    enabled = payload.blockUpdates;
  }
  return Promise.resolve({
    returnValue: true,
    root: true,
    blockUpdates: enabled
  });
}
function key(keyCode) {
  listeners.keydown({
    keyCode,
    preventDefault() {},
    stopImmediatePropagation() {}
  });
}
(async () => {
  ui.open(request, () => returned++);
  await tick();
  const buttons = elements.filter((e) => e.tag === 'button'),
    toggle = buttons[0];
  assert.equal(focused, toggle);
  assert.equal(toggle.attrs['aria-checked'], 'false');
  assert(!toggle.disabled);
  toggle.onclick();
  await tick();
  assert.equal(toggle.attrs['aria-checked'], 'true');
  assert(
    elements.some(
      (e) =>
        e.textContent ===
        'Changes apply after a TV restart. Standby is not enough. Active blocking is not verified here.'
    )
  );
  toggle.onclick();
  await tick();
  assert.equal(toggle.attrs['aria-checked'], 'false');
  changed = true;
  toggle.onclick();
  await tick();
  assert.equal(toggle.attrs['aria-checked'], 'true');
  assert(
    elements.some(
      (e) =>
        e.textContent ===
        'The setting changed elsewhere. Check it before trying again.'
    )
  );
  changed = false;
  fail = true;
  buttons[1].onclick();
  await tick();
  assert(toggle.disabled);
  assert.equal(toggle.attrs['aria-checked'], 'false');
  assert(
    elements.some(
      (e) =>
        e.textContent ===
        'Homebrew Channel with root access is required. Check its settings, then retry.'
    )
  );
  for (const [reply, phrase] of [
    [
      {
        returnValue: false,
        errorText: 'Denied methods call getConfiguration private-data'
      },
      'denied this app'
    ],
    [
      { returnValue: true, root: false, blockUpdates: false },
      'not running as root'
    ],
    [
      { returnValue: false, errorText: 'Service does not exist' },
      'service is unavailable'
    ],
    [
      { returnValue: true, root: true, blockUpdates: 'false' },
      'unsupported configuration'
    ]
  ]) {
    fail = reply;
    buttons[1].focus();
    buttons[1].onclick();
    await tick();
    const message = elements.find(
      (e) => e.id === 'rootFirmwareStatus'
    ).textContent;
    assert(
      message.includes(phrase),
      'show the specific Homebrew failure instead of claiming root is missing: ' +
        phrase
    );
    assert(!message.includes('private-data'));
    assert(toggle.disabled);
    assert.equal(focused, buttons[1]);
  }
  key(461);
  assert.equal(returned, 1);
  fail = false;
  enabled = false;
  hold = true;
  ui.open(request, () => returned++);
  await tick();
  key(461);
  const late = hold;
  hold = false;
  ui.open(request, () => returned++);
  await tick();
  late({ returnValue: true, root: true, blockUpdates: true });
  await tick();
  assert.equal(
    toggle.attrs['aria-checked'],
    'false',
    'old request cannot overwrite reopened panel'
  );
  key(40);
  assert.equal(focused, buttons[1]);
  key(40);
  assert.equal(focused, buttons[2]);
  key(13);
  assert.equal(returned, 3);
  console.log(
    'PASS firmware dialog: verified state, safe errors, remote/back focus, pending restart and stale replies'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
