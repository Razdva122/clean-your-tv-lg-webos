'use strict';
const assert = require('node:assert/strict');
const Weather = require('../../launcher/weather-data.js');
const fs = require('node:fs');
const vm = require('node:vm');
const dayLabelSource = fs
  .readFileSync(require.resolve('../../launcher/weather.js'), 'utf8')
  .match(/  function dayLabel\([\s\S]*?\n  }/)[0];
function rendererDayLabel(day, weather, now) {
  class ClockDate extends Date {
    static now() {
      return now;
    }
  }
  return vm.runInNewContext('(' + dayLabelSource + ')', {
    Date: ClockDate,
    t: (value) => value,
    weekday: (value) => value
  })(day, 0, weather);
}
function metAt(now) {
  const body = met();
  body.properties.meta.updated_at = new Date(now - 4.5 * 3600000).toISOString();
  body.properties.timeseries = [0, 24].map((hours) => ({
    ...structuredClone(body.properties.timeseries[0]),
    time: new Date(now + hours * 3600000 - 30 * 60000).toISOString()
  }));
  return body;
}
const timeout = setTimeout(() => {
  throw Error('provider test did not finish');
}, 5000);
const NOW = Date.parse('2026-10-25T00:30:00Z');
const place = {
  name: 'Berlin',
  latitude: 52.5,
  longitude: 13.4,
  timezone: 'Europe/Berlin'
};
function met() {
  return {
    properties: {
      meta: {
        updated_at: '2026-10-25T00:00:00Z',
        units: {
          air_temperature: 'celsius',
          wind_speed: 'm/s',
          relative_humidity: '%'
        }
      },
      timeseries: [
        ['2026-10-25T00:00:00Z', 10, 'partlycloudy_night'],
        ['2026-10-25T01:00:00Z', 8, 'rain'],
        ['2026-10-25T23:30:00Z', 4, 'snow'],
        ['2026-10-26T12:00:00Z', 11, 'clearsky_day']
      ].map(([time, temp, symbol]) => ({
        time,
        data: {
          instant: {
            details: {
              air_temperature: temp,
              wind_speed: 1.4,
              relative_humidity: 70
            }
          },
          next_1_hours: { summary: { symbol_code: symbol } }
        }
      }))
    }
  };
}
const om = { current: { temperature_2m: 12, weather_code: 3 }, daily: {} };
const flush = () => new Promise((r) => setImmediate(r));
function harness(saved, late = false) {
  let clock = NOW,
    memory = saved ? JSON.stringify(saved) : null;
  const calls = [];
  function request(source) {
    return (value) => {
      let resolve, reject;
      const promise = new Promise((a, b) => {
        resolve = a;
        reject = b;
      });
      if (source === 'met-no')
        assert.equal(
          JSON.parse(memory).metAttempt.at,
          clock,
          'attempt persists before native transport starts'
        );
      const item = { source, value, resolve, reject, cancelled: false };
      calls.push(item);
      return {
        promise,
        cancel() {
          item.cancelled = true;
          if (!late) reject(Error('cancelled'));
        }
      };
    };
  }
  const store = Weather.create({
    now: () => clock,
    storage: {
      getItem: () => memory,
      setItem: (k, v) => (memory = v),
      removeItem: () => (memory = null)
    },
    request: request('open-meteo'),
    metRequest: request('met-no')
  });
  return {
    store,
    calls,
    saved: () => JSON.parse(memory),
    advance: (ms) => (clock += ms)
  };
}
const settings = (provider = 'auto') => ({
  enabled: true,
  provider,
  location: place,
  locationLanguage: 'en'
});
(async () => {
  const value = Weather.normalizeMet(met(), place, NOW);
  assert.equal(value.wind, 1.4);
  assert.equal(value.humidity, 70);
  assert.equal(value.feels, null);
  assert.equal(value.precip, null);
  assert.equal(value.code, 2);
  assert.equal(value.isDay, false);
  assert.deepEqual(
    value.days.map((d) => [d.date, d.low, d.high]),
    [
      ['2026-10-25', 8, 10],
      ['2026-10-26', 4, 11]
    ]
  );
  for (const [symbol, code] of [
    ['clearsky_day', 0],
    ['cloudy', 3],
    ['fog', 45],
    ['lightrain', 61],
    ['heavyrain', 65],
    ['sleet', 67],
    ['snow', 73],
    ['rainshowers_day', 80],
    ['snowshowers_night', 85],
    ['rainandthunder', 95]
  ]) {
    const body = met();
    body.properties.timeseries[0].data.next_1_hours.summary.symbol_code =
      symbol;
    assert.equal(Weather.normalizeMet(body, place, NOW).code, code, symbol);
  }
  for (const mutate of [
    (b) => (b.properties.meta.units.air_temperature = 'fahrenheit'),
    (b) => (b.properties.meta.units.wind_speed = 'km/h'),
    (b) => (b.properties.meta.units.relative_humidity = 'fraction'),
    (b) => (b.properties.meta.updated_at = 'bad'),
    (b) => (b.properties.meta.updated_at = '2026-02-30T00:00:00Z'),
    (b) => (b.properties.meta.updated_at = '2026-10-24T12:29:59Z'),
    (b) => (b.properties.timeseries[0].time = 'bad'),
    (b) => (b.properties.timeseries[3].time = '2026-11-31T00:00:00Z'),
    (b) =>
      (b.properties.timeseries[0].data.instant.details.air_temperature = 999),
    (b) => (b.properties.timeseries[0].data.instant.details.wind_speed = -1),
    (b) =>
      (b.properties.timeseries[0].data.instant.details.relative_humidity = 101)
  ]) {
    const body = met();
    mutate(body);
    assert.throws(() => Weather.normalizeMet(body, place, NOW));
  }
  for (const hours of [3.5, 4.5, 6, 12]) {
    const body = met();
    body.properties.meta.updated_at = new Date(
      NOW - hours * 3600000
    ).toISOString();
    assert.equal(
      Weather.normalizeMet(body, place, NOW).temp,
      10,
      `${hours}-hour model retains current forecast points`
    );
  }
  const oldPoint = met();
  oldPoint.properties.timeseries = [oldPoint.properties.timeseries[0]];
  assert.throws(() => Weather.normalizeMet(oldPoint, place, NOW + 3 * 3600000));
  for (const [zone, instant, offset] of [
    ['Asia/Tokyo', '2026-10-24T23:30:00Z', 32400],
    ['Asia/Tokyo', '2026-10-25T15:30:00Z', 32400],
    ['America/Los_Angeles', '2026-10-25T00:30:00Z', -25200],
    ['Europe/Berlin', '2026-10-25T00:30:00Z', 7200],
    ['Europe/Berlin', '2026-10-25T01:30:00Z', 3600]
  ]) {
    const now = Date.parse(instant);
    const weather = Weather.normalizeMet(
      metAt(now),
      { ...place, timezone: zone },
      now
    );
    assert.equal(
      rendererDayLabel(weather.days[0], weather, now),
      'Today',
      zone + ' local midnight'
    );
    assert.equal(
      rendererDayLabel(weather.days[1], weather, now),
      'Tomorrow',
      zone + ' next local date'
    );
    assert.equal(weather.offset, offset, zone + ' current offset');
  }
  const extended = met();
  for (let day = 27; day <= 31; day++) {
    const row = structuredClone(extended.properties.timeseries[0]);
    row.time = `2026-10-${day}T12:00:00Z`;
    extended.properties.timeseries.push(row);
  }
  assert.equal(Weather.normalizeMet(extended, place, NOW).days.length, 4);
  assert.equal(
    Weather.normalizeMet(met(), { ...place, timezone: 'invalid/zone' }, NOW)
      .timezone,
    'UTC'
  );
  const six = met();
  six.properties.timeseries[0].data.next_6_hours =
    six.properties.timeseries[0].data.next_1_hours;
  six.properties.timeseries[0].data.next_1_hours = { details: {} };
  assert.equal(Weather.normalizeMet(six, place, NOW).code, 2);
  const unknown = met();
  unknown.properties.timeseries[0].data.next_1_hours.summary.symbol_code =
    'unknown';
  assert.equal(Weather.normalizeMet(unknown, place, NOW).code, null);
  const optional = met();
  delete optional.properties.timeseries[0].data.instant.details.wind_speed;
  assert.equal(Weather.normalizeMet(optional, place, NOW).wind, null);
  assert.throws(() => Weather.normalizeMet(met(), place, NaN));
  const intl = global.Intl;
  try {
    global.Intl = undefined;
    assert.equal(Weather.normalizeMet(met(), place, NOW).timezone, 'UTC');
    assert.equal(Weather.normalizeMet(met(), place, NOW).days[0].low, 4);
    const utc = Weather.normalizeMet(met(), place, NOW);
    assert.equal(utc.offset, 0);
    assert.equal(rendererDayLabel(utc.days[0], utc, NOW), 'Today');
  } finally {
    global.Intl = intl;
  }
  assert.equal(harness().store.state().provider, 'auto');
  assert.equal(
    harness({ enabled: false }).store.state().provider,
    'open-meteo'
  );
  for (const provider of ['met-no', 'open-meteo']) {
    const h = harness(settings(provider));
    h.store.start();
    await flush();
    assert.equal(h.calls[0].source, provider);
    h.calls[0].reject(Error('offline'));
    await flush();
    assert.equal(h.calls.length, 1);
    assert.equal(h.store.state().status, 'error');
    h.store.destroy();
  }
  // Admission belongs to MET's actual request boundary, not success/backoff state.
  const cooldown = harness(settings('met-no'));
  cooldown.store.start();
  await flush();
  cooldown.calls[0].reject(Error('offline'));
  await flush();
  cooldown.advance(5 * 60000);
  cooldown.store.refresh();
  await flush();
  assert.equal(
    cooldown.calls.length,
    1,
    'failed MET attempt cannot repeat after five minutes'
  );
  await cooldown.store.refresh(true);
  assert.equal(cooldown.calls.length, 1, 'force cannot bypass MET cadence');
  await cooldown.store.setPreferences({
    enabled: false,
    provider: 'open-meteo'
  });
  await cooldown.store.setPreferences({ enabled: true, provider: 'met-no' });
  assert.equal(
    cooldown.calls.length,
    1,
    'Off/source toggle cannot bypass MET cadence'
  );
  assert.equal(cooldown.store.state().status, 'error');
  assert.equal(
    cooldown.store.state().data,
    null,
    'cooldown cannot claim ready without data'
  );
  const failedReload = harness(cooldown.saved());
  failedReload.advance(5 * 60000);
  await failedReload.store.start();
  assert.equal(failedReload.calls.length, 0, 'failed attempt survives reload');
  failedReload.store.destroy();
  cooldown.advance(175 * 60000 - 1);
  await cooldown.store.refresh(true);
  assert.equal(cooldown.calls.length, 1, 'blocked just before three hours');
  cooldown.advance(1);
  cooldown.store.refresh(true);
  await flush();
  assert.equal(cooldown.calls.length, 2, 'three-hour boundary permits request');
  cooldown.store.destroy();
  const cachedFallback = harness({
    ...settings(),
    lastSource: 'open-meteo',
    caches: {
      'open-meteo': {
        key: '52.500,13.400',
        updated: NOW - 16 * 60000,
        data: Weather.normalize(om, place)
      },
      'met-no': {
        key: '52.500,13.400',
        updated: NOW - 10 * 60000,
        data: Weather.normalizeMet(met(), place, NOW)
      }
    }
  });
  cachedFallback.store.start();
  await flush();
  assert.equal(cachedFallback.calls[0].source, 'open-meteo');
  cachedFallback.calls[0].reject(Error('offline'));
  await flush();
  assert.equal(
    cachedFallback.calls.length,
    1,
    'Auto fallback reuses fresh MET entry'
  );
  assert.equal(cachedFallback.store.state().source, 'met-no');
  assert.equal(
    cachedFallback.store.state().updated,
    NOW - 10 * 60000,
    'reuse preserves cache age'
  );
  await cachedFallback.store.refresh(true);
  assert.equal(
    cachedFallback.calls.length,
    1,
    'force reuses fresh source entry'
  );
  cachedFallback.store.destroy();
  for (const stoppedBy of ['off', 'hidden', 'provider', 'destroy']) {
    const stopped = harness(settings('met-no'), true);
    stopped.store.start();
    await flush();
    if (stoppedBy === 'off')
      await stopped.store.setPreferences({ enabled: false });
    if (stoppedBy === 'hidden') stopped.store.setAllowed(false);
    if (stoppedBy === 'provider')
      await stopped.store.setPreferences({
        enabled: false,
        provider: 'open-meteo'
      });
    if (stoppedBy === 'destroy') stopped.store.destroy();
    assert(stopped.calls[0].cancelled);
    stopped.calls[0].resolve(met());
    await flush();
    assert.equal(stopped.calls.length, 1, 'cancel cannot trigger fallback');
    const resumed = harness({
      ...stopped.saved(),
      enabled: true,
      provider: 'met-no'
    });
    await resumed.store.start();
    assert.equal(
      resumed.calls.length,
      0,
      stoppedBy + ' cancellation persists cooldown'
    );
    assert.equal(resumed.store.state().status, 'error');
    resumed.store.destroy();
    stopped.store.destroy();
  }
  const autoCooldown = harness(settings('met-no'));
  autoCooldown.store.start();
  await flush();
  autoCooldown.calls[0].reject(Error('offline'));
  await flush();
  autoCooldown.store.setPreferences({ provider: 'auto' });
  await flush();
  assert.equal(
    autoCooldown.calls.length,
    2,
    'Auto can use other provider while MET cools down'
  );
  assert.equal(autoCooldown.calls[1].source, 'open-meteo');
  autoCooldown.calls[1].resolve(om);
  await flush();
  autoCooldown.store.destroy();
  for (const record of [
    { key: '52.5,13.4', at: NOW + 100 * 3600000 },
    { key: '52.5,13.4', at: 'bad' },
    { key: '52.5,13.4', at: -1 },
    { key: 'bad', at: NOW },
    { key: 'bad', at: NOW - 24 * 3600000 },
    false
  ]) {
    const damagedAttempt = harness({
      ...settings('met-no'),
      metAttempt: record
    });
    damagedAttempt.store.start();
    await flush();
    assert.equal(
      damagedAttempt.calls.length,
      0,
      'malformed/future record has conservative cooldown'
    );
    assert.deepEqual(
      damagedAttempt.saved().metAttempt,
      { key: '52.5,13.4', at: NOW },
      'repair persists a bounded timestamp'
    );
    damagedAttempt.advance(3 * 3600000);
    damagedAttempt.store.refresh(true);
    await flush();
    assert.equal(
      damagedAttempt.calls.length,
      1,
      'repaired record permits request at three hours'
    );
    damagedAttempt.store.destroy();
  }
  const cachedOpenFallback = harness({
    ...settings(),
    lastSource: 'met-no',
    metAttempt: { key: '52.5,13.4', at: NOW },
    caches: {
      'open-meteo': {
        key: '52.500,13.400',
        updated: NOW - 10 * 60000,
        data: Weather.normalize(om, place)
      }
    }
  });
  await cachedOpenFallback.store.start();
  await cachedOpenFallback.store.refresh(true);
  assert.equal(
    cachedOpenFallback.calls.length,
    0,
    'forced Auto fallback reuses fresh Open-Meteo entry'
  );
  assert.equal(cachedOpenFallback.store.state().source, 'open-meteo');
  assert.equal(cachedOpenFallback.store.state().updated, NOW - 10 * 60000);
  cachedOpenFallback.store.destroy();
  const moved = harness({
    ...settings('met-no'),
    location: { ...place, latitude: -1.23455 },
    metAttempt: { key: '-1.2345,13.4', at: NOW }
  });
  await moved.store.start();
  assert.equal(
    moved.calls.length,
    0,
    'request key matches native negative tie rounding'
  );
  moved.store.search('next');
  moved.calls[0].resolve({
    results: [{ ...place, id: 2, latitude: -1.234549, name: 'renamed' }]
  });
  await flush();
  await moved.store.select(2);
  assert.equal(
    moved.calls.length,
    1,
    'same canonical request under new location name stays blocked'
  );
  moved.store.search('different');
  moved.calls[1].resolve({ results: [{ ...place, id: 3, latitude: -1.2344 }] });
  await flush();
  moved.store.select(3);
  await flush();
  assert.equal(
    moved.calls[2].source,
    'met-no',
    'genuinely different request location can start'
  );
  assert.deepEqual(
    moved.saved().metAttempt,
    { key: '-1.2344,13.4', at: NOW },
    'only latest request location retained'
  );
  moved.store.destroy();
  const h = harness(settings());
  h.store.start();
  await flush();
  assert.equal(h.calls[0].source, 'met-no');
  h.calls[0].resolve({});
  await flush();
  assert.equal(h.calls[1].source, 'open-meteo');
  h.calls[1].resolve(om);
  await flush();
  assert.equal(h.store.state().source, 'open-meteo');
  h.advance(16 * 60000);
  h.store.refresh();
  await flush();
  assert.equal(h.calls[2].source, 'open-meteo', 'last good first');
  h.calls[2].reject(Error('offline'));
  await flush();
  assert.equal(
    h.calls.length,
    3,
    'failed first MET attempt remains in cooldown'
  );
  assert.equal(h.store.state().status, 'stale');
  h.advance(164 * 60000);
  h.store.refresh(true);
  await flush();
  h.calls[3].reject(Error('offline'));
  await flush();
  assert.equal(h.calls[4].source, 'met-no', 'MET eligible at three hours');
  h.calls[4].resolve(metAt(NOW + 3 * 3600000));
  await flush();
  assert.equal(h.store.state().source, 'met-no');
  const manualOpen = h.store.setPreferences({ provider: 'open-meteo' });
  await flush();
  h.calls[5].resolve(om);
  await manualOpen;
  const count = h.calls.length;
  await h.store.setPreferences({ provider: 'met-no' });
  assert.equal(h.store.state().source, 'met-no');
  assert.equal(h.calls.length, count, 'MET three hour freshness');
  assert.deepEqual(Object.keys(h.saved().caches).sort(), [
    'met-no',
    'open-meteo'
  ]);
  const reload = harness(h.saved());
  reload.advance(3 * 3600000);
  await reload.store.start();
  assert.equal(reload.calls.length, 0);
  assert.equal(reload.store.state().source, 'met-no');
  reload.store.destroy();
  h.store.destroy();
  for (const stop of [
    (s) => s.setPreferences({ enabled: false }),
    (s) => s.setAllowed(false),
    (s) => s.destroy()
  ]) {
    const c = harness(settings(), true);
    c.store.start();
    await flush();
    stop(c.store);
    assert(c.calls[0].cancelled);
    c.calls[0].resolve(met());
    await flush();
    assert.equal(c.calls.length, 1);
    assert.equal(c.store.state().data, null);
  }
  const switched = harness(settings(), true);
  switched.store.start();
  await flush();
  switched.store.setPreferences({ provider: 'open-meteo' });
  await flush();
  assert(switched.calls[0].cancelled);
  switched.calls[0].resolve(met());
  switched.calls[1].resolve(om);
  await flush();
  assert.equal(switched.store.state().source, 'open-meteo');
  switched.store.destroy();
  const legacy = harness({
    ...settings('open-meteo'),
    provider: undefined,
    cache: {
      key: '52.500,13.400',
      updated: NOW,
      data: Weather.normalize(om, place)
    }
  });
  await legacy.store.start();
  assert.equal(legacy.calls.length, 0);
  assert.equal(legacy.store.state().source, 'open-meteo');
  legacy.store.destroy();
  const bounded = harness(settings());
  bounded.store.start();
  await flush();
  bounded.calls[0].reject(Error('offline'));
  await flush();
  bounded.calls[1].resolve({});
  await flush();
  assert.equal(bounded.calls.length, 2);
  assert.equal(bounded.store.state().status, 'error');
  await bounded.store.refresh();
  assert.equal(bounded.calls.length, 2, 'bounded retry backoff');
  bounded.store.destroy();
  const isolated = harness({
    ...settings('met-no'),
    cache: {
      key: '52.500,13.400',
      updated: NOW,
      data: Weather.normalize(om, place)
    }
  });
  isolated.store.start();
  await flush();
  assert.equal(
    isolated.store.state().data,
    null,
    'manual MET never displays legacy Open-Meteo'
  );
  isolated.store.destroy();
  const dstCache = {
    ...settings('met-no'),
    caches: {
      'met-no': {
        key: '52.500,13.400',
        updated: NOW,
        data: Weather.normalizeMet(metAt(NOW), place, NOW)
      }
    }
  };
  const dstRestored = harness(dstCache);
  dstRestored.advance(3600000);
  await dstRestored.store.start();
  assert.equal(
    dstRestored.store.state().data.offset,
    3600,
    'restored MET offset follows DST'
  );
  assert.equal(
    dstRestored.calls.length,
    0,
    'DST does not force fresh forecast request'
  );
  dstRestored.store.destroy();
  const dstLive = harness(dstCache);
  await dstLive.store.start();
  assert.equal(dstLive.store.state().data.offset, 7200);
  dstLive.advance(3600000);
  assert.equal(
    dstLive.store.state().data.offset,
    3600,
    'live cached offset follows DST'
  );
  dstLive.store.destroy();
  const aged = harness({
    ...settings('met-no'),
    caches: {
      'met-no': {
        key: '52.500,13.400',
        updated: NOW,
        data: Weather.normalizeMet(met(), place, NOW)
      },
      other: { key: 'bad', updated: NOW, data: {} }
    }
  });
  await aged.store.start();
  aged.advance(179 * 60000);
  await aged.store.refresh();
  assert.equal(aged.calls.length, 0, 'MET cache fresh for three hours');
  aged.advance(60000);
  aged.store.refresh();
  await flush();
  assert.equal(aged.calls.length, 1);
  aged.calls[0].reject(Error('offline'));
  await flush();
  assert.equal(aged.store.state().stale, true);
  aged.advance(181 * 60000);
  assert.equal(aged.store.state().data, null, 'six hour max age');
  aged.store.destroy();
  const relocated = harness(settings());
  relocated.store.start();
  await flush();
  relocated.calls[0].resolve(met());
  await flush();
  relocated.store.search('Paris');
  relocated.calls[1].resolve({
    results: [
      {
        id: 9,
        name: 'Paris',
        latitude: 48.8,
        longitude: 2.3,
        timezone: 'Europe/Paris'
      }
    ]
  });
  await flush();
  relocated.store.select(9);
  await flush();
  assert.equal(relocated.store.state().location.timezone, 'Europe/Paris');
  assert.equal(relocated.store.state().source, null);
  assert.deepEqual(relocated.saved().caches, {}, 'only one location retained');
  assert.equal(relocated.calls[2].source, 'met-no');
  relocated.store.destroy();
  for (const provider of ['met-no', 'open-meteo']) {
    const localizedPlace = { ...place, id: 2950159 };
    const localized = harness({
      ...settings(provider),
      location: localizedPlace,
      lastSource: provider,
      caches: {
        'met-no': {
          key: '52.500,13.400',
          updated: NOW,
          data: Weather.normalizeMet(met(), localizedPlace, NOW)
        },
        'open-meteo': {
          key: '52.500,13.400',
          updated: NOW,
          data: Weather.normalize(om, localizedPlace)
        }
      }
    });
    await localized.store.start();
    localized.store.setLanguage('ru');
    await flush();
    assert.match(localized.calls[0].value, /geocoding-api.*\/v1\/get/);
    localized.calls[0].resolve({ ...localizedPlace, name: 'Берлин' });
    await flush();
    assert.equal(localized.store.state().data.city, 'Берлин');
    await localized.store.setPreferences({
      provider: provider === 'met-no' ? 'open-meteo' : 'met-no'
    });
    assert.equal(localized.store.state().location.name, 'Берлин');
    assert.equal(
      localized.store.state().data.city,
      'Берлин',
      'switching fresh source cache preserves the localized city'
    );
    assert.equal(
      localized.calls.length,
      1,
      'localization needs no forecast refetch'
    );
    for (const cache of Object.values(localized.saved().caches)) {
      assert.equal(cache.data.city, 'Берлин');
      assert.equal(cache.updated, NOW, 'localization cannot extend cache age');
    }
    localized.store.destroy();
  }
  clearTimeout(timeout);
  console.log(
    'PASS weather providers normalization, bounded selection, caches and cancellation'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
