/* Trusted weather data. Themes never choose endpoints or access location/network APIs. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WeatherData = factory();
})(this, function () {
  'use strict';
  var KEY = 'tvhome.weather.v1',
    FRESH = 15 * 60000,
    MAX_AGE = 6 * 60 * 60000,
    RETRY = 5 * 60000,
    AUTO_AGE = 24 * 60 * 60000;
  var formats = ['text', 'current', 'details', 'forecast'];
  function finite(v) {
    return typeof v === 'number' && isFinite(v) ? v : null;
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
      feels: finite(c.apparent_temperature),
      wind: finite(c.wind_speed_10m),
      humidity: finite(c.relative_humidity_2m),
      precip: finite(
        d.precipitation_probability_max && d.precipitation_probability_max[0]
      ),
      code: finite(c.weather_code),
      isDay: c.is_day !== 0,
      time: text(c.time, 40) || '',
      timezone: text(body.timezone, 80) || 'UTC',
      offset: finite(body.utc_offset_seconds) || 0,
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
      dead = false;
    function key() {
      return model.location
        ? model.location.latitude.toFixed(3) +
            ',' +
            model.location.longitude.toFixed(3)
        : '';
    }
    function persist() {
      try {
        storage.setItem(
          KEY,
          JSON.stringify({
            version: 1,
            enabled: model.enabled,
            units: model.units,
            preferred: model.preferred,
            mode: model.mode,
            location: model.location,
            locationLanguage: locationLanguage,
            autoUpdated: autoUpdated,
            cache: model.data
              ? { key: key(), updated: model.updated, data: model.data }
              : null
          })
        );
      } catch (_) {}
    }
    function expire() {
      if (
        model.data &&
        (now() - model.updated > MAX_AGE || now() < model.updated)
      ) {
        model.data = null;
        model.stale = false;
      }
    }
    function emit() {
      listeners.slice().forEach(function (fn) {
        fn(state());
      });
    }
    function state() {
      expire();
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
        now() - model.updated < FRESH &&
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
              admin1: body.region
            });
            if (!l) throw Error('weather-location');
            if (
              key() !==
              l.latitude.toFixed(3) + ',' + l.longitude.toFixed(3)
            ) {
              model.data = null;
              model.updated = 0;
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
            now() - model.updated < FRESH
          )
            return null;
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
          if (body) {
            model.data = normalize(body, model.location);
            model.updated = now();
            model.stale = false;
          }
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
      var cache = saved.cache;
      if (
        cache &&
        cache.key === key() &&
        finite(cache.updated) !== null &&
        now() >= cache.updated &&
        now() - cache.updated <= MAX_AGE &&
        cache.data &&
        finite(cache.data.temp) !== null &&
        Array.isArray(cache.data.days)
      ) {
        model.data = cache.data;
        model.updated = cache.updated;
        model.stale = now() - cache.updated >= FRESH;
        model.status = model.stale ? 'stale' : 'ready';
      }
      return refresh();
    }
    function setPreferences(next) {
      if (!next || typeof next !== 'object') throw Error('weather-preferences');
      Object.keys(next).forEach(function (k) {
        if (
          (k === 'enabled' && typeof next[k] === 'boolean') ||
          (k === 'units' && ['metric', 'imperial'].indexOf(next[k]) >= 0) ||
          (k === 'preferred' && formats.indexOf(next[k]) >= 0)
        )
          model[k] = next[k];
        else throw Error('weather-preferences');
      });
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
      model.location = l;
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
    condition: condition,
    example: example,
    key: KEY,
    formats: formats
  };
});
