'use strict';
const fs = require('node:fs'),
  vm = require('node:vm'),
  assert = require('node:assert/strict');
const source = fs
  .readFileSync('tests/themes/wallpaper.cjs', 'utf8')
  .split('let f=fixture(undefined)')[0];
const fixture = vm.runInNewContext(source + ';fixture', { require });
function waiting() {
  const f = fixture(true),
    create = f.doc.createElement;
  let callback,
    cancelled = false;
  f.doc.createElement = function (tag) {
    const n = create(tag);
    if (tag === 'video') {
      n.videoWidth = 3840;
      n.videoHeight = 2160;
      n.requestVideoFrameCallback = (fn) => {
        callback = fn;
        return 42;
      };
      n.cancelVideoFrameCallback = (id) => {
        assert.equal(id, 42);
        cancelled = true;
      };
    }
    return n;
  };
  f.api.configure(f.input);
  const video = f.videos.at(-1);
  video.fire('playing');
  return {
    f,
    video,
    present: () => callback(0, { mediaTime: 0 }),
    cancelled: () => cancelled
  };
}
let test = waiting();
assert.equal(
  test.f.api.state().actualQuality,
  'image',
  'playing alone must not hide the poster before a video frame is presented'
);
assert.equal(
  test.f.nodes.homeSurface.classList.contains('ctv-wallpaper-playing'),
  false
);
assert.equal(
  test.video.poster,
  'blob:poster',
  'native video uses the same already-decoded poster'
);
test.present();
assert.equal(test.f.api.state().actualQuality, '4k');
assert(test.f.nodes.homeSurface.classList.contains('ctv-wallpaper-playing'));
test = waiting();
test.f.api.suspend('settings');
assert(test.cancelled(), 'detach cancels pending first-frame callback');
test.present();
assert.equal(test.f.api.state().actualQuality, 'image');
assert.equal(
  test.f.nodes.homeSurface.classList.contains('ctv-wallpaper-playing'),
  false,
  'a stale presented-frame callback cannot reveal detached media'
);
console.log(
  'PASS poster retained through playing, native poster, first presented frame and stale callback cancellation'
);
test = waiting();
test.video.readyState = 2;
test.video.currentTime = 0.04;
test.video.fire('timeupdate');
assert.equal(
  test.f.api.state().actualQuality,
  'image',
  'one advancing sample is not enough to bypass presented-frame confirmation'
);
test.video.currentTime = 0.08;
test.video.fire('timeupdate');
assert.equal(
  test.f.api.state().actualQuality,
  '4k',
  'decoded advancing frames must reveal video even when native presented-frame callback never arrives'
);
assert(
  test.cancelled(),
  'progress fallback cancels unused native frame callback'
);
test.present();
assert.equal(test.f.api.state().actualQuality, '4k');
test = waiting();
test.video.readyState = 1;
test.video.currentTime = 0.04;
test.video.fire('timeupdate');
test.video.currentTime = 0.08;
test.video.fire('timeupdate');
assert.equal(
  test.f.api.state().actualQuality,
  'image',
  'metadata progress cannot expose a video without decoded frame data'
);
test.f.api.suspend('settings');
console.log(
  'PASS missing native frame callback recovers only with decoded frame progress'
);
test = waiting();
test.video.readyState = 1;
const startupTimer = Array.from(test.f.timers.keys())[0];
for (let i = 1; i < 5; i++) {
  test.video.currentTime = i / 10;
  test.video.fire('timeupdate');
}
assert(
  test.f.timers.has(startupTimer),
  'progress without decoded frames cannot indefinitely postpone startup fallback'
);
test.f.timers.get(startupTimer)();
assert.equal(test.f.videos.at(-1).src, 'blob:fhd');
console.log('PASS undecoded progress keeps the bounded startup fallback');
