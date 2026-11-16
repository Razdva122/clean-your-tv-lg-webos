'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const EventEmitter = require('node:events');
assert.ok(
  fs.existsSync(path.join(__dirname, 'screensaver.js')),
  'Root adapter exists'
);
const create = require('./screensaver');
const controller = require('../../screensaver/controller');
const createLG = require('../../native/app/screensaver-lg');
let owner = {
  active: true,
  generation: 7,
  healthy: true,
  legacyHelperActive: false
};
let time = 1000;
let update;
let currentIdentity;
let wireClosed = 0;
let subscription;
let cancelled = 0;
let popupSupported;
let opened = 0;
let subscriptions = 0;
let acquiredMedia = 0;
let releasedMedia = 0;
let nextTimer = 0;
const timers = new Set();
const launches = [];
const acknowledgements = [];
const service = {
  subscribe(uri, payload) {
    subscriptions += 1;
    assert.equal(
      uri,
      'luna://com.webos.service.tvpower/power/registerScreenSaverRequest'
    );
    assert.equal(payload.subscribe, true);
    subscription = new EventEmitter();
    subscription.cancel = () => {
      cancelled += 1;
    };
    return subscription;
  },
  call(uri, payload, callback) {
    assert.equal(
      uri,
      'luna://com.webos.service.tvpower/power/responseScreenSaverRequest'
    );
    acknowledgements.push(payload);
    callback({ payload: { returnValue: true } });
  }
};
const adapter = create({
  controller,
  createLG,
  service,
  getOwner: () => owner,
  context: () => ({
    popupSupported,
    previewEligible: true,
    inAppEligible: true,
    globalTriggerVerified: true,
    globalEligible: true,
    idleTimeoutMs: 100
  }),
  now: () => time,
  setInterval: () => {
    timers.add(++nextTimer);
    return nextTimer;
  },
  clearInterval: (timer) => timers.delete(timer),
  acquireMedia() {
    acquiredMedia += 1;
    return {
      mode: 'video',
      lease: {
        contentType: 'video/mp4',
        serve: () => {},
        release: () => {
          releasedMedia += 1;
        }
      }
    };
  },
  listen(getSession, receive, ready) {
    opened += 1;
    currentIdentity = getSession;
    update = receive;
    ready(null, {
      endpoint: 'http://127.0.0.1:12345/screensaver',
      close: () => {
        wireClosed += 1;
      }
    });
  },
  launch(id, params, done) {
    launches.push({ id, params });
    done(true);
  }
});
function ready() {
  const session = currentIdentity();
  assert.ok(session);
  return update({
    schema: 1,
    sessionId: session.sessionId,
    generation: session.generation,
    visible: true,
    focused: true,
    mediaState: 'ready'
  });
}
assert.equal(
  adapter.preview(7),
  false,
  'construction does not activate screensaver'
);
assert.equal(adapter.enable(6), false, 'stale generation cannot enable');
assert.equal(
  adapter.enable(7),
  false,
  'missing popup capability refuses enable'
);
assert.equal(opened, 0, 'unsupported popup must not allocate transport');
assert.equal(subscriptions, 0, 'unsupported popup must not register LG client');
assert.equal(acquiredMedia, 0, 'unsupported owner cannot acquire media');
assert.equal(timers.size, 0, 'the dormant adapter must not schedule polling');
popupSupported = true;
assert.equal(adapter.enable(7), true);
assert.equal(adapter.preview(7), true);
assert.equal(launches[0].id, 'com.cleanyourtv.screensaver');
const firstReady = ready();
assert.equal(firstReady.close, false);
assert.equal(
  firstReady.content.mode,
  'video',
  'Root host media lease reaches shared renderer contract'
);
subscription.emit('response', {
  payload: { returnValue: true, subscribed: true }
});
subscription.emit('response', {
  payload: { returnValue: true, state: 'Active', timestamp: '9007199254740993' }
});
assert.equal(
  acknowledgements[0].ack,
  false,
  'only active healthy owned popup defers LG'
);
assert.equal(
  adapter.stop(6),
  false,
  'late old-owner stop must not close active popup'
);
assert.equal(ready().close, false);
assert.equal(adapter.activity(6), false);
assert.equal(ready().close, false);
assert.equal(adapter.stop(7), true);
assert.equal(wireClosed, 1, 'explicit stop releases controller transport');
assert.equal(cancelled, 1, 'explicit stop releases LG registration');
assert.equal(releasedMedia, 1, 'Root stop releases the owned media lease');
assert.equal(timers.size, 0, 'Root stop clears owned polling');
assert.equal(
  adapter.preview(7),
  false,
  'explicit stop is not automatically cleared'
);

