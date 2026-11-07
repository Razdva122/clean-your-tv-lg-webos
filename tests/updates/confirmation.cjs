const assert = require('node:assert/strict'),
  fs = require('fs'),
  vm = require('vm');
const elements = [],
  listeners = {};
let focused,
  accepted = 0;
class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.hidden = false;
    this.attrs = {};
    elements.push(this);
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  focus() {
    focused = this;
    document.activeElement = this;
    (listeners.focusin || []).forEach((fn) => fn({ target: this }));
  }
  click() {
    if (!this.disabled && this.onclick) this.onclick();
  }
}
const document = {
  documentElement: {},
  createElement: (tag) => new Element(tag),
  body: new Element('body'),
  addEventListener: (name, fn) => (listeners[name] ||= []).push(fn)
};
const window = {
  document,
  navigator: { language: 'en' },
  localStorage: { getItem: () => null }
};
vm.runInNewContext(fs.readFileSync('launcher/i18n.js', 'utf8'), { window });
const source = new Element('button');
source.focus();
const open = () =>
  window.HomeI18n.confirm(
    {
      title: 'Install Home update?',
      message: 'Saved settings',
      action: 'Install update'
    },
    () => accepted++
  );
function key(code, repeat = false, type = 'keydown') {
  let stopped = false;
  for (const fn of listeners[type] || []) {
    fn({
      keyCode: code,
      repeat,
      preventDefault() {},
      stopImmediatePropagation() {
        stopped = true;
      }
    });
    if (stopped) break;
  }
  if (type === 'keydown' && !repeat) key(code, false, 'keyup');
  return stopped;
}
assert.equal(
  typeof window.HomeI18n.confirm,
  'function',
  'shared explicit confirmation dialog exists'
);
open();
const dialog = elements.find((e) => e.attrs.role === 'alertdialog'),
  buttons = dialog.children[0].children.filter((e) => e.tag === 'div')[0]
    .children;
assert.equal(focused, buttons[0]);
assert.equal(focused.textContent, 'Cancel');
assert.equal(dialog.attrs['aria-modal'], 'true');
source.focus();
assert.equal(focused, buttons[0], 'focus stays inside confirmation');
key(13, true);
assert.equal(dialog.hidden, false);
key(13);
assert.equal(dialog.hidden, true);
assert.equal(focused, source);
assert.equal(accepted, 0);
open();
key(39);
assert.equal(focused, buttons[1]);
source.focus();
assert.equal(
  focused,
  buttons[1],
  'background status refresh preserves selected action'
);
key(461);
assert.equal(dialog.hidden, true);
assert.equal(accepted, 0);
assert.equal(focused, source);
open();
key(39);
key(13, true);
assert.equal(accepted, 0);
key(13);
assert.equal(accepted, 1);
assert.equal(dialog.hidden, true);
key(13, false, 'keyup');
assert.equal(accepted, 1);
open();
key(27);
assert.equal(dialog.hidden, true);
assert.equal(focused, source);
console.log(
  'PASS explicit confirmation, Cancel default, focus trap, Back/Escape, held OK and single acceptance'
);
