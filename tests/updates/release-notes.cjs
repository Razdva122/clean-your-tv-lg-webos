const assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.scrollTop = 0;
    this.clientHeight = 400;
    this.scrollHeight = 1600;
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  set textContent(value) {
    this.children = [];
    this.text = value;
  }
  get textContent() {
    return (this.text || '') + this.children.map((e) => e.textContent).join('');
  }
  set innerHTML(_) {
    throw Error('Release notes must never inject HTML');
  }
}
const document = {
    createElement: (tag) => new Element(tag),
    createTextNode: (text) => ({ textContent: text })
  },
  window = {};
vm.runInNewContext(fs.readFileSync('launcher/release-notes.js', 'utf8'), {
  document,
  window
});
const notes = new Element('div');
window.HomeReleaseNotes.render(
  notes,
  '## Changes\n\n- **Automatic** checks\n- Read [the guide](javascript:alert(1))\n\n<script>alert(1)</script>'
);
assert.equal(notes.children[0].tag, 'h2');
assert.equal(notes.children[1].tag, 'ul');
assert.equal(notes.children[1].children[0].children[0].tag, 'strong');
assert(notes.textContent.includes('the guide'));
assert(!notes.textContent.includes('javascript:'));
assert(notes.textContent.includes('<script>'), 'HTML remains inert text');
window.HomeReleaseNotes.scroll(notes, 1);
assert.equal(notes.scrollTop, 300);
const heading = notes.children[0];
window.HomeReleaseNotes.render(notes, notes._releaseNotesSource);
assert.strictEqual(notes.children[0], heading);
assert.equal(
  notes.scrollTop,
  300,
  'unchanged polling preserves DOM and reading position'
);
window.HomeReleaseNotes.scroll(notes, -1);
assert.equal(notes.scrollTop, 0);
window.HomeReleaseNotes.render(notes, 'New notes');
assert.equal(notes.scrollTop, 0);
console.log('PASS safe readable Markdown, remote scrolling, stable polling');
