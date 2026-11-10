'use strict';
const assert = require('node:assert/strict');
const name = require('../launcher/tv-name');
function storage(entries = []) {
  const values = new Map(entries);
  return {
    values,
    getItem: (k) => (values.has(k) ? values.get(k) : null),
    setItem: (k, v) => values.set(k, v)
  };
}
const legacy = storage([
  ['tvhome.layout', 'legacy layout'],
  ['tvhome.language', 'hi']
]);
let model = name.create(legacy, 'Home');
assert.equal(model.get(), 'Home');
assert.equal(legacy.getItem('tvhome.layout'), 'legacy layout');
assert.equal(legacy.getItem('tvhome.language'), 'hi');
assert.equal(model.set(' Aashiyaan '), 'Aashiyaan');
model = name.create(legacy, 'Home'); // Replacement package defaults must not reset a saved choice.
assert.equal(model.get(), 'Aashiyaan');
assert.equal(model.set(''), 'Home');
assert.equal(name.normalize('आशियाना'), 'आशियाना');
for (const value of ['x'.repeat(49), 'bad\nname', 'bad\u202ename', '\ud800'])
  assert.throws(() => model.set(value));
const failed = storage([['tvhome.name', 'Aashiyaan']]);
failed.setItem = () => {
  throw Error('quota');
};
const stable = name.create(failed, 'Home');
assert.throws(() => stable.set('Changed'));
assert.equal(stable.get(), 'Aashiyaan');
assert.equal(
  name.create(storage([['tvhome.name', 'bad\nname']]), 'Home').get(),
  'Home'
);
const snapshot = {
  schema: 1,
  inventory: {
    apps: [
      {
        id: 'example.app',
        title: 'Example',
        icon: 'data:image/png;base64,YQ=='
      }
    ],
    inputs: []
  },
  config: { columns: 5, dockApps: [], hiddenApps: [] },
  settings: { 'tvhome.name': 'Aashiyaan' }
};
for (const module of [
  '../launcher/user-data',
  '../updater-service/user-data',
  '../root-edition/ui/root-profile-data'
]) {
  const data = require(module);
  assert.equal(data.validate(snapshot).settings['tvhome.name'], 'Aashiyaan');
  const old = JSON.parse(JSON.stringify(snapshot));
  delete old.settings['tvhome.name'];
  assert.doesNotThrow(() => data.validate(old));
  for (const value of ['x'.repeat(49), 'bad\nname']) {
    const invalid = JSON.parse(JSON.stringify(snapshot));
    invalid.settings['tvhome.name'] = value;
    assert.throws(() => data.validate(invalid));
  }
}
console.log(
  'TV name: upgrade defaults, later changes, persistence, validation and both profile formats passed.'
);
// Simulated LS2 results: never imply acceptance on a physical television.
const app = 'com.gathin.tvhome';
const primaryPoint = (title) => ({
  id: app,
  launchPointId: app + '_default',
  title
});
function exercise(responses) {
  const calls = [];
  let result;
  name.rename(
    (uri, payload, callback) => {
      calls.push({ uri, payload });
      callback(responses.shift());
    },
    app,
    'New',
    (value) => (result = value)
  );
  return { calls, result };
}
const points = (title) => ({
  returnValue: true,
  launchPoints: [
    primaryPoint(title),
    { id: app, launchPointId: 'secondary', title: 'Other' }
  ]
});
let run = exercise([points('Home'), { returnValue: true }, points('New')]);
assert.equal(run.result, true);
assert.deepEqual(run.calls[1].payload, {
  launchPointId: app + '_default',
  title: 'New'
});
for (const responses of [
  [points('Home'), { returnValue: false }],
  [points('Home'), { returnValue: true }, points('Home')],
  [
    {
      returnValue: true,
      launchPoints: [primaryPoint('Home'), primaryPoint('Home')]
    }
  ],
  [
    {
      returnValue: true,
      launchPoints: [{ id: app, launchPointId: 'secondary', title: 'Home' }]
    }
  ]
]) {
  run = exercise(responses);
  assert.equal(run.result, false);
  assert.ok(run.calls.every((c) => !c.uri.includes('addLaunchPoint')));
}
assert.throws(() =>
  name.rename(
    () => {
      throw Error('must not call');
    },
    app,
    'bad\nname',
    () => {}
  )
);
