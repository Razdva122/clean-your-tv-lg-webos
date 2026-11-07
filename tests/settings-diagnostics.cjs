'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const ids = {},
  buttons = [],
  pending = {},
  calls = [];
class Element {
  constructor() {
    this.className = '';
    this.children = [];
    this.attrs = {};
    this.classList = {
      contains: (n) => this.className.split(' ').includes(n),
      add: (n) => {
        this.className += ' ' + n;
      },
      remove: (n) => {
        this.className = this.className
          .split(' ')
          .filter((x) => x !== n)
          .join(' ');
      },
      toggle: (n, value) => {
        if (value === undefined) value = !this.classList.contains(n);
        this.classList[value ? 'add' : 'remove'](n);
      }
    };
  }
  set innerHTML(html) {
    for (const match of html.matchAll(
      /<(button|p|div|pre|span)\b[^>]*id="([^"]+)"[^>]*>/g
    )) {
      const e = new Element();
      ids[match[2]] = e;
      if (match[1] === 'button') buttons.push(e);
      if (match[0].includes('class="hidden"')) e.className = 'hidden';
    }
  }
  appendChild(e) {
    this.children.push(e);
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  addEventListener() {}
  focus() {
    document.activeElement = this;
  }
  querySelectorAll() {
    return buttons;
  }
}
const document = {
  body: new Element(),
  createElement: () => new Element(),
  getElementById: (id) => ids[id],
  addEventListener() {},
  activeElement: { focus() {} }
};
const window = {};
const context = {
  window,
  document,
  setTimeout: () => 1,
  clearTimeout() {},
  PalmServiceBridge: class {
    cancel() {}
    call(uri) {
      calls.push(uri);
      pending[uri.split('/').pop()] = (r) =>
        this.onservicecallback(JSON.stringify(r));
    }
  }
};
vm.runInNewContext(
  fs.readFileSync('launcher/renewal-panel.js', 'utf8'),
  context
);
window.RenewalPanel.open();
pending.status({
  returnValue: true,
  version: '1.4.2',
  state: {
    enabled: false,
    error: 'storage-error',
    diagnostic: {
      component: 'settings',
      operation: 'mkdir',
      code: 'EACCES',
      path: 'PRIVATE'
    },
    token: 'PRIVATE',
    last: { status: 'PRIVATE', checkedAt: 'PRIVATE', lastRenewedAt: 'PRIVATE' }
  }
});
ids.developerOpen.onclick();
ids.renewalDiagnostics.onclick();
assert.equal(
  document.activeElement,
  ids.renewalDetails,
  'opening diagnostics must bring the report into remote focus'
);
function report() {
  const text = ids.renewalDetails.textContent;
  assert(!text.includes('PRIVATE'));
  return JSON.parse(text.slice(text.indexOf('{')));
}
assert.deepEqual(report().diagnostic, {
  component: 'settings',
  operation: 'mkdir',
  code: 'EACCES'
});
assert.equal(report().serviceVersion, '1.4.2');
assert.equal(
  report().launcher,
  undefined,
  'do not report a hard-coded launcher version'
);
pending.homeStatus({
  returnValue: false,
  errorCode: -1,
  errorText: 'PRIVATE',
  diagnostic: {
    component: 'home',
    operation: 'write',
    code: 'EACCES',
    path: 'PRIVATE'
  }
});
assert.deepEqual(report().home.homeStatus, {
  returnValue: false,
  errorCode: -1,
  diagnostic: { component: 'home', operation: 'write', code: 'EACCES' }
});
assert.equal(ids.homeRoutingToggle.hidden, true);
assert.match(ids.homeRoutingStatus.textContent, /unknown/);
ids.homeVisit.onclick();
pending.openLGHome({
  returnValue: false,
  errorCode: 'PRIVATE',
  diagnostic: { component: 'PRIVATE', operation: 'PRIVATE', code: 'PRIVATE' }
});
assert.equal(report().home.openLGHome.errorCode, undefined);
assert.deepEqual(report().home.openLGHome.diagnostic, {
  component: 'home',
  operation: 'rpc',
  code: 'REQUEST_FAILED'
});
assert.equal(
  calls.some(
    (uri) =>
      uri.endsWith('/setHomeControl') || uri.includes('applicationManager')
  ),
  false
);
ids.renewalClose.onclick();
window.RenewalPanel.open();
pending.status({
  returnValue: true,
  version: '1.4.2',
  state: { enabled: false }
});
const oldHome = pending.homeStatus;
ids.renewalClose.onclick();
window.RenewalPanel.open();
pending.status({
  returnValue: true,
  version: '1.4.2',
  state: { enabled: false }
});
ids.developerOpen.onclick();
ids.renewalDiagnostics.onclick();
oldHome({ returnValue: false, errorCode: -1 });
assert.deepEqual(
  report().home,
  {},
  'a previous settings session must not publish stale diagnostics'
);
pending.homeStatus({ returnValue: true, enabled: true });
assert.equal(report().home.homeStatus.enabled, true);
console.log(
  'PASS settings diagnostics: async Home results, safe fields, actual service version, unknown switch and no side effects'
);
