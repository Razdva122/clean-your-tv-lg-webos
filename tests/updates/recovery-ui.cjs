const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const elements = {},
  events = {},
  calls = [];
let status = 'aborted';
for (const id of [
  'refresh',
  'restore',
  'open',
  'status',
  'recoveryReading',
  'guidance',
  'diagnostic',
  'details'
])
  elements[id] = {
    disabled: false,
    textContent: '',
    scrollTop: 0,
    clientHeight: 400,
    setAttribute() {},
    focus() {},
    click() {
      if (!this.disabled && this.onclick) this.onclick();
    }
  };
const document = {
  hidden: false,
  getElementById: (id) => elements[id],
  addEventListener: (name, fn) => (events[name] = fn)
};
function Bridge() {
  this.cancel = () => {};
  this.call = (uri) => {
    calls.push(uri);
    if (uri.endsWith('/reconcile'))
      this.onservicecallback(
        JSON.stringify({
          returnValue: true,
          result: { status, prior: { home: '1.3.5' } }
        })
      );
  };
}
let confirmation;
const i18n = {
  t: (s, p) => s.replace(/\{(\w+)\}/g, (_, k) => p[k]),
  ready: (f) => f(),
  apply() {},
  confirm: (options, accept) => {
    confirmation = { options, accept };
  }
};
vm.runInNewContext(fs.readFileSync('updater-app/app.js', 'utf8'), {
  window: { HomeI18n: i18n },
  document,
  PalmServiceBridge: Bridge,
  setTimeout: () => 1,
  clearTimeout: () => {}
});
assert.equal(elements.restore.disabled, true);
status = 'complete';
assert.equal(typeof events.webOSRelaunch, 'function');
events.webOSRelaunch();
assert.equal(elements.restore.disabled, false);
assert.equal(elements.status.textContent, 'No recovery needed.');
elements.restore.onclick();
assert.equal(elements.restore.textContent, 'Restore previous Home');
assert.equal(confirmation.options.action, 'Restore previous Home');
assert(
  confirmation.options.message.includes(
    'Settings changed after the update will be lost.'
  )
);
document.hidden = true;
let count = calls.length;
events.visibilitychange();
assert.equal(calls.length, count);
document.hidden = false;
events.visibilitychange();
assert.equal(elements.restore.textContent, 'Restore previous Home');
elements.restore.onclick();
assert.equal(
  calls.some((u) => u.endsWith('/rollback')),
  false,
  'returning to recovery must reset confirmation'
);
confirmation.accept();
assert.equal(calls.filter((u) => u.endsWith('/rollback')).length, 1);
count = calls.length;
events.webOSRelaunch();
assert.equal(calls.length, count, 'do not reconcile during rollback');
events.keydown({ keyCode: 40, preventDefault() {} });
assert.equal(
  elements.recoveryReading.scrollTop,
  300,
  'remote reads long independent recovery status and copy'
);
events.keydown({ keyCode: 461, preventDefault() {} });
assert(
  calls.includes('luna://com.webos.applicationManager/launch'),
  'Back opens Home from independent recovery'
);
console.log(
  'PASS recovery refresh on relaunch/visibility, confirmation reset and busy guard'
);
