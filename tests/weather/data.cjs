'use strict';
const assert = require('node:assert/strict'),
  Weather = require('../../launcher/weather-data.js');
const memory = {};
const storage = {
  getItem: (k) => memory[k] || null,
  setItem: (k, v) => (memory[k] = v),
  removeItem: (k) => delete memory[k]
};
let clock = 100000000,
  calls = [],
  pending = [];
const create = () =>
  Weather.create({
    storage,
    now: () => clock,
    request: (url) => {
      calls.push(url);
      let resolve, reject;
      const promise = new Promise((a, b) => {
        resolve = a;
        reject = b;
      });
      const item = { url, resolve, reject, cancelled: false };
      pending.push(item);
      return {
        promise,
        cancel() {
          item.cancelled = true;
          reject(Error('cancelled'));
        }
      };
    }
  });
const flush = () => new Promise((r) => setImmediate(r));
const answer = async (body) => {
  await flush();
  pending.shift().resolve(body);
  await new Promise((r) => setImmediate(r));
};
const location = {
  id: 1,
  name: 'Berlin',
  latitude: 52.5,
  longitude: 13.4,
  country: 'Germany'
};
const payload = {
  timezone: 'Europe/Berlin',
  current: {
    temperature_2m: 10,
    apparent_temperature: 8,
    weather_code: 3,
    is_day: 1,
    wind_speed_10m: 4,
    relative_humidity_2m: 60
  },
  daily: {
    time: ['2026-11-09'],
    temperature_2m_min: [4],
    temperature_2m_max: [11],
    weather_code: [61],
    precipitation_probability_max: [50]
  }
};
(async () => {
  const store = create();
  store.start();
  assert.equal(calls.length, 0, 'off by default');
  store.setPreferences({ enabled: true });
  assert.equal(calls.length, 0, 'no city means no request');
  store.search('B');
  assert.equal(calls.length, 0);
  store.search('Berlin');
  await answer({ results: [location, { ...location, latitude: 999 }] });
  assert.equal(store.state().results.length, 1);
  store.select(1);
  await answer(payload);
  assert.equal(store.state().data.temp, 10);
  assert.equal(store.state().data.days.length, 1);
  const count = calls.length;
  store.setPreferences({ units: 'imperial', preferred: 'details' });
  assert.equal(calls.length, count, 'canonical cache reused');
  assert.equal(store.state().data.temp, 10);
  clock += 16 * 60000;
  store.refresh();
  await flush();
  pending.shift().reject(Error('offline'));
  await new Promise((r) => setImmediate(r));
  assert.equal(store.state().stale, true);
  clock += 6 * 60 * 60000;
  store.refresh();
  await flush();
  assert.equal(store.state().data, null, 'expired data removed');
  store.setPreferences({ enabled: false });
  assert(pending.shift().cancelled);
  const stopped = calls.length;
  store.refresh();
  assert.equal(calls.length, stopped);
  const restored = create();
  restored.start();
  assert.equal(restored.state().enabled, false);
  assert.equal(calls.length, stopped, 'disabled startup no requests');
  restored.setPreferences({ enabled: true });
  await flush();
  restored.setAllowed(false);
  assert(pending.pop().cancelled);
  const blocked = calls.length;
  restored.setMode('auto');
  assert.equal(calls.length, blocked, 'Ribbon blocks location lookup');
  restored.setAllowed(true);
  await answer({
    success: true,
    city: 'Paris',
    country_code: 'FR',
    latitude: 48.8,
    longitude: 2.3
  });
  await answer(payload);
  assert.equal(restored.state().location.name, 'Paris');
  assert(!JSON.stringify(memory).includes('"ip"'));
  restored.destroy();
  const invalid = create();
  invalid.start();
  invalid.refresh(true);
  await answer({ ...payload, current: { temperature_2m: null } });
  assert.equal(
    invalid.state().status,
    'stale',
    'malformed response follows bounded failure path'
  );
  invalid.refresh(true);
  await answer(payload);
  assert.equal(invalid.state().status, 'ready');
  invalid.destroy();
  assert.equal(
    Weather.normalize({ ...payload, current: { temperature_2m: 0 } }, location)
      .wind,
    null
  );
  assert.throws(() =>
    Weather.normalize(
      { ...payload, current: { temperature_2m: null } },
      location
    )
  );
  const damaged = JSON.parse(memory[Weather.key]);
  damaged.caches['open-meteo'].data.days = [
    null,
    { date: '<bad>', low: -999, high: 999 }
  ];
  damaged.caches['open-meteo'].data.humidity = 150;
  memory[Weather.key] = JSON.stringify(damaged);
  const sanitized = create();
  await sanitized.start();
  assert.deepEqual(sanitized.state().data.days, []);
  assert.equal(sanitized.state().data.humidity, null);
  const enabled = sanitized.state().enabled;
  assert.throws(() =>
    sanitized.setPreferences({ enabled: !enabled, invalid: true })
  );
  assert.equal(
    sanitized.state().enabled,
    enabled,
    'invalid preferences do not partially mutate state'
  );
  sanitized.destroy();
  let expiresAt = 100000000;
  const expiring = Weather.create({
    now: () => expiresAt,
    storage: {
      getItem: () =>
        JSON.stringify({
          enabled: true,
          location,
          locationLanguage: 'en',
          cache: {
            key: '52.500,13.400',
            updated: expiresAt - 6 * 3600000 + 10,
            data: Weather.normalize(payload, location)
          }
        }),
      setItem() {}
    },
    request: () => ({ promise: Promise.reject(Error('offline')), cancel() {} })
  });
  await expiring.start();
  const expiredEvents = [];
  expiring.onChange((s) => expiredEvents.push(s));
  expiresAt += 20;
  await expiring.refresh();
  assert.equal(
    expiredEvents.length,
    1,
    'expiry emits even during offline retry backoff'
  );
  assert.equal(expiredEvents[0].data, null);
  assert.equal(expiredEvents[0].status, 'error');
  expiring.destroy();
  assert.equal(Weather.condition(null).label, 'Unavailable');
  assert.equal(Weather.condition(0, false).icon, 'clear-night');
  console.log(
    'PASS weather data opt-in, location, canonical cache, errors, cancellation, expiry and restore'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
