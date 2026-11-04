// Focused-input preview controller: dwell, single media, failure cooldown and release.
const assert = require('node:assert/strict');
const preview = require('../../launcher/input-preview');

// A manual clock: timers only fire when the test advances time.
let time = 0, timers = [], nextId = 1;
global.setTimeout = (fn, ms) => { const id = nextId++; timers.push({id, at: time + ms, fn}); return id; };
global.clearTimeout = id => { timers = timers.filter(t => t.id !== id); };
function advance(ms) {
  const until = time + ms;
  for (;;) {
    timers.sort((a, b) => a.at - b.at);
    const next = timers[0];
    if (!next || next.at > until) break;
    timers.shift(); time = next.at; next.fn();
  }
  time = until;
}

function fakeMedia(uri) {
  const listeners = {}, video = {calls: [], pause() { this.calls.push('pause'); }, load() { this.calls.push('load'); },
    removeAttribute(name) { this.calls.push('remove ' + name); }, querySelector() { return {removeAttribute: name => video.calls.push('source remove ' + name)}; }};
  const media = {uri, tagName: 'DIV', video, parentNode: null,
    addEventListener(type, fn, capture) { assert.equal(capture, true, 'media events are captured'); (listeners[type] = listeners[type] || []).push(fn); },
    querySelector: selector => selector === 'video' ? video : null,
    fire(type) { (listeners[type] || []).forEach(fn => fn()); }};
  return media;
}
function harness(extra = {}) {
  const made = [], mounted = [], changes = [];
  let on = true;
  const controller = preview.create({now: () => time, enabled: () => on,
    createMedia: uri => { const media = fakeMedia(uri); made.push(media); return media; },
    mount: (media, input) => { media.parentNode = {removeChild: child => { child.parentNode = null; child.removed = true; }}; mounted.push(input.appId); },
    onchange: input => changes.push(input && input.appId), ...extra});
  return {controller, made, mounted, changes, set: value => { on = value; }, live: () => made.filter(m => !m.removed)};
}
const hdmi1 = {appId: 'com.webos.app.hdmi1', source: 'ext://hdmi:1', connected: true};
const hdmi2 = {appId: 'com.webos.app.hdmi2', source: 'ext://hdmi:2', connected: null};

// The dwell fires only after 800 ms; refocusing elsewhere restarts it.
let h = harness();
h.controller.focus(hdmi1);
advance(799);
assert.equal(h.made.length, 0, 'no media before the dwell');
h.controller.focus(hdmi2);
advance(799);
assert.equal(h.made.length, 0, 'a new focus restarts the dwell');
advance(1);
assert.deepEqual(h.made.map(m => m.uri), ['ext://hdmi:2'], 'unknown connection state is allowed');
assert.equal(h.controller.playing(), false);
assert.deepEqual(h.changes, [], 'previewing is reported only once the picture plays');
h.made[0].fire('playing');
h.made[0].fire('playing');
assert.deepEqual(h.changes, ['com.webos.app.hdmi2'], 'playing is reported once');
assert.equal(h.controller.playing(), true);

// A repeated focus on the same source (a shelf re-render) keeps the running preview,
// and remount moves the same media into the rebuilt tile and restores its state.
h.controller.focus({...hdmi2, label: 'renamed'});
h.controller.remount();
advance(5000);
assert.equal(h.live().length, 1, 'same source keeps its media');
assert.equal(h.made.length, 1, 'no new media for a re-render');
assert.deepEqual(h.mounted, ['com.webos.app.hdmi2', 'com.webos.app.hdmi2'], 'the same media is mounted again');
assert.deepEqual(h.changes, ['com.webos.app.hdmi2', 'com.webos.app.hdmi2'], 'the rebuilt tile is marked previewing');

// Moving on releases the old media in the verified order before a new one exists.
h.controller.focus(hdmi1);
assert.equal(h.live().length, 0, 'old media is released immediately');
assert.deepEqual(h.made[0].video.calls, ['pause', 'source remove src', 'remove src', 'load']);
assert.deepEqual(h.changes, ['com.webos.app.hdmi2', 'com.webos.app.hdmi2', null]);
advance(800);
assert.equal(h.live().length, 1, 'a single media element at a time');
assert.deepEqual(h.mounted, ['com.webos.app.hdmi2', 'com.webos.app.hdmi2', 'com.webos.app.hdmi1']);

// Rapid focus changes never stack media.
for (let i = 0; i < 10; i++) { h.controller.focus(i % 2 ? hdmi1 : hdmi2); advance(400); }
assert(h.live().length <= 1);

// stop() is idempotent and a stopped preview reports nothing more.
h.controller.stop(); h.controller.stop();
assert.equal(h.live().length, 0);
advance(10000);
assert.equal(h.live().length, 0, 'no pending dwell after stop');

