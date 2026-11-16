'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const acorn = require('acorn');
const file = path.resolve(__dirname, '../screensaver/settings.js');
assert.ok(fs.existsSync(file), 'shared settings module exists');
const settings = require(file);
const cacheRoot = 'http://127.0.0.1:12345/' + 'a'.repeat(32) + '/';
assert.equal(settings.personalMediaUrl('photo', cacheRoot + '4k.mp4'), true);
assert.equal(settings.personalMediaUrl('photo', cacheRoot + 'photo.png'), true);
assert.equal(settings.personalMediaUrl('video', cacheRoot + '1080p.mp4'), true);
assert.equal(settings.personalMediaUrl('video', cacheRoot + 'photo.jpg'), true);
assert.equal(
  settings.personalMediaUrl('photo', cacheRoot + 'photo.png\n'),
  false
);
assert.equal(
  settings.personalMediaUrl('video', cacheRoot + '../4k.mp4'),
  false
);
assert.equal(
  settings.personalMediaUrl(
    'video',
    cacheRoot.replace('127.0.0.1', 'localhost') + '4k.mp4'
  ),
  false
);
const defaults = {
  enabled: false,
  scope: 'global',
  mode: 'ambient',
  assetId: '',
  clockOverlay: true,
  quality: 'auto',
  idleTimeoutMs: 60000
};
assert.equal(settings.normalize({ enabled: true }).scope, 'global');
assert.equal(
  settings.normalize({ enabled: true, scope: 'cytv' }).scope,
  'global'
);
assert.equal(
  settings.normalize({
    enabled: true,
    scope: 'global',
    mode: 'video',
    assetId: 'personal-video'
  }).scope,
  'cytv'
);
assert.deepEqual(settings.normalize(), defaults);
assert.equal(
  settings.normalize({ ...defaults, clockOverlay: false }).clockOverlay,
  false
);
assert.equal(settings.normalize({ mode: 'clock' }).mode, 'clock');
assert.equal(
  settings.canActivate(
    { ...defaults, enabled: true },
    {
      popupSupported: true,
      inAppEligible: true
    }
  ),
  true
);
assert.deepEqual(settings.normalize(null), defaults);
assert.deepEqual(settings.normalize([]), defaults);
assert.deepEqual(
  settings.normalize({
    enabled: 'true',
    scope: 'all',
    mode: 'html',
    assetId: 'file:///private/photo.jpg',
    idleTimeoutMs: '120000'
  }),
  defaults
);
assert.deepEqual(
  settings.normalize(Object.create({ enabled: true, scope: 'global' })),
  defaults,
  'inherited options cannot silently enable feature'
);
const desired = {
  enabled: true,
  scope: 'global',
  mode: 'video',
  assetId: 'asset_ABC-123',
  clockOverlay: false,
  quality: '1080p',
  idleTimeoutMs: 123456
};
assert.deepEqual(settings.normalize(desired), desired);
assert.deepEqual(
  desired,
  {
    enabled: true,
    scope: 'global',
    mode: 'video',
    assetId: 'asset_ABC-123',
    clockOverlay: false,
    quality: '1080p',
    idleTimeoutMs: 123456
  },
  'normalization never mutates input'
);
for (const [input, expected] of [
  [0, 30000],
  [-1, 30000],
  [29999, 30000],
  [1800001, 1800000],
  [60000.7, 60001],
  [Infinity, 60000],
  [NaN, 60000]
]) {
  assert.equal(
    settings.normalize({ idleTimeoutMs: input }).idleTimeoutMs,
    expected
  );
}
for (const assetId of [
  'https://example.org/photo',
  '../photo',
  '/photo',
  'file:photo',
  'a/b',
  'a\\b',
  'a%2fb',
  'a b',
  'a\n',
  'x'.repeat(129)
]) {
  assert.equal(
    settings.normalize({ assetId }).assetId,
    '',
    'asset reference cannot authorize a URL or path'
  );
}
assert.equal(settings.canActivate({ enabled: true }), false);
assert.equal(
  settings.canActivate(defaults, { popupSupported: true, inAppEligible: true }),
  false,
  'default remains disabled even with capability'
);
assert.equal(
  settings.canActivate(
    { enabled: true },
    { popupSupported: true, inAppEligible: true }
  ),
  true
);
assert.equal(
  settings.canActivate(
    { enabled: true, mode: 'photo' },
    { popupSupported: true, inAppEligible: true }
  ),
  false,
  'photo needs an explicit opaque asset'
);
assert.equal(
  settings.canActivate(
    { enabled: true, mode: 'photo', assetId: 'photo1' },
    { popupSupported: true, inAppEligible: true }
  ),
  true
);
assert.equal(
  settings.canActivate(desired, { popupSupported: true, globalEligible: true }),
  false,
  'global eligibility alone cannot bypass unverified trigger'
);
assert.equal(
  settings.canActivate(desired, {
    popupSupported: true,
    globalTriggerVerified: true
  }),
  false,
  'verified trigger cannot imply current playback eligibility'
);
assert.equal(
  settings.canActivate(desired, {
    popupSupported: true,
    globalTriggerVerified: true,
    globalEligible: true
  }),
  true
);
assert.deepEqual(
  settings.normalize(desired),
  desired,
  'capability absence preserves requested global intent'
);
const source = fs.readFileSync(file, 'utf8');
acorn.parse(source, { ecmaVersion: 5 });
const browser = {};
vm.runInNewContext(source, browser);
assert.equal(
  browser.CYTVScreensaverSettings.canActivate(
    { enabled: true },
    { popupSupported: true, inAppEligible: true }
  ),
  true,
  'browser uses the same settings contract'
);
console.log(
  'screensaver settings: normalization, explicit eligibility, intent retention and browser ES5 checks passed'
);
