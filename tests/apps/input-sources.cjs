// Live input status over the captured inventory, and the Inputs shelf preference.
const assert = require('node:assert/strict');
const sources = require('../../launcher/input-sources');
const inventory = [{appId:'com.webos.app.hdmi1',label:'HDMI 1'},{appId:'com.webos.app.hdmi2',label:'Game room'},{label:'no id'},{appId:'com.webos.app.hdmi1',label:'dup'},{appId:'com.gathin.tvhome',label:'Home'}];

function harness(options = {}) {
  const calls = [];
  const model = sources.create({inventory, ...options, call: (uri, params, reply) => calls.push({uri, params, reply})});
  const changes = [];
  model.onchange(list => changes.push(list));
  return {model, calls, changes};
}

// The captured inventory is shown before and without live status; unknown status never dims.
let h = harness();
const captured = [
  {appId:'com.webos.app.hdmi1',label:'HDMI 1',deviceName:null,connected:null,kind:'hdmi',source:'ext://hdmi:1'},
  {appId:'com.webos.app.hdmi2',label:'Game room',deviceName:null,connected:null,kind:'hdmi',source:'ext://hdmi:2'}
];
assert.deepEqual(h.model.list(), captured, 'inventory is de-duplicated; entries without an app ID and Home itself are dropped');
h.model.start(); h.model.start();
assert.equal(h.calls.length, 1, 'one subscription per Home session');
assert.equal(h.calls[0].uri, 'luna://com.webos.service.eim/getAllInputStatus');
assert.deepEqual(h.calls[0].params, {subscribe:true});

// Live status overlays the inventory: captured order stays, uncaptured ports follow in the TV's order.
h.calls[0].reply({returnValue:true, devices:[
  {id:'HDMI_4',appId:'com.webos.app.hdmi4',label:'HDMI 4',spdProductDescription:'SHIELD Android TV'},
  {id:'HDMI_3',appId:'com.webos.app.hdmi3',label:'HDMI 3',connected:false},
  {id:'HDMI_1',appId:'com.webos.app.hdmi1',label:'HDMI 1',connected:true,deviceName:'PlayStation 5'},
  {id:'HDMI_2',appId:'com.webos.app.hdmi2',connected:'yes',deviceName:'game room'},
  {id:'MVPD_IP-com.gathin.tvhome',appId:'com.gathin.tvhome',label:'Home',connected:true},
  {id:'MVPD_IP-com.example.iptv',appId:'com.example.iptv',label:'IPTV',connected:true},
  {id:'COMP_1',appId:'com.webos.app.externalinput.component',label:'Component',connected:false},
  {id:'broken'}, null
]});
assert.equal(h.model.live(), true);
assert.deepEqual(h.model.list(), [
  {appId:'com.webos.app.hdmi1',label:'HDMI 1',deviceName:'PlayStation 5',connected:true,kind:'game',source:'ext://hdmi:1'},
  {appId:'com.webos.app.hdmi2',label:'Game room',deviceName:null,connected:null,kind:'hdmi',source:'ext://hdmi:2'},
  {appId:'com.webos.app.hdmi4',label:'HDMI 4',deviceName:'SHIELD Android TV',connected:null,kind:'stream',source:'ext://hdmi:4'},
  {appId:'com.webos.app.hdmi3',label:'HDMI 3',deviceName:null,connected:false,kind:'hdmi',source:'ext://hdmi:3'},
  {appId:'com.webos.app.externalinput.component',label:'Component',deviceName:null,connected:false,kind:'hdmi',source:null}
], 'a missing live label keeps the captured one; a device name equal to the label is dropped; non-boolean status is unknown; app-registered inputs are not sources');
assert.equal(h.changes.length, 1);

// The TV's newer label wins over the captured one; captured inputs absent from the reply stay without status.
h.calls[0].reply({returnValue:true, devices:[{appId:'com.webos.app.hdmi2',label:'Console',connected:true}]});
assert.deepEqual(h.model.list().map(i => [i.label, i.connected]), [['HDMI 1', null], ['Console', true]]);
const update = {returnValue:true, devices:[{appId:'com.webos.app.hdmi1',label:'HDMI 1',connected:false}]};
h.calls[0].reply(update);
const count = h.changes.length;
h.calls[0].reply(update);
assert.equal(h.changes.length, count, 'identical subscription replies are not republished');
assert.equal(h.model.list()[0].connected, false);

