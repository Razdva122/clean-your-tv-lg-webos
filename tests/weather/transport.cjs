'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const file = 'launcher/weather-transport.js';
assert(fs.existsSync(file), 'native weather transport must exist');
function setup(available = true) {
  const calls = [],
    timers = new Map();
  let timerId = 0;
  const root = {
    Promise,
    Date,
    setTimeout(fn, ms) {
      assert(ms > 12000 && ms <= 20000);
      timers.set(++timerId, fn);
      return timerId;
    },
    clearTimeout(id) {
      timers.delete(id);
    }
  };
  if (available)
    root.PalmServiceBridge = function () {
      this.call = (uri, body) =>
        calls.push({ uri, body: JSON.parse(body), bridge: this });
      this.cancel = () => {
        this.cancelled = true;
      };
    };
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), { window: root });
  return { root, calls, timers };
}
(async () => {
  const unavailable = setup(false).root.HomeWeatherTransport.met({
    latitude: 1,
    longitude: 2
  });
  await assert.rejects(unavailable.promise);
  unavailable.cancel();
  for (const rootEdition of [false, true]) {
    const { root, calls, timers } = setup();
    if (rootEdition) root.ROOT_VERSION = 'test';
    const request = root.HomeWeatherTransport.met({
      latitude: 1.123456,
      longitude: 2
    });
    const call = calls[0];
    assert.equal(
      call.uri,
      'luna://' +
        (rootEdition
          ? 'com.cleanyourtv.root.preview.service'
          : 'com.gathin.tvhome.renewal') +
        '/weatherForecast'
    );
    assert.deepEqual(Object.keys(call.body).sort(), [
      'id',
      'latitude',
      'longitude'
    ]);
    assert.match(call.body.id, /^[a-zA-Z0-9-]{1,64}$/);
    assert.equal(call.body.latitude, 1.123456);
    call.bridge.onservicecallback(
      JSON.stringify({ returnValue: true, forecast: { properties: {} } })
    );
    assert.deepEqual(JSON.parse(JSON.stringify(await request.promise)), {
      properties: {}
    });
    assert.equal(timers.size, 0);
    request.cancel();
    assert.equal(calls.length, 1, 'settled request is inert');
  }
  for (const response of [
    'broken',
    '{}',
    '{"returnValue":false}',
    '{"returnValue":true,"forecast":[]}',
    '{"returnValue":true,"forecast":null}'
  ]) {
    const { root, calls } = setup(),
      request = root.HomeWeatherTransport.met({ latitude: 1, longitude: 2 });
    calls[0].bridge.onservicecallback(response);
    await assert.rejects(request.promise);
  }
  for (const deadline of [false, true]) {
    const { root, calls, timers } = setup(),
      request = root.HomeWeatherTransport.met({ latitude: 1, longitude: 2 });
    const rejected = assert.rejects(request.promise),
      original = calls[0],
      late = original.bridge.onservicecallback;
    if (deadline) [...timers.values()][0]();
    else request.cancel();
    await rejected;
    assert(original.bridge.cancelled);
    assert.equal(calls[1].uri, original.uri + 'Cancel');
    assert.deepEqual(calls[1].body, { id: original.body.id });
    late('{"returnValue":true,"forecast":{}}');
    request.cancel();
    assert.equal(calls.length, 2);
    assert.equal(timers.size, 0);
  }
  const { root, calls } = setup();
  const first = root.HomeWeatherTransport.met({ latitude: 1, longitude: 2 }),
    second = root.HomeWeatherTransport.met({ latitude: 1, longitude: 2 });
  assert.notEqual(calls[0].body.id, calls[1].body.id);
  const rejection = Promise.all([
    assert.rejects(first.promise),
    assert.rejects(second.promise)
  ]);
  first.cancel();
  second.cancel();
  await rejection;
  console.log(
    'PASS weather transport: service selection, validation, deadline, cancel, late callbacks'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