// Timeout before playing tears down and skips the source until the cooldown ends.
h = harness();
h.controller.focus(hdmi1);
advance(800 + 3999);
assert.equal(h.live().length, 1);
advance(1);
assert.equal(h.live().length, 0, 'no playing within 4 s fails');
assert.deepEqual(h.changes, [], 'a preview that never played reports no change');
h.controller.focus(hdmi2); h.controller.focus(hdmi1);
advance(5000);
assert.equal(h.made.length, 1, 'a failed source is skipped during the cooldown');
advance(60000);
h.controller.focus(hdmi2); h.controller.focus(hdmi1);
advance(800);
assert.equal(h.made.length, 2, 'the source is retried after the cooldown');

// An error, including one captured from a <source>, fails the same way; other sources still play.
h = harness();
h.controller.focus(hdmi1); advance(800);
h.made[0].fire('playing');
h.made[0].fire('error');
assert.equal(h.live().length, 0);
assert.deepEqual(h.changes, ['com.webos.app.hdmi1', null], 'a playing preview that fails reports its end');
h.controller.focus(hdmi2); advance(800);
assert.equal(h.live().length, 1);

// Inputs without a source, disconnected inputs and a disabled setting never start.
h = harness();
for (const input of [null, {appId: 'com.webos.app.externalinput.av1', source: null, connected: true}, {...hdmi1, connected: false}]) {
  h.controller.focus(input); advance(5000);
}
assert.equal(h.made.length, 0);
h.set(false);
h.controller.focus(hdmi1); advance(5000);
assert.equal(h.made.length, 0, 'the switch off prevents previews');
h.set(true);
h.controller.focus(hdmi1); advance(400);
h.set(false); advance(400);
assert.equal(h.made.length, 0, 'turning the switch off during the dwell cancels it');

// A focused input that disconnects stops its preview.
h = harness();
h.controller.focus(hdmi1); advance(800); h.made[0].fire('playing');
h.controller.focus({...hdmi1, connected: false});
assert.equal(h.live().length, 0);
assert.deepEqual(h.changes, ['com.webos.app.hdmi1', null]);

// No tile to mount into ends the preview without a failure cooldown; a remount that
// finds no tile releases the media.
let tile = false;
h = harness({mount: media => { if (!tile) return false; media.parentNode = {removeChild: child => { child.parentNode = null; child.removed = true; }}; return true; }});
h.controller.focus(hdmi1); advance(800);
assert.deepEqual(h.made[0].video.calls, ['pause', 'source remove src', 'remove src', 'load'], 'an unmounted preview is released at once');
tile = true;
h.controller.focus(hdmi2); h.controller.focus(hdmi1); advance(800);
assert.equal(h.made.length, 2, 'no cooldown after a missing tile');
h.made[1].fire('playing');
tile = false;
h.controller.remount();
assert.equal(h.made[1].removed, true, 'a remount without a tile releases the preview');
assert.deepEqual(h.changes, ['com.webos.app.hdmi1', null]);

// The default media is a muted webOS video with a typed source.
const created = [];
global.document = {createElement: tag => { const el = {tag, attrs: {}, children: [], setAttribute(k, v) { this.attrs[k] = v; }, appendChild(c) { this.children.push(c); }}; created.push(el); return el; }};
const wrapper = preview.createVideo('ext://hdmi:3'), video = wrapper.children[0], source = video.children[0];
assert.equal(wrapper.tag, 'div');
assert.equal(video.muted, true);
assert.deepEqual(video.attrs, {autoplay: '', muted: ''});
assert.deepEqual(source.attrs, {type: 'service/webos-external', src: 'ext://hdmi:3'});
console.log('PASS input preview: dwell, single media, re-render remount, failure cooldown, release order and eligibility');

// The foreground input owns the decoder before its media element is created.
let ownership=[], releasedMedia;
h=harness({onclaim:()=>ownership.push('claim'),onrelease:()=>{assert(!releasedMedia||releasedMedia.removed);ownership.push('release');},createMedia:uri=>{assert.equal(ownership.at(-1),'claim');releasedMedia=fakeMedia(uri);return releasedMedia;}});
h.controller.focus(hdmi1);advance(799);assert.deepEqual(ownership,[]);
advance(1);assert.deepEqual(ownership,['claim']);h.controller.stop();assert.deepEqual(ownership,['claim','release']);h.controller.stop();assert.equal(ownership.length,2);
h=harness({onclaim:()=>ownership.push('claim'),onrelease:()=>ownership.push('release'),createMedia:()=>{throw Error('decoder unavailable');}});
h.controller.focus(hdmi1);advance(800);assert.deepEqual(ownership.slice(-2),['claim','release'],'failed allocation restores background');
console.log('PASS decoder ownership handed back after release or allocation failure');
