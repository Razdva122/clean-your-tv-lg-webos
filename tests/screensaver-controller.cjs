'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { create } = require('../screensaver/controller');

test('a controller owns only its fixed popup and suppresses LG only while ready', () => {
  let receive, current, tick;
  let time = 0;
  const commands = [];
  const controller = create({
    generation: 9,
    now: () => time,
    listen: (get, onMessage, done) => {
      current = get;
      receive = onMessage;
      done(null, { endpoint: 'http://127.0.0.1:1234/screensaver', close() {} });
    },
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval() {},
    launch(id, params, done) {
      commands.push([id, params]);
      done(true);
    },
    context: () => ({
      ownerHealthy: true,
      popupSupported: true,
      previewEligible: true
    })
  });
  assert.equal(controller.preview(), false);
  controller.enable();
  assert.equal(controller.preview(), true);
  const [id, params] = commands[0];
  assert.equal(id, 'com.cleanyourtv.screensaver');
  assert.match(params.sessionId, /^[0-9a-f]{48}$/);
  assert.equal(controller.getSession(), null);
  assert.equal(
    receive({
      schema: 1,
      ...current(),
      visible: true,
      focused: true,
      mediaState: 'ready'
    }).close,
    false
  );
  assert.equal(controller.getSession().state, 'visible');
  controller.stop();
  assert.equal(controller.getSession(), null);
  assert.equal(
    receive({
      schema: 1,
      ...params,
      visible: true,
      focused: true,
      mediaState: 'ready'
    }).close,
    true
  );
  time += 3000;
  tick();
  assert.equal(current(), null);
  assert.equal(commands.length, 1);
});

test('verified in-app inactivity waits for the full interval after activity', () => {
  let time = 100;
  let launches = 0;
  const controller = create({
    generation: 2,
    now: () => time,
    listen: (get, onMessage, done) =>
      done(null, { endpoint: 'http://127.0.0.1:1234/screensaver', close() {} }),
    setInterval: () => 1,
    clearInterval() {},
    launch(id, params, done) {
      launches++;
      done(true);
    },
    context: () => ({
      ownerHealthy: true,
      popupSupported: true,
      inAppEligible: true,
      idleTimeoutMs: 5000
    })
  });
  controller.enable();
  controller.activity();
  time = 5099;
  assert.equal(controller.eligible(), false);
  time = 5100;
  assert.equal(controller.eligible(), true);
  assert.equal(launches, 1);
  controller.dispose();
});

test('invalid video falls back to ambient glow and releases the media lease once', () => {
  let receive, serve, params;
  let released = 0;
  const controller = create({
    generation: 7,
    listen: (get, onMessage, done, onMedia) => {
      receive = onMessage;
      serve = onMedia;
      done(null, { endpoint: 'http://127.0.0.1:1234/screensaver', close() {} });
    },
    setInterval: () => 1,
    clearInterval() {},
    launch(id, value, done) {
      params = value;
      done(true);
    },
    acquireMedia: () => ({
      mode: 'video',
      lease: {
        contentType: 'video/mp4',
        serve(req, res) {
          res.served = true;
        },
        release() {
          released++;
        }
      }
    }),
    context: () => ({
      ownerHealthy: true,
      popupSupported: true,
      previewEligible: true,
      clockOverlay: true,
      clock: { locale: 'ru', hour12: true }
    })
  });
  controller.enable();
  assert.equal(controller.preview(), true);
  const loading = {
    schema: 1,
    ...params,
    visible: true,
    focused: true,
    mediaState: 'loading'
  };
  const path = `/screensaver/media/${params.sessionId}`;
  assert.deepEqual(receive(loading), {
    close: false,
    content: {
      mode: 'video',
      url: 'http://127.0.0.1:1234' + path,
      clockOverlay: true,
      clock: { locale: 'ru', hour12: true }
    }
  });
  const response = {};
  assert.equal(serve(params, {}, response), true);
  assert.deepEqual(response, { served: true });
  assert.deepEqual(receive({ ...loading, mediaState: 'error' }), {
    close: false,
    content: {
      mode: 'ambient',
      clockOverlay: true,
      clock: { locale: 'ru', hour12: true }
    }
  });
  assert.equal(serve(params, {}, {}), false);
  assert.equal(receive({ ...loading, mediaState: 'ready' }).close, false);
  assert.equal(controller.getSession().state, 'visible');
  controller.dispose();
  assert.equal(released, 1);
});

test('owner revocation during asset acquisition releases the returned lease without launching', () => {
  let launches = 0;
  let releases = 0;
  const controller = create({
    generation: 8,
    listen: (get, onMessage, done) =>
      done(null, { endpoint: 'http://127.0.0.1:1234/screensaver', close() {} }),
    setInterval: () => 1,
    clearInterval() {},
    launch() {
      launches++;
    },
    acquireMedia: () => {
      controller.dispose();
      return {
        mode: 'photo',
        lease: {
          contentType: 'image/png',
          serve() {},
          release() {
            releases++;
          }
        }
      };
    },
    context: () => ({
      ownerHealthy: true,
      popupSupported: true,
      previewEligible: true
    })
  });
  controller.enable();
  assert.equal(controller.preview(), false);
  assert.equal(launches, 0);
  assert.equal(releases, 1);
});

test('the first request can wait for the loopback listener without launching after disposal', async () => {
  for (const disposed of [false, true]) {
    let listening;
    let launches = 0;
    const controller = create({
      generation: 3,
      listen: (_get, _receive, ready) => {
        listening = ready;
      },
      launch(_id, _params, done) {
        launches += 1;
        done(true);
      },
      context: () => ({
        ownerHealthy: true,
        popupSupported: true,
        previewEligible: true
      })
    });
    controller.enable();
    const firstPreview = controller
      .whenReady()
      .then((ready) => ready && controller.preview());
    assert.equal(launches, 0);
    if (disposed) controller.dispose();
    listening(null, {
      endpoint: 'http://127.0.0.1:1234/screensaver',
      close() {}
    });
    assert.equal(await firstPreview, !disposed);
    assert.equal(launches, disposed ? 0 : 1);
    controller.dispose();
  }
});