assert.equal(adapter.enable(7), true);
assert.equal(adapter.preview(7), true);
ready();
const previousUpdate = update;
const previousSession = currentIdentity();
owner = {
  active: true,
  generation: 8,
  healthy: true,
  legacyHelperActive: false
};
adapter.reconcile();
assert.equal(adapter.preview(8), false, 'new generation needs explicit enable');
assert.equal(adapter.enable(8), true);
assert.equal(adapter.preview(8), true);
assert.equal(ready().close, false);
assert.equal(
  previousUpdate({
    schema: 1,
    ...previousSession,
    visible: true,
    focused: true,
    mediaState: 'ready'
  }).close,
  true,
  'old renderer cannot revive disposed owner'
);
assert.equal(adapter.stop(7), false);
assert.equal(ready().close, false);
owner.legacyHelperActive = true;
adapter.reconcile();
assert.equal(
  adapter.enable(8),
  false,
  'active legacy Helper is an ownership refusal'
);
assert.equal(adapter.getSession(), null);
owner.legacyHelperActive = false;
assert.equal(adapter.preview(8), false, 'recovery never auto-reenables');
assert.equal(adapter.enable(8), true);
adapter.activity(8);
time += 101;
assert.equal(
  adapter.eligible(8),
  true,
  'verified in-app eligibility uses shared idle policy'
);
ready();
owner.healthy = false;
assert.equal(
  adapter.getSession(),
  null,
  'unhealthy owner cannot supply a veto session'
);
assert.equal(adapter.preview(8), false);
owner.healthy = true;
assert.equal(adapter.preview(8), false);
assert.equal(adapter.enable(8), true);
assert.equal(adapter.preview(8), true);
ready();
const cancelledBeforeStandby = cancelled;
const closedBeforeStandby = wireClosed;
assert.equal(
  adapter.powerInactive(7),
  false,
  'stale standby does not affect current owner'
);
assert.equal(ready().close, false);
assert.equal(adapter.powerInactive(8), true);
assert.equal(
  cancelled,
  cancelledBeforeStandby + 1,
  'standby releases LG registration'
);
assert.equal(
  wireClosed,
  closedBeforeStandby + 1,
  'standby disposes controller transport'
);
assert.equal(adapter.getSession(), null);
assert.equal(
  adapter.preview(8),
  false,
  'wake requires explicit enable after standby'
);
function lgRequest(timestamp) {
  subscription.emit('response', {
    payload: { returnValue: true, subscribed: true }
  });
  subscription.emit('response', {
    payload: { returnValue: true, state: 'Active', timestamp }
  });
}
owner.generation = 9;
assert.equal(adapter.enable(9), true);
lgRequest('100');
assert.equal(ready().close, false);
assert.equal(acknowledgements.at(-1).ack, false);
owner.healthy = false;
adapter.reconcile();
owner.healthy = true;
assert.equal(adapter.enable(9), true);
const beforeNextIdle = launches.length;
lgRequest('101');
assert.equal(
  launches.length,
  beforeNextIdle,
  'same owner grants LG the next idle even after reconnect'
);
assert.equal(acknowledgements.at(-1).ack, true);
lgRequest('102');
assert.equal(
  launches.length,
  beforeNextIdle + 1,
  'only the next idle is reserved for LG'
);
ready();
owner.generation = 10;
assert.equal(adapter.enable(10), true);
lgRequest('103');
assert.equal(
  launches.length,
  beforeNextIdle + 2,
  'a new verified owner starts a new cycle'
);
ready();
adapter.dispose();
assert.equal(timers.size, 0, 'dispose clears owned polling');
assert.equal(adapter.enable(10), false, 'disposed adapter never restarts');
assert.ok(
  launches.every((item) => item.id === 'com.cleanyourtv.screensaver'),
  'no third-party app is touched'
);
console.log(
  'Root screensaver adapter: generation, recovery, legacy ownership, LG and stop checks passed'
);
