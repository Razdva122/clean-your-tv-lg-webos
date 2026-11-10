/* Trusted weather data. Themes never choose endpoints or access location/network APIs. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WeatherData = factory();
})(this, function () {
  'use strict';
  var KEY = 'tvhome.weather.v1',
    FRESH = 15 * 60000,
    MET_FRESH = 3 * 60 * 60000,
    // Global MET models update every six hours; allow one missed model cycle.
    MET_MODEL_AGE = 12 * 60 * 60000,
    MAX_AGE = 6 * 60 * 60000,
    RETRY = 5 * 60000,
    AUTO_AGE = 24 * 60 * 60000;
  var formats = ['text', 'current', 'details', 'forecast'];
  function finite(v) {
    return typeof v === 'number' && isFinite(v) ? v : null;
  }
  function bounded(v, low, high) {
    return finite(v) !== null && v >= low && v <= high ? v : null;
  }
  function text(v, max) {
    return typeof v === 'string' && v.trim() ? v.trim().slice(0, max) : null;
  }
  function location(input) {
    if (
      !input ||
      typeof input !== 'object' ||
      !text(input.name, 120) ||
      finite(input.latitude) === null ||
      finite(input.longitude) === null ||
      Math.abs(input.latitude) > 90 ||
      Math.abs(input.longitude) > 180
    )
      return null;
    var out = {
      name: text(input.name, 120),
      latitude: input.latitude,
      longitude: input.longitude,
      country: text(input.country, 120) || '',
      admin1: text(input.admin1, 120) || ''
    };
    if (typeof input.id === 'number' && input.id > 0 && input.id % 1 === 0)
      out.id = input.id;
    var zone = timezone(input.timezone);
    if (zone) out.timezone = zone;
    return out;
  }
  function normalize(body, place) {
    var c = body && body.current,
      d = (body && body.daily) || {};
    if (
      !c ||
      finite(c.temperature_2m) === null ||
      Math.abs(c.temperature_2m) > 150
    )
      throw Error('weather-invalid');
    var days = Array.isArray(d.time)
      ? d.time
          .slice(0, 4)
          .map(function (date, i) {
            return {
              date: date,
              low: finite(d.temperature_2m_min && d.temperature_2m_min[i]),
              high: finite(d.temperature_2m_max && d.temperature_2m_max[i]),
              code: finite(d.weather_code && d.weather_code[i])
            };
          })
          .filter(function (day) {
            return (
              typeof day.date === 'string' &&
              /^\d{4}-\d{2}-\d{2}$/.test(day.date) &&
              day.low !== null &&
              day.high !== null &&
              day.low <= day.high &&
              Math.abs(day.low) <= 150 &&
              Math.abs(day.high) <= 150
            );
          })
      : [];
    return {
      city: place.name,
      temp: c.temperature_2m,
      feels: bounded(c.apparent_temperature, -150, 150),
      wind: bounded(c.wind_speed_10m, 0, 150),
      humidity: bounded(c.relative_humidity_2m, 0, 100),
      precip: bounded(
        d.precipitation_probability_max && d.precipitation_probability_max[0],
        0,
        100
      ),
      code: finite(c.weather_code),
      isDay: c.is_day !== 0,
      time: text(c.time, 40) || '',
      timezone: text(body.timezone, 80) || 'UTC',
      offset: finite(body.utc_offset_seconds) || 0,
      days: days
    };
  }
  function timezone(value) {
    if (
      typeof value !== 'string' ||
      value.length > 80 ||
      !/^[A-Za-z_]+(?:\/[A-Za-z0-9_+\-]+)*$/.test(value)
    )
      return null;
    try {
      if (typeof Intl === 'undefined' || !Intl.DateTimeFormat) return null;
      new Intl.DateTimeFormat('en-US', { timeZone: value }).format(new Date(0));
      return value;
    } catch (_) {
      return null;
    }
  }
  function calendarFormatter(zone) {
    return zone !== 'UTC'
      ? new Intl.DateTimeFormat('en-US', {
          timeZone: zone,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        })
      : null;
  }
  function calendarParts(formatter, ms) {
    return formatter.format(new Date(ms)).match(/\d+/g);
  }
  function calendarOffset(formatter, ms) {
    if (!formatter) return 0;
    var parts = calendarParts(formatter, ms);
    return (
      (Date.UTC(
        Number(parts[2]),
        Number(parts[0]) - 1,
        Number(parts[1]),
        Number(parts[3]) % 24,
        Number(parts[4]),
        Number(parts[5])
      ) -
        Math.floor(ms / 1000) * 1000) /
      1000
    );
  }
  function metCode(symbol) {
    var name = String(symbol || '').replace(/_(day|night|polartwilight)$/, ''),
      simple = { clearsky: 0, fair: 1, partlycloudy: 2, cloudy: 3, fog: 45 };
    if (Object.prototype.hasOwnProperty.call(simple, name)) return simple[name];
    if (!/^(light|heavy)?(rain|sleet|snow)(showers)?(andthunder)?$/.test(name))
      return null;
    if (/thunder/.test(name)) return 95;
    if (/snowshowers/.test(name)) return 85;
    if (/snow/.test(name)) return 73;
    if (/sleet/.test(name)) return 67;
    if (/rainshowers/.test(name)) return 80;
    return name === 'heavyrain' ? 65 : 61;
  }
  function metTime(value) {
    if (
      typeof value !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)
    )
      throw Error('weather-invalid');
    var ms = Date.parse(value);
    if (
      !isFinite(ms) ||
      new Date(ms).toISOString().replace('.000Z', 'Z') !==
        value.replace('.000Z', 'Z')
    )
      throw Error('weather-invalid');
    return ms;
  }
  function normalizeMet(body, place, nowMs) {
    var props = body && body.properties,
      meta = props && props.meta,
      units = meta && meta.units,
      rows = props && props.timeseries,
      updated = metTime(meta && meta.updated_at),
      zone = timezone(place.timezone) || 'UTC';
    if (
      finite(nowMs) === null ||
      !units ||
      units.air_temperature !== 'celsius' ||
      units.wind_speed !== 'm/s' ||
      units.relative_humidity !== '%' ||
      !isFinite(updated) ||
      updated > nowMs ||
      nowMs - updated > MET_MODEL_AGE ||
      !Array.isArray(rows) ||
      !rows.length
    )
      throw Error('weather-invalid');
    var formatter = calendarFormatter(zone);
    function dateKey(ms) {
      if (!formatter) return new Date(ms).toISOString().slice(0, 10);
      var parts = calendarParts(formatter, ms);
      return parts[2] + '-' + parts[0] + '-' + parts[1];
    }
    var points = rows
      .map(function (row) {
        var ms = metTime(row && row.time),
          data = row && row.data,
          details = data && data.instant && data.instant.details,
          summary =
            data &&
            ((data.next_1_hours && data.next_1_hours.summary) ||
              (data.next_6_hours && data.next_6_hours.summary) ||
              (data.next_12_hours && data.next_12_hours.summary)),
          symbol = summary && summary.symbol_code;
        if (
          !isFinite(ms) ||
          !details ||
          bounded(details.air_temperature, -150, 150) === null ||
          (details.wind_speed !== undefined &&
            bounded(details.wind_speed, 0, 150) === null) ||
          (details.relative_humidity !== undefined &&
            bounded(details.relative_humidity, 0, 100) === null)
        )
          throw Error('weather-invalid');
        return {
          ms: ms,
          temp: details.air_temperature,
          wind: bounded(details.wind_speed, 0, 150),
          humidity: bounded(details.relative_humidity, 0, 100),
          code: metCode(symbol),
          isDay: !/_night$/.test(symbol || '')
        };
      })
      .sort(function (a, b) {
        return a.ms - b.ms;
      });
    var current = points[0];
    points.forEach(function (point) {
      if (point.ms <= nowMs) current = point;
    });
    if (Math.abs(current.ms - nowMs) > MET_FRESH)
      throw Error('weather-invalid');
    // These are forecast ranges from supplied timestamped points, not observations.
    var days = [],
      today = dateKey(nowMs);
    points.forEach(function (point) {
      var date = dateKey(point.ms),
        day = days[days.length - 1];
      if (date < today) return;
      if (!day || day.date !== date) {
        if (days.length >= 4) return;
        day = {
          date: date,
          low: point.temp,
          high: point.temp,
          code: point.code
        };
        days.push(day);
      } else {
        day.low = Math.min(day.low, point.temp);
        day.high = Math.max(day.high, point.temp);
      }
    });
    return {
      city: place.name,
      temp: current.temp,
      feels: null,
      wind: current.wind,
      humidity: current.humidity,
      precip: null,
      code: current.code,
      isDay: current.isDay,
      time: new Date(current.ms).toISOString(),
      timezone: zone,
      offset: calendarOffset(formatter, nowMs),
      days: days
    };
  }
  function condition(code, day) {
    if (code === 0)
      return {
        label: 'Clear',
        icon: day === false ? 'clear-night' : 'clear-day'
      };
    if (code === 1 || code === 2)
      return {
        label: 'Partly cloudy',
        icon: day === false ? 'partly-cloudy-night' : 'partly-cloudy-day'
      };
    if (code === 3) return { label: 'Overcast', icon: 'overcast' };
    if (code === 45 || code === 48) return { label: 'Fog', icon: 'fog' };
    if (code >= 51 && code <= 57) return { label: 'Drizzle', icon: 'drizzle' };
    if (code >= 61 && code <= 67) return { label: 'Rain', icon: 'rain' };
    if ((code >= 71 && code <= 77) || code === 85 || code === 86)
      return { label: 'Snow', icon: 'snow' };
    if (code >= 80 && code <= 82) return { label: 'Showers', icon: 'rain' };
    if (code >= 95 && code <= 99)
      return { label: 'Thunderstorm', icon: 'thunderstorms' };
    return { label: 'Unavailable', icon: null };
  }
  function query(base, params) {
    return (
      base +
      '?' +
      Object.keys(params)
        .map(function (k) {
          return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
        })
        .join('&')
    );
  }
  function xhrRequest(url) {
    var xhr = new XMLHttpRequest(),
      finish,
      settled = false;
    var promise = new Promise(function (resolve, reject) {
      finish = function (error, value) {
        if (settled) return;
        settled = true;
        error ? reject(error) : resolve(value);
      };
      xhr.open('GET', url, true);
      xhr.withCredentials = false;
      xhr.timeout = 12000;
      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        try {
          if (
            xhr.status < 200 ||
            xhr.status >= 300 ||
            xhr.responseText.length > 1024 * 1024
          )
            throw Error('weather-network');
          var body = JSON.parse(xhr.responseText);
          if (!body || body.error || body.success === false)
            throw Error('weather-response');
          finish(null, body);
        } catch (e) {
          finish(e);
        }
      };
      xhr.onerror =
        xhr.ontimeout =
        xhr.onabort =
          function () {
            finish(Error('weather-network'));
          };
      xhr.send();
    });
    return {
      promise: promise,
      cancel: function () {
        xhr.abort();
        finish(Error('weather-cancelled'));
      }
    };
  }
  function create(env) {
    env = env || {};
    var storage =
        env.storage ||
        (typeof localStorage !== 'undefined' ? localStorage : null),
      now = env.now || Date.now,
      request = env.request || xhrRequest;
    var saved = {};
    try {
      saved = JSON.parse(storage.getItem(KEY) || '{}') || {};
    } catch (_) {}
    var model = {
      provider:
        ['auto', 'met-no', 'open-meteo'].indexOf(saved.provider) >= 0
          ? saved.provider
          : Object.keys(saved).length
            ? 'open-meteo'
            : 'auto',
      source: null,
      enabled: saved.enabled === true,
      units: saved.units === 'imperial' ? 'imperial' : 'metric',
      preferred:
        formats.indexOf(saved.preferred) >= 0 ? saved.preferred : 'text',
      mode: saved.mode === 'auto' ? 'auto' : 'manual',
      location: location(saved.location),
      data: null,
      updated: 0,
      stale: false,
      status: 'choose',
      results: [],
      searchStatus: 'idle'
    };
    var allowed = true,
      language = env.language || 'en',
      locationLanguage = saved.locationLanguage || '',
      autoUpdated = finite(saved.autoUpdated) || 0,
      active = null,
      searchActive = null,
      generation = 0,
      searchGeneration = 0,
      retryAt = 0,
      listeners = [],
      dead = false,
      caches = {},
      metAttempt = readMetAttempt(saved.metAttempt),
      lastSource =
        saved.lastSource === 'met-no' || saved.lastSource === 'open-meteo'
          ? saved.lastSource
          : null;
    function key() {
      return model.location
        ? model.location.latitude.toFixed(3) +
            ',' +
            model.location.longitude.toFixed(3)
        : '';
    }
    function metKey(place) {
      return place
        ? String(Math.round(place.latitude * 10000) / 10000) +
            ',' +
            String(Math.round(place.longitude * 10000) / 10000)
        : '';
    }
    function readMetAttempt(value) {
      if (value === undefined || value === null) return null;
      var parts = typeof value.key === 'string' ? value.key.split(',') : [],
        place = { latitude: Number(parts[0]), longitude: Number(parts[1]) },
        validKey =
          parts.length === 2 &&
          bounded(place.latitude, -90, 90) !== null &&
          bounded(place.longitude, -180, 180) !== null &&
          metKey(place) === value.key;
      // Bad/future records impose one bounded cooldown, never an indefinite lockout.
      return {
        key: validKey ? value.key : metKey(model.location),
        at: !validKey || bounded(value.at, 0, now()) === null ? now() : value.at
      };
    }
    function persist() {
      try {
        storage.setItem(
          KEY,
          JSON.stringify({
            version: 1,
            provider: model.provider,
            lastSource: lastSource,
            metAttempt: metAttempt,
            caches: caches,
            enabled: model.enabled,
            units: model.units,
            preferred: model.preferred,
            mode: model.mode,
            location: model.location,
            locationLanguage: locationLanguage,
            autoUpdated: autoUpdated
          })
        );
      } catch (_) {}
    }
    function freshAge() {
      return model.source === 'met-no' ? MET_FRESH : FRESH;
    }
    function useCache() {
      var source =
          model.provider === 'auto' ? lastSource || 'met-no' : model.provider,
        cache = caches[source];
      if (!cache && model.provider === 'auto') {
        source = source === 'met-no' ? 'open-meteo' : 'met-no';
        cache = caches[source];
      }
      model.data = null;
      model.source = null;
      model.updated = 0;
      model.stale = false;
      if (
        cache &&
        cache.key === key() &&
        now() >= cache.updated &&
        now() - cache.updated <= MAX_AGE
      ) {
        model.data = cache.data;
        model.source = source;
        model.updated = cache.updated;
        model.stale = now() - cache.updated >= freshAge();
      }
      model.status = model.data
        ? model.stale
          ? 'stale'
          : 'ready'
        : model.location
          ? 'loading'
          : 'choose';
    }
    function expire() {
      if (
        model.data &&
        (now() - model.updated > MAX_AGE || now() < model.updated)
      ) {
        if (model.source) delete caches[model.source];
        model.data = null;
        model.source = null;
        model.stale = false;
        model.status = active ? 'loading' : model.location ? 'error' : 'choose';
        persist();
        emit();
      }
    }
    function emit() {
      listeners.slice().forEach(function (fn) {
        fn(state());
      });
    }
    function state() {
      expire();
      if (model.source === 'met-no' && model.data) {
        // Cached forecasts can cross a DST change without needing a new request.
        model.data.offset = calendarOffset(
          calendarFormatter(timezone(model.data.timezone) || 'UTC'),
          now()
        );
      }
      return JSON.parse(JSON.stringify(model));
    }
    function cancel() {
      generation++;
      if (active) active.cancel();
      active = null;
      searchGeneration++;
      if (searchActive) searchActive.cancel();
      searchActive = null;
      model.searchStatus = 'idle';
    }
    function fetch(url) {
      active = request(url);
      return active.promise;
    }
    function geoLanguage() {
      return language.indexOf('zh') === 0 ? 'zh' : language.split('-')[0];
    }
    function refresh(force) {
      expire();
      if (
        dead ||
        !model.enabled ||
        !allowed ||
        active ||
        (!force && now() < retryAt)
      )
        return Promise.resolve();
      if (!model.location && model.mode === 'manual') {
        model.status = 'choose';
        emit();
        return Promise.resolve();
      }
      if (
        model.data &&
        !model.stale &&
        now() - model.updated < freshAge() &&
        locationLanguage === language &&
        !force
      )
        return Promise.resolve();
      var token = ++generation;
      model.status = model.data
        ? 'ready'
        : model.location
          ? 'loading'
          : 'locating';
      emit();
      var flow = Promise.resolve();
      if (
        model.mode === 'auto' &&
        (!model.location || now() - autoUpdated > AUTO_AGE)
      ) {
        // GeoJS has a CORS-capable, keyless JSON endpoint. Do not retain IP/ASN fields.
        flow = flow
          .then(function () {
            if (token !== generation) return null;
            return fetch('https://get.geojs.io/v1/ip/geo.json');
          })
          .then(function (body) {
            if (token !== generation) return;
            var l = location({
              name: body.city,
              latitude: Number(body.latitude),
              longitude: Number(body.longitude),
              country: body.country_code || body.country,
              admin1: body.region,
              timezone: body.timezone
            });
            if (!l) throw Error('weather-location');
            if (
              key() !==
              l.latitude.toFixed(3) + ',' + l.longitude.toFixed(3)
            ) {
              model.data = null;
              model.updated = 0;
              model.source = null;
              caches = {};
              lastSource = null;
            }
            model.location = l;
            autoUpdated = now();
            locationLanguage = language;
            persist();
          });
      }
      flow = flow.then(function () {
        if (token !== generation) return;
        if (
          model.location &&
          model.location.id &&
          locationLanguage !== language
        )
          return fetch(
            query('https://geocoding-api.open-meteo.com/v1/get', {
              id: model.location.id,
              language: geoLanguage()
            })
          ).then(
            function (body) {
              if (token !== generation) return;
              var l = location(body);
              if (l && l.id === model.location.id) {
                model.location = l;
                if (model.data) model.data.city = l.name;
                Object.keys(caches).forEach(function (source) {
                  caches[source].data.city = l.name;
                });
                locationLanguage = language;
                persist();
              }
            },
            function () {}
          );
      });
      return flow
        .then(function () {
          if (token !== generation) return;
          if (
            !force &&
            model.data &&
            !model.stale &&
            now() - model.updated < freshAge()
          )
            return null;
          var first =
            model.provider === 'auto' ? lastSource || 'met-no' : model.provider;
          function attempt(source, fallback) {
            if (token !== generation) return Promise.resolve();
            var cache = caches[source];
            if (
              (source === 'met-no' || !force || source !== first) &&
              cache &&
              cache.key === key() &&
              now() >= cache.updated &&
              now() - cache.updated < (source === 'met-no' ? MET_FRESH : FRESH)
            ) {
              model.data = cache.data;
              model.source = source;
              model.updated = cache.updated;
              model.stale = false;
              lastSource = source;
              return Promise.resolve();
            }
            var operation = Promise.resolve()
              .then(function () {
                if (token !== generation) return;
                if (source === 'met-no') {
                  if (!env.metRequest) throw Error('weather-unavailable');
                  if (
                    metAttempt &&
                    metAttempt.key === metKey(model.location) &&
                    now() - metAttempt.at < MET_FRESH
                  )
                    throw Error('weather-cooldown');
                  metAttempt = { key: metKey(model.location), at: now() };
                  persist();
                  active = env.metRequest(model.location);
                  return active.promise;
                }
                return fetch(
                  query('https://api.open-meteo.com/v1/forecast', {
                    latitude: model.location.latitude,
                    longitude: model.location.longitude,
                    current:
                      'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m',
                    daily:
                      'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                    wind_speed_unit: 'ms',
                    temperature_unit: 'celsius',
                    forecast_days: 4,
                    timezone: 'auto'
                  })
                );
              })
              .then(function (body) {
                if (token !== generation) return;
                var data =
                  source === 'met-no'
                    ? normalizeMet(body, model.location, now())
                    : normalize(body, model.location);
                model.data = data;
                model.source = source;
                model.updated = now();
                model.stale = false;
                lastSource = source;
                caches[source] = {
                  key: key(),
                  updated: model.updated,
                  data: data
                };
              });
            return operation.catch(function (error) {
              if (token !== generation) return;
              if (fallback)
                return attempt(
                  source === 'met-no' ? 'open-meteo' : 'met-no',
                  false
                );
              throw error;
            });
          }
          return attempt(first, model.provider === 'auto');
        })
        .then(function () {
          if (token !== generation) return;
          model.status = 'ready';
          retryAt = 0;
          persist();
        })
        .catch(function () {
          if (token !== generation) return;
          retryAt = now() + RETRY;
          expire();
          model.stale = !!model.data;
          model.status = model.data
            ? 'stale'
            : model.mode === 'auto' && !model.location
              ? 'location-error'
              : 'error';
        })
        .then(function () {
          if (token === generation) {
            active = null;
            emit();
          }
        });
    }
    function start() {
      ['met-no', 'open-meteo'].forEach(function (source) {
        var cache = saved.caches && saved.caches[source];
        if (!cache && source === 'open-meteo') cache = saved.cache;
        if (
          !cache ||
          !model.location ||
          cache.key !== key() ||
          finite(cache.updated) === null ||
          now() < cache.updated ||
          now() - cache.updated > MAX_AGE ||
          !cache.data ||
          finite(cache.data.temp) === null ||
          !Array.isArray(cache.data.days)
        )
          return;
        try {
          var data = cache.data,
            days = data.days.filter(function (day) {
              return day && typeof day === 'object';
            });
          var sanitized = normalize(
            {
              current: {
                temperature_2m: data.temp,
                apparent_temperature: data.feels,
                wind_speed_10m: data.wind,
                relative_humidity_2m: data.humidity,
                weather_code: data.code,
                is_day: data.isDay === false ? 0 : 1,
                time: data.time
              },
              daily: {
                time: days.map(function (d) {
                  return d.date;
                }),
                temperature_2m_min: days.map(function (d) {
                  return d.low;
                }),
                temperature_2m_max: days.map(function (d) {
                  return d.high;
                }),
                weather_code: days.map(function (d) {
                  return d.code;
                }),
                precipitation_probability_max: [data.precip]
              },
              timezone: data.timezone,
              utc_offset_seconds: data.offset
            },
            model.location
          );
          caches[source] = {
            key: key(),
            updated: cache.updated,
            data: sanitized
          };
        } catch (_) {}
      });
      useCache();
      persist();
      return refresh();
    }
    function setPreferences(next) {
      if (!next || typeof next !== 'object') throw Error('weather-preferences');
      Object.keys(next).forEach(function (k) {
        if (
          (k === 'enabled' && typeof next[k] === 'boolean') ||
          (k === 'units' && ['metric', 'imperial'].indexOf(next[k]) >= 0) ||
          (k === 'preferred' && formats.indexOf(next[k]) >= 0) ||
          (k === 'provider' &&
            ['auto', 'met-no', 'open-meteo'].indexOf(next[k]) >= 0)
        )
          return;
        else throw Error('weather-preferences');
      });
      var changed = next.provider && next.provider !== model.provider;
      if (changed) cancel();
      Object.keys(next).forEach(function (k) {
        model[k] = next[k];
      });
      if (changed) {
        retryAt = 0;
        useCache();
      }
      if (!model.enabled) cancel();
      persist();
      emit();
      if (model.enabled) return refresh();
      return Promise.resolve();
    }
    function setAllowed(value) {
      if (allowed === !!value) return;
      allowed = !!value;
      if (!allowed) cancel();
      else refresh();
      emit();
    }
    function setLanguage(value) {
      if (language === value) return;
      cancel();
      language = text(value, 20) || 'en';
      model.results = [];
      emit();
      refresh();
    }
    function setMode(value) {
      if (['manual', 'auto'].indexOf(value) < 0) throw Error('weather-mode');
      if (model.mode === value) return;
      cancel();
      model.mode = value;
      caches = {};
      lastSource = null;
      model.source = null;
      model.location = null;
      model.data = null;
      model.updated = 0;
      model.results = [];
      model.status = 'choose';
      retryAt = 0;
      persist();
      emit();
      return refresh();
    }
    function search(term) {
      if (!model.enabled || !allowed || dead) return Promise.resolve();
      term = text(term, 100) || '';
      var token = ++searchGeneration;
      if (searchActive) searchActive.cancel();
      model.results = [];
      if (term.length < 2) {
        model.searchStatus = 'short';
        emit();
        return Promise.resolve();
      }
      model.searchStatus = 'loading';
      emit();
      searchActive = request(
        query('https://geocoding-api.open-meteo.com/v1/search', {
          name: term,
          count: 5,
          language: geoLanguage(),
          format: 'json'
        })
      );
      return searchActive.promise
        .then(
          function (body) {
            if (token !== searchGeneration) return;
            model.results = (Array.isArray(body.results) ? body.results : [])
              .slice(0, 5)
              .map(location)
              .filter(function (l) {
                return l && l.id;
              });
            model.searchStatus = model.results.length ? 'results' : 'empty';
          },
          function () {
            if (token === searchGeneration) model.searchStatus = 'error';
          }
        )
        .then(function () {
          if (token === searchGeneration) {
            searchActive = null;
            emit();
          }
        });
    }
    function select(id) {
      var l = model.results.filter(function (r) {
        return r.id === id;
      })[0];
      if (!l) return;
      cancel();
      model.mode = 'manual';
      if (key() !== l.latitude.toFixed(3) + ',' + l.longitude.toFixed(3)) {
        caches = {};
        lastSource = null;
      }
      model.location = l;
      model.source = null;
      model.data = null;
      model.updated = 0;
      model.results = [];
      model.status = 'loading';
      locationLanguage = language;
      retryAt = 0;
      persist();
      emit();
      return refresh();
    }
    return {
      state: state,
      start: start,
      refresh: refresh,
      search: search,
      select: select,
      setMode: setMode,
      setLanguage: setLanguage,
      setAllowed: setAllowed,
      setPreferences: setPreferences,
      onChange: function (fn) {
        listeners.push(fn);
        return function () {
          listeners = listeners.filter(function (f) {
            return f !== fn;
          });
        };
      },
      destroy: function () {
        dead = true;
        cancel();
        listeners = [];
      },
      clear: function () {
        cancel();
        storage.removeItem(KEY);
        caches = {};
        lastSource = null;
        model.source = null;
        model.enabled = false;
        model.location = null;
        model.data = null;
        emit();
      }
    };
  }
  function example() {
    return {
      city: null,
      temp: -3,
      feels: -7,
      wind: 4,
      humidity: 78,
      precip: 20,
      code: 3,
      isDay: true,
      timezone: 'UTC',
      offset: 0,
      days: [
        [-7, -1, 3],
        [-8, -2, 73],
        [-5, 0, 2],
        [-4, 1, 0]
      ].map(function (v, i) {
        var date = new Date();
        date.setUTCDate(date.getUTCDate() + i);
        return {
          date: date.toISOString().slice(0, 10),
          low: v[0],
          high: v[1],
          code: v[2]
        };
      })
    };
  }
  return {
    create: create,
    normalize: normalize,
    normalizeMet: normalizeMet,
    condition: condition,
    example: example,
    key: KEY,
    formats: formats
  };
});