// A later failure returns to the captured inventory instead of keeping stale status.
h.calls[0].reply({returnValue:false, errorText:'Denied method call'});
assert.equal(h.model.live(), false);
assert.deepEqual(h.model.list(), captured);

// Denied, empty, malformed or missing replies keep the inventory without status.
for (const reply of [{returnValue:false}, {returnValue:true, devices:[]}, {returnValue:true}, null, 'text']) {
  h = harness(); h.model.start(); h.calls[0].reply(reply);
  assert.equal(h.model.live(), false, JSON.stringify(reply));
  assert.deepEqual(h.model.list(), captured);
  assert.equal(h.changes.length, 0, 'fallback to the same inventory is not a change');
}
const throwing = sources.create({inventory, call: () => { throw Error('no bridge'); }});
throwing.start();
assert.deepEqual(throwing.list(), captured, 'a missing service bridge keeps the inventory');
const silent = sources.create({inventory});
silent.start();
assert.deepEqual(silent.list(), captured, 'no service caller keeps the inventory');
assert.deepEqual(sources.create({}).list(), [], 'no inventory and no status is an empty list');

// A replaced inventory (profile restore) is read on demand.
let current = [{appId:'a',label:'A'}];
const lazy = sources.create({inventory: () => current});
current = [{appId:'b',label:'B'}];
assert.deepEqual(lazy.list().map(i => i.appId), ['b']);

// Preview sources: HDMI ports by app ID or EIM port ID; anything else has no live preview.
for (const [appId, id, uri] of [
  ['com.webos.app.hdmi1', null, 'ext://hdmi:1'], ['com.webos.app.hdmi4', 'HDMI_4', 'ext://hdmi:4'], ['preview.hdmi2', 'HDMI_2', 'ext://hdmi:2'],
  ['com.webos.app.hdmi10', null, null], ['com.webos.app.externalinput.av1', 'AV_1', null], ['com.webos.app.livetv', null, null], [null, null, null]
]) assert.equal(sources.source(appId, id), uri, appId + ' / ' + id);

// Icon family classifier.
for (const [label, device, kind] of [
  ['HDMI 1', 'PlayStation 5', 'game'], ['Xbox', null, 'game'], ['HDMI 2', 'Nintendo Switch', 'game'], ['PS5', null, 'game'],
  ['HDMI 3', 'Apple TV', 'stream'], ['Chromecast', null, 'stream'], ['HDMI', 'Fire TV Stick', 'stream'], ['Roku Ultra', null, 'stream'],
  ['Office PC', null, 'pc'], ['HDMI 4', 'MacBook Pro', 'pc'], ['Laptop', null, 'pc'],
  ['HDMI 1', null, 'hdmi'], ['Machine room', null, 'hdmi'], ['Switchboard', null, 'hdmi'], ['Firewall', null, 'hdmi']
]) assert.equal(sources.classify(label, device), kind, label + ' / ' + device);

const memory = new Map();
const storage = {getItem: k => memory.has(k) ? memory.get(k) : null, setItem: (k, v) => memory.set(k, v)};
// Previews default on, persist either way, and tolerate broken storage.
memory.clear();
assert.equal(sources.previewEnabled(storage), true, 'previews are on by default');
sources.setPreviewEnabled(storage, false);
assert.equal(memory.get(sources.previewKey), '{"version":1,"enabled":false}');
assert.equal(sources.previewEnabled(storage), false);
sources.setPreviewEnabled(storage, true);
assert.equal(sources.previewEnabled(storage), true);
for (const raw of ['{bad', '{"version":2,"enabled":false}', '{"version":1,"enabled":"no"}', 'null']) {
  memory.set(sources.previewKey, raw);
  assert.equal(sources.previewEnabled(storage), true, 'unknown preview preference keeps the default: ' + raw);
}
assert.equal(sources.previewEnabled({getItem() { throw Error('denied'); }}), true);
assert.throws(() => sources.setPreviewEnabled(storage, 1), /invalid-input-preview-setting/);
console.log('PASS input sources: live status overlay, inventory fallback, classifier, preview sources and preferences');
